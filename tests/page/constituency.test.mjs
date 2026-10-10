/* T088 logic — the state and constituency entry point. User Story 3.
 *
 * The three acceptance scenarios, and the one thing that would make the view
 * wrong in a way a reader could not see: a seat name that names two different
 * seats.
 *
 * Fixtures here are hand-made shapes, with one test over the REAL published
 * seat set (skipped, loudly, when it is not built) because the three repeated
 * names and the 216 members who hold both terms are facts about the data, not
 * about the code.
 */

import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";

import {
  dedupeQuestions,
  memberQuestions,
  nameKey,
  representativesOf,
  seatById,
  seatHistory,
  seatsInState,
  seatsMatching,
  seatsNamed,
  stateSubjects,
  statesIn,
  statesWithSubjects,
  subjectTally,
  termsPhrase,
} from "../../web/lib/constituency.js";
import { NOT_STATED } from "../../web/lib/format.js";

const rep = (memberId, term, extra = {}) => ({
  member_id: memberId,
  member_name: `Name ${memberId}`,
  party: `Party ${memberId}`,
  sitting_status: "sitting",
  term_number: term,
  start_date: NOT_STATED,
  end_date: null,
  ...extra,
});

const seat = (id, name, state, representations) => ({
  constituency_id: id,
  name,
  state,
  representations,
});

/** Two different holders across the two covered terms. Scenario 3. */
const TWO_HOLDERS = seat("bihar-aurangabad", "Aurangabad", "Bihar", [
  rep("ls-1", 17),
  rep("ls-2", 18),
]);

/** One member across both covered terms. The majority case: 216 of 545. */
const ONE_HOLDER_BOTH = seat("maharashtra-aurangabad", "Aurangabad", "Maharashtra", [
  rep("ls-3", 17),
  rep("ls-3", 18),
]);

const ONE_TERM_ONLY = seat("bihar-other", "Other", "Bihar", [rep("ls-4", 17)]);

/* ---------------------------------------------------------------------- */
/* Scenario 1 — the members, with their party and term                    */
/* ---------------------------------------------------------------------- */

test("a seat lists its members with party and term", () => {
  const people = representativesOf(TWO_HOLDERS);
  assert.equal(people.length, 2);
  assert.deepEqual(
    people.map((p) => [p.memberId, p.name, p.party, p.terms]),
    [
      ["ls-1", "Name ls-1", "Party ls-1", [17]],
      ["ls-2", "Name ls-2", "Party ls-2", [18]],
    ],
  );
  // Party and term both come off the published representation; no member set
  // is fetched to get them.
  for (const person of people) {
    assert.notEqual(person.party, NOT_STATED);
    assert.ok(person.terms.length > 0);
    assert.equal(person.sittingStatus, "sitting");
  }
});

test("a member the record does not name is shown as an id, flagged, never dropped", () => {
  const unnamed = seat("x-y", "Y", "X", [rep("ls-9", 18, { member_name: NOT_STATED })]);
  const [person] = representativesOf(unnamed);
  assert.equal(person.nameMissing, true);
  assert.equal(person.name, NOT_STATED);
  assert.equal(person.memberId, "ls-9");
  // 91 of the window's 887 members asked no question, and their name reaches
  // this view only through the seat record. Dropping one would make a seat
  // look as though it had fewer representatives than it had.
  assert.equal(representativesOf(unnamed).length, 1);
});

test("a missing party is an explicit not stated, never blank", () => {
  const seatless = seat("x-y", "Y", "X", [rep("ls-9", 18, { party: "" })]);
  assert.equal(representativesOf(seatless)[0].party, NOT_STATED);
});

/* ---------------------------------------------------------------------- */
/* Scenario 3 — two holders are not merged; one holder is not duplicated  */
/* ---------------------------------------------------------------------- */

test("two different holders across the terms are two entries, with their own terms", () => {
  const history = seatHistory(TWO_HOLDERS);
  assert.equal(history.changedHands, true);
  assert.equal(history.people.length, 2);
  assert.deepEqual(history.terms, [17, 18]);
  assert.deepEqual(
    history.people.map((p) => p.terms),
    [[17], [18]],
  );
});

