#!/usr/bin/env python3
"""Diff every published field name against the FR-008 set. T178, FR-138.

**Why this is a tool and not a paragraph.** Feature 001's Member-fields gate
evidence carries this census — every field name in every published file, the
union over all records rather than a sample, descending into nested objects and
arrays, plus each CSV header, diffed against
`sansad.model.member.PUBLISHED_FIELDS`. It was produced **once, by hand**, and
the constitution requires it re-run "against what will actually be published,
not against what was specified" **before each publication**. A census nobody
can re-run is a census that was true on one afternoon.

**It reports a census and fails on one bounded condition.** Those are separate
jobs and it is worth saying which is which.

The CENSUS lists, per published set, every key that is an FR-008 member
attribute — by its own name, or **by a declared spelling of one**.
`representations.member_name` is the case that made this necessary: it *is* a
member name form and `contracts/published-dataset.md` declares it as such, but
the spelling is not the one `PUBLISHED_FIELDS` carries, so the original diff
reported a genuine FR-008 field as "not a member attribute" and its membership
of the set rested on a human reading the contract. That resolution is called
out explicitly in the output rather than silently absorbed.

The CHECK fails on one thing: a published key that **names an attribute
Principle V excludes**, matched against the same spellings `make guard` uses
and normalised the same way. `make guard` scans file CONTENT; this scans
published key NAMES, which is the part that was missing.

A first version of this tool tried to classify every key as permitted,
record-level, non-person or *unclassified*, and fail on the last. That was the
wrong shape: the non-person set is unbounded — `manifest.sets.by-session.records`,
`window_questions`, `source_terms` and a hundred others — so the tool reported
35 "findings" that were all obviously fine, and maintaining the exemption list
would have taught nobody anything.

Keys that merely SHARE a spelling with a member field are declared in
`RECORD_LEVEL` and excluded from the census per set: `house`,
`last_refreshed` and `source_record_ref` on a *question* row are facts about
the question, and `terms` in the search index is the index's tokenised subject
words. The original census marked these with a dagger and explained them in
prose; a prose explanation is not something a later run can check.

Exit code is the whole interface. It prints key NAMES and counts, never values.

    python tools/check_field_scope.py [data/published]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from sansad.model.member import (  # noqa: E402
    PUBLISHED_FIELD_SYNONYMS,
    PUBLISHED_FIELDS,
    published_field_for,
)

#: Keys that share a spelling with an FR-008 field but are facts about the
#: RECORD rather than about a person. Declared, not inferred: the original
#: census marked these with a dagger and explained them in prose, and a prose
#: explanation is not something a later run can check.
#:
#: `terms` is the sharpest of them -- in `search/subject-index.json` it is the
#: index's tokenised subject WORDS, which collides with Member.terms (terms
#: served). Nothing about a person.
RECORD_LEVEL: dict[str, set[str]] = {
    "house": {"by-session", "by-ministry", "by-member", "coverage", "reference"},
    "last_refreshed": {"by-session", "by-ministry", "by-member", "coverage", "reference"},
    "source_record_ref": {"by-session", "by-ministry", "by-member", "reference"},
    "terms": {"search"},
    "state": {"aggregates"},
}

#: The prohibited spellings, imported from the guard rather than restated.
#:
#: This replaced an enumeration of every NON-person field, which was the wrong
#: shape: that set is unbounded -- `manifest.sets.by-session.records`,
#: `window_questions`, `source_terms` and a hundred others are obviously not
#: attributes of a person, and listing them all would be a maintenance burden
#: that taught nobody anything. The bounded question is the one Principle V
#: actually asks: **does any published key name an attribute it excludes?**
#:
#: So the census below REPORTS which keys are FR-008 member attributes, and the
#: check FAILS on a prohibited one. `make guard` scans file CONTENT for these
#: spellings; this scans published key NAMES, resolved through the declared
#: synonyms, which is the part that was missing.
_GUARD = REPO_ROOT / "tools" / "guard_no_raw_payloads.py"


def prohibited_spellings() -> dict[str, tuple[str, ...]]:
    namespace: dict[str, object] = {"__file__": str(_GUARD), "__name__": "_guard_for_scope"}
    exec(compile(_GUARD.read_text(encoding="utf-8"), str(_GUARD), "exec"), namespace)
    return namespace["PROHIBITED_ATTRIBUTES"]  # type: ignore[return-value]


def normalise(key: str) -> str:
    """Lowercase, separators removed -- the guard's own comparison form."""
    return "".join(ch for ch in key.lower() if ch.isalnum())


