/* T079 — subject search logic. The owner's rules, each with a test.
 *
 * Nothing here touches the network or the DOM. `loadDigest` is injected, so
 * the two claims that matter most about the fetching — that only sessions
 * containing a match are ever fetched, and that a digest is fetched only when
 * a page of 25 actually needs it — are asserted by COUNTING the calls rather
 * than by reading the code.
 *
 * The index fixture is built by the same encoding the Python side writes
 * (`prefixes` + `doc_prefix` + `doc_number`, delta-encoded postings), so
 * `questionIdAt` is exercised against the real shape rather than a convenient
 * one. `the invariant holds over the WHOLE published index` runs the same
 * assertions over `data/published/search/subject-index.json` when it is built.
 */

import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { test } from "node:test";

import {
  DigestUnavailable,
  ORDER_STATEMENT,
  PAGE_SIZE,
  SearchIndexShapeError,
  askerIndex,
  askersFor,
  createResultSet,
  digestFileName,
  documentCount,
  orderWithinSession,
  parseQuestionId,
  planSearch,
  positionsFor,
  questionIdAt,
} from "../../web/lib/search.js";
import { STATUS_FIELDS, questionBucket, statusField } from "../../web/lib/profile.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const GOLDEN = JSON.parse(readFileSync(join(HERE, "python-parity-golden.json"), "utf8"));
const PUBLISHED_INDEX = join(HERE, "..", "..", "data", "published", "search", "subject-index.json");

/* ---------------------------------------------------------------------- */
/* Fixture: an index in the real published encoding                       */
/* ---------------------------------------------------------------------- */

/** Build an index the way `search_index.py` does: prefix table, parallel
 * document arrays, sorted terms, delta-encoded postings. */
function buildIndex(docs, postingsByTerm) {
  const prefixes = [];
  const prefixAt = new Map();
  const doc_prefix = [];
  const doc_number = [];
  for (const id of docs) {
    const cut = id.lastIndexOf("/");
    const prefix = id.slice(0, cut);
    const number = id.slice(cut + 1);
    if (!prefixAt.has(prefix)) {
      prefixAt.set(prefix, prefixes.length);
      prefixes.push(prefix);
    }
    doc_prefix.push(prefixAt.get(prefix));
    doc_number.push(number);
  }
  const terms = Object.keys(postingsByTerm).sort();
  const postings = terms.map((term) => {
    const ids = [...postingsByTerm[term]].sort((a, b) => a - b);
    const deltas = [];
    let previous = 0;
    for (const value of ids) {
      deltas.push(value - previous);
      previous = value;
    }
    return deltas;
  });
  return { prefixes, doc_prefix, doc_number, terms, postings, built: "2026-10-10" };
}

/* Five sessions, deliberately out of (term, number) order in document order,
 * so a test that passed by accident of insertion order fails. */
const DOCS = [
  /* 0 */ "lok-sabha/17/2/starred/5",
  /* 1 */ "lok-sabha/17/2/unstarred/5",
  /* 2 */ "lok-sabha/17/2/unstarred/9",
  /* 3 */ "lok-sabha/18/8/starred/1",
  /* 4 */ "lok-sabha/18/8/starred/2",
  /* 5 */ "lok-sabha/18/8/unstarred/3",
  /* 6 */ "lok-sabha/17/10/starred/4",
  /* 7 */ "lok-sabha/18/3/unstarred/7",
];

const INDEX = buildIndex(DOCS, {
  water: [0, 1, 3, 4, 6, 7],
  drinking: [1, 3, 7],
  scheme: [2, 5],
  rural: [7],
});

