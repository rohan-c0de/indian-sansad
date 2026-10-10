"""T088 — `aggregates/state-subjects`, and SC-007's reproducibility over it.

US3 acceptance scenario 2 asks that a state's subjects be summarised. This
aggregate is what the page reads, and SC-007 is the promise that matters about
it: "Any count or comparison shown can be reproduced by hand from the published
record using the stated counting basis."

**The reproduction is the point of this file.** `test_every_state_s_counts_are
_reproducible_from_the_published_by_member_files` re-derives all 36 states from
`by-member/` without importing `sansad.views.state_subjects` at all — the owner's
requirement, 2026-10-10. A test that re-ran the aggregator would prove it agrees
with itself, which is not what SC-007 promises a consumer.

The attribution rule it reproduces, from the published counting basis:

* a question counts ONCE toward a state if at least one identified asker holds
  a seat there;
* a question co-asked across two states counts for BOTH;
* a question with no identified asker has no state and is EXCLUDED.

That maps onto the by-member partition exactly: a question is in a member's file
**iff** that member is an identified asker of it. So a state's questions are the
union of its members' files, de-duplicated on `question_id` — and the
de-duplication is guarantee 6, which is why the basis insists on it.
"""

from __future__ import annotations

import collections
import json
from pathlib import Path

import pytest

from sansad.views.basis import BASIS_VERSION, state_subject_basis
from sansad.views.state_subjects import DEFAULT_TOP_N, state_subjects, states_by_member

PUBLISHED = Path(__file__).resolve().parents[2] / "data" / "published"


def _rows(stem: str) -> list[dict]:
    path = PUBLISHED / stem
    if not path.is_file():
        pytest.skip(f"{stem} not built -- NOT AUDITED, not a pass. Run `make refresh`.")
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


# ---------------------------------------------------------------------------
# The aggregator's own rules, on constructed input
# ---------------------------------------------------------------------------
class _Q:
    """The two attributes the tally reads. Not a Question: this test is about
    the counting rule, and a real Question would drag its validation in."""

    def __init__(self, subject, askers):
        self.subject = subject
        self.asking_members = tuple(askers)


MEMBER_STATES = {"m1": "Alpha", "m2": "Alpha", "m3": "Beta"}


def test_a_question_counts_once_per_state_not_once_per_asker():
    """Two askers from ONE state is one question for that state."""
    result = state_subjects([_Q("Water", ("m1", "m2"))], member_states=MEMBER_STATES)
    assert result.series == {("Alpha", "Water"): 1}
    assert result.state_totals == {"Alpha": 1}
    assert result.multi_state == 0


def test_a_question_co_asked_across_two_states_counts_for_both():
    result = state_subjects([_Q("Water", ("m1", "m3"))], member_states=MEMBER_STATES)
    assert result.series == {("Alpha", "Water"): 1, ("Beta", "Water"): 1}
    assert result.multi_state == 1
    # The states therefore sum to MORE than the question total. Stated, not hidden.
    assert sum(result.state_totals.values()) == 2


def test_a_question_with_no_identified_asker_is_excluded_and_counted():
    result = state_subjects(
        [_Q("Water", ()), _Q("Roads", ("unknown-id",)), _Q("Power", ("m1",))],
        member_states=MEMBER_STATES,
    )
    assert result.unattributable == 2
    assert result.series == {("Alpha", "Power"): 1}


def test_subjects_are_exact_lines_and_near_duplicates_stay_separate():
    """ "no stemming, no case folding and no merging of near-identical lines"."""
    result = state_subjects(
        [
            _Q("Drinking Water Supply", ("m1",)),
            _Q("Drinking water supply", ("m1",)),
            _Q("Drinking Water Supply ", ("m1",)),
        ],
        member_states=MEMBER_STATES,
    )
    assert len(result.series) == 3, f"subject lines were merged: {result.series}"
    assert result.state_subject_counts == {"Alpha": 3}


