/* The fetch layer. T076.
 *
 * EVERY request this page makes goes through `requestUrl` below. That is not
 * tidiness -- it is the only place the same-origin rule can be enforced, and
 * the rule is load-bearing rather than cautious:
 *
 *   `spike/route-capture.md` T005 verified first-hand that the upstream sends
 *   NO `Access-Control-Allow-Origin` header. A browser is therefore refused
 *   cross-origin reads of it. The page's entire viability rests on reading
 *   this project's OWN published files from its own host, and a request that
 *   wandered off-origin would not degrade -- it would fail, silently, in a
 *   visitor's browser where nobody is watching.
 *
 * So `requestUrl` REFUSES rather than attempts: it throws `CrossOriginRefused`
 * before calling fetch at all. `tests/page/fetch-layer.test.mjs` proves both
 * halves -- that it throws, and that the injected fetch was never reached.
 *
 * Paths are RELATIVE (`./data/published/...`, owner decision 2026-10-10).
 * Root-relative paths are refused too: GitHub Pages serves a project site
 * under `/<repo>/`, so `/data/published/x` resolves to the user site root and
 * 404s. A relative path works both there and under `make serve-local`.
 *
 * Nothing here is imported from anywhere but this repository: no CDN, no web
 * font, no analytics, no module specifier that is not a relative path.
 */

/** Published dataset root, relative to the page. Owner decision 2026-10-10. */
export const PUBLISHED_BASE = "./data/published/";

/** Raised instead of making a request that would leave this origin. */
export class CrossOriginRefused extends Error {
  constructor(message) {
    super(message);
    this.name = "CrossOriginRefused";
  }
}

/** Raised when a published file is missing or unreadable. */
export class PublishedFileUnavailable extends Error {
  constructor(message, { status } = {}) {
    super(message);
    this.name = "PublishedFileUnavailable";
    this.status = status ?? null;
  }
}

function pageHref(options) {
  if (options.pageUrl) return options.pageUrl;
  if (typeof location !== "undefined" && location.href) return location.href;
  throw new TypeError("no page URL: pass `pageUrl` when there is no `location`");
}

function pageOrigin(options) {
  if (options.origin) return options.origin;
  return new URL(pageHref(options)).origin;
}

function fetchFn(options) {
  if (options.fetchImpl) return options.fetchImpl;
  if (typeof fetch === "function") return fetch;
  throw new TypeError("no fetch available: pass `fetchImpl`");
}

/**
 * Resolve `target` against the page and refuse it if it leaves this origin.
 *
 * Exported separately from the request so a test can assert the refusal
 * without a network stack at all.
 */
export function assertSameOrigin(target, options = {}) {
  const origin = pageOrigin(options);
  let url;
  try {
    url = new URL(target, pageHref(options));
  } catch (cause) {
    throw new CrossOriginRefused(`refused: not a resolvable URL: ${String(target)}`, {
      cause,
    });
  }
  if (url.origin !== origin) {
    // The message names the two origins and nothing else. A thrown message can
    // end up in a console a visitor pastes somewhere.
    throw new CrossOriginRefused(
      `refused: ${url.origin} is not this page's origin (${origin}). ` +
        "This page reads only its own published files.",
    );
  }
  if (url.protocol !== "http:" && url.protocol !== "https:" && url.protocol !== "file:") {
    throw new CrossOriginRefused(`refused: unsupported scheme ${url.protocol}`);
  }
  return url;
}

/**
 * THE one function every request goes through.
 *
 * Returns the `Response`. Callers above parse it; nothing else calls fetch.
 */
export async function requestUrl(target, options = {}) {
  const url = assertSameOrigin(target, options);
  const impl = fetchFn(options);
  const response = await impl(url.href, {
    // No credentials, no cookies: the dataset is public static files and the
    // page has no session of any kind.
    credentials: "omit",
    // `same-origin` makes the browser itself refuse a cross-origin redirect
    // rather than following one past the check above.
    mode: "same-origin",
    redirect: "error",
    headers: { Accept: "text/plain, application/json" },
  });
  if (!response || !response.ok) {
    throw new PublishedFileUnavailable(
      `could not read ${url.pathname}: HTTP ${response ? response.status : "no response"}`,
      { status: response ? response.status : null },
    );
  }
  return response;
}

