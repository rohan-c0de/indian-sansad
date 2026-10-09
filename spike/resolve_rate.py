#!/usr/bin/env python3
"""Throwaway resolver prototype. Measures the identity-resolution rate.

T011. **Deliberately not in `src/`.** `plan.md` Risk 3 calls identity
resolution at ~2h/week "the recommendation's least defensible assumption", and
SC-002's 95% target is an admitted invented default. This file exists to TEST
that figure, not to satisfy it. Keeping it out of `src/` is what stops it
becoming the production matcher by default -- the production matcher should be
designed against this measurement, not grown from it.

Reads from $SANSAD_SCRATCH, outside the repository. Writes its aggregate report
to stdout and its per-form detail back into $SANSAD_SCRATCH. Nothing it writes
into the repository is anything but an aggregate.

====================================================================
MATCHER CONFIGURATION -- FIXED BEFORE THE FIRST RUN, NOT TUNED AFTER
====================================================================
T012: "Do not tune the matcher to reach 95% -- the figure is an invented
default and the measurement's job is to test it, not to satisfy it."

So every threshold below was chosen on stated grounds before any rate was
observed, and is recorded here so a reviewer can disagree with the choice
rather than guess at it:

  APPROX_THRESHOLD = 0.90
      difflib.SequenceMatcher ratio on normalised forms. 0.90 is the
      conventional "near-identical string" cut, high enough that it will not
      merge two different people sharing a surname. NOT chosen by trying
      several and keeping the best.

  APPROX_MARGIN = 0.02
      If the best candidate beats the runner-up by less than this, the result
      is `ambiguous`, not `resolved`. data-model.md requires it: "an ambiguous
      match MUST NOT be silently collapsed to the first candidate".

  HONORIFICS
      Stripped because 98.1% of observed asker forms carry one
      (route-capture.md) and an honorific is not part of anyone's identity.
      `md`/`mohd` are DELIBERATELY ABSENT from this list: they are frequently
      part of a given name rather than a title, and stripping them would
      corrupt real names to flatter the rate.

  CANDIDATE POOL -- measured BOTH ways, `--pool full` and `--pool term`

      `--pool term` selects members whose `lsExpr` CONTAINS the term being
      measured. `lsExpr` is a comma-separated enumeration of every Lok Sabha a
      member served in ("11,12,14,16,17"), which is exact membership rather
      than the approximation `lastLoksabha` gives.

      This replaced an earlier `lastLoksabha == N` test, and the replacement is
      a CORRECTNESS fix, not a tuning change. The control that establishes it:
      for the 18th Lok Sabha the two definitions select the IDENTICAL 544-member
      set, so the previously published 99.68% is unaffected. For the 17th they
      differ sharply -- `lsExpr` contains 17 for 559 members against
      `lastLoksabha == 17` for only 343, because the 216 members who continued
      into the 18th carry lastLoksabha == 18. Measuring the 17th with the old
      test would have withheld 216 of its own sitting members from the pool and
      manufactured unresolved forms that the real pipeline would never see.
      The roster is every Lok Sabha member since the 1st: 5,426 people, of whom
      only 544 have `lastLoksabha == 18`. Matching an 18th-Lok-Sabha question
      against all 5,426 puts 4,882 people in the pool who could not possibly
      have asked it, which manufactures ambiguity that the real pipeline would
      never face.
      Restricting the pool is therefore a CORRECTNESS constraint, not a tuning
      knob -- a question asked in the 18th Lok Sabha cannot have been asked by
      a member whose service ended in the 9th. It is nonetheless reported as a
      SEPARATE configuration rather than folded in silently, because `--pool
      full` is the honest pessimistic bound and the gap between the two is
      itself a finding. Both numbers appear in resolution-rate.md. Neither was
      selected after the fact for being the nicer one.

      A window-level rate is NOT computed by pooling both terms together. Each
      question belongs to exactly one term and is matched against that term's
      members, so the window figure is the sum of the per-term numerators and
      denominators. That is arithmetically identical to per-question pooling
      and needs no change to this script.

Tiers run exact -> normalised -> approximate, in that order, and stop at the
first tier that produces any candidate. A later tier never overrides an
earlier one.

====================================================================
OPTIONAL FINAL TIER: --containment  (OFF by default)
====================================================================
Bidirectional token containment, implemented exactly as described in
spike-report.md T014 Option C:

    "A form resolves if its canonical token set is a strict subset OR strict
     superset of exactly one pool member's token set."

Reached only when every tier above has failed to produce a single member --
i.e. on `unresolved` or `ambiguous` -- which is how the simulation recorded in
spike-report.md was computed. If containment matches more than one distinct
member the form stays unresolved/ambiguous; it never collapses a genuine
ambiguity, per data-model.md.

It exists because the 17th Lok Sabha's failures classified into 10 forms whose
tokens are a strict subset of a roster name (a middle name the question omits)
and 8 where the roster name is a subset of the form (a middle name the question
adds) -- one mechanism, 3,876 instances.

WHY IT IS OFF BY DEFAULT, and why that matters: adding a tier after seeing a
rate fall short is the move T012 forbids. Keeping it behind a flag means the
unchanged matcher remains runnable and directly comparable, so the before/after
is a measurement rather than a replacement.

THIS TIER WAS WRITTEN BEFORE SESSIONS 11-15 OF THE 17TH LOK SABHA WERE
FETCHED. Those sessions are the holdout, and they did not exist on disk when
this code was authored, so no rule or threshold here can have been fitted to
them. Nothing below is adjusted after seeing the holdout result.
"""

