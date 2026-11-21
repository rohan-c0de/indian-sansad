/* T088 — the state and constituency entry point. User Story 3.
 *
 * Pure logic, no DOM: `app.js` renders, this decides. Everything here works on
 * the published records as fetched — `reference/constituencies.jsonl` and
 * `aggregates/state-subjects.jsonl` for the summaries, and one
 * `by-member/<id>.jsonl` at a time for a member's questions.
 *
 * THE WALK, and why it is this one (owner decision 2026-10-10):
 *
 *   1. the constituency reference set   -- 252,226 B, fetched on first use
 *   2. the chosen member's own file     -- fetched when the visitor opens them
 *
 * Never the whole question record, and never a per-state question partition,
 * which `contracts/published-dataset.md` deliberately does not publish. The
 * 3.4 MB `reference/members.jsonl` is NOT fetched: T086 put each member's name,
 * party and sitting status onto the representation precisely so this view would
 * not need it. Measured in `spike/size-budget.md` -> T086.
 *
 * PICK A STATE FIRST. Three constituency names in this window name a different
 * seat in each of two states — Aurangabad, Hamirpur, Maharajganj — so a name on
 * its own is ambiguous and this module never resolves one to a single seat.
 * `seatsNamed` returns EVERY match, and the page shows each with its state.
 */

import { isMissing, NOT_STATED, ordinal } from "./format.js";
import { questionBucket, STATUS_FIELDS, statusField } from "./profile.js";

/** The basis unit the state subject summary is published under. */
export const STATE_BASIS_UNIT = "state-question";

/* ---------------------------------------------------------------------- */
/* Seats and states                                                       */
/* ---------------------------------------------------------------------- */

/** Case- and space-insensitive key for matching a typed name. Matching only:
 * the published spelling is what is ever displayed. */
export function nameKey(value) {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, " ");
}

/**
 * Every state in the seat set, with how many seats and members it reaches.
 *
 * Ordered by name. NOT by seat count: an order by size is a ranking of states,
 * and this phase publishes none — and a visitor looking for their own state
 * wants it where the alphabet puts it.
 */
export function statesIn(seats) {
  const byState = new Map();
  for (const seat of seats ?? []) {
    const state = isMissing(seat?.state) ? NOT_STATED : String(seat.state);
    let entry = byState.get(state);
    if (!entry) {
      entry = { state, seats: 0, members: new Set() };
      byState.set(state, entry);
    }
    entry.seats += 1;
    for (const rep of seat.representations ?? []) {
      if (rep?.member_id) entry.members.add(String(rep.member_id));
    }
  }
  return [...byState.values()]
    .map((e) => ({ state: e.state, seats: e.seats, members: e.members.size }))
    .sort((a, b) => a.state.localeCompare(b.state, "en"));
}

/** One state's seats, by name. */
export function seatsInState(seats, state) {
  const wanted = nameKey(state);
  return (seats ?? [])
    .filter((seat) => nameKey(seat?.state) === wanted)
    .sort((a, b) => String(a.name).localeCompare(String(b.name), "en"));
}

/**
 * Every seat matching a typed name, across all states.
 *
 * Returns a LIST, always, even for one match. A function that returned "the"
 * seat for a name would be wrong three times in this window, and wrong
 * silently — the caller would get Bihar's Aurangabad or Maharashtra's
 * depending on file order.
 */
export function seatsNamed(seats, name) {
  const wanted = nameKey(name);
  if (!wanted) return [];
  return (seats ?? [])
    .filter((seat) => nameKey(seat?.name) === wanted)
    .sort((a, b) => String(a.state).localeCompare(String(b.state), "en"));
}

/** Seats whose name contains the typed text, for an as-you-type hint. */
export function seatsMatching(seats, text, { limit = 12 } = {}) {
  const wanted = nameKey(text);
  if (wanted.length < 2) return [];
  const out = [];
  for (const seat of seats ?? []) {
    const key = nameKey(seat?.name);
    if (key.includes(wanted)) out.push(seat);
    if (out.length >= limit * 4) break;
  }
  return out
    .sort(
      (a, b) =>
        Number(nameKey(a.name) !== wanted) - Number(nameKey(b.name) !== wanted) ||
        String(a.name).localeCompare(String(b.name), "en") ||
        String(a.state).localeCompare(String(b.state), "en"),
    )
    .slice(0, limit);
}

