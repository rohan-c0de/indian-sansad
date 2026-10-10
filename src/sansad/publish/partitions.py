"""T051 -- the question partitions, on the three axes FR-007 names.

`data/published/by-session/`, `by-ministry/` and `by-member/`, each in both
formats. The same question records republished under different keys, which is
why `contracts/published-dataset.md` guarantee 6 tells a consumer combining
partitions to **de-duplicate on `question_id` rather than sum**.

## Why the dataset history is one commit deep

Owner decision 2026-10-09 (`spike/size-budget.md`). Writing these partitions is
what begins committing **216.5 MiB measured** per refresh. That breaches
GitHub's "ideally less than 1 GB" guidance on about the **fifth** refresh and
the 5 GB figure within twenty-four, so full history was rejected; publishing
only changed partitions slows the growth without bounding it. A **rolling
orphan branch** bounds it, because the dataset's history is one commit deep at
all times.

**This module writes files into a directory and does no git.** The directory
the workflow passes is a worktree of the `published` branch; committing it as a
single force-pushed commit on success, and pushing **nothing** on a failed or
partial refresh so the previous snapshot keeps being served (FR-010), is the
scheduled workflow's job (T058, which owns the publish mechanism). Keeping the
git mechanics out of here is deliberate: a module that could push is a module
that can push a partial dataset.

`data/published/` is **git-ignored on `main`** -- it is a build output and must
never be committed there.

## Three rules the partitioning obeys

1. **A co-asked question appears in each asker's file and is never duplicated
   per asker** (FR-003). One record per question per file. The same question
   genuinely appears in several *files*; it never appears twice in one.
2. **An unresolved question still gets published.** It has no `member_id`, so it
   reaches no by-member file -- but it is in its session's and its ministry's
   partition carrying `resolution_status`, because "a consumer filtering on
   `resolution_status == "resolved"` is making an explicit choice, not receiving
   a default" (guarantee 2).
3. **File names are keyed on ids, never on display names.** A session id carries
   slashes (`lok-sabha/17/1`) so it is slugged for the filename; the id inside
   the records is untouched. A confirmed ministry rename changes the display
   name and not the id, so it does not rename a published file.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from sansad.model._common import ResolutionStatus
from sansad.model.question import Question
from sansad.publish.attribution import WHOLE_DATASET_FIELDS
from sansad.publish.formats import CSV_SUFFIX, NDJSON_SUFFIX, rows_for, write_both

__all__ = [
    "BY_MEMBER_DIR",
    "BY_MINISTRY_DIR",
    "BY_SESSION_DIR",
    "PARTITION_MANIFEST_NAME",
    "PartitionResult",
    "partition_key",
    "write_manifest",
    "write_partitions",
]

BY_SESSION_DIR = "by-session"
BY_MINISTRY_DIR = "by-ministry"
BY_MEMBER_DIR = "by-member"

#: Guarantee 7 -- "Every published set carries the date it was last rebuilt
#: (FR-016)." Each record carries `last_refreshed`; this carries it for the
#: **set**, together with the file and record counts a consumer needs to tell a
#: complete snapshot from a truncated one.
PARTITION_MANIFEST_NAME = "manifest.json"


def partition_key(value: str) -> str:
    """A filesystem-safe key for an id that may contain separators.

    `lok-sabha/17/1` becomes `lok-sabha-17-1`. The id inside the published
    records is **not** rewritten -- only the filename -- so a consumer joining
    on `session` still matches the reference set.
    """
    safe = "".join(ch if ch.isalnum() or ch in "-_." else "-" for ch in value.strip())
    while "--" in safe:
        safe = safe.replace("--", "-")
    return safe.strip("-") or "not-stated"


@dataclass(frozen=True, slots=True)
class PartitionResult:
    """What one axis wrote."""

    axis: str
    files: int
    records: int
    bytes_ndjson: int
    bytes_csv: int


def _write_axis(
    root: Path, axis: str, grouped: Mapping[str, Sequence[Question]]
) -> PartitionResult:
    directory = root / axis
    files = records = ndjson_bytes = csv_bytes = 0
    for key in sorted(grouped):
        questions = grouped[key]
        rows = rows_for(questions)
        stem = partition_key(key)
        write_both(directory, stem, rows)
        files += 2
        records += len(rows)
        ndjson_bytes += (directory / f"{stem}{NDJSON_SUFFIX}").stat().st_size
        csv_bytes += (directory / f"{stem}{CSV_SUFFIX}").stat().st_size
    return PartitionResult(
        axis=axis,
        files=files,
        records=records,
        bytes_ndjson=ndjson_bytes,
        bytes_csv=csv_bytes,
    )


def write_partitions(directory: Path, questions: Iterable[Question]) -> tuple[PartitionResult, ...]:
    """Write all three question partitions, both formats.

    One pass over the questions builds all three groupings, because the window
    is ~10^5 records and three passes would be three reads for no gain.
    """
    materialised = list(questions)
    by_session: dict[str, list[Question]] = {}
    by_ministry: dict[str, list[Question]] = {}
    by_member: dict[str, list[Question]] = {}

    for question in materialised:
        by_session.setdefault(question.session, []).append(question)
        by_ministry.setdefault(question.ministry_id, []).append(question)
        # A co-asked question lands in each asker's file, once each. An
        # unresolved or ambiguous one has no asker and lands in none -- it is
        # still published on the other two axes, carrying its status.
        for member_id in question.asking_members:
            by_member.setdefault(member_id, []).append(question)

    root = Path(directory)
    return (
        _write_axis(root, BY_SESSION_DIR, by_session),
        _write_axis(root, BY_MINISTRY_DIR, by_ministry),
        _write_axis(root, BY_MEMBER_DIR, by_member),
    )


def write_manifest(
    directory: Path,
    *,
    last_refreshed: str,
    sets: Mapping[str, Mapping[str, int]],
    extra: Mapping[str, object] | None = None,
) -> Path:
    """Write the set-level rebuild stamp (guarantee 7, FR-016).

    Sorted keys and a trailing newline, so two refreshes over the same data
    produce a byte-identical file: the snapshot is force-pushed as one commit
    and an unexplained diff in a one-commit-deep history cannot be diffed
    against anything.
    """
    path = Path(directory) / PARTITION_MANIFEST_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    body: dict[str, object] = {
        # The licence and the source-terms disclosure are applied HERE rather
        # than passed in by the caller, so a refresh cannot publish a manifest
        # without them by forgetting an argument. `extra` is applied after, and
        # deliberately cannot override these -- see the guard below.
        **WHOLE_DATASET_FIELDS,
        "last_refreshed": last_refreshed,
        "sets": {name: dict(counts) for name, counts in sorted(sets.items())},
    }
    if extra:
        overridden = sorted(set(extra) & set(WHOLE_DATASET_FIELDS))
        if overridden:
            raise ValueError(
                "manifest `extra` may not override the licence or source-terms "
                f"fields: {overridden}"
            )
        body.update(extra)
    path.write_text(
        json.dumps(body, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def unresolved_are_published(questions: Iterable[Question]) -> bool:
    """Whether every unresolved question still reaches a published partition.

    Guarantee 2's structural form. True when each one has a session and a
    ministry to be published under -- which is what keeps it in the record with
    its status rather than dropped for lacking an asker.
    """
    return all(
        bool(q.session and q.ministry_id)
        for q in questions
        if q.resolution_status is not ResolutionStatus.RESOLVED
    )
