#!/usr/bin/env python3
"""Does `src/sansad/resolve` reproduce the spike's measured numbers?

T046 carries forward a matcher configuration that was holdout-validated in
`spike/resolve_rate.py`, and every figure in the owner's SC-002 decision rests
on it. Carrying it forward is a claim; this script is the check. It re-runs the
**production** resolver over the **same** window the spike measured and
compares, per question and per name form, against the spike's own per-form
detail files.

Three configurations, with the figures `spike/resolution-rate.md` published:

    containment OFF                      spike: 86,352 / 95,269 = 90.64%
    containment ON                       spike: 90,299 / 95,269 = 94.78%
    containment ON + four assertions     spike: 91,708 / 95,269 = 96.26%

**Reads only from `$SANSAD_SCRATCH`. Writes nothing, anywhere.** Output goes to
stdout. Constitution Principle V: no raw upstream payload is ever written
inside the repository tree, and the question and roster files this reads are
exactly such payloads -- filtered through the spike's own allowlist, but
upstream bodies all the same. The scratch path is resolved with symlinks and
`..` collapsed and compared against the repository root; it refuses rather than
falling back.

**What is printed is aggregates plus name forms.** Name forms are inside
Principle V's permitted set; no other attribute of any person appears in the
output, and no record is reproduced.

**The pool is selected on `lsExpr`, exactly as `--pool term` does.** Not through
`Member.terms`, which falls back to `lastLoksabha` when `lsExpr` is empty -- a
fallback `sansad.ingest.members` adds and the spike does not. Replicating the
spike means replicating its pool rule, so the rule is applied here on the raw
record and the divergence between the two is reported as a control rather than
being allowed to masquerade as a matcher difference.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sansad.ingest.members import load_members
from sansad.ingest.questions import load_question_records
from sansad.model._common import ResolutionStatus
from sansad.resolve import resolve_questions
from sansad.resolve.assertions import load_assertions

#: The figures to reproduce, from `spike/resolution-rate.md` -> FINAL.
SPIKE_WINDOW = {
    "off": (86_352, 95_269, "90.64%"),
    "on": (90_299, 95_269, "94.78%"),
    "assertions": (91_708, 95_269, "96.26%"),
}
#: Per-term resolved counts the report gives, so a window mismatch can be
#: attributed to a term rather than only observed.
SPIKE_PER_TERM = {
    (18, "off"): 34_610,
    (17, "off"): 51_742,
    (18, "on"): 34_716,
    (17, "on"): 55_583,  # derived: 90,299 - 34,716
}
TERMS = (18, 17)


def scratch_root() -> Path:
    raw = os.environ.get("SANSAD_SCRATCH") or ""
    if not raw:
        sys.exit(
            "SANSAD_SCRATCH is not set. This script reads the spike's fetched "
            "window and will not look for it inside the repository."
        )
    resolved = Path(os.path.realpath(Path(raw).expanduser()))
    repo = Path(os.path.realpath(Path(__file__).resolve().parents[1]))
    if resolved == repo or repo in resolved.parents:
        sys.exit(
            f"REFUSED: SANSAD_SCRATCH resolves inside the repository.\n"
            f"  resolved  : {resolved}\n  repo root : {repo}\n"
            f"Constitution Principle V."
        )
    if not resolved.is_dir():
        sys.exit(f"SANSAD_SCRATCH does not exist: {resolved}")
    return resolved


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def ls_expr_terms(record: Mapping[str, Any]) -> set[int]:
    """`lsExpr` parsed the spike's way, and only that way."""
    return {
        int(part) for part in str(record.get("lsExpr") or "").split(",") if part.strip().isdigit()
    }


def pct(numerator: int, denominator: int) -> str:
    return f"{100.0 * numerator / denominator:.2f}%" if denominator else "n/a"