export function seatById(seats, constituencyId) {
  const wanted = String(constituencyId ?? "");
  return (seats ?? []).find((seat) => String(seat?.constituency_id) === wanted) ?? null;
}

/* ---------------------------------------------------------------------- */
/* The people who held a seat                                            */
/* ---------------------------------------------------------------------- */

/**
 * One entry per DISTINCT member who held this seat in the window, each with
 * every term they held it for.
 *
 * Two different members across the two terms are two entries — "both members
 * appear with their respective periods, not merged into one", US3 scenario 3.
 * One member across both terms is ONE entry listing both terms, because that
 * is one person, and showing them twice would read as two holders.
 *
 * Ordered by first term, then by name, so the seat reads chronologically and
 * the order does not depend on the file's.
 *
 * `start_date` and `end_date` are deliberately not surfaced: all 1,103
 * published representations carry `not stated`, and the term number is the
 * period this record actually has.
 */
export function representativesOf(seat) {
  const byMember = new Map();
  for (const rep of seat?.representations ?? []) {
    const id = String(rep?.member_id ?? "");
    if (!id) continue;
    let entry = byMember.get(id);
    if (!entry) {
      entry = {
        memberId: id,
        name: isMissing(rep.member_name) ? NOT_STATED : String(rep.member_name),
        party: isMissing(rep.party) ? NOT_STATED : String(rep.party),
        sittingStatus: isMissing(rep.sitting_status) ? NOT_STATED : String(rep.sitting_status),
        terms: [],
        // True when the record names them but not who they are. The page shows
        // the id with a flag rather than an empty row.
        nameMissing: isMissing(rep.member_name),
      };
      byMember.set(id, entry);
    }
    if (Number.isInteger(rep.term_number) && !entry.terms.includes(rep.term_number)) {
      entry.terms.push(rep.term_number);
    }
  }
  const out = [...byMember.values()];
  for (const entry of out) entry.terms.sort((a, b) => a - b);
  return out.sort(
    (a, b) => (a.terms[0] ?? 0) - (b.terms[0] ?? 0) || a.name.localeCompare(b.name, "en"),
  );
}

/** `[17, 18]` -> `17th and 18th Lok Sabha`; `[18]` -> `18th Lok Sabha`. */
export function termsPhrase(terms) {
  const list = (terms ?? []).filter((t) => Number.isInteger(t));
  if (list.length === 0) return NOT_STATED;
  const words = list.map((t) => ordinal(t));
  const joined =
    words.length === 1
      ? words[0]
      : `${words.slice(0, -1).join(", ")} and ${words[words.length - 1]}`;
  return `${joined} Lok Sabha`;
}

/**
 * What this seat's history in the window is, in one shape the page can render
 * without deciding anything itself.
 *
 * `changedHands` is about MEMBERS, not terms: one member across both terms did
 * not change hands, and the two are different facts a reader needs separately.
 */
export function seatHistory(seat) {
  const people = representativesOf(seat);
  const terms = [
    ...new Set((seat?.representations ?? []).map((r) => r?.term_number).filter(Number.isInteger)),
  ].sort((a, b) => a - b);
  return {
    people,
    terms,
    changedHands: people.length > 1,
    termsCovered: terms.length,
  };
}

/* ---------------------------------------------------------------------- */
/* A member's questions                                                   */
/* ---------------------------------------------------------------------- */

/**
 * De-duplicate on `question_id` — contract guarantee 6, and the counting basis
 * says so in as many words.
 *
 * A by-member file cannot contain a duplicate today, but this is the function
 * every count below goes through, so the rule is applied once rather than
 * trusted everywhere.
 */
export function dedupeQuestions(records) {
  const byId = new Map();
  for (const record of records ?? []) {
    const id = String(record?.question_id ?? "");
    if (id && !byId.has(id)) byId.set(id, record);
  }
  return [...byId.values()];
}

