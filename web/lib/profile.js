/* Ministry-profile and comparison logic. Pure functions, no DOM. T078/T080.
 *
 * Reads `aggregates/ministry-profile.jsonl` -- 1,146 rows, one per
 * (ministry, session) -- and `reference/ministries.jsonl`. The aggregate is
 * precomputed because `research.md` records that fetching ~10^5 question
 * records into a page is not viable.
 *
 * Two rules here are load-bearing rather than tidy:
 *
 * 1. **The type mix counts EVERY question, identified asker or not.**
 *    `ministry_id` and the question type come off the QUESTION RECORD, not off
 *    resolution, so the mix is not a resolved-only figure. The page must label
 *    it that way, because a mix shown beside a resolution split otherwise
 *    reads as "resolved questions by type" -- which would silently drop the
 *    unresolved and partly-resolved questions out of a figure that includes
 *    them.
 *
 * 2. **The four status counts must sum to the question count.** Asserted here
 *    and in `tests/page/profile.test.mjs`. If they ever stop summing, the
 *    page is showing a split that does not account for every question, and a
 *    reader would subtract to find a fifth bucket that is not labelled.
 */

import { parseSessionId } from "./format.js";

/** The four buckets, in the order they are shown. Matches T070's
 * `STATUS_COUNT_FIELDS` -- a fifth bucket added there must be added here, and
 * the sum assertion is what makes that impossible to miss. */
export const STATUS_FIELDS = Object.freeze([
  { key: "fully_linked", label: "Fully linked", flagged: false },
  { key: "partly_linked", label: "Partly linked", flagged: true },
  { key: "not_linked", label: "Not linked", flagged: true },
  { key: "ambiguous", label: "Ambiguous", flagged: true },
]);

/** The three keys whose label the page must show with a visible flag. Derived
 * from STATUS_FIELDS so the two cannot disagree. */
export const FLAGGED_STATUS_KEYS = Object.freeze(
  STATUS_FIELDS.filter((f) => f.flagged).map((f) => f.key),
);

/** One status key's label and whether it is flagged, or null for an unknown
 * key. The page renders status as TEXT from this and never retypes a label:
 * T079's result cards and T078's status strip say the same words because they
 * read the same list. */
export function statusField(key) {
  return STATUS_FIELDS.find((f) => f.key === key) ?? null;
}

/**
 * Which status bucket ONE question falls in, from the two fields the search
 * digest publishes: `resolution_status` and `asking_members`.
 *
 * The mirror of `_bucket` in `src/sansad/views/ministry_profile.py`, and the
 * ORDER IS THE SAME ORDER for the same reason: `ambiguous` is tested before
 * the asker check, because an ambiguous question deliberately publishes no
 * `asking_members` and would otherwise be counted as "nobody was identified".
 * `tests/page/search.test.mjs` asserts this against golden cases the Python
 * side wrote, so the two cannot drift apart silently.
 *
 * Returns null for a record carrying no status at all, so the page shows
 * "not stated" rather than guessing a bucket.
 */
export function questionBucket(record) {
  const status = record?.resolution_status;
  if (typeof status !== "string" || status.length === 0) return null;
  if (status === "resolved") return "fully_linked";
  if (status === "ambiguous") return "ambiguous";
  if (Array.isArray(record.asking_members) && record.asking_members.length > 0) {
    return "partly_linked";
  }
  return "not_linked";
}

export class StatusSumMismatch extends Error {
  constructor(message) {
    super(message);
    this.name = "StatusSumMismatch";
  }
}

/** Every status count for one row, and the assertion that they account for it. */
export function statusCounts(row) {
  const counts = {};
  let sum = 0;
  for (const field of STATUS_FIELDS) {
    const value = Number(row?.[field.key] ?? 0);
    counts[field.key] = Number.isFinite(value) ? value : 0;
    sum += counts[field.key];
  }
  const questions = Number(row?.questions ?? 0);
  if (sum !== questions) {
    throw new StatusSumMismatch(
      `status counts sum to ${sum} but the row carries ${questions} questions ` +
        `(${row?.ministry_id} / ${row?.session}). A split that does not account ` +
        "for every question invites a reader to subtract and find an unlabelled bucket.",
    );
  }
  return { counts, sum, flagged: counts.partly_linked + counts.not_linked + counts.ambiguous };
}

/** Every session id present in the profile rows, ordered by (term, number). */
export function profileSessions(rows) {
  const seen = new Set();
  for (const row of rows ?? []) seen.add(row.session);
  return [...seen]
    .map(parseSessionId)
    .filter(Boolean)
    .sort((a, b) => a.term - b.term || a.number - b.number);
}

/** Every ministry id present, with its display name, sorted by name. */
export function profileMinistries(rows, ministryRecords) {
  const byId = new Map((ministryRecords ?? []).map((m) => [m.ministry_id, m]));
  const ids = new Set((rows ?? []).map((r) => r.ministry_id));
  return [...ids]
    .map((id) => {
      const record = byId.get(id) ?? null;
      return {
        ministryId: id,
        name: record?.canonical_name ?? id,
        // Rename DATES are not published, so former names are shown with no
        // date. Inventing "(renamed 2021)" would be a claim the record does
        // not support.
        formerNames: Array.isArray(record?.former_names) ? [...record.former_names] : [],
      };
    })
    .sort((a, b) => a.name.localeCompare(b.name));
}