def run_term(
    scratch: Path,
    term: int,
    roster: list[dict[str, Any]],
    *,
    containment: bool,
    assertions: Mapping[str, Any] | None,
):
    pool_records = [r for r in roster if term in ls_expr_terms(r)]
    members = load_members(pool_records, last_refreshed="2026-10-09")

    # Control: does `sansad.ingest.members` agree with the spike's pool rule?
    disagreeing_pool = sum(
        1
        for record, member in zip(pool_records, members, strict=True)
        if {t.number for t in member.terms} != ls_expr_terms(record)
    )

    questions = load_question_records(
        read_jsonl(scratch / f"questions_ls{term}.jsonl"), last_refreshed="2026-10-09"
    )
    result = resolve_questions(questions, members, assertions=assertions, containment=containment)
    no_asker = sum(1 for q in questions if not q.asker_forms)
    # In record order, NOT keyed by question_id. The derived composite
    # `(lokNo, sessionNo, quesNo)` is NOT unique over the full window -- 7,431
    # records collide onto an already-used id, because `quesNo` is numbered per
    # (session, TYPE) and starred/unstarred are separate series. A dict keyed by
    # it silently drops records and miscounts. See `spike/matcher-equivalence.md`.
    asker_forms = tuple(q.asker_forms for q in questions)
    return result, len(members), disagreeing_pool, no_asker, asker_forms


def check_question_identity(scratch: Path) -> list[tuple[int, int, int, int, int]]:
    """Is the derived `question_id` actually unique over the full window?

    `route-capture.md` left this open: "`quesNo` uniqueness is observed **within
    one session only** (250 records, 0 duplicates)". The composite
    `(lokNo, sessionNo, quesNo)` that `sansad.ingest.questions` derives rests on
    it, and contract guarantee 6 ("a `question_id` appearing in several files is
    **one** question") rests on the composite. Checking it is free here, and the
    full window is the only place it can be checked.

    Returns one row per term: (term, records, distinct composite, distinct
    composite+type, distinct composite+type+date).
    """
    rows: list[tuple[int, int, int, int, int]] = []
    for term in TERMS:
        records = read_jsonl(scratch / f"questions_ls{term}.jsonl")
        base = {(r["lokNo"], r["sessionNo"], r["quesNo"]) for r in records}
        with_type = {(r["lokNo"], r["sessionNo"], r["quesNo"], r["type"]) for r in records}
        with_date = {
            (r["lokNo"], r["sessionNo"], r["quesNo"], r["type"], r["date"]) for r in records
        }
        rows.append((term, len(records), len(base), len(with_type), len(with_date)))
    return rows


def spike_forms(scratch: Path, term: int, *, containment: bool) -> dict[str, dict[str, Any]]:
    suffix = "_containment" if containment else ""
    path = scratch / f"resolution_detail_ls{term}_term{suffix}.json"
    if not path.exists():
        return {}
    return json.load(path.open(encoding="utf-8"))["forms"]


def compare_forms(
    outcomes: Mapping[str, Any], reference: Mapping[str, Mapping[str, Any]]
) -> list[tuple[str, str, str]]:
    """Forms where the production matcher and the spike script disagree.

    Returns (form, spike_description, production_description). Compared on
    status and member ids -- the two things a published join is made of -- and
    on the tier, because `ResolutionRecord.method` publishes it and the owner's
    decision rests on the per-tier breakdown.
    """
    out: list[tuple[str, str, str]] = []
    for form, spike in sorted(reference.items()):
        produced = outcomes.get(form)
        if produced is None:
            out.append((form, f"{spike['status']} via {spike['tier']}", "FORM ABSENT"))
            continue
        spike_ids = tuple(spike.get("member_ids") or ())
        if (
            produced.status.value != spike["status"]
            or produced.member_ids != spike_ids
            or produced.tier_reached != spike["tier"]
        ):
            out.append(
                (
                    form,
                    f"{spike['status']} via {spike['tier']} -> {spike_ids or '()'}",
                    f"{produced.status.value} via {produced.tier_reached} "
                    f"-> {produced.member_ids or '()'}",
                )
            )
    missing_from_spike = sorted(set(outcomes) - set(reference))
    for form in missing_from_spike:
        produced = outcomes[form]
        out.append(
            (
                form,
                "FORM ABSENT",
                f"{produced.status.value} via {produced.tier_reached} "
                f"-> {produced.member_ids or '()'}",
            )
        )
    return out