/** The digest rows for each session. Dates deliberately NOT in id order. */
const DIGESTS = {
  "lok-sabha/17/2": [
    { question_id: "lok-sabha/17/2/starred/5", subject: "Water supply", date: "2019-07-10", ministry_id: "jal-shakti", resolution_status: "resolved", asking_members: ["ls-1"] },
    { question_id: "lok-sabha/17/2/unstarred/5", subject: "Drinking water quality", date: "2019-07-12", ministry_id: "jal-shakti", resolution_status: "unresolved", asking_members: ["ls-2"] },
    { question_id: "lok-sabha/17/2/unstarred/9", subject: "Scheme coverage", date: "2019-07-11", ministry_id: "rural-development", resolution_status: "unresolved", asking_members: [] },
  ],
  "lok-sabha/17/10": [
    { question_id: "lok-sabha/17/10/starred/4", subject: "Water bodies", date: "2022-12-01", ministry_id: "jal-shakti", resolution_status: "ambiguous", asking_members: [] },
  ],
  "lok-sabha/18/3": [
    { question_id: "lok-sabha/18/3/unstarred/7", subject: "Rural drinking water", date: "2025-02-03", ministry_id: "jal-shakti", resolution_status: "resolved", asking_members: ["ls-1", "ls-9999"] },
  ],
  "lok-sabha/18/8": [
    { question_id: "lok-sabha/18/8/starred/1", subject: "Drinking water in schools", date: "2026-07-20", ministry_id: "education", resolution_status: "resolved", asking_members: ["ls-2"] },
    { question_id: "lok-sabha/18/8/starred/2", subject: "Water metering", date: "2026-07-22", ministry_id: "jal-shakti", resolution_status: "resolved", asking_members: ["ls-1"] },
    { question_id: "lok-sabha/18/8/unstarred/3", subject: "Scheme rollout", date: "2026-07-21", ministry_id: "rural-development", resolution_status: "unresolved", asking_members: ["ls-1"] },
  ],
};

const NAMES = askerIndex([
  { member_id: "ls-1", canonical_name: "A Member", party: "Party One", state: "Kerala" },
  { member_id: "ls-2", canonical_name: "B Member", party: "Party Two", state: "Bihar" },
]);

/** A loader that records every call, so "only what was needed" is counted. */
function recordingLoader(digests = DIGESTS, { failOn = null } = {}) {
  const calls = [];
  return {
    calls,
    load: async (sessionId) => {
      calls.push(sessionId);
      if (failOn === sessionId) throw new Error(`HTTP 503 for ${sessionId}`);
      if (!(sessionId in digests)) throw new Error(`HTTP 404 for ${sessionId}`);
      return digests[sessionId];
    },
  };
}

/* ---------------------------------------------------------------------- */
/* The index encoding                                                     */
/* ---------------------------------------------------------------------- */

test("a question id is rebuilt from the prefix encoding, not stored whole", () => {
  assert.equal(documentCount(INDEX), DOCS.length);
  for (let i = 0; i < DOCS.length; i += 1) {
    assert.equal(questionIdAt(INDEX, i), DOCS[i]);
  }
  // The encoding is actually doing its job: fewer prefixes than documents.
  assert.ok(INDEX.prefixes.length < DOCS.length);
});

test("postings are delta-decoded back to ascending positions", () => {
  assert.deepEqual(positionsFor(INDEX, "water"), [0, 1, 3, 4, 6, 7]);
  assert.deepEqual(positionsFor(INDEX, "WATER"), [0, 1, 3, 4, 6, 7], "lookup is lowercased");
  assert.deepEqual(positionsFor(INDEX, "rural"), [7]);
});

test("a term in no posting list returns null, not an empty array", () => {
  // The distinction IS the zero-results message: an empty array would make
  // "this word is in no subject" look like "the intersection was empty".
  assert.equal(positionsFor(INDEX, "bioluminescence"), null);
  assert.notEqual(positionsFor(INDEX, "rural"), null);
});

test("an index missing an array is refused with a named error, not a crash", () => {
  assert.throws(() => positionsFor({ terms: [] }, "x"), SearchIndexShapeError);
  assert.throws(() => planSearch({ terms: ["x"] }, "water"), SearchIndexShapeError);
});

