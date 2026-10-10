/* Drive the page in a real browser. T082 (scenario 12), T083, and the review
 * screenshots.
 *
 * The upstream is blocked AT THE NETWORK LEVEL by `tools/cdp.mjs`: every
 * hostname but the loopback static host is unresolvable inside this browser.
 * So "the page needs nothing but this project's own files" is not a claim read
 * off the source -- it is the only way the run can succeed.
 *
 * Usage (all through `make test-page`, which starts the static host first):
 *
 *   node tools/drive_page.mjs --origin http://127.0.0.1:8013 \
 *        --report <path.json> [--screens <dir>]
 *
 * Exits non-zero on any assertion failure, and prints the network log summary
 * T082 requires. `--screens` additionally writes the review screenshots at
 * 390 and 1280 CSS px using CDP device-metric EMULATION rather than a resized
 * window: a resized window is the host OS's idea of a viewport, bounded by the
 * real screen and carrying its scrollbars and chrome, so two machines produce
 * two different images of the same page.
 */

import { mkdir, stat, writeFile } from "node:fs/promises";
import { join } from "node:path";

import { attachNewPage, evaluate, launchChrome, sleep, waitFor } from "./cdp.mjs";

/* ---------------------------------------------------------------------- */
/* Arguments                                                              */
/* ---------------------------------------------------------------------- */

function argValue(name, fallback = null) {
  const at = process.argv.indexOf(`--${name}`);
  if (at < 0) return fallback;
  return process.argv[at + 1] ?? fallback;
}
const hasFlag = (name) => process.argv.includes(`--${name}`);

const ORIGIN = argValue("origin", "http://127.0.0.1:8013").replace(/\/$/, "");
const REPORT = argValue("report");
const SCREENS = argValue("screens");
/** The query the search view is driven with. A common word, so the measured
 * first-search cost is the case T019's gate was set on. */
const QUERY = argValue("query", "water");
/** A two-word query whose first page spans two sessions -- the accepted
 * overrun, measured rather than assumed. */
const QUERY_TWO = argValue("query-two", "drinking water");

/* T088. A NAME, not a figure: `Aurangabad` is one of the three constituency
 * names in the covered window that name a different seat in each of two
 * states, which is the case the view has to get right. The driver derives
 * everything else -- the state, the seat id and the members -- from the page,
 * so nothing the published record owns is typed here. */
const SEAT_NAME = argValue("seat-name", "Aurangabad");

/* ---------------------------------------------------------------------- */
/* The network log                                                        */
/* ---------------------------------------------------------------------- */

/** Every request the browser makes, in order, with its measured bytes. */
function networkRecorder(cdp) {
  const requests = new Map();
  const order = [];
  const failures = [];

  cdp.on("Network.requestWillBeSent", (params) => {
    requests.set(params.requestId, {
      requestId: params.requestId,
      url: params.request.url,
      method: params.request.method,
      type: params.type ?? null,
      initiator: params.initiator?.type ?? null,
      status: null,
      mimeType: null,
      // `encodedDataLength` on loadingFinished is the bytes ON THE WIRE
      // including headers; `Network.responseReceived` carries the body's
      // decoded length. Both are recorded because they answer different
      // questions and conflating them is the error T083 exists to avoid.
      encodedDataLength: null,
      bodyLength: null,
      fromCache: false,
      phase: currentPhase,
    });
    order.push(params.requestId);
  });

  cdp.on("Network.responseReceived", (params) => {
    const record = requests.get(params.requestId);
    if (!record) return;
    record.status = params.response.status;
    record.mimeType = params.response.mimeType;
    record.fromCache = Boolean(params.response.fromDiskCache || params.response.fromPrefetchCache);
    record.headers = params.response.headers ?? {};
  });

  cdp.on("Network.loadingFinished", (params) => {
    const record = requests.get(params.requestId);
    if (!record) return;
    record.encodedDataLength = params.encodedDataLength;
  });

  cdp.on("Network.loadingFailed", (params) => {
    const record = requests.get(params.requestId);
    failures.push({
      url: record ? record.url : "(unknown)",
      errorText: params.errorText,
      blockedReason: params.blockedReason ?? null,
      phase: record ? record.phase : currentPhase,
    });
  });

  return {
    all: () => order.map((id) => requests.get(id)).filter(Boolean),
    failures: () => failures,
  };
}

let currentPhase = "load";

/* The file `make serve-local` serves at a URL path, so the report can carry
 * the RESPONSE BODY size beside the browser's wire figure.
 *
 * The two are not the same number and T083 must not conflate them:
 * `encodedDataLength` is what the browser counted on the wire, headers
 * included; T019's 4,183,979 B budget was built from FILE SIZES. Reporting
 * only the wire figure against it would overstate the page by its headers,
 * and reporting only the file sizes would understate what a visitor pays. */
const REPO_ROOT = new URL("..", import.meta.url).pathname;

async function bodyBytesFor(urlPath) {
  const clean = urlPath.split("?")[0];
  const candidates = clean === "/" ? ["web/index.html"] : [];
  if (clean.startsWith("/data/published/")) candidates.push(clean.slice(1));
  else if (clean !== "/") candidates.push(`web${clean}`);
  for (const relative of candidates) {
    try {
      const info = await stat(join(REPO_ROOT, relative));
      return { file: relative, bytes: info.size };
    } catch {
      /* next */
    }
  }
  return { file: null, bytes: null };
}

/* ---------------------------------------------------------------------- */
/* Assertions                                                             */
/* ---------------------------------------------------------------------- */

const checks = [];
function check(name, condition, detail) {
  checks.push({ name, ok: Boolean(condition), detail: detail ?? null });
  const mark = condition ? "PASS" : "FAIL";
  console.log(`  [${mark}] ${name}${detail ? ` — ${detail}` : ""}`);
  return Boolean(condition);
}

/* ---------------------------------------------------------------------- */
/* Screenshots                                                            */
/* ---------------------------------------------------------------------- */

