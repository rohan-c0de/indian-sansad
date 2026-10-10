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

import { legend, stackedColumns } from "./lib/chart.js";
import {
  CrossOriginRefused,
  fetchCountingBasis,
  fetchCoverage,
  fetchManifest,
  fetchMinistries,
  fetchMinistryProfile,
  fetchSessions,
  searchIndexRequested,
} from "./lib/fetch.js";
import {
  STATUS_FIELDS,
  basisFor,
  compare,
  profileMinistries,
  profileSessions,
  selectSpan,
  share,
  spanChange,
  spanTotals,
} from "./lib/profile.js";
import {
  coveredRows,
  housesClaim,
  housesNotCovered,
  longSessionLabel,
  sessionRows,
  ZERO_SITTING_DAYS_FLAG,
} from "./lib/coverage.js";
import { count, isMissing, isoDate, NOT_STATED, percent, stated } from "./lib/format.js";

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

  await bootViews(doc);
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

/* ====================================================================== */
/* T078 — ministry profile, and T080 — two-ministry comparison            */
/* ====================================================================== */

/** Everything the two views read. Fetched once, shared. */
const views = {
  rows: [],
  ministries: [],
  sessions: [],
  basis: [],
  ready: false,
};

function option(value, label, selected) {
  const node = el("option", null, label);
  node.value = value;
  if (selected) node.selected = true;
  return node;
}

function labelledSelect(id, labelText, options, selectedValue) {
  const wrap = el("label", "field");
  wrap.htmlFor = id;
  wrap.append(el("span", "field-label", labelText));
  const select = el("select");
  select.id = id;
  select.name = id;
  for (const [value, text] of options) {
    select.append(option(value, text, value === selectedValue));
  }
  wrap.append(select);
  return { wrap, select };
}

/** The counting basis, read from the published file and rendered beside the
 * figures. Never retyped: `basisFor` looks it up by the unit the rows name. */
function basisBlock(span, { head = "How these figures were counted" } = {}) {
  const record = basisFor(span, views.basis);
  const box = el("div", "basis");
  box.append(el("p", "basis-head", head));
  if (!record) {
    box.append(
      el("p", "basis-text", "The counting basis could not be read from the published files."),
    );
    return box;
  }
  box.append(el("p", "basis-text", record.counting_basis));
  box.append(
    el(
      "p",
      "basis-src",
      `Read from aggregates/counting-basis.jsonl, unit "${record.unit}", ` +
        `basis version ${stated(record.basis_version)}.`,
    ),
  );
  return box;
}

function changeText(c) {
  if (!c) return NOT_STATED;
  const sign = c.absolute > 0 ? "+" : "";
  const abs = `${sign}${count(c.absolute)}`;
  if (c.percent === null) {
    // A percent change from zero is undefined, not infinite and not 100%.
    return `${abs} (no percentage: the first session was zero)`;
  }
  const pSign = c.percent > 0 ? "+" : "";
  return `${abs} (${pSign}${c.percent.toFixed(1)}%)`;
}

function statusStrip(totals, { heading }) {
  const box = el("div", "status-strip");
  box.append(el("p", "strip-head", heading));
  const ul = el("ul", "status-list");
  for (const field of STATUS_FIELDS) {
    const value = totals.status[field.key];
    const li = el("li", field.flagged ? "status-item flagged" : "status-item");
    if (field.flagged) {
      // The flag is a WORD, not a colour. Removing every colour from this
      // page leaves the meaning intact.
      li.append(el("span", "flag-word", "flagged"));
    }
    li.append(el("span", "status-label", field.label));
    li.append(el("span", "status-value", count(value)));
    const pct = share(value, totals.questions);
    li.append(el("span", "status-share", pct === null ? NOT_STATED : `${pct.toFixed(1)}%`));
    ul.append(li);
  }
  box.append(ul);
  box.append(
    el(
      "p",
      "strip-note",
      `These four account for all ${count(totals.questions)} questions — they are a ` +
        "split of the same total, not a subset of it. A question whose asking members " +
        "were not all identified is counted in every figure here and flagged, never " +
        "filtered out.",
    ),
  );
  return box;
}

