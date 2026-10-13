/* Indian Sansad — the page shell and its router. T130, T136.
 *
 * An ES module, loaded directly by index.html with no build step. Everything
 * it renders is read at runtime from this project's own published files; no
 * figure, licence line or basis sentence is typed into the page.
 *
 * WHAT THIS FILE IS, after feature 002. It was 2,332 lines holding every view
 * on the page. It is now the shell: the coverage statement a visitor lands on,
 * the licence footer, and the router that mounts one view at a time. The three
 * other view families moved to `web/views/`, and everything more than one of
 * them needs moved down to `web/lib/shared.js`.
 *
 * Why the shared layer went DOWN to `lib/` rather than staying here: the views
 * are loaded with `import()`, so if they imported their helpers back out of
 * this module the graph would be `app -> view -> app` — a cycle through a
 * dynamic import, where which bindings are initialised depends on evaluation
 * order rather than on anything written down. With the helpers in `lib/` the
 * graph is acyclic and nothing in a view knows this file exists.
 *
 * WHAT THE SHELL MAY FETCH. Four files, and no others: the coverage
 * statement, the session reference, the counting basis and the manifest —
 * 4,540 B at gzip -6 between them. Every other published file belongs to a
 * view and is read when a reader opens it (FR-126, FR-127, FR-151). `boot()`
 * asserts that below, and throws rather than warns.
 *
 * Rendering rule: nothing from a published file ever reaches `innerHTML`.
 * Every value goes in through `textContent`. The records are this project's
 * own, but they are built from an upstream payload nobody controls, and a page
 * that interpolated them into markup would be one upstream change away from
 * executing it.
 */

import {
  ZERO_SITTING_DAYS_FLAG,
  coveredRows,
  housesClaim,
  housesNotCovered,
  longSessionLabel,
  sessionRows,
} from "./lib/coverage.js";
import {
  compositionAssetsRequested,
  fetchCountingBasis,
  fetchCoverage,
  fetchManifest,
  fetchSessions,
  ministryAssetsRequested,
  searchAssetsRequested,
  seatAssetsRequested,
} from "./lib/fetch.js";
import { NOT_STATED, count, isMissing, isoDate, percent, stated } from "./lib/format.js";
import { renderDisclosure } from "./lib/licence.js";
import {
  describe,
  el,
  fact,
  list,
  renderUnavailable,
  replaceChildren,
  views,
} from "./lib/shared.js";

