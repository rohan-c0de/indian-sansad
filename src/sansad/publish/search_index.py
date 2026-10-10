"""T071 — the published subject-search index.

Written to `data/published/search/`, so in-browser subject search needs no
server. `contracts/published-dataset.md` already promises it and already states
its measured size, so the shape is not a free choice.

## The tokenisation and scope are T018's, carried over unchanged

| | |
|---|---|
| Case | lowercased |
| Split | on non-alphanumeric |
| Minimum token length | **3** |
| Stopwords | the **36** T018 used, verbatim |
| Stemming | **none** |
| Postings | delta-encoded ascending doc ids |
| Scope | **subjects only** |

**The wider scope was measured and NOT adopted, on the measurement.** T018
measured both candidates over all 34,720 questions of the 18th Lok Sabha:

| Variant | Distinct terms | Postings | Bytes | Projected to 95,269 |
|---|---|---|---|---|
| `subjects_only` — **CHOSEN** | 11,145 | 143,020 | 1,195,277 | **3,279,748 (3.13 MiB)** |
| `subjects_plus_ministry_and_member` | 11,895 | 380,537 | 1,895,621 | 5,201,438 (4.96 MiB) |

> "The wider variant is **measured but not adopted**, and adopting it is **not**
> a free change: it adds **1.83 MiB** to every visitor's download (+58.6%) for
> search over fields the page already has in its ministry and member reference
> sets."

So the narrower scope is a decision resting on a number, not a default. The
page can already filter by ministry from the ministry reference set and by
member from the member set; paying 58.6% more on every first load to duplicate
that inside the index is the trade T018 declined.

**A smaller index is achievable, and that is why this one is not smaller.**
Stemming and a longer stopword list would both shrink it. T018's reason for
declining them stands: "The measurement should reflect what a maintainer at
~2h/week would actually ship and keep working, not the floor an optimiser could
reach." Changing the tokeniser now would also void T018's measurement, and
T072's gate compares against it.

## No match grading — owner decision 2026-10-10

**The index publishes no similarity grade, score, weight or tier.** T018's
prototype stores none: a posting is a document id and nothing else. A grade
would therefore be unmeasured and unspecified, and T079 is required to list
matches in a documented fixed order with no match labelled "near-identical" or
"similar".

This is a decision about honesty rather than about effort. The index can tell a
page *how many query terms a subject matched*, and a page could sort on that —
but presenting that as "near-identical" would dress an unmeasured heuristic as a
property of the data. `tests/contract/test_search_index.py` asserts no grading
field is published, which is the only thing that keeps the decision true as the
code changes.

## What a posting points at

A posting is a position in the document list, and the document list rebuilds
`question_id` values. The page resolves an id against the published question
records to get the date, the ministry and the askers — which is why T073
asserts the ids **resolve** rather than merely exist. A question whose asker
could not be identified is indexed like any other: FR-004 reaches search too,
and a subject search that quietly omitted unlinked questions would be filtering
the record.

## Terms are VALUES, not keys — and the guard is why

An inverted index wants to be `{"term": [postings]}`. It is not, and the reason
is worth stating because it looks like a worse shape until you see it.

`tools/guard_no_raw_payloads.py` treats a prohibited spelling in a **structured
position** -- a JSON key, a CSV header, an assignment target -- as a payload,
while allowing the same word in prose. Six of its spellings are ordinary English
words it explicitly marks as prose-ambiguous: `address`, `children`,
`daughters`, `email`, `marital`, `mobile`. Its assumption is that a JSON key is
a **field name**.

In an inverted index over subject lines, every key is an English word. Real
parliamentary subjects produce exactly those six tokens, and the first build of
this index failed `make guard` on all six:

    data/published/search/subject-index.json:1: key 'mobile' is a prohibited
    'personal phone' field (Constitution Principle V)

**The guard was right and the format was wrong.** Those tokens are *data* --
words someone asked a question about -- and putting data in key position is what
made them look like field names. So terms live in a sorted `terms` array and
postings in a parallel `postings` array, which puts every token in value
position where the guard's prose/structured distinction works as designed.

**No protection was given up.** The guard still scans this file, and a
prohibited spelling it classifies as *unambiguous* -- the compound field names,
as opposed to the six plain words -- is flagged in value position too. Only
those six are allowed through, which is the behaviour the guard documents. The
index could not carry a personal attribute in any case: it indexes
`Question.subject` only, and the FR-008 allowlist drops every such attribute at
the ingest boundary long before this runs.

(Those compound names are deliberately not spelled out here. An earlier draft of
this docstring listed three of them as examples and `make guard` failed on this
file -- correctly. A module that documents a prohibition by reproducing it is the
hole the guard exists to close.)

The cost is that a browser binary-searches a sorted array instead of doing an
object lookup. `terms` is sorted for that purpose.

## The document list is encoded, and T072 is why

**Measured first, then changed.** The first build came in at **4,607,033 B
(4.39 MiB)** against T018's projected 3,279,748 B — **40.5% over**, and over
T019's first-load budget too. The breakdown said where:

| | Bytes | Share |
|---|---:|---:|
| document list, as plain `question_id` strings | 3,018,967 | **65.5%** |
| terms and postings | 1,588,027 | 34.5% |

**Both of T018's predictions held.** Distinct terms grew sub-linearly as it said
they would — 16,979 where linear scaling predicted 30,581 — and postings per
document actually *fell*, 3.70 against the 18th Lok Sabha's 4.12. The index
proper was fine. What T018 could not have projected is that `question_id` would
get **2.61x longer**: it gained `type` and the term when the 7,431-record
collision was fixed, going from `ls-17-1-500` to
`lok-sabha/17/1/starred/500`.

**So the scope was not the lever, and was not changed.** `subjects_only` is
already the narrower of the two variants T018 measured, and the tokeniser is
untouched — changing it would void the measurement T072 compares against. What
is compacted is the **document encoding**, for exactly the reason T018 gave for
delta-encoding postings: an un-encoded structure overstates the size and makes
the page look less viable than it is.

Every `question_id` is `{house}/{term}/{session}/{type}/{number}`, and the first
four parts take only a few dozen distinct values across the whole window. So the
list is stored as a prefix table plus two parallel integer arrays, and
`question_id_at` rebuilds the exact id. Nothing is lost: T073 asserts the
reconstructed ids resolve against the published records.
"""

