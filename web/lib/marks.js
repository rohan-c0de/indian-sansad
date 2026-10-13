/* The two typographic devices the whole page is built from. T123, T124.
 *
 * Both live here rather than in a view module because three views use each,
 * and a device rendered two slightly different ways in two places is not a
 * device -- it is a coincidence. The stylesheet has one rule per class below
 * and nothing else may style them.
 */

import { NOT_STATED, count, isMissing } from "./format.js";

/* ---------------------------------------------------------------------- */
/* The starred mark (T123, FR-113)                                        */
/* ---------------------------------------------------------------------- */

/* Parliament prints an asterisk against a starred question. The page prints
 * the same asterisk, and **the word is still there** for anyone who cannot see
 * it: the glyph is aria-hidden and a visually-hidden "starred" sits beside it,
 * so a screen reader hears the word and never the character name.
 *
 * An UNSTARRED question carries no mark at all. That asymmetry is the whole
 * device: a mark that appeared on everything would say nothing, and "unstarred"
 * is the absence of the star, not a second symbol. The type is still rendered
 * as a word in the row's meta line either way, so nothing here is the only
 * carrier of the distinction (FR-104).
 *
 * The published values are exactly `STARRED` and `UNSTARRED` -- see
 * `aggregates/ministry-profile.jsonl` -> `question_type_mix`. Anything else is
 * treated as unknown and marked as such rather than guessed into one bucket.
 */

export const STARRED = "STARRED";
export const UNSTARRED = "UNSTARRED";

/** The asterisk Parliament itself prints, or nothing. */
export function starMark(type, doc = document) {
  if (type !== STARRED) return null;
  const wrap = doc.createElement("span");
  wrap.className = "star";
  const glyph = doc.createElement("span");
  glyph.className = "star-glyph";
  glyph.setAttribute("aria-hidden", "true");
  glyph.textContent = "*";
  const word = doc.createElement("span");
  word.className = "visually-hidden";
  /* The trailing space is load-bearing. Without it the mark and the subject
   * concatenate in `textContent` -- measured as "*starredCentral Assistance
   * for the Godavari..." -- and a screen reader announces "starredCentral" as
   * one word. The glyph's `margin-right` separates them for the eye only; a
   * reader who hears the page needs an actual character. */
  word.textContent = "starred ";
  wrap.append(glyph, word);
  return wrap;
}

/** The question type as a word, for the meta line. Never a colour, never a
 * glyph alone. An unrecognised value says so instead of being bucketed. */
export function typeWord(type) {
  if (type === STARRED) return "starred";
  if (type === UNSTARRED) return "unstarred";
  return isMissing(type) ? NOT_STATED : String(type);
}

/* ---------------------------------------------------------------------- */
/* Figure against its denominator (T124, FR-114, FR-120)                  */
/* ---------------------------------------------------------------------- */

/* Every figure on this page is shown next to the total it was drawn from, as
 * ONE typographic unit -- not a figure with its basis in a footnote. "4 of 4
 * identified", "240 of 544 members", "6,254 of 95,268 questions".
 *
 * Why a helper rather than a convention: a convention gets followed in the
 * place it was written and forgotten in the next view. The denominator is the
 * standard the rest of the published record holds to, and a chart or a row
 * that drops it is the defect FR-120 exists to prevent.
 *
 * On `value <= total`: it usually holds and deliberately is not enforced. The
 * published `question` counting basis records an overlap that makes it false
 * on purpose -- a partly-resolved question is counted both in its identified
 * askers' files and in the unresolved total, "so a per-member total and the
 * unresolved total deliberately overlap, and adding them is wrong". A pairing
 * that crosses that overlap passes `note` so the basis travels with the
 * figure, rather than rendering a quietly impossible percentage.
 */

/**
 * @param {number} value  the count
 * @param {number} total  the denominator it was drawn from
 * @param {object} [opts]
 * @param {string} [opts.unit]  what is counted, as a word: "question",
 *   "member", "state-question". Keys `aggregates/counting-basis.jsonl`.
 * @param {string} [opts.label] what the figure is OF, e.g. "identified"
 * @param {string} [opts.note]  a basis caveat that must travel with it
 */
export function figure(value, total, { unit, label, note } = {}, doc = document) {
  const wrap = doc.createElement("span");
  wrap.className = "figure";

  const n = doc.createElement("b");
  n.className = "figure-value";
  n.textContent = count(value);
  wrap.append(n);

  // "of <total>" is NOT optional. A figure with no denominator does not get
  // rendered by this helper at all -- it says "not stated" instead, because a
  // bare count is the thing the helper exists to prevent.
  const denom = doc.createElement("span");
  denom.className = "figure-denominator";
  denom.textContent =
    typeof total === "number" && Number.isFinite(total)
      ? ` of ${count(total)}`
      : ` of ${NOT_STATED}`;
  wrap.append(denom);

  if (label) {
    const what = doc.createElement("span");
    what.className = "figure-label";
    what.textContent = ` ${label}`;
    wrap.append(what);
  }
  if (unit) wrap.dataset.unit = unit;
  if (note) {
    const caveat = doc.createElement("span");
    caveat.className = "figure-note";
    caveat.textContent = note;
    wrap.append(caveat);
  }
  return wrap;
}

/** The same pairing as plain text, for a chart label or an aria-label where an
 * element cannot go. Identical wording, so the two can never diverge. */
export function figureText(value, total, { label } = {}) {
  const head = `${count(value)} of ${
    typeof total === "number" && Number.isFinite(total) ? count(total) : NOT_STATED
  }`;
  return label ? `${head} ${label}` : head;
}