/**
 * Select one ministry's rows across an inclusive span of sessions.
 *
 * The span is given as two session ids; order between them does not matter.
 * Sessions in the span with NO row for this ministry are returned as explicit
 * zero rows rather than skipped -- a gap in the series is information, and a
 * chart that silently closed it would imply continuity that is not there.
 */
export function selectSpan(rows, { ministryId, fromSession, toSession, allSessions }) {
  const from = parseSessionId(fromSession);
  const to = parseSessionId(toSession);
  if (!from || !to) return [];
  const lo = from.term < to.term || (from.term === to.term && from.number <= to.number) ? from : to;
  const hi = lo === from ? to : from;

  const inSpan = (s) =>
    (s.term > lo.term || (s.term === lo.term && s.number >= lo.number)) &&
    (s.term < hi.term || (s.term === hi.term && s.number <= hi.number));

  const bySession = new Map(
    (rows ?? []).filter((r) => r.ministry_id === ministryId).map((r) => [r.session, r]),
  );
  const sessions = (allSessions ?? profileSessions(rows)).filter(inSpan);

  return sessions.map((session) => {
    const row = bySession.get(session.sessionId) ?? null;
    const base = row ?? {
      ministry_id: ministryId,
      session: session.sessionId,
      questions: 0,
      question_type_mix: {},
      fully_linked: 0,
      partly_linked: 0,
      not_linked: 0,
      ambiguous: 0,
      counting_basis_unit: null,
      basis_version: null,
    };
    const status = statusCounts(base);
    return {
      session,
      row: base,
      present: row !== null,
      questions: Number(base.questions ?? 0),
      typeMix: { ...(base.question_type_mix ?? {}) },
      status: status.counts,
      flagged: status.flagged,
    };
  });
}

/** Every question type seen across a span, in a stable order. */
export function typesIn(span) {
  const types = new Set();
  for (const entry of span ?? []) {
    for (const type of Object.keys(entry.typeMix)) types.add(type);
  }
  return [...types].sort();
}

/** Totals over a span. The status counts must still sum. */
export function spanTotals(span) {
  const totals = {
    questions: 0,
    typeMix: {},
    status: Object.fromEntries(STATUS_FIELDS.map((f) => [f.key, 0])),
    flagged: 0,
    sessions: (span ?? []).length,
    sessionsWithQuestions: 0,
  };
  for (const entry of span ?? []) {
    totals.questions += entry.questions;
    if (entry.questions > 0) totals.sessionsWithQuestions += 1;
    for (const [type, n] of Object.entries(entry.typeMix)) {
      totals.typeMix[type] = (totals.typeMix[type] ?? 0) + n;
    }
    for (const field of STATUS_FIELDS) {
      totals.status[field.key] += entry.status[field.key];
    }
    totals.flagged += entry.flagged;
  }
  const sum = STATUS_FIELDS.reduce((acc, f) => acc + totals.status[f.key], 0);
  if (sum !== totals.questions) {
    throw new StatusSumMismatch(
      `span status counts sum to ${sum} but the span carries ${totals.questions} questions`,
    );
  }
  return totals;
}

/** Absolute and percent change, or null when there is nothing to compare. */
export function change(first, last) {
  if (typeof first !== "number" || typeof last !== "number") return null;
  const absolute = last - first;
  // A percent change from zero is undefined, not infinite and not 100%.
  const percent = first === 0 ? null : (absolute / first) * 100;
  return { first, last, absolute, percent };
}

/** Share of a total as a percentage, or null when the total is zero. */
export function share(part, total) {
  if (typeof part !== "number" || typeof total !== "number" || total === 0) return null;
  return (part / total) * 100;
}

/**
 * How the questions and the type mix changed across the span: first selected
 * session against last selected session.
 */
export function spanChange(span) {
  if (!span || span.length === 0) return null;
  const first = span[0];
  const last = span[span.length - 1];
  const types = typesIn(span);
  return {
    firstSession: first.session,
    lastSession: last.session,
    singleSession: span.length === 1,
    questions: change(first.questions, last.questions),
    byType: types.map((type) => ({
      type,
      count: change(first.typeMix[type] ?? 0, last.typeMix[type] ?? 0),
      // The SHARE of the mix matters as much as the count: a ministry can take
      // more questions overall while the starred share falls.
      shareFirst: share(first.typeMix[type] ?? 0, first.questions),
      shareLast: share(last.typeMix[type] ?? 0, last.questions),
    })),
  };
}

/** The counting-basis record that applies to a span, read from the published
 * file. Never retyped in the page. */
export function basisFor(span, basisRecords) {
  const unit = span?.find((e) => e.row.counting_basis_unit)?.row.counting_basis_unit ?? "question";
  return (basisRecords ?? []).find((b) => b.unit === unit) ?? null;
}

/** T080: two ministries over the same span, with one shared basis. */
export function compare(rows, { ministryIds, fromSession, toSession, allSessions }) {
  const sides = (ministryIds ?? []).map((ministryId) => {
    const span = selectSpan(rows, { ministryId, fromSession, toSession, allSessions });
    return { ministryId, span, totals: spanTotals(span), change: spanChange(span) };
  });
  const types = new Set();
  for (const side of sides) for (const t of typesIn(side.span)) types.add(t);
  return { sides, types: [...types].sort() };
}
