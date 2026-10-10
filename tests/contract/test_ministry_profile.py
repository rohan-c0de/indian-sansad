"""T073 — the ministry-profile aggregate, checked against the published files.

Two things are being protected here, and they are different.

**The totals must be reproducible from the published question records.** FR-012
and SC-007: a count a consumer cannot reproduce is a count whose basis they were
not told. So the independent count below is written against the **files** —
re-read from disk and counted by hand — and never calls
`sansad.views.ministry_profile`. A check that called the aggregation code would
prove it agrees with itself.

**The resolution-status counts must sum to the question count.** Owner decision
2026-10-10, recorded in T070: T078 has to flag unresolved and ambiguous
questions rather than filter them out, and an aggregate that carries the total
but not the split forces the page to re-derive the flags outside the T064 basis
stamp and outside this test. If the split does not sum, a page built on it shows
a total that disagrees with its own breakdown.

**De-duplication on `question_id` is part of the assertion, not an aside.**
`contracts/published-dataset.md` guarantee 6: the partitions republish the same
records under different keys, so a consumer combining them must de-duplicate.
The independent count de-duplicates, and would be wrong by the co-asking
multiplier if it did not.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest


@pytest.fixture
def members():
    from sansad.ingest.members import load_members

    return load_members(
        json.loads(
            (Path(__file__).resolve().parents[1] / "fixtures" / "roster.json").read_text(
                encoding="utf-8"
            )
        )["members"],
        last_refreshed="2026-10-10",
    )


@pytest.fixture
def published(tmp_path, members, question_records):
    """A real published dataset, written by the real publish layer.

    Built from several fixtures so the statuses actually vary: `co_asked` gives
    resolved questions, `unresolvable` gives one fully unresolved and one
    **partly** resolved, `ambiguous` gives an ambiguous one, and
    `shared_ques_no` gives both question types.
    """
    from sansad.publish.partitions import write_partitions
    from sansad.resolve import resolve_questions
    from sansad.views.ministry_profile import ministry_profiles

    records = []
    for name in ("co_asked.json", "unresolvable.json", "ambiguous.json", "shared_ques_no.json"):
        records.extend(question_records(name))
    resolved = resolve_questions(records, members)
    write_partitions(tmp_path, resolved.questions)

    from sansad.publish.aggregates import write_aggregates
    from sansad.views.composition import compose
    from sansad.views.subject_trends import subject_trends

    write_aggregates(
        tmp_path,
        compositions=[compose(members, term=18)],
        trends=subject_trends(resolved.questions),
        profiles=ministry_profiles(resolved.questions),
    )
    return tmp_path


def _rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _independent_counts(published: Path) -> dict[tuple[str, str], Counter]:
    """Count the published question FILES by hand. No aggregation code.

    De-duplicates on `question_id` across every partition, exactly as guarantee
    6 tells a consumer to.
    """
    seen: dict[str, dict] = {}
    for axis in ("by-session", "by-ministry", "by-member"):
        for path in sorted((published / axis).glob("*.jsonl")):
            for row in _rows(path):
                seen[row["question_id"]] = row

    out: dict[tuple[str, str], Counter] = {}
    for row in seen.values():
        key = (row["ministry_id"], row["session"])
        counter = out.setdefault(key, Counter())
        counter["questions"] += 1
        counter[f"type:{row['type']}"] += 1
        status = row["resolution_status"]
        askers = row["asking_members"] or []
        if status == "resolved":
            counter["fully_linked"] += 1
        elif status == "ambiguous":
            counter["ambiguous"] += 1
        elif askers:
            counter["partly_linked"] += 1
        else:
            counter["not_linked"] += 1
    return out


def test_the_profile_totals_match_an_independent_count_of_the_published_files(published):
    """Requirement (i). Counted from the files, de-duplicated on question_id."""
    from sansad.publish.aggregates import AGGREGATES_DIR_NAME, MINISTRY_PROFILE_STEM

    rows = _rows(published / AGGREGATES_DIR_NAME / f"{MINISTRY_PROFILE_STEM}.jsonl")
    assert rows, "no ministry-profile rows were published"

    independent = _independent_counts(published)
    assert independent, "the fixtures produced no published questions"

    published_counts = {(r["ministry_id"], r["session"]): r for r in rows}
    assert set(published_counts) == set(independent), (
        f"profile keys differ from the published records: "
        f"profile-only={sorted(set(published_counts) - set(independent))}, "
        f"records-only={sorted(set(independent) - set(published_counts))}"
    )
    for key, counter in independent.items():
        assert published_counts[key]["questions"] == counter["questions"], (
            f"{key}: profile says {published_counts[key]['questions']}, "
            f"the records say {counter['questions']}"
        )


def test_the_type_mix_matches_the_independent_count(published):
    from sansad.publish.aggregates import AGGREGATES_DIR_NAME, MINISTRY_PROFILE_STEM

    rows = _rows(published / AGGREGATES_DIR_NAME / f"{MINISTRY_PROFILE_STEM}.jsonl")
    independent = _independent_counts(published)
    for row in rows:
        key = (row["ministry_id"], row["session"])
        mix = row["question_type_mix"]
        assert sum(mix.values()) == row["questions"], f"{key}: the type mix does not sum"
        for qtype, count in mix.items():
            assert independent[key][f"type:{qtype}"] == count, f"{key}/{qtype}"


def test_the_status_counts_sum_to_the_question_count_for_every_row(published):
    """Requirement (ii), and T070's MUST.

    A fourth count, `ambiguous`, is included: `data-model.md` has that status,
    and the owner's instruction was to add a fourth so the sum still holds if
    one ever appears. Asserting the SUM rather than the three names is what
    makes the invariant survive a fourth bucket.
    """
    from sansad.publish.aggregates import AGGREGATES_DIR_NAME, MINISTRY_PROFILE_STEM
    from sansad.views.ministry_profile import STATUS_COUNT_FIELDS

    rows = _rows(published / AGGREGATES_DIR_NAME / f"{MINISTRY_PROFILE_STEM}.jsonl")
    assert rows
    for row in rows:
        parts = {field: row[field] for field in STATUS_COUNT_FIELDS}
        assert sum(parts.values()) == row["questions"], (
            f"{row['ministry_id']}/{row['session']}: "
            f"{' + '.join(f'{k}={v}' for k, v in parts.items())} "
            f"= {sum(parts.values())}, but questions = {row['questions']}"
        )


def test_the_status_split_matches_the_independent_count(published):
    from sansad.publish.aggregates import AGGREGATES_DIR_NAME, MINISTRY_PROFILE_STEM

    rows = _rows(published / AGGREGATES_DIR_NAME / f"{MINISTRY_PROFILE_STEM}.jsonl")
    independent = _independent_counts(published)
    for row in rows:
        key = (row["ministry_id"], row["session"])
        for field in ("fully_linked", "partly_linked", "not_linked", "ambiguous"):
            assert row[field] == independent[key][field], f"{key}/{field}"


def test_the_fixtures_actually_exercise_every_status(published):
    """The control. If every fixture question resolved, the three tests above
    would pass while testing one bucket."""
    independent = _independent_counts(published)
    totals = Counter()
    for counter in independent.values():
        totals.update(counter)
    assert totals["fully_linked"] > 0
    assert totals["partly_linked"] > 0, "no partly-resolved question in the fixtures"
    assert totals["not_linked"] > 0
    assert totals["ambiguous"] > 0, "no ambiguous question in the fixtures"


def test_every_profile_row_carries_a_resolvable_basis_reference(published):
    """Requirement (iii)."""
    from sansad.publish.aggregates import (
        AGGREGATES_DIR_NAME,
        COUNTING_BASIS_STEM,
        MINISTRY_PROFILE_STEM,
    )

    root = published / AGGREGATES_DIR_NAME
    basis = {
        (r["unit"], r["basis_version"]): r["counting_basis"]
        for r in _rows(root / f"{COUNTING_BASIS_STEM}.jsonl")
    }
    assert basis
    rows = _rows(root / f"{MINISTRY_PROFILE_STEM}.jsonl")
    assert rows
    for row in rows:
        key = (row["counting_basis_unit"], row["basis_version"])
        assert key in basis, f"basis reference {key} does not resolve"
        assert len(basis[key]) > 80


def test_both_formats_carry_the_same_profile_records(published):
    from sansad.publish.aggregates import AGGREGATES_DIR_NAME, MINISTRY_PROFILE_STEM
    from sansad.publish.formats import read_csv, read_ndjson, text_projection

    root = published / AGGREGATES_DIR_NAME
    nd = [text_projection(r) for r in read_ndjson(root / f"{MINISTRY_PROFILE_STEM}.jsonl")]
    assert nd == list(read_csv(root / f"{MINISTRY_PROFILE_STEM}.csv"))
