"""T062 — the published aggregates: totals reconcile, nothing is dropped, basis stated.

`spec.md` User Story 4 acceptance scenarios:

1. "**Given** a covered term, **When** a user requests a composition breakdown,
   **Then** the categories sum to the total membership for that term and any
   member with missing attributes is shown under an explicit 'not stated'
   category" — never omitted.
2. "**Given** a subject, **When** a user requests its trend, **Then** a
   per-session series is returned with the counting basis stated."

And FR-012 / SC-007: counts must be reproducible by counting the published
question records, with the counting basis stated **alongside the numbers**.

The reconciliation test is the one with teeth. A breakdown that silently drops
members with a missing attribute still sums to *something* — it sums to a
smaller denominator, and every percentage computed from it is wrong in the
flattering direction. So the test asserts the sum equals the term's total
membership **and** that the total is itself published, because a sum that
reconciles against an unstated total reconciles against nothing.
"""

from __future__ import annotations

import pytest

from sansad.model._common import NOT_STATED


@pytest.fixture
def members():
    """Six members: four complete, one with no party, one with no state.

    The two incomplete ones are the point — they must appear under "not
    stated", not vanish.
    """
    from sansad.ingest.members import load_members

    rows = [
        {
            "memberId": "ls-1",
            "memberName": "One",
            "party": "Party A",
            "state": "State One",
            "constituency": "C1",
            "house": "Lok Sabha",
            "lsExpr": "17,18",
            "sittingStatus": "sitting",
        },
        {
            "memberId": "ls-2",
            "memberName": "Two",
            "party": "Party A",
            "state": "State One",
            "constituency": "C2",
            "house": "Lok Sabha",
            "lsExpr": "18",
            "sittingStatus": "sitting",
        },
        {
            "memberId": "ls-3",
            "memberName": "Three",
            "party": "Party B",
            "state": "State Two",
            "constituency": "C3",
            "house": "Lok Sabha",
            "lsExpr": "16,17,18",
            "sittingStatus": "sitting",
        },
        {
            "memberId": "ls-4",
            "memberName": "Four",
            "party": "Party B",
            "state": "State Two",
            "constituency": "C4",
            "house": "Lok Sabha",
            "lsExpr": "18",
            "sittingStatus": "sitting",
        },
        # no party
        {
            "memberId": "ls-5",
            "memberName": "Five",
            "state": "State Two",
            "constituency": "C5",
            "house": "Lok Sabha",
            "lsExpr": "18",
            "sittingStatus": "sitting",
        },
        # no state
        {
            "memberId": "ls-6",
            "memberName": "Six",
            "party": "Party A",
            "constituency": "C6",
            "house": "Lok Sabha",
            "lsExpr": "18",
            "sittingStatus": "sitting",
        },
    ]
    return load_members(rows, last_refreshed="2026-10-10")


@pytest.fixture
def question_batch(question_records):
    return question_records("co_asked.json")


# ---------------------------------------------------------------------------
# Scenario 1 — the categories sum to the term's total membership
# ---------------------------------------------------------------------------
def test_every_dimension_sums_to_the_terms_total_membership(members):
    from sansad.views.composition import compose

    result = compose(members, term=18)

    assert result.total_members == 6, "all six members served in the 18th"
    for dimension, buckets in result.breakdown.items():
        assert sum(buckets.values()) == result.total_members, (
            f"{dimension} sums to {sum(buckets.values())}, not {result.total_members}"
        )


def test_the_total_is_published_not_merely_implied(members):
    """A sum that reconciles against an unstated total reconciles against nothing."""
    from sansad.views.composition import compose

    rows = compose(members, term=18).as_rows()
    assert rows
    for row in rows:
        assert row["total_members"] == 6
        assert row["term"] == 18


def test_a_member_with_a_missing_attribute_appears_under_not_stated(members):
    from sansad.views.composition import compose

    result = compose(members, term=18)

    assert result.breakdown["party"][NOT_STATED] == 1, "the member with no party vanished"
    assert result.breakdown["state"][NOT_STATED] == 1, "the member with no state vanished"
    # ...and it is a category, not a silently smaller denominator.
    assert sum(result.breakdown["party"].values()) == 6
    assert sum(result.breakdown["state"].values()) == 6


def test_not_stated_is_absent_when_nothing_is_missing(members):
    """The control. A "not stated" bucket that is always present would be noise."""
    from sansad.views.composition import compose

    complete = [m for m in members if m.member_id in {"ls-1", "ls-2", "ls-3", "ls-4"}]
    result = compose(complete, term=18)
    assert NOT_STATED not in result.breakdown["party"]
    assert sum(result.breakdown["party"].values()) == 4


def test_terms_served_is_a_count_not_a_list(members):
    """ "number of terms served" — the third permitted dimension."""
    from sansad.views.composition import compose

    buckets = compose(members, term=18).breakdown["terms_served"]
    assert buckets == {1: 4, 2: 1, 3: 1}
    assert sum(buckets.values()) == 6


def test_a_member_who_did_not_serve_in_the_term_is_excluded(members):
    from sansad.views.composition import compose

    result = compose(members, term=17)
    assert result.total_members == 2, "only ls-1 and ls-3 served in the 17th"


# ---------------------------------------------------------------------------
# Scenario 2 — a per-session series, with its basis
# ---------------------------------------------------------------------------
def test_a_subject_trend_is_a_per_session_series(members, question_batch):
    from sansad.resolve import resolve_questions
    from sansad.views.subject_trends import subject_trends

    resolved = resolve_questions(question_batch, members)
    trends = subject_trends(resolved.questions)

    assert trends.series, "no series produced"
    for entry in trends.as_rows():
        assert entry["subject"]
        assert entry["session"]
        assert entry["questions"] >= 1


