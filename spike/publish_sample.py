#!/usr/bin/env python3
"""Prototype publish of ONE real session, across every axis the contract names.

T016. Throwaway. Writes to $SANSAD_SCRATCH only -- `data/published/` is not
created by this script and must not be, because nothing here is pipeline code
and a half-shaped dataset in the real output directory would be mistaken for one.

TWO MODES:
  (default)  one real session, for the T016 per-session byte measurement.
  --window   EVERY question across both covered terms, partitioned exactly as
             the contract specifies -- by-session per session, by-ministry and
             by-member across the whole window. This turns T017's projection
             into a MEASUREMENT, and produces the real file count that T015 had
             to record as UNVERIFIED against GitHub's unpublished ceiling.

Emits every axis `contracts/published-dataset.md` names:
  - by-session   : one question partition for the chosen session
  - by-ministry  : one question file per ministry
  - by-member    : one question file per member_id; a co-asked question appears
                   in each asker's file (contract guarantee 6)
  - reference    : members, ministries, sessions
  - coverage     : the coverage statement for the slice
in BOTH newline-delimited JSON and CSV, because the contract says "Each set is
published in both ... neither is authoritative over the other."

Measures bytes per file, per axis, per format, and the total. The point is a
real byte count from real records, replacing research.md's three UNVERIFIED
assumptions about published size.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

ALLOWED_QUESTION_FIELDS = (
    "question_id", "house", "session", "date", "type", "subject",
    "ministry_id", "asking_members", "resolution_status",
    "source_record_ref", "last_refreshed",
)
# FR-008 set only. No attribute outside it, by construction rather than by filter.
ALLOWED_MEMBER_FIELDS = (
    "member_id", "canonical_name", "name_variants", "house", "party",
    "state", "constituency", "terms", "sitting_status",
    "source_record_ref", "last_refreshed",
)

LAST_REFRESHED = "2026-10-09"


def safe_name(s: str) -> str:
    keep = [c if (c.isalnum() or c in "-_") else "-" for c in (s or "unknown")]
    out = "".join(keep).strip("-").lower()
    while "--" in out:
        out = out.replace("--", "-")
    return out[:80] or "unknown"


def write_ndjson(path: Path, rows: list[dict]) -> int:
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return path.stat().st_size


def write_csv(path: Path, rows: list[dict], fields: tuple[str, ...]) -> int:
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(fields), extrasaction="ignore")
        w.writeheader()
        for r in rows:
            flat = dict(r)
            for k, v in flat.items():
                if isinstance(v, (list, tuple)):
                    # CSV cannot hold a list. Pipe-separated, which is the
                    # choice the real publisher will have to make explicit in
                    # the contract -- recorded here as a prototype decision,
                    # not a settled format.
                    flat[k] = "|".join(str(x) for x in v)
            w.writerow(flat)
    return path.stat().st_size


def main() -> int:
    raw = os.environ.get("SANSAD_SCRATCH")
    if not raw:
        sys.exit("SANSAD_SCRATCH is not set.")
    scratch = Path(os.path.realpath(raw))
    repo = Path(os.path.realpath(Path(__file__).resolve().parent.parent))
    if scratch == repo or repo in scratch.parents:
        sys.exit("REFUSED: SANSAD_SCRATCH is inside the repository.")

    pool = sys.argv[sys.argv.index("--pool") + 1] if "--pool" in sys.argv else "term"
    session = sys.argv[sys.argv.index("--session") + 1] if "--session" in sys.argv else None
    window = "--window" in sys.argv
    terms = [int(x) for x in (sys.argv[sys.argv.index("--loksabha") + 1].split(",")
             if "--loksabha" in sys.argv else (["17", "18"] if window else ["18"]))]

    roster_p = scratch / "roster_ls.jsonl"
    if not roster_p.exists():
        sys.exit(f"missing input: {roster_p}")
    roster = {f"ls-{m['mpsno']}": m
              for m in (json.loads(l) for l in roster_p.open(encoding="utf-8") if l.strip())}

    # Resolution is per-term: a question is matched against its own term's
    # members, so each term carries its own detail file. Merging the FORMS
    # dicts across terms would be wrong -- the same name form can resolve to
    # different members in different terms -- so they are kept keyed by term.
    forms_by_term: dict[int, dict] = {}
    questions = []
    for t in terms:
        dp = scratch / f"resolution_detail_ls{t}_{pool}.json"
        qp = scratch / f"questions_ls{t}.jsonl"
        for need in (dp, qp):
            if not need.exists():
                sys.exit(f"missing input: {need}")
        forms_by_term[t] = json.loads(dp.read_text(encoding="utf-8"))["forms"]
        for l in qp.open(encoding="utf-8"):
            if l.strip():
                q = json.loads(l)
                q["_term"] = t
                questions.append(q)
    print(f"loaded {len(questions):,} questions across terms {terms} "
          f"(pool: {pool})", flush=True)

    if window:
        slice_qs = questions
        print("WINDOW MODE: publishing every question across both terms",
              flush=True)
    else:
        # --- choose the session: the largest one, so the projection is not
        #     flattered by picking a quiet session ---
        if session is None:
            counts = defaultdict(int)
            for q in questions:
                counts[str(q.get("sessionNo"))] += 1
            session = max(counts, key=lambda k: counts[k])
            print(f"session not given; chose the LARGEST session {session} "
                  f"({counts[session]} questions) so the projection is not "
                  f"flattered by a quiet one", flush=True)
        slice_qs = [q for q in questions if str(q.get("sessionNo")) == str(session)]
        if not slice_qs:
            sys.exit(f"no questions for session {session}")

    # --- build published question records ---
    ministries: dict[str, str] = {}
    pub_qs: list[dict] = []
    for q in slice_qs:
        mname = (q.get("ministry") or "not stated").strip()
        mid = safe_name(mname)
        ministries[mid] = mname
        askers, statuses = [], []
        forms = forms_by_term[q["_term"]]
        for nm in (q.get("member") or []):
            r = forms.get((nm or "").strip())
            if r is None:
                statuses.append("unresolved")
                continue
            statuses.append(r["status"])
            if r["status"] == "resolved":
                askers.extend(r["member_ids"])
        if statuses and set(statuses) == {"resolved"}:
            status = "resolved"
        elif "unresolved" in statuses or not statuses:
            status = "unresolved"
        else:
            status = "ambiguous"
        pub_qs.append({
            "question_id": f"ls-{q.get('lokNo')}-{q.get('sessionNo')}-{q.get('quesNo')}",
            "house": "lok-sabha",
            "session": f"ls-{q.get('lokNo')}-{q.get('sessionNo')}",
            "date": q.get("date"),
            "type": q.get("type"),
            "subject": q.get("subjects"),
            "ministry_id": mid,
            "asking_members": sorted(set(askers)),
            "resolution_status": status,
            "source_record_ref": f"api_ls/question:{q.get('lokNo')}/{q.get('sessionNo')}/{q.get('quesNo')}",
            "last_refreshed": LAST_REFRESHED,
        })

    out = scratch / "publish_sample"
    for sub in ("by-session", "by-ministry", "by-member", "reference", "aggregates"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    sizes: list[dict] = []

    def record(axis: str, name: str, rows: list[dict], fields: tuple[str, ...], sub: str):
        nj = out / sub / f"{name}.jsonl"
        nc = out / sub / f"{name}.csv"
        bj = write_ndjson(nj, rows)
        bc = write_csv(nc, rows, fields)
        sizes.append({"axis": axis, "file": f"{sub}/{name}", "records": len(rows),
                      "ndjson_bytes": bj, "csv_bytes": bc})

    # by-session -- one partition per (term, session)
    per_ses: dict[str, list[dict]] = defaultdict(list)
    for q in pub_qs:
        per_ses[q["session"]].append(q)
    for sid, rows in sorted(per_ses.items()):
        record("by-session", sid, rows, ALLOWED_QUESTION_FIELDS, "by-session")

    # by-ministry
    per_min: dict[str, list[dict]] = defaultdict(list)
    for q in pub_qs:
        per_min[q["ministry_id"]].append(q)
    for mid, rows in sorted(per_min.items()):
        record("by-ministry", mid, rows, ALLOWED_QUESTION_FIELDS, "by-ministry")

    # by-member -- a co-asked question appears in EACH asker's file
    per_mem: dict[str, list[dict]] = defaultdict(list)
    for q in pub_qs:
        for mid in q["asking_members"]:
            per_mem[mid].append(q)
    for mid, rows in sorted(per_mem.items()):
        record("by-member", mid, rows, ALLOWED_QUESTION_FIELDS, "by-member")

    # reference: members (FR-008 fields only)
    mem_rows = []
    for mid in sorted(per_mem):
        m = roster.get(mid, {})
        variants = sorted({v for v in (m.get("mpFirstLastName"), m.get("mpLastFirstName")) if v})
        mem_rows.append({
            "member_id": mid,
            "canonical_name": m.get("mpFirstLastName") or "not stated",
            "name_variants": variants,
            "house": "lok-sabha",
            "party": m.get("partyFname") or "not stated",
            "state": m.get("stateName") or "not stated",
            "constituency": m.get("constName") or "not stated",
            "terms": m.get("noOfTerms"),
            "sitting_status": m.get("status") or "not stated",
            "source_record_ref": f"api_ls/member:{m.get('mpsno')}",
            "last_refreshed": LAST_REFRESHED,
        })
    record("reference", "members", mem_rows, ALLOWED_MEMBER_FIELDS, "reference")

    min_rows = [{"ministry_id": k, "canonical_name": v, "name_variants": [v]}
                for k, v in sorted(ministries.items())]
    record("reference", "ministries", min_rows,
           ("ministry_id", "canonical_name", "name_variants"), "reference")

    def dparse(d):
        try:
            return dt.datetime.strptime(d, "%d.%m.%Y").date()
        except Exception:
            return None
    ses_rows = []
    for sid, rows in sorted(per_ses.items()):
        ds = [dparse(r["date"]) for r in rows if r["date"]]
        ds = [d for d in ds if d]
        ses_rows.append({"session_id": sid, "house": "lok-sabha",
                         "number": sid.rsplit("-", 1)[-1],
                         "start_date": str(min(ds)) if ds else None,
                         "end_date": str(max(ds)) if ds else None,
                         "sitting_days": None})
    record("reference", "sessions", ses_rows,
           ("session_id", "house", "number", "start_date", "end_date", "sitting_days"),
           "reference")

    st = defaultdict(int)
    for q in pub_qs:
        st[q["resolution_status"]] += 1
    cov = [{"house": "lok-sabha",
            "period_start": min(r["start_date"] for r in ses_rows if r["start_date"]),
            "period_end": max(r["end_date"] for r in ses_rows if r["end_date"]),
            "sessions_covered": [r["session_id"] for r in ses_rows],
            "known_gaps": ["question and answer text: behind document files, "
                           "never opened (Principle III)"],
            "resolution_rate": round(100.0 * st["resolved"] / len(pub_qs), 2),
            "last_refreshed": LAST_REFRESHED, "last_known_good": False}]
    record("coverage", "coverage-statement", cov,
           ("house", "period_start", "period_end", "sessions_covered",
            "known_gaps", "resolution_rate", "last_refreshed", "last_known_good"),
           "aggregates")

    by_axis: dict[str, dict] = defaultdict(lambda: {"files": 0, "records": 0,
                                                    "ndjson_bytes": 0, "csv_bytes": 0})
    for s in sizes:
        a = by_axis[s["axis"]]
        a["files"] += 2
        a["records"] += s["records"]
        a["ndjson_bytes"] += s["ndjson_bytes"]
        a["csv_bytes"] += s["csv_bytes"]

    total_nd = sum(s["ndjson_bytes"] for s in sizes)
    total_csv = sum(s["csv_bytes"] for s in sizes)
    nd_ses = sum(s["ndjson_bytes"] + s["csv_bytes"] for s in sizes
                 if s["axis"] == "by-session")
    print(json.dumps({
        "mode": "WINDOW (both terms, every question)" if window else f"single session {session}",
        "terms": terms,
        "sessions_published": len(per_ses),
        "questions_in_session": len(pub_qs),
        "distinct_ministries": len(per_min),
        "distinct_members_with_files": len(per_mem),
        "resolution_status_in_session": dict(st),
        "files_written": 2 * len(sizes),
        "by_axis": {k: dict(v) for k, v in sorted(by_axis.items())},
        "total_ndjson_bytes": total_nd,
        "total_csv_bytes": total_csv,
        "total_bytes_both_formats": total_nd + total_csv,
        "bytes_per_question_both_formats": round((total_nd + total_csv) / len(pub_qs), 1),
        "single_copy_by_session_bytes": nd_ses,
        "duplication_multiple_vs_single_copy": round((total_nd + total_csv) / nd_ses, 3),
        "largest_single_file_bytes": max(
            max(s["ndjson_bytes"], s["csv_bytes"]) for s in sizes),
        "output_dir": str(out),
    }, indent=1, ensure_ascii=False))

    (scratch / "publish_sample_sizes.json").write_text(
        json.dumps(sizes, indent=1), encoding="utf-8")
    print(f"\n# per-file sizes -> {scratch / 'publish_sample_sizes.json'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
