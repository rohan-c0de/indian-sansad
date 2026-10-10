"""T054 -- on a failed or shape-changed refresh, keep the previous snapshot (FR-010).

FR-010 and FR-011 pull in opposite directions and this module is one half of
that split. `sansad.signals.alerts` makes the maintainer's half loud; this
makes the visitor's half quiet: the previously published record is **retained
and re-dated as last-known-good**, rather than replaced by an empty or partial
one.

**The previous snapshot is passed in by path.** Locally it is a directory --
whatever `data/published/` held before this run. In CI it is a checkout of the
`published` branch, which the workflow does **before** overwriting anything,
because FR-010's last-known-good and FR-011's signal for a question leaving
`resolved` both need the prior record to compare against (T058 (a)).

Passing it in rather than discovering it is deliberate. A module that went
looking for the previous snapshot would have to guess where it is, and the
guess differs between a laptop and a runner -- which is exactly the kind of
difference that works until the first real failure.

## What "retained and re-dated" means, precisely

The published files are **not** rewritten. Only the Coverage Statement is, and
only to say two things: `last_known_good` becomes `last-known-good`, and
`last_refreshed` keeps the date of the **last successful** refresh rather than
today's. The second half matters: re-stamping today's date on a snapshot that
is not from today would make a stale record look fresh, which is the single
thing FR-010 is trying to prevent. The record stays "coherent and dated"
because the date it carries is the date it is actually from.

## What this module refuses to do

It will not promote an **empty or partial** directory to last-known-good. A
previous snapshot that is missing its manifest, or has no partitions, is not a
snapshot -- serving it would be presenting a partial record as complete, which
SC-006 forbids. In that case the refresh has nothing good to fall back on, and
saying so is the only honest outcome.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from sansad.model._common import NOT_STATED
from sansad.model.coverage_statement import Freshness
from sansad.publish.coverage import COVERAGE_STEM
from sansad.publish.formats import CSV_SUFFIX, NDJSON_SUFFIX, read_ndjson, write_both
from sansad.publish.partitions import (
    BY_MEMBER_DIR,
    BY_MINISTRY_DIR,
    BY_SESSION_DIR,
    PARTITION_MANIFEST_NAME,
)

__all__ = [
    "REQUIRED_SETS",
    "PreviousSnapshot",
    "inspect_previous",
    "retain_previous",
]

#: A directory must carry all of these to count as a usable snapshot. The
#: manifest alone is not enough -- it is a stamp, not the data.
REQUIRED_SETS: tuple[str, ...] = (BY_SESSION_DIR, BY_MINISTRY_DIR, BY_MEMBER_DIR)


@dataclass(frozen=True, slots=True)
class PreviousSnapshot:
    """What was found at the path the caller passed."""

    path: Path
    exists: bool
    usable: bool
    last_refreshed: str = NOT_STATED
    missing: tuple[str, ...] = ()
    question_files: int = 0

    @property
    def reason(self) -> str:
        """Why it is or is not usable, in one line, for the maintainer."""
        if not self.exists:
            return f"no previous snapshot at {self.path}"
        if not self.usable:
            return (
                f"previous snapshot at {self.path} is incomplete -- missing "
                f"{', '.join(self.missing)}. Refusing to serve a partial record as "
                f"complete (SC-006)."
            )
        return (
            f"previous snapshot at {self.path} is usable, last refreshed "
            f"{self.last_refreshed}, {self.question_files} question file(s)"
        )


def inspect_previous(path: Path | None) -> PreviousSnapshot:
    """Decide whether the directory at `path` is a snapshot worth keeping."""
    if path is None:
        return PreviousSnapshot(path=Path("(none given)"), exists=False, usable=False)
    root = Path(path)
    if not root.is_dir():
        return PreviousSnapshot(path=root, exists=False, usable=False)

    missing = [name for name in REQUIRED_SETS if not (root / name).is_dir()]
    manifest = root / PARTITION_MANIFEST_NAME
    if not manifest.is_file():
        missing.append(PARTITION_MANIFEST_NAME)

    last_refreshed = NOT_STATED
    if manifest.is_file():
        try:
            last_refreshed = str(
                json.loads(manifest.read_text(encoding="utf-8")).get("last_refreshed") or NOT_STATED
            )
        except json.JSONDecodeError:
            missing.append(f"{PARTITION_MANIFEST_NAME} (unreadable)")

    question_files = sum(
        1
        for name in REQUIRED_SETS
        for _ in (root / name).glob(f"*{NDJSON_SUFFIX}")
        if (root / name).is_dir()
    )
    usable = not missing and question_files > 0
    if question_files == 0 and not missing:
        missing.append("any question partition file")
    return PreviousSnapshot(
        path=root,
        exists=True,
        usable=usable,
        last_refreshed=last_refreshed,
        missing=tuple(missing),
        question_files=question_files,
    )


def retain_previous(
    previous: Path | None,
    destination: Path,
    *,
    reason: str,
    today: str = NOT_STATED,
    copy: bool = True,
) -> PreviousSnapshot:
    """Keep the previous snapshot and re-date its Coverage Statement.

    Args:
        previous: the previous snapshot's directory -- `data/published/` locally,
            a checkout of the `published` branch in CI.
        destination: where the retained snapshot should end up. When it is the
            same directory as `previous`, nothing is copied and only the
            Coverage Statement is restamped.
        reason: why the refresh failed. Published into the statement, so a
            visitor seeing stale data can see that it is stale and why --
            quietly, without an error page.
        today: the date of the **failed** attempt. Recorded as
            `last_attempted`; it does NOT become `last_refreshed`.

    Returns the inspection result. **Raises nothing on an unusable previous
    snapshot** -- it reports it, because a failed refresh with no good fallback
    is a state to describe, not an exception to add on top of the one that
    already happened.
    """
    found = inspect_previous(previous)
    if not found.usable:
        return found

    source = found.path
    target = Path(destination)
    if copy and source.resolve() != target.resolve():
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)

    _restamp_coverage(target, last_refreshed=found.last_refreshed, reason=reason, today=today)
    return found


def _restamp_coverage(
    directory: Path, *, last_refreshed: str, reason: str, today: str
) -> tuple[Path, ...]:
    """Mark the retained Coverage Statement as last-known-good.

    `last_refreshed` is **carried over**, not advanced. `last_attempted` and
    `last_known_good_reason` are added so the staleness is self-describing.
    """
    ndjson_path = Path(directory) / f"{COVERAGE_STEM}{NDJSON_SUFFIX}"
    if not ndjson_path.is_file():
        return ()
    rows = read_ndjson(ndjson_path)
    restamped: list[dict[str, object]] = []
    for row in rows:
        updated = dict(row)
        updated["last_known_good"] = Freshness.LAST_KNOWN_GOOD.value
        updated["last_refreshed"] = row.get("last_refreshed") or last_refreshed
        updated["last_attempted"] = today
        updated["last_known_good_reason"] = reason
        restamped.append(updated)
    return write_both(Path(directory), COVERAGE_STEM, restamped)


def published_sets(directory: Path) -> Iterable[Path]:
    """Every published file under `directory`, for a size or audit sweep."""
    root = Path(directory)
    for suffix in (NDJSON_SUFFIX, CSV_SUFFIX):
        yield from sorted(root.rglob(f"*{suffix}"))
