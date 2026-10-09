#!/usr/bin/env python3
"""Prototype subject-search index over the real subjects in the slice.

T018. Throwaway. Writes to $SANSAD_SCRATCH only.

Why this exists: User Story 2's "has this subject been asked before" search
runs in the VISITOR'S BROWSER (research.md, client-side decision), so the index
it searches must be a published file the page fetches. There is no server to
query. research.md records its size as UNVERIFIED and names the open choice:

    "whether the index covers question subjects only or subjects plus ministry
     and member names"

T018 requires one of those to be MEASURED and the other recorded as
**unmeasured**, not as equivalent. This script measures both so the record can
say which is which honestly -- but the measured-and-chosen one is declared in
the output, and the other is labelled for what it is.

Tokenisation is deliberately simple: lowercase, split on non-alphanumerics,
drop tokens of 1-2 characters and a small English stopword set. Nothing
stemmed, nothing language-specific. A more aggressive tokeniser would shrink
the index, and that is exactly why it is not used here -- the measurement
should reflect a tokeniser a maintainer would actually ship at ~2h/week, not
the smallest index achievable.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

STOPWORDS = frozenset("""
a an and are as at be been by for from has have in into is it its of on or
that the their there these this to was were will with not no any all
""".split())

MIN_TOKEN_LEN = 3


def tokenise(text: str) -> set[str]:
    if not text:
        return set()
    out, cur = set(), []
    for ch in text.lower():
        if ch.isalnum():
            cur.append(ch)
        else:
            if cur:
                t = "".join(cur)
                if len(t) >= MIN_TOKEN_LEN and t not in STOPWORDS:
                    out.add(t)
                cur = []
    if cur:
        t = "".join(cur)
        if len(t) >= MIN_TOKEN_LEN and t not in STOPWORDS:
            out.add(t)
    return out


def build(questions: list[dict], include_ministry: bool, include_member: bool):
    postings: dict[str, set[int]] = defaultdict(set)
    for i, q in enumerate(questions):
        toks = tokenise(q.get("subjects") or "")
        if include_ministry:
            toks |= tokenise(q.get("ministry") or "")
        if include_member:
            for nm in (q.get("member") or []):
                toks |= tokenise(nm or "")
        for t in toks:
            postings[t].add(i)
    return postings


def serialise(postings: dict[str, set[int]], qids: list[str]) -> bytes:
    """Compact shape a browser can fetch and use directly.

    Postings are delta-encoded against a sorted doc list, which is what any
    real in-browser index would do; measuring an un-encoded index would
    overstate the size and make the budget look worse than it is.
    """
    doc = {}
    for term, ids in postings.items():
        s = sorted(ids)
        deltas, prev = [], 0
        for v in s:
            deltas.append(v - prev)
            prev = v
        doc[term] = deltas
    blob = {"docs": qids, "terms": doc}
    return json.dumps(blob, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def main() -> int:
    raw = os.environ.get("SANSAD_SCRATCH")
    if not raw:
        sys.exit("SANSAD_SCRATCH is not set.")
    scratch = Path(os.path.realpath(raw))
    repo = Path(os.path.realpath(Path(__file__).resolve().parent.parent))
    if scratch == repo or repo in scratch.parents:
        sys.exit("REFUSED: SANSAD_SCRATCH is inside the repository.")

    terms = [int(x) for x in (sys.argv[sys.argv.index("--loksabha") + 1].split(",")
             if "--loksabha" in sys.argv else ["18"])]
    questions = []
    for t in terms:
        qp = scratch / f"questions_ls{t}.jsonl"
        if not qp.exists():
            sys.exit(f"missing input: {qp}")
        questions += [json.loads(l) for l in qp.open(encoding="utf-8") if l.strip()]

    session = sys.argv[sys.argv.index("--session") + 1] if "--session" in sys.argv else None
    if session is not None:
        questions = [q for q in questions if str(q.get("sessionNo")) == str(session)]

    qids = [f"ls-{q.get('lokNo')}-{q.get('sessionNo')}-{q.get('quesNo')}" for q in questions]

    variants = {
        "subjects_only": (False, False),
        "subjects_plus_ministry_and_member": (True, True),
    }
    results = {}
    out_dir = scratch / "index_sample"
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, (inc_min, inc_mem) in variants.items():
        postings = build(questions, inc_min, inc_mem)
        blob = serialise(postings, qids)
        p = out_dir / f"{name}.json"
        p.write_bytes(blob)
        results[name] = {
            "questions_indexed": len(questions),
            "distinct_terms": len(postings),
            "total_postings": sum(len(v) for v in postings.values()),
            "bytes": len(blob),
            "bytes_per_question": round(len(blob) / len(questions), 2) if questions else None,
            "file": str(p),
        }

    print(json.dumps({
        "slice": {"house": "lok-sabha", "loksabha": terms,
                  "session": session or "ALL SESSIONS IN SLICE",
                  "questions_indexed": len(questions)},
        "tokeniser": {
            "lowercase": True, "split_on": "non-alphanumeric",
            "min_token_length": MIN_TOKEN_LEN,
            "stopwords": sorted(STOPWORDS),
            "stemming": None,
            "postings_encoding": "delta-encoded ascending doc ids",
            "note": "deliberately unaggressive -- a smaller index is achievable "
                    "and is not what a 2h/week maintainer would ship",
        },
        "MEASURED_AND_CHOSEN": "subjects_only",
        "ALSO_MEASURED_FOR_COMPARISON": "subjects_plus_ministry_and_member",
        "variants": results,
    }, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
