/* Indian Sansad — page entry point. T074/T077.
 *
 * An ES module, loaded directly by index.html with no build step. Everything
 * it renders is read at runtime from this project's own published files; no
 * figure, licence line or basis sentence is typed into the page.
 *
 * What this part implements: the shell (T074), the stylesheet (T075), the
 * fetch layer (T076) and the coverage display (T077). The ministry profile
 * (T078), subject search (T079) and comparison (T080) are deliberately empty
 * regions in index.html, marked as such on screen.
 *
 * Rendering rule: nothing from a published file ever reaches `innerHTML`.
 * Every value goes in through `textContent`. The records are this project's
 * own, but they are built from an upstream payload nobody controls, and a page
 * that interpolated them into markup would be one upstream change away from
 * executing it.
 */

import {
  CrossOriginRefused,
  fetchCountingBasis,
  fetchCoverage,
  fetchManifest,
  fetchSessions,
  searchIndexRequested,
} from "./lib/fetch.js";
import {
  count,
  houseName,
  isMissing,
  isoDate,
  NOT_STATED,
  orderSessions,
  percent,
  sessionLabel,
  stated,
} from "./lib/format.js";

/* ---------------------------------------------------------------------- */
/* Small DOM helpers. No library.                                         */
/* ---------------------------------------------------------------------- */

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

function replaceChildren(node, ...children) {
  node.replaceChildren(...children);
}

/** A labelled figure with the sentence that says how it was counted. */
function fact(label, value, note) {
  const wrap = el("div", "fact");
  wrap.append(el("p", "fact-label", label), el("p", "fact-value", value));
  if (note) wrap.append(el("p", "fact-note", note));
  return wrap;
}

function list(className, items, render) {
  const ul = el("ul", className);
  for (const item of items) {
    const li = el("li");
    render(li, item);
    ul.append(li);
  }
  return ul;
}

/* ---------------------------------------------------------------------- */
/* T077 — the coverage statement                                          */
/* ---------------------------------------------------------------------- */

const HOUSE_LOK_SABHA = "lok-sabha";

function renderCoverage(container, { coverage, sessions, basis }) {
  const rows = new Map(coverage.map((row) => [row.house, row]));
  const lok = rows.get(HOUSE_LOK_SABHA);
  if (!lok) {
    renderUnavailable(container, "The coverage statement carries no Lok Sabha row.");
    return;
  }

  const frag = document.createDocumentFragment();

  /* --- Houses. The one claim the page must make loudly (FR-013). ------- */
  const houses = el("div", "houses");
  houses.append(el("p", "houses-value", "Lok Sabha only"));
  const others = coverage.filter((row) => row.house !== HOUSE_LOK_SABHA);
  if (others.length > 0) {
    const notCovered = others.map((row) => houseName(row.house)).join(", ");
    houses.append(
      el("p", "houses-note", `${notCovered} is not covered by this dataset.`),
    );
    for (const row of others) {
      if (!isMissing(row.unobtainable_reason)) {
        houses.append(el("p", "houses-why", `Why: ${row.unobtainable_reason}`));
      }
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
        `${count(lok.ministry_names_without_confirmed_mapping)} names are awaiting a ` +
        "maintainer decision on whether they are renames of one another.",
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
  frag.append(renderSessions(lok, sessions));

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
  const box = el("section", "sessions");
  box.append(el("h3", null, "Sessions covered"));
  box.append(
    el(
      "p",
      "gaps-lede",
      "Ordered by term and session number. The published record carries no " +
        `start or end date for any session, so every date below reads "${NOT_STATED}" ` +
        "— the page does not estimate one.",
    ),
  );

  const byId = new Map(
    (sessions ?? []).map((s) => [`${s.house}/${s.term}/${s.number}`, s]),
  );
  const ordered = orderSessions(lok.sessions_covered ?? []);

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
  for (const session of ordered) {
    const row = el("tr");
    const th = el("th", null, sessionLabel(session));
    th.scope = "row";
    row.append(th);

    const record = byId.get(session.sessionId);
    const start = record ? isoDate(record.start_date) : NOT_STATED;
    const end = record ? isoDate(record.end_date) : NOT_STATED;
    const dates =
      start === NOT_STATED && end === NOT_STATED ? NOT_STATED : `${start} – ${end}`;
    const dateCell = el("td", dates === NOT_STATED ? "not-stated" : null, dates);
    row.append(dateCell);

    const days = record ? record.sitting_days : null;
    row.append(
      el(
        "td",
        isMissing(days) ? "num-col not-stated" : "num-col",
        isMissing(days) ? NOT_STATED : count(days),
      ),
    );
    tbody.append(row);
  }
  table.append(tbody);
  wrap.append(table);
  box.append(wrap);
  return box;
}

/* ---------------------------------------------------------------------- */
/* Footer — licence, attribution and scope, from the manifest             */
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
    a.rel = "noopener noreferrer";
    li.append(a);
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

function renderUnavailable(container, message, detail) {
  const box = el("div", "unavailable");
  box.append(el("p", "unavailable-head", "This could not be read"));
  box.append(el("p", null, message));
  if (detail) box.append(el("p", "unavailable-detail", detail));
  box.append(
    el(
      "p",
      "unavailable-note",
      "Nothing above is estimated or filled in. The published files are still " +
        "downloadable directly.",
    ),
  );
  replaceChildren(container, box);
  container.dataset.state = "error";
}

/* ---------------------------------------------------------------------- */
/* Boot                                                                   */
/* ---------------------------------------------------------------------- */

export async function boot(doc = document) {
  const coverageBody = doc.getElementById("coverage-body");
  const licenceBody = doc.getElementById("licence-body");

  // The index must not have been touched by anything above. This is an
  // assertion about the page, not a decision: if it is ever false, a visitor
  // who never searches is paying 2.37 MiB and T019's budget is wrong.
  if (searchIndexRequested()) {
    throw new Error("the search index was requested during boot; it must be lazy");
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

  if (manifest.status === "fulfilled") {
    renderLicence(licenceBody, manifest.value);
  } else {
    renderUnavailable(
      licenceBody,
      "The licence could not be read from the published manifest.",
      describe(manifest.reason),
    );
  }
}

function describe(error) {
  if (!error) return "";
  if (error instanceof CrossOriginRefused) {
    return `${error.name}: ${error.message}`;
  }
  return `${error.name || "Error"}: ${error.message || String(error)}`;
}

if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      boot();
    });
  } else {
    boot();
  }
}
