/* T078/T080 logic. The sum invariant is the one that must never slip. */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import {
  STATUS_FIELDS,
  StatusSumMismatch,
  basisFor,
  change,
  compare,
  profileMinistries,
  profileSessions,
  selectSpan,
  share,
  spanChange,
  spanTotals,
  statusCounts,
  typesIn,
} from "../../web/lib/profile.js";

const row = (ministry, session, q, mix, status) => ({
  ministry_id: ministry,
  session,
  questions: q,
  question_type_mix: mix,
  counting_basis_unit: "question",
  basis_version: "1",
  ...status,
});

const ROWS = [
  row("a", "lok-sabha/17/2", 100, { STARRED: 10, UNSTARRED: 90 },
      { fully_linked: 90, partly_linked: 6, not_linked: 4, ambiguous: 0 }),
  row("a", "lok-sabha/17/10", 150, { STARRED: 30, UNSTARRED: 120 },
      { fully_linked: 140, partly_linked: 5, not_linked: 3, ambiguous: 2 }),
  row("a", "lok-sabha/18/2", 80, { STARRED: 8, UNSTARRED: 72 },
      { fully_linked: 80, partly_linked: 0, not_linked: 0, ambiguous: 0 }),
  row("b", "lok-sabha/17/2", 40, { STARRED: 4, UNSTARRED: 36 },
      { fully_linked: 38, partly_linked: 1, not_linked: 1, ambiguous: 0 }),
  row("b", "lok-sabha/18/2", 60, { UNSTARRED: 60 },
      { fully_linked: 55, partly_linked: 3, not_linked: 2, ambiguous: 0 }),
];

/* ---------------------------------------------------------------------- */
/* The sum invariant                                                      */
/* ---------------------------------------------------------------------- */

test("the four status counts account for every question", () => {
  const { counts, sum, flagged } = statusCounts(ROWS[1]);
  assert.equal(sum, 150);
  assert.equal(counts.fully_linked, 140);
  assert.equal(flagged, 10, "partly + not + ambiguous are all flagged");
  assert.deepEqual(STATUS_FIELDS.map((f) => f.key), [
    "fully_linked", "partly_linked", "not_linked", "ambiguous",
  ]);
});

test("a split that does not account for every question THROWS", () => {
  // Not a silent render. A reader could subtract and find an unlabelled
  // bucket, which is worse than an error.
  const broken = { ...ROWS[0], not_linked: 3 };
  assert.throws(() => statusCounts(broken), StatusSumMismatch);
  assert.throws(() => spanTotals([{ questions: 10, typeMix: {}, status: { fully_linked: 1 }, flagged: 0 }]),
    StatusSumMismatch);
});

test("the invariant holds over the WHOLE published aggregate", () => {
  // The fixtures above are hand-made; this is the real 1,146 rows.
  let rows;
  try {
    rows = readFileSync("data/published/aggregates/ministry-profile.jsonl", "utf8")
      .split("\n").filter((l) => l.trim()).map((l) => JSON.parse(l));
  } catch {
    return; // not built -- NOT AUDITED; the pytest suite reports this scope
  }
  assert.ok(rows.length > 1000, `only ${rows.length} rows`);
  let questions = 0;
  for (const r of rows) {
    questions += statusCounts(r).sum;          // throws if any row fails
  }
  assert.ok(questions > 0);
});

/* ---------------------------------------------------------------------- */
/* Span selection                                                         */
/* ---------------------------------------------------------------------- */

test("sessions and ministries come out ordered", () => {
  assert.deepEqual(profileSessions(ROWS).map((s) => `${s.term}/${s.number}`),
    ["17/2", "17/10", "18/2"]);
  const ministries = profileMinistries(ROWS, [
    { ministry_id: "a", canonical_name: "Zed Ministry", former_names: ["Old Zed"] },
    { ministry_id: "b", canonical_name: "Alpha Ministry", former_names: [] },
  ]);
  assert.deepEqual(ministries.map((m) => m.name), ["Alpha Ministry", "Zed Ministry"]);
  // Rename DATES are not published, so former names carry none.
  assert.deepEqual(ministries[1].formerNames, ["Old Zed"]);
});

test("a span is inclusive and order-independent", () => {
  const span = selectSpan(ROWS, {
    ministryId: "a", fromSession: "lok-sabha/18/2", toSession: "lok-sabha/17/2",
  });
  assert.deepEqual(span.map((e) => e.session.sessionId),
    ["lok-sabha/17/2", "lok-sabha/17/10", "lok-sabha/18/2"]);
  assert.deepEqual(span.map((e) => e.questions), [100, 150, 80]);
});