test("a question id and a digest file name are derived the Python way", () => {
  const parsed = parseQuestionId("lok-sabha/17/4/starred/12");
  assert.deepEqual(parsed, {
    questionId: "lok-sabha/17/4/starred/12",
    house: "lok-sabha",
    term: 17,
    session: 4,
    sessionId: "lok-sabha/17/4",
    type: "starred",
    number: 12,
  });
  assert.equal(parseQuestionId("nonsense"), null);
  assert.equal(digestFileName("lok-sabha/17/4"), "lok-sabha-17-4.jsonl");
  assert.throws(() => digestFileName("nope"), TypeError);
});

/* ---------------------------------------------------------------------- */
/* AND, and the total from the index alone                                */
/* ---------------------------------------------------------------------- */

test("EVERY query word must match — AND, not any", () => {
  const both = planSearch(INDEX, "drinking water");
  // "drinking" is at 1,3,7; "water" at 0,1,3,4,6,7 -> intersection 1,3,7.
  assert.equal(both.total, 3);
  assert.deepEqual(both.words, ["drinking", "water"]);

  const anyWouldBe = new Set([...positionsFor(INDEX, "drinking"), ...positionsFor(INDEX, "water")]);
  assert.equal(anyWouldBe.size, 6, "OR would return 6; AND must not");
});

test("the total comes from the index ALONE, before any digest is fetched", () => {
  const loader = recordingLoader();
  const plan = planSearch(INDEX, "water");
  assert.equal(plan.total, 6);
  assert.deepEqual(loader.calls, [], "planning must fetch nothing");
  // And it equals the real count of matching documents.
  assert.equal(plan.sessions.reduce((n, s) => n + s.questionIds.length, 0), 6);
});

test("a word that is in NO subject is named as the reason for zero results", () => {
  const plan = planSearch(INDEX, "water bioluminescence");
  assert.equal(plan.total, 0);
  assert.deepEqual(plan.missingWords, ["bioluminescence"]);
  assert.deepEqual(plan.sessions, []);
});

test("every missing word is named, not just the first", () => {
  const plan = planSearch(INDEX, "bioluminescence tardigrade");
  assert.deepEqual(plan.missingWords, ["bioluminescence", "tardigrade"]);
});

test("words all present but no overlap is zero hits with NO missing word", () => {
  // "rural" is at 7 only; "scheme" at 2,5. Both exist; the AND is empty.
  const plan = planSearch(INDEX, "rural scheme");
  assert.equal(plan.total, 0);
  assert.deepEqual(plan.missingWords, [], "nothing is missing; the intersection is empty");
  assert.deepEqual(plan.sessions, []);
});

/* ---------------------------------------------------------------------- */
/* Ignored words and an emptied query                                     */
/* ---------------------------------------------------------------------- */

test("words the tokenise rule drops are listed, and the rest still searches", () => {
  const plan = planSearch(INDEX, "the drinking of water");
  assert.deepEqual(plan.words, ["drinking", "water"]);
  assert.deepEqual(
    plan.ignored.map((i) => i.word),
    ["the", "of"],
  );
  assert.equal(plan.total, 3, "the query still ran on what was left");
});

test("a query with nothing left after the rule says so and searches nothing", () => {
  const plan = planSearch(INDEX, "the and of to");
  assert.equal(plan.emptyQuery, true);
  assert.equal(plan.blank, false);
  assert.equal(plan.total, 0);
  assert.deepEqual(plan.sessions, []);
  assert.equal(plan.ignored.length, 4, "all four are reported, not silently dropped");
});

test("a blank query is not the same as one the rule emptied", () => {
  const plan = planSearch(INDEX, "   ");
  assert.equal(plan.emptyQuery, true);
  assert.equal(plan.blank, true);
  assert.deepEqual(plan.ignored, []);
});

/* ---------------------------------------------------------------------- */
/* Order                                                                  */
/* ---------------------------------------------------------------------- */

