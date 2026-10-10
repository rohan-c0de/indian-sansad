/* The formatting rules the owner decided, as tests. */

import assert from "node:assert/strict";
import { test } from "node:test";

import {
  NOT_STATED,
  count,
  isMissing,
  isoDate,
  orderSessions,
  ordinal,
  percent,
  sessionLabel,
  stated,
} from "../../web/lib/format.js";

test("absent, null, blank and the literal all render as not stated", () => {
  for (const value of [null, undefined, "", "   ", "not stated", "NOT STATED", []]) {
    assert.equal(isMissing(value), true, `expected ${JSON.stringify(value)} missing`);
    assert.equal(stated(value), NOT_STATED);
  }
  assert.equal(stated("Lok Sabha"), "Lok Sabha");
  assert.equal(stated(0), "0", "zero is a value, not an absence");
  assert.equal(isMissing(0), false);
  assert.equal(isMissing(false), false);
});

test("an ISO date is formatted without going through Date()", () => {
  // Date() would apply the viewer's timezone and could shift the day.
  assert.equal(isoDate("2019-06-21"), "21 Jun 2019");
  assert.equal(isoDate("2026-08-12"), "12 Aug 2026");
  assert.equal(isoDate("2026-12-01"), "1 Dec 2026");
  // Anything that is not an ISO date is not guessed at.
  assert.equal(isoDate("21.06.2019"), NOT_STATED);
  assert.equal(isoDate("2026-13-01"), NOT_STATED);
  assert.equal(isoDate(null), NOT_STATED);
  assert.equal(isoDate("not stated"), NOT_STATED);
});

test("counts and rates", () => {
  assert.equal(count(95268), "95,268");
  assert.equal(count(0), "0");
  assert.equal(count(null), NOT_STATED);
  assert.equal(percent(0.947831), "94.78%");
  assert.equal(percent(0.95, { decimals: 0 }), "95%");
  assert.equal(percent(null), NOT_STATED);
});

test("ordinals", () => {
  assert.deepEqual([17, 18, 1, 2, 3, 11, 12, 13, 21].map(ordinal), [
    "17th", "18th", "1st", "2nd", "3rd", "11th", "12th", "13th", "21st",
  ]);
});

test("sessions order by (term, number), not as the record lists them", () => {
  // Exactly the order coverage.jsonl publishes -- it is sorted as STRINGS, so
  // session 10 comes before session 2. Printing that order would be wrong.
  const published = [
    "lok-sabha/17/1", "lok-sabha/17/10", "lok-sabha/17/11", "lok-sabha/17/12",
    "lok-sabha/17/14", "lok-sabha/17/15", "lok-sabha/17/2", "lok-sabha/17/3",
    "lok-sabha/18/2", "lok-sabha/18/8",
  ];
  const ordered = orderSessions(published).map((s) => `${s.term}/${s.number}`);
  assert.deepEqual(ordered, [
    "17/1", "17/2", "17/3", "17/10", "17/11", "17/12", "17/14", "17/15",
    "18/2", "18/8",
  ]);

  const desc = orderSessions(published, { direction: "desc" }).map(
    (s) => `${s.term}/${s.number}`,
  );
  assert.deepEqual(desc.slice(0, 3), ["18/8", "18/2", "17/15"]);
});

test("an unparseable session id is kept and placed last, never dropped", () => {
  const ordered = orderSessions(["lok-sabha/18/2", "nonsense", "lok-sabha/17/1"]);
  assert.equal(ordered.length, 3);
  assert.equal(ordered[2].sessionId, "nonsense");
  assert.equal(sessionLabel(ordered[2]), "nonsense");
  assert.equal(sessionLabel(ordered[0]), "17th LS · Session 1");
});