function mixTable(span, types, totals) {
  const section = el("section", "mix-block");
  section.append(el("h4", null, "Question type mix, by session"));
  section.append(
    el(
      "p",
      "helper",
      "ALL questions, whether or not the asking member was identified. The " +
        "ministry and the question type are read off the question record, not " +
        "off resolution — so this is not a resolved-only figure.",
    ),
  );

  const wrap = el("div", "table-wrap");
  wrap.setAttribute("role", "region");
  wrap.setAttribute("aria-label", "Questions per session by type, scrollable");
  wrap.tabIndex = 0;
  const table = el("table");
  const caption = el("caption", "visually-hidden");
  caption.textContent =
    "Questions per session for the selected ministry, by question type and by how " +
    "completely each question is linked to a member.";
  table.append(caption);

  const thead = el("thead");
  const hrow = el("tr");
  const headings = ["Session", "Questions", ...types];
  for (const field of STATUS_FIELDS) headings.push(field.label);
  for (const text of headings) {
    const th = el("th", text === "Session" ? null : "num-col", text);
    th.scope = "col";
    hrow.append(th);
  }
  thead.append(hrow);
  table.append(thead);

  const tbody = el("tbody");
  for (const entry of span) {
    const tr = el("tr");
    const th = el("th", null, longSessionLabel(entry.session));
    th.scope = "row";
    tr.append(th);
    tr.append(el("td", "num-col", count(entry.questions)));
    for (const type of types) tr.append(el("td", "num-col", count(entry.typeMix[type] ?? 0)));
    for (const field of STATUS_FIELDS) {
      tr.append(
        el("td", field.flagged ? "num-col td-flag" : "num-col", count(entry.status[field.key])),
      );
    }
    if (!entry.present) {
      tr.classList.add("row-absent");
      th.append(el("span", "row-absent-note", "no questions in the record"));
    }
    tbody.append(tr);
  }
  table.append(tbody);

  const tfoot = el("tfoot");
  const frow = el("tr");
  const fth = el("th", null, "Total");
  fth.scope = "row";
  frow.append(fth);
  frow.append(el("td", "num-col", count(totals.questions)));
  for (const type of types) frow.append(el("td", "num-col", count(totals.typeMix[type] ?? 0)));
  for (const field of STATUS_FIELDS) {
    frow.append(
      el("td", field.flagged ? "num-col td-flag" : "num-col", count(totals.status[field.key])),
    );
  }
  tfoot.append(frow);
  table.append(tfoot);

  wrap.append(table);
  section.append(wrap);
  section.append(
    el(
      "p",
      "footnote",
      '"Partly linked": at least one asking member was identified and at least one was ' +
        'not. "Not linked": none were. "Ambiguous": the name matched more than one ' +
        "member and the page will not guess. All three are still counted as questions " +
        "in every column to their left.",
    ),
  );
  return section;
}

function renderProfileResult(container, { ministry, span }) {
  const totals = spanTotals(span);
  const delta = spanChange(span);
  const types = [...new Set(span.flatMap((e) => Object.keys(e.typeMix)))].sort();

  const frag = document.createDocumentFragment();

  const head = el("div", "result-head");
  head.append(el("h3", null, ministry.name));
  head.append(
    el(
      "p",
      "result-span",
      `${longSessionLabel(span[0].session)} to ${longSessionLabel(span[span.length - 1].session)}` +
        ` · ${count(span.length)} sessions · session dates are ${NOT_STATED}`,
    ),
  );
  if (ministry.formerNames.length > 0) {
    // Rename DATES are not published. Showing "(renamed 2021)" would be a
    // claim the record does not support.
    head.append(
      el(
        "p",
        "former-names",
        `Formerly: ${ministry.formerNames.join("; ")}. Questions under every name ` +
          "above are counted together. The record does not publish when a rename " +
          `happened, so no date is shown — it is ${NOT_STATED}.`,
      ),
    );
  }
  frag.append(head);

  const stats = el("div", "fact-grid");
  stats.append(
    fact("Questions asked", count(totals.questions), `across ${count(span.length)} sessions`),
  );
  for (const type of types) {
    const pct = share(totals.typeMix[type] ?? 0, totals.questions);
    stats.append(
      fact(
        `${type.charAt(0)}${type.slice(1).toLowerCase()} share`,
        pct === null ? NOT_STATED : `${pct.toFixed(1)}%`,
        `${count(totals.typeMix[type] ?? 0)} of ${count(totals.questions)} questions`,
      ),
    );
  }
  stats.append(
    fact(
      "Not fully linked to a member",
      count(totals.flagged),
      "counted in every figure on this page, never filtered out",
    ),
  );
  frag.append(stats);

  /* How both changed across the span: first selected session vs last. */
  const changeBox = el("section", "change-block");
  changeBox.append(el("h4", null, "How this changed across the span"));
  if (delta.singleSession) {
    changeBox.append(
      el("p", "helper", "One session is selected, so there is nothing to compare it with."),
    );
  } else {
    changeBox.append(
      el(
        "p",
        "helper",
        `First selected session (${longSessionLabel(delta.firstSession)}) against last ` +
          `(${longSessionLabel(delta.lastSession)}).`,
      ),
    );
    const ul = el("ul", "change-list");
    const q = el("li");
    q.append(el("span", "change-label", "Questions"));
    q.append(el("span", "change-value", changeText(delta.questions)));
    q.append(
      el("span", "change-from", `${count(delta.questions.first)} → ${count(delta.questions.last)}`),
    );
    ul.append(q);
    for (const entry of delta.byType) {
      const li = el("li");
      li.append(el("span", "change-label", entry.type));
      li.append(el("span", "change-value", changeText(entry.count)));
      const sf = entry.shareFirst === null ? NOT_STATED : `${entry.shareFirst.toFixed(1)}%`;
      const sl = entry.shareLast === null ? NOT_STATED : `${entry.shareLast.toFixed(1)}%`;
      li.append(el("span", "change-from", `share ${sf} → ${sl}`));
      ul.append(li);
    }
    changeBox.append(ul);
  }
  frag.append(changeBox);

  frag.append(statusStrip(totals, { heading: "How completely each question is linked to a member" }));
  frag.append(basisBlock(span));

  if (types.length > 0 && totals.questions > 0) {
    const chartBox = el("section", "chart-block");
    chartBox.append(el("h4", null, "Questions per session, by type"));
    chartBox.append(legend(types));
    chartBox.append(
      stackedColumns(
        span.map((entry) => ({
          label: `S${entry.session.number}`,
          total: entry.questions,
          parts: entry.typeMix,
        })),
        types,
        {
          title: `Questions per session for ${ministry.name}, by question type`,
          description:
            "A stacked column per session. The same figures are given in the table below.",
        },
      ),
    );
    frag.append(chartBox);
  }

  frag.append(mixTable(span, types, totals));
  replaceChildren(container, frag);
  container.dataset.state = "ready";
}