test("sessions come out NEWEST FIRST — (term, number) descending", () => {
  const plan = planSearch(INDEX, "water");
  assert.deepEqual(
    plan.sessions.map((s) => s.sessionId),
    ["lok-sabha/18/8", "lok-sabha/18/3", "lok-sabha/17/10", "lok-sabha/17/2"],
  );
  // 17/10 before 17/2 is the whole point: a string sort gives the reverse.
  const stringSorted = plan.sessions.map((s) => s.sessionId).slice().sort().reverse();
  assert.notDeepEqual(plan.sessions.map((s) => s.sessionId), stringSorted);
});

test("only sessions that contain a match are listed at all", () => {
  const plan = planSearch(INDEX, "scheme");
  assert.deepEqual(
    plan.sessions.map((s) => s.sessionId),
    ["lok-sabha/18/8", "lok-sabha/17/2"],
    "18/3 and 17/10 have no `scheme` match and must not appear",
  );
});

test("within a session: newest date first, then question number, then id", () => {
  const ordered = orderWithinSession([
    { questionId: "a/1/1/unstarred/9", date: "2026-07-20", number: 9 },
    { questionId: "a/1/1/starred/4", date: "2026-07-22", number: 4 },
    { questionId: "a/1/1/unstarred/4", date: "2026-07-22", number: 4 },
    { questionId: "a/1/1/starred/1", date: "2026-07-21", number: 1 },
  ]);
  assert.deepEqual(ordered.map((r) => r.questionId), [
    // 07-22 first; within it number 4 ties, so the full id breaks it and
    // `starred` sorts before `unstarred`.
    "a/1/1/starred/4",
    "a/1/1/unstarred/4",
    "a/1/1/starred/1",
    "a/1/1/unstarred/9",
  ]);
});

test("a record with no usable date sorts LAST in its session, never dropped", () => {
  const ordered = orderWithinSession([
    { questionId: "a/1/1/starred/9", date: "not stated", number: 9 },
    { questionId: "a/1/1/starred/1", date: "2026-07-01", number: 1 },
    { questionId: "a/1/1/starred/2", date: null, number: 2 },
  ]);
  assert.deepEqual(ordered.map((r) => r.questionId), [
    "a/1/1/starred/1",
    "a/1/1/starred/2",
    "a/1/1/starred/9",
  ]);
  assert.equal(ordered.length, 3, "nothing was filtered out");
});

test("the order the page prints is the order the code implements", () => {
  // The page renders ORDER_STATEMENT, so the sentence cannot describe an
  // order this file does not produce without this failing.
  assert.match(ORDER_STATEMENT, /Newest session first/);
  assert.match(ORDER_STATEMENT, /newest question date/);
  assert.match(ORDER_STATEMENT, /question number/);
  // The owner's prohibition: no match is LABELLED "near-identical" or
  // "similar", and nothing claims relevance.
  for (const forbidden of ["near-identical", "near identical", "similar", "best match", "most relevant", "closest"]) {
    assert.ok(
      !ORDER_STATEMENT.toLowerCase().includes(forbidden),
      `the order statement must not say "${forbidden}"`,
    );
  }
  // It must say so positively, not merely avoid the words: a reader has to be
  // told the sequence is not a ranking, or the top result reads as the best.
  assert.match(ORDER_STATEMENT, /not ranked or scored/);
});

/* ---------------------------------------------------------------------- */
/* Paging, and the files it does NOT fetch                                */
/* ---------------------------------------------------------------------- */

test("25 per page is the published page size", () => {
  assert.equal(PAGE_SIZE, 25);
});

test("a first page that fits in the newest session fetches ONE digest", async () => {
  const loader = recordingLoader();
  const plan = planSearch(INDEX, "water");
  const set = createResultSet(plan, { loadDigest: loader.load, pageSize: 2 });
  const page = await set.next();
  assert.equal(page.added, 2);
  assert.equal(page.total, 6, "the total is still the whole match count");
  assert.deepEqual(loader.calls, ["lok-sabha/18/8"], "exactly one digest, the newest");
  assert.deepEqual(page.results.map((r) => r.questionId), [
    "lok-sabha/18/8/starred/2", // 2026-07-22
    "lok-sabha/18/8/starred/1", // 2026-07-20
  ]);
  assert.equal(page.done, false);
});

