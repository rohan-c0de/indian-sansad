"""T038 -- `quickstart.md` scenario 3 (FR-003): co-asked questions.

> **Expected**: one question record carrying several `member_id` values. Not
> several records.

`data-model.md` -> Question: "A co-asked question MUST carry every asking member
and MUST NOT be duplicated per asker."

Why one record rather than one per asker: duplicating the question per asker is
how a per-member count silently becomes a question count. The dataset contract
carries the consumer-facing half of the same rule as guarantee 4, and guarantee
6 says what follows for a consumer combining partitions -- "a `question_id`
appearing in several files is **one** question".

`route-capture.md` measured the mean asker count at **1.32** on 50 records and
**1.504** on 250, with the maximum rising from 6 to **20**, and recorded the
disagreement as the finding: "observed twice, not converged". So co-asking is
not an edge case in this dataset. It is the common case for a large minority of
records, and the multiplier it implies is not yet a settled number.
"""

from __future__ import annotations

from collections import Counter

from sansad.model._common import ResolutionStatus


def test_a_co_asked_question_is_one_record_with_several_member_ids(
    variant_members, question_records
):
    from sansad.resolve import resolve_questions

    records = question_records("co_asked.json")
    result = resolve_questions(records, variant_members)

    occurrences = Counter(q.question_id for q in result.questions)
    duplicated = {qid: n for qid, n in occurrences.items() if n > 1}
    assert not duplicated, f"question(s) duplicated per asker: {duplicated}"

    q101 = next(q for q in result.questions if q.question_id.endswith("/101"))
    assert q101.is_co_asked
    assert q101.asking_members == ("fx-0001", "fx-0002", "fx-0003"), (
        f"expected all three askers on one record, got {q101.asking_members}"
    )
    assert q101.resolution_status is ResolutionStatus.RESOLVED


def test_a_single_asker_question_is_unaffected(variant_members, question_records):
    from sansad.resolve import resolve_questions

    records = question_records("co_asked.json")
    result = resolve_questions(records, variant_members)

    q102 = next(q for q in result.questions if q.question_id.endswith("/102"))
    assert q102.is_co_asked is False
    assert q102.asking_members == ("fx-0001",)
    assert q102.resolution_status is ResolutionStatus.RESOLVED


def test_the_same_member_asking_twice_is_not_listed_twice(variant_members, question_records):
    """`Question.__post_init__` refuses a duplicate asker; this asserts the
    resolver never hands it one.

    Two written forms of the same person on one question -- which the required
    variant pair makes possible -- must collapse to one `member_id`, not two
    entries for one person.
    """
    from sansad.ingest.questions import QuestionRecord
    from sansad.resolve import resolve_questions

    records = question_records("co_asked.json")
    original = next(r for r in records if r.question.question_id.endswith("/101"))
    doubled = QuestionRecord(
        question=original.question,
        asker_forms=("Shri Sunil Kumar Singh", "Singh, Sunil K."),
    )

    result = resolve_questions([doubled], variant_members)
    q = result.questions[0]
    assert q.asking_members == ("fx-0001",)
    assert q.resolution_status is ResolutionStatus.RESOLVED


def test_every_asking_form_gets_its_own_resolution_record(variant_members, question_records):
    """FR-005 over a co-asked question: three askers, three auditable joins.

    One record per *form encountered* (T049), so a consumer can verify each of
    the three joins separately rather than being told the question as a whole
    resolved.
    """
    from sansad.resolve import resolve_questions

    records = question_records("co_asked.json")
    result = resolve_questions(records, variant_members)

    written_forms = {form for r in records for form in r.asker_forms}
    assert {r.name_as_written for r in result.records} == written_forms

    for record in result.records:
        assert record.source_record_ref, record.name_as_written
