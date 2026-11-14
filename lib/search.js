/* Subject search over the published index and digest. T079. Pure logic, no DOM.
 *
 * ======================================================================
 * THE ORDER (owner decision 2026-10-10), stated once, here
 * ======================================================================
 *
 *   newest session first -- (term, session number) DESCENDING
 *   within a session     -- newest question date first
 *   ties                 -- by question number
 *
 * Ordered on `(term, number)` and NOT on a date because every published
 * session carries `start_date: "not stated"` -- measured, 0 of 21 -- and
 * `(term, number)` was verified equal to ordering by each session's first
 * question date before being adopted. The page states this order on screen, so
 * a reader never infers it from the sequence.
 *
 * **There is no ranking and no grade.** Every result is in one order and that
 * order carries no claim about relevance. `search_index.py` publishes nothing
 * to rank with, and `tests/contract/test_search_index.py` asserts it stays
 * that way; a page that sorted by "number of query words matched" would be
 * presenting an unmeasured heuristic as a property of the data.
 *
 * The owner prohibited two specific match labels (tasks.md -> T079, owner
 * decision 2026-10-10), and this file DELIBERATELY DOES NOT SPELL THEM OUT --
 * `tests/unit/test_page_fetch_layer.py` scans every page file for them as
 * plain text, prose included, because the prohibition is on what a reader can
 * be shown and a comment is as readable as a label. A file that documented
 * the ban by reproducing it would be the hole the check exists to close. The
 * same reasoning is already recorded in `search_index.py` for the guard's
 * prohibited field names.
 *
 * **One tie-break is added to make the order TOTAL**, and it is named because
 * it is not in the owner's sentence: a starred and an unstarred question can
 * share both a date and a number, so after question number the full
 * `question_id` breaks the remaining tie. Without it two renders of the same
 * result set could differ in order, which would make "a documented fixed
 * order" false in the one case nobody would look for.
 *
 * ======================================================================
 * EVERY query word must match (AND)
 * ======================================================================
 *
 * Not any. A query of two words returns the questions whose subject carries
 * both. The total is the size of that intersection, computed from the INDEX
 * ALONE -- before a single digest byte is fetched -- so the page can say how
 * many matches exist without paying for the records to show them.
 *
 * A word that is in no posting list at all is named as the reason for zero
 * results. "No results" and "no results because `bioluminescence` is not in
 * any subject" are different statements, and only the second one tells a
 * visitor what to do next.
 *
 * ======================================================================
 * What is fetched, and when
 * ======================================================================
 *
 * The index (2,484,758 B) and `search/asker-names.jsonl` (92,713 B) are
 * fetched on the FIRST SEARCH only -- never on page load. After that, one
 * digest per session, and **only for sessions that contain a match**, and
 * only when the page actually needs that session's rows to fill a page of 25.
 * `spike/size-budget.md` -> T079 has the measurement that forced this shape:
 * resolving hits through the `by-session` partitions instead cost 4,348,529 B
 * for a common word, over T019's 4,183,979 B budget.
 */

import { tokeniseQuery } from "./tokenise.js";
import { digestFileName, parseSessionId } from "./format.js";

/** 25 per page. The owner's number; `size-budget.md` records that it is what
 * drives the two-session case, and that it was not changed for that. */
export const PAGE_SIZE = 25;

/** The order, in one sentence, for the page to render. Spelled once so the
 * page cannot state an order the code does not implement. */
export const ORDER_STATEMENT =
  "Newest session first, then newest question date within a session, then by " +
  "question number. Results are not ranked or scored, and the sequence says " +
  "nothing about how closely a subject matches: the published index carries " +
  "no such measure, so this page does not invent one.";

export class SearchIndexShapeError extends Error {
  constructor(message) {
    super(message);
    this.name = "SearchIndexShapeError";
  }
}

/* ---------------------------------------------------------------------- */
/* Reading the index                                                      */
/* ---------------------------------------------------------------------- */

function requireArrays(index) {
  for (const key of ["prefixes", "doc_prefix", "doc_number", "terms", "postings"]) {
    if (!Array.isArray(index?.[key])) {
      throw new SearchIndexShapeError(
        `the published search index has no ${key} array; it cannot be read`,
      );
    }
  }
}

