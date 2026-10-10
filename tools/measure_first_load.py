#!/usr/bin/env python3
"""T083 — the MEASURED first-load and first-search bytes, in two columns.

Reads the report `tools/drive_page.mjs` writes from a real browser network log
and prints, per phase:

  1. **raw bytes from the network log** — the T019 basis, and the only basis
     the gate's history is expressed in; and
  2. the **offline `gzip -6` estimate** — informational only, per the owner
     decision recorded in `spike/size-budget.md` → "OWNER DECISION 2026-10-10 —
     which basis is the contract".

Reporting either alone produces a false comparison, which is why both are here
and why the raw column is the one the verdict is read off.

**Neither column is the real compressed figure, and this says so every run.**
That one can only be read from the live site's response headers
(`Content-Encoding`, `Content-Length`) once GitHub Pages is serving the
`published` branch. `make serve-local` compresses nothing — this tool asserts
that from the recorded headers rather than assuming it — GitHub Pages does not
publish which encoder or level it uses, and Brotli, which most hosts prefer for
text, would be smaller than `gzip -6`.

**Two raw numbers, not one.** The browser's `encodedDataLength` counts the bytes
on the wire *including response headers*; T019's 4,183,979 B was built from
FILE SIZES. Both are printed, because comparing the wire figure to T019 charges
the page for headers T019 never counted, and comparing only file sizes
understates what a visitor actually pays. The body column is the like-for-like
one; the wire column is what was measured.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

#: T019's first-load budget. A RAW figure built from file sizes.
#: `spike/size-budget.md` → T019, and the contract per the owner decision.
T019_BUDGET_BYTES = 4_183_979

#: The like-for-like COMPRESSED restatement of the same four components,
#: recorded in `spike/size-budget.md` → "Compressed-basis estimate".
#: INFORMATIONAL ONLY — it gates nothing.
COMPRESSED_REFERENCE_BYTES = 847_324

#: Phases the driver records, and what each one means to T083.
PHASE_MEANING = {
    "load": "FIRST PAGE LOAD — what every visitor pays, search or no search",
    "search": "FIRST SEARCH, one-word query — the case T019's gate was set on",
    "more": '"Show 25 more" — one further digest, or none',
    "reload": "a second first load, for the two-session measurement below",
    "two": "FIRST SEARCH, two-word query spanning two sessions — the accepted overrun",
    "ignored": "a query with words the tokenise rule drops",
    "zero": "a query with no hits",
    "failure": "a blocked digest, to prove the error is visible",
}


def gzip6(path: Path) -> int:
    """`gzip -6` bytes for one file, using the real gzip.

    Shelled out rather than computed with zlib, because every `gzip -6` figure
    already in `spike/size-budget.md` was produced this way and a second
    implementation would make this table incomparable with that one.
    """
    result = subprocess.run(["gzip", "-6", "-c", str(path)], capture_output=True, check=True)
    return len(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="the JSON report drive_page.mjs wrote")
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    if "phases" not in report:
        print(f"{args.report}: no phases recorded — the browser run failed")
        return 1

    print("T083 — MEASURED first-load and first-search bytes, from a real browser")
    print("=" * 100)
    print(f"Chrome            : {report.get('chrome')}")
    print(f"CDP protocol      : {report.get('protocol')}")
    print(f"Origin            : {report.get('origin')}")
    print(f"Upstream blocked  : {report.get('hostResolverRules')}")
    print(f"Queries           : {report.get('query')!r} / {report.get('queryTwo')!r}")
    print()

    # The compression claim, asserted from the recorded headers rather than
    # assumed. If `make serve-local` ever did compress, every raw figure below
    # would silently become a compressed one.
    encodings = {
        entry.get("contentEncoding")
        for phase in report["phases"].values()
        for entry in phase.get("urls", [])
        if "contentEncoding" in entry
    }
    compressed = {e for e in encodings if e}
    if compressed:
        print(
            f"REFUSED: the static host returned Content-Encoding {sorted(compressed)}. "
            "Every raw figure below would be a compressed one."
        )
        return 1
    print(
        "Content-Encoding on every recorded response: ABSENT — `make serve-local` "
        "compresses nothing, so the wire figures below are raw."
    )
    print()

    gzip_cache: dict[str, int] = {}
    totals: dict[str, dict[str, int]] = {}

    for name, phase in report["phases"].items():
        urls = phase.get("urls", [])
        if not urls:
            continue
        print(f"PHASE {name} — {PHASE_MEANING.get(name, '')}")
        print("-" * 100)
        print(f"{'wire B':>12}{'body B':>12}{'gzip -6 B':>12}{'ratio':>8}  file")
        wire = body = gz = 0
        for entry in urls:
            file_name = entry.get("file")
            path = REPO_ROOT / file_name if file_name else None
            if path is not None and path.is_file():
                if file_name not in gzip_cache:
                    gzip_cache[file_name] = gzip6(path)
                entry_gz = gzip_cache[file_name]
            else:
                entry_gz = 0
            entry_wire = entry.get("encodedDataLength") or 0
            entry_body = entry.get("bodyBytes") or 0
            wire += entry_wire
            body += entry_body
            gz += entry_gz
            ratio = f"{100 * entry_gz / entry_body:.1f}%" if entry_body else "—"
            print(
                f"{entry_wire:>12,}{entry_body:>12,}{entry_gz:>12,}{ratio:>8}  "
                f"{file_name or entry.get('path')}"
            )
        print("-" * 100)
        overall = f"{100 * gz / body:.1f}%" if body else "—"
        print(f"{wire:>12,}{body:>12,}{gz:>12,}{overall:>8}  {len(urls)} request(s)")
        print()
        totals[name] = {"wire": wire, "body": body, "gzip": gz, "requests": len(urls)}

    # ---------------------------------------------------------------- verdict
    print("=" * 100)
    print("Against T019's budget")
    print("=" * 100)
    load = totals.get("load", {})
    search = totals.get("search", {})
    reload_ = totals.get("reload", {})
    two = totals.get("two", {})

    rows = []
    if load:
        rows.append(("first page load, no search", load["wire"], load["body"], load["gzip"]))
    if load and search:
        rows.append(
            (
                "first load + first search (one word, 1 digest)",
                load["wire"] + search["wire"],
                load["body"] + search["body"],
                load["gzip"] + search["gzip"],
            )
        )
    if load and search and totals.get("more"):
        more = totals["more"]
        rows.append(
            (
                'the same, plus "Show 25 more"',
                load["wire"] + search["wire"] + more["wire"],
                load["body"] + search["body"] + more["body"],
                load["gzip"] + search["gzip"] + more["gzip"],
            )
        )
    if reload_ and two:
        rows.append(
            (
                "first load + first search (two words, 2 digests)",
                reload_["wire"] + two["wire"],
                reload_["body"] + two["body"],
                reload_["gzip"] + two["gzip"],
            )
        )

    print(
        f"{'wire B':>12}{'vs T019':>10}{'body B':>12}{'vs T019':>10}"
        f"{'gzip -6 B':>12}{'vs cmp':>10}  measurement"
    )
    print("-" * 100)
    for label, wire, body, gz in rows:
        print(
            f"{wire:>12,}{100 * wire / T019_BUDGET_BYTES - 100:>+9.1f}%"
            f"{body:>12,}{100 * body / T019_BUDGET_BYTES - 100:>+9.1f}%"
            f"{gz:>12,}{100 * gz / COMPRESSED_REFERENCE_BYTES - 100:>+9.1f}%  {label}"
        )
    print("-" * 100)
    print(f"T019 budget (RAW, the contract)              : {T019_BUDGET_BYTES:>12,} B")
    print(f"like-for-like compressed reference (INFO ONLY): {COMPRESSED_REFERENCE_BYTES:>12,} B")
    print()
    # The last two rows are routinely IDENTICAL, and that is arithmetic rather
    # than a copy-paste fault: "Show 25 more" after a one-word query crosses
    # into the same second session the two-word query's first page spans, so
    # both totals are the index + the names + the same two digests + one page
    # load. Said here because two identical rows in a measurement table look
    # like a bug, and a reader who assumes it is one stops reading the table.
    identical = len(rows) >= 2 and rows[-1][1] == rows[-2][1]
    if identical:
        print(
            "  * The last two rows are equal because they fetched the SAME files: the "
            'second\n    session that "Show 25 more" crossed into is the second session '
            "the two-word\n    query's first page spans. Not a duplicated row."
        )
    print("Reading these:")
    print("  * The RAW columns are the contract. `spike/size-budget.md` records the owner")
    print("    decision that T019's 4,183,979 B stays the gate and that every compressed")
    print("    figure is informational: a result that passes raw and fails compressed has")
    print("    passed.")
    print("  * `body B` is the like-for-like raw column — T019 was built from file sizes.")
    print("    `wire B` is what the browser counted, response headers included, and is")
    print("    larger for that reason alone.")
    print("  * NEITHER gzip column is the real compressed figure. That is readable only")
    print("    from the live site's response headers (Content-Encoding, Content-Length)")
    print("    once Pages serves the `published` branch. Until then the encoder, the")
    print("    level, and whether a given file is compressed at all are assumptions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
