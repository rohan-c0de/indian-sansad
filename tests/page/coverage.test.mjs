/* Coverage-statement logic. The claim the page leads with is DERIVED. */

import assert from "node:assert/strict";
import { test } from "node:test";

import {
  NOT_APPLICABLE,
  coveredRows,
  ZERO_SITTING_DAYS_FLAG,
  hasZeroSittingDays,
  housesClaim,
  housesNotCovered,
  housesWithData,
  longSessionLabel,
  perSittingDay,
  sessionRows,
} from "../../web/lib/coverage.js";

/** The two rows the dataset publishes today, trimmed to what is read. */
const LOK = { house: "lok-sabha", total_questions: 95268, sessions_covered: [] };
const RAJYA = {
  house: "rajya-sabha",
  total_questions: 0,
  sessions_covered: [],
  unobtainable_reason: "route returns HTTP 403; cause unverified",
};

test("today the derived claim is the same words the literal was", () => {
  assert.equal(housesClaim([LOK, RAJYA]), "Lok Sabha only");
  assert.deepEqual(housesWithData([LOK, RAJYA]), ["lok-sabha"]);
});

test("a House with a row but no questions is NOT covered, and says why", () => {
  const absent = housesNotCovered([LOK, RAJYA]);
  assert.equal(absent.length, 1);
  assert.equal(absent[0].name, "Rajya Sabha");
  assert.match(absent[0].reason, /403/);
});

test("when a second House acquires data the claim changes by itself", () => {
  // The whole point of deriving it. Nobody edits a string for this to happen.
  const withRajya = { ...RAJYA, total_questions: 41234 };
  assert.equal(housesClaim([LOK, withRajya]), "Lok Sabha and Rajya Sabha");
  assert.deepEqual(housesNotCovered([LOK, withRajya]), []);
  assert.deepEqual(housesWithData([LOK, withRajya]).sort(), ["lok-sabha", "rajya-sabha"]);
});

test("three or more Houses read as a list", () => {
  const rows = [
    LOK,
    { house: "rajya-sabha", total_questions: 1 },
    { house: "state-assembly", total_questions: 1 },
  ];
  assert.equal(housesClaim(rows), "Lok Sabha, Rajya Sabha and State Assembly");
});

test("no House with data is said plainly, not as an empty claim", () => {
  assert.equal(housesClaim([{ ...LOK, total_questions: 0 }, RAJYA]), "No House is covered");
  assert.equal(housesClaim([]), "No House is covered");
});

/* ---------------------------------------------------------------------- */
/* Zero sitting days                                                      */
/* ---------------------------------------------------------------------- */

test("zero sitting days is a published value, not a missing one", () => {
  assert.equal(hasZeroSittingDays({ sitting_days: 0 }), true);
  assert.equal(hasZeroSittingDays({ sitting_days: 28 }), false);
  // Number(null) is 0, so a naive check reports "not stated" as zero -- a
  // different claim about the record, and a false one. Caught by this test.
  assert.equal(hasZeroSittingDays({ sitting_days: null }), false);
  assert.equal(hasZeroSittingDays({ sitting_days: "not stated" }), false);
  assert.equal(hasZeroSittingDays({}), false);
  assert.equal(hasZeroSittingDays(null), false);
});

test("a per-sitting-day figure is n/a when the denominator is zero", () => {
  // coverage.jsonl declares this case: "A sitting-day denominator of 0 would
  // divide by zero in any per-sitting-day rate."
  assert.equal(perSittingDay(4500, 0), NOT_APPLICABLE);
  assert.equal(perSittingDay(4500, null), NOT_APPLICABLE);
  assert.equal(perSittingDay(null, 10), NOT_APPLICABLE);
  assert.equal(perSittingDay(100, 10), 10);
  // Never Infinity, never 0, never a dropped row -- each is a different wrong
  // answer and only n/a says what happened.
  assert.notEqual(perSittingDay(4500, 0), Infinity);
  assert.notEqual(perSittingDay(4500, 0), 0);
});

/* ---------------------------------------------------------------------- */
/* Session rows                                                           */
/* ---------------------------------------------------------------------- */

const SESSION_RECORDS = [
  { house: "lok-sabha", term: 17, number: 2, start_date: "not stated", end_date: null, sitting_days: 20 },
  { house: "lok-sabha", term: 18, number: 8, start_date: "not stated", end_date: null, sitting_days: 0 },
  { house: "lok-sabha", term: 17, number: 10, start_date: "not stated", end_date: null, sitting_days: 13 },
];

test("session rows are ordered by (term, number) and carry the zero flag", () => {
  const rows = sessionRows(
    { sessions_covered: ["lok-sabha/18/8", "lok-sabha/17/10", "lok-sabha/17/2"] },
    SESSION_RECORDS,
  );
  assert.deepEqual(rows.map((r) => `${r.term}/${r.number}`), ["17/2", "17/10", "18/8"]);
  assert.equal(rows[0].sittingDays, 20);
  assert.equal(rows[2].zeroSittingDays, true);
  assert.equal(rows[0].zeroSittingDays, false);
  assert.match(ZERO_SITTING_DAYS_FLAG, /0 sitting days as published/);
});

test("a covered session with no reference record still produces a row", () => {
  // Dropping it would make the count on screen disagree with the count the
  // record publishes.
  const rows = sessionRows({ sessions_covered: ["lok-sabha/17/2", "lok-sabha/99/1"] }, SESSION_RECORDS);
  assert.equal(rows.length, 2);
  assert.equal(rows[1].record, null);
  assert.equal(rows[1].sittingDays, null);
  assert.equal(rows[1].zeroSittingDays, false);
});

test("session labels read in long form", () => {
  assert.equal(longSessionLabel({ house: "lok-sabha", term: 17, number: 4 }), "17th Lok Sabha · Session 4");
  assert.equal(longSessionLabel({ house: "lok-sabha", term: 18, number: 1 }), "18th Lok Sabha · Session 1");
  assert.equal(longSessionLabel({ house: "rajya-sabha", term: 1, number: 2 }), "1st Rajya Sabha · Session 2");
  assert.equal(longSessionLabel({ house: "lok-sabha", term: 3, number: 1 }), "3rd Lok Sabha · Session 1");
});

test("the rows whose figures are shown are derived, largest first", () => {
  const withRajya = { ...RAJYA, total_questions: 41234 };
  assert.deepEqual(coveredRows([withRajya, LOK]).map((r) => r.house), [
    "lok-sabha",
    "rajya-sabha",
  ]);
  assert.deepEqual(coveredRows([LOK, RAJYA]).map((r) => r.house), ["lok-sabha"]);
  assert.deepEqual(coveredRows([RAJYA]), []);
});