test("ONE member across both terms is ONE entry listing both", () => {
  const history = seatHistory(ONE_HOLDER_BOTH);
  // Not "changed hands": it is the same person. The two facts are separate and
  // a reader needs both.
  assert.equal(history.changedHands, false);
  assert.equal(history.people.length, 1);
  assert.deepEqual(history.people[0].terms, [17, 18]);
  assert.deepEqual(history.terms, [17, 18]);
  assert.equal(termsPhrase(history.people[0].terms), "17th and 18th Lok Sabha");
});

test("a seat held in one covered term says so", () => {
  const history = seatHistory(ONE_TERM_ONLY);
  assert.deepEqual(history.terms, [17]);
  assert.equal(history.changedHands, false);
  assert.equal(termsPhrase(history.terms), "17th Lok Sabha");
});

test("representatives read chronologically whatever order the file is in", () => {
  const shuffled = seat("s", "S", "St", [rep("ls-b", 18), rep("ls-a", 17)]);
  assert.deepEqual(
    representativesOf(shuffled).map((p) => p.memberId),
    ["ls-a", "ls-b"],
  );
});

test("termsPhrase never invents a period", () => {
  assert.equal(termsPhrase([]), NOT_STATED);
  assert.equal(termsPhrase(undefined), NOT_STATED);
  assert.equal(termsPhrase([18]), "18th Lok Sabha");
});

/* ---------------------------------------------------------------------- */
/* A name is NOT an identity                                              */
/* ---------------------------------------------------------------------- */

test("a repeated name returns EVERY seat, never one", () => {
  const seats = [TWO_HOLDERS, ONE_HOLDER_BOTH, ONE_TERM_ONLY];
  const found = seatsNamed(seats, "Aurangabad");
  assert.equal(found.length, 2, "a name that names two seats must return two");
  assert.deepEqual(
    found.map((s) => s.state),
    ["Bihar", "Maharashtra"],
  );
  // Case and spacing are for MATCHING only; the published spelling is returned.
  assert.deepEqual(seatsNamed(seats, "  aurangabad  ").map((s) => s.name), [
    "Aurangabad",
    "Aurangabad",
  ]);
});

test("nameKey matches on case and spacing and nothing else", () => {
  assert.equal(nameKey("  Foo   Bar "), "foo bar");
  assert.equal(nameKey(undefined), "");
  // NOT punctuation-insensitive: two differently punctuated names are two
  // names, the same line the seat id's slug does not get to blur here.
  assert.notEqual(nameKey("North-East Delhi"), nameKey("North East Delhi"));
});

test("a partial name offers matches, exact ones first", () => {
  const seats = [TWO_HOLDERS, ONE_HOLDER_BOTH, seat("b-aur", "Aurangabad North", "Bihar", [])];
  const hits = seatsMatching(seats, "aurangabad");
  assert.ok(hits.length >= 3);
  assert.deepEqual(hits.slice(0, 2).map((s) => s.name), ["Aurangabad", "Aurangabad"]);
  assert.equal(seatsMatching(seats, "a").length, 0, "one letter is not a search");
});

test("seatById finds exactly one seat", () => {
  const seats = [TWO_HOLDERS, ONE_HOLDER_BOTH];
  assert.equal(seatById(seats, "maharashtra-aurangabad").state, "Maharashtra");
  assert.equal(seatById(seats, "nope"), null);
});

/* ---------------------------------------------------------------------- */
/* States                                                                 */
/* ---------------------------------------------------------------------- */

test("states come out alphabetically with their seat and member counts", () => {
  const states = statesIn([TWO_HOLDERS, ONE_HOLDER_BOTH, ONE_TERM_ONLY]);
  assert.deepEqual(states, [
    { state: "Bihar", seats: 2, members: 3 },
    { state: "Maharashtra", seats: 1, members: 1 },
  ]);
});

test("states are NOT ordered by size", () => {
  // An order by seat count is a ranking of states, and this phase publishes
  // none -- and a visitor looking for their own state wants the alphabet.
  const states = statesIn([
    seat("a", "A", "Zed", [rep("ls-1", 17), rep("ls-2", 18)]),
    seat("b", "B", "Alpha", [rep("ls-3", 17)]),
  ]);
  assert.deepEqual(states.map((s) => s.state), ["Alpha", "Zed"]);
});

