/* THE DRIFT TEST. T079.
 *
 * `web/lib/tokenise.js` and `src/sansad/publish/search_index.py` implement the
 * same rule in two languages. Nothing in either file fails when they diverge:
 * the index stores a word under one spelling, the page looks it up under
 * another, the lookup misses, and the page honestly reports no results for a
 * word that is in the index.
 *
 * So the PYTHON side writes `python-parity-golden.json` -- its stopwords, its
 * minimum token length and its exact output for every case -- and this asserts
 * the JavaScript side against it, case by case. The other half of the pair is
 * `tests/unit/test_page_search_view.py`, which re-runs the generator with
 * `--check` and fails if the committed golden has gone stale against the live
 * Python tokeniser.
 *
 * PROVEN TO FAIL, not assumed to -- executed 2026-10-10, three mutations, one
 * at a time:
 *
 *   JS MIN_TOKEN_LENGTH 3 -> 4      5 of 11 tests fail; "68 of 358 case(s)
 *                                   disagree with the Python tokeniser"
 *   JS stopwords lose "all"         2 of 11 fail: the stopword assertion and
 *                                   the per-case parity
 *   PYTHON stopwords lose "all"     node still passes (it is the golden it
 *                                   agrees with), and
 *                                   `write_tokeniser_golden.py --check` exits
 *                                   1: "stopwords: -['all'] +[]", naming the
 *                                   2 cases that moved
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { test } from "node:test";

import {
  DROPPED_NO_LETTERS,
  DROPPED_STOPWORD,
  DROPPED_TOO_SHORT,
  MIN_TOKEN_LENGTH,
  STOPWORDS,
  tokenise,
  tokeniseQuery,
} from "../../web/lib/tokenise.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const GOLDEN = JSON.parse(readFileSync(join(HERE, "python-parity-golden.json"), "utf8"));

/* ---------------------------------------------------------------------- */
/* Parity with the Python tokeniser                                       */
/* ---------------------------------------------------------------------- */

test("the golden file is present and is not trivially small", () => {
  // A golden that lost its cases would turn every assertion below into a
  // vacuous pass, which is the one failure mode a golden file has.
  assert.ok(Array.isArray(GOLDEN.cases), "the golden has no cases array");
  assert.ok(GOLDEN.cases.length > 300, `only ${GOLDEN.cases.length} case(s) in the golden`);
  assert.ok(
    GOLDEN.cases.some((c) => c.tokens.length > 2),
    "no case in the golden produces more than two tokens; the corpus looks wrong",
  );
});

test("the stopword list is the Python side's, exactly", () => {
  assert.deepEqual([...STOPWORDS].sort(), GOLDEN.stopwords);
  assert.equal(STOPWORDS.size, GOLDEN.stopwords.length);
});

test("the minimum token length is the Python side's", () => {
  assert.equal(MIN_TOKEN_LENGTH, GOLDEN.min_token_length);
});

test("every golden case tokenises identically in JavaScript", () => {
  const wrong = [];
  for (const { input, tokens } of GOLDEN.cases) {
    const mine = [...tokenise(input)].sort();
    if (JSON.stringify(mine) !== JSON.stringify(tokens)) {
      wrong.push({ input, python: tokens, javascript: mine });
    }
  }
  assert.deepEqual(
    wrong,
    [],
    `${wrong.length} of ${GOLDEN.cases.length} case(s) disagree with the Python tokeniser`,
  );
});

test("the boundaries the rule is a decision about are actually in the corpus", () => {
  // Without this the parity test above could pass over a corpus that happened
  // to miss every edge: the assertion would be true and worthless.
  const inputs = new Set(GOLDEN.cases.map((c) => c.input));
  for (const required of ["", "the", "ab", "abc", "water water water", "COVID-19", "06243"]) {
    const shown = required === "" ? "(the empty string)" : JSON.stringify(required);
    assert.ok(inputs.has(required), `the corpus is missing the boundary case ${shown}`);
  }
  const byInput = new Map(GOLDEN.cases.map((c) => [c.input, c.tokens]));
  assert.deepEqual(byInput.get(""), [], "the empty string must produce nothing");
  assert.deepEqual(byInput.get("the"), [], "a stopword alone must produce nothing");
  assert.deepEqual(byInput.get("ab"), [], "a two-character token is below the minimum");
  assert.deepEqual(byInput.get("abc"), ["abc"], "a three-character token is at the minimum");
  assert.deepEqual(
    byInput.get("water water water"),
    ["water"],
    "a repeated term is ONE term: the tokeniser returns a set",
  );
  // Unicode: Python's isalnum() covers the letter categories, so an
  // ASCII-only split in JavaScript would fail here and nowhere else.
  const unicode = GOLDEN.cases.find((c) => c.input === "Śrī Lanka");
  assert.ok(unicode, "the corpus lost its Unicode case");
  assert.deepEqual([...tokenise("Śrī Lanka")].sort(), unicode.tokens);
});

/* ---------------------------------------------------------------------- */
/* tokeniseQuery -- the part the index does not have an opinion about     */
/* ---------------------------------------------------------------------- */

test("a query's words come out in the order typed, de-duplicated", () => {
  const { words, ignored, empty } = tokeniseQuery("Drinking Water drinking");
  assert.deepEqual(words, ["drinking", "water"]);
  assert.deepEqual(ignored, []);
  assert.equal(empty, false);
});

test("a word the rule drops is NAMED, with the reason", () => {
  const { words, ignored } = tokeniseQuery("the water of ab");
  assert.deepEqual(words, ["water"]);
  // The reason is the FIRST condition the word failed, in the order the
  // Python tokeniser applies them: `len(token) >= 3 and token not in
  // STOPWORDS`. So "of" is reported as too short, which it is, rather than as
  // a stopword, which it also is.
  assert.deepEqual(ignored, [
    { word: "the", reason: DROPPED_STOPWORD },
    { word: "of", reason: DROPPED_TOO_SHORT },
    { word: "ab", reason: DROPPED_TOO_SHORT },
  ]);
});

test("a query the rule empties says so, and still names what it dropped", () => {
  const { words, ignored, empty, blank } = tokeniseQuery("the and of");
  assert.deepEqual(words, []);
  assert.equal(empty, true);
  assert.equal(blank, false);
  assert.deepEqual(
    ignored.map((i) => i.word),
    ["the", "and", "of"],
  );
});

test("a blank query is distinguished from one the rule emptied", () => {
  for (const blankQuery of ["", "   ", "\t\n"]) {
    const result = tokeniseQuery(blankQuery);
    assert.equal(result.empty, true);
    assert.equal(result.blank, true, `${JSON.stringify(blankQuery)} should be blank`);
    assert.deepEqual(result.ignored, []);
  }
});

test("punctuation only is empty but not blank, and reports no ignored word", () => {
  const result = tokeniseQuery("!!! ... ---");
  assert.equal(result.empty, true);
  assert.equal(result.blank, false);
  assert.equal(result.noLetters, true);
  assert.deepEqual(result.ignored, [], "there was no word to ignore");
  assert.ok(DROPPED_NO_LETTERS.length > 0, "the reason string exists for the page to show");
});

test("a query is split on the same rule as a subject, so punctuation is not a word", () => {
  // `drinking-water` is TWO terms in the index, because the index split it
  // that way. A query tokenised any other way would miss it.
  assert.deepEqual(tokeniseQuery("drinking-water").words, ["drinking", "water"]);
  assert.deepEqual([...tokenise("drinking-water")].sort(), ["drinking", "water"]);
  assert.deepEqual(tokeniseQuery("don't").words, ["don"]);
});