def test_a_subject_series_is_reproducible_by_counting_the_records(members, question_batch):
    """FR-012 / SC-007: countable by hand from the published records.

    Counted here independently of the aggregation code — a second
    implementation, not a call into the first.
    """
    from collections import Counter

    from sansad.resolve import resolve_questions
    from sansad.views.subject_trends import subject_trends

    resolved = resolve_questions(question_batch, members)
    independent = Counter((q.subject, q.session) for q in resolved.questions)

    published = {
        (r["subject"], r["session"]): r["questions"]
        for r in subject_trends(resolved.questions).as_rows()
    }
    assert published == dict(independent)


# ---------------------------------------------------------------------------
# Every aggregate carries a counting basis
# ---------------------------------------------------------------------------
def test_every_aggregate_row_carries_a_resolvable_counting_basis(tmp_path, members, question_batch):
    """FR-012: the basis is stated alongside the numbers.

    Carried as a **reference** rather than inline, and the reference must
    resolve. Measured reason: inlining the prose on all 92,942 subject-trend
    rows cost **179 MiB of the 195 MiB** the aggregates added -- 91% of them, to
    repeat one sentence 92,942 times, taking the dataset from 225 MiB to
    420 MiB and from 22% to 41% of the 1 GiB ceiling. The prose is published
    once per unit, in the same directory as the numbers.

    This is a stronger assertion than the inline version it replaces: it checks
    the reference actually resolves, which an inline copy could not get wrong
    but a dangling reference would get wrong silently.
    """
    from sansad.publish.aggregates import (
        AGGREGATES_DIR_NAME,
        COUNTING_BASIS_STEM,
        write_aggregates,
    )
    from sansad.publish.formats import read_ndjson
    from sansad.resolve import resolve_questions
    from sansad.views.composition import compose
    from sansad.views.subject_trends import subject_trends

    resolved = resolve_questions(question_batch, members)
    write_aggregates(
        tmp_path,
        compositions=[compose(members, term=18)],
        trends=subject_trends(resolved.questions),
    )
    root = tmp_path / AGGREGATES_DIR_NAME
    basis = {
        (r["unit"], r["basis_version"]): r["counting_basis"]
        for r in read_ndjson(root / f"{COUNTING_BASIS_STEM}.jsonl")
    }
    assert basis, "no basis was published at all"

    for stem in ("composition", "subject-trends"):
        rows = read_ndjson(root / f"{stem}.jsonl")
        assert rows
        for row in rows:
            key = (row["counting_basis_unit"], row["basis_version"])
            assert key in basis, f"{stem}: basis reference {key} does not resolve"
            assert len(basis[key]) > 80, "a basis must be readable prose, not a label"


def test_the_basis_states_the_three_things_a_visitor_needs(question_batch, members):
    """T064: what is counted, that a co-asked question counts ONCE, and how
    unresolved and partly resolved questions are treated."""
    from sansad.views.basis import question_basis

    basis = question_basis()
    lowered = basis.lower()
    assert "question" in lowered
    assert "once" in lowered and "asker" in lowered, "the co-asking rule must be stated"
    assert "unresolved" in lowered, "the unresolved treatment must be stated"
    assert "partly" in lowered or "partially" in lowered, "partly-resolved must be stated"


def test_the_published_aggregate_files_exist_in_both_formats(tmp_path, members, question_batch):
    from sansad.publish.aggregates import AGGREGATES_DIR_NAME, write_aggregates
    from sansad.resolve import resolve_questions
    from sansad.views.composition import compose
    from sansad.views.subject_trends import subject_trends

    resolved = resolve_questions(question_batch, members)
    result = write_aggregates(
        tmp_path,
        compositions=[compose(members, term=18)],
        trends=subject_trends(resolved.questions),
    )

    root = tmp_path / AGGREGATES_DIR_NAME
    for stem in ("composition", "subject-trends"):
        assert (root / f"{stem}.jsonl").is_file()
        assert (root / f"{stem}.csv").is_file()
    assert result.files
    # both formats carry the same records
    from sansad.publish.formats import read_csv, read_ndjson, text_projection

    for stem in ("composition", "subject-trends"):
        nd = [text_projection(r) for r in read_ndjson(root / f"{stem}.jsonl")]
        assert nd == list(read_csv(root / f"{stem}.csv"))


def test_the_aggregates_are_named_in_the_coverage_statement(tmp_path):
    from sansad.model._common import House
    from sansad.publish.coverage import CoverageInputs, write_coverage_statements
    from sansad.publish.formats import read_ndjson

    write_coverage_statements(
        tmp_path,
        [
            CoverageInputs(
                house=House.LOK_SABHA,
                period_start="2019-06-21",
                period_end="2026-08-12",
                sessions_covered=("lok-sabha/18/2",),
                last_refreshed="2026-10-10",
                total_questions=10,
                resolved_automatic=9,
                resolved_assisted=10,
                published_sets=(
                    "by-session",
                    "by-ministry",
                    "by-member",
                    "reference",
                    "aggregates",
                    "coverage",
                    "resolution-records",
                ),
            )
        ],
    )
    row = read_ndjson(tmp_path / "coverage.jsonl")[0]
    assert "aggregates" in row["published_sets"]