from __future__ import annotations

import json
from bisect import bisect_left
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sansad.model.question import Question

__all__ = [
    "MIN_TOKEN_LENGTH",
    "SEARCH_DIR_NAME",
    "SEARCH_INDEX_NAME",
    "STOPWORDS",
    "SearchIndexResult",
    "build_index",
    "document_count",
    "lookup",
    "question_id_at",
    "tokenise",
    "write_search_index",
]

SEARCH_DIR_NAME = "search"
SEARCH_INDEX_NAME = "subject-index.json"

#: The 36 stopwords T018 measured with, verbatim. Changing this list changes
#: the index's size and voids T018's measurement, which T072 compares against.
STOPWORDS: frozenset[str] = frozenset(
    [
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
    ]
)

MIN_TOKEN_LENGTH = 3


def tokenise(text: str) -> set[str]:
    """T018's tokeniser, unchanged.

    A set, not a list: a term appearing twice in one subject is one posting.
    Deliberately no stemming -- see the module docstring.
    """
    if not text:
        return set()
    out: set[str] = set()
    current: list[str] = []
    for char in text.lower():
        if char.isalnum():
            current.append(char)
            continue
        if current:
            token = "".join(current)
            if len(token) >= MIN_TOKEN_LENGTH and token not in STOPWORDS:
                out.add(token)
            current = []
    if current:
        token = "".join(current)
        if len(token) >= MIN_TOKEN_LENGTH and token not in STOPWORDS:
            out.add(token)
    return out


@dataclass(frozen=True, slots=True)
class SearchIndexResult:
    """What was written, for T072's measurement."""

    path: Path
    bytes_written: int
    distinct_terms: int
    total_postings: int
    documents: int


