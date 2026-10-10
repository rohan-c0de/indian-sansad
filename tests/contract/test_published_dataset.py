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
def test_guarantee_5_coverage_statement_is_published_per_house(tmp_path):
    """ "The coverage statement names the period, the sessions included, known
    gaps, the current resolution rate, and whether the data is current or
    last-known-good."

    And one per House, **including a House with no route**: an omitted statement
    reads as "not looked at", where `data-model.md` requires the opposite.
    """
    from sansad.model._common import House
    from sansad.publish.coverage import (
        CoverageInputs,
        write_coverage_statements,
    )
    from sansad.publish.formats import read_ndjson

    lok_sabha = CoverageInputs(
        house=House.LOK_SABHA,
        period_start="2019-06-21",
        period_end="2026-08-12",
        sessions_covered=("lok-sabha/17/1", "lok-sabha/18/2"),
        last_refreshed="2026-10-09",
        total_questions=95_268,
        resolved_automatic=90_298,
        resolved_assisted=91_796,
        assertions_in_effect=4,
        assertions_overriding_an_automatic_match=0,
        duplicate_records_declared=("lok-sabha/17/4/unstarred/2204",),
        ministry_ids=56,
        ministry_names_observed=64,
        ministry_names_without_confirmed_mapping=56,
        ministry_name_groups_merged_by_normalisation=(("COMMUNICATION", "COMMUNICATIONS"),),
        ministry_names_in_reference_set_with_no_questions=4,
    )
    rajya_sabha = CoverageInputs(
        house=House.RAJYA_SABHA,
        period_start="not stated",
        period_end="not stated",
        sessions_covered=(),
        last_refreshed="2026-10-09",
        total_questions=0,
        resolved_automatic=0,
        resolved_assisted=0,
        unobtainable_reason="No Rajya Sabha route has been identified.",
    )
    write_coverage_statements(tmp_path, [lok_sabha, rajya_sabha])
    rows = {r["house"]: r for r in read_ndjson(tmp_path / "coverage.jsonl")}

    assert set(rows) == {"lok-sabha", "rajya-sabha"}, (
        "a House with no route still needs a statement"
    )

    ls = rows["lok-sabha"]
    # BOTH rates, each with its denominator -- "MUST be published, not merely
    # computed, so SC-002 is externally checkable".
    assert ls["total_questions"] == 95_268
    assert ls["resolved_automatic"] == 90_298
    assert ls["resolved_including_assertions"] == 91_796
    assert round(ls["resolution_rate_automatic"], 4) == 0.9478
    assert round(ls["resolution_rate_including_assertions"], 4) == 0.9636
    # ...and the two verdicts differ, which is the whole reason for two rates.
    assert ls["sc_002_met_on_automatic_rate"] is False
    assert ls["sc_002_met_on_published_rate"] is True

    assert ls["assertions_in_effect"] == 4
    assert ls["assertions_overriding_an_automatic_match"] == 0
    assert ls["duplicate_records_declared"] == ["lok-sabha/17/4/unstarred/2204"]
    assert ls["ministry_ids"] == 56
    assert ls["ministry_names_in_reference_set_with_no_questions"] == 4
    assert ls["last_known_good"] == "current"

    gaps = " ".join(ls["known_gaps"])
    for anomaly in ("lok-sabha/18/1", "lok-sabha/18/8", "lok-sabha/17/13"):
        assert anomaly in gaps, f"{anomaly} is not declared"
    assert "lok-sabha/17/4/unstarred/2204" in gaps

    rs = rows["rajya-sabha"]
    assert rs["unobtainable_reason"]
    # A House with no route must not claim knowledge of another House's gaps.
    assert not [g for g in rs["known_gaps"] if "lok-sabha" in g]


