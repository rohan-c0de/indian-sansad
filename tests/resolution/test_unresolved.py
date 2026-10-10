"""T037 -- `quickstart.md` scenario 2: nothing is silently dropped.

> **Expected**: a deliberately unresolvable asking name produces a published
> question with `resolution_status` of `unresolved` or `ambiguous`. The question
> count before and after resolution is **identical**. An ambiguous match lists
> its candidates rather than picking one.
>
> **Fails if**: any question disappears, or an ambiguous name is assigned a
> single member without a maintainer assertion.

The count assertion is the one with teeth. A resolver that drops what it cannot
match reports a higher resolution rate on a smaller denominator, and the
published record would look better for having lost records. `contracts/
published-dataset.md` guarantee 2 is the consumer-facing form of the same rule:
"A consumer filtering on `resolution_status == "resolved"` is making an
explicit choice, not receiving a default."
"""

from __future__ import annotations

from sansad.model._common import ResolutionStatus


def test_an_unresolvable_asker_is_retained_and_marked(roster_members, question_records):
    from sansad.resolve import resolve_questions

    records = question_records("unresolvable.json")
    result = resolve_questions(records, roster_members)

    by_id = {q.question_id: q for q in result.questions}
    q201 = next(q for qid, q in by_id.items() if qid.endswith("/201"))

    assert q201.resolution_status is ResolutionStatus.UNRESOLVED
    assert q201.asking_members == (), (
        f"an unresolvable asker was assigned {q201.asking_members} -- FR-004 forbids "
        f"a guessed member"
    )


def test_question_count_is_identical_before_and_after_resolution(roster_members, question_records):
    """Scenario 2's count clause, over every question fixture there is."""
    from sansad.resolve import resolve_questions

    for fixture in ("unresolvable.json", "co_asked.json", "ambiguous.json"):
        records = question_records(fixture)
        result = resolve_questions(records, roster_members)
        assert len(result.questions) == len(records), (
            f"{fixture}: {len(records)} question(s) in, {len(result.questions)} out"
        )
        assert {q.question_id for q in result.questions} == {
            r.question.question_id for r in records
        }, f"{fixture}: the set of question_ids changed during resolution"


def test_a_partly_resolved_question_is_not_counted_as_resolved(variant_members, question_records):
    """FR-003's non-additivity, which the spike had to re-walk 95,269 records to measure.

    `unresolvable.json` q202 is co-asked by one resolvable and one unresolvable
    form. "A question resolves only when *all* its askers do" -- the reason the
    four confirmed assertions recovered **1,498** questions rather than a sum
    of per-form figures -- 1,411 unblocked by one assertion and 87 by two
    together (`spike/matcher-equivalence.md`; the spike published 1,409, which
    undercounted).
    """
    from sansad.resolve import resolve_questions

    records = question_records("unresolvable.json")
    result = resolve_questions(records, variant_members)

    q202 = next(q for q in result.questions if q.question_id.endswith("/202"))

    assert q202.resolution_status is not ResolutionStatus.RESOLVED
    assert q202.counts_as_resolved is False
    # The asker that DID resolve is still visible -- retained, not discarded,
    # because dropping it would lose a true join to punish an unrelated one.
    assert q202.asking_members == ("fx-0001",)


def test_an_ambiguous_form_lists_its_candidates(roster_members, question_records):
    """Scenario 2's third clause and `data-model.md`'s collapse prohibition."""
    from sansad.resolve import resolve_questions

    records = question_records("ambiguous.json")
    result = resolve_questions(records, roster_members)

    q301 = next(q for q in result.questions if q.question_id.endswith("/301"))
    assert q301.resolution_status is ResolutionStatus.AMBIGUOUS
    assert q301.asking_members == (), "an ambiguous question must not publish a chosen asker"

    record = next(r for r in result.records if r.name_as_written == "Kavita Rao")
    assert record.status is ResolutionStatus.AMBIGUOUS
    assert record.member_id is None
    assert record.candidates == ("fx-0020", "fx-0021")


def test_the_automatic_and_assisted_counts_are_reported_separately(
    roster_members, question_records
):
    """T053 publishes two rates, so resolution has to count two.

    The owner's decision of 2026-10-09 left the automatic rate at 94.78% --
    below SC-002 -- with the published rate carried to 96.36% by four
    assertions. A single blended figure would hide a matcher regression behind
    accumulated hand corrections.
    """
    from sansad.resolve import resolve_questions

    records = question_records("unresolvable.json")
    result = resolve_questions(records, roster_members)

    assert result.total_questions == len(records)
    assert result.resolved_automatic <= result.resolved_assisted <= result.total_questions


def test_a_maintainer_assertion_is_never_overwritten_by_automatic_matching(
    roster_members, question_records
):
    """T048 / `data-model.md` -> Resolution Record.

    The form asserted here is the one `ambiguous.json` records as impossible to
    settle automatically: `fx-0020` and `fx-0021` share name, party and state,
    so nothing in a question record can break the tie. An assertion is the only
    thing that can, and the automatic matcher must not undo it on the next
    refresh.
    """
    from sansad.model.resolution_record import AssertedBy, ResolutionMethod
    from sansad.resolve import resolve_questions
    from sansad.resolve.assertions import Assertion

    assertion = Assertion(
        name_as_written="Kavita Rao",
        member_id="fx-0020",
        basis="test fixture: the maintainer settled a tie the record cannot",
    )
    records = question_records("ambiguous.json")
    result = resolve_questions(
        records, roster_members, assertions={assertion.name_as_written: assertion}
    )

    q301 = next(q for q in result.questions if q.question_id.endswith("/301"))
    assert q301.resolution_status is ResolutionStatus.RESOLVED
    assert q301.asking_members == ("fx-0020",)

    record = next(r for r in result.records if r.name_as_written == "Kavita Rao")
    assert record.method is ResolutionMethod.MANUAL_ASSERTION
    assert record.asserted_by is AssertedBy.MAINTAINER
    assert record.member_id == "fx-0020"


def test_the_four_owner_confirmed_assertions_are_seeded_and_only_those(fixtures_dir):
    """T048: "**Seed only pairs the owner has confirmed**".

    `spike/spike-report.md` lists five proposed pairs, of which row 4
    (`Poonam (Mahajan) Vajendla Rao`) was **dropped by the owner** and "stays
    among the residual forms, now **21**". A fifth seeded pair would be this
    project asserting an identity its owner declined to confirm.
    """
    from sansad.resolve.assertions import DROPPED_BY_OWNER, load_assertions

    seeded = load_assertions()

    assert len(seeded) == 4, f"expected the four confirmed pairs, got {sorted(seeded)}"
    assert set(seeded) == {
        "Sunil Dattatray Tatkare",
        "Ganesan Selvam",
        "D.K. Suresh",
        "V. Kalanidhi",
    }
    for form in DROPPED_BY_OWNER:
        assert form not in seeded, f"{form!r} was dropped by the owner and must not be seeded"
    for form, assertion in seeded.items():
        assert assertion.member_id, form
        assert assertion.basis, f"{form!r}: an assertion with no recorded basis is not one"
