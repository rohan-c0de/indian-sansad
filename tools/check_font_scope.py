#!/usr/bin/env python3
"""The only check in this repository that can see inside a font. T114.

**Why this exists at all.** Constitution Principle IV requires that all
published material is English, and `gate-evidence.md` evidenced that for feature
001 with a codepoint scan over every `.jsonl` file and the search index. Feature
002 ships three `woff2` files into `web/`, and **no pre-existing check can read
one**:

* `.woff2` is a member of `UNSCANNABLE_SUFFIXES` in
  `tools/guard_no_raw_payloads.py`, so `make guard` and `make audit-fields` skip
  font files entirely rather than failing on them.
* The 64 KB payload ceiling does not apply either: `PAYLOAD_SUFFIXES` lists only
  data formats (`.json`, `.jsonl`, `.csv`, …).
* The text scans in `tests/unit/test_page_fetch_layer.py` raise
  `UnicodeDecodeError` on a compressed binary, which is why that module routes
  these files here instead.

So without this tool a font could carry any script and every check in the
repository would stay green. Scanning the binary *as text* was considered and
rejected: a `woff2` is brotli-compressed, so a text scan produces false
negatives by construction and false positives by chance. Reading the `cmap` is
the only honest check, and it is what `fonttools[woff]` is a dev dependency for.

Exit code is the whole interface. It prints what it read and what it concluded;
it never prints a glyph or a decoded string.

    python tools/check_font_scope.py [web/fonts]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Principle IV, the block that must not be present. Devanagari proper.
DEVANAGARI = range(0x0900, 0x0980)

#: The total payload ceiling and file count, from SC-002.
TOTAL_CEILING_BYTES = 95_000
MAX_FILES = 4

#: What each file must be, declared here rather than discovered, so that
#: swapping a font for a different one is a deliberate edit to this table.
#:
#: `family` is matched as a SUBSTRING of the font's internal name, not for
#: equality: a `@font-face` `font-family` is an author-chosen label, and these
#: files call themselves `Newsreader 16pt 16pt SemiBold` and
#: `IBM Plex Sans SemiBold` internally while the stylesheet declares
#: `"Newsreader"` and `"IBM Plex Sans"`. Demanding equality would fail on
#: correct files.
EXPECTED: dict[str, tuple[str, int, int]] = {
    # file name: (family substring, usWeightClass, exact bytes)
    "newsreader-600.woff2": ("Newsreader", 600, 23_888),
    "ibm-plex-sans-400.woff2": ("IBM Plex Sans", 400, 17_604),
    "ibm-plex-sans-600.woff2": ("IBM Plex Sans", 600, 19_192),
}

#: Every distinct non-ASCII codepoint the published dataset actually contains,
#: from feature 001's Gate 4 evidence, with its occurrence count.
#:
#: Checked against the `cmap` rather than against the declared `unicode-range`,
#: because the two are not the same thing -- which is the finding that produced
#: `ACCEPTED_FALLBACKS` below.
DATASET_CODEPOINTS: tuple[tuple[int, str, int], ...] = (
    (0x2019, "RIGHT SINGLE QUOTATION MARK", 1967),
    (0x2013, "EN DASH", 724),
    (0x2018, "LEFT SINGLE QUOTATION MARK", 453),
    (0x201D, "RIGHT DOUBLE QUOTATION MARK", 79),
    (0x201C, "LEFT DOUBLE QUOTATION MARK", 62),
    (0x2011, "NON-BREAKING HYPHEN", 51),
    (0x00A0, "NO-BREAK SPACE", 35),
    (0x00F1, "LATIN SMALL LETTER N WITH TILDE", 23),
    (0x00E8, "LATIN SMALL LETTER E WITH GRAVE", 16),
    (0x202F, "NARROW NO-BREAK SPACE", 14),
    (0x2014, "EM DASH", 13),
    (0x00E9, "LATIN SMALL LETTER E WITH ACUTE", 6),
    (0x2060, "WORD JOINER", 5),
)

#: Three dataset codepoints that are in the subset's DECLARED `unicode-range`
#: and in none of the shipped fonts. Found 2026-10-13 by reading the `cmap`,
#: and recorded rather than fixed -- see `web/fonts/PROVENANCE.md`.
#:
#: They render from the fallback stack: U+202F and U+2060 are invisible, and
#: U+2011 is 51 hyphens at a slightly different face. Rewriting them at render
#: time would change what the page shows relative to what the record says.
#:
#: This set exists so the condition is ASSERTED rather than rediscovered: a
#: *new* dataset codepoint missing from the fonts is a finding, while these
#: three are a recorded exception. Narrowing it later is a tightening; widening
#: it is a decision that belongs in PROVENANCE.md first.
ACCEPTED_FALLBACKS: frozenset[int] = frozenset({0x2011, 0x202F, 0x2060})


def codepoints_of(path: Path) -> set[int]:
    """Every codepoint the font maps, from every `cmap` subtable."""
    from fontTools.ttLib import TTFont  # imported late: dev-only dependency

    out: set[int] = set()
    with TTFont(path) as font:
        for table in font["cmap"].tables:
            out |= set(table.cmap.keys())
    return out


def metadata_of(path: Path) -> tuple[str, int]:
    """The font's internal family name and `usWeightClass`."""
    from fontTools.ttLib import TTFont

    with TTFont(path) as font:
        family = ""
        for record in font["name"].names:
            if record.nameID == 1:
                try:
                    family = record.toUnicode()
                except UnicodeDecodeError:
                    continue
                break
        return family, int(font["OS/2"].usWeightClass)