from __future__ import annotations

import json
import os
import re
import statistics
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

APPROX_THRESHOLD = 0.90
APPROX_MARGIN = 0.02

HONORIFICS = frozenset({
    "shri", "shrimati", "shrimathi", "smt", "smti", "sri", "srimati",
    "dr", "doctor", "prof", "professor", "adv", "advocate",
    "kumari", "kum", "kunwar", "kunwari", "sardar", "shrimatiji",
    "col", "colonel", "lt", "gen", "general", "capt", "captain", "maj", "major",
    "justice", "thiru", "thirumathi", "er", "mr", "mrs", "ms", "miss",
})

# Roster fields that are name forms. Each gives a `name_variant` for its member.
NAME_FORM_FIELDS = ("mpFirstLastName", "mpLastFirstName")


def canon(text: str) -> str:
    """Normalise a name form.

    Lowercase; drop honorific tokens; strip punctuation to spaces; collapse
    whitespace. Deliberately does NOT reorder tokens -- token reordering is
    what the approximate tier is for, and folding it into normalisation would
    hide which tier did the work.
    """
    if not text:
        return ""
    s = text.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    tokens = [t for t in s.split() if t and t not in HONORIFICS]
    return " ".join(tokens)


def canon_sorted(text: str) -> str:
    """Normalised form with tokens sorted -- order-insensitive comparison."""
    return " ".join(sorted(canon(text).split()))


def terms_served(member: dict) -> set[int]:
    """Parse `lsExpr` -- the comma-separated list of Lok Sabhas served in."""
    return {int(x) for x in str(member.get("lsExpr") or "").split(",")
            if x.strip().isdigit()}


def load_roster(path: Path, pool: str, loksabha: int) -> tuple[list[dict], dict]:
    members: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                members.append(json.loads(line))
    if pool == "term":
        members = [m for m in members if loksabha in terms_served(m)]
    # member_id is minted here as the upstream record id. data-model.md requires
    # it never be derived from a name; mpsno satisfies that.
    for m in members:
        m["_member_id"] = f"ls-{m.get('mpsno')}"
        variants = set()
        for f in NAME_FORM_FIELDS:
            v = (m.get(f) or "").strip()
            if v:
                variants.add(v)
        built = " ".join(
            x for x in (
                (m.get("initial") or "").strip(),
                (m.get("firstName") or "").strip(),
                (m.get("lastName") or "").strip(),
            ) if x
        ).strip()
        if built:
            variants.add(built)
        plain = " ".join(
            x for x in ((m.get("firstName") or "").strip(),
                        (m.get("lastName") or "").strip()) if x
        ).strip()
        if plain:
            variants.add(plain)
        m["_variants"] = sorted(variants)
    return members, {}


def build_indexes(members: list[dict]):
    exact: dict[str, set[str]] = defaultdict(set)
    norm: dict[str, set[str]] = defaultdict(set)
    sortd: dict[str, set[str]] = defaultdict(set)
    tokensets: dict[frozenset[str], set[str]] = defaultdict(set)
    for m in members:
        mid = m["_member_id"]
        for v in m["_variants"]:
            exact[v].add(mid)
            c = canon(v)
            if c:
                norm[c].add(mid)
                sortd[canon_sorted(v)].add(mid)
                tokensets[frozenset(c.split())].add(mid)
    return exact, norm, sortd, tokensets


