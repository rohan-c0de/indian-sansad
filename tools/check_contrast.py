#!/usr/bin/env python3
"""Recompute every palette contrast ratio from the stylesheet's own tokens. T113.

FR-107: "Every contrast ratio in the palette MUST be recomputed with the WCAG
relative-luminance formula and recorded in the stylesheet beside the token it
describes. Text MUST clear 4.5:1 and marks that carry meaning MUST clear 3:1."

**This checks two different things, and the second is the one that matters.**

1. Every pair clears its floor, or is a declared exception that says what
   carries the meaning instead.
2. **The figure recorded in the stylesheet equals the figure computed here.**

(2) exists because feature 001 found three recorded ratios that were simply
wrong -- `--ink` on white was written as 14.07:1 and is 15.97:1, `--ink` on the
ground as 12.98:1 against 14.51:1, `--accent` as 7.33:1 against 8.03:1. They
were conservative rather than dangerous, and that is beside the point: a
recorded measurement nobody can reproduce is not a measurement. Comments drift
from code silently. This makes them unable to.

Exit code is the whole interface.

    python tools/check_contrast.py [web/style.css]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Floors, from FR-107.
TEXT_FLOOR = 4.5
MARK_FLOOR = 3.0

#: Which tokens are grounds, and which are drawn on them.
#:
#: Declared here rather than inferred, so that giving a token a new role is a
#: deliberate edit to this table and not a side effect of a stylesheet change.
#: `--house` is listed as BOTH text and mark because it is used for both, and
#: the stricter floor therefore applies to it.
GROUNDS = ("--paper", "--sheet")
TEXT_TOKENS = ("--ink", "--ink-soft", "--house", "--mark")
MARK_TOKENS = ("--house", "--mark", "--series-2")

#: Pairs that do NOT clear a floor, with what carries the meaning instead.
#:
#: Every entry is a recorded decision, not a waiver: the requirement each cites
#: is what makes the shortfall survivable, and an entry with no such mechanism
#: would be a finding dressed as an exception.
SUB_FLOOR: dict[tuple[str, str], str] = {
    ("--paper", "--sheet"): (
        "FR-108 -- a surface is never distinguished from the page ground by "
        "this fill difference alone; a rule, a boundary or space carries it"
    ),
    ("--house", "--mark"): (
        "FR-109 -- these two are never the only difference between two "
        "meanings; --house marks the institution and --mark marks interaction, "
        "and nothing is distinguished by which of the two it is"
    ),
    ("--series-2", "--house"): (
        "FR-122 -- adjacent chart segments are stroked in the surface colour "
        "and every series is named in text. Required, not preferred: no colour "
        "can clear 3:1 against both the near-white grounds and --house, because "
        "that needs paper:house >= 9:1 and it is 6.75:1"
    ),
}

_ROOT = re.compile(r":root\s*\{(.*?)\}", re.S)
_TOKEN = re.compile(r"(--[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\s*;")


def luminance(hex_colour: str) -> float:
    """WCAG relative luminance."""
    value = hex_colour.lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    channels = [int(value[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def ratio(a: str, b: str) -> float:
    """WCAG contrast ratio between two hex colours."""
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def tokens_in(css: str) -> dict[str, str]:
    """The `:root` custom properties that hold a hex colour."""
    block = _ROOT.search(css)
    if not block:
        return {}
    return {name: value.lower() for name, value in _TOKEN.findall(block.group(1))}


def check(path: Path) -> int:
    css = path.read_text(encoding="utf-8")
    tokens = tokens_in(css)
    findings: list[str] = []

    print(f"check-contrast: {path.relative_to(REPO_ROOT)}")
    if not tokens:
        print("  no :root hex tokens found -- NOT a pass; this check read nothing")
        return 1

    missing = [t for t in (*GROUNDS, *TEXT_TOKENS, *MARK_TOKENS) if t not in tokens]
    if missing:
        findings.append(f"declared in this tool but not in the stylesheet: {sorted(set(missing))}")

    # --- every foreground against every ground --------------------------
    print(f"  {'pair':<30}{'ratio':>9}  floor  verdict")
    print("  " + "-" * 62)
    pairs: list[tuple[str, str, float, float]] = []
    for fg in sorted(set((*TEXT_TOKENS, *MARK_TOKENS))):
        if fg not in tokens:
            continue
        floor = TEXT_FLOOR if fg in TEXT_TOKENS else MARK_FLOOR
        for ground in GROUNDS:
            if ground not in tokens:
                continue
            value = ratio(tokens[fg], tokens[ground])
            pairs.append((fg, ground, value, floor))

    # --- the declared sub-floor pairs ------------------------------------
    for a, b in SUB_FLOOR:
        if a in tokens and b in tokens:
            pairs.append((a, b, ratio(tokens[a], tokens[b]), 0.0))

    for fg, ground, value, floor in pairs:
        key = (fg, ground)
        label = f"{fg} on {ground}" if floor else f"{fg} vs {ground}"
        if key in SUB_FLOOR:
            print(f"  {label:<30}{value:>8.2f}:1   --    recorded exception")
        elif value >= floor:
            print(f"  {label:<30}{value:>8.2f}:1  {floor:>4.1f}  PASS")
        else:
            print(f"  {label:<30}{value:>8.2f}:1  {floor:>4.1f}  FAIL")
            findings.append(
                f"{label} is {value:.2f}:1, below the {floor:.1f}:1 floor, and is not "
                f"a recorded exception in SUB_FLOOR"
            )

    # --- (2) the recorded figure must equal the computed one -------------
    #
    # Formatted to two decimals, the spelling the stylesheet header uses.
    unrecorded: list[str] = []
    for fg, ground, value, floor in pairs:
        if f"{value:.2f}:1" not in css:
            unrecorded.append(f"{fg} {'on' if floor else 'vs'} {ground} = {value:.2f}:1")
    if unrecorded:
        findings.append(
            "computed but NOT recorded in the stylesheet (FR-107 requires the figure "
            "beside the token, and a figure that drifted from the token is the defect "
            f"this check exists for): {unrecorded}"
        )

    # --- an exception with no stated mechanism is not an exception -------
    for (a, b), why in SUB_FLOOR.items():
        if a in tokens and b in tokens and why.split(" --")[0] not in css:
            findings.append(
                f"{a} vs {b} is a recorded exception on {why.split(' --')[0]}, but the "
                f"stylesheet does not cite it -- the shortfall is unexplained where it matters"
            )

    print()
    if findings:
        print(f"check-contrast: FAIL -- {len(findings)} finding(s)")
        for item in findings:
            print(f"  - {item}")
        return 1
    print(
        f"check-contrast: PASS -- {len(pairs)} pair(s) computed; "
        f"text floor {TEXT_FLOOR}:1, mark floor {MARK_FLOOR}:1; "
        f"{len(SUB_FLOOR)} recorded exception(s)"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "stylesheet",
        nargs="?",
        default=str(REPO_ROOT / "web" / "style.css"),
        help="the stylesheet holding the :root palette (default: web/style.css)",
    )
    args = parser.parse_args(argv)
    path = Path(args.stylesheet).resolve()
    if not path.is_file():
        print(f"check-contrast: {path} is not a file -- NOT a pass")
        return 1
    return check(path)


if __name__ == "__main__":
    sys.exit(main())