function renderCoverage(container, { coverage, sessions, basis }) {
  // Whichever Houses carry questions, largest first. No House is named here:
  // naming one would decide whose figures appear, and that is the drift the
  // derived claim exists to remove.
  const covered = coveredRows(coverage);
  if (covered.length === 0) {
    renderUnavailable(
      container,
      "The coverage statement carries no House with any published question.",
    );
    return;
  }
  const lok = covered[0];

  const frag = document.createDocumentFragment();

  /* --- Houses. The one claim the page must make loudly (FR-013).
         DERIVED from which rows actually carry questions, never typed: if a
         Rajya Sabha route is ever found, this changes by itself rather than
         by someone remembering to edit a string. ------------------------- */
  const houses = el("div", "houses");
  houses.append(el("p", "houses-value", housesClaim(coverage)));
  const absent = housesNotCovered(coverage);
  if (absent.length > 0) {
    houses.append(
      el(
        "p",
        "houses-note",
        `${absent.map((h) => h.name).join(", ")} is not covered by this dataset.`,
      ),
    );
    for (const row of absent) {
      if (row.reason) houses.append(el("p", "houses-why", `Why: ${row.reason}`));
    }
  }
  frag.append(houses);

  /* --- The figures. ---------------------------------------------------- */
  const grid = el("div", "fact-grid");

  const period = `${isoDate(lok.period_start)} – ${isoDate(lok.period_end)}`;
  grid.append(
    fact(
      "Period covered",
      period,
      `${count(lok.sessions_covered_count)} sessions, listed below`,
    ),
  );

  grid.append(
    fact(
      "Questions published",
      count(lok.total_questions),
      declaredDuplicates(lok),
    ),
  );

  grid.append(
    fact(
      "Asking members identified, automatically",
      percent(lok.resolution_rate_automatic),
      `${count(lok.resolved_automatic)} of ${count(lok.total_questions)} questions. ` +
        `Target ${percent(lok.sc_002_target, { decimals: 0 })} — ` +
        (lok.sc_002_met_on_automatic_rate ? "met." : "NOT met on this figure."),
    ),
  );

  grid.append(
    fact(
      "Identified, including maintainer corrections",
      percent(lok.resolution_rate_including_assertions),
      `${count(lok.resolved_including_assertions)} of ${count(lok.total_questions)}, ` +
        `with ${count(lok.assertions_in_effect)} confirmed corrections ` +
        `(${count(lok.assertions_overriding_an_automatic_match)} of which override an ` +
        `automatic match). Target ${percent(lok.sc_002_target, { decimals: 0 })} — ` +
        (lok.sc_002_met_on_published_rate ? "met." : "NOT met on this figure."),
    ),
  );

  grid.append(
    fact(
      "Ministries",
      count(lok.ministry_ids),
      `from ${count(lok.ministry_names_observed)} distinct names in the source. ` +
        `No confirmed rename mapping covers ${count(lok.ministry_names_without_confirmed_mapping)} ` +
        `of those names, so UP TO ${count(lok.ministry_names_without_confirmed_mapping)} of them ` +
        "could turn out to be renames of one another — the record does not claim that any of " +
        "them is. A rename cannot be detected automatically here, so each one waits on a " +
        "maintainer decision.",
    ),
  );

  grid.append(
    fact(
      "Last rebuilt",
      isoDate(lok.last_refreshed),
      lok.last_known_good === "current"
        ? "This is a current record."
        : `This is the last known good record: ${stated(lok.last_known_good)}.`,
    ),
  );

  frag.append(grid);

  /* --- The counting basis, read at runtime, never retyped. ------------- */
  const questionBasis = basis.find((row) => row.unit === "question");
  if (questionBasis) {
    const box = el("div", "basis");
    box.append(el("p", "basis-head", "How these questions were counted"));
    box.append(el("p", "basis-text", questionBasis.counting_basis));
    box.append(
      el(
        "p",
        "basis-src",
        `Read from aggregates/counting-basis.jsonl, unit "${questionBasis.unit}", ` +
          `basis version ${stated(questionBasis.basis_version)}. This page does not ` +
          "keep its own copy of this text.",
      ),
    );
    frag.append(box);
  }

  /* --- Sessions, ordered by (term, number). ---------------------------- */
  for (const row of covered) {
    frag.append(renderSessions(row, sessions));
  }

  /* --- Known gaps, verbatim. ------------------------------------------- */
  const gaps = Array.isArray(lok.known_gaps) ? lok.known_gaps : [];
  const gapBox = el("section", "gaps");
  gapBox.append(el("h3", null, `Known gaps (${count(gaps.length)})`));
  gapBox.append(
    el(
      "p",
      "gaps-lede",
      "Declared, not implied. Each is published in the record as written here.",
    ),
  );
  if (gaps.length === 0) {
    gapBox.append(el("p", "status", "The record declares no gaps."));
  } else {
    gapBox.append(list("gap-list", gaps, (li, gap) => {
      li.textContent = String(gap);
    }));
  }
  frag.append(gapBox);

  /* --- Merged ministry names. The owner's condition on the fold: every
         merged group is listed, so a merge can never be silent. ---------- */
  const merged = Array.isArray(lok.ministry_name_groups_merged_by_normalisation)
    ? lok.ministry_name_groups_merged_by_normalisation
    : [];
  const mergeBox = el("section", "merges");
  mergeBox.append(el("h3", null, "Ministry names merged as spelling variants"));
  if (merged.length === 0) {
    mergeBox.append(el("p", "status", "No names were merged."));
  } else {
    mergeBox.append(
      el(
        "p",
        "gaps-lede",
        "These groups were treated as one ministry because normalising their " +
          "spelling made them identical. No rename was assumed.",
      ),
    );
    mergeBox.append(list("merge-list", merged, (li, group) => {
      li.textContent = (Array.isArray(group) ? group : [group]).join("  ·  ");
    }));
  }
  frag.append(mergeBox);

  replaceChildren(container, frag);
  container.dataset.state = "ready";
}

function declaredDuplicates(row) {
  const dupes = Array.isArray(row.duplicate_records_declared)
    ? row.duplicate_records_declared
    : [];
  if (dupes.length === 0) return "No duplicate source record was declared.";
  return (
    `${count(dupes.length)} record the source served more than once is kept ` +
    `once, and declared: ${dupes.join(", ")}.`
  );
}