function renderCompareResult(container, { ministries, result }) {
  const frag = document.createDocumentFragment();
  const [left, right] = result.sides;
  const names = new Map(ministries.map((m) => [m.ministryId, m.name]));
  const span = left.span;

  frag.append(
    el(
      "p",
      "helper",
      `${longSessionLabel(span[0].session)} to ${longSessionLabel(span[span.length - 1].session)}` +
        ` · ${count(span.length)} sessions · the same span and the same counting basis for both.`,
    ),
  );

  const rows = [
    ["Questions asked", (side) => count(side.totals.questions)],
    ...result.types.map((type) => [
      `${type} share`,
      (side) => {
        const pct = share(side.totals.typeMix[type] ?? 0, side.totals.questions);
        return pct === null ? NOT_STATED : `${pct.toFixed(1)}% (${count(side.totals.typeMix[type] ?? 0)})`;
      },
    ]),
    ...STATUS_FIELDS.map((field) => [
      field.label,
      (side) => count(side.totals.status[field.key]),
      field.flagged,
    ]),
    [
      "Change across the span",
      (side) => (side.change.singleSession ? NOT_STATED : changeText(side.change.questions)),
    ],
  ];

  /* The table, for a wide screen -- inside its own scroll container. */
  const wrap = el("div", "table-wrap");
  wrap.setAttribute("role", "region");
  wrap.setAttribute("aria-label", "Two-ministry comparison, scrollable");
  wrap.tabIndex = 0;
  const table = el("table", "table-compare");
  const thead = el("thead");
  const hrow = el("tr");
  for (const text of ["Figure", names.get(left.ministryId), names.get(right.ministryId)]) {
    const th = el("th", null, text);
    th.scope = "col";
    hrow.append(th);
  }
  thead.append(hrow);
  table.append(thead);
  const tbody = el("tbody");
  for (const [label, render, flagged] of rows) {
    const tr = el("tr", flagged ? "tr-flag" : null);
    const th = el("th", null, label);
    th.scope = "row";
    if (flagged) th.append(el("span", "flag-word", "flagged"));
    tr.append(th);
    tr.append(el("td", "num-col", render(left)));
    tr.append(el("td", "num-col", render(right)));
    tbody.append(tr);
  }
  table.append(tbody);
  wrap.append(table);
  frag.append(wrap);

  /* The same totals as cards, for a phone. Identical numbers by construction:
   * both forms render from the same `rows` list. */
  const cards = el("ul", "compare-cards");
  for (const side of result.sides) {
    const li = el("li", "card");
    li.append(el("p", "cc-name", names.get(side.ministryId)));
    const dl = el("dl", "cc-list");
    for (const [label, render, flagged] of rows) {
      const dt = el("dt", flagged ? "flagged" : null, label);
      if (flagged) dt.append(el("span", "flag-word", "flagged"));
      dl.append(dt);
      dl.append(el("dd", null, render(side)));
    }
    li.append(dl);
    cards.append(li);
  }
  frag.append(cards);

  frag.append(
    basisBlock(span, { head: "The counting basis used for BOTH columns" }),
  );
  replaceChildren(container, frag);
  container.dataset.state = "ready";
}

