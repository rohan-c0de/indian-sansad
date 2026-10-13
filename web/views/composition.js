/* House composition, the 17th Lok Sabha against the 18th. T162.
 *
 * The only view in this feature that adds a request. `aggregates/composition.jsonl`
 * is 25,237 B raw and 1,835 B on the wire -- the cheapest file the page reads --
 * and before this feature it was fetched by NOTHING: feature 001 published the
 * aggregate and explicitly left the view for later ("the page may add it
 * later; nothing here requires it to").
 *
 * Three dimensions, because three is what the published aggregate carries and
 * three is what FR-008 permits: party, state, and number of terms served.
 * Gender, age band, profession and qualification are not in the aggregate and
 * may not be published without a recorded decision under Principle V.
 *
 * NO DATE APPEARS IN THIS VIEW, and that is a property of the record rather
 * than a choice: every one of the 9,986 term records in the published member
 * reference reads `start_date: "not stated"`, as do all 21 sessions. Terms can
 * be ordered and counted; they cannot be placed on a calendar (FR-124).
 */

import { horizontalBars, legend } from "../lib/chart.js";
import { loadComposition } from "../lib/fetch.js";
import { count } from "../lib/format.js";
import { figure, figureText } from "../lib/marks.js";
import {
  describe,
  el,
  list,
  renderUnavailable,
  replaceChildren,
} from "../lib/shared.js";

/** Everything this view holds between visits, so returning never refetches. */
const state = {
  rows: null,
  loaded: false,
};

/** The dimensions, in the order they are shown, with the published spelling.
 *
 * `terms_served` is last deliberately: it is the one a reader is least likely
 * to have an expectation about, and the one most distorted by a single
 * dominant category -- 282 of 544 members in the 18th served exactly one term. */
const DIMENSIONS = [
  { key: "party", label: "Party" },
  { key: "state", label: "State" },
  { key: "terms_served", label: "Terms served" },
];

/** How many categories a dimension shows before the rest become a counted
 * group. Twelve, matching what `tools/show_composition.py` already prints, so
 * the page and the CLI do not disagree about the same aggregate. */
const SHOWN = 12;

/** The published rows for one term and dimension, largest first. */
function rowsFor(rows, term, dimension) {
  return rows
    .filter((r) => r.term === term && r.dimension === dimension)
    .slice()
    .sort((a, b) => b.members - a.members || String(a.category).localeCompare(String(b.category)));
}

/** The terms present in the aggregate, ascending. Derived, never typed: if a
 * 19th Lok Sabha is ever published this view shows it without an edit. */
function termsIn(rows) {
  return [...new Set(rows.map((r) => r.term))].sort((a, b) => a - b);
}

/** One term's total membership, as the aggregate itself states it. */
function totalFor(rows, term) {
  const row = rows.find((r) => r.term === term);
  return row ? row.total_members : null;
}

/**
 * One dimension, both terms, as paired horizontal bars plus the table.
 *
 * The table is the authoritative form (FR-121) and carries every category,
 * including the ones the chart groups -- so nothing is unreachable, only
 * undrawn.
 */
