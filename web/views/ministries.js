/* The ministry views: one ministry's profile, two compared, and the whole
 * House's question load across the covered sessions. T133.
 *
 * MOVED here from `app.js`, where all three lived alongside every other view
 * in a 2,332-line module. Nothing in this file was rewritten in the move --
 * the diff that created it is a cut and a paste, so a behaviour change here
 * would be a behaviour change somebody made on purpose.
 *
 * Loaded by `import()` on a reader's FIRST USE of any of the three views
 * (FR-128). The three share one module and one pair of files, so opening any
 * of them pays for all three and the other two then cost nothing.
 */

import { legend, stackedColumns } from "../lib/chart.js";
import { longSessionLabel } from "../lib/coverage.js";
import { fetchMinistries, fetchMinistryProfile } from "../lib/fetch.js";
import { NOT_STATED, count, isMissing, percent, sessionLabel, stated } from "../lib/format.js";
import { figure, figureText } from "../lib/marks.js";
import {
  STATUS_FIELDS,
  basisFor,
  compare,
  profileMinistries,
  profileSessions,
  questionBucket,
  selectSpan,
  share,
  spanChange,
  spanTotals,
  statusField,
} from "../lib/profile.js";
import {
  describe,
  el,
  fact,
  renderUnavailable,
  replaceChildren,
  views,
} from "../lib/shared.js";
import {
  basisBlock,
  changeText,
  labelledSelect,
  mixTable,
  statusStrip,
} from "../lib/viewkit.js";

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
  // (d) A pre-selection is a choice the page made, not one the reader made.
  // Say so, or the first ministry reads as a recommendation.
  picker.append(
    el(
      "p",
      "picker-note",
      "A ministry is pre-selected so the view has something to show: it is the " +
        "first of " +
        `${count(ministries.length)} by name, and the span is every published session. ` +
        "It is not a recommendation and nothing is ranked. Change any of the three above.",
    ),
  );

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

  // (d) No pre-selection here: a comparison the page chose would put two
  // ministries side by side as though someone had asked the question.
  const NONE = "";
  const choices = [[NONE, "Choose a ministry…"], ...ministries];
  const a = labelledSelect("compare-a", "First ministry", choices, NONE);
  const b = labelledSelect("compare-b", "Second ministry", choices, NONE);
  const from = labelledSelect("compare-from", "From session", sessions, first);
  const to = labelledSelect("compare-to", "To session", sessions, last);

  const form = el("div", "picker");
  form.append(a.wrap, b.wrap, from.wrap, to.wrap);
  replaceChildren(picker, form);
  picker.append(
    el(
      "p",
      "picker-note",
      "Choose two ministries to compare. Nothing is pre-selected: a pair the page " +
        "picked would read as a comparison someone had asked for.",
    ),
  );

  const draw = () => {
    if (!a.select.value || !b.select.value) {
      const waiting = el("p", "status", "Choose two ministries above to compare them.");
      replaceChildren(result, waiting);
      result.dataset.state = "empty";
      return;
    }
    if (a.select.value === b.select.value) {
      replaceChildren(
        result,
        el("p", "status", "Those are the same ministry. Choose a different second one."),
      );
      result.dataset.state = "empty";
      return;
    }
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

  if (ministries.status === "fulfilled") {
    views.ministryNames = new Map(ministries.value.map((m) => [m.ministry_id, m]));
  }
  /* And if THIS view's fetch failed while the search view had already loaded
   * the names, the map is left as it was rather than blanked. `fetchMinistries`
   * is memoised, so the two views share one request either way. */

  /* The search and seat views used to be built HERE, by this function, which
   * is why it was called `bootViews` rather than something about ministries.
   * In the single-scroll page every view had to exist on load, so one boot
   * sequence built all four and the comment that stood here explained why a
   * failed ministry-profile download must not take the other two off the page.
   *
   * The router makes that structurally impossible instead of carefully
   * handled: each view is mounted by its own module when a reader opens it, so
   * this one cannot take another down and does not need to be careful not to.
   * The two calls are removed rather than moved -- `app.js` owns the view map
   * now, and nothing here knows another view exists.
   */

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
  // `views.ministryNames` is already set above, before the early return.
  views.ministries = profileMinistries(
    views.rows,
    ministries.status === "fulfilled" ? ministries.value : [],
  );
  views.ready = true;

  buildProfileView(doc);
  buildCompareView(doc);
}

/* ---------------------------------------------------------------------- */
/* The view's entry point, called by the router in app.js                 */
/* ---------------------------------------------------------------------- */

/** Build all three ministry views and load the pair of files they share. */
export async function mount(doc = document) {
  await bootViews(doc);
}