def build_index(questions: Iterable[Question]) -> dict[str, object]:
    """Build the index. Subjects only, postings delta-encoded.

    Document order is the order questions arrive, which the publish layer has
    already sorted -- so the index is byte-identical across two refreshes over
    the same data, like every other published file.
    """
    materialised = list(questions)

    # --- the document list, prefix-encoded (see the module docstring) -------
    prefixes: list[str] = []
    prefix_index: dict[str, int] = {}
    doc_prefix: list[int] = []
    doc_number: list[str] = []
    for question in materialised:
        prefix, _, number = question.question_id.rpartition("/")
        position = prefix_index.get(prefix)
        if position is None:
            position = len(prefixes)
            prefix_index[prefix] = position
            prefixes.append(prefix)
        doc_prefix.append(position)
        doc_number.append(number)

    postings: dict[str, list[int]] = {}
    for position, question in enumerate(materialised):
        for token in tokenise(question.subject):
            postings.setdefault(token, []).append(position)

    term_list: list[str] = sorted(postings)
    posting_lists: list[list[int]] = []
    for token in term_list:
        ids = sorted(postings[token])
        deltas: list[int] = []
        previous = 0
        for value in ids:
            deltas.append(value - previous)
            previous = value
        posting_lists.append(deltas)

    return {
        # The document list, prefix-encoded. `doc_prefix[i]` indexes
        # `prefixes`; `doc_number[i]` is the trailing question number. A posting
        # is an index into these two parallel arrays.
        "prefixes": prefixes,
        "doc_prefix": doc_prefix,
        "doc_number": doc_number,
        # Terms in VALUE position, sorted, with postings in a parallel array.
        # See the module docstring: in key position, six ordinary English words
        # look like prohibited field names to the guard.
        "terms": term_list,
        "postings": posting_lists,
        # FR-016: every published set carries the date it was last rebuilt.
        "built": datetime.now(UTC).date().isoformat(),
    }


def question_id_at(index: dict[str, object], position: int) -> str:
    """Rebuild the exact `question_id` at a document position.

    The browser-side equivalent is two array reads and a concatenation, which is
    the whole reason the encoding is this shape rather than something that needs
    a decoder.
    """
    prefixes: list[str] = index["prefixes"]  # type: ignore[assignment]
    doc_prefix: list[int] = index["doc_prefix"]  # type: ignore[assignment]
    doc_number: list[str] = index["doc_number"]  # type: ignore[assignment]
    return f"{prefixes[doc_prefix[position]]}/{doc_number[position]}"


def document_count(index: dict[str, object]) -> int:
    return len(index["doc_number"])  # type: ignore[arg-type]


def lookup(index: dict[str, object], term: str) -> list[str]:
    """The `question_id` values a term resolves to. No score, by decision.

    Returned in document order, which is the publish layer's order -- a
    documented fixed order, which is what T079 is required to use.
    """
    terms: list[str] = index["terms"]  # type: ignore[assignment]
    postings: list[list[int]] = index["postings"]  # type: ignore[assignment]
    position_in_terms = bisect_left(terms, term.lower())
    if position_in_terms >= len(terms) or terms[position_in_terms] != term.lower():
        return []
    deltas = postings[position_in_terms]
    if not deltas:
        return []
    out: list[str] = []
    position = 0
    for delta in deltas:
        position += delta
        out.append(question_id_at(index, position))
    return out


def write_search_index(directory: Path, questions: Iterable[Question]) -> SearchIndexResult:
    """Write the index as one JSON file.

    One file, not NDJSON and not both formats: it is an index a browser fetches
    whole and uses as a map, not a record set a consumer reads row by row.
    `contracts/published-dataset.md` lists it separately from the record sets
    for that reason, and notes consumers "should expect the page to fetch it
    lazily, only on an actual search".
    """
    index = build_index(questions)
    root = Path(directory) / SEARCH_DIR_NAME
    root.mkdir(parents=True, exist_ok=True)
    path = root / SEARCH_INDEX_NAME
    path.write_text(
        json.dumps(index, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )
    postings: list[list[int]] = index["postings"]  # type: ignore[assignment]
    return SearchIndexResult(
        path=path,
        bytes_written=path.stat().st_size,
        distinct_terms=len(index["terms"]),  # type: ignore[arg-type]
        total_postings=sum(len(v) for v in postings),
        documents=document_count(index),
    )