function renderSessions(lok, sessions) {
  const rows = sessionRows(lok, sessions);

  /* (b) Twenty-one rows is a wall in front of the figures that matter, so the
     table is COLLAPSED by default. What stays visible above it: the Houses
     claim, the period, the question count, both identification rates and the
     known-gaps list. A <details> needs no script and is keyboard-operable and
     announced by screen readers for free. */
  const box = el("details", "sessions");
  const summary = el("summary");
  summary.append(el("span", "summary-label", `${count(rows.length)} sessions`));
  summary.append(
    el("span", "summary-note", "ordered by term and session number · dates not stated"),
  );
  box.append(summary);

  const zeroDay = rows.filter((row) => row.zeroSittingDays);
  box.append(
    el(
      "p",
      "gaps-lede",
      "The published record carries no start or end date for any session, so every " +
        `date below reads "${NOT_STATED}" — the page does not estimate one.`,
    ),
  );
  if (zeroDay.length > 0) {
    /* (c) A text flag, above the table as well as in it, so the reader meets
       it whether or not they scan the rows. Never colour alone. */
    box.append(
      el(
        "p",
        "zero-days-note",
        `${count(zeroDay.length)} session carries ${ZERO_SITTING_DAYS_FLAG}. ` +
          "Any per-sitting-day figure for it reads n/a rather than dividing by zero.",
      ),
    );
  }

  const wrap = el("div", "table-wrap");
  wrap.setAttribute("role", "region");
  wrap.setAttribute("aria-label", "Sessions covered, scrollable");
  wrap.tabIndex = 0;

  const table = el("table");
  const thead = el("thead");
  const hrow = el("tr");
  for (const [text, cls] of [
    ["Session", null],
    ["Dates", null],
    ["Sitting days", "num-col"],
  ]) {
    const th = el("th", cls, text);
    th.scope = "col";
    hrow.append(th);
  }
  thead.append(hrow);
  table.append(thead);

  const tbody = el("tbody");
  for (const session of rows) {
    const tr = el("tr");
    const th = el("th", null, longSessionLabel(session));
    th.scope = "row";
    tr.append(th);

    const start = isoDate(session.startDate);
    const end = isoDate(session.endDate);
    const dates =
      start === NOT_STATED && end === NOT_STATED ? NOT_STATED : `${start} – ${end}`;
    tr.append(el("td", dates === NOT_STATED ? "not-stated" : null, dates));

    const cell = el("td", "num-col");
    if (session.sittingDays === null) {
      cell.classList.add("not-stated");
      cell.textContent = NOT_STATED;
    } else if (session.zeroSittingDays) {
      cell.append(el("span", "zero-days-value", "0"));
      cell.append(el("span", "zero-days-flag", ZERO_SITTING_DAYS_FLAG));
    } else {
      cell.textContent = count(session.sittingDays);
    }
    tr.append(cell);
    tbody.append(tr);
  }
  table.append(tbody);
  wrap.append(table);
  box.append(wrap);
  return box;
}

/* ---------------------------------------------------------------------- */
/* Footer — licence, scope, source terms, corrections, attribution        */
/* ---------------------------------------------------------------------- */

function renderLicence(container, manifest) {
  const frag = document.createDocumentFragment();
  const box = el("div", "licence");

  box.append(el("p", "licence-head", "Licence"));
  box.append(
    el(
      "p",
      "licence-id",
      `Added work: ${stated(manifest.license)}`,
    ),
  );
  box.append(el("p", "licence-scope", stated(manifest.license_scope)));

  // The source-terms disclosure sits directly under the licence scope: the
  // scope says what IS licensed, and this says what was never determined. A
  // reader who stops after the grant has read half of it.
  box.append(renderDisclosure(container.ownerDocument, manifest));

  box.append(el("p", "licence-head", "How to attribute this data"));
  const quote = el("blockquote", "attribution");
  quote.append(el("p", null, stated(manifest.attribution)));
  box.append(quote);

  const links = el("ul", "licence-links");
  if (!isMissing(manifest.license_file)) {
    const li = el("li");
    const a = el("a", null, manifest.license_file);
    // Relative: the licence file sits at the root of the published branch
    // beside this page, copied there by the refresh workflow.
    a.href = `./${manifest.license_file}`;
    li.append(a);
    li.append(el("span", "licence-links-note", " — the full dataset licence"));
    links.append(li);
  }
  if (!isMissing(manifest.project_url)) {
    const li = el("li");
    // The ONE outbound link on the page. A link is not a request: nothing is
    // fetched from it unless a reader clicks.
    const a = el("a", null, manifest.project_url);
    a.href = manifest.project_url;
    // (d) The one link that leaves this host. New tab, and `noopener` so the
    // opened page gets no handle on this one; `noreferrer` so it is not told
    // where the reader came from.
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    li.append(a);
    li.append(el("span", "licence-links-note", " (opens in a new tab)"));
    li.append(el("span", "licence-links-note", " — the project"));
    links.append(li);
  }
  box.append(links);

  box.append(
    el(
      "p",
      "licence-src",
      `Read at runtime from manifest.json, rebuilt ${isoDate(manifest.last_refreshed)}. ` +
        "None of the above is written into this page.",
    ),
  );

  frag.append(box);
  replaceChildren(container, frag);
  container.dataset.state = "ready";
}