def containment_match(form: str, tokensets) -> tuple[list[str], int]:
    """Strict bidirectional token containment.

    Returns (member_ids, n_pool_names_matched). Resolves only when exactly ONE
    distinct member is implicated -- several matching names belonging to the
    same person is still one identity and still resolves.
    """
    ft = frozenset(canon(form).split())
    if not ft:
        return ([], 0)
    hits: set[str] = set()
    n = 0
    for pt, ids in tokensets.items():
        if not pt:
            continue
        if ft < pt or pt < ft:
            hits |= ids
            n += 1
    return (sorted(hits), n)


def resolve_form(form: str, exact, norm, sortd, norm_keys: list[str],
                 tokensets=None):
    """Return (status, tier, member_ids, best_score)."""
    raw = form.strip()

    # --- tier 1: exact, verbatim ---
    if raw in exact:
        ids = exact[raw]
        if len(ids) == 1:
            return ("resolved", "exact", sorted(ids), 1.0)
        return fallback("ambiguous", "exact", sorted(ids), 1.0)

    # --- tier 2: normalised (honorifics and punctuation removed) ---
    c = canon(raw)
    if c and c in norm:
        ids = norm[c]
        if len(ids) == 1:
            return ("resolved", "normalised", sorted(ids), 1.0)
        return fallback("ambiguous", "normalised", sorted(ids), 1.0)

    # --- tier 2b: normalised, token order ignored ---
    cs = canon_sorted(raw)
    if cs and cs in sortd:
        ids = sortd[cs]
        if len(ids) == 1:
            return ("resolved", "normalised-reordered", sorted(ids), 1.0)
        return fallback("ambiguous", "normalised-reordered", sorted(ids), 1.0)

    def fallback(status, tier, ids, score):
        """Last resort: the optional containment tier, if enabled."""
        if tokensets is None or status == "resolved":
            return (status, tier, ids, score)
        cids, _ = containment_match(raw, tokensets)
        if len(cids) == 1:
            return ("resolved", "token-containment", cids, 1.0)
        return (status, tier, ids, score)

    # --- tier 3: approximate ---
    if not c:
        return fallback("unresolved", "none", [], 0.0)
    scored: list[tuple[float, str]] = []
    # SequenceMatcher caches an index of seq2, so seq2 is set ONCE per form and
    # seq1 is swapped per candidate -- the cheap direction. real_quick_ratio and
    # quick_ratio are documented UPPER BOUNDS on ratio, so skipping a candidate
    # that fails them cannot change any result; it only avoids the full
    # comparison. This is a speed change, not a semantic one: without it the
    # full-pool run is ~30M comparisons.
    sm = SequenceMatcher(None)
    sm.set_seq2(c)
    for key in norm_keys:
        sm.set_seq1(key)
        if sm.real_quick_ratio() < APPROX_THRESHOLD:
            continue
        if sm.quick_ratio() < APPROX_THRESHOLD:
            continue
        r = sm.ratio()
        if r >= APPROX_THRESHOLD:
            scored.append((r, key))
    if not scored:
        return fallback("unresolved", "approximate-none", [], 0.0)
    scored.sort(reverse=True)
    best_score, best_key = scored[0]
    ids = sorted(norm[best_key])
    if len(ids) > 1:
        return fallback("ambiguous", "approximate", ids, best_score)
    runner = next((s for s, k in scored[1:] if norm[k] != norm[best_key]), None)
    if runner is not None and (best_score - runner) < APPROX_MARGIN:
        tied = sorted({i for s, k in scored if s >= best_score - APPROX_MARGIN
                       for i in norm[k]})
        return fallback("ambiguous", "approximate", tied, best_score)
    return ("resolved", "approximate", ids, best_score)