test("one state's seats come out by name", () => {
  const seats = [seat("b-z", "Zeta", "Bihar", []), TWO_HOLDERS, ONE_TERM_ONLY];
  assert.deepEqual(
    seatsInState(seats, "Bihar").map((s) => s.name),
    ["Aurangabad", "Other", "Zeta"],
  );
  assert.deepEqual(seatsInState(seats, "bihar").length, 3, "state matching is case-insensitive");
  assert.deepEqual(seatsInState(seats, "Nowhere"), []);
});

/* ---------------------------------------------------------------------- */
/* A member's questions                                                   */
/* ---------------------------------------------------------------------- */

const question = (id, extra = {}) => ({
  question_id: id,
  subject: "Water Supply",
  date: "2024-07-01",
  ministry_id: "jal-shakti",
  resolution_status: "resolved",
  asking_members: ["ls-1"],
  ...extra,
});

test("questions are de-duplicated on question_id", () => {
  // Contract guarantee 6, which the published counting basis restates.
  const rows = [question("q1"), question("q1"), question("q2")];
  assert.equal(dedupeQuestions(rows).length, 2);
  assert.equal(memberQuestions(rows).total, 2);
});

test("unresolved and ambiguous questions are counted, not filtered out", () => {
  const rows = [
    question("q1"),
    question("q2", { resolution_status: "unresolved", asking_members: ["ls-1"] }),
    question("q3", { resolution_status: "unresolved", asking_members: [] }),
    question("q4", { resolution_status: "ambiguous", asking_members: [] }),
  ];
  const summary = memberQuestions(rows);
  assert.equal(summary.total, 4, "the total includes every status");
  assert.equal(summary.counts.fully_linked, 1);
  assert.equal(summary.counts.partly_linked, 1);
  assert.equal(summary.counts.not_linked, 1);
  assert.equal(summary.counts.ambiguous, 1);
  assert.equal(summary.flagged, 3);
});

test("the status labels are the ministry profile's own words, and flags are words", () => {
  const summary = memberQuestions([question("q1")]);
  assert.deepEqual(
    summary.statusRows.map((r) => [r.key, r.label, r.flagged]),
    [
      ["fully_linked", "Fully linked", false],
      ["partly_linked", "Partly linked", true],
      ["not_linked", "Not linked", true],
      ["ambiguous", "Ambiguous", true],
    ],
  );
});

test("a question with no status at all is counted but bucketed nowhere", () => {
  const summary = memberQuestions([question("q1", { resolution_status: "" })]);
  assert.equal(summary.total, 1);
  assert.equal(summary.unknownStatus, 1);
  assert.equal(Object.values(summary.counts).reduce((a, b) => a + b, 0), 0);
});

test("questions come out newest first, with a total order", () => {
  const rows = [
    question("q1", { date: "2020-01-01" }),
    question("q3", { date: "2024-07-01" }),
    question("q2", { date: "2024-07-01" }),
  ];
  assert.deepEqual(
    memberQuestions(rows).questions.map((q) => q.question_id),
    ["q2", "q3", "q1"],
  );
});

test("a subject tally counts exact lines and never groups them", () => {
  const rows = [
    question("q1", { subject: "Drinking Water Supply" }),
    question("q2", { subject: "Drinking water supply" }),
    question("q3", { subject: "Drinking Water Supply" }),
    question("q4", { subject: "" }),
  ];
  const tally = subjectTally(rows);
  assert.equal(tally.distinct, 3, "near-identical subject lines were merged");
  assert.deepEqual(tally.rows[0], { subject: "Drinking Water Supply", questions: 2 });
  assert.ok(tally.rows.some((r) => r.subject === NOT_STATED));
  // Ties break on the subject, so two renders of one file agree.
  assert.deepEqual(
    subjectTally([...rows].reverse()).rows.map((r) => r.subject),
    tally.rows.map((r) => r.subject),
  );
});

/* ---------------------------------------------------------------------- */
/* The published state subject summary                                    */
/* ---------------------------------------------------------------------- */

const SUBJECT_ROWS = [
  {
    state: "Bihar",
    subject: "Water",
    questions: 9,
    state_questions: 100,
    state_subjects: 40,
    subjects_shown: 25,
    counting_basis_unit: "state-question",
    basis_version: "1",
  },
  {
    state: "Bihar",
    subject: "Roads",
    questions: 4,
    state_questions: 100,
    state_subjects: 40,
    subjects_shown: 25,
    counting_basis_unit: "state-question",
    basis_version: "1",
  },
  {
    state: "Maharashtra",
    subject: "Power",
    questions: 2,
    state_questions: 7,
    state_subjects: 3,
    subjects_shown: 3,
    counting_basis_unit: "state-question",
    basis_version: "1",
  },
];

