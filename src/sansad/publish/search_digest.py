"""T079's per-session search digest and asker-name lookup.

**Owner decision 2026-10-10.** A search result shows a subject, a date, a
ministry and the asking members. Resolving a hit through the `by-session`
question partitions was MEASURED and rejected: the first 25 results for a
common word cost **4,348,529 B** -- the 2,484,758 B index plus one median
1,863,771 B partition -- which is **+3.9%** over T019's 4,183,979 B first-load
budget, and a two-word query spanning two sessions cost **7,236,751 B,
+73.0%**. The index was never the problem; the partitions were.

So the digest republishes, per session, only the six fields a result card
shows. It adds bytes to the dataset to save bytes on a page load, which is the
trade T019 exists to arbitrate.

## One format, not two, and this is a deliberate departure

`contracts/published-dataset.md` says each published set is in both NDJSON and
CSV. The digest and the name lookup are **NDJSON only**, following the
`search/subject-index.json` precedent rather than the dataset rule, for a
reason that does not apply to the other sets:

**the digest contains no information that is not already published in both
formats.** Every field is a copy of a `by-session` field, and every name is a
copy of a `reference/members` field -- both of which ship as NDJSON *and* CSV.
A consumer who wants this data as CSV already has it. A CSV digest would be a
*third* copy of the same records, published for a reader who does not exist,
on a file whose entire purpose is to be the cheapest possible fetch.

The contract's rule protects a consumer's choice of format over the dataset.
It is not protecting anything here, and `search/` is already the one directory
where that rule does not hold.

## What is NOT in it

No member attribute beyond the four the name lookup carries -- `member_id`,
`canonical_name`, `party`, `state` -- every one of which is already in
`Member.PUBLISHED_FIELDS`. The lookup is built from the *published* member
records, not from the upstream payload, so it cannot introduce an attribute
that never passed the FR-008 allowlist. It carries only members who actually
appear as an asker: publishing the whole roster here would publish names the
search can never show.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from sansad.model.member import Member
from sansad.model.question import Question
from sansad.publish.search_index import SEARCH_DIR_NAME

__all__ = [
    "ASKER_NAMES_NAME",
    "DIGEST_DIR_NAME",
    "DIGEST_FIELDS",
    "NAME_FIELDS",
    "SearchDigestResult",
    "asker_name_rows",
    "digest_row",
    "session_file_name",
    "write_search_digest",
]

#: Under `search/`, beside the index it serves.
DIGEST_DIR_NAME = "digest"
ASKER_NAMES_NAME = "asker-names.jsonl"

#: Published on `manifest.json` (owner decision 2026-10-10). Both sets stay
#: under `search/` and are NOT promoted to the top level: `asker-names.jsonl`
#: is a strictly smaller projection of `reference/members.jsonl`, no consumer
#: has asked for it, and promoting it would create a stability promise about a
#: file that exists to make one page cheap.
SEARCH_SETS_NOTE = (
    "Everything under search/ -- subject-index.json, digest/ and "
    "asker-names.jsonl -- is an aid for this project's own page, not a "
    "separate claim about the record. A consumer can skip it entirely: every "
    "field in digest/ is a copy of a by-session field and every name in "
    "asker-names.jsonl is a copy of a reference/members field, both of which "
    "are published in NDJSON and CSV. These three are the only published sets "
    "not in both formats."
)

#: Exactly the fields a result card shows. Adding one here adds bytes to every
#: search, so it is a decision rather than a convenience.
DIGEST_FIELDS: tuple[str, ...] = (
    "question_id",
    "subject",
    "date",
    "ministry_id",
    "resolution_status",
    "asking_members",
)

#: The four the lookup publishes. All four are in `Member.PUBLISHED_FIELDS`;
#: `tests/contract/test_search_digest.py` asserts that rather than trusting it.
NAME_FIELDS: tuple[str, ...] = ("member_id", "canonical_name", "party", "state")


@dataclass(frozen=True, slots=True)
class SearchDigestResult:
    """What was written, for the measurement in `spike/size-budget.md`."""

    digest_files: tuple[Path, ...]
    names_file: Path
    records: int
    askers: int
    bytes_written: int


def session_file_name(question_id: str) -> str:
    """`lok-sabha/17/4/starred/12` -> `lok-sabha-17-4.jsonl`.

    The same stem `by-session/` uses, so a reader can line the two up, and so
    a page that knows a `question_id` knows the file without an index lookup.
    """
    parts = question_id.split("/")
    if len(parts) < 3:
        raise ValueError(f"not a question_id: {question_id!r}")
    return f"{parts[0]}-{parts[1]}-{parts[2]}.jsonl"


def digest_row(question: Question) -> dict[str, object]:
    """One record. Field order is fixed, so two builds are byte-identical."""
    return {
        "question_id": question.question_id,
        "subject": question.subject,
        "date": question.date,
        "ministry_id": question.ministry_id,
        "resolution_status": question.resolution_status.value,
        "asking_members": list(question.asking_members),
    }


def asker_name_rows(
    questions: Iterable[Question], members: Sequence[Member]
) -> list[dict[str, object]]:
    """Only the members who actually appear as an asker, sorted by id."""
    askers: set[str] = set()
    for question in questions:
        askers.update(question.asking_members)
    by_id: Mapping[str, Member] = {m.member_id: m for m in members}
    rows: list[dict[str, object]] = []
    for member_id in sorted(askers):
        member = by_id.get(member_id)
        if member is None:
            # An asker with no member record would be a join this project
            # published and cannot explain. Fail rather than drop it: the
            # contract's guarantee 3 says every join is verifiable.
            raise ValueError(f"asking member {member_id!r} has no published member record")
        rows.append(
            {
                "member_id": member.member_id,
                "canonical_name": member.canonical_name,
                "party": member.party,
                "state": member.state,
            }
        )
    return rows


def _write_ndjson(path: Path, rows: Iterable[Mapping[str, object]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows
    )
    path.write_text(body, encoding="utf-8")
    return len(body.encode("utf-8"))


def write_search_digest(
    directory: Path, questions: Sequence[Question], members: Sequence[Member]
) -> SearchDigestResult:
    """Write one digest file per session, plus the asker-name lookup.

    Rows are sorted by `question_id` within each file and the files are written
    in sorted order, so two refreshes over the same data produce byte-identical
    output -- which matters because the snapshot is force-pushed as a single
    commit with no history to diff an unexplained change against.
    """
    root = Path(directory) / SEARCH_DIR_NAME / DIGEST_DIR_NAME
    root.mkdir(parents=True, exist_ok=True)

    by_session: dict[str, list[Question]] = {}
    for question in questions:
        by_session.setdefault(session_file_name(question.question_id), []).append(question)

    written: list[Path] = []
    total_bytes = 0
    records = 0
    for name in sorted(by_session):
        rows = [digest_row(q) for q in by_session[name]]
        rows.sort(key=lambda row: str(row["question_id"]))
        path = root / name
        total_bytes += _write_ndjson(path, rows)
        written.append(path)
        records += len(rows)

    names_path = Path(directory) / SEARCH_DIR_NAME / ASKER_NAMES_NAME
    name_rows = asker_name_rows(questions, members)
    total_bytes += _write_ndjson(names_path, name_rows)

    return SearchDigestResult(
        digest_files=tuple(written),
        names_file=names_path,
        records=records,
        askers=len(name_rows),
        bytes_written=total_bytes,
    )