/* ---------------------------------------------------------------------- */
/* Failure — quiet for the visitor, specific enough to act on (FR-010)    */
/* ---------------------------------------------------------------------- */

/* ====================================================================== */
/* The router — T130, FR-146 to FR-153                                    */
/* ====================================================================== */

/* Eight views, one rendered at a time, switched by the URL hash.
 *
 * HASH rather than a path, and that is a hosting constraint rather than a
 * preference: GitHub Pages serves static files, so `/search` would 404 on a
 * direct load and would need redirect configuration the free tier does not
 * offer. A hash never reaches the server. It also gives back and forward for
 * free, which is FR-147.
 *
 * `module` is `null` for the two views the shell renders itself — their data
 * is already on the first load, so there is nothing to defer. Every other view
 * names a module that is loaded with `import()` on first open and memoised,
 * so a reader pays for a view once and only if they open it.
 *
 * The ids are a PUBLIC INTERFACE. Someone may link to `#composition`, so
 * renaming one breaks their link; `tests/unit/test_view_routes.py` pins the
 * set.
 */
const VIEWS = [
  { id: "coverage", heading: "Coverage", module: null },
  { id: "search", heading: "Subject search", module: "./views/search.js" },
  { id: "seat", heading: "Your state and constituency", module: "./views/seat.js" },
  { id: "ministry", heading: "Ministry profile", module: "./views/ministries.js" },
  { id: "compare", heading: "Compare two ministries", module: "./views/ministries.js" },
  { id: "load", heading: "Question load by session", module: "./views/ministries.js" },
  { id: "composition", heading: "House composition", module: "./views/composition.js" },
];

/* SEVEN views, not the eight `contracts/view-routes.md` first listed.
 *
 * `licence` was planned as the eighth, and that was wrong: the licence, the
 * attribution and the SOURCE-TERMS DISCLOSURE live in the page footer, which
 * sits outside <main> and therefore renders on every view. Feature 001 put
 * them there deliberately -- the disclosure that the source's terms were never
 * determined is a standing obligation, not a page a reader opts into.
 *
 * Turning it into a switchable view would have hidden it behind a choice, so
 * it stays in the footer and is visible from all seven. The contract was
 * written before anyone looked at where the licence actually lived; it is
 * corrected rather than honoured.
 */

/** The view a visitor lands on, and where an unknown hash resolves (FR-153).
 *
 * The coverage statement, deliberately: what the record claims to cover is
 * read before anything drawn from it. */
const LANDING = "coverage";

/** Loaded view modules, by specifier. A view opened twice costs one import. */
const loaded = new Map();

/** Which views have been mounted, so returning to one does not rebuild it and
 * does not refetch what it already has (FR-152). */
const mounted = new Set();

function viewById(id) {
  return VIEWS.find((v) => v.id === id) ?? null;
}