# ---------------------------------------------------------------------------
# 6. Subsets are addressable, and partitions de-duplicate  -- PENDING T051/T052
# ---------------------------------------------------------------------------
def test_guarantee_6_identity_distinguishes_starred_from_unstarred(question_records):
    """The precondition for guarantee 6's de-duplication instruction.

    Guarantee 6 tells a consumer to de-duplicate on `question_id` rather than
    sum across partitions. That instruction is only safe if a `question_id`
    identifies exactly one question. **Until 2026-10-09 it did not**: the
    composite omitted `type`, `quesNo` is numbered per (session, type), and
    7,431 of 95,269 real records collided onto an already-used id -- so a
    consumer following the instruction merged a starred question with an
    unstarred one.

    The fixture is the minimum case: one `STARRED` and one `UNSTARRED` question
    in the same session carrying the same `quesNo`.
    """
    records = question_records("shared_ques_no.json")
    ids = [r.question.question_id for r in records]

    assert len(ids) == len(set(ids)), f"colliding question_id(s): {ids}"
    assert "lok-sabha/18/5/starred/55" in ids
    assert "lok-sabha/18/5/unstarred/55" in ids

    starred = next(r for r in records if r.question.type == "STARRED")
    unstarred = next(
        r
        for r in records
        if r.question.type == "UNSTARRED" and r.question.question_id.endswith("/55")
    )
    assert starred.question.question_id != unstarred.question.question_id
    assert starred.question.session == unstarred.question.session
    # ...and the two are genuinely different questions, not one record twice.
    assert starred.question.subject != unstarred.question.subject


def test_guarantee_6_invisible_type_padding_does_not_create_a_second_id(question_records):
    """The 17th Lok Sabha serves `'UNSTARRED '`; the 18th serves `'UNSTARRED'`.

    Two ids differing by trailing whitespace would be two ids for one question
    -- the same defect as the collision, entering from the opposite direction.
    """
    records = question_records("shared_ques_no.json")
    padded = next(r for r in records if r.question.question_id.endswith("/56"))

    assert padded.question.question_id == "lok-sabha/18/5/unstarred/56"
    assert padded.question.type == "UNSTARRED"


def test_guarantee_6_an_upstream_duplicate_is_reduced_to_one_and_declared(fixtures_dir):
    """One question out of two byte-identical records, and the drop is declared.

    FR-013: a gap must be "reflected in the Coverage Statement rather than
    passing silently". A duplicate dropped and not declared is a silent edit to
    the record count, and the published total would stop matching the
    upstream's own `totalRecordSize` with no explanation on the page.
    """
    import json

    from sansad.ingest.questions import (
        KNOWN_GAP_DUPLICATE_RECORDS,
        DuplicateRecord,
        load_question_records,
    )

    body = json.loads((fixtures_dir / "shared_ques_no.json").read_text(encoding="utf-8"))
    duplicates: list[DuplicateRecord] = []
    records = load_question_records(
        body["listOfQuestions"], last_refreshed="2026-10-09", duplicates=duplicates
    )

    assert len(body["listOfQuestions"]) == 5
    assert len(records) == 4, "the duplicate record was not reduced to one"

    assert len(duplicates) == 1
    declared = duplicates[0]
    assert declared.question_id == "lok-sabha/18/5/unstarred/57"
    assert declared.copies == 2
    assert declared.identical is True
    assert declared.question_id in declared.gap_note
    assert KNOWN_GAP_DUPLICATE_RECORDS


def test_guarantee_6_non_identical_records_sharing_an_id_are_refused(fixtures_dir):
    """Two *different* questions under one id must raise, not pick a winner.

    Keeping either drops a real question (FR-004); keeping both hands consumers
    two records under one id and breaks the instruction guarantee 6 gives them.
    There is no publishable choice, so ingest refuses and the maintainer
    decides. Measured over the full window after adding `type`: **zero** such
    cases -- this path is unreached on today's data and exists for the next
    time the upstream renumbers.
    """
    import json

    from sansad.ingest.questions import load_question_records

    body = json.loads((fixtures_dir / "shared_ques_no.json").read_text(encoding="utf-8"))
    rows = [dict(r) for r in body["listOfQuestions"]]
    # Make the second copy of quesNo 57 a different question under the same id.
    rows[-1]["subjects"] = "A DIFFERENT subject under the same composite identity"

    with pytest.raises(ValueError, match="NOT identical"):
        load_question_records(rows, last_refreshed="2026-10-09")