def test_only_the_top_n_are_published_with_their_denominator():
    questions = [_Q(f"Subject {i:02d}", ("m1",)) for i in range(5) for _ in range(5 - i)]
    result = state_subjects(questions, member_states=MEMBER_STATES, top_n=2)
    rows = result.as_rows()
    assert [r["subject"] for r in rows] == ["Subject 00", "Subject 01"]
    assert [r["questions"] for r in rows] == [5, 4]
    for row in rows:
        # The denominator travels with every row.
        assert row["state_questions"] == 15
        assert row["state_subjects"] == 5
        assert row["subjects_shown"] == 2
        assert row["counting_basis_unit"] == "state-question"
        assert row["basis_version"] == BASIS_VERSION
        assert "rank" not in row and "position" not in row


def test_ties_break_on_the_subject_so_two_refreshes_are_byte_identical():
    questions = [_Q("Zebra", ("m1",)), _Q("Apple", ("m1",))]
    first = state_subjects(questions, member_states=MEMBER_STATES).as_rows()
    second = state_subjects(list(reversed(questions)), member_states=MEMBER_STATES).as_rows()
    assert first == second
    assert [r["subject"] for r in first] == ["Apple", "Zebra"]


def test_a_top_n_below_one_is_refused():
    with pytest.raises(ValueError, match="at least 1"):
        state_subjects([], member_states=MEMBER_STATES, top_n=0)


def test_states_by_member_reads_the_seat_set():
    from sansad.model.constituency import Constituency, Representation

    seats = (
        Constituency(
            constituency_id="alpha-one",
            name="One",
            state="Alpha",
            representations=(Representation(member_id="m1", term_number=17),),
        ),
        Constituency(
            constituency_id="beta-two",
            name="Two",
            state="Beta",
            representations=(Representation(member_id="m3", term_number=18),),
        ),
    )
    assert states_by_member(seats) == {"m1": "Alpha", "m3": "Beta"}


# ---------------------------------------------------------------------------
# The counting basis -- the attribution rule must be IN it
# ---------------------------------------------------------------------------
def test_the_basis_states_the_attribution_rule():
    """The owner's requirement: publish the attribution rule in the counting
    basis, as every other aggregate does."""
    basis = state_subject_basis(unattributable=2_241, multi_state=16_284, states=36, top_n=25)
    assert len(basis) > 80, "a basis must be readable prose, not a label"
    low = basis.lower()
    # 1. once per state, not per asker
    assert "once" in low and "not once per asker" in low
    # 2. both states, and the warning not to sum them
    assert "both" in low and "16,284" in basis
    assert "do not sum the states" in low
    # 3. the excluded ones, with their number stated separately
    assert "excluded" in low and "2,241" in basis
    # 4. exact subject lines, not topics
    assert "exact subject lines" in low and "not" in low and "topics" in low
    assert "no stemming" in low and "no case folding" in low
    # The top-N bound and its denominator
    assert "top 25" in low


def test_the_published_basis_resolves_for_every_state_subjects_row():
    basis = {
        (r["unit"], r["basis_version"]): r["counting_basis"]
        for r in _rows("aggregates/counting-basis.jsonl")
    }
    rows = _rows("aggregates/state-subjects.jsonl")
    assert rows
    for row in rows:
        key = (row["counting_basis_unit"], row["basis_version"])
        assert key in basis, f"basis reference {key} does not resolve"
        assert len(basis[key]) > 80
    # And the published prose carries this refresh's own figures, not the
    # defaults -- a stamp describing a different window would look authoritative.
    text = basis[("state-question", BASIS_VERSION)]
    assert "0 questions in this window" not in text