/**
 * Rebuild the `question_id` at a document position.
 *
 * The mirror of `question_id_at` in `src/sansad/publish/search_index.py`: the
 * document list is a prefix table plus two parallel arrays, which is why this
 * is two array reads and a concatenation rather than a decoder.
 */
export function questionIdAt(index, position) {
  return `${index.prefixes[index.doc_prefix[position]]}/${index.doc_number[position]}`;
}

export function documentCount(index) {
  return index.doc_number.length;
}

/** Binary search the sorted `terms` array. Terms are VALUES, not keys -- see
 * the Python module docstring for the guard reason that shape exists. */
function termPosition(index, term) {
  const terms = index.terms;
  let lo = 0;
  let hi = terms.length - 1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (terms[mid] === term) return mid;
    if (terms[mid] < term) lo = mid + 1;
    else hi = mid - 1;
  }
  return -1;
}

/**
 * The document positions one term resolves to, ascending.
 *
 * `null` -- not the empty array -- when the term is in no posting list at all.
 * The difference is the whole of the zero-results message: an empty array
 * would make "this word is in no subject" indistinguishable from "this word
 * matched nothing once intersected".
 */
export function positionsFor(index, term) {
  requireArrays(index);
  const at = termPosition(index, String(term).toLowerCase());
  if (at < 0) return null;
  const deltas = index.postings[at];
  if (!Array.isArray(deltas)) return null;
  const out = [];
  let position = 0;
  for (const delta of deltas) {
    position += delta;
    out.push(position);
  }
  return out;
}

/* ---------------------------------------------------------------------- */
/* Planning a search -- from the index alone                              */
/* ---------------------------------------------------------------------- */

/** `lok-sabha/17/4/starred/12` -> its parts, or null. */
export function parseQuestionId(questionId) {
  const parts = String(questionId ?? "").split("/");
  if (parts.length !== 5) return null;
  const term = Number(parts[1]);
  const number = Number(parts[4]);
  if (!Number.isInteger(term) || !Number.isInteger(Number(parts[2]))) return null;
  return {
    questionId: String(questionId),
    house: parts[0],
    term,
    session: Number(parts[2]),
    sessionId: `${parts[0]}/${parts[1]}/${parts[2]}`,
    type: parts[3],
    // A question number that is not an integer is kept as NaN rather than
    // dropped: the row still exists and must still be shown, it just sorts
    // last within its date.
    number: Number.isInteger(number) ? number : Number.NaN,
  };
}

/* Re-exported, not reimplemented: it lives in `lib/format.js` beside
 * `parseSessionId`, because `lib/fetch.js` needs it to build a URL and the
 * transport layer must not import the search logic to learn a filename. */
export { digestFileName };

/**
 * Plan a search. Reads the INDEX ONLY -- no digest is fetched here.
 *
 * Returns
 *   words        the terms looked up, in the order typed
 *   ignored      [{word, reason}] the tokenise rule dropped
 *   blank        the visitor typed nothing
 *   emptyQuery   the rule left nothing to look up
 *   missingWords the words that are in NO posting list -- the named reason
 *                for zero results
 *   total        the number of matching questions, from the index alone
 *   sessions     [{sessionId, term, number, questionIds}] in RESULT ORDER,
 *                newest session first; only sessions that contain a match
 */