/** The id in the current hash, or the landing view. */
function idFromHash() {
  const raw = String(location.hash || "").replace(/^#/, "");
  return viewById(raw) ? raw : LANDING;
}

/**
 * Load and mount one view, once.
 *
 * A failed `import()` degrades to a worded message INSIDE that view and leaves
 * the shell and every other view working (FR-010). It is recorded as mounted
 * either way, so a reader who returns gets the message rather than a second
 * failing download.
 */
async function mountView(view, doc) {
  if (mounted.has(view.id) || !view.module) {
    mounted.add(view.id);
    return;
  }
  mounted.add(view.id);
  try {
    let mod = loaded.get(view.module);
    if (!mod) {
      mod = await import(view.module);
      loaded.set(view.module, mod);
    }
    await mod.mount(doc, view.id);
  } catch (error) {
    /* The message goes in a CHILD of the view, never into the view itself.
     *
     * `renderUnavailable` calls `replaceChildren`, so passing the section
     * container here wiped the view's own <h2> along with everything else --
     * measured: a failed module left `view-search` with no heading at all, and
     * the router's focus move then had nothing to focus and silently left the
     * reader on <body>. A view that fails must still be a view: it keeps its
     * heading and its lede, and the failure is reported underneath them. */
    const host = doc.getElementById(`view-${view.id}`);
    const slot = host
      ? host.querySelector("[data-state]") ?? host.appendChild(doc.createElement("div"))
      : null;
    if (slot) {
      renderUnavailable(slot, "This view could not be loaded.", describe(error));
    }
  }
}

/**
 * Show one view and hide the rest.
 *
 * Focus moves to the new view's heading. Without that a keyboard reader stays
 * where the old view was — which, after the old view is hidden, is nowhere.
 * `tabIndex = -1` makes the heading focusable without adding a tab stop, which
 * is the pattern this page already uses on a search result.
 */
async function showView(id, doc, { moveFocus = true } = {}) {
  const view = viewById(id) ?? viewById(LANDING);

  for (const candidate of VIEWS) {
    const section = doc.getElementById(`view-${candidate.id}`);
    if (section) section.hidden = candidate.id !== view.id;
    const tab = doc.querySelector(`[data-view="${candidate.id}"]`);
    if (tab) {
      const current = candidate.id === view.id;
      // aria-current for assistive technology, and a data attribute the
      // stylesheet hangs a NON-COLOUR cue on (FR-149).
      if (current) tab.setAttribute("aria-current", "page");
      else tab.removeAttribute("aria-current");
    }
  }

  await mountView(view, doc);

  if (moveFocus) {
    const host = doc.getElementById(`view-${view.id}`);
    const heading = host ? host.querySelector("h1, h2") : null;
    if (heading) {
      heading.tabIndex = -1;
      heading.focus({ preventScroll: false });
    }
  }
}

/** Wire the hash to the views. Called once, by boot(). */
function startRouter(doc) {
  window.addEventListener("hashchange", () => {
    void showView(idFromHash(), doc);
  });
  // The first render must NOT move focus: a page that steals focus on load
  // takes it away from the browser's own chrome before a reader has done
  // anything.
  return showView(idFromHash(), doc, { moveFocus: false });
}

/** The view ids, for the tests and for `tools/list_page_urls.py`. */
export const VIEW_IDS = Object.freeze(VIEWS.map((v) => v.id));
export const LANDING_VIEW = LANDING;

/* ====================================================================== */
/* Boot — T128                                                            */
/* ====================================================================== */

/* The assertions below are about the PAGE, not decisions the page makes. Each
 * one being false would mean a visitor pays for a view they never opened, and
 * each throws rather than warns, because feature 001 chose a thrown error here
 * so a discipline breach fails loudly instead of appearing as a slightly
 * larger number nobody reads.
 *
 * Five predicates now, where there were two. The three new ones exist because
 * FR-151 moved `ministry-profile.jsonl` and `ministries.jsonl` off the first
 * load — 19,408 B on the wire between them — and because `composition.jsonl`
 * and every module under `views/` must not be on it either.
 */
const BOOT_GUARDS = [
  ["a search file", searchAssetsRequested],
  ["a seat file", seatAssetsRequested],
  ["a ministry file", ministryAssetsRequested],
  ["a composition file", compositionAssetsRequested],
];

export async function boot(doc = document) {
  const coverageBody = doc.getElementById("coverage-body");
  const licenceBody = doc.getElementById("licence-body");

  for (const [what, requested] of BOOT_GUARDS) {
    if (requested()) {
      throw new Error(`${what} was requested during boot; all of them must be lazy`);
    }
  }
  // No view module either (FR-128). `loaded` is this file's own memo, so an
  // import that happened before boot would be visible here.
  if (loaded.size > 0) {
    throw new Error(
      `${loaded.size} view module(s) were imported during boot; all of them must be lazy`,
    );
  }

  const results = await Promise.allSettled([
    fetchCoverage(),
    fetchSessions(),
    fetchCountingBasis(),
    fetchManifest(),
  ]);
  const [coverage, sessions, basis, manifest] = results;

  if (coverage.status === "fulfilled") {
    try {
      renderCoverage(coverageBody, {
        coverage: coverage.value,
        sessions: sessions.status === "fulfilled" ? sessions.value : [],
        basis: basis.status === "fulfilled" ? basis.value : [],
      });
    } catch (error) {
      renderUnavailable(
        coverageBody,
        "The coverage statement was read but could not be displayed.",
        String(error && error.message),
      );
    }
  } else {
    renderUnavailable(
      coverageBody,
      "The coverage statement could not be read from the published files.",
      describe(coverage.reason),
    );
  }

  if (basis.status === "fulfilled") views.basis = basis.value;

  if (manifest.status === "fulfilled") {
    renderLicence(licenceBody, manifest.value);
  } else {
    renderUnavailable(
      licenceBody,
      "The licence could not be read from the published manifest.",
      describe(manifest.reason),
    );
  }

  await startRouter(doc);
}

if (typeof document !== "undefined") {
  void boot();
}
