"""T087 -- the constituency reference set, which US3 enters the record through.

Three assertions `tasks.md` names, and the defects T086 fixed behind them:

> a constituency with two different holders across the covered terms lists both
> with periods; a state resolves to its members; every member reached this way
> has party and term.

**Every case is built from `tests/fixtures/constituencies.json`**, which is
hand-written -- no upstream response, per `tests/fixtures/README.md`. The real
dataset is not read here: a contract test that asserted against the current
build would pass or fail on whatever was last published rather than on the rule.
The measured figures from the real roster are recorded in
`specs/001-resolved-metadata-layer/spike/size-budget.md` instead.

**What these tests do not establish.** They say nothing about the page. The
view's own behaviour is `tests/page/constituency.test.mjs`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sansad.ingest.members import load_members
from sansad.ingest.questions import ministry_id_for
from sansad.model._common import NOT_STATED
from sansad.model.constituency import constituency_id_for
from sansad.publish.formats import rows_for
from sansad.publish.reference import constituencies_from

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

#: The window the fixture is written against, and the window `sansad.cli`
#: publishes. Spelled here rather than imported so a change to the covered
#: window has to be made deliberately in the test too.
WINDOW: tuple[int, ...] = (17, 18)


@pytest.fixture(scope="module")
def members():
    body = json.loads((FIXTURES / "constituencies.json").read_text(encoding="utf-8"))
    return load_members(body["members"], last_refreshed="2026-10-10")


@pytest.fixture(scope="module")
def constituencies(members):
    return constituencies_from(members, window=WINDOW)


@pytest.fixture(scope="module")
def by_id(constituencies):
    return {c.constituency_id: c for c in constituencies}


# ---------------------------------------------------------------------------
# 1. Two different holders across the covered terms -- US3 scenario 3
# ---------------------------------------------------------------------------
def test_two_holders_across_the_terms_are_both_listed_with_their_terms(by_id):
    """ "Both members appear with their respective periods, not merged into one."""
    seat = by_id[constituency_id_for("Constituency Theta", "State Alpha")]
    assert seat.changed_hands_in_window is True
    assert seat.term_numbers == (17, 18)

    pairs = [(r.member_id, r.term_number) for r in seat.representations]
    assert pairs == [("fx-c001", 17), ("fx-c002", 18)], (
        "both holders must be listed, term first, and neither merged away"
    )
    # The period is the TERM NUMBER. No date is invented: the module docstring
    # of sansad.publish.reference declares session and term periods a gap.
    assert {r.start_date for r in seat.representations} == {NOT_STATED}
    assert {r.end_date for r in seat.representations} == {None}


def test_one_member_holding_both_terms_gets_two_representations(by_id):
    """The case the old key collapsed, and the majority case in the real data.

    `Constituency.__post_init__` keyed duplicates on `(member_id, start_date)`
    and every `start_date` is NOT_STATED, so one member could contribute only
    one representation however many terms they served. 216 of the real window's
    545 seats are held by one member across both covered terms.
    """
    seat = by_id[constituency_id_for("Constituency Iota", "State Alpha")]
    assert [(r.member_id, r.term_number) for r in seat.representations] == [
        ("fx-c003", 17),
        ("fx-c003", 18),
    ]
    assert seat.term_numbers == (17, 18)
    # One member, so the seat did NOT change hands -- the two properties say
    # different things and a page needs both.
    assert seat.changed_hands_in_window is False


def test_a_seat_held_in_only_one_covered_term_says_so(by_id):
    seat = by_id[constituency_id_for("Constituency Kappa", "State Alpha")]
    assert seat.term_numbers == (17,)
    assert seat.changed_hands_in_window is False


# ---------------------------------------------------------------------------
# 2. A state resolves to its members
# ---------------------------------------------------------------------------
def test_a_state_resolves_to_its_seats_and_their_members(constituencies):
    """SC-008: "A person who knows only their constituency or state can reach
    their members' questions without knowing a member's name."

    The walk the page makes: filter the set by `state`, then take the
    `member_id`s off the representations. No member reference set is involved.
    """
    alpha = [c for c in constituencies if c.state == "State Alpha"]
    assert {c.name for c in alpha} == {
        "Constituency Theta",
        "Constituency Iota",
        "Constituency Kappa",
        "Constituency Nu",
    }
    reached = {r.member_id for c in alpha for r in c.representations}
    assert reached == {"fx-c001", "fx-c002", "fx-c003", "fx-c004", "fx-c009"}


def test_the_same_seat_name_in_two_states_is_two_rows(by_id, constituencies):
    """ "Constituency names repeat across states, so a typed name must always
    show its state" (owner decision 2026-10-10).

    Three real names do this -- Aurangabad, Hamirpur, Maharajganj -- and before
    T086 they merged: the published `aurangabad` row carried `state:
    "Hyderabad"` and 22 representations from both seats.
    """
    alpha = by_id[constituency_id_for("Constituency Theta", "State Alpha")]
    beta = by_id[constituency_id_for("Constituency Theta", "State Beta")]
    assert alpha.constituency_id != beta.constituency_id
    assert alpha.name == beta.name == "Constituency Theta"
    assert (alpha.state, beta.state) == ("State Alpha", "State Beta")
    assert {r.member_id for r in beta.representations} == {"fx-c005"}
    assert "fx-c005" not in {r.member_id for r in alpha.representations}

    # And the id carries the state, so a row can never be addressed by name
    # alone -- which is what made the merge possible.
    assert "state-beta" in beta.constituency_id