def main() -> int:
    raw_scratch = os.environ.get("SANSAD_SCRATCH")
    if not raw_scratch:
        sys.exit("SANSAD_SCRATCH is not set.")
    scratch = Path(os.path.realpath(raw_scratch))
    repo = Path(os.path.realpath(Path(__file__).resolve().parent.parent))
    if scratch == repo or repo in scratch.parents:
        sys.exit("REFUSED: SANSAD_SCRATCH is inside the repository.")

    loksabha = 18
    if "--loksabha" in sys.argv:
        loksabha = int(sys.argv[sys.argv.index("--loksabha") + 1])

    roster_p = scratch / "roster_ls.jsonl"
    # --questions lets a sub-slice be measured against its own term's pool --
    # needed to score sessions 11-15 as a holdout while the pool stays LS17.
    if "--questions" in sys.argv:
        questions_p = scratch / sys.argv[sys.argv.index("--questions") + 1]
    else:
        questions_p = scratch / f"questions_ls{loksabha}.jsonl"
    for p in (roster_p, questions_p):
        if not p.exists():
            sys.exit(f"missing input: {p}  (run spike/fetch_slice.py first)")

    pool = "full"
    if "--pool" in sys.argv:
        pool = sys.argv[sys.argv.index("--pool") + 1]
    if pool not in ("full", "term"):
        sys.exit("--pool must be 'full' or 'term'")

    members, _ = load_roster(roster_p, pool, loksabha)
    if not members:
        sys.exit(f"pool '{pool}' selected 0 members for Lok Sabha {loksabha}")
    use_containment = "--containment" in sys.argv
    exact, norm, sortd, tokensets = build_indexes(members)
    norm_keys = list(norm.keys())

    questions: list[dict] = []
    with questions_p.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                questions.append(json.loads(line))

    # --- gather distinct asker name forms ---
    form_counts: Counter[str] = Counter()
    asker_counts: list[int] = []
    sessions: Counter[str] = Counter()
    dates: list[str] = []
    for q in questions:
        mem = q.get("member") or []
        asker_counts.append(len(mem))
        sessions[str(q.get("sessionNo"))] += 1
        if q.get("date"):
            dates.append(str(q["date"]))
        for nm in mem:
            if nm and nm.strip():
                form_counts[nm.strip()] += 1

    # --- resolve each DISTINCT form once ---
    results: dict[str, dict] = {}
    for form in form_counts:
        status, tier, ids, score = resolve_form(
            form, exact, norm, sortd, norm_keys,
            tokensets if use_containment else None)
        results[form] = {"status": status, "tier": tier,
                         "member_ids": ids, "score": round(score, 4),
                         "instances": form_counts[form]}

    # --- aggregate three ways, because the three disagree and SC-002 is
    #     ambiguous about which one it means ---
    by_form = Counter(r["status"] for r in results.values())
    by_instance: Counter[str] = Counter()
    for form, r in results.items():
        by_instance[r["status"]] += r["instances"]

    q_status: Counter[str] = Counter()
    for q in questions:
        mem = [m.strip() for m in (q.get("member") or []) if m and m.strip()]
        if not mem:
            q_status["no_asker_field"] += 1
            continue
        sts = {results[m]["status"] for m in mem}
        if sts == {"resolved"}:
            q_status["resolved"] += 1
        elif "unresolved" in sts:
            q_status["unresolved"] += 1
        else:
            q_status["ambiguous"] += 1

    tiers = Counter(r["tier"] for r in results.values())
    tier_instances: Counter[str] = Counter()
    for r in results.values():
        tier_instances[r["tier"]] += r["instances"]

    def pct(n: int, d: int) -> str:
        return f"{100.0 * n / d:.2f}%" if d else "n/a"

    n_forms = sum(by_form.values())
    n_inst = sum(by_instance.values())
    n_q = len(questions)

    out = {
        "slice": {
            "house": "Lok Sabha",
            "loksabha": loksabha,
            "sessions_present": sorted(sessions, key=lambda s: int(s) if s.isdigit() else 99),
            "questions_per_session": dict(sorted(
                sessions.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 99)),
            "questions_in_slice": n_q,
            "questions_file": questions_p.name,
            "date_min": min(dates) if dates else None,
            "date_max": max(dates) if dates else None,
        },
        "roster": {
            "members": len(members),
            "distinct_name_variants_indexed": len(exact),
            "distinct_normalised_keys": len(norm),
        },
        "matcher_config": {
            "tier_order": ["exact", "normalised", "normalised-reordered", "approximate"],
            "APPROX_THRESHOLD": APPROX_THRESHOLD,
            "APPROX_MARGIN": APPROX_MARGIN,
            "similarity": "difflib.SequenceMatcher.ratio on normalised forms",
            "honorifics_stripped": sorted(HONORIFICS),
            "honorifics_deliberately_not_stripped": ["md", "mohd"],
            "candidate_pool": ("FULL roster, no term restriction (5,426 members)"
                               if pool == "full" else
                               f"Lok Sabha {loksabha} only (lsExpr contains "
                               f"{loksabha}): {len(members)} members"),
            "tuned_after_seeing_results": False,
            "containment_tier_enabled": use_containment,
        },
        "asker_multiplicity": {
            "questions": n_q,
            "name_instances": n_inst,
            "mean_askers_per_question": round(statistics.mean(asker_counts), 4) if asker_counts else None,
            "median_askers_per_question": statistics.median(asker_counts) if asker_counts else None,
            "max_askers_per_question": max(asker_counts) if asker_counts else None,
            "distribution": dict(sorted(Counter(asker_counts).items())),
        },
        "rate_by_distinct_name_form": {
            "denominator": n_forms,
            "resolved": by_form["resolved"], "resolved_pct": pct(by_form["resolved"], n_forms),
            "ambiguous": by_form["ambiguous"], "ambiguous_pct": pct(by_form["ambiguous"], n_forms),
            "unresolved": by_form["unresolved"], "unresolved_pct": pct(by_form["unresolved"], n_forms),
        },
        "rate_by_name_instance": {
            "denominator": n_inst,
            "resolved": by_instance["resolved"], "resolved_pct": pct(by_instance["resolved"], n_inst),
            "ambiguous": by_instance["ambiguous"], "ambiguous_pct": pct(by_instance["ambiguous"], n_inst),
            "unresolved": by_instance["unresolved"], "unresolved_pct": pct(by_instance["unresolved"], n_inst),
        },
        "rate_by_question_all_askers_resolved": {
            "denominator": n_q,
            "resolved": q_status["resolved"], "resolved_pct": pct(q_status["resolved"], n_q),
            "ambiguous": q_status["ambiguous"], "ambiguous_pct": pct(q_status["ambiguous"], n_q),
            "unresolved": q_status["unresolved"], "unresolved_pct": pct(q_status["unresolved"], n_q),
            "no_asker_field": q_status["no_asker_field"],
        },
        "which_tier_did_the_work": {
            "by_distinct_form": dict(tiers),
            "by_name_instance": dict(tier_instances),
        },
        "sc_002_comparison": {
            "target": "95% of in-scope questions resolve to exactly one member identity",
            "measured_by_question": pct(q_status["resolved"], n_q),
            "measured_by_name_instance": pct(by_instance["resolved"], n_inst),
            "measured_by_distinct_form": pct(by_form["resolved"], n_forms),
        },
    }

    print(json.dumps(out, indent=1, ensure_ascii=False))

    # --- per-form detail written to SCRATCH, not the repo ---
    detail_p = scratch / f"resolution_detail_ls{loksabha}_{pool}{'_containment' if use_containment else ''}.json"
    detail_p.write_text(json.dumps(
        {"aggregate": out,
         "forms": {f: r for f, r in sorted(results.items())}},
        indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\n# per-form detail -> {detail_p}", file=sys.stderr)

    needing = sorted(
        ((f, r) for f, r in results.items() if r["status"] != "resolved"),
        key=lambda kv: (-kv[1]["instances"], kv[0]),
    )
    wl = scratch / f"correction_worklist_ls{loksabha}_{pool}{'_containment' if use_containment else ''}.md"
    with wl.open("w", encoding="utf-8") as fh:
        fh.write(f"# T013 correction worklist (Lok Sabha {loksabha}, pool: {pool})\n\n")
        fh.write(f"{len(needing)} distinct name forms came out ambiguous or unresolved.\n")
        fh.write("Ordered by how many question instances each one blocks, "
                 "so the first corrections are the highest-value ones.\n\n")
        fh.write("| # | name form as written | status | tier reached | instances blocked | candidate member_ids |\n")
        fh.write("|---|---|---|---|---|---|\n")
        for i, (f, r) in enumerate(needing, 1):
            cands = ", ".join(r["member_ids"][:6]) or "(none)"
            fh.write(f"| {i} | {f} | {r['status']} | {r['tier']} | "
                     f"{r['instances']} | {cands} |\n")
    print(f"# correction worklist -> {wl}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
