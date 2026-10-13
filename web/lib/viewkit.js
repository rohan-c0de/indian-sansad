/* The view helpers: controls, figure tables, and the status vocabulary. T136.
 *
 * Split out of `lib/shared.js` for a measured reason. `shared.js` is on the
 * FIRST LOAD -- the shell imports `el`, `replaceChildren`, `renderUnavailable`
 * and `describe` from it -- and these functions pull in `lib/chart.js` and
 * `lib/profile.js`, which the shell does not need. Measured in a browser: both
 * modules were on the first load, 6,222 B at gzip -6 between them, paid by a
 * visitor who only ever read the coverage statement.
 *
 * So the dependency is cut where the need is: `shared.js` keeps the DOM
 * primitives and imports nothing heavy; this module holds everything a VIEW
 * needs and is reached only through a view's own `import()`.
 *
 *     app.js      -> lib/shared.js   (primitives only)
 *     views/*     -> lib/viewkit.js  -> lib/{chart,profile,coverage}.js
 */

import { legend, stackedColumns } from "./chart.js";
import { longSessionLabel } from "./coverage.js";
import { NOT_STATED, count, isMissing, percent, stated } from "./format.js";
import { STATUS_FIELDS, basisFor, share } from "./profile.js";
import { fetchMinistries } from "./fetch.js";
import { el, list, views } from "./shared.js";

export function option(value, label, selected) {
  const node = el("option", null, label);
  node.value = value;
  if (selected) node.selected = true;
  return node;
}

export function labelledSelect(id, labelText, options, selectedValue) {
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
export function basisBlock(span, { head = "How these figures were counted" } = {}) {
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

/** The published basis for one unit, rendered through the shared block so this
 * view, the ministry profile and the comparison all print it the same way. */
export function basisBlockForUnit(unit, options) {
  return basisBlock([{ row: { counting_basis_unit: unit } }], options);
}

export function changeText(c) {
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

export function statusStrip(totals, { heading }) {
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

export function mixTable(span, types, totals) {
  const section = el("section", "mix-block");
  section.append(el("h4", null, "Question type mix, by session"));
  section.append(
    el(
      "p",
      "helper",
      "ALL questions, whether or not the asking member was identified. The " +
        "ministry and the question type are read off the question record, not " +
        "off resolution — so this is not a resolved-only figure. Session dates " +
        "are not stated in the published record.",
    ),
  );

  const wrap = el("div", "table-wrap");
  wrap.setAttribute("role", "region");
  wrap.setAttribute("aria-label", "Questions per session by type, scrollable");
  wrap.tabIndex = 0;
  const table = el("table");
  // The caption stays SHORT. It lives inside the table, and the table lives
  // inside a horizontal scroller -- so a long caption is 974 px wide at a
  // 390 px viewport and a reader has to scroll sideways to read prose. The
  // long description is the page-width paragraph above, which wraps.
  const caption = el("caption", "table-caption");
  caption.textContent = "Questions per session, by type and by link status";
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

/** Load the ministry NAME lookup, once, for whichever view needs it first.
 *
 * `reference/ministries.jsonl` used to be fetched by `bootViews()` on page
 * load, so `views.ministryNames` was always populated by the time anything
 * read it. T137 took that file off the first load -- it is 1,856 B on the wire
 * and a visitor who never opens a ministry view should not pay for it -- and
 * the ministry views were wired to fetch it on first open.
 *
 * The SEARCH view was not, and it reads this lookup for every result row. The
 * measured consequence: opening `#search` without opening `#ministry` first
 * left the map empty, so `ministryNameFor` fell through to its unknown-id
 * branch and **every row was flagged** "this ministry id is not in the
 * published ministry reference set" -- on a reference set that contains all 56
 * of them. 57 px of false flag on every result, which is also what made the
 * row-height measurement unreadable.
 *
 * Memoised in `lib/fetch.js`, so a reader who opens both views pays once. */
export async function ensureMinistryNames() {
  if (views.ministryNames && views.ministryNames.size > 0) return;
  try {
    const rows = await fetchMinistries();
    views.ministryNames = new Map(rows.map((m) => [m.ministry_id, m]));
  } catch {
    /* Left empty deliberately. A failed name lookup must not take the result
     * list off the page: `ministryNameFor` then shows the raw id WITH a flag,
     * which is the honest rendering of "the name could not be read" and is
     * exactly what the flag is for. */
  }
}

export function ministryNameFor(ministryId) {
  if (isMissing(ministryId)) return { text: NOT_STATED, flagged: true };
  const record = views.ministryNames.get(ministryId);
  if (!record) {
    // An id the reference set does not carry. Shown AS TEXT with a flag --
    // never silently blank, and never guessed at from the slug.
    return { text: String(ministryId), flagged: true };
  }
  return { text: record.canonical_name ?? String(ministryId), flagged: false };
}

/* The published question TYPE for a question id.
 *
 * `parseQuestionId` yields the id's own path segment, which is lowercase
 * (`starred` / `unstarred`); the published type field elsewhere in the record
 * is uppercase (`STARRED` / `UNSTARRED`), and `lib/marks.js` compares against
 * the published spelling. Normalised in ONE place so the two spellings cannot
 * drift into two behaviours. An id that does not parse yields null, and
 * `starMark` then renders nothing rather than guessing a bucket. */
export function questionTypeOf(parsed) {
  if (!parsed || typeof parsed.type !== "string") return null;
  return parsed.type.toUpperCase();
}