/**
 * One member's published questions, counted and bucketed.
 *
 * The status buckets come from `lib/profile.js` — the ministry profile's own
 * list — so this view, the profile's status strip and a search result all say
 * the same words. Unresolved and ambiguous questions are INCLUDED in the
 * total, as the published basis requires, and flagged as text.
 */
export function memberQuestions(records) {
  const questions = dedupeQuestions(records);
  const counts = {};
  for (const field of STATUS_FIELDS) counts[field.key] = 0;
  let unknownStatus = 0;
  for (const question of questions) {
    const bucket = questionBucket(question);
    if (bucket && bucket in counts) counts[bucket] += 1;
    else unknownStatus += 1;
  }
  const flagged = STATUS_FIELDS.filter((f) => f.flagged).reduce(
    (sum, f) => sum + counts[f.key],
    0,
  );
  return {
    questions: questions.sort(byDateThenId),
    total: questions.length,
    counts,
    unknownStatus,
    flagged,
    /** The status rows to render, label and flag from the shared list. */
    statusRows: STATUS_FIELDS.map((f) => ({
      ...statusField(f.key),
      questions: counts[f.key],
    })),
  };
}

/** Newest first, then by id so the order is total and stable. */
function byDateThenId(a, b) {
  const da = String(a?.date ?? "");
  const db = String(b?.date ?? "");
  if (da !== db) return db.localeCompare(da, "en");
  return String(a?.question_id ?? "").localeCompare(String(b?.question_id ?? ""), "en");
}

/**
 * A member's own subject lines, most questions first.
 *
 * Exact subject lines, never grouped — the same rule the published aggregate
 * states, so a reader comparing this with `state-subjects` is comparing like
 * with like. Ties break on the subject, so the order is deterministic.
 */
export function subjectTally(records, { limit = 0 } = {}) {
  const counts = new Map();
  for (const question of dedupeQuestions(records)) {
    const subject = isMissing(question?.subject) ? NOT_STATED : String(question.subject);
    counts.set(subject, (counts.get(subject) ?? 0) + 1);
  }
  const rows = [...counts.entries()]
    .map(([subject, questions]) => ({ subject, questions }))
    .sort((a, b) => b.questions - a.questions || a.subject.localeCompare(b.subject, "en"));
  return {
    rows: limit > 0 ? rows.slice(0, limit) : rows,
    distinct: rows.length,
    shown: limit > 0 ? Math.min(limit, rows.length) : rows.length,
  };
}

/* ---------------------------------------------------------------------- */
/* The published state subject summary                                    */
/* ---------------------------------------------------------------------- */

/**
 * One state's rows out of `aggregates/state-subjects.jsonl`, in published
 * order, with the denominators the file carries on every row.
 *
 * The page NEVER recomputes these from question records: the published figure
 * and its basis are the claim, and a page that recomputed would be showing a
 * number the dataset does not contain. `tests/contract/test_state_subjects.py`
 * is where the reproduction is proved.
 */
export function stateSubjects(rows, state) {
  const wanted = nameKey(state);
  const mine = (rows ?? []).filter((row) => nameKey(row?.state) === wanted);
  if (mine.length === 0) return null;
  return {
    state: String(mine[0].state),
    rows: mine.map((row) => ({
      subject: isMissing(row.subject) ? NOT_STATED : String(row.subject),
      questions: Number(row.questions) || 0,
    })),
    stateQuestions: Number(mine[0].state_questions) || 0,
    stateSubjects: Number(mine[0].state_subjects) || 0,
    subjectsShown: Number(mine[0].subjects_shown) || mine.length,
    basisUnit: String(mine[0].counting_basis_unit ?? STATE_BASIS_UNIT),
    basisVersion: String(mine[0].basis_version ?? ""),
  };
}

/** Which states the published summary covers, so the page can say when a
 * state it can show seats for has no subject summary. */
export function statesWithSubjects(rows) {
  return new Set((rows ?? []).map((row) => nameKey(row?.state)));
}