/** Build a published-file URL, refusing anything that escapes the base. */
export function publishedPath(relativePath) {
  if (typeof relativePath !== "string" || relativePath.length === 0) {
    throw new TypeError("publishedPath needs a non-empty string");
  }
  if (relativePath.startsWith("/")) {
    throw new CrossOriginRefused(
      "refused: root-relative paths break a GitHub Pages project site; " +
        "published paths are relative",
    );
  }
  if (relativePath.includes("..")) {
    throw new CrossOriginRefused("refused: a published path may not contain `..`");
  }
  if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(relativePath)) {
    throw new CrossOriginRefused(`refused: ${relativePath} is not a relative path`);
  }
  return PUBLISHED_BASE + relativePath;
}

/** Fetch one published file as text. */
export async function fetchText(relativePath, options = {}) {
  const response = await requestUrl(publishedPath(relativePath), options);
  return response.text();
}

/** Fetch one published `.json` file. */
export async function fetchJson(relativePath, options = {}) {
  return JSON.parse(await fetchText(relativePath, options));
}

/** Fetch one published `.jsonl` file as an array of records. */
export async function fetchNdjson(relativePath, options = {}) {
  const text = await fetchText(relativePath, options);
  const rows = [];
  for (const line of text.split("\n")) {
    const trimmed = line.trim();
    if (trimmed.length > 0) rows.push(JSON.parse(trimmed));
  }
  return rows;
}

/* ------------------------------------------------------------------------ */
/* The named published files. Spelled once, here.                           */
/* ------------------------------------------------------------------------ */

/* Exactly what this page can request -- nothing dead, nothing speculative.
 * T078/T079/T080 add their own entries when they are built; an unused entry
 * here would overstate the page's request surface, and that surface is the
 * thing T082 asserts against a real network log. */
export const PUBLISHED_FILES = Object.freeze({
  manifest: "manifest.json",
  coverage: "coverage.jsonl",
  countingBasis: "aggregates/counting-basis.jsonl",
  sessions: "reference/sessions.jsonl",
  searchIndex: "search/subject-index.json",
});

/** Every URL this page can request, as it would be resolved. For the record,
 * and for `tools/list_page_urls.py` to print without running a browser. */
export function requestableUrls() {
  return Object.values(PUBLISHED_FILES).map(publishedPath);
}

export const fetchManifest = (o) => fetchJson(PUBLISHED_FILES.manifest, o);
export const fetchCoverage = (o) => fetchNdjson(PUBLISHED_FILES.coverage, o);
export const fetchCountingBasis = (o) => fetchNdjson(PUBLISHED_FILES.countingBasis, o);
export const fetchSessions = (o) => fetchNdjson(PUBLISHED_FILES.sessions, o);

/* ------------------------------------------------------------------------ */
/* The search index, fetched LAZILY -- on the first search only.            */
/* ------------------------------------------------------------------------ */

/* T072 measured the index at 2,484,758 B (2.37 MiB) -- 1.0% of the dataset,
 * but about 73% of the bytes a first page load would cost if it were fetched
 * eagerly. A visitor who never searches must not pay for it, so it is not
 * requested until `loadSearchIndex` is called, and `app.js` calls it from the
 * search handler and from nowhere else.
 *
 * The promise is memoised rather than the value: two searches started before
 * the first resolves must share ONE request, not race two.
 */
let searchIndexPromise = null;

export function loadSearchIndex(options = {}) {
  if (searchIndexPromise === null) {
    searchIndexPromise = fetchJson(PUBLISHED_FILES.searchIndex, options).catch((error) => {
      // A failed load must not poison every later attempt.
      searchIndexPromise = null;
      throw error;
    });
  }
  return searchIndexPromise;
}

/** Whether the index has been requested yet. For tests and for the page's own
 * "not loaded" state; never used to decide whether to fetch. */
export function searchIndexRequested() {
  return searchIndexPromise !== null;
}

/** Test seam only: forget that the index was requested. */
export function resetSearchIndex() {
  searchIndexPromise = null;
}
