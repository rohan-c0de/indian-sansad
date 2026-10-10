#!/usr/bin/env python3
"""T085 / quickstart.md scenario 6 — a reproducible ministry question profile.

    make report MINISTRY=<name> SESSIONS=5-8 [LS_TERM=18]

Scenario 6 asks for "a ministry question profile whose totals can be reproduced
by counting the published question records by hand, and which states the
counting basis alongside the numbers". So this prints three things:

1. the figures from the **published aggregate**
   (`aggregates/ministry-profile.jsonl`), which is what the page renders;
2. an **independent recount** over the published question records in
   `by-session/`, de-duplicated on `question_id`, which never touches the
   aggregation code and is the "by hand" half; and
3. the **counting basis**, read from `aggregates/counting-basis.jsonl` and
   printed verbatim beside the numbers — never retyped here, for the same
   reason the page does not retype it.

It exits non-zero if (1) and (2) disagree. A report that printed a figure
without re-deriving it would be testing nothing, and SC-007 is about
reproducibility rather than about having a number to show.

**`SESSIONS=5-8` is session NUMBERS, across every covered term.** The published
window covers two Lok Sabha terms and both number their sessions from 1, so
`5-8` is ambiguous on its own: it matches 17th-LS sessions 5-8 *and* 18th-LS
sessions 5-8. Rather than pick one silently, this covers both and says so on
the output; `LS_TERM=18` narrows it. Choosing one term quietly is how a figure
comes to mean something different from what the reader assumed.

(`LS_TERM` rather than `TERM` because every interactive shell exports `TERM`;
the Makefile records the measurement.)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The four buckets, in the order the page shows them. Imported rather than
#: retyped, so a fifth bucket added upstream appears here too.
sys.path.insert(0, str(REPO_ROOT / "src"))
from sansad.views.ministry_profile import STATUS_COUNT_FIELDS  # noqa: E402


def ndjson(path: Path) -> list[dict]:
    if not path.is_file():
        raise SystemExit(f"not built: {path}")
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def parse_sessions(spec: str) -> tuple[int, int]:
    text = str(spec).strip()
    if "-" in text:
        low, _, high = text.partition("-")
    else:
        low = high = text
    try:
        return int(low), int(high)
    except ValueError as error:
        raise SystemExit(f"SESSIONS={spec!r} is not a number or a range like 5-8") from error


def find_ministry(name: str, ministries: list[dict]) -> dict:
    """Match on the id, the canonical name, or any published name variant."""
    wanted = name.strip().casefold()
    for record in ministries:
        candidates = {
            str(record.get("ministry_id", "")).casefold(),
            str(record.get("canonical_name", "")).casefold(),
            *(str(v).casefold() for v in record.get("name_variants", [])),
            *(str(v).casefold() for v in record.get("former_names", [])),
        }
        if wanted in candidates:
            return record
    partial = [
        r
        for r in ministries
        if wanted in str(r.get("canonical_name", "")).casefold()
        or wanted in str(r.get("ministry_id", "")).casefold()
    ]
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        names = ", ".join(sorted(str(r["canonical_name"]) for r in partial))
        raise SystemExit(f"MINISTRY={name!r} matches {len(partial)} ministries: {names}")
    raise SystemExit(
        f"MINISTRY={name!r} matches no published ministry. "
        f"{len(ministries)} are published; see data/published/reference/ministries.csv"
    )


def recount(published: Path, ministry_id: str, sessions: set[str]) -> dict:
    """The INDEPENDENT count, straight off `by-session/`.

    Does not import the aggregation code, does not read the aggregate, and
    de-duplicates on `question_id` — the manifest declares one byte-identical
    duplicate the upstream serves twice, and a recount that double-counted it
    would disagree with the aggregate for a reason that is not a defect.
    """
    per_session: dict[str, dict] = {}
    seen_ids: set[str] = set()
    duplicates: list[str] = []
    for path in sorted((published / "by-session").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("ministry_id") != ministry_id or row.get("session") not in sessions:
                continue
            question_id = row.get("question_id")
            if question_id in seen_ids:
                duplicates.append(question_id)
                continue
            seen_ids.add(question_id)
            bucket = per_session.setdefault(
                row["session"],
                {"questions": 0, "types": defaultdict(int), "status": defaultdict(int)},
            )
            bucket["questions"] += 1
            bucket["types"][row.get("type", "not stated")] += 1
            # The same rule as `ministry_profile._bucket`, re-derived here from
            # the two published fields rather than imported: that is what makes
            # this an independent check and not a second call to the same code.
            status = row.get("resolution_status")
            askers = row.get("asking_members") or []
            if status == "resolved":
                key = "fully_linked"
            elif status == "ambiguous":
                key = "ambiguous"
            elif askers:
                key = "partly_linked"
            else:
                key = "not_linked"
            bucket["status"][key] += 1
    return {"per_session": per_session, "duplicates": duplicates}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ministry", required=True)
    parser.add_argument("--sessions", required=True)
    parser.add_argument("--term", default="", help="narrow to one Lok Sabha term, e.g. 18")
    parser.add_argument("--published", type=Path, default=REPO_ROOT / "data" / "published")
    args = parser.parse_args()

    published = args.published
    ministries = ndjson(published / "reference" / "ministries.jsonl")
    rows = ndjson(published / "aggregates" / "ministry-profile.jsonl")
    basis_rows = ndjson(published / "aggregates" / "counting-basis.jsonl")
    session_rows = ndjson(published / "reference" / "sessions.jsonl")

    ministry = find_ministry(args.ministry, ministries)
    low, high = parse_sessions(args.sessions)
    term = str(args.term).strip()

    wanted_sessions = [
        s
        for s in session_rows
        if low <= int(s["number"]) <= high and (not term or str(s["term"]) == term)
    ]
    wanted_sessions.sort(key=lambda s: (int(s["term"]), int(s["number"])))
    session_ids = [s["session_id"] for s in wanted_sessions]

    print("make report — quickstart.md scenario 6 (US2, FR-012, SC-007)")
    print("=" * 94)
    print(f"Ministry    : {ministry['canonical_name']}   (id {ministry['ministry_id']})")
    if ministry.get("former_names"):
        print(
            f"              formerly {'; '.join(ministry['former_names'])} — questions "
            "under every name are counted together; the record does not publish when a "
            "rename happened, so no date is shown"
        )
    print(f"Sessions    : numbers {low}-{high}" + (f", term {term} only" if term else ""))
    if not term:
        print(
            "              ACROSS BOTH COVERED TERMS. The two Lok Sabha terms each "
            "number their sessions from 1, so a bare range matches both; pass "
            "LS_TERM= to narrow it."
        )
    print(f"              resolves to {len(session_ids)}: {', '.join(session_ids)}")
    print()

    if not session_ids:
        print("No published session has a number in that range.")
        return 1

    # ---- (1) the published aggregate -----------------------------------
    by_session = {
        r["session"]: r
        for r in rows
        if r["ministry_id"] == ministry["ministry_id"] and r["session"] in set(session_ids)
    }

    types = sorted({t for r in by_session.values() for t in (r.get("question_type_mix") or {})})
    header = f"{'session':<18}{'questions':>10}"
    for one in types:
        header += f"{one:>10}"
    for field in STATUS_COUNT_FIELDS:
        header += f"{field:>14}"

    print("1. FROM THE PUBLISHED AGGREGATE — aggregates/ministry-profile.jsonl")
    print("-" * 94)
    print(header)
    agg_totals = {"questions": 0, "types": defaultdict(int), "status": defaultdict(int)}
    for session_id in session_ids:
        row = by_session.get(session_id)
        if row is None:
            # An explicit zero, not a skipped row: a gap in the series is
            # information, and the page shows it the same way.
            line = f"{session_id:<18}{0:>10}"
            for _ in types:
                line += f"{0:>10}"
            for _ in STATUS_COUNT_FIELDS:
                line += f"{0:>14}"
            print(line + "   (no row — this ministry has no question in this session)")
            continue
        line = f"{session_id:<18}{row['questions']:>10}"
        agg_totals["questions"] += row["questions"]
        mix = row.get("question_type_mix") or {}
        for one in types:
            line += f"{mix.get(one, 0):>10}"
            agg_totals["types"][one] += mix.get(one, 0)
        for field in STATUS_COUNT_FIELDS:
            line += f"{row.get(field, 0):>14}"
            agg_totals["status"][field] += row.get(field, 0)
        print(line)
    line = f"{'TOTAL':<18}{agg_totals['questions']:>10}"
    for one in types:
        line += f"{agg_totals['types'][one]:>10}"
    for field in STATUS_COUNT_FIELDS:
        line += f"{agg_totals['status'][field]:>14}"
    print("-" * 94)
    print(line)
    status_sum = sum(agg_totals["status"][f] for f in STATUS_COUNT_FIELDS)
    print(
        f"{'':<18}{'':>10}  status split sums to {status_sum:,} against "
        f"{agg_totals['questions']:,} questions"
        + ("  OK" if status_sum == agg_totals["questions"] else "  MISMATCH")
    )
    print()

    # ---- (2) the independent recount ------------------------------------
    print("2. RECOUNTED INDEPENDENTLY — straight off by-session/, de-duplicated on question_id")
    print("-" * 94)
    print(header)
    manual = recount(published, ministry["ministry_id"], set(session_ids))
    man_totals = {"questions": 0, "types": defaultdict(int), "status": defaultdict(int)}
    for session_id in session_ids:
        bucket = manual["per_session"].get(session_id)
        questions = bucket["questions"] if bucket else 0
        line = f"{session_id:<18}{questions:>10}"
        man_totals["questions"] += questions
        for one in types:
            value = bucket["types"].get(one, 0) if bucket else 0
            line += f"{value:>10}"
            man_totals["types"][one] += value
        for field in STATUS_COUNT_FIELDS:
            value = bucket["status"].get(field, 0) if bucket else 0
            line += f"{value:>14}"
            man_totals["status"][field] += value
        print(line)
    line = f"{'TOTAL':<18}{man_totals['questions']:>10}"
    for one in types:
        line += f"{man_totals['types'][one]:>10}"
    for field in STATUS_COUNT_FIELDS:
        line += f"{man_totals['status'][field]:>14}"
    print("-" * 94)
    print(line)
    if manual["duplicates"]:
        print(
            f"{len(manual['duplicates'])} duplicate question_id(s) dropped from the recount: "
            f"{', '.join(sorted(set(manual['duplicates'])))}"
        )
    print()

    # ---- (3) the counting basis, read not retyped -----------------------
    units = {
        r.get("counting_basis_unit") for r in by_session.values() if r.get("counting_basis_unit")
    }
    unit = sorted(units)[0] if units else "question"
    basis = next((b for b in basis_rows if b.get("unit") == unit), None)
    print("3. THE COUNTING BASIS — read from aggregates/counting-basis.jsonl, not retyped here")
    print("-" * 94)
    if basis is None:
        print(f"  NO published basis for unit {unit!r}. The figures above are unexplained.")
    else:
        print(f"  unit          : {basis['unit']}")
        print(f"  basis_version : {basis.get('basis_version')}")
        print(f"  counting_basis: {basis['counting_basis']}")
    print()

    # ---- the comparison ------------------------------------------------
    print("=" * 94)
    differences = []
    if agg_totals["questions"] != man_totals["questions"]:
        differences.append(
            f"questions: aggregate {agg_totals['questions']:,} vs recount {man_totals['questions']:,}"
        )
    for one in types:
        if agg_totals["types"][one] != man_totals["types"][one]:
            differences.append(
                f"{one}: aggregate {agg_totals['types'][one]:,} vs recount {man_totals['types'][one]:,}"
            )
    for field in STATUS_COUNT_FIELDS:
        if agg_totals["status"][field] != man_totals["status"][field]:
            differences.append(
                f"{field}: aggregate {agg_totals['status'][field]:,} vs "
                f"recount {man_totals['status'][field]:,}"
            )
    if status_sum != agg_totals["questions"]:
        differences.append(f"status split sums to {status_sum:,}, not {agg_totals['questions']:,}")
    if basis is None:
        differences.append(f"no counting basis published for unit {unit!r}")

    if differences:
        print("make report: FAIL — the published aggregate and an independent recount differ:")
        for one in differences:
            print(f"  - {one}")
        return 1
    print(
        f"make report: PASS — every figure above was reproduced by counting the published "
        f"question records independently ({man_totals['questions']:,} questions over "
        f"{len(session_ids)} session(s)), and the counting basis is stated beside them."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