def test_every_published_id_is_unique_and_names_its_state(constituencies):
    ids = [c.constituency_id for c in constituencies]
    assert len(set(ids)) == len(ids), "constituency_id must identify one seat"
    for seat in constituencies:
        assert seat.constituency_id == constituency_id_for(seat.name, seat.state)


def test_the_two_id_halves_collapse_when_they_are_one_slug(by_id):
    """8 of the real window's 545 seats carry their own state's name."""
    seat_id = constituency_id_for("State Delta", "State Delta")
    assert seat_id == "state-delta", "an identical slug must not be repeated"
    assert by_id[seat_id].name == "State Delta"


# ---------------------------------------------------------------------------
# 3. Every member reached this way has party and term
# ---------------------------------------------------------------------------
def test_every_member_reached_has_a_party_and_a_term(members, constituencies):
    """ "every member reached this way has party and term".

    Term comes off the representation. **Party does not**: it is on the Member
    record, which the constituency set does not carry. This test therefore
    asserts the pair is obtainable -- for every `member_id` on a representation
    there is a member with a stated party and the matching term -- and NOT that
    one fetch is enough to show it. What the page actually fetches is T088's
    question, and the gap is recorded in `spike/size-budget.md`.
    """
    by_member = {m.member_id: m for m in members}
    reached = {(r.member_id, r.term_number) for c in constituencies for r in c.representations}
    assert reached, "the set reached no member at all"
    for member_id, term_number in sorted(reached):
        member = by_member[member_id]
        assert member.party, f"{member_id} has no party value at all"
        assert term_number in WINDOW
        assert term_number in {t.number for t in member.terms}


def test_a_missing_party_is_an_explicit_not_stated(members):
    """ "Missing attributes MUST be represented as an explicit 'not stated'
    value, never silently dropped." """
    member = next(m for m in members if m.member_id == "fx-c009")
    assert member.party == NOT_STATED
    assert member.sitting_status == NOT_STATED


# ---------------------------------------------------------------------------
# The covered window
# ---------------------------------------------------------------------------
def test_a_seat_with_no_in_window_representation_is_not_published(by_id):
    """Terms 15 and 16 only. The published set covers the 17th and 18th, and a
    row with no representation inside it would be an entry a visitor can open
    that answers with nothing.

    This bounds the set: 897 rows over every term the roster records become the
    **545** seats the window covers, and 5,361 representations become 1,103.
    """
    assert constituency_id_for("Constituency Lambda", "State Gamma") not in by_id


def test_an_out_of_window_term_is_dropped_from_a_seat_that_is_published(by_id):
    """One member, terms 16 and 17. The 16th is not part of this record."""
    seat = by_id[constituency_id_for("Constituency Mu", "State Gamma")]
    assert [(r.member_id, r.term_number) for r in seat.representations] == [("fx-c007", 17)]
    assert 16 not in seat.term_numbers


def test_the_window_is_required_and_an_empty_one_is_refused(members):
    """No default. A default would silently restore the unbounded behaviour,
    which is the defect, and this project's rule is that a step refuses rather
    than guesses which window it is publishing."""
    with pytest.raises(TypeError):
        constituencies_from(members)  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="at least one term"):
        constituencies_from(members, window=())


# ---------------------------------------------------------------------------
# The published shape, and the slug rule's copy
# ---------------------------------------------------------------------------
def test_the_published_row_carries_exactly_the_contracted_fields(constituencies):
    from sansad.model.constituency import PUBLISHED_FIELDS

    rows = rows_for(constituencies)
    assert rows, "no rows were produced"
    for row in rows:
        assert tuple(row) == PUBLISHED_FIELDS
        for rep in row["representations"]:
            assert tuple(rep) == ("member_id", "start_date", "end_date", "term_number")


def test_the_slug_copy_agrees_with_ministry_id_for():
    """`constituency_id_for` reimplements the slug rather than importing it, so
    `sansad.model` does not depend on `sansad.ingest`. This is the test that
    stops the copy drifting."""
    for name in (
        "Aurangabad",
        "Dadra and Nagar Haveli and Daman and Diu",
        "  Mixed CASE, punctuation! ",
        "North-East Delhi",
        "Thiruvananthapuram",
    ):
        assert constituency_id_for(name, "") == f"not-stated-{ministry_id_for(name)}"


def test_an_unnameable_seat_is_not_given_a_state_prefixed_id():
    """A name that slugs to nothing has no identity to prefix."""
    assert constituency_id_for("", "State Alpha") == NOT_STATED
    assert constituency_id_for("!!!", "State Alpha") == NOT_STATED
