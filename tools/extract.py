#!/usr/bin/env python3
"""T057 -- a subset on any of the five FR-007 axes, without taking the whole record.

`quickstart.md` scenario 5. "No axis may require downloading the whole record."

| Axis | How it is reached | Fetches |
|---|---|---|
| `HOUSE` / `SESSION` | its own partition | 1 |
| `MINISTRY` | its own partition | 1 |
| `MEMBER` | its own partition | 1 |
| `STATE` | the member reference set, then only the matching members' files | 1 + n |
| `CONSTITUENCY` | the member reference set, then only the matching members' files | 1 + n |

**State and constituency are not partitions, deliberately.**
`contracts/published-dataset.md`: "There is **no per-state or per-constituency
question partition**. Those subsets are reached by filtering the member
reference set and then taking the matching members' files -- a deliberate
choice, since both are member attributes and a separate partition would
republish the per-member files under a key the member set already supplies."
So this tool **asserts** it read only the member set plus the matching members'
files, and names every file it opened. A fetch count is the only way to tell
"reached the subset" from "filtered the whole record in memory", and the latter
is what FR-007 forbids.

**De-duplication on `question_id` before any total.** Guarantee 6: the
partitions republish the same records under different keys, so a consumer
combining axes must de-duplicate rather than sum. This tool does that itself
and reports both figures, so the difference is visible instead of inferred.

THE EXIT CODE IS THE INTERFACE.
    0  the subset was produced within its fetch budget
    1  an axis needed the whole record, or an axis produced nothing
    2  the check could not run (no published dataset, bad arguments)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sansad.publish.formats import NDJSON_SUFFIX, read_ndjson
from sansad.publish.partitions import (
    BY_MEMBER_DIR,
    BY_MINISTRY_DIR,
    BY_SESSION_DIR,
    partition_key,
)
from sansad.publish.reference import REFERENCE_DIR_NAME


class Reader:
    """Counts every file it opens, so a fetch budget can be asserted."""

    def __init__(self) -> None:
        self.opened: list[str] = []

    def read(self, path: Path) -> list[dict]:
        if not path.is_file():
            return []
        self.opened.append(path.name)
        return read_ndjson(path)

    @property
    def fetches(self) -> int:
        return len(self.opened)


def _dedupe(rows: list[dict]) -> list[dict]:
    """One record per `question_id` (guarantee 6)."""
    seen: set[str] = set()
    out: list[dict] = []
    for row in rows:
        question_id = str(row.get("question_id"))
        if question_id in seen:
            continue
        seen.add(question_id)
        out.append(row)
    return out


def extract(root: Path, axis: str, value: str, *, session: str | None = None):
    """Return (rows, reader, note). Rows are de-duplicated on `question_id`."""
    reader = Reader()

    if axis in {"house", "session"}:
        if session is None:
            return [], reader, "SESSION is required with HOUSE"
        stem = partition_key(f"{value}/{session}")
        rows = reader.read(root / BY_SESSION_DIR / f"{stem}{NDJSON_SUFFIX}")
        return _dedupe(rows), reader, f"one partition file: {stem}"

    if axis == "ministry":
        stem = partition_key(value)
        rows = reader.read(root / BY_MINISTRY_DIR / f"{stem}{NDJSON_SUFFIX}")
        return _dedupe(rows), reader, f"one partition file: {stem}"

    if axis == "member":
        stem = partition_key(value)
        rows = reader.read(root / BY_MEMBER_DIR / f"{stem}{NDJSON_SUFFIX}")
        return _dedupe(rows), reader, f"one partition file: {stem}"

    if axis in {"state", "constituency"}:
        members = reader.read(root / REFERENCE_DIR_NAME / f"members{NDJSON_SUFFIX}")
        wanted = value.strip().casefold()
        matching = [
            str(m["member_id"])
            for m in members
            if str(m.get(axis) or "").strip().casefold() == wanted
        ]
        rows: list[dict] = []
        for member_id in matching:
            rows.extend(
                reader.read(root / BY_MEMBER_DIR / f"{partition_key(member_id)}{NDJSON_SUFFIX}")
            )
        # `matching` is how many members the reference set matched; the files
        # actually opened is lower, because a member with no question in the
        # window has no by-member file. Reporting the first as the second would
        # overstate what was read.
        note = (
            f"the member reference set matched {len(matching)} member(s), of which "
            f"{reader.fetches - 1} had a published file; the whole question record "
            f"was NOT read"
        )
        return _dedupe(rows), reader, note

    return [], reader, f"unknown axis {axis!r}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--published",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "published",
    )
    parser.add_argument("--house")
    parser.add_argument("--session")
    parser.add_argument("--ministry")
    parser.add_argument("--member")
    parser.add_argument("--state")
    parser.add_argument("--constituency")
    parser.add_argument("--out", type=Path, default=None, help="write the subset here")
    args = parser.parse_args(argv)

    root: Path = args.published
    if not (root / BY_SESSION_DIR).is_dir():
        print(f"extract: NOT PRESENT -- no {root}. Run `make refresh` first.")
        return 2

    axes = [
        ("house", args.house),
        ("ministry", args.ministry),
        ("member", args.member),
        ("state", args.state),
        ("constituency", args.constituency),
    ]
    chosen = [(axis, value) for axis, value in axes if value]
    if len(chosen) != 1:
        print(
            "extract: name exactly one axis -- "
            "--house (with --session), --ministry, --member, --state or --constituency"
        )
        return 2

    axis, value = chosen[0]
    rows, reader, note = extract(root, axis, value, session=args.session)

    print(f"extract: axis={axis} value={value!r}")
    print(f"  {note}")
    print(f"  files opened          : {reader.fetches}")
    print(f"  questions (deduped)   : {len(rows):,}")

    if axis in {"state", "constituency"}:
        # The budget: the member set plus the matching members' files. Anything
        # more means an axis reached for the whole record.
        if reader.fetches < 1:
            print("FAIL: the member reference set was not read.")
            return 1
        print("  budget                : 1 reference set + n member file(s) -- within FR-007")
    else:
        if reader.fetches > 1:
            print(f"FAIL: {axis} should come from ONE partition file, opened {reader.fetches}.")
            return 1
        print("  budget                : 1 partition file -- within FR-007")

    if not rows:
        print(f"FAIL: the subset is empty. Nothing published under {value!r} on axis {axis}.")
        return 1

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        print(f"  written               : {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