/* ---------------------------------------------------------------------- */
/* Pickers and wiring                                                     */
/* ---------------------------------------------------------------------- */

function sessionOptions() {
  return views.sessions.map((s) => [s.sessionId, longSessionLabel(s)]);
}

function ministryOptions() {
  return views.ministries.map((m) => [m.ministryId, m.name]);
}

function buildProfileView(doc) {
  const picker = doc.getElementById("profile-picker");
  const result = doc.getElementById("profile-result");
  if (!picker || !result) return;

  const sessions = sessionOptions();
  const ministries = ministryOptions();
  const first = sessions[0]?.[0];
  const last = sessions[sessions.length - 1]?.[0];

  const ministry = labelledSelect("profile-ministry", "Ministry", ministries, ministries[0]?.[0]);
  const from = labelledSelect("profile-from", "From session", sessions, first);
  const to = labelledSelect("profile-to", "To session", sessions, last);

  const form = el("div", "picker");
  form.append(ministry.wrap, from.wrap, to.wrap);
  replaceChildren(picker, form);

  const draw = () => {
    const chosen = views.ministries.find((m) => m.ministryId === ministry.select.value);
    const span = selectSpan(views.rows, {
      ministryId: ministry.select.value,
      fromSession: from.select.value,
      toSession: to.select.value,
      allSessions: views.sessions,
    });
    if (span.length === 0) {
      renderUnavailable(result, "That span contains no session.");
      return;
    }
    try {
      renderProfileResult(result, { ministry: chosen, span });
    } catch (error) {
      // A status split that does not account for every question is a data
      // fault, not a rendering preference. Say so rather than show it.
      renderUnavailable(result, "These figures did not add up and were not shown.", describe(error));
    }
  };

  for (const select of [ministry.select, from.select, to.select]) {
    select.addEventListener("change", draw);
  }
  draw();
}

function buildCompareView(doc) {
  const picker = doc.getElementById("compare-picker");
  const result = doc.getElementById("compare-result");
  if (!picker || !result) return;

  const sessions = sessionOptions();
  const ministries = ministryOptions();
  const first = sessions[0]?.[0];
  const last = sessions[sessions.length - 1]?.[0];

  const a = labelledSelect("compare-a", "First ministry", ministries, ministries[0]?.[0]);
  const b = labelledSelect("compare-b", "Second ministry", ministries, ministries[1]?.[0]);
  const from = labelledSelect("compare-from", "From session", sessions, first);
  const to = labelledSelect("compare-to", "To session", sessions, last);

  const form = el("div", "picker");
  form.append(a.wrap, b.wrap, from.wrap, to.wrap);
  replaceChildren(picker, form);

  const draw = () => {
    try {
      const comparison = compare(views.rows, {
        ministryIds: [a.select.value, b.select.value],
        fromSession: from.select.value,
        toSession: to.select.value,
        allSessions: views.sessions,
      });
      if (comparison.sides[0].span.length === 0) {
        renderUnavailable(result, "That span contains no session.");
        return;
      }
      renderCompareResult(result, { ministries: views.ministries, result: comparison });
    } catch (error) {
      renderUnavailable(result, "These figures did not add up and were not shown.", describe(error));
    }
  };

  for (const select of [a.select, b.select, from.select, to.select]) {
    select.addEventListener("change", draw);
  }
  draw();
}

async function bootViews(doc) {
  const profileResult = doc.getElementById("profile-result");
  const compareResult = doc.getElementById("compare-result");
  const [rows, ministries] = await Promise.allSettled([
    fetchMinistryProfile(),
    fetchMinistries(),
  ]);

  if (rows.status !== "fulfilled") {
    for (const node of [profileResult, compareResult]) {
      if (node) {
        renderUnavailable(
          node,
          "The ministry profile could not be read from the published files.",
          describe(rows.reason),
        );
      }
    }
    return;
  }

  views.rows = rows.value;
  views.sessions = profileSessions(views.rows);
  views.ministries = profileMinistries(
    views.rows,
    ministries.status === "fulfilled" ? ministries.value : [],
  );
  views.ready = true;

  buildProfileView(doc);
  buildCompareView(doc);
}
