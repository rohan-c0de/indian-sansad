#!/usr/bin/env python3
"""Fetch the spike's real slice into $SANSAD_SCRATCH. THROWAWAY.

This is measurement scaffolding for spike item 3 (T011-T014), deliberately not
in `src/`. Nothing here is pipeline code.

TWO RULES IT ENFORCES, both from Constitution Principle V:

1. **Everything it writes goes under $SANSAD_SCRATCH, outside the repository.**
   It resolves the path and refuses to run if it lands inside the tree, the
   same assertion `make scratch` makes, repeated here because a script that
   trusts its caller's environment variable is not a guard.

2. **Fields are selected by a POSITIVE allowlist**, never by denying a list of
   prohibited ones. Two reasons. First, Principle V: "The absence of a
   prohibition is NOT permission" -- a deny-list silently admits every field
   the upstream adds later, and the upstream carries no contract, versioning or
   deprecation notice. Second, practical: naming the prohibited fields in this
   file would itself trip `tools/guard_no_raw_payloads.py`, which scans Python
   source at full strictness. A guard you have to exempt your own code from is
   a guard with a hole in it.

The member allowlist below IS the FR-008 set -- name forms, party, state,
constituency, House, term, sitting status -- plus the upstream record id and
timestamps, which are record metadata rather than personal attributes.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://sansad.in"
ROSTER_PATH = "/api_ls/member"
SESSION_PATH = "/api_ls/business/getAllLoksabhaAndSession"
# The upstream's own spelling. "qet", not "get". Correcting it yields 404.
QUESTION_PATH = "/api_ls/question/qetFilteredQuestionsAns"

# --- FR-008 allowlist for member records ---------------------------------
MEMBER_ALLOWED = (
    "mpsno",            # upstream record id -> source_record_ref
    "initial",          # name form component
    "firstName",        # name form component
    "lastName",         # name form component
    "mpFirstLastName",  # name form, given-first
    "mpLastFirstName",  # name form, surname-first
    "partyFname",       # party, full
    "partySname",       # party, short
    "stateName",        # state
    "constName",        # constituency
    "noOfTerms",        # term
    "lastLoksabha",     # term
    "lsExpr",           # term
    "status",           # sitting status
    "createdAt",        # record metadata, FR-016
    "updatedAt",        # record metadata, FR-016
)

# --- allowlist for question records --------------------------------------
# The four document-path fields are excluded under Principle III (never
# opened, never depended on) and the Hindi field under Principle IV.
QUESTION_ALLOWED = (
    "quesNo",
    "lokNo",
    "sessionNo",
    "date",
    "type",
    "subjects",
    "ministry",
    "member",
    "supplementaryType",
)

PAGE_SIZE = 1000
LOKSABHA = 18   # default; override with --loksabha N


def scratch_dir() -> Path:
    raw = os.environ.get("SANSAD_SCRATCH")
    if not raw:
        sys.exit("SANSAD_SCRATCH is not set. Run `make scratch` and export it.")
    resolved = Path(os.path.realpath(raw))
    repo = Path(os.path.realpath(Path(__file__).resolve().parent.parent))
    if resolved == repo or repo in resolved.parents:
        sys.exit(
            f"REFUSED: SANSAD_SCRATCH resolves inside the repository.\n"
            f"  resolved  : {resolved}\n  repo root : {repo}\n"
            f"Constitution Principle V: no raw upstream payload is ever "
            f"written inside this tree."
        )
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def get_json(url: str, timeout: int = 180, attempts: int = 4):
    """GET and parse. Retries on transport error with linear backoff.

    No HEAD probe anywhere: `route-capture.md` T005 records HEAD returning 403
    where GET returns 200 on this service.
    """
    last = None
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8")), resp.status
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
                json.JSONDecodeError) as exc:
            last = exc
            if attempt < attempts:
                wait = 5 * attempt
                print(f"    attempt {attempt} failed ({type(exc).__name__}); "
                      f"retrying in {wait}s", flush=True)
                time.sleep(wait)
    raise RuntimeError(f"gave up after {attempts} attempts: {last}")


def project(record: dict, allowed: tuple[str, ...]) -> dict:
    return {k: record.get(k) for k in allowed}


def fetch_roster(out: Path) -> int:
    print(f"roster: GET {ROSTER_PATH}", flush=True)
    t0 = time.monotonic()
    payload, status = get_json(BASE + ROSTER_PATH)
    rows = payload["membersDtoList"]
    meta = payload.get("metaDatasDto", {})
    print(f"  status={status} totalElements={meta.get('totalElements')} "
          f"rows={len(rows)} elapsed={time.monotonic()-t0:.1f}s", flush=True)
    dropped = sorted(set(rows[0]) - set(MEMBER_ALLOWED)) if rows else []
    with out.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(project(r, MEMBER_ALLOWED), ensure_ascii=False) + "\n")
    print(f"  kept {len(MEMBER_ALLOWED)} allowlisted field(s); "
          f"DROPPED {len(dropped)} upstream field(s) before any write",
          flush=True)
    return len(rows)


def session_numbers(loksabha: int) -> list[int]:
    """Session numbers for a term, from the upstream's own enumeration."""
    payload, _ = get_json(f"{BASE}{SESSION_PATH}?locale=en")
    for row in payload:
        if row.get("loksabha") == loksabha:
            return sorted(s["sessionNo"] for s in row.get("sessions", []))
    return []