export function planSearch(index, query) {
  const { words, ignored, empty, blank, noLetters } = tokeniseQuery(query);
  const base = {
    query: typeof query === "string" ? query : "",
    words,
    ignored,
    blank: Boolean(blank),
    noLetters: Boolean(noLetters),
    emptyQuery: empty,
    missingWords: [],
    total: 0,
    sessions: [],
  };
  if (empty) return base;

  requireArrays(index);

  /* Every word's postings. A word in NO posting list is recorded by name --
   * it is the reason for zero results, and naming it is the difference
   * between a dead end and a next step. */
  const lists = [];
  const missingWords = [];
  for (const word of words) {
    const positions = positionsFor(index, word);
    if (positions === null) missingWords.push(word);
    else lists.push(positions);
  }
  if (missingWords.length > 0) {
    return { ...base, missingWords };
  }

  /* AND: intersect. Smallest list first, so the work is bounded by the rarest
   * word rather than by the commonest. */
  lists.sort((a, b) => a.length - b.length);
  let intersection = lists[0];
  for (let i = 1; i < lists.length && intersection.length > 0; i += 1) {
    const next = new Set(lists[i]);
    intersection = intersection.filter((position) => next.has(position));
  }

  /* Group by session, in result order. The session is read off the
   * `question_id`, which the index rebuilds -- so this needs no digest. */
  const bySession = new Map();
  const unparseable = [];
  for (const position of intersection) {
    const questionId = questionIdAt(index, position);
    const parsed = parseQuestionId(questionId);
    if (!parsed) {
      unparseable.push(questionId);
      continue;
    }
    let bucket = bySession.get(parsed.sessionId);
    if (!bucket) {
      bucket = {
        sessionId: parsed.sessionId,
        term: parsed.term,
        number: parsed.session,
        questionIds: [],
      };
      bySession.set(parsed.sessionId, bucket);
    }
    bucket.questionIds.push(questionId);
  }

  const sessions = [...bySession.values()].sort(
    // NEWEST SESSION FIRST: (term, number) descending.
    (a, b) => b.term - a.term || b.number - a.number,
  );

  return {
    ...base,
    missingWords: [],
    /* The total comes from the INDEX ALONE, before any digest is fetched
     * (owner decision 2026-10-10). A question whose id could not be parsed is
     * still a match and is still counted; it is listed separately rather than
     * dropped out of the total.
     *
     * Written as a block comment, not `//`: the page-hardcoding test strips
     * block comments but not line comments, so a date in a `//` comment that
     * happens to equal `manifest.last_refreshed` fails it. The test is right
     * to be blunt there -- it is the check that stops a published figure
     * being typed into the page -- so the comment style bends, not the test. */
    total: intersection.length,
    sessions,
    unparseable,
  };
}

/* ---------------------------------------------------------------------- */
/* Ordering within a session                                             */
/* ---------------------------------------------------------------------- */

/**
 * Order one session's matched records: newest question date first, then by
 * question number, then by the full id so the order is total.
 *
 * A record with no usable date sorts AFTER every dated one rather than being
 * dropped or treated as the oldest possible date -- "not stated" is not a
 * date, and FR-004 reaches search too.
 */
export function orderWithinSession(records) {
  return [...records].sort((a, b) => {
    const da = typeof a.date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(a.date) ? a.date : "";
    const db = typeof b.date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(b.date) ? b.date : "";
    if (da !== db) {
      if (da === "") return 1;
      if (db === "") return -1;
      return db < da ? -1 : 1; // newest first
    }
    const na = Number.isFinite(a.number) ? a.number : Number.POSITIVE_INFINITY;
    const nb = Number.isFinite(b.number) ? b.number : Number.POSITIVE_INFINITY;
    if (na !== nb) return na - nb;
    // The documented extra tie-break: a starred and an unstarred question can
    // share a date AND a number.
    return a.questionId < b.questionId ? -1 : a.questionId > b.questionId ? 1 : 0;
  });
}

/* ---------------------------------------------------------------------- */
/* Paging -- one digest at a time, only where a match is                 */
/* ---------------------------------------------------------------------- */

export class DigestUnavailable extends Error {
  constructor(message, { sessionId, cause } = {}) {
    super(message, { cause });
    this.name = "DigestUnavailable";
    this.sessionId = sessionId ?? null;
  }
}

/**
 * A paged result set over a plan.
 *
 * `loadDigest(sessionId)` must resolve to that session's digest records. It is
 * injected rather than imported so a test can count the calls and make one
 * fail; the page passes the memoised loader in `lib/fetch.js`.
 *
 * `next()` resolves `{ results, added, done, exhausted }` and fetches the
 * **minimum** number of digests to fill one page: it stops as soon as it has
 * `pageSize` more results, so a query whose first 25 results all sit in the
 * newest matching session fetches exactly one file. A session with no match
 * is never fetched at all, because the plan never lists it.
 */
