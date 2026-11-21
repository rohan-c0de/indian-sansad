/* The query tokeniser. T079.
 *
 * This is the SECOND copy of a rule, and that is the problem it has to solve.
 *
 * `src/sansad/publish/search_index.py` tokenises the subject lines that go
 * INTO the published index. This tokenises the query a visitor types. If the
 * two ever disagree, the page stops finding things with no error anywhere: a
 * word stored under one spelling is looked up under another, the lookup
 * misses, and the page truthfully reports no results for a word that is in
 * the index. Nothing in either file would fail, and nobody would know.
 *
 * So the two are pinned to one artefact rather than to good intentions.
 * `tools/write_parity_golden.py` has the PYTHON tokeniser write
 * `tests/page/python-parity-golden.json` -- its stopwords, its minimum token
 * length, and its exact output for 358 inputs, most of them real published
 * subject lines. `tests/page/tokenise.test.mjs` asserts every value here
 * against that file, and `tests/unit/test_page_search_view.py` asserts the
 * file still matches the live Python side. Editing either tokeniser without
 * the other fails a test.
 *
 * Owner decision 2026-10-10: the query is tokenised EXACTLY as the index was
 * built -- same lowercasing, same split, same minimum length, same stopwords,
 * no stemming. Words the rule drops are listed to the visitor rather than
 * silently discarded, which is what `tokeniseQuery` returns alongside them.
 */

/** T018's 36 stopwords, verbatim. The golden file asserts this set. */
export const STOPWORDS = Object.freeze(
  new Set([
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "there",
    "these",
    "this",
    "to",
    "was",
    "were",
    "will",
    "with",
    "not",
    "no",
    "any",
    "all",
  ]),
);

/** T018's minimum token length. */
export const MIN_TOKEN_LENGTH = 3;

/* Python's `str.isalnum()` is true for the Unicode letter and number
 * categories, so the split is on `\p{L}\p{N}` and NOT on `[a-z0-9]`. The
 * difference is not theoretical: the published subjects contain `Śrī` and
 * `naïve`, and an ASCII-only class would split those into fragments the index
 * does not contain. Both are in the golden corpus for that reason. */
const ALNUM = /[\p{L}\p{N}]/u;

/**
 * Split `text` into index terms. Mirrors the Python `tokenise` exactly.
 *
 * Returns a Set, because a term appearing twice in one string is one term --
 * the Python side returns a set for the same reason (it is one posting).
 */
export function tokenise(text) {
  const out = new Set();
  if (typeof text !== "string" || text.length === 0) return out;
  let current = "";
  const take = () => {
    if (current.length >= MIN_TOKEN_LENGTH && !STOPWORDS.has(current)) out.add(current);
    current = "";
  };
  for (const char of text.toLowerCase()) {
    if (ALNUM.test(char)) current += char;
    else take();
  }
  take();
  return out;
}

/** Why one word of a query was dropped. Shown to the visitor verbatim. */
export const DROPPED_TOO_SHORT = "shorter than 3 characters";
export const DROPPED_STOPWORD = "a very common word the index does not store";
export const DROPPED_NO_LETTERS = "no letters or digits";

/**
 * Tokenise a visitor's query the way the index was built, and say what the
 * rule dropped.
 *
 * Returns:
 *   words   -- the terms to look up, in first-appearance order, de-duplicated
 *   ignored -- [{ word, reason }] for every word the rule dropped
 *   empty   -- true when the rule left nothing to look up
 *
 * `ignored` is the point of this function existing at all. A visitor who
 * searches "the water" and is shown results for "water" has had a word
 * silently removed from their question; being told "ignored: the" is the
 * difference between a tool and a guess.
 *
 * The words shown in `ignored` are the visitor's own, lowercased -- the split
 * is on the same rule, so a dropped word is reported as the run of
 * alphanumerics it actually was, not as the raw substring with its
 * punctuation.
 */
export function tokeniseQuery(query) {
  const words = [];
  const ignored = [];
  const seen = new Set();
  if (typeof query !== "string" || query.trim().length === 0) {
    return { words, ignored, empty: true, blank: true };
  }

  /* Split on the SAME rule as `tokenise`, but keep every run -- including the
   * ones the rule drops, which `tokenise` throws away and this must report. */
  const runs = [];
  let current = "";
  for (const char of query.toLowerCase()) {
    if (ALNUM.test(char)) current += char;
    else if (current.length > 0) {
      runs.push(current);
      current = "";
    }
  }
  if (current.length > 0) runs.push(current);

  if (runs.length === 0) {
    // Punctuation only: there is no word to report as ignored, because the
    // rule never saw one.
    return { words, ignored, empty: true, blank: false, noLetters: true };
  }

  for (const run of runs) {
    if (seen.has(run)) continue;
    seen.add(run);
    if (run.length < MIN_TOKEN_LENGTH) {
      ignored.push({ word: run, reason: DROPPED_TOO_SHORT });
    } else if (STOPWORDS.has(run)) {
      ignored.push({ word: run, reason: DROPPED_STOPWORD });
    } else {
      words.push(run);
    }
  }

  return { words, ignored, empty: words.length === 0, blank: false };
}