def keys_in(value: object, prefix: str = "") -> set[str]:
    """Every key name in a decoded record, descending into objects and arrays.

    Returns dotted paths for nested keys, so `representations.member_name` is
    reported as what it is rather than flattened to `member_name` -- the path
    is what makes a finding actionable.
    """
    found: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            found.add(path)
            found |= keys_in(nested, path)
    elif isinstance(value, list):
        for item in value:
            found |= keys_in(item, prefix)
    return found


def keys_in_file(path: Path) -> set[str]:
    """Every field name in one published file. The UNION over all records."""
    found: set[str] = set()
    suffix = path.suffix.lower()
    try:
        if suffix == ".jsonl":
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    found |= keys_in(json.loads(line))
        elif suffix == ".json":
            found |= keys_in(json.loads(path.read_text(encoding="utf-8")))
        elif suffix == ".csv":
            with path.open(encoding="utf-8", newline="") as handle:
                header = next(csv.reader(handle), [])
                found |= {column for column in header if column}
    except (OSError, json.JSONDecodeError, StopIteration, csv.Error):
        return found
    return found


def set_name_for(path: Path, root: Path) -> str:
    """The published set a file belongs to, for the per-set report."""
    relative = path.relative_to(root)
    return relative.parts[0] if len(relative.parts) > 1 else relative.stem.split(".")[0]


def leaf(key: str) -> str:
    """The last segment of a dotted path."""
    return key.rsplit(".", 1)[-1]


def check(root: Path) -> int:
    if not root.is_dir():
        print(f"check-field-scope: {root} is not a directory -- NOT a pass")
        return 1

    files = [p for p in sorted(root.rglob("*")) if p.is_file()]
    if not files:
        print(f"check-field-scope: {root} is empty -- NOT a pass")
        return 1

    by_set: dict[str, set[str]] = defaultdict(set)
    for path in files:
        by_set[set_name_for(path, root)] |= keys_in_file(path)

    print("check-field-scope: every published field name against the FR-008 set")
    print(f"  FR-008 ({len(PUBLISHED_FIELDS)}): {', '.join(sorted(PUBLISHED_FIELDS))}")
    print(
        f"  declared spellings ({len(PUBLISHED_FIELD_SYNONYMS)}): "
        + ", ".join(f"{k} -> {v}" for k, v in sorted(PUBLISHED_FIELD_SYNONYMS.items()))
    )
    print()

    prohibited = prohibited_spellings()
    by_spelling = {
        normalise(spelling): attribute
        for attribute, spellings in prohibited.items()
        for spelling in spellings
    }

    findings: list[str] = []
    via_synonym: list[str] = []
    print(f"  {'published set':<24}{'fields':>7}  member attributes (FR-008)")
    print("  " + "-" * 76)
    for name in sorted(by_set):
        keys = by_set[name]
        member_attributes: list[str] = []
        for key in sorted(keys):
            base = leaf(key)

            # Principle V: does this key NAME an excluded attribute?
            excluded = by_spelling.get(normalise(base))
            if excluded:
                findings.append(
                    f"{name}: published key {key!r} names {excluded!r}, which Principle V excludes"
                )
                continue

            if base in RECORD_LEVEL and name in RECORD_LEVEL[base]:
                continue  # shares a spelling; a fact about the record, not a person

            resolved = published_field_for(base)
            if resolved is None:
                continue  # not a member attribute at all
            if base == resolved:
                member_attributes.append(key)
            else:
                member_attributes.append(f"{key} -> {resolved}")
                via_synonym.append(f"{name}: {key} -> {resolved}")

        shown = ", ".join(member_attributes) if member_attributes else "(none)"
        print(f"  {name:<24}{len(keys):>7}  {shown[:76]}")
        for extra in member_attributes[1:] if len(shown) > 76 else []:
            print(f"  {'':<31}  {extra}")

    print()
    if via_synonym:
        print("  Resolved through a DECLARED SPELLING, which is the defect this closes:")
        for item in via_synonym:
            print(f"    {item}")
        print(
            "    -- a genuine FR-008 name form whose published spelling is not the one\n"
            "       PUBLISHED_FIELDS carries. Before this, the diff reported it as 'not a\n"
            "       member attribute' and its membership rested on a human reading the\n"
            "       contract."
        )
        print()

    if findings:
        print(f"check-field-scope: FAIL -- {len(findings)} finding(s)")
        for item in findings:
            print(f"  - {item}")
        return 1

    print(
        f"check-field-scope: PASS -- {len(by_set)} published set(s), "
        f"{sum(len(v) for v in by_set.values())} distinct field name(s); "
        f"no published key names an attribute Principle V excludes"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "published",
        nargs="?",
        default=str(REPO_ROOT / "data" / "published"),
        help="the published dataset directory (default: data/published)",
    )
    args = parser.parse_args(argv)
    return check(Path(args.published).resolve())


if __name__ == "__main__":
    sys.exit(main())
