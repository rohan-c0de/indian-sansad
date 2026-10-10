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
from sansad.ingest.questions import DuplicateRecord, load_question_records
from sansad.model._common import ResolutionStatus
from sansad.resolve import resolve_questions
from sansad.resolve.assertions import load_assertions

#: The figures to reproduce, from `spike/resolution-rate.md` -> FINAL.
#: Expected figures on the **spike's basis** -- all 95,269 records as served,
#: with the one upstream duplicate NOT removed, because that is the denominator
#: `spike/resolution-rate.md` measured against.
#:
#: The first two are the spike's published figures, unchanged, and must
#: reproduce exactly. The third is **corrected**: the spike published
#: 91,708 / 96.26%, which undercounted by 89 questions. 87 of those are
#: co-asked by two of the four asserted forms and resolve only when both
#: assertions are applied -- invisible to a per-form recount. The remaining 2
#: are NOT explained: the code that produced 1,409 was never committed, so the
#: last two questions cannot be traced to a line.
#: See `spike/matcher-equivalence.md`.
SPIKE_WINDOW = {
    "off": (86_352, 95_269, "90.64%"),
    "on": (90_299, 95_269, "94.78%"),
    "assertions": (91_797, 95_269, "96.36%"),
}
#: What the spike published for the assisted configuration, kept so the
#: correction stays visible in the output rather than only in a commit message.
SPIKE_PUBLISHED_ASSISTED = (91_708, 95_269, "96.26%")
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
    dedupe: bool,
):
    pool_records = [r for r in roster if term in ls_expr_terms(r)]
    members = load_members(pool_records, last_refreshed="2026-10-09")

    # Control: does `sansad.ingest.members` agree with the spike's pool rule?
    disagreeing_pool = sum(
        1
        for record, member in zip(pool_records, members, strict=True)
        if {t.number for t in member.terms} != ls_expr_terms(record)
    )

    duplicates: list[DuplicateRecord] = []
    questions = load_question_records(
        read_jsonl(scratch / f"questions_ls{term}.jsonl"),
        last_refreshed="2026-10-09",
        dedupe=dedupe,
        duplicates=duplicates,
    )
    result = resolve_questions(questions, members, assertions=assertions, containment=containment)
    no_asker = sum(1 for q in questions if not q.asker_forms)
    # In record order, NOT keyed by question_id. The derived composite
    # `(lokNo, sessionNo, quesNo)` is NOT unique over the full window -- 7,431
    # records collide onto an already-used id, because `quesNo` is numbered per
    # (session, TYPE) and starred/unstarred are separate series. A dict keyed by
    # it silently drops records and miscounts. See `spike/matcher-equivalence.md`.
    asker_forms = tuple(q.asker_forms for q in questions)
    return result, len(members), disagreeing_pool, no_asker, asker_forms, tuple(duplicates)


#: The one `question_id` the upstream serves twice over the covered window,
#: byte-identical. Declared, not tolerated: `sansad.ingest.questions` reduces it
#: to one and the Coverage Statement carries the gap (FR-013). Any OTHER
#: collision is a failure of the composite identity.
DECLARED_DUPLICATE = "lok-sabha/17/4/unstarred/2204"


