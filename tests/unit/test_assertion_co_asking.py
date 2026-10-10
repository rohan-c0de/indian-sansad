"""A question co-asked by two forms that each need an assertion.

This is the mechanism behind the **87-question** correction recorded in
`spike/matcher-equivalence.md`, and the reason the spike's published figure of
1,409 recovered questions undercounted.

A question resolves only when **all** its askers do (FR-003). So a question
co-asked by two residual forms is unblocked by **neither assertion alone** --
only by both together. A recount that scores one asserted form at a time
cannot see such a question: under each form taken separately the question is
still blocked by the other, so it is credited to neither. The spike's own text
warns about exactly this ("blocked counts overlap and cannot be summed") and
its 1,409 figure is nonetheless 2 below the per-form-reachable count of 1,411
and 89 below the per-question count of 1,498. Those 2 are **not explained**:
the code that produced 1,409 was never committed, so they cannot be traced to
a line.

This test is the smallest case that distinguishes the two counting methods, so
the correction rests on a reproducible mechanism rather than on a diff between
two large numbers.

**The fixture carries both cases, and the second is the control.** `q402` is
co-asked by one residual form and one the matcher resolves unaided, so **one**
assertion unblocks it -- the 1,411-question case. If only `q401` were present,
a resolver that applied assertions in some wrong way could pass by accident.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sansad.ingest.members import load_members
from sansad.ingest.questions import load_question_records
from sansad.model._common import ResolutionStatus
from sansad.model.resolution_record import AssertedBy, ResolutionMethod
from sansad.resolve import resolve_questions
from sansad.resolve.assertions import Assertion

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "co_asked_assertions.json"

VENKAT = "R.K. Venkat"
MUTHUSAMY = "Muthusamy T"


@pytest.fixture(scope="module")
def fixture_body() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture
def members(fixture_body):
    return load_members(fixture_body["members"], last_refreshed="2026-10-09")


@pytest.fixture
def records(fixture_body):
    return load_question_records(fixture_body["listOfQuestions"], last_refreshed="2026-10-09")


@pytest.fixture
def all_assertions(fixture_body) -> dict[str, Assertion]:
    return {
        row["name_as_written"]: Assertion(
            name_as_written=row["name_as_written"],
            member_id=row["member_id"],
            basis=row["basis"],
        )
        for row in fixture_body["assertions"]
    }


def _by_suffix(result, suffix: str):
    return next(q for q in result.questions if q.question_id.endswith(suffix))


def test_both_asker_forms_are_unresolved_without_any_assertion(members, records):
    """The premise. If either form resolved unaided, the test below would be
    measuring nothing."""
    result = resolve_questions(records, members)

    assert result.outcomes[VENKAT].status is ResolutionStatus.UNRESOLVED
    assert result.outcomes[MUTHUSAMY].status is ResolutionStatus.UNRESOLVED
    assert result.outcomes["Priya Anand"].status is ResolutionStatus.RESOLVED


@pytest.mark.parametrize(
    ("loaded", "expected_401"),
    [
        ((), ResolutionStatus.UNRESOLVED),
        ((VENKAT,), ResolutionStatus.UNRESOLVED),
        ((MUTHUSAMY,), ResolutionStatus.UNRESOLVED),
        ((VENKAT, MUTHUSAMY), ResolutionStatus.RESOLVED),
    ],
    ids=["neither", "venkat-only", "muthusamy-only", "both"],
)
def test_the_co_asked_question_resolves_only_when_both_assertions_are_loaded(
    members, records, all_assertions, loaded, expected_401
):
    """The whole point, in one parametrised case per subset of the two assertions."""
    subset = {form: all_assertions[form] for form in loaded}
    result = resolve_questions(records, members, assertions=subset)

    q401 = _by_suffix(result, "/401")
    assert q401.resolution_status is expected_401, (
        f"with assertions {sorted(loaded)} loaded, q401 came out "
        f"{q401.resolution_status.value}, expected {expected_401.value}"
    )
    if expected_401 is ResolutionStatus.RESOLVED:
        assert q401.asking_members == ("fx-0040", "fx-0041")
    else:
        # Whichever asker did resolve is retained; the question is not resolved.
        assert q401.asking_members != ("fx-0040", "fx-0041")


def test_one_assertion_is_enough_for_a_question_whose_other_asker_resolves(
    members, records, all_assertions
):
    """The control -- the 1,411-question case, which a per-form method DOES see."""
    result = resolve_questions(records, members, assertions={VENKAT: all_assertions[VENKAT]})

    q402 = _by_suffix(result, "/402")
    assert q402.resolution_status is ResolutionStatus.RESOLVED
    assert q402.asking_members == ("fx-0040", "fx-0042")

    # ...and the co-asked one is still blocked by the assertion that is absent.
    assert _by_suffix(result, "/401").resolution_status is ResolutionStatus.UNRESOLVED


def test_a_per_form_recount_undercounts_by_exactly_the_co_asked_question(
    members, records, all_assertions
):
    """The arithmetic of the undercount, on two questions instead of 95,269.

    Per-question counting recovers **2**. Summing per-form "questions this form
    alone unblocks" recovers **1**. The missing one is `q401` -- the case where
    two assertions are jointly necessary and individually insufficient. Scale
    that mechanism to the window and it is the 87 questions by which the
    published 96.26% undercounted.
    """
    automatic = resolve_questions(records, members)
    assisted = resolve_questions(records, members, assertions=all_assertions)

    per_question_gain = assisted.resolved_assisted - automatic.resolved_automatic
    assert per_question_gain == 2

    per_form_gain = 0
    for form in (VENKAT, MUTHUSAMY):
        alone = resolve_questions(records, members, assertions={form: all_assertions[form]})
        per_form_gain += alone.resolved_assisted - automatic.resolved_automatic
    assert per_form_gain == 1, (
        "the per-form method should miss the jointly-blocked question; if it does not, "
        "this fixture no longer reproduces the mechanism"
    )
    assert per_question_gain - per_form_gain == 1


def test_the_two_assertions_are_recorded_as_maintainer_joins(members, records, all_assertions):
    """T053 publishes the automatic rate separately, so both joins must be
    labelled as human judgement rather than matcher output."""
    result = resolve_questions(records, members, assertions=all_assertions)

    for form in (VENKAT, MUTHUSAMY):
        record = next(r for r in result.records if r.name_as_written == form)
        assert record.method is ResolutionMethod.MANUAL_ASSERTION
        assert record.asserted_by is AssertedBy.MAINTAINER
        assert record.status is ResolutionStatus.RESOLVED

    # The automatic rate must NOT absorb them.
    assert result.resolved_automatic == 0
    assert result.resolved_assisted == 2
