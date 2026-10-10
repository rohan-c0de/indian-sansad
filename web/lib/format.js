/* Formatting helpers. No data decisions live here except one, and it is the
 * important one: NOT_STATED.
 *
 * Owner decision 2026-10-10: where the published record does not carry
 * something, the page says "not stated" and never invents it. The published
 * data already uses the literal string `not stated` (see
 * `src/sansad/model/_common.py` -> `NOT_STATED`), so a value that is absent,
 * null, empty or already that string all render the same way and a reader
 * cannot tell which of those it was -- because the distinction is not one the
 * record supports.
 *
 * All 21 published sessions carry `start_date: "not stated"` and
 * `end_date: null`. Session dates therefore never appear on this page.
 */

export const NOT_STATED = "not stated";

/** True when the record carries nothing usable for this field. */
export function isMissing(value) {
  if (value === null || value === undefined) return true;
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed.length === 0 || trimmed.toLowerCase() === NOT_STATED;
  }
  if (Array.isArray(value)) return value.length === 0;
  return false;
}

/** The only way a value reaches the page. Missing becomes "not stated". */
export function stated(value, render) {
  if (isMissing(value)) return NOT_STATED;
  return render ? render(value) : String(value);
}

const INTEGER = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

/** Grouped integer, Indian digit grouping, tabular in the stylesheet. */
export function count(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return NOT_STATED;
  return INTEGER.format(Math.round(value));
}

/** A published rate (0..1) as a percentage with two decimals. */
export function percent(value, { decimals = 2 } = {}) {
  if (typeof value !== "number" || !Number.isFinite(value)) return NOT_STATED;
  return `${(value * 100).toFixed(decimals)}%`;
}

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

/** An ISO-8601 date as `21 Jun 2019`. Anything else is "not stated".
 *
 * Deliberately NOT `Date` parsing: a published date is already ISO-8601 at the
 * ingest boundary (`iso_date()`), and running it through `new Date()` would
 * shift it by the viewer's timezone -- a date one day out is worse than one
 * that is plainly unformatted.
 */
export function isoDate(value) {
  if (isMissing(value)) return NOT_STATED;
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value).trim());
  if (!match) return NOT_STATED;
  const [, year, month, day] = match;
  const name = MONTHS[Number(month) - 1];
  if (!name) return NOT_STATED;
  return `${Number(day)} ${name} ${year}`;
}

/** Ordinal for a Lok Sabha term: 17 -> "17th". */
export function ordinal(n) {
  if (typeof n !== "number" || !Number.isFinite(n)) return NOT_STATED;
  const rem100 = n % 100;
  if (rem100 >= 11 && rem100 <= 13) return `${n}th`;
  switch (n % 10) {
    case 1: return `${n}st`;
    case 2: return `${n}nd`;
    case 3: return `${n}rd`;
    default: return `${n}th`;
  }
}

/** `lok-sabha` -> `Lok Sabha`. Houses are the only slugs we re-title. */
export function houseName(slug) {
  if (isMissing(slug)) return NOT_STATED;
  return String(slug)
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

/**
 * Split a `session_id` (`lok-sabha/17/4`) into its parts.
 *
 * Returns `null` when it does not have that shape, so a caller can fall back
 * to printing the id rather than printing a wrong number.
 */
export function parseSessionId(sessionId) {
  const parts = String(sessionId ?? "").split("/");
  if (parts.length !== 3) return null;
  const term = Number(parts[1]);
  const number = Number(parts[2]);
  if (!Number.isInteger(term) || !Number.isInteger(number)) return null;
  return { house: parts[0], term, number, sessionId: String(sessionId) };
}

/**
 * Order sessions by (term, number). Owner decision 2026-10-10.
 *
 * NOT by date: all 21 published sessions have `start_date: "not stated"`. And
 * NOT by the order the record lists them in -- `coverage.jsonl`'s
 * `sessions_covered` is sorted as STRINGS, so it reads
 * `17/1, 17/10, 17/11, 17/12, 17/14, 17/15, 17/2, ...`. Printing that order
 * would show session 10 before session 2.
 *
 * `direction` is "asc" by default; T079's result order is "desc".
 */
export function orderSessions(sessionIds, { direction = "asc" } = {}) {
  const sign = direction === "desc" ? -1 : 1;
  const parsed = [];
  const unparseable = [];
  for (const id of sessionIds ?? []) {
    const p = parseSessionId(id);
    if (p) parsed.push(p);
    else unparseable.push(String(id));
  }
  parsed.sort((a, b) => sign * (a.term - b.term || a.number - b.number));
  // Anything unparseable goes last, in the order given, and is never dropped.
  return [...parsed, ...unparseable.map((id) => ({ sessionId: id, term: null, number: null }))];
}

/** `17th LS · Session 4` */
export function sessionLabel(session) {
  if (!session || session.term === null || session.term === undefined) {
    return stated(session && session.sessionId);
  }
  return `${ordinal(session.term)} LS · Session ${session.number}`;
}
