#!/usr/bin/env python3
"""`make composition TERM=n` -- quickstart.md scenario 8 (User Story 4).

> **Expected**: category counts sum to that term's total membership. Members
> with missing attributes appear under an explicit "not stated" category, never
> omitted.

Reads the **published** aggregate rather than recomputing, so what it prints is
what a consumer gets. A printer that recomputed would hide a bad publish.

**It prints the reconciliation, not just the numbers.** The scenario's whole
assertion is that the categories sum to the total, so the sum is written out
category by category and compared to the published total. A tool that printed
the breakdown and left the reader to add it up would be testing nothing.

THE EXIT CODE IS THE INTERFACE.
    0  every dimension reconciles against the published total
    1  a dimension does not sum to the total, or the term is absent
    2  nothing published yet
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sansad.publish.aggregates import (
    AGGREGATES_DIR_NAME,
    COMPOSITION_STEM,
    COUNTING_BASIS_STEM,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--term", type=int, required=True)
    parser.add_argument(
        "--published",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "published",
    )
    args = parser.parse_args(argv)

    root: Path = args.published / AGGREGATES_DIR_NAME
    path = root / f"{COMPOSITION_STEM}.jsonl"
    if not path.is_file():
        print(f"composition: NOT PRESENT -- no {path}. Run `make refresh` first.")
        return 2

    rows = [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]
    mine = [r for r in rows if r["term"] == args.term]
    if not mine:
        terms = sorted({r["term"] for r in rows})
        print(f"composition: no rows for term {args.term}. Published terms: {terms}")
        return 1

    total = mine[0]["total_members"]
    print(f"=== House composition, {args.term}th Lok Sabha ===")
    print(f"total membership published for this term: {total:,}")
    print()

    failed = False
    for dimension in ("party", "state", "terms_served"):
        buckets = [r for r in mine if r["dimension"] == dimension]
        if not buckets:
            continue
        print(f"--- {dimension} ({len(buckets)} categories) ---")
        shown = sorted(buckets, key=lambda r: (-r["members"], str(r["category"])))
        for row in shown[:12]:
            marker = (
                "  <- explicit 'not stated' category" if row["category"] == "not stated" else ""
            )
            print(f"  {row['members']:>6,}  {str(row['category'])[:48]}{marker}")
        if len(shown) > 12:
            rest = sum(r["members"] for r in shown[12:])
            print(f"  {rest:>6,}  ... and {len(shown) - 12} further categories")

        # --- the reconciliation, written out ---
        parts = [r["members"] for r in shown]
        summed = sum(parts)
        if len(parts) <= 14:
            arithmetic = " + ".join(f"{n:,}" for n in parts)
        else:
            head = " + ".join(f"{n:,}" for n in parts[:12])
            arithmetic = f"{head} + ... ({len(parts) - 12} more) = {summed:,}"
        print(f"  RECONCILE: {arithmetic}")
        verdict = "OK" if summed == total else "MISMATCH"
        if summed != total:
            failed = True
        print(f"             = {summed:,}  against published total {total:,}  -> {verdict}")
        print()

    basis_path = root / f"{COUNTING_BASIS_STEM}.jsonl"
    if basis_path.is_file():
        for row in (json.loads(line) for line in basis_path.open(encoding="utf-8") if line.strip()):
            if row["unit"] == "member":
                print("--- counting basis (unit: member) ---")
                for line in row["counting_basis"].split(". "):
                    if line.strip():
                        print(f"  {line.strip().rstrip('.')}.")
                break
    else:
        print("WARNING: the counting basis is not published; FR-012 requires it.")
        failed = True

    print()
    if failed:
        print("composition: FAIL -- a dimension does not reconcile, or the basis is missing.")
        return 1
    print("composition: PASS -- every dimension sums to the published total membership.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
