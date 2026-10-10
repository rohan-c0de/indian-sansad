"""T039 -- the nine guarantees in `contracts/published-dataset.md`.

One test per guarantee, named for its number, so a failure says which promise
to a consumer is broken rather than that "the contract test failed".

**Guarantees 5, 6 and 7's published-set clause are expected to FAIL until the
publish tasks exist** (T051 partitions, T052 reference sets, T053 coverage).
They are written now, against the modules that will provide them, and they fail
by `ModuleNotFoundError` -- deliberately not skipped. A skipped contract test
reads as a pass in a summary line, and the whole point of writing these before
the implementation is that the gap stays visible.
"""

from __future__ import annotations

import pytest

from sansad.model._common import ResolutionStatus
from sansad.model.member import PUBLISHED_FIELDS as MEMBER_PUBLISHED_FIELDS
from sansad.model.question import PUBLISHED_FIELDS as QUESTION_PUBLISHED_FIELDS


# ---------------------------------------------------------------------------
# 1. Identity stability
# ---------------------------------------------------------------------------
def test_guarantee_1_member_id_is_stable_never_reused_and_not_name_derived(roster_members):
    """ "A `member_id` refers to the same person permanently. It is never reused
    and never changes because a name variant was added (FR-002)."""
    from sansad.resolve.identity import IdentityRegistry, add_name_variants

    registry = IdentityRegistry()
    first = registry.member_id_for("5199")
    again = registry.member_id_for("5199")
    assert first == again, "the same upstream record was given two identities"

    other = registry.member_id_for("4963")
    assert other != first

    with pytest.raises(ValueError):
        registry.claim(first, source_record_id="9999")

    member = next(m for m in roster_members if m.member_id == "fx-0001")
    assert add_name_variants(member, ["Singh, Sunil K."]).member_id == member.member_id

    # Not derived from a name: two members sharing a name have different ids.
    gupta = [m.member_id for m in roster_members if m.canonical_name == "Mohan Lal Gupta"]
    assert len(set(gupta)) == 2


# ---------------------------------------------------------------------------
# 2. Nothing is silently dropped
# ---------------------------------------------------------------------------
def test_guarantee_2_an_unresolved_question_is_still_published_with_its_status(
    roster_members, question_records
):
    """ "A consumer filtering on `resolution_status == "resolved"` is making an
    explicit choice, not receiving a default."""
    from sansad.publish.formats import rows_for
    from sansad.resolve import resolve_questions

    records = question_records("unresolvable.json")
    result = resolve_questions(records, roster_members)
    rows = rows_for(result.questions)

    assert len(rows) == len(records)
    statuses = {row["resolution_status"] for row in rows}
    assert ResolutionStatus.UNRESOLVED.value in statuses
    assert all(row["resolution_status"] for row in rows), (
        "a published question with an empty resolution_status gives a consumer no "
        "way to make the explicit choice guarantee 2 promises"
    )


# ---------------------------------------------------------------------------
# 3. Every join is independently verifiable
# ---------------------------------------------------------------------------
def test_guarantee_3_every_join_has_a_resolution_record_with_form_and_source_ref(
    variant_members, question_records
):
    """ "For any question-to-member join, the matching resolution record gives
    the name form as written and the source record reference (FR-005)."""
    from sansad.resolve import resolve_questions

    records = question_records("co_asked.json")
    result = resolve_questions(records, variant_members)

    joined_ids = {mid for q in result.questions for mid in q.asking_members}
    assert joined_ids, "no joins to verify -- the fixture or the resolver is wrong"

    recorded_ids = {r.member_id for r in result.records if r.member_id}
    assert joined_ids <= recorded_ids, (
        f"published join(s) with no resolution record: {sorted(joined_ids - recorded_ids)}"
    )
    for record in result.records:
        assert record.name_as_written
        assert record.source_record_ref


# ---------------------------------------------------------------------------
# 4. Co-asked questions are not duplicated
# ---------------------------------------------------------------------------
def test_guarantee_4_one_question_record_carries_all_its_askers(variant_members, question_records):
    from sansad.resolve import resolve_questions

    records = question_records("co_asked.json")
    result = resolve_questions(records, variant_members)

    ids = [q.question_id for q in result.questions]
    assert len(ids) == len(set(ids))
    assert any(len(q.asking_members) > 1 for q in result.questions)


# ---------------------------------------------------------------------------
# 5. Coverage is declared, not implied  -- PENDING T053
# ---------------------------------------------------------------------------
def test_guarantee_5_coverage_statement_is_published_per_house():
    """ "The coverage statement names the period, the sessions included, known
    gaps, the current resolution rate, and whether the data is current or
    last-known-good."""
    from sansad.publish import coverage  # PENDING T053

    assert hasattr(coverage, "write_coverage_statements")