test("Show more fetches the NEXT digest only when the page needs it", async () => {
  const loader = recordingLoader();
  const plan = planSearch(INDEX, "water");
  const set = createResultSet(plan, { loadDigest: loader.load, pageSize: 2 });

  await set.next();
  assert.deepEqual(loader.calls, ["lok-sabha/18/8"]);

  // 18/8 holds only 2 of the 6 `water` matches, so the second page must
  // cross into 18/3 and 17/10 -- and no further.
  const second = await set.next();
  assert.equal(second.added, 2);
  assert.deepEqual(loader.calls, ["lok-sabha/18/8", "lok-sabha/18/3", "lok-sabha/17/10"]);
  assert.equal(second.done, false, "17/2 still has matches");

  const third = await set.next();
  assert.equal(third.added, 2);
  assert.deepEqual(loader.calls, [
    "lok-sabha/18/8",
    "lok-sabha/18/3",
    "lok-sabha/17/10",
    "lok-sabha/17/2",
  ]);
  assert.equal(third.done, true);
  assert.equal(third.shown, 6);
  assert.equal(third.results.length, plan.total);
});

test("a page larger than the result set finishes in one call and is done", async () => {
  const loader = recordingLoader();
  const plan = planSearch(INDEX, "scheme");
  const set = createResultSet(plan, { loadDigest: loader.load, pageSize: 25 });
  const page = await set.next();
  assert.equal(page.added, 2);
  assert.equal(page.done, true);
  assert.deepEqual(loader.calls, ["lok-sabha/18/8", "lok-sabha/17/2"]);
  assert.equal(page.pages, 1);
});

test("the whole result set comes out in the documented order across sessions", async () => {
  const loader = recordingLoader();
  const plan = planSearch(INDEX, "water");
  const set = createResultSet(plan, { loadDigest: loader.load, pageSize: 25 });
  const page = await set.next();
  assert.deepEqual(page.results.map((r) => r.questionId), [
    "lok-sabha/18/8/starred/2",
    "lok-sabha/18/8/starred/1",
    "lok-sabha/18/3/unstarred/7",
    "lok-sabha/17/10/starred/4",
    // Within 17/2 the NEWEST DATE is first: unstarred/5 is 2019-07-12 and
    // starred/5 is 2019-07-10, so the lower question number comes second.
    // Ordering on the id instead would reverse these two.
    "lok-sabha/17/2/unstarred/5",
    "lok-sabha/17/2/starred/5",
  ]);
});

test("a result set with no sessions is done immediately and fetches nothing", async () => {
  const loader = recordingLoader();
  const plan = planSearch(INDEX, "bioluminescence");
  const set = createResultSet(plan, { loadDigest: loader.load });
  const page = await set.next();
  assert.deepEqual(page.results, []);
  assert.equal(page.done, true);
  assert.deepEqual(loader.calls, []);
});

test("createResultSet refuses to exist without a loader", () => {
  assert.throws(() => createResultSet(planSearch(INDEX, "water"), {}), TypeError);
});

/* ---------------------------------------------------------------------- */
/* Fetch failure                                                          */
/* ---------------------------------------------------------------------- */

test("a failed digest fetch throws a NAMED error carrying the session", async () => {
  const loader = recordingLoader(DIGESTS, { failOn: "lok-sabha/18/8" });
  const plan = planSearch(INDEX, "water");
  const set = createResultSet(plan, { loadDigest: loader.load, pageSize: 25 });
  await assert.rejects(
    () => set.next(),
    (error) => {
      assert.ok(error instanceof DigestUnavailable);
      assert.equal(error.sessionId, "lok-sabha/18/8");
      assert.match(error.message, /could not be read/);
      // The original failure is kept, so the page can show the HTTP status.
      assert.match(String(error.cause && error.cause.message), /503/);
      return true;
    },
  );
});