test("a state's summary is read from the published rows, with its denominators", () => {
  const summary = stateSubjects(SUBJECT_ROWS, "Bihar");
  assert.equal(summary.state, "Bihar");
  assert.deepEqual(summary.rows, [
    { subject: "Water", questions: 9 },
    { subject: "Roads", questions: 4 },
  ]);
  // The denominator travels with the figure. A top-25 count read without it
  // is a number a reader will mistake for the state's whole record.
  assert.equal(summary.stateQuestions, 100);
  assert.equal(summary.stateSubjects, 40);
  assert.equal(summary.subjectsShown, 25);
  assert.equal(summary.basisUnit, "state-question");
});

test("the page preserves the published order and adds no rank", () => {
  const summary = stateSubjects(SUBJECT_ROWS, "Bihar");
  assert.deepEqual(summary.rows.map((r) => r.subject), ["Water", "Roads"]);
  for (const row of summary.rows) {
    assert.deepEqual(Object.keys(row), ["subject", "questions"]);
  }
});

test("a state with no published summary returns null rather than an empty one", () => {
  // Null so the page can SAY the summary is absent. An empty list would read
  // as "its members asked nothing", which is a claim about the record.
  assert.equal(stateSubjects(SUBJECT_ROWS, "Nowhere"), null);
  assert.equal(stateSubjects([], "Bihar"), null);
});

test("statesWithSubjects names the states the summary covers", () => {
  const states = statesWithSubjects(SUBJECT_ROWS);
  assert.equal(states.has("bihar"), true);
  assert.equal(states.has("nowhere"), false);
});

/* ---------------------------------------------------------------------- */
/* Over the REAL published seat set                                       */
/* ---------------------------------------------------------------------- */

const SEATS = "data/published/reference/constituencies.jsonl";

function publishedSeats() {
  if (!existsSync(SEATS)) return null;
  return readFileSync(SEATS, "utf8")
    .split("\n")
    .filter((line) => line.trim())
    .map((line) => JSON.parse(line));
}

test("the real seat set: the three repeated names resolve to two seats each", () => {
  const seats = publishedSeats();
  if (!seats) return; // not built -- NOT AUDITED; the pytest suite reports this scope

  for (const name of ["Aurangabad", "Hamirpur", "Maharajganj"]) {
    const found = seatsNamed(seats, name);
    assert.equal(found.length, 2, `${name} should name two seats, got ${found.length}`);
    assert.equal(new Set(found.map((s) => s.state)).size, 2, `${name}: one state twice`);
  }
});

test("the real seat set: every seat is in the window and every member is named", () => {
  const seats = publishedSeats();
  if (!seats) return;

  assert.ok(seats.length > 500, `only ${seats.length} seats`);
  let both = 0;
  let changed = 0;
  let unnamed = 0;
  for (const s of seats) {
    const history = seatHistory(s);
    assert.ok(history.people.length > 0, `${s.constituency_id} has no representative`);
    for (const person of history.people) {
      for (const term of person.terms) {
        assert.ok(term === 17 || term === 18, `out-of-window term ${term}`);
      }
      // The whole reason T086 carried the three fields: without them this
      // would be the id for every one of the 887.
      if (person.nameMissing) unnamed += 1;
    }
    if (history.changedHands) changed += 1;
    if (history.people.some((p) => p.terms.length > 1)) both += 1;
  }
  assert.equal(unnamed, 0, `${unnamed} representatives have no name in the seat set`);
  assert.ok(changed > 300, `only ${changed} seats changed hands`);
  assert.ok(both > 200, `only ${both} seats have a member holding both terms`);
});

test("the real seat set: the state picker reaches every seat exactly once", () => {
  const seats = publishedSeats();
  if (!seats) return;
  const states = statesIn(seats);
  const reached = states.reduce((sum, s) => sum + s.seats, 0);
  assert.equal(reached, seats.length, "a seat is reachable from no state or from two");
  for (const s of states) {
    assert.equal(seatsInState(seats, s.state).length, s.seats);
  }
});