# ---------------------------------------------------------------------------
# SC-007 -- reproduce every state by hand from the published by-member files
# ---------------------------------------------------------------------------
def test_every_state_s_counts_are_reproducible_from_the_published_by_member_files():
    """The owner's requirement, and SC-007 over this aggregate.

    Nothing from `sansad.views.state_subjects` is used to produce the expected
    figures: they come from `reference/constituencies.jsonl` (which member sits
    for which state) and `by-member/*.jsonl` (which questions they asked),
    de-duplicated on `question_id` exactly as the basis says to.

    All 36 states, 1.2 s measured.
    """
    seats = _rows("reference/constituencies.jsonl")
    published = _rows("aggregates/state-subjects.jsonl")

    members_by_state: dict[str, set[str]] = collections.defaultdict(set)
    for seat in seats:
        for rep in seat["representations"]:
            members_by_state[seat["state"]].add(rep["member_id"])

    by_state: dict[str, dict[str, int]] = collections.defaultdict(dict)
    totals: dict[str, int] = {}
    distinct: dict[str, int] = {}
    for row in published:
        by_state[row["state"]][row["subject"]] = row["questions"]
        totals[row["state"]] = row["state_questions"]
        distinct[row["state"]] = row["state_subjects"]

    assert set(by_state) == set(members_by_state), (
        "the aggregate and the seat set disagree about which states exist"
    )

    for state, member_ids in sorted(members_by_state.items()):
        # The union of the state's members' files, de-duplicated on
        # question_id -- guarantee 6, which the basis restates.
        subject_of: dict[str, str] = {}
        for member_id in sorted(member_ids):
            path = PUBLISHED / "by-member" / f"{member_id}.jsonl"
            if not path.is_file():
                continue  # a member who asked nothing has no file
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                subject_of[record["question_id"]] = record["subject"]

        counts = collections.Counter(subject_of.values())
        assert len(subject_of) == totals[state], (
            f"{state}: counted {len(subject_of)} questions by hand, "
            f"the aggregate publishes {totals[state]}"
        )
        assert len(counts) == distinct[state], (
            f"{state}: counted {len(counts)} distinct subject lines by hand, "
            f"the aggregate publishes {distinct[state]}"
        )
        for subject, published_count in by_state[state].items():
            assert counts[subject] == published_count, (
                f"{state} / {subject!r}: counted {counts[subject]} by hand, "
                f"the aggregate publishes {published_count}"
            )
        # The published rows really are the largest ones.
        cutoff = min(by_state[state].values())
        for subject, count in counts.items():
            if subject not in by_state[state]:
                assert count <= cutoff, (
                    f"{state} / {subject!r} has {count} questions but was not published, "
                    f"while {cutoff} was"
                )


def test_the_unattributable_total_is_reproducible_from_the_question_record():
    """The number the basis states separately.

    A question is unattributable iff none of its asking members holds a seat in
    the window. Re-derived from `by-session/` and the seat set.
    """
    seats = _rows("reference/constituencies.jsonl")
    seated = {rep["member_id"] for seat in seats for rep in seat["representations"]}

    sessions = sorted((PUBLISHED / "by-session").glob("*.jsonl"))
    if not sessions:
        pytest.skip("by-session not built -- NOT AUDITED, not a pass.")

    unattributable = 0
    total = 0
    for path in sessions:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            total += 1
            if not any(m in seated for m in (record.get("asking_members") or ())):
                unattributable += 1

    basis = {r["unit"]: r["counting_basis"] for r in _rows("aggregates/counting-basis.jsonl")}
    assert f"{unattributable:,} questions in this window" in basis["state-question"], (
        f"the basis does not state {unattributable:,} as the unattributable count"
    )
    assert 0 < unattributable < total


def test_the_published_top_n_is_the_decided_one():
    """Owner decision 2026-10-10: top 25 per state."""
    assert DEFAULT_TOP_N == 25
    rows = _rows("aggregates/state-subjects.jsonl")
    per_state = collections.Counter(r["state"] for r in rows)
    assert max(per_state.values()) <= DEFAULT_TOP_N
    assert set(r["subjects_shown"] for r in rows) <= {DEFAULT_TOP_N}