test("a failure on a LATER page does not discard the results already shown", async () => {
  const loader = recordingLoader(DIGESTS, { failOn: "lok-sabha/18/3" });
  const plan = planSearch(INDEX, "water");
  const set = createResultSet(plan, { loadDigest: loader.load, pageSize: 2 });
  const first = await set.next();
  assert.equal(first.added, 2);
  await assert.rejects(() => set.next(), DigestUnavailable);
  // The two already-shown results are still there: the page shows an error
  // BESIDE them rather than replacing them with an empty list.
  assert.equal(set.shown, 2);
});

/* ---------------------------------------------------------------------- */
/* Flags                                                                  */
/* ---------------------------------------------------------------------- */

test("the status bucket matches the PYTHON rule, case for case", () => {
  assert.deepEqual(
    STATUS_FIELDS.map((f) => f.key),
    GOLDEN.status_buckets,
    "the four buckets must be the Python side's STATUS_COUNT_FIELDS, in order",
  );
  for (const expected of GOLDEN.status_bucket_cases) {
    assert.equal(
      questionBucket({
        resolution_status: expected.resolution_status,
        asking_members: expected.asking_members,
      }),
      expected.bucket,
      `${expected.resolution_status} with ${expected.asking_members.length} asker(s)`,
    );
  }
  // The order of the tests is the thing that could regress silently: an
  // ambiguous question publishes NO askers, so a copy that tested the asker
  // list first would call it "not linked".
  assert.equal(
    questionBucket({ resolution_status: "ambiguous", asking_members: [] }),
    "ambiguous",
  );
  assert.notEqual(
    questionBucket({ resolution_status: "ambiguous", asking_members: [] }),
    "not_linked",
  );
});

test("a record with no status at all gets no bucket, so the page says not stated", () => {
  assert.equal(questionBucket({}), null);
  assert.equal(questionBucket({ resolution_status: "" }), null);
  assert.equal(statusField("nonsense"), null);
});

test("the labels are the ministry profile's, not retyped", () => {
  // The owner's requirement: the same wording in both views. These come out
  // of one list, so they are equal by construction; this asserts the lookup
  // the search view uses actually reaches that list.
  for (const field of STATUS_FIELDS) {
    assert.equal(statusField(field.key).label, field.label);
    assert.equal(statusField(field.key).flagged, field.flagged);
  }
  assert.equal(statusField("partly_linked").label, "Partly linked");
  assert.equal(statusField("partly_linked").flagged, true);
  assert.equal(statusField("fully_linked").flagged, false);
});

test("a question with some askers unidentified shows the identified ones, flagged", async () => {
  const loader = recordingLoader();
  const plan = planSearch(INDEX, "rural");
  const set = createResultSet(plan, { loadDigest: loader.load });
  const page = await set.next();
  const record = page.results[0];
  assert.equal(record.questionId, "lok-sabha/18/3/unstarred/7");

  const { identified, unknownIds } = askersFor(record, NAMES);
  // ls-1 resolves; ls-9999 is in the digest but not in asker-names.
  assert.deepEqual(identified.map((m) => m.canonical_name), ["A Member"]);
  assert.deepEqual(unknownIds, ["ls-9999"], "the id is RETURNED, not dropped");
});

test("an unresolved question with some askers is Partly linked and flagged", async () => {
  const loader = recordingLoader();
  const plan = planSearch(INDEX, "scheme");
  const set = createResultSet(plan, { loadDigest: loader.load });
  const page = await set.next();
  const byId = new Map(page.results.map((r) => [r.questionId, r]));

  const partly = byId.get("lok-sabha/18/8/unstarred/3");
  assert.equal(questionBucket(partly), "partly_linked");
  assert.equal(statusField("partly_linked").flagged, true);

  const none = byId.get("lok-sabha/17/2/unstarred/9");
  assert.equal(questionBucket(none), "not_linked");
  assert.deepEqual(askersFor(none, NAMES), { identified: [], unknownIds: [] });
});

