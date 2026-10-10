#!/usr/bin/env python3
"""T056 -- every published join has a Resolution Record (FR-005). Scenario 4.

> for every published join, a resolution record exists giving the name form as
> written and the source record reference. **The check recomputes nothing** --
> it confirms a consumer could audit the join without re-deriving it.
> -- `quickstart.md` scenario 4

**"Recomputes nothing" is the whole design.** This tool does not import the
matcher, does not normalise a name and does not look at the roster. It reads
the published files and asks one question: for each `member_id` a published
question claims as an asker, is there a resolution record that resolved to it,
carrying the name as written and a source record reference? A checker that
re-ran the resolver would prove the resolver agrees with itself -- which is not
what FR-005 promises a third party.

THE EXIT CODE IS THE INTERFACE.
    0  every published join is auditable
    1  a join has no resolution record, or a record is missing its provenance
    2  the check could not run (no published dataset, unreadable input)
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sansad.cli import RESOLUTION_STEM
from sansad.model._common import NOT_STATED
from sansad.publish.formats import NDJSON_SUFFIX, read_ndjson
from sansad.publish.partitions import BY_SESSION_DIR


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "published",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "published",
        help="the published dataset directory (default: data/published)",
    )
    args = parser.parse_args(argv)
    root: Path = args.published

    sessions = root / BY_SESSION_DIR
    records_path = root / f"{RESOLUTION_STEM}{NDJSON_SUFFIX}"
    if not sessions.is_dir():
        print(f"verify-joins: NOT PRESENT -- no {sessions}. Run `make refresh` first.")
        return 2
    if not records_path.is_file():
        print(f"verify-joins: NOT PRESENT -- no {records_path}.")
        return 2

    # --- what the published record claims ---
    joins: Counter[str] = Counter()
    questions = 0
    for path in sorted(sessions.glob(f"*{NDJSON_SUFFIX}")):
        for row in read_ndjson(path):
            questions += 1
            for member_id in row.get("asking_members") or ():
                joins[str(member_id)] += 1

    # --- what a consumer can audit it against ---
    resolved_to: set[str] = set()
    without_form = 0
    without_ref = 0
    total_records = 0
    for row in read_ndjson(records_path):
        total_records += 1
        if not str(row.get("name_as_written") or "").strip():
            without_form += 1
        if str(row.get("source_record_ref") or NOT_STATED) in ("", NOT_STATED):
            without_ref += 1
        member_id = row.get("member_id")
        if member_id:
            resolved_to.add(str(member_id))

    unauditable = sorted(set(joins) - resolved_to)

    print(f"verify-joins: {questions:,} published question(s) in {BY_SESSION_DIR}/")
    print(f"              {sum(joins.values()):,} join(s) to {len(joins):,} member identity/ies")
    print(f"              {total_records:,} resolution record(s)")
    print(f"              {len(resolved_to):,} identity/ies reachable through a record")

    failed = False
    if unauditable:
        failed = True
        print(f"\nFAIL: {len(unauditable)} published join(s) with NO resolution record:")
        for member_id in unauditable[:20]:
            print(f"  {member_id}  ({joins[member_id]:,} question(s))")
        if len(unauditable) > 20:
            print(f"  ... and {len(unauditable) - 20} more")
    if without_form:
        failed = True
        print(f"\nFAIL: {without_form} resolution record(s) carry no name as written.")
    if without_ref:
        failed = True
        print(f"\nFAIL: {without_ref} resolution record(s) carry no source record reference.")

    if failed:
        print("\nFR-005 requires a consumer be able to verify any join without re-deriving it.")
        return 1
    print("\nverify-joins: PASS -- every published join is auditable (FR-005).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
