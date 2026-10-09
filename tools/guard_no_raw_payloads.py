#!/usr/bin/env python3
"""Fail the repository tree if a prohibited personal attribute, or an oversized
raw payload, has entered it.

Constitution Principle V (NON-NEGOTIABLE) bounds published member data to:
name forms, party, state, constituency, House, term, sitting status.

It names the prohibited attributes explicitly -- "personal phone, Delhi phone,
email, present and permanent address, date of birth, marital status, and number
of sons and daughters" -- and defines the scope as "everything a third party can
reach: the published dataset files, any extract, any interactive page, any
derived statistic, and any fixture, sample, or test file in the repository."

quickstart.md scenario 10 records why this script exists at all: "A committed
fixture of a raw upstream response is the likeliest route by which the full
personal-data payload enters the repository", and "This check is the only
automated thing standing between that payload and publication."

THE EXIT CODE IS THE WHOLE INTERFACE.
    0  nothing prohibited found
    1  a prohibited attribute or an oversized payload was found
    2  the guard itself could not run (bad arguments, unreadable root)

It prints the offending path and key. IT NEVER PRINTS THE VALUE. A guard that
echoes the payload it caught has published the payload.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# What is prohibited
# ---------------------------------------------------------------------------
# Constitution Principle V's verbatim list, each entry carrying the spellings
# the upstream and its consumers are observed or likely to use. Matched
# case-insensitively, and insensitively to the separator between words, so
# `mobileNo`, `mobile_no`, `mobile-no`, `Mobile No` and `MOBILENO` all match.
#
# NOTE ON COMPLETENESS: this list cannot be complete. The upstream carries no
# contract, versioning or deprecation notice (research.md), so a future field
# name is unknowable. T031 widens the scope; the list is widened whenever a new
# spelling is observed. A pass by this guard is evidence that these spellings
# are absent -- not that the tree is clean.

PROHIBITED_ATTRIBUTES: dict[str, tuple[str, ...]] = {
    "personal phone": (
        "mobileno", "mobilenumber", "mobile", "phoneno", "phonenumber",
        "telephoneno", "telephonenumber", "personalphone", "personalmobile",
        "contactno", "contactnumber", "residencephone", "residencephoneno",
    ),
    "Delhi phone": (
        "delhiphone", "delhiphoneno", "delhiphonenumber", "delhimobile",
        "delhitelephone", "delhitelephoneno", "delhicontact", "delhicontactno",
        "delhiresidencephone", "delhiaddressphone",
    ),
    "email": (
        "email", "emailid", "emailaddress", "mailid", "mailaddress",
        "personalemail", "officialemail", "eid",
    ),
    "present address": (
        "presentaddress", "presentadd", "currentaddress", "residentialaddress",
        "localaddress", "delhiaddress", "address",
    ),
    "permanent address": (
        "permanentaddress", "permanentadd", "permaddress", "homeaddress",
        "nativeaddress",
    ),
    "date of birth": (
        "dob", "dateofbirth", "birthdate", "birthday", "dateofbirthday",
    ),
    "marital status": (
        "maritalstatus", "marital", "maritalstate", "spousename",
        "wifename", "husbandname",
    ),
    "number of sons and daughters": (
        "noofsons", "numberofsons", "sons", "nosons",
        "noofdaughters", "numberofdaughters", "daughters", "nodaughters",
        "noofsonsanddaughters", "noofchildren", "numberofchildren", "children",
    ),
}

# A handful of the spellings above are ordinary English words that appear
# innocently in prose ("address", "children", "mobile", "sons"). Flagging those
# in a README or a spec would make the guard noisy and therefore ignored --
# the failure mode that kills a guard. So those spellings are only prohibited
# when they appear in a STRUCTURED position: as a JSON/YAML key, a CSV header
# cell, or an assignment target. The unambiguous spellings (dob, emailId,
# maritalStatus, noOfSons...) are prohibited anywhere, in any file.
AMBIGUOUS_IN_PROSE: frozenset[str] = frozenset({
    "mobile", "address", "sons", "daughters", "children", "marital",
    "eid", "email",
})

# ---------------------------------------------------------------------------
# Where to look
# ---------------------------------------------------------------------------

SKIP_DIRS: frozenset[str] = frozenset({
    ".git", ".venv", "venv", "node_modules", "__pycache__",
    ".pytest_cache", ".ruff_cache", ".mypy_cache", ".idea", ".vscode",
    "htmlcov", "dist", "build",
})

# Extensions treated as payload-shaped for the size ceiling. A raw upstream
# response arriving as a committed fixture is the case this exists for.
PAYLOAD_SUFFIXES: frozenset[str] = frozenset({
    ".json", ".jsonl", ".ndjson", ".csv", ".tsv", ".xml", ".yaml", ".yml",
})

PAYLOAD_SIZE_CEILING_BYTES = 64 * 1024  # 64 KB, per T002

# Binary and generated files are not scanned for text. They are still size-checked
# when payload-shaped.
UNSCANNABLE_SUFFIXES: frozenset[str] = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg", ".pdf",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".zip", ".gz", ".tar", ".bz2", ".xz", ".7z",
    ".so", ".dylib", ".dll", ".pyc", ".pyo", ".o", ".a",
    ".mp3", ".mp4", ".wav", ".mov", ".webm",
    ".sqlite", ".db", ".parquet",
})

# This guard's own source names every prohibited spelling, by necessity. So does
# any file whose job is to document or test the prohibition. Each exemption is
# an explicit, individually-justified hole in the guard -- never a pattern.
SELF_EXEMPT: frozenset[str] = frozenset({
    "tools/guard_no_raw_payloads.py",   # this file: the list lives here
    "tests/unit/test_guard_no_raw_payloads.py",  # tests the list
})


def _canonical(text: str) -> str:
    """Lowercase and strip every non-alphanumeric character.

    This is what makes one spelling in the list cover a family of them:
    `mobile_no`, `mobileNo`, `mobile-no`, `Mobile No` and `MOBILENO` all
    canonicalise to `mobileno`.
    """
    return re.sub(r"[^a-z0-9]", "", text.lower())


# Build the lookup once: canonical spelling -> Principle V attribute name.
_SPELLING_TO_ATTRIBUTE: dict[str, str] = {}
for _attribute, _spellings in PROHIBITED_ATTRIBUTES.items():
    for _spelling in _spellings:
        _SPELLING_TO_ATTRIBUTE[_canonical(_spelling)] = _attribute

_CANONICAL_AMBIGUOUS: frozenset[str] = frozenset(
    _canonical(s) for s in AMBIGUOUS_IN_PROSE
)

# A token in a structured position. Each alternative captures the identifier:
#   "mobileNo":            JSON / YAML double-quoted key
#   'mobileNo':            single-quoted key
#   mobileNo:              bare YAML key
#   mobileNo =            assignment
#   <mobileNo>            XML element
_STRUCTURED_KEY = re.compile(
    r"""
      "\s*([A-Za-z][A-Za-z0-9 _\-]{1,40})\s*"\s*:      # "key":
    | '\s*([A-Za-z][A-Za-z0-9 _\-]{1,40})\s*'\s*:      # 'key':
    | ^\s*([A-Za-z][A-Za-z0-9_\-]{1,40})\s*:           # bare yaml key:
    | ^\s*([A-Za-z][A-Za-z0-9_]{1,40})\s*=             # key =
    | <\s*([A-Za-z][A-Za-z0-9_\-]{1,40})\s*[>/ ]       # <key>
    """,
    re.VERBOSE | re.MULTILINE,
)

# Any word-ish token, for the unambiguous spellings that are prohibited anywhere.
_ANY_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9_\-]{1,40}")


def _csv_header_cells(line: str) -> list[str]:
    """Split a candidate CSV/TSV header line into cells.

    Deliberately naive: a header row with a quoted comma inside a cell will be
    over-split. Over-splitting can only produce MORE candidate tokens, so it
    cannot cause a miss -- which is the right direction for a guard to err.
    """
    sep = "\t" if "\t" in line and line.count("\t") >= line.count(",") else ","
    return [cell.strip().strip('"').strip("'") for cell in line.split(sep)]


MARKDOWN_SUFFIXES: frozenset[str] = frozenset({".md", ".markdown", ".rst"})

# Deliberately NOT including .txt: a .txt file is as likely to be a dumped
# response body as it is to be documentation, and the dump is the case this
# guard exists for.

_FENCE = re.compile(r"^\s{0,3}(```|~~~)")


def _fence_mask(lines: list[str]) -> list[bool]:
    """True for each line sitting inside a fenced code block."""
    inside = False
    mask: list[bool] = []
    for line in lines:
        if _FENCE.match(line):
            mask.append(False)          # the fence delimiter is not content
            inside = not inside
            continue
        mask.append(inside)
    return mask


def scan_text(relpath: str, text: str) -> list[tuple[int, str, str]]:
    """Return (line_number, offending_key, principle_v_attribute) findings.

    Values are never captured, never returned, and never printed.

    TWO STRICTNESS LEVELS, and the reason for them. This project's own
    governance and specification documents necessarily NAME the attributes they
    prohibit: Principle V's own prohibition text does, T002's own task text
    does, and the assessment records which fields the member endpoint serves --
    which T004 is likewise instructed to do ("Record field *names* and record
    *counts* only"). A guard that fails the tree for documenting the
    prohibition is a guard that gets switched off, which is worse than no guard
    because it looks like one.

      * A prohibited spelling in a STRUCTURED POSITION -- a JSON/YAML key, a
        CSV header cell, an XML element, an assignment target -- is a payload.
        Fails in every file type, Markdown included.
      * A prohibited spelling in MARKDOWN PROSE outside a code fence is a
        mention. Does not fail. Inside a fence it is treated as data and does
        fail, because a committed raw response pasted into a document lands in
        a fence.
      * In every NON-Markdown file an unambiguous spelling (`dob`,
        `maritalStatus`, `noOfSons` ...) fails in any position whatsoever.

    THE HOLE THIS LEAVES, stated rather than hidden: a raw payload reformatted
    into unfenced Markdown prose would pass. The hole is narrow -- real JSON
    carries `"key":` structure that the structured check catches even unfenced,
    and real CSV carries a header row -- but it is not closed, and no claim is
    made here that it is.
    """
    findings: list[tuple[int, str, str]] = []
    seen: set[tuple[str, str]] = set()
    lines = text.splitlines()
    is_tabular = relpath.endswith((".csv", ".tsv"))
    is_markdown = Path(relpath).suffix.lower() in MARKDOWN_SUFFIXES
    in_fence = _fence_mask(lines) if is_markdown else [False] * len(lines)

    for lineno, line in enumerate(lines, start=1):
        hits: set[str] = set()

        # --- structured positions: in scope in every file type ---
        for match in _STRUCTURED_KEY.finditer(line):
            for group in match.groups():
                if group:
                    hits.add(_canonical(group))

        # CSV/TSV: line 1 is the header row, so every cell is a field name.
        if is_tabular and lineno == 1:
            hits.update(_canonical(cell) for cell in _csv_header_cells(line))

        # --- bare tokens: out of scope in Markdown prose, in scope elsewhere ---
        if (not is_markdown) or in_fence[lineno - 1]:
            for match in _ANY_TOKEN.finditer(line):
                token = _canonical(match.group(0))
                if token in _CANONICAL_AMBIGUOUS:
                    continue            # prose-ambiguous: structured only
                hits.add(token)

        for canon in sorted(hits):
            attribute = _SPELLING_TO_ATTRIBUTE.get(canon)
            if attribute is None:
                continue
            key = (canon, attribute)
            if key in seen:
                continue
            seen.add(key)
            findings.append((lineno, canon, attribute))

    return findings


def iter_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for path in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and not path.is_symlink():
            out.append(path)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fail the tree if a Constitution Principle V prohibited attribute, "
            "or an oversized raw payload, has entered it. Prints paths and "
            "keys only -- never values."
        )
    )
    parser.add_argument(
        "root", nargs="?", default=".",
        help="Directory to scan (default: current directory).",
    )
    parser.add_argument(
        "--max-payload-bytes", type=int, default=PAYLOAD_SIZE_CEILING_BYTES,
        help=f"Payload size ceiling in bytes (default: {PAYLOAD_SIZE_CEILING_BYTES}).",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"guard: not a directory: {root}", file=sys.stderr)
        return 2

    attribute_violations: list[str] = []
    size_violations: list[str] = []
    scanned = 0
    skipped_unreadable: list[str] = []

    for path in iter_files(root):
        relpath = path.relative_to(root).as_posix()
        suffix = path.suffix.lower()

        # --- size ceiling, applied to payload-shaped files ---
        if suffix in PAYLOAD_SUFFIXES:
            size = path.stat().st_size
            if size > args.max_payload_bytes:
                size_violations.append(
                    f"{relpath}: {size} bytes exceeds the "
                    f"{args.max_payload_bytes}-byte payload ceiling"
                )

        # --- attribute scan ---
        if relpath in SELF_EXEMPT or suffix in UNSCANNABLE_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            skipped_unreadable.append(relpath)
            continue

        scanned += 1
        for lineno, key, attribute in scan_text(relpath, text):
            attribute_violations.append(
                f"{relpath}:{lineno}: key '{key}' is a prohibited "
                f"'{attribute}' field (Constitution Principle V)"
            )

    if attribute_violations:
        print("PROHIBITED ATTRIBUTES FOUND (values deliberately not shown):")
        for line in attribute_violations:
            print(f"  {line}")
    if size_violations:
        print("PAYLOAD SIZE CEILING EXCEEDED:")
        for line in size_violations:
            print(f"  {line}")

    if attribute_violations or size_violations:
        print(
            f"\nguard: FAIL -- {len(attribute_violations)} attribute "
            f"violation(s), {len(size_violations)} size violation(s) "
            f"across {scanned} scanned file(s) under {root}"
        )
        return 1

    print(
        f"guard: PASS -- {scanned} file(s) scanned under {root}; "
        f"no prohibited attribute, no payload over "
        f"{args.max_payload_bytes} bytes"
    )
    if skipped_unreadable:
        print(
            f"guard: note -- {len(skipped_unreadable)} file(s) not decodable "
            f"as UTF-8 and therefore not attribute-scanned: "
            f"{', '.join(skipped_unreadable[:5])}"
            + (" ..." if len(skipped_unreadable) > 5 else "")
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