test("a session with no row for this ministry is an explicit zero, not a skip", () => {
  // A gap in the series is information. A chart that closed it would imply a
  // continuity that is not in the record.
  const span = selectSpan(ROWS, {
    ministryId: "b", fromSession: "lok-sabha/17/2", toSession: "lok-sabha/18/2",
  });
  assert.equal(span.length, 3);
  assert.equal(span[1].session.sessionId, "lok-sabha/17/10");
  assert.equal(span[1].present, false);
  assert.equal(span[1].questions, 0);
  assert.equal(span[1].status.fully_linked, 0);
});

test("one session is a valid span", () => {
  const span = selectSpan(ROWS, {
    ministryId: "a", fromSession: "lok-sabha/17/2", toSession: "lok-sabha/17/2",
  });
  assert.equal(span.length, 1);
  assert.equal(spanChange(span).singleSession, true);
  assert.equal(spanChange(span).questions.absolute, 0);
});

/* ---------------------------------------------------------------------- */
/* Totals and change                                                      */
/* ---------------------------------------------------------------------- */

test("span totals add up and keep the invariant", () => {
  const span = selectSpan(ROWS, {
    ministryId: "a", fromSession: "lok-sabha/17/2", toSession: "lok-sabha/18/2",
  });
  const totals = spanTotals(span);
  assert.equal(totals.questions, 330);
  assert.deepEqual(totals.typeMix, { STARRED: 48, UNSTARRED: 282 });
  assert.equal(totals.status.fully_linked, 310);
  assert.equal(totals.flagged, 20);
  assert.equal(
    STATUS_FIELDS.reduce((a, f) => a + totals.status[f.key], 0),
    totals.questions,
  );
  assert.deepEqual(typesIn(span), ["STARRED", "UNSTARRED"]);
});

test("change is first selected session against last, absolute and percent", () => {
  const span = selectSpan(ROWS, {
    ministryId: "a", fromSession: "lok-sabha/17/2", toSession: "lok-sabha/18/2",
  });
  const c = spanChange(span);
  assert.equal(c.firstSession.sessionId, "lok-sabha/17/2");
  assert.equal(c.lastSession.sessionId, "lok-sabha/18/2");
  assert.equal(c.questions.absolute, -20);
  assert.equal(Math.round(c.questions.percent), -20);
  const starred = c.byType.find((t) => t.type === "STARRED");
  assert.equal(starred.count.absolute, -2);
  assert.equal(Math.round(starred.shareFirst), 10);
  assert.equal(Math.round(starred.shareLast), 10);
});

test("a percent change from zero is undefined, not infinite and not 100%", () => {
  assert.equal(change(0, 50).percent, null);
  assert.equal(change(0, 50).absolute, 50);
  assert.equal(change(50, 0).percent, -100);
  assert.equal(share(1, 0), null);
  assert.equal(share(1, 4), 25);
});

/* ---------------------------------------------------------------------- */
/* Basis and comparison                                                   */
/* ---------------------------------------------------------------------- */

test("the basis is looked up by the unit the rows name, never retyped", () => {
  const basis = [
    { unit: "question", basis_version: "1", counting_basis: "What is counted: QUESTIONS..." },
    { unit: "member", basis_version: "1", counting_basis: "What is counted: MEMBERS..." },
  ];
  const span = selectSpan(ROWS, {
    ministryId: "a", fromSession: "lok-sabha/17/2", toSession: "lok-sabha/18/2",
  });
  assert.equal(basisFor(span, basis).unit, "question");
  assert.equal(basisFor(span, []), null);
});

test("comparison uses the same span and the same basis for both", () => {
  const result = compare(ROWS, {
    ministryIds: ["a", "b"],
    fromSession: "lok-sabha/17/2",
    toSession: "lok-sabha/18/2",
  });
  assert.equal(result.sides.length, 2);
  assert.equal(result.sides[0].totals.questions, 330);
  assert.equal(result.sides[1].totals.questions, 100);
  // Both sides cover the SAME sessions, including ones where a ministry has
  // no row -- otherwise the two columns would be counting different spans.
  assert.deepEqual(
    result.sides[0].span.map((e) => e.session.sessionId),
    result.sides[1].span.map((e) => e.session.sessionId),
  );
  assert.deepEqual(result.types, ["STARRED", "UNSTARRED"]);
});
