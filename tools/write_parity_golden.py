#!/usr/bin/env python3
"""Write (and check) the Python/JavaScript parity golden the page's tests read.

T079. The page duplicates exactly TWO rules out of Python into JavaScript, and
this file is what stops them drifting apart in silence.

**Rule 1 -- the tokeniser.** `src/sansad/publish/search_index.py` tokenises the
subjects that go INTO the published index. `web/lib/tokenise.js` tokenises the
query a visitor types. If those two ever disagree, the page silently stops
finding things: a word the index stored under one spelling is looked up under
another, the lookup misses, and the page says "no results" with no error
anywhere. Nothing in either file would fail.

**Rule 2 -- the status bucket.** `src/sansad/views/ministry_profile.py` decides
which of the four link-status buckets one question falls in, and
`web/lib/profile.js` -> `questionBucket` makes the same decision over the two
fields the search digest publishes. The order of the tests is load-bearing
(`ambiguous` before the asker check), and a page that got that order wrong
would report an ambiguous question as "Not linked" -- a different claim about
the same record, shown beside counts that say otherwise.

So each pair is pinned to one artefact. The **Python** side writes
`tests/page/python-parity-golden.json`: its stopword list, its minimum token
length, the exact tokens it produces for every input in the corpus, and the
bucket it assigns to every status case. The
**Node** side (`tests/page/tokenise.test.mjs`) reads that file and asserts the
JavaScript tokeniser produces the same tokens, carries the same stopwords and
the same minimum length. `tests/unit/test_page_search_view.py` runs `--check`
here, which regenerates in memory and fails if the committed file no longer
matches the live Python tokeniser.

The three ways the pair can drift, and which check catches each:

| Change | Caught by |
|---|---|
| Python side edited, golden not regenerated | `--check` (pytest) |
| Golden regenerated, JS not updated | `node --test` |
| JS side edited | `node --test` |

**The corpus is committed inside the golden**, deliberately. Regeneration reads
the `input` strings out of the existing file and re-tokenises them, so the check
runs with no `data/published/` present — the dataset is git-ignored on `main`,
and a drift test that skipped itself in CI would be a drift test in name only.
`--refresh-corpus` is the one mode that reads the published digest, and it is
run by hand when the corpus should be re-sampled, never by a test.

The corpus is **real subject lines plus crafted edge cases**. The real lines are
what the index actually contains; the crafted ones cover the boundaries no
sample is guaranteed to hit — a stopword alone, a two-character token, digits,
an apostrophe, a hyphen, a repeated token (the tokeniser returns a SET, so a
word twice is one token), and a string with nothing left after the rule.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from sansad.model._common import House, ResolutionStatus  # noqa: E402
from sansad.model.question import Question  # noqa: E402
from sansad.publish.search_index import (  # noqa: E402
    MIN_TOKEN_LENGTH,
    STOPWORDS,
    tokenise,
)
from sansad.views.ministry_profile import STATUS_COUNT_FIELDS, _bucket  # noqa: E402

GOLDEN = REPO_ROOT / "tests" / "page" / "python-parity-golden.json"
DIGEST = REPO_ROOT / "data" / "published" / "search" / "digest"

#: Every line whose position in its session file is a multiple of this is
#: sampled. A stride rather than `random.sample` so the corpus is the same on
#: every machine with no seed to remember, and so re-running it over an
#: unchanged dataset rewrites nothing.
#:
#: 331 was chosen to keep the file under the 64 KB payload ceiling
#: `make guard` applies to `tests/` -- a golden that tripped the guard would be
#: a check that gets deleted rather than one that gets fixed.
CORPUS_STRIDE = 331

#: The boundaries of the rule, written out rather than hoped for. Each one is a
#: case the tokeniser's behaviour is a DECISION about, not an accident:
#: `MIN_TOKEN_LENGTH` is 3, the stopword list is applied after lowercasing, the
#: split is on anything Python calls non-alphanumeric, and the result is a set.
CRAFTED: tuple[str, ...] = (
    "",
    "   ",
    "the",
    "THE",
    "the and of to in",
    "a an and are as at be been by",
    "ab",
    "abc",
    "ab cd ef",
    "water",
    "WATER",
    "Water",
    "wAtEr",
    "water water water",
    "water, water; water.",
    "drinking water",
    "drinking-water",
    "drinking_water",
    "drinking   water",
    "  drinking water  ",
    "water\twater\nwater",
    "Pradhan Mantri Awas Yojana",
    "PM-KISAN",
    "COVID-19",
    "covid 19",
    "19",
    "2019",
    "06243",
    "123 4567 89",
    "Rs. 100 crore",
    "don't",
    "dont",
    "India's exports",
    "A.I.I.M.S.",
    "AIIMS, Madurai",
    "National Highways (NH-44)",
    "50% of schools",
    "e-governance",
    "e governance",
    "Jal Jeevan Mission/Har Ghar Jal",
    "scheme & programme",
    "the scheme of the government for the people",
    "no any all not",
    "there these this that",
    "will with were was",
    "has have is it its",
    "from for in into of on or to",
    "Ministry of Women and Child Development",
    "Setting up of New AIIMS",
    "Non-Performing Assets",
    "x",
    "xy",
    "xyz",
    "----",
    "...",
    "!!!",
    "a-b-c",
    "ABC abc AbC",
    "Śrī Lanka",
    "naïve scheme",
)


#: Rule 2's corpus: every (status, asker-count) combination the digest can
#: carry, including the two that look alike and are not -- an ambiguous
#: question (no askers published, by design) and an unresolved one with no
#: askers. `_bucket` separates them by testing `ambiguous` FIRST, and a
#: JavaScript copy that tested the asker list first would collapse them.
STATUS_CASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("resolved", ("ls-1",)),
    ("resolved", ("ls-1", "ls-2")),
    # `("resolved", ())` is DELIBERATELY ABSENT, and not by oversight:
    # `Question.__post_init__` REFUSES it -- "resolution_status is 'resolved'
    # with no asking_members ... never recorded as resolved to nobody". So the
    # shape cannot reach a published file, and a golden case asserting what
    # Python does with it would be asserting something about an object the
    # model will not build.
    ("ambiguous", ()),
    ("ambiguous", ("ls-1",)),
    ("unresolved", ("ls-1",)),
    ("unresolved", ("ls-1", "ls-2")),
    ("unresolved", ()),
)


def status_bucket_cases() -> list[dict[str, object]]:
    """What the PYTHON `_bucket` assigns to each case, for the JS to match."""
    rows: list[dict[str, object]] = []
    for status, askers in STATUS_CASES:
        question = Question(
            question_id="lok-sabha/18/8/starred/1",
            house=House.LOK_SABHA,
            session="lok-sabha/18/8",
            date="2026-07-20",
            type="STARRED",
            subject="parity case",
            ministry_id="culture",
            asking_members=askers,
            resolution_status=ResolutionStatus(status),
        )
        rows.append(
            {
                "resolution_status": status,
                "asking_members": list(askers),
                "bucket": _bucket(question),
            }
        )
    return rows


def sample_real_subjects() -> list[str]:
    """A deterministic stride through the published digest's subject lines."""
    if not DIGEST.is_dir():
        raise SystemExit(
            f"--refresh-corpus needs the published digest at {DIGEST}, which is not built. "
            "Run `make refresh` first, or regenerate without --refresh-corpus."
        )
    seen: set[str] = set()
    for path in sorted(DIGEST.glob("*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for position, line in enumerate(handle):
                if position % CORPUS_STRIDE:
                    continue
                subject = json.loads(line).get("subject")
                if isinstance(subject, str) and subject:
                    seen.add(subject)
    return sorted(seen)


def existing_corpus() -> list[str]:
    """The `input` strings already committed in the golden."""
    if not GOLDEN.is_file():
        raise SystemExit(
            f"no golden at {GOLDEN}. Generate one with --refresh-corpus, which samples "
            "the published digest."
        )
    document = json.loads(GOLDEN.read_text(encoding="utf-8"))
    return [case["input"] for case in document["cases"]]


def build(corpus: list[str]) -> dict[str, object]:
    """The golden document. Sorted and separator-fixed, so two runs over the
    same corpus are byte-identical and `--check` can compare text."""
    return {
        "_note": (
            "GENERATED by tools/write_tokeniser_golden.py from the PYTHON tokeniser in "
            "src/sansad/publish/search_index.py. Do not edit by hand. "
            "tests/page/tokenise.test.mjs asserts web/lib/tokenise.js agrees with every "
            "value here; tests/unit/test_page_search_view.py asserts this file still "
            "matches the live Python tokeniser."
        ),
        "min_token_length": MIN_TOKEN_LENGTH,
        "stopwords": sorted(STOPWORDS),
        # Rule 2. The key order is STATUS_COUNT_FIELDS itself, so a fifth
        # bucket added on the Python side shows up here and fails the JS
        # assertion that the two lists are equal.
        "status_buckets": list(STATUS_COUNT_FIELDS),
        "status_bucket_cases": status_bucket_cases(),
        "cases": [
            # Tokens SORTED: the Python tokeniser returns a set, so its
            # iteration order is not a property of the tokeniser and must not
            # become one of this file.
            {"input": text, "tokens": sorted(tokenise(text))}
            for text in corpus
        ],
    }


def serialise(document: dict[str, object]) -> str:
    return json.dumps(document, ensure_ascii=False, indent=1, sort_keys=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Regenerate in memory and fail if the committed golden differs. Reads no "
        "published data: the corpus comes out of the golden itself.",
    )
    parser.add_argument(
        "--refresh-corpus",
        action="store_true",
        help="Re-sample the real subject lines from data/published/search/digest/ before "
        "writing. By hand only -- no test runs this.",
    )
    args = parser.parse_args()

    if args.refresh_corpus:
        corpus = sorted({*sample_real_subjects(), *CRAFTED})
    else:
        corpus = sorted({*existing_corpus(), *CRAFTED}) if GOLDEN.is_file() else sorted(CRAFTED)

    text = serialise(build(corpus))

    if args.check:
        if not GOLDEN.is_file():
            print(f"FAIL: no golden at {GOLDEN}")
            return 1
        on_disk = GOLDEN.read_text(encoding="utf-8")
        if on_disk == text:
            document = json.loads(on_disk)
            print(
                f"parity golden: OK -- {len(document['cases'])} tokeniser case(s), "
                f"{len(document['status_bucket_cases'])} status-bucket case(s), "
                f"{len(document['stopwords'])} stopword(s), "
                f"min_token_length {document['min_token_length']}, "
                f"{len(on_disk.encode('utf-8')):,} B"
            )
            return 0
        print("parity golden: STALE -- the Python side no longer agrees with the file.")
        print(f"  file : {GOLDEN}")
        print("  Regenerate with: python3 tools/write_parity_golden.py")
        old = json.loads(on_disk)
        new = json.loads(text)
        if old["stopwords"] != new["stopwords"]:
            removed = sorted(set(old["stopwords"]) - set(new["stopwords"]))
            added = sorted(set(new["stopwords"]) - set(old["stopwords"]))
            print(f"  stopwords: -{removed} +{added}")
        if old["min_token_length"] != new["min_token_length"]:
            print(f"  min_token_length: {old['min_token_length']} -> {new['min_token_length']}")
        if old.get("status_buckets") != new["status_buckets"]:
            print(f"  status_buckets: {old.get('status_buckets')} -> {new['status_buckets']}")
        old_buckets = {
            (c["resolution_status"], tuple(c["asking_members"])): c["bucket"]
            for c in old.get("status_bucket_cases", [])
        }
        for case in new["status_bucket_cases"]:
            key = (case["resolution_status"], tuple(case["asking_members"]))
            if old_buckets.get(key, object()) != case["bucket"]:
                print(f"  bucket {key}: was {old_buckets.get(key)!r}, now {case['bucket']!r}")
        old_cases = {c["input"]: c["tokens"] for c in old["cases"]}
        differing = [
            c["input"] for c in new["cases"] if old_cases.get(c["input"], object()) != c["tokens"]
        ]
        if differing:
            print(f"  {len(differing)} case(s) tokenise differently, first few:")
            for text_in in differing[:5]:
                print(
                    f"    {text_in!r}: was {old_cases.get(text_in)!r}, "
                    f"now {sorted(tokenise(text_in))!r}"
                )
        return 1

    GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN.write_text(text, encoding="utf-8")
    size = len(text.encode("utf-8"))
    document = json.loads(text)
    print(
        f"wrote {GOLDEN.relative_to(REPO_ROOT)} -- {len(document['cases'])} tokeniser "
        f"case(s), {len(document['status_bucket_cases'])} status-bucket case(s), "
        f"{len(document['stopwords'])} stopword(s), {size:,} B"
    )
    ceiling = 64 * 1024
    if size > ceiling:
        print(
            f"  REFUSED SHAPE: {size:,} B is over the {ceiling:,} B payload ceiling "
            "`make guard` applies to tests/. Raise CORPUS_STRIDE and regenerate."
        )
        return 1
    print(f"  {100 * size / ceiling:.1f}% of the {ceiling:,} B guard ceiling for tests/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