export function createResultSet(plan, { loadDigest, pageSize = PAGE_SIZE } = {}) {
  if (typeof loadDigest !== "function") {
    throw new TypeError("createResultSet needs a loadDigest(sessionId) function");
  }
  const results = [];
  const fetched = [];
  let sessionCursor = 0;
  /** Records of the session being consumed, already ordered, with the index of
   * the next one to emit. */
  let current = null;

  const totalPages = () => Math.ceil(plan.total / pageSize);

  async function fillFrom(session) {
    const wanted = new Set(session.questionIds);
    let rows;
    try {
      rows = await loadDigest(session.sessionId);
    } catch (cause) {
      throw new DigestUnavailable(
        `the records for ${session.sessionId} could not be read`,
        { sessionId: session.sessionId, cause },
      );
    }
    fetched.push(session.sessionId);
    const matched = [];
    const seen = new Set();
    for (const row of rows ?? []) {
      const questionId = row?.question_id;
      if (!wanted.has(questionId) || seen.has(questionId)) continue;
      seen.add(questionId);
      const parsed = parseQuestionId(questionId);
      matched.push({
        ...row,
        questionId,
        sessionId: session.sessionId,
        term: session.term,
        sessionNumber: session.number,
        type: parsed ? parsed.type : null,
        number: parsed ? parsed.number : Number.NaN,
      });
    }
    /* A matched id the digest does not carry is a real inconsistency between
     * two published files. It is surfaced as a row, not swallowed: the index
     * promised a question the digest does not have, and a reader counting
     * results would otherwise find the total short with no explanation. */
    const missing = session.questionIds.filter((id) => !seen.has(id));
    for (const questionId of missing) {
      const parsed = parseQuestionId(questionId);
      matched.push({
        questionId,
        sessionId: session.sessionId,
        term: session.term,
        sessionNumber: session.number,
        type: parsed ? parsed.type : null,
        number: parsed ? parsed.number : Number.NaN,
        subject: null,
        date: null,
        ministry_id: null,
        resolution_status: null,
        asking_members: [],
        notInDigest: true,
      });
    }
    return { records: orderWithinSession(matched), at: 0 };
  }

  async function next() {
    const before = results.length;
    while (results.length - before < pageSize && (current || sessionCursor < plan.sessions.length)) {
      if (!current || current.at >= current.records.length) {
        if (sessionCursor >= plan.sessions.length) break;
        current = await fillFrom(plan.sessions[sessionCursor]);
        sessionCursor += 1;
        continue;
      }
      results.push(current.records[current.at]);
      current.at += 1;
    }
    const exhausted = sessionCursor >= plan.sessions.length && (!current || current.at >= current.records.length);
    return {
      results: [...results],
      added: results.length - before,
      done: exhausted,
      shown: results.length,
      total: plan.total,
      sessionsFetched: [...fetched],
      pages: totalPages(),
    };
  }

  return {
    next,
    get shown() {
      return results.length;
    },
    get sessionsFetched() {
      return [...fetched];
    },
    get total() {
      return plan.total;
    },
  };
}

/* ---------------------------------------------------------------------- */
/* Asker names                                                            */
/* ---------------------------------------------------------------------- */

/** `search/asker-names.jsonl` rows, keyed by `member_id`. */
export function askerIndex(rows) {
  const out = new Map();
  for (const row of rows ?? []) {
    if (row && typeof row.member_id === "string") out.set(row.member_id, row);
  }
  return out;
}

/**
 * The askers of one question, resolved against the name lookup.
 *
 * Returns `{ identified, unknownIds }`. An id the lookup does not carry is
 * returned in `unknownIds` so the page can show the id AS TEXT with a flag --
 * never silently dropped, and never shown as a name it is not. The digest's
 * `asking_members` is what the resolution published; a gap here is a join this
 * project made and cannot name, which is exactly the thing FR-004 says must
 * stay visible.
 */
export function askersFor(record, names) {
  const identified = [];
  const unknownIds = [];
  for (const memberId of record?.asking_members ?? []) {
    const row = names?.get ? names.get(memberId) : undefined;
    if (row) identified.push(row);
    else unknownIds.push(String(memberId));
  }
  return { identified, unknownIds };
}