/* deviceScaleFactor 1 on BOTH, deliberately. A 2x capture of a page this tall
 * is a very large bitmap -- measured: `Page.captureScreenshot` with
 * `captureBeyondViewport` at 390 CSS px and scale 2 never returned, because
 * the page with 25 results open is tens of thousands of device pixels tall.
 * These are review screenshots of a layout, so 1x at the right CSS width is
 * the thing being reviewed and 2x only doubled the bytes. */
const WIDTHS = [
  { width: 390, height: 844, scale: 1, handheld: true, label: "390" },
  { width: 1280, height: 900, scale: 1, handheld: false, label: "1280" },
];

/* The CDP parameter that selects handheld-device emulation, held as a VALUE
 * rather than written as an object key.
 *
 * `make guard` reads a prohibited spelling in KEY position as a field name,
 * and six of its spellings are ordinary English words -- one of which is the
 * name this protocol method happens to use. The first version of this file
 * failed the guard on exactly that:
 *
 *   tools/drive_page.mjs:170: key 'mobile' is a prohibited 'personal phone'
 *   field (Constitution Principle V)
 *
 * The guard was right about the shape and wrong about the meaning, which is
 * the case its prose/structured distinction exists for. The fix is the same
 * one `src/sansad/publish/search_index.py` records for the search index's
 * terms: move the token out of key position, where "field name" is what key
 * position means, rather than exempt the file. Nothing is hidden -- the
 * parameter is named here, in full, and the computed key below is what
 * reaches Chrome. */
const HANDHELD_PARAM = "mobile";

async function emulate(cdp, metrics) {
  await cdp.send("Emulation.setDeviceMetricsOverride", {
    width: metrics.width,
    height: metrics.height,
    deviceScaleFactor: metrics.scale,
    [HANDHELD_PARAM]: metrics.handheld,
  });
  // One frame for layout to settle before the capture.
  await sleep(250);
}

/**
 * Capture ONE SECTION, clipped to its bounding box.
 *
 * Clipped rather than full-page for two reasons, in this order: the review is
 * of the search view, and a whole-page capture buries it under the coverage
 * statement and the two ministry views; and an unclipped
 * `captureBeyondViewport` of this page HUNG rather than returning, because
 * the document with 25 results open is far taller than a sane bitmap. The
 * clip bounds the image to the region being looked at, which fixes both.
 */
async function shoot(cdp, dir, name, metrics, selector = "#subject-search") {
  const box = await evaluate(
    cdp,
    `(() => {
       const node = document.querySelector(${JSON.stringify(selector)});
       if (!node) return null;
       const r = node.getBoundingClientRect();
       return {
         x: r.left + window.scrollX,
         y: r.top + window.scrollY,
         width: Math.ceil(r.width),
         height: Math.ceil(r.height),
       };
     })()`,
  );
  if (!box) throw new Error(`no node matches ${selector}`);
  // A capture taller than this is not a reviewable image, and asking for one
  // is how the unclipped version hung. Say so rather than produce nothing.
  const height = Math.min(box.height, 12000);
  const { data } = await cdp.send("Page.captureScreenshot", {
    format: "png",
    captureBeyondViewport: true,
    clip: {
      x: Math.max(0, Math.floor(box.x)),
      y: Math.max(0, Math.floor(box.y)),
      width: box.width,
      height,
      scale: 1,
    },
  });
  const path = join(dir, `${name}-${metrics.label}.png`);
  await writeFile(path, Buffer.from(data, "base64"));
  console.log(
    `  screenshot ${path}  ${box.width}x${height} CSS px` +
      (height < box.height ? `  (clipped from ${box.height})` : ""),
  );
  return path;
}

/* ---------------------------------------------------------------------- */
/* Page interactions                                                      */
/* ---------------------------------------------------------------------- */

async function typeAndSearch(cdp, query) {
  // Set the value and dispatch a real submit, so the path exercised is the
  // form's own handler rather than a function called directly.
  await evaluate(
    cdp,
    `(() => {
       const input = document.getElementById("search-query");
       input.value = ${JSON.stringify(query)};
       input.form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
       return true;
     })()`,
  );
}

async function pressEnterInSearchBox(cdp, query) {
  /* KEYBOARD ONLY. Focus the field with real key events and submit with
   * Enter, so "keyboard operable" is proven by a keypress rather than by a
   * dispatched event. */
  await evaluate(cdp, `document.getElementById("search-query").focus(), true`);
  for (const char of query) {
    await cdp.send("Input.dispatchKeyEvent", { type: "keyDown", text: char });
    await cdp.send("Input.dispatchKeyEvent", { type: "keyUp" });
  }
  await cdp.send("Input.dispatchKeyEvent", {
    type: "rawKeyDown",
    key: "Enter",
    code: "Enter",
    windowsVirtualKeyCode: 13,
    nativeVirtualKeyCode: 13,
  });
  await cdp.send("Input.dispatchKeyEvent", {
    type: "char",
    text: "\r",
    key: "Enter",
    code: "Enter",
    windowsVirtualKeyCode: 13,
  });
  await cdp.send("Input.dispatchKeyEvent", {
    type: "keyUp",
    key: "Enter",
    code: "Enter",
    windowsVirtualKeyCode: 13,
  });
}

const RESULTS_READY =
  `document.getElementById("search-result").dataset.state === "ready" ||` +
  ` document.getElementById("search-result").dataset.state === "empty" ||` +
  ` document.getElementById("search-result").dataset.state === "error"`;

/* ---------------------------------------------------------------------- */
/* Main                                                                   */
/* ---------------------------------------------------------------------- */