function renderDimension(rows, dimension) {
  const terms = termsIn(rows);
  const section = el("section", "composition-dimension chart-block");
  section.append(el("h3", null, dimension.label));

  const series = terms.map((t) => ({ name: `${t}th Lok Sabha`, term: t }));

  // Every category in either term, so a party present in one and absent from
  // the other still appears -- with a zero, which is a fact about that term.
  const categories = [
    ...new Set(terms.flatMap((t) => rowsFor(rows, t, dimension.key).map((r) => r.category))),
  ];
  const weight = (category) =>
    terms.reduce((n, t) => {
      const row = rowsFor(rows, t, dimension.key).find((r) => r.category === category);
      return n + (row ? row.members : 0);
    }, 0);
  categories.sort((a, b) => weight(b) - weight(a) || String(a).localeCompare(String(b)));

  const shown = categories.slice(0, SHOWN);
  const rest = categories.slice(SHOWN);

  const columns = shown.map((category) => ({
    label: String(category),
    parts: Object.fromEntries(
      terms.map((t) => {
        const row = rowsFor(rows, t, dimension.key).find((r) => r.category === category);
        return [`${t}th Lok Sabha`, row ? row.members : 0];
      }),
    ),
    totals: Object.fromEntries(terms.map((t) => [`${t}th Lok Sabha`, totalFor(rows, t)])),
  }));

  /* The LEGEND, which was missing and which FR-122 requires.
   *
   * Found by the driver's chart check rather than by reading this file: with
   * two bars per row and no legend, the only thing distinguishing the 17th
   * Lok Sabha from the 18th inside the chart was the FILL -- which is meaning
   * carried by colour alone, and is the one thing the chart contract forbids
   * outright. The table beneath has "17th Lok Sabha" and "18th Lok Sabha" as
   * column headers, so the information was reachable; it was not reachable
   * from the chart, which is the part a reader looks at first. */
  section.append(legend(series.map((s) => s.name)));
  section.append(
    horizontalBars(columns, series.map((s) => s.name), {
      title: `House composition by ${dimension.label.toLowerCase()}, by term`,
      description:
        "Paired bars, one per term, in the legend's order. Every figure is in " +
        "the table below, which carries all categories including the ones " +
        "grouped here.",
    }),
  );

  // What is NOT drawn, stated with its count (FR-103). Never silently dropped.
  if (rest.length > 0) {
    const carried = terms.map((t) => ({
      term: t,
      members: rest.reduce((n, category) => {
        const row = rowsFor(rows, t, dimension.key).find((r) => r.category === category);
        return n + (row ? row.members : 0);
      }, 0),
    }));
    const note = el("p", "composition-rest");
    note.append(
      document.createTextNode(`and ${count(rest.length)} further categories, carrying `),
    );
    carried.forEach((entry, index) => {
      if (index > 0) note.append(document.createTextNode(" and "));
      note.append(
        figure(entry.members, totalFor(rows, entry.term), {
          unit: "member",
          label: `members in the ${entry.term}th`,
        }),
      );
    });
    note.append(
      document.createTextNode(". Every one of them is in the table below, not withheld."),
    );
    section.append(note);
  }

  // The full table: every category, every term, reconciling to the published
  // total. This is the form a keyboard and a screen reader reach.
  const table = el("table", "composition-table");
  const caption = el("caption", "table-caption");
  caption.textContent =
    `Every published ${dimension.label.toLowerCase()} category, both terms, ` +
    "with each term's total membership as the denominator.";
  table.append(caption);
  const thead = el("thead");
  const headRow = el("tr");
  headRow.append(el("th", null, dimension.label));
  for (const t of terms) headRow.append(el("th", null, `${t}th Lok Sabha`));
  thead.append(headRow);
  table.append(thead);
  const tbody = el("tbody");
  for (const category of categories) {
    const tr = el("tr");
    tr.append(el("th", null, String(category)));
    for (const t of terms) {
      const row = rowsFor(rows, t, dimension.key).find((r) => r.category === category);
      tr.append(
        el("td", null, figureText(row ? row.members : 0, totalFor(rows, t), { label: "" }).trim()),
      );
    }
    tbody.append(tr);
  }
  table.append(tbody);
  const wrap = el("div", "table-wrap");
  wrap.append(table);
  section.append(wrap);

  return section;
}

/** The counting basis for this view, rendered from the published statement. */
function basisNote(rows) {
  const box = el("div", "basis");
  box.append(el("p", "basis-head", "How these figures were counted"));
  const unit = rows.length > 0 ? rows[0].counting_basis_unit : null;
  box.append(
    el(
      "p",
      "basis-text",
      `Counted in ${unit ?? "members"}: one member counted once per term they ` +
        "served, never twice in the same term. The denominator on every figure " +
        "is that term's total published membership, so the categories sum to it.",
    ),
  );
  return box;
}

async function render(host) {
  if (!state.loaded) {
    replaceChildren(host, el("p", "status", "Reading the composition aggregate…"));
    host.dataset.state = "loading";
    try {
      state.rows = await loadComposition();
      state.loaded = true;
    } catch (error) {
      renderUnavailable(
        host,
        "The House composition could not be read from the published files.",
        describe(error),
      );
      return;
    }
  }

  const rows = state.rows ?? [];
  if (rows.length === 0) {
    renderUnavailable(host, "The composition aggregate carries no rows.");
    return;
  }

  const frag = document.createDocumentFragment();
  const terms = termsIn(rows);
  const intro = el("p", "composition-intro");
  intro.append(document.createTextNode("Total membership published for "));
  terms.forEach((t, index) => {
    if (index > 0) intro.append(document.createTextNode(" and "));
    intro.append(
      figure(totalFor(rows, t), totalFor(rows, t), {
        unit: "member",
        label: `in the ${t}th Lok Sabha`,
      }),
    );
  });
  intro.append(
    document.createTextNode(
      ". No date appears in this view: every published term and session reads " +
        "“not stated”, so terms can be ordered and counted but not placed on a calendar.",
    ),
  );
  frag.append(intro);
  frag.append(basisNote(rows));

  for (const dimension of DIMENSIONS) {
    frag.append(renderDimension(rows, dimension));
  }

  replaceChildren(host, frag);
  host.dataset.state = "ready";
}

/* ---------------------------------------------------------------------- */
/* The view's entry point, called by the router in app.js                 */
/* ---------------------------------------------------------------------- */

export async function mount(doc = document) {
  const host = doc.getElementById("composition-result");
  if (host) await render(host);
}