test("an ambiguous question is still a result, flagged, with no asker invented", async () => {
  const loader = recordingLoader();
  const plan = planSearch(INDEX, "water");
  const set = createResultSet(plan, { loadDigest: loader.load, pageSize: 25 });
  const page = await set.next();
  const ambiguous = page.results.find((r) => r.questionId === "lok-sabha/17/10/starred/4");
  assert.ok(ambiguous, "FR-004: an ambiguous question is NOT filtered out of search");
  assert.equal(questionBucket(ambiguous), "ambiguous");
  assert.deepEqual(askersFor(ambiguous, NAMES).identified, []);
});

test("an id the index matched but the digest does not carry is flagged, not hidden", async () => {
  // Two published files disagreeing. The result still appears, marked, so the
  // count a reader sees matches the total the index gave.
  const thin = { ...DIGESTS, "lok-sabha/18/8": [DIGESTS["lok-sabha/18/8"][0]] };
  const loader = recordingLoader(thin);
  const plan = planSearch(INDEX, "water");
  const set = createResultSet(plan, { loadDigest: loader.load, pageSize: 25 });
  const page = await set.next();
  assert.equal(page.results.length, plan.total, "no result went missing");
  const orphan = page.results.find((r) => r.questionId === "lok-sabha/18/8/starred/2");
  assert.equal(orphan.notInDigest, true);
  assert.equal(orphan.subject, null, "nothing is invented for it");
});

test("askersFor is safe with a missing lookup and a missing list", () => {
  assert.deepEqual(askersFor({}, NAMES), { identified: [], unknownIds: [] });
  assert.deepEqual(askersFor({ asking_members: ["ls-1"] }, new Map()), {
    identified: [],
    unknownIds: ["ls-1"],
  });
});

/* ---------------------------------------------------------------------- */
/* Over the REAL published index, when it is built                        */
/* ---------------------------------------------------------------------- */

test("the encoding and the AND rule hold over the WHOLE published index", (t) => {
  if (!existsSync(PUBLISHED_INDEX)) {
    // Skipped, not passed: data/published/ is git-ignored on main.
    t.skip("data/published/search/subject-index.json is not built — NOT AUDITED");
    return;
  }
  const index = JSON.parse(readFileSync(PUBLISHED_INDEX, "utf8"));
  assert.equal(index.doc_prefix.length, index.doc_number.length);
  assert.equal(index.terms.length, index.postings.length);

  // Sorted terms: the binary search is wrong on an unsorted array, and would
  // fail by MISSING matches rather than by erroring.
  for (let i = 1; i < index.terms.length; i += 1) {
    assert.ok(index.terms[i - 1] < index.terms[i], `terms unsorted at ${i}`);
  }

  // Every id rebuilds to the published shape.
  for (const position of [0, 1, 1000, documentCount(index) - 1]) {
    assert.ok(parseQuestionId(questionIdAt(index, position)), `position ${position}`);
  }

  // A common word's AND with itself is itself; with a second word it shrinks.
  const water = planSearch(index, "water");
  assert.ok(water.total > 100, `only ${water.total} hits for "water"`);
  const drinkingWater = planSearch(index, "drinking water");
  assert.ok(
    drinkingWater.total < water.total,
    "AND must narrow: drinking water cannot have more hits than water",
  );
  assert.deepEqual(drinkingWater.missingWords, []);

  // Sessions newest first, and only sessions with a match.
  const ids = water.sessions.map((s) => `${s.term}/${s.number}`);
  for (let i = 1; i < water.sessions.length; i += 1) {
    const a = water.sessions[i - 1];
    const b = water.sessions[i];
    assert.ok(a.term > b.term || (a.term === b.term && a.number > b.number), `out of order at ${ids[i]}`);
  }
  for (const session of water.sessions) {
    assert.ok(session.questionIds.length > 0, `${session.sessionId} listed with no match`);
  }

  // The index publishes NO grade. Asserted here too, because the page's whole
  // no-ranking rule rests on there being nothing to rank with.
  for (const key of Object.keys(index)) {
    assert.ok(
      !/score|weight|grade|rank|similar/i.test(key),
      `the published index carries a grading field: ${key}`,
    );
  }
});