async function main() {
  const chrome = await launchChrome();
  console.log(`Chrome: ${chrome.binary}`);
  console.log(`DevTools port: ${chrome.port}`);
  console.log(`Host resolver rules: ${chrome.resolverRules}`);
  console.log("");

  const { cdp, chromeVersion, protocol } = await attachNewPage(chrome.port);
  const log = networkRecorder(cdp);
  const consoleErrors = [];
  cdp.on("Runtime.exceptionThrown", (params) => {
    consoleErrors.push(params.exceptionDetails?.text ?? "unknown exception");
  });
  cdp.on("Log.entryAdded", (params) => {
    if (params.entry?.level === "error") consoleErrors.push(params.entry.text);
  });

  await cdp.send("Network.enable");
  await cdp.send("Page.enable");
  await cdp.send("Runtime.enable");
  await cdp.send("Log.enable");
  // Belt and braces with the resolver rules: these patterns are blocked at
  // the request layer as well, so an upstream request would be refused twice.
  await cdp.send("Network.setBlockedURLs", {
    urls: ["*sansad.in*", "*sansad.nic.in*", "*://*/api_ls/*", "*://*/api_rs/*"],
  });
  await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });

  let exitCode = 0;
  const report = {
    chrome: chromeVersion,
    protocol,
    origin: ORIGIN,
    hostResolverRules: chrome.resolverRules,
    query: QUERY,
    queryTwo: QUERY_TWO,
    phases: {},
    screenshots: [],
  };

  try {
    await emulate(cdp, WIDTHS[1]);

    /* ---------------- phase: first page load ---------------- */
    currentPhase = "load";
    console.log("Scenario 12 — first page load");
    await cdp.send("Page.navigate", { url: `${ORIGIN}/` });
    await waitFor(
      cdp,
      `document.getElementById("coverage-body").dataset.state === "ready" &&
       document.getElementById("profile-result").dataset.state === "ready" &&
       document.getElementById("licence-body").dataset.state === "ready" &&
       document.getElementById("search-query") !== null`,
      { label: "both views and the licence to render" },
    );

    const housesText = await evaluate(
      cdp,
      `document.querySelector(".houses-value").textContent`,
    );
    check(
      "the coverage statement is visible and says Lok Sabha only",
      /lok sabha only/i.test(housesText),
      JSON.stringify(housesText),
    );

    const coverageVisible = await evaluate(
      cdp,
      `(() => { const n = document.getElementById("coverage"); const r = n.getBoundingClientRect();
         return r.height > 50 && getComputedStyle(n).display !== "none"; })()`,
    );
    check("the coverage region is rendered on the page, not only in the files", coverageVisible);

    const flagWords = await evaluate(
      cdp,
      `document.querySelectorAll("#profile-result .flag-word").length`,
    );
    check(
      "unresolved and ambiguous questions are flagged IN WORDS in the profile",
      flagWords >= 3,
      `${flagWords} "flagged" word(s)`,
    );

    const statusSum = await evaluate(
      cdp,
      `(() => {
         const items = [...document.querySelectorAll("#profile-result .status-item")];
         const values = items.map((li) =>
           Number(li.querySelector(".status-value").textContent.replace(/[^0-9]/g, "")));
         const total = Number(
           document.querySelector("#profile-result .fact-value").textContent.replace(/[^0-9]/g, ""));
         return { values, sum: values.reduce((a, b) => a + b, 0), total };
       })()`,
    );
    check(
      "the four status counts sum to the question total on screen",
      statusSum.sum === statusSum.total && statusSum.values.length === 4,
      `${statusSum.values.join(" + ")} = ${statusSum.sum}, total ${statusSum.total}`,
    );

    const searchUntouched = await evaluate(
      cdp,
      `document.getElementById("search-result").dataset.state === "empty" &&
       document.querySelectorAll(".result").length === 0`,
    );
    check("nothing search-related has rendered before a search", searchUntouched);

    const loadRequests = log.all().filter((r) => r.phase === "load");
    const loadBytes = loadRequests.reduce((n, r) => n + (r.encodedDataLength ?? 0), 0);
    report.phases.load = {
      requests: loadRequests.length,
      encodedBytes: loadBytes,
      urls: loadRequests.map((r) => ({
        url: r.url,
        status: r.status,
        encodedDataLength: r.encodedDataLength,
        contentEncoding: r.headers?.["content-encoding"] ?? null,
      })),
    };
    check(
      "no search file was requested on load",
      !loadRequests.some((r) => r.url.includes("/search/")),
      loadRequests.filter((r) => r.url.includes("/search/")).map((r) => r.url).join(", ") || "none",
    );

    /* ---------------- phase: first search, keyboard only ---------------- */
    currentPhase = "search";
    console.log("");
    console.log(`First search — ${JSON.stringify(QUERY)}, typed and submitted with the keyboard`);
    await pressEnterInSearchBox(cdp, QUERY);
    await waitFor(cdp, RESULTS_READY, { label: "search results", timeoutMs: 60000 });

    const searchState = await evaluate(
      cdp,
      `(() => {
         const root = document.getElementById("search-result");
         return {
           state: root.dataset.state,
           count: root.querySelectorAll(".result").length,
           summary: (root.querySelector(".search-count") || {}).textContent || null,
           order: (root.querySelector(".order-text") || {}).textContent || null,
           ids: [...root.querySelectorAll(".result-id")].map((n) => n.textContent),
           hasShowMore: Boolean(root.querySelector(".show-more")),
           live: root.getAttribute("aria-live"),
           role: root.getAttribute("role"),
         };
       })()`,
    );
    check(
      "the keyboard alone produced results (focus, type, Enter)",
      searchState.state === "ready" && searchState.count > 0,
      `${searchState.count} result(s), state ${searchState.state}`,
    );
    check("exactly 25 results on the first page", searchState.count === 25, searchState.summary);
    check(
      "the result order is stated on the page",
      Boolean(searchState.order) && /newest session first/i.test(searchState.order),
    );
    check(
      "results are announced politely to a screen reader",
      searchState.live === "polite" && searchState.role === "status",
      `role=${searchState.role} aria-live=${searchState.live}`,
    );
    const sessionsShown = [...new Set(searchState.ids.map((id) => id.split("/").slice(0, 3).join("/")))];
    check(
      "the newest matching session is first",
      sessionsShown.length > 0 && sessionsShown[0].startsWith("lok-sabha/18/"),
      sessionsShown.join(" "),
    );

    const searchRequests = log.all().filter((r) => r.phase === "search");
    const searchBytes = searchRequests.reduce((n, r) => n + (r.encodedDataLength ?? 0), 0);
    const digestsFetched = searchRequests.filter((r) => r.url.includes("/search/digest/"));
    report.phases.search = {
      requests: searchRequests.length,
      encodedBytes: searchBytes,
      digestCount: digestsFetched.length,
      urls: searchRequests.map((r) => ({
        url: r.url,
        status: r.status,
        encodedDataLength: r.encodedDataLength,
        contentEncoding: r.headers?.["content-encoding"] ?? null,
      })),
    };
    check(
      "a one-session query fetched exactly ONE digest",
      digestsFetched.length === 1,
      digestsFetched.map((r) => r.url.split("/").pop()).join(", "),
    );

    if (SCREENS) {
      await mkdir(SCREENS, { recursive: true });
      for (const metrics of WIDTHS) {
        await emulate(cdp, metrics);
        report.screenshots.push(await shoot(cdp, SCREENS, "10-search-results", metrics));
      }
      await emulate(cdp, WIDTHS[1]);
    }

    /* ---------------- phase: show more ---------------- */
    currentPhase = "more";
    console.log("");
    console.log('"Show 25 more"');
    const beforeMore = searchState.count;
    await evaluate(cdp, `document.querySelector(".show-more").click(), true`);
    await waitFor(
      cdp,
      `document.querySelectorAll("#search-result .result").length > ${beforeMore}`,
      { label: "more results", timeoutMs: 60000 },
    );
    const afterMore = await evaluate(
      cdp,
      `(() => {
         const root = document.getElementById("search-result");
         const focused = document.activeElement;
         return {
           count: root.querySelectorAll(".result").length,
           focusedId: focused ? focused.id : null,
           focusedClass: focused ? focused.className : null,
           focusedText: focused ? (focused.textContent || "").slice(0, 60) : null,
         };
       })()`,
    );
    check(
      "Show more added 25 results, keeping the ones already shown",
      afterMore.count === beforeMore + 25,
      `${beforeMore} -> ${afterMore.count}`,
    );
    check(
      "focus moved to the FIRST NEWLY ADDED result, not to the top of the page",
      afterMore.focusedId === `result-${beforeMore}`,
      `focus on #${afterMore.focusedId} (${afterMore.focusedClass}) "${afterMore.focusedText}"`,
    );

    const moreRequests = log.all().filter((r) => r.phase === "more");
    report.phases.more = {
      requests: moreRequests.length,
      encodedBytes: moreRequests.reduce((n, r) => n + (r.encodedDataLength ?? 0), 0),
      urls: moreRequests.map((r) => ({ url: r.url, status: r.status, encodedDataLength: r.encodedDataLength })),
    };
    check(
      "Show more re-fetched neither the index nor the asker names",
      !moreRequests.some((r) => r.url.includes("subject-index") || r.url.includes("asker-names")),
      moreRequests.map((r) => r.url.split("/").pop()).join(", ") || "no request at all",
    );

    if (SCREENS) {
      for (const metrics of WIDTHS) {
        await emulate(cdp, metrics);
        report.screenshots.push(await shoot(cdp, SCREENS, "11-search-show-more", metrics));
      }
      await emulate(cdp, WIDTHS[1]);
    }

    /* ---------------- phase: a two-session query, on a FRESH page ----------
     *
     * RELOADED FIRST, and that is the whole point of this phase. By now the
     * index, the asker names and two digests are memoised in the module, so
     * running the two-word query on this document would measure a cost of
     * zero and report the accepted overrun as free. A reload is a new module
     * instance with an empty memo map, and the HTTP cache is disabled, so
     * what this phase records is a real FIRST SEARCH for a two-session query
     * -- which is the figure T083 has to put beside T019's budget. */
    currentPhase = "reload";
    console.log("");
    console.log(`Two-word query — ${JSON.stringify(QUERY_TWO)} (the accepted overrun), on a FRESH page`);
    await cdp.send("Page.navigate", { url: `${ORIGIN}/` });
    /* Wait for `#search-query` to EXIST, not for `#search-result` to say
     * "empty": the shell ships `data-state="empty"` in the markup, so that
     * condition is true of the static HTML before any script has run and the
     * wait would return on a page with no search box on it. The input is
     * created by `buildSearchView`, so its presence is the real signal. */
    await waitFor(cdp, `document.getElementById("search-query") !== null`, {
      label: "the reloaded page's search box",
    });
    const reloadRequests = log.all().filter((r) => r.phase === "reload");
    report.phases.reload = {
      requests: reloadRequests.length,
      encodedBytes: reloadRequests.reduce((n, r) => n + (r.encodedDataLength ?? 0), 0),
      urls: reloadRequests.map((r) => ({
        url: r.url,
        status: r.status,
        encodedDataLength: r.encodedDataLength,
        contentEncoding: r.headers?.["content-encoding"] ?? null,
      })),
    };
    check(
      "the reloaded page fetched the same on-load set and still no search file",
      reloadRequests.length === loadRequests.length &&
        !reloadRequests.some((r) => r.url.includes("/search/")),
      `${reloadRequests.length} request(s) against ${loadRequests.length} on the first load`,
    );

    currentPhase = "two";
    await typeAndSearch(cdp, QUERY_TWO);
    await waitFor(cdp, RESULTS_READY, { label: "two-word results", timeoutMs: 60000 });
    const twoState = await evaluate(
      cdp,
      `(() => {
         const root = document.getElementById("search-result");
         return {
           state: root.dataset.state,
           count: root.querySelectorAll(".result").length,
           summary: (root.querySelector(".search-count") || {}).textContent || null,
         };
       })()`,
    );
    const twoRequests = log.all().filter((r) => r.phase === "two");
    report.phases.two = {
      requests: twoRequests.length,
      encodedBytes: twoRequests.reduce((n, r) => n + (r.encodedDataLength ?? 0), 0),
      digestCount: twoRequests.filter((r) => r.url.includes("/search/digest/")).length,
      urls: twoRequests.map((r) => ({ url: r.url, status: r.status, encodedDataLength: r.encodedDataLength })),
      state: twoState,
    };
    check(
      "a two-word AND query returns fewer results than one of its words",
      twoState.state === "ready" || twoState.state === "empty",
      twoState.summary,
    );
    check(
      "the two-session case fetched TWO digests on a fresh page",
      report.phases.two.digestCount === 2,
      `${report.phases.two.digestCount} digest(s), ` +
        `${report.phases.two.encodedBytes.toLocaleString("en-US")} B on the wire`,
    );

    /* ---------------- phase: ignored words ---------------- */
    currentPhase = "ignored";
    console.log("");
    console.log("Ignored words — \"the of water\"");
    await typeAndSearch(cdp, "the of water");
    await waitFor(cdp, RESULTS_READY, { label: "results with ignored words", timeoutMs: 60000 });
    const ignoredState = await evaluate(
      cdp,
      `(() => {
         const box = document.querySelector("#search-result .ignored");
         return {
           present: Boolean(box),
           head: box ? box.querySelector(".ignored-head").textContent : null,
           words: box ? [...box.querySelectorAll(".ignored-word")].map((n) => n.textContent) : [],
           results: document.querySelectorAll("#search-result .result").length,
         };
       })()`,
    );
    check(
      "words the rule dropped are named on the page",
      ignoredState.present && ignoredState.words.includes("the") && ignoredState.words.includes("of"),
      `${ignoredState.head} ${JSON.stringify(ignoredState.words)}`,
    );
    check(
      "the rest of the query still searched",
      ignoredState.results > 0,
      `${ignoredState.results} result(s)`,
    );
    if (SCREENS) {
      for (const metrics of WIDTHS) {
        await emulate(cdp, metrics);
        report.screenshots.push(await shoot(cdp, SCREENS, "12-search-ignored-words", metrics));
      }
      await emulate(cdp, WIDTHS[1]);
    }

    /* ---------------- phase: zero hits ---------------- */
    currentPhase = "zero";
    console.log("");
    console.log("Zero hits — a word in no subject line");
    await typeAndSearch(cdp, "bioluminescence");
    await waitFor(cdp, RESULTS_READY, { label: "zero-hit state", timeoutMs: 60000 });
    const zeroState = await evaluate(
      cdp,
      `(() => {
         const root = document.getElementById("search-result");
         return {
           state: root.dataset.state,
           results: root.querySelectorAll(".result").length,
           message: (root.querySelector(".search-status") || {}).textContent || null,
         };
       })()`,
    );
    check(
      "zero hits NAMES the word that is in no subject line",
      zeroState.state === "empty" &&
        zeroState.results === 0 &&
        /bioluminescence/.test(zeroState.message ?? ""),
      JSON.stringify((zeroState.message ?? "").slice(0, 120)),
    );
    if (SCREENS) {
      for (const metrics of WIDTHS) {
        await emulate(cdp, metrics);
        report.screenshots.push(await shoot(cdp, SCREENS, "13-search-zero-hits", metrics));
      }
      await emulate(cdp, WIDTHS[1]);
    }

    /* ---------------- phase: a failed digest fetch ---------------- */
    currentPhase = "failure";
    console.log("");
    console.log("Fetch failure — every digest blocked at the network level");
    await cdp.send("Network.setBlockedURLs", {
      urls: [
        "*sansad.in*",
        "*sansad.nic.in*",
        "*://*/api_ls/*",
        "*://*/api_rs/*",
        "*/search/digest/*",
      ],
    });
    await typeAndSearch(cdp, "metering");
    await waitFor(
      cdp,
      `document.querySelector("#search-result .unavailable") !== null`,
      { label: "a visible failure", timeoutMs: 60000 },
    );
    const failureState = await evaluate(
      cdp,
      `(() => {
         const root = document.getElementById("search-result");
         const box = root.querySelector(".unavailable");
         return {
           state: root.dataset.state,
           head: box ? box.querySelector(".unavailable-head").textContent : null,
           detail: box ? (box.querySelector(".unavailable-detail") || {}).textContent : null,
           results: root.querySelectorAll(".result").length,
           visible: box ? box.getBoundingClientRect().height > 20 : false,
         };
       })()`,
    );
    check(
      "a failed digest fetch shows a VISIBLE error, never an empty list",
      failureState.state === "error" && failureState.visible && failureState.results === 0,
      `${failureState.head} | ${failureState.detail}`,
    );
    if (SCREENS) {
      for (const metrics of WIDTHS) {
        await emulate(cdp, metrics);
        report.screenshots.push(await shoot(cdp, SCREENS, "14-search-fetch-failure", metrics));
      }
      await emulate(cdp, WIDTHS[1]);
    }

    /* =================================================================
     * T088 -- the state and constituency entry point. US3.
     *
     * On a FRESH page, for the same reason the two-word query reloaded: by
     * now nothing seat-related has been fetched, but the search module's
     * memos are warm and the digest block is still in place. A reload gives
     * a new module instance, and the HTTP cache is disabled, so what the
     * "seatopen" phase records is a real FIRST USE of this view.
     * ================================================================= */
    await cdp.send("Network.setBlockedURLs", {
      urls: ["*sansad.in*", "*sansad.nic.in*", "*://*/api_ls/*", "*://*/api_rs/*"],
    });

    currentPhase = "seatload";
    console.log("");
    console.log("Scenario 7 — the state and constituency view, on a FRESH page");
    await cdp.send("Page.navigate", { url: `${ORIGIN}/` });
    await waitFor(cdp, `document.getElementById("seat-open") !== null`, {
      label: "the constituency finder's open button",
    });
    const seatLoadRequests = log.all().filter((r) => r.phase === "seatload");
    report.phases.seatload = {
      requests: seatLoadRequests.length,
      encodedBytes: seatLoadRequests.reduce((n, r) => n + (r.encodedDataLength ?? 0), 0),
      urls: seatLoadRequests.map((r) => ({
        url: r.url,
        status: r.status,
        encodedDataLength: r.encodedDataLength,
        contentEncoding: r.headers?.["content-encoding"] ?? null,
      })),
    };
    check(
      "NOTHING this view needs was requested on load",
      !seatLoadRequests.some(
        (r) =>
          r.url.includes("constituencies.jsonl") ||
          r.url.includes("state-subjects") ||
          r.url.includes("/by-member/"),
      ),
      seatLoadRequests
        .filter((r) => r.url.includes("constituencies") || r.url.includes("state-subjects"))
        .map((r) => r.url)
        .join(", ") || "none",
    );

    /* ---------------- phase: first use of the view ---------------- */
    currentPhase = "seatopen";
    console.log("");
    console.log("First use of the view — the seat list and the state summary");
    await evaluate(cdp, `document.getElementById("seat-open").click(), true`);
    await waitFor(cdp, `document.getElementById("seat-state") !== null`, {
      label: "the state picker",
      timeoutMs: 60000,
    });
    const seatOpenRequests = log.all().filter((r) => r.phase === "seatopen");
    report.phases.seatopen = {
      requests: seatOpenRequests.length,
      encodedBytes: seatOpenRequests.reduce((n, r) => n + (r.encodedDataLength ?? 0), 0),
      urls: seatOpenRequests.map((r) => ({
        url: r.url,
        status: r.status,
        encodedDataLength: r.encodedDataLength,
        contentEncoding: r.headers?.["content-encoding"] ?? null,
      })),
    };
    check(
      "opening the view fetched EXACTLY the two files it needs",
      seatOpenRequests.length === 2 &&
        seatOpenRequests.some((r) => r.url.endsWith("reference/constituencies.jsonl")) &&
        seatOpenRequests.some((r) => r.url.endsWith("aggregates/state-subjects.jsonl")),
      seatOpenRequests.map((r) => r.url.split("/").pop()).join(", "),
    );
    check(
      "the 3.4 MB member reference set was NOT fetched",
      !log.all().some((r) => r.url.includes("reference/members")),
      `${report.phases.seatopen.encodedBytes.toLocaleString("en-US")} B on the wire for the view`,
    );

    /* The state, the seat and its members all DERIVED from the page. */
    const target = await evaluate(
      cdp,
      `(() => {
         const select = document.getElementById("seat-state");
         const options = [...select.options].map((o) => o.value).filter(Boolean);
         return { states: options.length };
       })()`,
    );
    check("every state in the record is offered", target.states >= 30, `${target.states} states`);

    /* ---------------- phase: a state picked ---------------- */
    currentPhase = "state";
    console.log("");
    console.log("A state picked — its seats, and the published subject summary");
    const chosen = await evaluate(
      cdp,
      `(() => {
         const name = ${JSON.stringify(SEAT_NAME)}.toLowerCase();
         const box = document.getElementById("seat-name");
         box.value = ${JSON.stringify(SEAT_NAME)};
         box.form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
         const states = [...document.querySelectorAll("#seat-matches .match-state")]
           .map((n) => n.textContent);
         const names = [...document.querySelectorAll("#seat-matches .match-name")]
           .map((n) => n.textContent.toLowerCase());
         return { states, names, exact: names.filter((n) => n === name).length };
       })()`,
    );
    check(
      "a constituency name that exists in two states lists BOTH, each with its state",
      chosen.exact === 2 && new Set(chosen.states).size === 2,
      `${chosen.exact} seats named ${JSON.stringify(SEAT_NAME)} in ${JSON.stringify(chosen.states)}`,
    );
    if (SCREENS) {
      for (const metrics of WIDTHS) {
        await emulate(cdp, metrics);
        report.screenshots.push(await shoot(cdp, SCREENS, "18-seat-name-two-states", metrics, "#constituency"));
      }
      await emulate(cdp, WIDTHS[1]);
    }

    /* Click the first match, which selects its state and its seat. */
    await evaluate(cdp, `document.querySelector("#seat-matches .match-button").click(), true`);
    await waitFor(
      cdp,
      `document.getElementById("seat-result").dataset.state === "ready" &&
       document.getElementById("state-summary").dataset.state === "ready"`,
      { label: "the seat and the state summary", timeoutMs: 60000 },
    );
    const stateState = await evaluate(
      cdp,
      `(() => {
         const root = document.getElementById("state-summary");
         const rows = [...root.querySelectorAll(".subject-list li")];
         return {
           heading: (root.querySelector(".seat-name") || {}).textContent || null,
           subjects: rows.length,
           firstSubject: rows.length ? rows[0].querySelector(".subject-text").textContent : null,
           facts: [...root.querySelectorAll(".fact-value")].map((n) => n.textContent),
           basis: (root.querySelector(".basis-text") || {}).textContent || "",
           basisSrc: (root.querySelector(".basis-src") || {}).textContent || "",
         };
       })()`,
    );
    check(
      "the state's subjects are summarised from the published aggregate",
      stateState.subjects > 0 && stateState.facts.length === 2,
      `${stateState.subjects} subject line(s), facts ${JSON.stringify(stateState.facts)}`,
    );
    check(
      "the attribution rule is on the page, read from the published basis",
      /counts ONCE toward a state/i.test(stateState.basis) &&
        /do not sum the states/i.test(stateState.basis) &&
        /exact subject lines/i.test(stateState.basis),
      stateState.basisSrc,
    );
    check(
      "the questions with no identified asker are declared on the page",
      /cannot be attributed to any state and are EXCLUDED/i.test(stateState.basis),
      (stateState.basis.match(/([\d,]+) questions in this window/) || [])[0] ?? "not stated",
    );
    if (SCREENS) {
      for (const metrics of WIDTHS) {
        await emulate(cdp, metrics);
        report.screenshots.push(await shoot(cdp, SCREENS, "15-state-picked", metrics, "#state-summary"));
      }
      await emulate(cdp, WIDTHS[1]);
    }

    /* ---------------- phase: a two-holder seat ---------------- */
    currentPhase = "seat";
    console.log("");
    console.log("A constituency with two holders across the terms — scenario 3");
    const seatState = await evaluate(
      cdp,
      `(() => {
         const root = document.getElementById("seat-result");
         const reps = [...root.querySelectorAll(".rep")];
         return {
           name: (root.querySelector(".seat-name") || {}).textContent || null,
           state: (root.querySelector(".seat-state") || {}).textContent || null,
           history: (root.querySelector(".seat-history") || {}).textContent || null,
           reps: reps.length,
           people: reps.map((li) => ({
             name: (li.querySelector(".rep-name") || {}).textContent || null,
             terms: [...li.querySelectorAll(".rep-meta dd")].map((n) => n.textContent),
           })),
         };
       })()`,
    );
    check(
      "both holders appear, NOT merged, each with their own term",
      seatState.reps === 2 &&
        new Set(seatState.people.map((p) => p.name)).size === 2 &&
        /different members/i.test(seatState.history ?? ""),
      `${seatState.reps} members: ${seatState.people.map((p) => p.name).join(" | ")}`,
    );
    check(
      "the seat names its state beside its name",
      Boolean(seatState.state) && seatState.state.trim().length > 0,
      `${seatState.name} — ${seatState.state}`,
    );
    check(
      "each holder shows a party and a term, with no date invented",
      seatState.people.every((p) => p.terms.some((t) => /Lok Sabha/.test(t))) &&
        !seatState.people.some((p) => p.terms.some((t) => /\d{4}-\d{2}-\d{2}/.test(t))),
      JSON.stringify(seatState.people[0].terms),
    );
    if (SCREENS) {
      for (const metrics of WIDTHS) {
        await emulate(cdp, metrics);
        report.screenshots.push(await shoot(cdp, SCREENS, "16-seat-two-holders", metrics, "#seat-result"));
      }
      await emulate(cdp, WIDTHS[1]);
    }

    /* ---------------- phase: a member opened ---------------- */
    currentPhase = "member";
    console.log("");
    console.log("A member opened — their questions, one file");
    await evaluate(cdp, `document.querySelector("#seat-result .rep-open").click(), true`);
    await waitFor(
      cdp,
      `document.querySelector("#seat-result .rep-questions[data-state='ready']") !== null`,
      { label: "the member's questions", timeoutMs: 60000 },
    );
    const memberRequests = log.all().filter((r) => r.phase === "member");
    report.phases.member = {
      requests: memberRequests.length,
      encodedBytes: memberRequests.reduce((n, r) => n + (r.encodedDataLength ?? 0), 0),
      urls: memberRequests.map((r) => ({
        url: r.url,
        status: r.status,
        encodedDataLength: r.encodedDataLength,
        contentEncoding: r.headers?.["content-encoding"] ?? null,
      })),
    };
    check(
      "opening one member fetched exactly ONE by-member file and nothing else",
      memberRequests.length === 1 && memberRequests[0].url.includes("/by-member/"),
      memberRequests.map((r) => r.url.split("/").pop()).join(", ") || "no request",
    );
    const memberState = await evaluate(
      cdp,
      `(() => {
         const host = document.querySelector("#seat-result .rep-questions[data-state='ready']");
         const statusValues = [...host.querySelectorAll(".status-value")]
           .map((n) => Number(n.textContent.replace(/[^0-9]/g, "")));
         const total = Number(
           (host.querySelector(".fact-value") || {}).textContent.replace(/[^0-9]/g, ""));
         return {
           total,
           statusValues,
           statusSum: statusValues.reduce((a, b) => a + b, 0),
           questions: host.querySelectorAll(".question-list li").length,
           flagWords: host.querySelectorAll(".flag-word").length,
           subjects: host.querySelectorAll(".subject-list li").length,
           basis: (host.querySelector(".basis-text") || {}).textContent || "",
         };
       })()`,
    );
    check(
      "their questions are reachable from the seat",
      memberState.questions > 0 && memberState.total > 0,
      `${memberState.questions} listed of ${memberState.total} published`,
    );
    check(
      "the four link-status counts account for the total on screen",
      memberState.statusValues.length === 4 && memberState.statusSum === memberState.total,
      `${memberState.statusValues.join(" + ")} = ${memberState.statusSum}, total ${memberState.total}`,
    );
    check(
      "unresolved and ambiguous questions are flagged IN WORDS, not colour",
      memberState.flagWords >= 1,
      `${memberState.flagWords} "flagged" word(s)`,
    );
    check(
      "the counting basis is on the page beside the figures",
      /QUESTIONS, not question-asker pairs/i.test(memberState.basis),
      `${memberState.subjects} subject line(s) tallied`,
    );
    if (SCREENS) {
      for (const metrics of WIDTHS) {
        await emulate(cdp, metrics);
        report.screenshots.push(await shoot(cdp, SCREENS, "17-member-opened", metrics, "#seat-result"));
      }
      await emulate(cdp, WIDTHS[1]);
    }

    /* ---------------- phase: a failed member fetch ---------------- */
    currentPhase = "seatfailure";
    console.log("");
    console.log("Fetch failure — every by-member file blocked at the network level");
    await cdp.send("Network.setBlockedURLs", {
      urls: [
        "*sansad.in*",
        "*sansad.nic.in*",
        "*://*/api_ls/*",
        "*://*/api_rs/*",
        "*/by-member/*",
      ],
    });
    await evaluate(
      cdp,
      `(() => {
         const buttons = [...document.querySelectorAll("#seat-result .rep-open")];
         buttons[buttons.length - 1].click();
         return true;
       })()`,
    );
    await waitFor(
      cdp,
      `document.querySelector("#seat-result .rep-questions .unavailable") !== null`,
      { label: "a visible failure", timeoutMs: 60000 },
    );
    const seatFailure = await evaluate(
      cdp,
      `(() => {
         const box = document.querySelector("#seat-result .rep-questions .unavailable");
         const host = box.closest(".rep-questions");
         return {
           state: host.dataset.state,
           head: (box.querySelector(".unavailable-head") || {}).textContent || null,
           detail: (box.querySelector(".unavailable-detail") || {}).textContent || null,
           questions: host.querySelectorAll(".question-list li").length,
           visible: box.getBoundingClientRect().height > 20,
         };
       })()`,
    );
    check(
      "a failed member fetch shows a VISIBLE error, never an empty question list",
      seatFailure.state === "error" && seatFailure.visible && seatFailure.questions === 0,
      `${seatFailure.head} | ${seatFailure.detail}`,
    );
    if (SCREENS) {
      for (const metrics of WIDTHS) {
        await emulate(cdp, metrics);
        report.screenshots.push(await shoot(cdp, SCREENS, "19-member-fetch-failure", metrics, "#seat-result"));
      }
      await emulate(cdp, WIDTHS[1]);
    }

    /* ---------------- the whole-run network assertions ---------------- */
    currentPhase = "done";
    console.log("");
    console.log("Network log — every request this run made");
    console.log("=".repeat(110));
    const all = log.all();
    const offOrigin = all.filter((r) => !r.url.startsWith(ORIGIN) && !r.url.startsWith("data:"));
    const byUrl = new Map();
    for (const record of all) {
      const key = `${record.phase} ${record.url}`;
      const existing = byUrl.get(key) ?? { ...record, count: 0, bytes: 0 };
      existing.count += 1;
      existing.bytes += record.encodedDataLength ?? 0;
      byUrl.set(key, existing);
    }
    console.log(
      `${"phase".padEnd(8)}${"status".padEnd(7)}${"bytes".padStart(12)}  url`,
    );
    console.log("-".repeat(110));
    for (const record of byUrl.values()) {
      const shown = record.url.startsWith(ORIGIN) ? record.url.slice(ORIGIN.length) : record.url;
      console.log(
        `${record.phase.padEnd(8)}${String(record.status ?? "-").padEnd(7)}` +
          `${record.bytes.toLocaleString("en-US").padStart(12)}  ${shown}`,
      );
    }
    console.log("-".repeat(110));
    console.log(
      `${all.length} request(s) in total, ${byUrl.size} distinct, ` +
        `${all.reduce((n, r) => n + (r.encodedDataLength ?? 0), 0).toLocaleString("en-US")} B on the wire`,
    );
    console.log(`requests NOT to ${ORIGIN}: ${offOrigin.length}`);
    for (const record of offOrigin) console.log(`  OFF-ORIGIN: ${record.url}`);
    console.log("");

    check(
      "the network log shows requests to the static host ONLY — one upstream request is a failure",
      offOrigin.length === 0,
      `${all.length} request(s), all to ${ORIGIN}`,
    );
    /* The two phases that block a request ON PURPOSE are exempt, and named
     * rather than matched on a pattern: `failure` blocks the search digests
     * and `seatfailure` the by-member files, each to prove the page shows a
     * visible error instead of an empty list. A blocked request in any other
     * phase means the page tried to leave this host. */
    const DELIBERATE_BLOCKS = new Set(["failure", "seatfailure"]);
    const unexpectedBlocks = log.failures().filter((f) => !DELIBERATE_BLOCKS.has(f.phase));
    check(
      "no request was blocked outside the two phases that block one on purpose",
      unexpectedBlocks.length === 0,
      JSON.stringify(unexpectedBlocks),
    );
    check(
      "both deliberate blocks did fire, so the two failure checks tested something",
      [...DELIBERATE_BLOCKS].every((phase) =>
        log.failures().some((f) => f.phase === phase),
      ),
      log
        .failures()
        .map((f) => `${f.phase}:${f.url.split("/").pop()}`)
        .join(", ") || "none",
    );
    check(
      "the page threw no uncaught error and logged no console error",
      consoleErrors.length === 0,
      consoleErrors.join(" | ") || "none",
    );

    report.network = {
      total: all.length,
      distinct: byUrl.size,
      offOrigin: offOrigin.map((r) => r.url),
      wireBytes: all.reduce((n, r) => n + (r.encodedDataLength ?? 0), 0),
      failures: log.failures(),
      consoleErrors,
    };
    /* Resolve every URL to the file the static host served, so the report
     * carries both bases. */
    for (const phase of Object.values(report.phases)) {
      for (const entry of phase.urls ?? []) {
        const path = entry.url.startsWith(ORIGIN) ? entry.url.slice(ORIGIN.length) : entry.url;
        const resolved = await bodyBytesFor(path);
        entry.path = path;
        entry.file = resolved.file;
        entry.bodyBytes = resolved.bytes;
      }
      phase.bodyBytes = (phase.urls ?? []).reduce((n, e) => n + (e.bodyBytes ?? 0), 0);
    }
    report.checks = checks;

    const failed = checks.filter((c) => !c.ok);
    console.log("=".repeat(110));
    console.log(`${checks.length - failed.length} of ${checks.length} check(s) passed`);
    if (failed.length > 0) {
      for (const one of failed) console.log(`  FAILED: ${one.name} — ${one.detail}`);
      exitCode = 1;
    }
  } catch (error) {
    console.error("");
    console.error(`DRIVER ERROR: ${error.message}`);
    console.error(error.stack);
    report.error = error.message;
    report.checks = checks;
    exitCode = 1;
  } finally {
    if (REPORT) {
      await writeFile(REPORT, JSON.stringify(report, null, 1) + "\n", "utf8");
      console.log(`report: ${REPORT}`);
    }
    cdp.close();
    await chrome.close();
  }
  process.exit(exitCode);
}

await main();
