"""T036 -- `quickstart.md` scenario 1: identity resolution across name variants.

> **Expected**: the fixture containing both `Shri Sunil Kumar Singh` and
> `Singh, Sunil K.` yields **one** `member_id` for both. Two members with
> genuinely different identities and similar names remain separate.

Both halves are asserted here, and the second is the one that fails quietly if
it is left out: a matcher can score very well on the first by merging
aggressively, and merging is how two people become one published identity.
`data-model.md` -> Member: "Two members with identical or near-identical names
MUST NOT be merged; distinctness is decided on attributes beyond the name."

`spike/spike-report.md` records that the residual class after the containment
tier is "initials, parenthetical aliases and divergent orderings", and that all
four owner-confirmed assertions are of that kind -- so the forms exercised here
are the shape that actually costs this project hand work, not an invented one.
"""

from __future__ import annotations

import pytest

from sansad.model._common import ResolutionStatus

REQUIRED_PAIR = ("Shri Sunil Kumar Singh", "Singh, Sunil K.")


def test_required_variant_pair_yields_one_member_id(variant_members):
    """Scenario 1's first clause. One identity for both written forms."""
    from sansad.resolve.match import MemberIndex, resolve_form

    index = MemberIndex(variant_members)
    outcomes = {form: resolve_form(form, index) for form in REQUIRED_PAIR}

    for form, outcome in outcomes.items():
        assert outcome.status is ResolutionStatus.RESOLVED, (
            f"{form!r} did not resolve: status={outcome.status.value}, "
            f"tier_reached={outcome.tier_reached}, candidates={outcome.member_ids}"
        )

    resolved_ids = {outcome.member_ids[0] for outcome in outcomes.values()}
    assert resolved_ids == {"fx-0001"}, (
        f"the required pair resolved to {resolved_ids} -- scenario 1 requires ONE member_id"
    )


def test_honorific_reordering_and_initial_forms_all_reach_one_identity(variant_members):
    """The three mechanisms the pair combines, each on its own member.

    `route-capture.md` measured the honorific on **98.1%** of asker instances,
    so it is the dominant normalisation problem and is exercised directly
    rather than only through the required pair.
    """
    from sansad.resolve.match import MemberIndex, resolve_form

    index = MemberIndex(variant_members)
    cases = {
        "Smt. Asha Devi Verma": "fx-0002",  # honorific
        "Verma Asha Devi": "fx-0002",  # token reordering, no comma
        "A. D. Verma": "fx-0002",  # all-initials form
        "Ramesh Chandra Pillai": "fx-0003",
    }
    for form, expected in cases.items():
        outcome = resolve_form(form, index)
        assert outcome.status is ResolutionStatus.RESOLVED, (
            f"{form!r}: status={outcome.status.value} tier={outcome.tier_reached}"
        )
        assert outcome.member_ids == (expected,), f"{form!r} -> {outcome.member_ids}"


def test_containment_tier_resolves_a_form_the_roster_does_not_spell_out(roster_members):
    """The tier adopted by owner decision 2026-10-09, on the roster-only set.

    `Ramesh Pillai` is a strict token subset of the roster's
    `Ramesh Chandra Pillai` -- the mechanism `spike-report.md` measured as 10
    subset forms plus 8 superset forms, "one mechanism, 3,876 instances".
    Asserted against `roster_members` deliberately: with the variant list
    present the form matches exactly and the tier is never reached, which would
    make this test pass while testing nothing.
    """
    from sansad.model.resolution_record import ResolutionMethod
    from sansad.resolve.match import MemberIndex, resolve_form

    index = MemberIndex(roster_members)
    outcome = resolve_form("Ramesh Pillai", index)

    assert outcome.status is ResolutionStatus.RESOLVED
    assert outcome.member_ids == ("fx-0003",)
    assert outcome.method is ResolutionMethod.TOKEN_CONTAINMENT, (
        f"expected the containment tier to do this work, got {outcome.method}"
    )


def test_containment_is_reached_only_after_every_earlier_tier(variant_members):
    """T046: the containment tier "is reached **only** when every earlier tier
    has failed to produce a single member"."""
    from sansad.model.resolution_record import ResolutionMethod
    from sansad.resolve.match import MemberIndex, resolve_form

    index = MemberIndex(variant_members)
    outcome = resolve_form("Ramesh Pillai", index)

    assert outcome.status is ResolutionStatus.RESOLVED
    assert outcome.member_ids == ("fx-0003",)
    assert outcome.method is not ResolutionMethod.TOKEN_CONTAINMENT, (
        "an exact variant match must not be credited to the containment tier"
    )


def test_two_near_identical_members_are_not_merged(roster_members):
    """Scenario 1's second clause, and `data-model.md`'s merge prohibition."""
    ids = [m.member_id for m in roster_members]
    assert len(ids) == len(set(ids)), f"duplicate member_id in the ingested roster: {ids}"

    gupta = [m for m in roster_members if m.canonical_name == "Mohan Lal Gupta"]
    rao = [m for m in roster_members if m.canonical_name == "Kavita Rao"]
    assert {m.member_id for m in gupta} == {"fx-0010", "fx-0011"}
    assert {m.member_id for m in rao} == {"fx-0020", "fx-0021"}


@pytest.mark.parametrize(
    ("form", "expected_candidates"),
    [
        ("Mohan Lal Gupta", ("fx-0010", "fx-0011")),
        ("Kavita Rao", ("fx-0020", "fx-0021")),
    ],
)
def test_a_name_shared_by_two_identities_is_ambiguous_not_collapsed(
    roster_members, form, expected_candidates
):
    """A shared name must not resolve to whichever identity sorts first."""
    from sansad.resolve.match import MemberIndex, resolve_form

    index = MemberIndex(roster_members)
    outcome = resolve_form(form, index)

    assert outcome.status is ResolutionStatus.AMBIGUOUS, (
        f"{form!r} resolved to {outcome.member_ids} -- that is the silent collapse "
        f"to one candidate that Edge Cases forbids"
    )
    assert outcome.member_ids == expected_candidates


def test_distinctness_is_decided_on_attributes_beyond_the_name(roster_members):
    """T047: "distinctness between near-identical names is decided on
    attributes beyond the name"."""
    from sansad.resolve.ambiguity import distinguishing_attributes

    by_id = {m.member_id: m for m in roster_members}

    # Differ on three attributes.
    assert distinguishing_attributes(by_id["fx-0010"], by_id["fx-0011"]) == (
        "constituency",
        "party",
        "state",
    )
    # The harder pair: identical name, party AND state; only constituency differs.
    assert distinguishing_attributes(by_id["fx-0020"], by_id["fx-0021"]) == ("constituency",)


def test_adding_a_name_variant_does_not_change_member_id(roster_members):
    """FR-002: `member_id` "MUST NOT change when a name variant is added"."""
    from sansad.resolve.identity import add_name_variants

    original = next(m for m in roster_members if m.member_id == "fx-0001")
    widened = add_name_variants(original, ["Singh, Sunil K.", "S. K. Singh"])

    assert widened.member_id == original.member_id
    assert set(original.name_variants) <= set(widened.name_variants)
    assert "Singh, Sunil K." in widened.name_variants