def check(directory: Path) -> int:
    """Returns the process exit code. 0 clean, 1 on any finding."""
    findings: list[str] = []
    fonts = sorted(directory.glob("*.woff2"))

    print(f"check-fonts: {directory.relative_to(REPO_ROOT)}")

    if not fonts:
        print("  no .woff2 found -- NOT a pass; this check had nothing to read")
        return 1

    if len(fonts) > MAX_FILES:
        findings.append(f"{len(fonts)} font files exceeds the {MAX_FILES}-file limit (SC-002)")

    total = 0
    for path in fonts:
        size = path.stat().st_size
        total += size
        name = path.name
        family, weight = metadata_of(path)
        cps = codepoints_of(path)
        devanagari = sorted(c for c in cps if c in DEVANAGARI)

        print(f"  {name}")
        print(f"      {size:,} B | family {family!r} | usWeightClass {weight}")
        print(f"      cmap: {len(cps)} codepoints, U+{min(cps):04X}..U+{max(cps):04X}")

        # --- Principle IV: the check this tool exists for ------------------
        if devanagari:
            findings.append(
                f"{name}: {len(devanagari)} Devanagari codepoint(s) "
                f"in U+0900-U+097F -- Constitution Principle IV"
            )
            print(f"      Devanagari: {len(devanagari)} FOUND -- FINDING")
        else:
            print("      Devanagari U+0900-U+097F: none")

        # --- the file is the one that was declared ------------------------
        expected = EXPECTED.get(name)
        if expected is None:
            findings.append(f"{name}: not in EXPECTED -- add it deliberately or do not ship it")
        else:
            want_family, want_weight, want_bytes = expected
            if want_family.lower() not in family.lower():
                findings.append(
                    f"{name}: internal family {family!r} does not contain {want_family!r}"
                )
            if weight != want_weight:
                findings.append(f"{name}: usWeightClass {weight} but {want_weight} was declared")
            if size != want_bytes:
                findings.append(f"{name}: {size} B but {want_bytes} B was declared")

        # --- OFL requires the licence to travel with the font -------------
        if not list(directory.glob("OFL-*.txt")):
            findings.append(f"{name}: no OFL-*.txt beside it (SIL OFL 1.1 requires it)")

        # --- every dataset codepoint renders, or is a recorded exception ---
        missing = [(c, n, k) for c, n, k in DATASET_CODEPOINTS if c not in cps]
        unexpected = [(c, n, k) for c, n, k in missing if c not in ACCEPTED_FALLBACKS]
        accepted = [(c, n, k) for c, n, k in missing if c in ACCEPTED_FALLBACKS]
        if accepted:
            print(
                "      recorded fallbacks: "
                + ", ".join(f"U+{c:04X} {n} (x{k})" for c, n, k in accepted)
            )
        if unexpected:
            for cp, label, count in unexpected:
                findings.append(
                    f"{name}: U+{cp:04X} {label} occurs {count} time(s) in the published "
                    f"record and is in no shipped font, and is not a recorded fallback"
                )

    print(f"  total: {total:,} B across {len(fonts)} file(s)")
    if total > TOTAL_CEILING_BYTES:
        findings.append(f"total {total:,} B exceeds the {TOTAL_CEILING_BYTES:,} B ceiling (SC-002)")
    else:
        headroom = TOTAL_CEILING_BYTES - total
        print(
            f"  ceiling: {TOTAL_CEILING_BYTES:,} B (SC-002) -- "
            f"{headroom:,} B headroom, {total / TOTAL_CEILING_BYTES:.0%} used"
        )

    if findings:
        print()
        print(f"check-fonts: FAIL -- {len(findings)} finding(s)")
        for item in findings:
            print(f"  - {item}")
        return 1

    print("check-fonts: PASS")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "directory",
        nargs="?",
        default=str(REPO_ROOT / "web" / "fonts"),
        help="the directory holding the self-hosted fonts (default: web/fonts)",
    )
    args = parser.parse_args(argv)
    directory = Path(args.directory).resolve()
    if not directory.is_dir():
        print(f"check-fonts: {directory} is not a directory -- NOT a pass")
        return 1
    return check(directory)


if __name__ == "__main__":
    sys.exit(main())