def test_guarantee_6_a_question_id_in_several_partitions_is_one_question(
    tmp_path, variant_members, question_records
):
    """ "a `question_id` appearing in several files is **one** question: a
    consumer combining partitions must de-duplicate on `question_id` rather
    than sum across them."

    Asserted on the published files: the same question genuinely appears in
    several *files*, never twice in one, and summing across axes over-counts by
    exactly the co-asking multiplier.
    """
    from sansad.publish.formats import NDJSON_SUFFIX, read_ndjson
    from sansad.publish.partitions import (
        BY_MEMBER_DIR,
        BY_MINISTRY_DIR,
        BY_SESSION_DIR,
        write_partitions,
    )
    from sansad.resolve import resolve_questions

    result = resolve_questions(question_records("co_asked.json"), variant_members)
    write_partitions(tmp_path, result.questions)

    per_axis: dict[str, list[str]] = {}
    for axis in (BY_SESSION_DIR, BY_MINISTRY_DIR, BY_MEMBER_DIR):
        ids: list[str] = []
        for path in sorted((tmp_path / axis).glob(f"*{NDJSON_SUFFIX}")):
            rows = read_ndjson(path)
            file_ids = [r["question_id"] for r in rows]
            assert len(file_ids) == len(set(file_ids)), (
                f"{path.name}: the same question_id appears twice in ONE file"
            )
            ids.extend(file_ids)
        per_axis[axis] = ids

    # Each question is published exactly once per session and per ministry.
    assert sorted(per_axis[BY_SESSION_DIR]) == sorted({q.question_id for q in result.questions})
    assert len(per_axis[BY_MINISTRY_DIR]) == len(result.questions)

    # by-member republishes a co-asked question once per asker -- which is why
    # summing across partitions over-counts and the guarantee says de-duplicate.
    assert len(per_axis[BY_MEMBER_DIR]) > len(set(per_axis[BY_MEMBER_DIR]))
    assert set(per_axis[BY_MEMBER_DIR]) <= set(per_axis[BY_SESSION_DIR])
    combined = per_axis[BY_SESSION_DIR] + per_axis[BY_MINISTRY_DIR] + per_axis[BY_MEMBER_DIR]
    assert len(set(combined)) == len(result.questions), (
        "de-duplicating on question_id must recover the true question count"
    )
    assert len(combined) > len(set(combined)), "summing across axes must over-count"


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


def test_guarantee_7_every_published_set_carries_its_rebuild_date(
    tmp_path, variant_members, question_records
):
    """ "Every published set carries the date it was last rebuilt (FR-016)."

    The per-record half is asserted above; this is the per-set half, which is
    the manifest. It also carries the file and record counts a consumer needs
    to tell a complete snapshot from a truncated one.
    """
    import json

    from sansad.publish.partitions import (
        PARTITION_MANIFEST_NAME,
        write_manifest,
        write_partitions,
    )
    from sansad.resolve import resolve_questions

    result = resolve_questions(question_records("co_asked.json"), variant_members)
    partitions = write_partitions(tmp_path, result.questions)
    path = write_manifest(
        tmp_path,
        last_refreshed="2026-10-09",
        sets={p.axis: {"files": p.files, "records": p.records} for p in partitions},
    )

    assert path.name == PARTITION_MANIFEST_NAME
    body = json.loads(path.read_text(encoding="utf-8"))
    assert body["last_refreshed"] == "2026-10-09"
    assert set(body["sets"]) == {"by-session", "by-ministry", "by-member"}
    for counts in body["sets"].values():
        assert counts["files"] > 0
        assert counts["records"] > 0

    # Byte-deterministic: the snapshot is force-pushed as one commit, and an
    # unexplained diff in a one-commit-deep history cannot be diffed.
    first = path.read_bytes()
    write_manifest(
        tmp_path,
        last_refreshed="2026-10-09",
        sets={p.axis: {"files": p.files, "records": p.records} for p in partitions},
    )
    assert path.read_bytes() == first


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