def main() -> int:
    scratch = scratch_root()
    roster = read_jsonl(scratch / "roster_ls.jsonl")
    assertions = load_assertions()

    print("# Matcher equivalence: `src/sansad/resolve` against `spike/resolve_rate.py`")
    print()
    print(f"- scratch root: `{scratch}` (outside the repository; nothing written)")
    print(f"- roster records read: **{len(roster)}**")
    print(f"- assertions loaded from `data/assertions/`: **{len(assertions)}**")
    print()

    results: dict[str, dict[int, Any]] = {}
    pool_sizes: dict[int, int] = {}
    pool_disagreements: dict[int, int] = {}
    no_asker_counts: dict[int, int] = {}
    disagreements: dict[str, list[tuple[str, str, str]]] = {}
    question_forms: dict[int, tuple[tuple[str, ...], ...]] = {}

    for config, containment, applied in (
        ("off", False, None),
        ("on", True, None),
        ("assertions", True, assertions),
    ):
        results[config] = {}
        rows: list[tuple[str, str, str]] = []
        for term in TERMS:
            result, pool, pool_bad, no_asker, asker_forms = run_term(
                scratch, term, roster, containment=containment, assertions=applied
            )
            question_forms[term] = asker_forms
            results[config][term] = result
            pool_sizes[term] = pool
            pool_disagreements[term] = pool_bad
            no_asker_counts[term] = no_asker
            if applied is None:
                rows.extend(
                    compare_forms(
                        result.outcomes, spike_forms(scratch, term, containment=containment)
                    )
                )
        if applied is None:
            disagreements[config] = rows

    print("## The three result lines")
    print()
    print("| Configuration | Produced | Rate | Spike | Rate | Agrees |")
    print("|---|---:|---:|---:|---:|:--:|")
    produced_window: dict[str, tuple[int, int]] = {}
    for config, label in (
        ("off", "containment OFF"),
        ("on", "containment ON"),
        ("assertions", "containment ON + four assertions"),
    ):
        key = "resolved_assisted" if config == "assertions" else "resolved_automatic"
        resolved = sum(getattr(results[config][t], key) for t in TERMS)
        total = sum(results[config][t].total_questions for t in TERMS)
        produced_window[config] = (resolved, total)
        s_res, s_total, s_pct = SPIKE_WINDOW[config]
        agrees = "YES" if (resolved, total) == (s_res, s_total) else "**NO**"
        print(
            f"| {label} | {resolved:,} / {total:,} | **{pct(resolved, total)}** "
            f"| {s_res:,} / {s_total:,} | {s_pct} | {agrees} |"
        )
    print()

    print("## Per term, so a mismatch has an address")
    print()
    print("| Term | Pool (lsExpr) | Questions | No asker field | OFF | spike | ON | spike |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    for term in TERMS:
        off = results["off"][term].resolved_automatic
        on = results["on"][term].resolved_automatic
        print(
            f"| {term}th LS | {pool_sizes[term]} | {results['off'][term].total_questions:,} "
            f"| {no_asker_counts[term]} | {off:,} | {SPIKE_PER_TERM[(term, 'off')]:,} "
            f"| {on:,} | {SPIKE_PER_TERM[(term, 'on')]:,} |"
        )
    print()
    bad_pools = sum(pool_disagreements.values())
    print(
        f"**Pool-rule control**: {bad_pools} of "
        f"{sum(pool_sizes.values())} pooled member(s) where "
        f"`sansad.ingest.members`' term list differs from the spike's `lsExpr` parse. "
        f"Non-zero would mean the production ingest and the spike disagree about who was "
        f"eligible, independently of any matcher behaviour."
    )
    print()

    print("## Derived question identity, checked over the full window")
    print()
    print(
        "Not a matcher property, but this is the first run over all 95,269 records and the "
        'check costs nothing. `route-capture.md` left it open: *"`quesNo` uniqueness is '
        'observed **within one session only** (250 records, 0 duplicates)"*.'
    )
    print()
    print("| Term | Records | distinct (lokNo, sessionNo, quesNo) | + type | + type + date |")
    print("|---|---:|---:|---:|---:|")
    identity_collisions = 0
    identity_collisions_with_type = 0
    for term, records, base, with_type, with_date in check_question_identity(scratch):
        identity_collisions += records - base
        identity_collisions_with_type += records - with_type
        print(
            f"| {term}th LS | {records:,} | {base:,} "
            f"({records - base:,} collisions) | {with_type:,} "
            f"({records - with_type:,}) | {with_date:,} ({records - with_date:,}) |"
        )
    print()
    print(
        f"**The composite `sansad.ingest.questions` derives is NOT unique: "
        f"{identity_collisions:,} record(s) collide onto an already-used id.** Adding `type` "
        f"leaves {identity_collisions_with_type:,}. Reported, not fixed -- see "
        f"`spike/matcher-equivalence.md`."
    )
    print()

    print("## Per-form disagreements")
    print()
    total_disagreements = sum(len(v) for v in disagreements.values())
    for config, label in (("off", "containment OFF"), ("on", "containment ON")):
        rows = disagreements[config]
        forms_compared = len(results[config][18].outcomes) + len(results[config][17].outcomes)
        print(f"**{label}** -- {len(rows)} disagreement(s) over {forms_compared} distinct forms.")
        if rows:
            print()
            print("| Name form as written | spike | production |")
            print("|---|---|---|")
            for form, spike, produced in rows[:50]:
                print(f"| `{form}` | {spike} | {produced} |")
            if len(rows) > 50:
                print(f"| … | {len(rows) - 50} more | |")
        print()
    print(f"**Total disagreement count: {total_disagreements}.**")
    print()

    print("## Would any assertion have overridden a different automatic match?")
    print()
    print(
        "T048 lets a maintainer assertion win unconditionally -- including over a "
        "*confident* automatic match. Expected: none of the four lands on a form the "
        "matcher already resolved, because all four are residual forms it failed on. "
        "This is the check for that."
    )
    print()
    print("| Assertion form | asserted member | automatic outcome | conflict |")
    print("|---|---|---|---|")
    conflicts = 0
    for form in sorted(assertions):
        assertion = assertions[form]
        automatic = None
        for term in TERMS:
            automatic = results["on"][term].automatic_outcomes.get(form) or automatic
        if automatic is None:
            print(f"| `{form}` | {assertion.member_id} | form not present in the window | n/a |")
            continue
        described = (
            f"{automatic.status.value} via {automatic.tier_reached} "
            f"-> {automatic.member_ids or '()'}"
        )
        conflict = automatic.status is ResolutionStatus.RESOLVED and automatic.member_ids != (
            assertion.member_id,
        )
        conflicts += int(conflict)
        print(
            f"| `{form}` | {assertion.member_id} | {described} | "
            f"{'**DIFFERENT MEMBER**' if conflict else 'none'} |"
        )
    print()
    print(f"**Assertions overriding a different resolved member: {conflicts}.**")
    print()

    print("## Where the assertion figure differs, decomposed")
    print()
    print(
        "The spike's rule, verbatim: *\"counting those whose **every** residual asker is one "
        'of the four confirmed forms"*. That is the rule implemented in '
        "`sansad.resolve.status_for_question`. Below, the questions that rule recovers, "
        "grouped by **how many** of the four block each one -- because a method that scores "
        "one asserted form at a time cannot recover a question that two of them block "
        "together, and that is where a per-form computation and a per-question one part."
    )
    print()
    print("| Questions recovered, by how many of the four block them | Count |")
    print("|---|---:|")
    buckets: dict[int, int] = {}
    asserted_forms = set(assertions)
    for term in TERMS:
        outcomes = results["on"][term].outcomes
        for forms in question_forms[term]:
            if not forms:
                continue
            residual = {f for f in forms if outcomes[f].status is not ResolutionStatus.RESOLVED}
            if residual and residual <= asserted_forms:
                buckets[len(residual)] = buckets.get(len(residual), 0) + 1
    for count in sorted(buckets):
        label = (
            "exactly one asserted form residual"
            if count == 1
            else f"{count} asserted forms residual"
        )
        print(f"| {label} | {buckets[count]:,} |")
    recovered = sum(buckets.values())
    single = buckets.get(1, 0)
    print(f"| **total recovered** | **{recovered:,}** |")
    print()
    spike_recovered = SPIKE_WINDOW["assertions"][0] - SPIKE_WINDOW["on"][0]
    print(f"- spike's published recovered figure: **{spike_recovered:,}**")
    print(f"- recovered by exactly one assertion: **{single:,}** (per-form sets are disjoint here)")
    print(
        f"- recoverable only by two assertions together: **{recovered - single:,}** "
        f"-- invisible to a per-form method"
    )
    print(f"- unaccounted remainder: **{single - spike_recovered:,}**")
    print()

    print("## Verdict")
    print()
    reproduced = all(produced_window[c] == SPIKE_WINDOW[c][:2] for c in ("off", "on", "assertions"))
    if reproduced and total_disagreements == 0 and conflicts == 0 and bad_pools == 0:
        print(
            "**VERIFIED WORKING.** All three window figures reproduce exactly, no form "
            "disagrees, the pool rule agrees, and no assertion overrides a different "
            "resolved member."
        )
        return 0
    print("**MISMATCH.** See the tables above. The matcher is NOT to be changed to close a")
    print("gap found here -- a difference is a finding about the port, and its cause belongs")
    print("in `spike/matcher-equivalence.md` before anything is edited.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
