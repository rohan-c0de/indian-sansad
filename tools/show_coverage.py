#!/usr/bin/env python3
"""`make coverage` -- print the published Coverage Statement for every House.

T053 / `quickstart.md` scenario 11 (FR-013). Reads the **published** file
rather than recomputing, so what it prints is what a consumer gets. If the
statement on disk is wrong, this says the wrong thing too -- which is the point:
a printer that recomputed would hide a bad publish.

> **If Rajya Sabha data is absent, the statement says Lok Sabha only** -- it
> must not imply coverage it does not have.

THE EXIT CODE IS THE INTERFACE.
    0  a statement exists for every House and was printed
    1  a House has no statement, which FR-013 forbids
    2  nothing published yet
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sansad.model._common import House

COVERAGE_FILE = "coverage.jsonl"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "published",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "published",
    )
    args = parser.parse_args(argv)
    path: Path = args.published / COVERAGE_FILE
    if not path.is_file():
        print(f"coverage: NOT PRESENT -- no {path}. Run `make refresh` first.")
        return 2

    rows = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    for row in rows:
        print(f"=== {row.get('house')} ===")
        for key, value in row.items():
            if key == "house":
                continue
            if isinstance(value, list):
                if not value:
                    print(f"  {key}: (none)")
                    continue
                print(f"  {key}:")
                for item in value:
                    print(f"    - {item}")
            else:
                print(f"  {key}: {value}")
        print()

    houses = {str(row.get("house")) for row in rows}
    missing = [h.value for h in House if h.value not in houses]
    if missing:
        print(f"FAIL: no Coverage Statement for {', '.join(missing)}.")
        print("FR-013 requires one per House -- an absent statement reads as 'not looked at',")
        print("and data-model.md requires the opposite: say so explicitly.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