def check_question_identity(scratch: Path) -> tuple[list[tuple[int, int, int, int]], list[str]]:
    """Assert the derived `question_id` is unique over the full window.

    `route-capture.md` left this open -- "`quesNo` uniqueness is observed
    **within one session only** (250 records, 0 duplicates) ... the ingest must
    assert it, not trust it" -- and it did not hold: the old
    `(lokNo, sessionNo, quesNo)` composite collided on 7,431 of 95,269 records,
    because `quesNo` is numbered per (session, `type`).

    This now runs on every invocation, so the corrected composite cannot
    regress unnoticed. It is the only check here that is a **pass/fail
    assertion** rather than a comparison against the spike: the spike never
    measured it.

    Returns (per-term rows, unexpected collisions). A row is
    (term, records, distinct old composite, distinct new composite).
    """
    rows: list[tuple[int, int, int, int]] = []
    unexpected: list[str] = []
    for term in TERMS:
        records = read_jsonl(scratch / f"questions_ls{term}.jsonl")
        old_composite = {(r["lokNo"], r["sessionNo"], r["quesNo"]) for r in records}

        # The production mapper with de-duplication OFF, so every record keeps
        # its own entry and a collision is visible rather than already merged.
        mapped = load_question_records(records, last_refreshed="2026-10-09", dedupe=False)
        seen: dict[str, int] = {}
        for record in mapped:
            question_id = record.question.question_id
            seen[question_id] = seen.get(question_id, 0) + 1
        rows.append((term, len(records), len(old_composite), len(seen)))

        for question_id, copies in sorted(seen.items()):
            if copies > 1 and question_id != DECLARED_DUPLICATE:
                unexpected.append(f"{question_id} x{copies}")
    return rows, unexpected


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

    published: dict[str, dict[int, Any]] = {}
    declared_duplicates: list[DuplicateRecord] = []

    for config, containment, applied in (
        ("off", False, None),
        ("on", True, None),
        ("assertions", True, assertions),
    ):
        results[config] = {}
        published[config] = {}
        rows: list[tuple[str, str, str]] = []
        for term in TERMS:
            # Spike basis: every record as served, duplicate included.
            result, pool, pool_bad, no_asker, asker_forms, _ = run_term(
                scratch, term, roster, containment=containment, assertions=applied, dedupe=False
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
            # Published basis: the upstream duplicate reduced to one.
            pub, _, _, _, _, dups = run_term(
                scratch, term, roster, containment=containment, assertions=applied, dedupe=True
            )
            published[config][term] = pub
            if config == "assertions":
                declared_duplicates.extend(dups)
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

    print(
        f"The spike published **{SPIKE_PUBLISHED_ASSISTED[0]:,} / "
        f"{SPIKE_PUBLISHED_ASSISTED[1]:,} = {SPIKE_PUBLISHED_ASSISTED[2]}** for the assisted "
        f"configuration. That **undercounted** -- see the decomposition below. The expected "
        f"value above is the corrected one."
    )
    print()

    print("## The published basis -- one upstream duplicate removed")
    print()
    print(
        "The table above uses the spike's denominator: all 95,269 records as served. The "
        "upstream serves one of them twice (byte-identical), so the number of distinct "
        "questions is one lower, and these are the figures the project publishes. The dropped "
        "copy is declared as a known gap in the Coverage Statement (FR-013), not removed "
        "silently."
    )
    print()
    print("| Configuration | Resolved | Questions | Rate | Margin vs SC-002's 95% |")
    print("|---|---:|---:|---:|---:|")
    for config, label in (
        ("off", "containment OFF"),
        ("on", "containment ON"),
        ("assertions", "containment ON + four assertions"),
    ):
        key = "resolved_assisted" if config == "assertions" else "resolved_automatic"
        resolved = sum(getattr(published[config][t], key) for t in TERMS)
        total = sum(published[config][t].total_questions for t in TERMS)
        rate = 100.0 * resolved / total if total else 0.0
        print(
            f"| {label} | {resolved:,} | {total:,} | **{rate:.2f}%** | {rate - 95.0:+.2f} points |"
        )
    print()
    print(
        f"Declared upstream duplicate(s): "
        f"{', '.join(f'`{d.question_id}` (x{d.copies})' for d in declared_duplicates) or 'none'}"
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

    print("## Derived question identity, asserted over the full window")
    print()
    print(
        '`route-capture.md` left this open: *"`quesNo` uniqueness is observed **within one '
        "session only** (250 records, 0 duplicates) ... the ingest must assert it, not trust "
        'it"*. It did not hold. The composite now includes `type`, and this is the assertion.'
    )
    print()
    print(
        "| Term | Records | distinct old `(lokNo, sessionNo, quesNo)` "
        "| distinct `(House, session, type, quesNo)` |"
    )
    print("|---|---:|---:|---:|")
    identity_rows, unexpected = check_question_identity(scratch)
    old_collisions = 0
    new_collisions = 0
    for term, records, old_distinct, new_distinct in identity_rows:
        old_collisions += records - old_distinct
        new_collisions += records - new_distinct
        print(
            f"| {term}th LS | {records:,} | {old_distinct:,} "
            f"(**{records - old_distinct:,}** collisions) | {new_distinct:,} "
            f"({records - new_distinct:,}) |"
        )
    print()
    print(f"- old composite: **{old_collisions:,}** record(s) collided onto an already-used id")
    print(
        f"- corrected composite: **{new_collisions:,}** collision(s), which must all be the one "
        f"declared upstream duplicate `{DECLARED_DUPLICATE}`"
    )
    if unexpected:
        print()
        print("**UNDECLARED COLLISIONS -- the composite identity is still wrong:**")
        for entry in unexpected:
            print(f"- `{entry}`")
    else:
        print("- undeclared collisions: **0**")
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
    # The figure the spike PUBLISHED, not the corrected expectation -- otherwise this
    # section would compare the correction against itself and report a remainder of 0.
    spike_recovered = SPIKE_PUBLISHED_ASSISTED[0] - SPIKE_WINDOW["on"][0]
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
    if (
        reproduced
        and total_disagreements == 0
        and conflicts == 0
        and bad_pools == 0
        and not unexpected
    ):
        print(
            "**VERIFIED WORKING.** All three window figures reproduce exactly, no form "
            "disagrees, the pool rule agrees, and no assertion overrides a different "
            "resolved member."
        )
        return 0
    if unexpected:
        print(
            f"**IDENTITY FAILURE.** {len(unexpected)} undeclared `question_id` collision(s). "
            f"The composite is still not unique -- fix the composite, not the figures."
        )
        print()
    print("**MISMATCH.** See the tables above. The matcher is NOT to be changed to close a")
    print("gap found here -- a difference is a finding about the port, and its cause belongs")
    print("in `spike/matcher-equivalence.md` before anything is edited.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