def fetch_questions_per_session(out: Path, loksabha: int) -> tuple[int, int]:
    """Fetch session by session instead of paging through the whole term.

    WHY: paging the whole term means `pageNo` reaches 61 for the 17th Lok
    Sabha, and each request asks the service to position itself inside a
    60,549-row result set. Asking per session makes every result set ~4,000
    rows and caps page depth at ~5.

    This is also the experiment that separates two explanations for the 17th
    being ~3x slower per page than the 18th -- offset depth versus result-set
    size. Both predict per-session is faster, so a speed-up does not
    distinguish them; but no speed-up would rule BOTH out and point at
    throttling instead. The whole-term page times are kept as the control at
    $SANSAD_SCRATCH/ls17_wholeterm_page_times.txt.
    """
    sessions = session_numbers(loksabha)
    if not sessions:
        raise RuntimeError(f"no sessions enumerated for loksabha {loksabha}")
    print(f"questions: loksabhaNo={loksabha}, PER-SESSION mode, "
          f"sessions {sessions}", flush=True)

    written = 0
    grand_total = 0
    page_times: list[tuple[int, int, float]] = []
    with out.open("w", encoding="utf-8") as fh:
        for sn in sessions:
            t0 = time.monotonic()
            first, _ = get_json(
                f"{BASE}{QUESTION_PATH}?loksabhaNo={loksabha}&sessionNumber={sn}"
                f"&pageNo=1&locale=en&pageSize={PAGE_SIZE}"
            )
            total = first[0]["totalRecordSize"]
            grand_total += total
            pages = -(-total // PAGE_SIZE)
            el = time.monotonic() - t0
            page_times.append((sn, 1, el))
            rows = first[0]["listOfQuestions"] or []
            for r in rows:
                fh.write(json.dumps(project(r, QUESTION_ALLOWED),
                                    ensure_ascii=False) + "\n")
            written += len(rows)
            print(f"  session {sn:>2}: total={total:>6}  pages={pages}  "
                  f"page 1/{pages} {len(rows):>4} rows ({el:.1f}s)", flush=True)

            for page in range(2, pages + 1):
                t0 = time.monotonic()
                payload, _ = get_json(
                    f"{BASE}{QUESTION_PATH}?loksabhaNo={loksabha}"
                    f"&sessionNumber={sn}&pageNo={page}&locale=en"
                    f"&pageSize={PAGE_SIZE}"
                )
                rows = payload[0]["listOfQuestions"] or []
                for r in rows:
                    fh.write(json.dumps(project(r, QUESTION_ALLOWED),
                                        ensure_ascii=False) + "\n")
                written += len(rows)
                el = time.monotonic() - t0
                page_times.append((sn, page, el))
                print(f"  session {sn:>2}: page {page}/{pages} "
                      f"{len(rows):>4} rows ({el:.1f}s)  cumulative={written}",
                      flush=True)

    ts = [t for _, _, t in page_times]
    if ts:
        ts_sorted = sorted(ts)
        med = ts_sorted[len(ts_sorted) // 2]
        print(f"\n  PER-SESSION page timing: {len(ts)} requests  "
              f"min={min(ts):.1f}s  median={med:.1f}s  "
              f"mean={sum(ts)/len(ts):.1f}s  max={max(ts):.1f}s", flush=True)
    return written, grand_total


def fetch_questions(out: Path, loksabha: int) -> tuple[int, int]:
    first, status = get_json(
        f"{BASE}{QUESTION_PATH}?loksabhaNo={loksabha}&pageNo=1"
        f"&locale=en&pageSize={PAGE_SIZE}"
    )
    total = first[0]["totalRecordSize"]
    pages = -(-total // PAGE_SIZE)
    print(f"questions: loksabhaNo={loksabha}, totalRecordSize={total}, "
          f"pageSize={PAGE_SIZE} -> {pages} pages", flush=True)

    written = 0
    with out.open("w", encoding="utf-8") as fh:
        for page in range(1, pages + 1):
            t0 = time.monotonic()
            if page == 1:
                payload = first
            else:
                payload, status = get_json(
                    f"{BASE}{QUESTION_PATH}?loksabhaNo={loksabha}&pageNo={page}"
                    f"&locale=en&pageSize={PAGE_SIZE}"
                )
            rows = payload[0]["listOfQuestions"] or []
            for r in rows:
                fh.write(json.dumps(project(r, QUESTION_ALLOWED),
                                    ensure_ascii=False) + "\n")
            written += len(rows)
            print(f"  page {page}/{pages}: {len(rows):>4} rows  "
                  f"({time.monotonic()-t0:.1f}s)  cumulative={written}",
                  flush=True)
            if not rows:
                print("  empty page -- stopping early", flush=True)
                break
    return written, total


def main() -> int:
    loksabha = LOKSABHA
    if "--loksabha" in sys.argv:
        loksabha = int(sys.argv[sys.argv.index("--loksabha") + 1])
    skip_roster = "--skip-roster" in sys.argv

    scratch = scratch_dir()
    print(f"SANSAD_SCRATCH = {scratch}  (verified outside the repo)", flush=True)
    print(f"loksabhaNo = {loksabha}\n", flush=True)

    roster_out = scratch / "roster_ls.jsonl"
    questions_out = scratch / f"questions_ls{loksabha}.jsonl"

    t0 = time.monotonic()
    if skip_roster and roster_out.exists():
        n_members = sum(1 for l in roster_out.open(encoding="utf-8") if l.strip())
        print(f"roster: reusing {roster_out} ({n_members} rows) -- the roster is "
              f"term-independent, so re-fetching 5.0 MiB would change nothing\n",
              flush=True)
    else:
        n_members = fetch_roster(roster_out)
        print(f"  -> {roster_out} ({roster_out.stat().st_size} bytes)\n", flush=True)

    if "--per-session" in sys.argv:
        n_questions, total = fetch_questions_per_session(questions_out, loksabha)
    else:
        n_questions, total = fetch_questions(questions_out, loksabha)
    print(f"\n  -> {questions_out} ({questions_out.stat().st_size} bytes)")
    print(f"\nSUMMARY  members={n_members}  questions_written={n_questions}  "
          f"totalRecordSize={total}  "
          f"complete={'YES' if n_questions == total else 'NO'}  "
          f"elapsed={time.monotonic()-t0:.1f}s", flush=True)
    return 0 if n_questions == total else 1


if __name__ == "__main__":
    sys.exit(main())
