#!/usr/bin/env python3
"""T089 -- `make lookup CONSTITUENCY=<name>`. `quickstart.md` scenario 7 (US3, SC-008).

> **Expected**: the members representing it within the covered period, each with
> party and term, and their questions reachable. A constituency held by
> different members across the two terms lists both with periods, not merged.
> -- `quickstart.md` scenario 7

**A NAME IS NOT AN IDENTITY, and this tool never pretends otherwise.** Three
constituency names in the covered window name a *different seat* in each of two
states -- Aurangabad (Bihar / Maharashtra), Hamirpur (Himachal Pradesh / Uttar
Pradesh), Maharajganj (Bihar / Uttar Pradesh). Given one of those, this prints
BOTH seats, each under its own state, and says so. It does not pick one, and it
does not merge them: picking would be wrong half the time and silently, and
merging is the exact failure T086 found in the published set.

`STATE=` narrows to one of them.

**It walks the same two files the page does**, deliberately: the constituency
reference set, then the chosen members' own question files. Not
`reference/members.jsonl` (3.4 MB) -- T086 put the name, party and sitting
status on each representation so neither the page nor this tool needs it. A
tool that reached the answer another way would not be checking the route a
consumer has.

THE EXIT CODE IS THE INTERFACE.
    0  the constituency was found and printed
    1  no constituency of that name is in the published record
    2  the check could not run (no published dataset, unreadable input)
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sansad.model._common import NOT_STATED
from sansad.publish.formats import NDJSON_SUFFIX, read_ndjson
from sansad.publish.reference import REFERENCE_DIR_NAME

#: How many of a member's subject lines to print. A sample, said to be one.
SUBJECT_SAMPLE = 5
#: How many questions to print per member.
QUESTION_SAMPLE = 5


def _key(value: str) -> str:
    return " ".join(str(value or "").split()).lower()


def _ordinal(n: int) -> str:
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def _terms_phrase(terms: list[int]) -> str:
    if not terms:
        return NOT_STATED
    words = [_ordinal(t) for t in terms]
    joined = words[0] if len(words) == 1 else f"{', '.join(words[:-1])} and {words[-1]}"
    return f"{joined} Lok Sabha"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--constituency", required=True, help="the seat name, e.g. Aurangabad")
    parser.add_argument("--state", default="", help="narrow to one state when the name repeats")
    parser.add_argument(
        "--published",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "published",
        help="the published dataset directory (default: data/published)",
    )
    args = parser.parse_args(argv)
    root: Path = args.published

    seats_path = root / REFERENCE_DIR_NAME / f"constituencies{NDJSON_SUFFIX}"
    if not seats_path.is_file():
        print(f"lookup: NOT PRESENT -- no {seats_path}. Run `make refresh` first.")
        return 2

    seats = list(read_ndjson(seats_path))
    wanted = _key(args.constituency)
    matches = [s for s in seats if _key(s.get("name")) == wanted]
    if args.state:
        matches = [s for s in matches if _key(s.get("state")) == _key(args.state)]

    print(f"lookup: {args.constituency!r}" + (f" in {args.state!r}" if args.state else ""))
    print(f"        read from {seats_path}")
    print(f"        {len(seats):,} seat(s) in the covered window")
    print()

    if not matches:
        near = sorted(
            {str(s.get("name")) for s in seats if wanted and wanted in _key(s.get("name"))}
        )
        print(f"FAIL: no constituency named {args.constituency!r} is in the published record.")
        if near:
            print(f"      Names containing it: {', '.join(near[:10])}")
        print("      The record covers the 17th and 18th Lok Sabha; a seat with no")
        print("      representation in that window is not published.")
        return 1

    if len(matches) > 1:
        # The whole point. Never one answer, never merged.
        print(f"** {len(matches)} DIFFERENT SEATS share the name {args.constituency!r}. **")
        print("   They are different constituencies in different states, not one seat.")
        print(f'   Narrow with STATE=, e.g. STATE="{matches[0].get("state")}".')
        print()

    for seat in matches:
        _print_seat(seat, root)

    return 0


def _print_seat(seat: dict, root: Path) -> None:
    name = seat.get("name", NOT_STATED)
    state = seat.get("state", NOT_STATED)
    print("=" * 78)
    print(f"{name}  --  {state}")
    print(f"  seat id: {seat.get('constituency_id')}")

    # One entry per DISTINCT member, each with every term they held the seat.
    by_member: dict[str, dict] = {}
    for rep in seat.get("representations") or ():
        member_id = str(rep.get("member_id") or "")
        if not member_id:
            continue
        entry = by_member.setdefault(
            member_id,
            {
                "member_id": member_id,
                "name": rep.get("member_name") or NOT_STATED,
                "party": rep.get("party") or NOT_STATED,
                "sitting_status": rep.get("sitting_status") or NOT_STATED,
                "terms": [],
            },
        )
        if isinstance(rep.get("term_number"), int) and rep["term_number"] not in entry["terms"]:
            entry["terms"].append(rep["term_number"])
    people = sorted(by_member.values(), key=lambda e: (min(e["terms"] or [0]), e["name"]))
    for entry in people:
        entry["terms"].sort()

    terms = sorted({t for e in people for t in e["terms"]})
    if len(people) > 1:
        print(
            f"  {len(people)} DIFFERENT members represented this seat across "
            f"{_terms_phrase(terms)}."
        )
        print("  They are listed separately, with their own terms -- NOT merged.")
    elif people:
        print(f"  One member represented this seat across {_terms_phrase(terms)}.")
    else:
        print("  The published record lists no representation for this seat.")
    print()

    for entry in people:
        print(f"  {entry['name']}")
        print(f"    party          : {entry['party']}")
        print(f"    represented    : {_terms_phrase(entry['terms'])}")
        print(f"    sitting status : {entry['sitting_status']} (as of the last refresh)")
        print(f"    member id      : {entry['member_id']}")
        _print_questions(entry["member_id"], root)
        print()


def _print_questions(member_id: str, root: Path) -> None:
    """The SECOND fetch: this member's own file, and nothing else.

    "their questions reachable" -- so the questions are printed, not merely
    counted. De-duplicated on `question_id` first, which is guarantee 6 and
    what the published counting basis tells a consumer to do.
    """
    path = root / "by-member" / f"{member_id}{NDJSON_SUFFIX}"
    if not path.is_file():
        print("    questions      : none published -- this member asked none in the window")
        return

    by_id: dict[str, dict] = {}
    for row in read_ndjson(path):
        by_id.setdefault(str(row.get("question_id")), row)
    questions = sorted(
        by_id.values(),
        key=lambda r: (str(r.get("date") or ""), str(r.get("question_id") or "")),
        reverse=True,
    )
    statuses = Counter(str(q.get("resolution_status") or NOT_STATED) for q in questions)
    print(f"    questions      : {len(questions):,}  (file: {path.name})")
    print(
        "                     by resolution status: "
        + ", ".join(f"{status} {n:,}" for status, n in sorted(statuses.items()))
    )

    subjects = Counter(str(q.get("subject") or NOT_STATED) for q in questions)
    if subjects:
        print(
            f"    most-asked     : {len(subjects):,} distinct subject line(s); top {SUBJECT_SAMPLE}:"
        )
        for subject, n in sorted(subjects.items(), key=lambda kv: (-kv[1], kv[0]))[:SUBJECT_SAMPLE]:
            print(f"                     {n:>4}  {subject}")

    print(f"    newest {min(QUESTION_SAMPLE, len(questions))} of {len(questions):,}:")
    for question in questions[:QUESTION_SAMPLE]:
        print(
            f"                     {question.get('date')}  {question.get('question_id')}"
            f"  [{question.get('resolution_status')}]"
        )
        print(f"                       {question.get('subject')}")


if __name__ == "__main__":
    raise SystemExit(main())