# ---------------------------------------------------------------------------
# 6. Subsets are addressable, and partitions de-duplicate  -- PENDING T051/T052
# ---------------------------------------------------------------------------
def test_guarantee_6_a_question_id_in_several_partitions_is_one_question():
    """ "a `question_id` appearing in several files is **one** question: a
    consumer combining partitions must de-duplicate on `question_id` rather
    than sum across them."""
    from sansad.publish import partitions  # PENDING T051

    assert hasattr(partitions, "write_partitions")


# ---------------------------------------------------------------------------
# 7. Freshness is stated
# ---------------------------------------------------------------------------
def test_guarantee_7_every_entity_carries_the_date_it_was_last_rebuilt(
    roster_members, question_records
):
    """The entity half of "Every published set carries the date it was last
    rebuilt (FR-016)". The per-set half is asserted below, and needs T051."""
    from sansad.model._common import NOT_STATED
    from sansad.resolve import resolve_questions
    from tests.conftest import FIXTURE_REFRESHED_ON

    assert all(m.last_refreshed == FIXTURE_REFRESHED_ON for m in roster_members)

    records = question_records("co_asked.json")
    result = resolve_questions(records, roster_members)
    assert all(q.last_refreshed == FIXTURE_REFRESHED_ON for q in result.questions)
    # NOT_STATED is truthy, so a bare `assert row["last_refreshed"]` would pass
    # on a record carrying no date at all. Guarantee 7 is about a date.
    assert FIXTURE_REFRESHED_ON != NOT_STATED


def test_guarantee_7_every_published_set_carries_its_rebuild_date():
    from sansad.publish import partitions  # PENDING T051

    assert hasattr(partitions, "PARTITION_MANIFEST_NAME")


# ---------------------------------------------------------------------------
# 8. Field scope is bounded
# ---------------------------------------------------------------------------
def test_guarantee_8_published_rows_carry_no_field_outside_the_published_list(
    roster_members, question_records
):
    """ "No member attribute outside the published list appears, absent a
    recorded decision authorising it (FR-008, SC-010)."""
    from sansad.publish.formats import rows_for
    from sansad.resolve import resolve_questions

    member_rows = rows_for(roster_members)
    for row in member_rows:
        assert tuple(row) == MEMBER_PUBLISHED_FIELDS, (
            f"published member row carries {sorted(set(row) - set(MEMBER_PUBLISHED_FIELDS))} "
            f"outside data-model.md's list"
        )

    result = resolve_questions(question_records("co_asked.json"), roster_members)
    for row in rows_for(result.questions):
        extra = set(row) - set(QUESTION_PUBLISHED_FIELDS)
        assert not extra, f"published question row carries {sorted(extra)}"


# ---------------------------------------------------------------------------
# 9. No document-derived content
# ---------------------------------------------------------------------------
def test_guarantee_9_nothing_in_the_dataset_comes_from_a_document_file(
    roster_members, question_records
):
    """ "Nothing in the dataset is extracted from a PDF or any other document
    file (FR-015). Consumers wanting debate or answer text will not find it
    here."

    Asserted structurally: the published Question row has no field that could
    hold answer or question text, and nothing in it resembles a document path.
    Principle III's rule is that the four `*FilePath` / `*DocPath` fields are
    never followed; a row with no place to put the result is the strongest form
    of that.
    """
    from sansad.publish.formats import rows_for
    from sansad.resolve import resolve_questions

    result = resolve_questions(question_records("co_asked.json"), roster_members)
    rows = rows_for(result.questions)
    assert rows

    forbidden_substrings = ("text", "filepath", "docpath", "pdf", "document")
    for row in rows:
        for key in row:
            flat = key.replace("_", "").lower()
            assert not any(s in flat for s in forbidden_substrings), key


# ---------------------------------------------------------------------------
# Both formats, neither authoritative
# ---------------------------------------------------------------------------
def test_both_formats_carry_the_same_records(tmp_path, roster_members):
    """ "Each set is published in both newline-delimited JSON and CSV. The two
    are the same records; neither is authoritative over the other."

    Equality is asserted on the text projection of each row rather than on raw
    values, because CSV has no types. The projection is the writers' own, so
    this is a check that the two writers agree -- not a reimplementation of one
    of them inside the test.
    """
    from sansad.publish.formats import (
        read_csv,
        read_ndjson,
        rows_for,
        text_projection,
        write_both,
    )

    rows = rows_for(roster_members)
    ndjson_path, csv_path = write_both(tmp_path, "members", rows)

    assert ndjson_path.suffix == ".jsonl"
    assert csv_path.suffix == ".csv"

    from_ndjson = [text_projection(r) for r in read_ndjson(ndjson_path)]
    from_csv = list(read_csv(csv_path))

    assert from_ndjson == from_csv, "the two published formats disagree"
    assert len(from_csv) == len(roster_members)
