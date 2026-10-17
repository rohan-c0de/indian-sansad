/* Coverage-statement logic. Pure functions, no DOM.
 *
 * Everything here is DERIVED from the published record. Nothing about which
 * House is covered, how many sessions there are, or whether a session has
 * sitting days is written into the page -- the page prints what these
 * functions return.
 */

import { houseName, isMissing, orderSessions, parseSessionId } from "./format.js";

/** A House row counts as covered when it actually carries questions.
 *
 * `coverage.jsonl` publishes a row for EVERY House, including one with no
 * route -- "an omitted statement reads as 'not looked at'". So the presence of
 * a row is not the claim; `total_questions > 0` is.
 */
export function housesWithData(coverageRows) {
  return (coverageRows ?? [])
    .filter((row) => Number(row?.total_questions) > 0)
    .map((row) => String(row.house));
}

/**
 * The claim the page leads with, derived rather than typed.
 *
 * With only the Lok Sabha carrying questions this returns "Lok Sabha only" --
 * the same words FR-013 and scenario 12 require today. If a Rajya Sabha route
 * is ever found and its row carries questions, the claim changes by itself
 * rather than by someone remembering to edit a string.
 */
export function housesClaim(coverageRows) {
  const covered = housesWithData(coverageRows).map(houseName).sort();
  if (covered.length === 0) return "No House is covered";
  if (covered.length === 1) return `${covered[0]} only`;
  if (covered.length === 2) return `${covered[0]} and ${covered[1]}`;
  return `${covered.slice(0, -1).join(", ")} and ${covered[covered.length - 1]}`;
}

/**
 * The rows the page shows figures for: every House that carries questions,
 * most questions first.
 *
 * The page used to pick "the lok-sabha row" by name. That left one typed
 * house identity deciding whose figures appeared, which is the same drift the
 * derived claim above exists to remove: with a Rajya Sabha route found, the
 * claim would have changed and the figures would not.
 */
export function coveredRows(coverageRows) {
  return (coverageRows ?? [])
    .filter((row) => Number(row?.total_questions) > 0)
    .sort((a, b) => Number(b.total_questions) - Number(a.total_questions));
}

/** The Houses that have a row but no questions, with the reason if published. */
export function housesNotCovered(coverageRows) {
  const covered = new Set(housesWithData(coverageRows));
  return (coverageRows ?? [])
    .filter((row) => !covered.has(String(row.house)))
    .map((row) => ({
      house: String(row.house),
      name: houseName(row.house),
      reason: isMissing(row.unobtainable_reason) ? null : String(row.unobtainable_reason),
    }));
}

/** Zero sitting days is a published value, not a missing one.
 *
 * `Number(null)` is 0, so a naive `Number(x) === 0` reports a session whose
 * sitting days are NOT STATED as having zero of them -- which is a different
 * claim about the record and a false one. The value has to be a real number
 * before it can be zero.
 */
export function hasZeroSittingDays(record) {
  if (record === null || record === undefined) return false;
  const days = record.sitting_days;
  if (typeof days !== "number" || !Number.isFinite(days)) return false;
  return days === 0;
}

/**
 * A per-sitting-day rate, or "n/a" when the denominator is zero.
 *
 * `coverage.jsonl` declares the case: "A sitting-day denominator of 0 would
 * divide by zero in any per-sitting-day rate." Returning Infinity, 0 or a
 * silently-omitted row would each be a different wrong answer; "n/a" is the
 * only one that says what happened.
 */
export const NOT_APPLICABLE = "n/a";

export function perSittingDay(total, sittingDays) {
  if (typeof sittingDays !== "number" || !Number.isFinite(sittingDays) || sittingDays === 0) {
    return NOT_APPLICABLE;
  }
  if (typeof total !== "number" || !Number.isFinite(total)) return NOT_APPLICABLE;
  return total / sittingDays;
}

/**
 * The session rows the page renders, ordered by (term, number).
 *
 * Joins the Houses' `sessions_covered` list against the session reference set.
 * A session in the coverage list with no reference record still produces a row
 * -- dropping it would make the count on screen disagree with the count the
 * record publishes.
 */
export function sessionRows(coverageRow, sessionRecords) {
  const byId = new Map(
    (sessionRecords ?? []).map((s) => [`${s.house}/${s.term}/${s.number}`, s]),
  );
  return orderSessions(coverageRow?.sessions_covered ?? []).map((session) => {
    const record = byId.get(session.sessionId) ?? null;
    return {
      ...session,
      record,
      sittingDays: record && !isMissing(record.sitting_days) ? Number(record.sitting_days) : null,
      zeroSittingDays: hasZeroSittingDays(record),
      startDate: record ? record.start_date : null,
      endDate: record ? record.end_date : null,
    };
  });
}

/** `17th Lok Sabha · Session 4`, the long form the owner asked for. */
export function longSessionLabel(session) {
  const parsed =
    session && session.term !== null && session.term !== undefined
      ? session
      : parseSessionId(session?.sessionId);
  if (!parsed || parsed.term === null || parsed.term === undefined) {
    return String(session?.sessionId ?? "");
  }
  const rem100 = parsed.term % 100;
  let suffix = "th";
  if (rem100 < 11 || rem100 > 13) {
    suffix = { 1: "st", 2: "nd", 3: "rd" }[parsed.term % 10] ?? "th";
  }
  return `${parsed.term}${suffix} ${houseName(parsed.house)} · Session ${parsed.number}`;
}

/** The text flag a zero-sitting-day session carries. Text, never colour. */
export const ZERO_SITTING_DAYS_FLAG = "0 sitting days as published — see known gaps";
