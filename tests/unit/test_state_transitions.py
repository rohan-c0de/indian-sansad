"""T096 -- the `resolution_status` transitions in `data-model.md`.

`data-model.md` -> State Transitions, verbatim:

    unresolved --automatic match--> resolved
    unresolved --several equal matches--> ambiguous
    ambiguous  --maintainer assertion--> resolved
    resolved   --upstream name change--> ambiguous   (re-resolution needed; MUST notify, FR-011)

    A transition out of `resolved` MUST raise a maintainer signal, because it
    means a previously published join has become uncertain.

**A transition needs two snapshots, so every test here resolves twice.** The
status of one question in one pass is a state, not a transition; what the rule
is about is the same `question_id` carrying one status in the published record
a consumer already took and a different one after the next refresh. So each
test below changes exactly ONE input between the two passes -- the matcher
tier, the roster, the assertions, or the written asker form -- and asserts the
status moved along the named edge. Changing two would prove the status moved
without saying which edge did it.

**One edge the diagram does not draw, and this file does.** The rule is "a
transition out of `resolved`", not "a transition from `resolved` to
`ambiguous`". `resolved -> unresolved` is reachable by the same upstream name
change when the new form matches nothing rather than matching several, and it
is the worse of the two for a consumer. It is covered here, and recorded as an
edge `data-model.md` omits rather than one it forbids.

**The signal is raised by nothing in the pipeline.** `sansad.signals.alerts`
defines `resolved_transitions_out`, the fourth of the four maintainer signals
the dataset contract names, and **no module under `src/` calls it** -- the
comparison against the previous snapshot that would detect such a transition
is NOT PRESENT (`--previous` feeds T054's last-known-good retention only).
That gap is pinned by the last test in this file rather than described in a
comment, so it fails when the detection lands and is read by a person rather
than being carried as a note nobody re-checks.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sansad.ingest.members import load_members
from sansad.ingest.questions import load_question_records
from sansad.model._common import ResolutionStatus
from sansad.model.resolution_record import ResolutionMethod
from sansad.resolve import resolve_questions
from sansad.resolve.assertions import Assertion
from sansad.signals.alerts import Severity, SignalKind, resolved_transitions_out

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
REFRESHED_ON = "2026-10-09"

#: The two members `near_identical_members.json` pairs: one name, one party,
#: one state, two people, distinguishable only by a constituency the question
#: route does not carry. The fixture's own note calls this "the harder case".
KAVITA = ("fx-0020", "fx-0021")


@pytest.fixture(scope="module")
def roster() -> list[dict]:
    return list(json.loads((FIXTURES / "roster.json").read_text(encoding="utf-8"))["members"])


@pytest.fixture(scope="module")
def members(roster):
    return load_members(roster, last_refreshed=REFRESHED_ON)


def _question(asker: str, *, ques_no: int = 901) -> list:
    """One question record carrying one written asker form.

    Built from the `ambiguous.json` record so the shape is the route's own
    rather than this file's idea of it, with the asker and number replaced.
    """
    body = json.loads((FIXTURES / "ambiguous.json").read_text(encoding="utf-8"))
    row = dict(body["listOfQuestions"][0])
    row["quesNo"] = ques_no
    row["member"] = [asker]
    return load_question_records([row], last_refreshed=REFRESHED_ON)


def _status(questions) -> dict[str, ResolutionStatus]:
    return {q.question_id: q.resolution_status for q in questions}


def _transitions_out_of_resolved(before, after) -> tuple[str, ...]:
    """Question ids that were `resolved` in `before` and are not in `after`.

    **A local helper, not an import.** Nothing in `src/` does this comparison
    -- see the module docstring and the pin at the foot of this file. It is
    here so the transition can be asserted at all; it is deliberately four
    lines, so it cannot be mistaken for the missing implementation.
    """
    was = _status(before)
    now = _status(after)
    return tuple(
        sorted(
            qid
            for qid, status in was.items()
            if status is ResolutionStatus.RESOLVED
            and now.get(qid, ResolutionStatus.UNRESOLVED) is not ResolutionStatus.RESOLVED
        )
    )


# ---------------------------------------------------------------------------
# unresolved --automatic match--> resolved
# ---------------------------------------------------------------------------
def test_unresolved_becomes_resolved_when_the_matcher_reaches_the_form(members):
    """The one input that changes is the containment tier.

    `Ramesh Pillai` is the fixture form the owner's adopted token-containment
    tier recovers: nothing below that tier matches it, and the tier resolves it
    to the roster's `Ramesh Chandra Pillai`. This is the edge that carried the
    automatic rate from 90.64% to 94.78%, exercised on one record.
    """
    records = _question("Ramesh Pillai")

    before = resolve_questions(records, members, containment=False)
    after = resolve_questions(records, members, containment=True)

    (qid,) = _status(before.questions)
    assert _status(before.questions)[qid] is ResolutionStatus.UNRESOLVED
    assert _status(after.questions)[qid] is ResolutionStatus.RESOLVED

    # The join itself appears, and it is auditable: the Resolution Record names
    # the tier that produced it, so a consumer can see WHICH edge was taken.
    assert before.questions[0].asking_members == ()
    assert after.questions[0].asking_members == ("fx-0003",)
    (record,) = after.records
    assert record.method is ResolutionMethod.TOKEN_CONTAINMENT
    assert record.status is ResolutionStatus.RESOLVED


# ---------------------------------------------------------------------------
# unresolved --several equal matches--> ambiguous
# ---------------------------------------------------------------------------
def test_unresolved_becomes_ambiguous_when_the_roster_offers_several_equal_matches(
    members,
):
    """The one input that changes is the roster: the two Kavita Raos arrive.

    `ambiguous`, not `resolved`: the two candidates differ only by a
    constituency the question record does not carry, so nothing in the record
    can break the tie. Collapsing to whichever sorts first is the failure
    `spec.md` Edge Cases names, and the Resolution Record has to list both.
    """
    records = _question("Kavita Rao")
    without = [m for m in members if m.member_id not in KAVITA]

    before = resolve_questions(records, without)
    after = resolve_questions(records, members)

    (qid,) = _status(before.questions)
    assert _status(before.questions)[qid] is ResolutionStatus.UNRESOLVED
    assert _status(after.questions)[qid] is ResolutionStatus.AMBIGUOUS

    # "an ambiguous match MUST NOT be silently collapsed to the first candidate"
    assert after.questions[0].asking_members == ()
    (record,) = after.records
    assert record.member_id is None
    assert record.candidates == KAVITA


# ---------------------------------------------------------------------------
# ambiguous --maintainer assertion--> resolved
# ---------------------------------------------------------------------------
def test_ambiguous_becomes_resolved_on_a_maintainer_assertion(members):
    """The one input that changes is the assertion set.

    And the automatic outcome is NOT overwritten by it: `ResolvedQuestions`
    keeps both, which is what lets the Coverage Statement publish the
    automatic rate separately from the assisted one (SC-002).
    """
    records = _question("Kavita Rao")
    assertion = Assertion(
        name_as_written="Kavita Rao",
        member_id="fx-0020",
        basis="Fixture assertion for T096: the owner picked the Zeta seat holder.",
    )

    before = resolve_questions(records, members)
    after = resolve_questions(records, members, assertions={"Kavita Rao": assertion})

    (qid,) = _status(before.questions)
    assert _status(before.questions)[qid] is ResolutionStatus.AMBIGUOUS
    assert _status(after.questions)[qid] is ResolutionStatus.RESOLVED

    assert after.questions[0].asking_members == ("fx-0020",)
    (record,) = after.records
    assert record.method is ResolutionMethod.MANUAL_ASSERTION
    assert record.asserted_by.value == "maintainer"

    # The assisted rate moved; the automatic rate did not. A blended figure
    # would hide the fact that the matcher still cannot do this one unaided.
    assert after.resolved_assisted == 1
    assert after.resolved_automatic == 0
    assert before.resolved_assisted == 0


# ---------------------------------------------------------------------------
# resolved --upstream name change--> ambiguous   (and --> unresolved)
# ---------------------------------------------------------------------------
def test_resolved_becomes_ambiguous_when_the_upstream_roster_grows_a_second_holder(
    members,
):
    """A published join becomes uncertain. The one input that changes is the roster.

    This is the edge the rule exists for: the refresh a consumer took resolved
    this question to `fx-0020`, and the next one cannot, because the upstream
    roster now carries a second person under the same name. The question is
    still published -- nothing is dropped -- but `asking_members` goes from one
    id to none, so the join a consumer already has disappears from the record.
    """
    records = _question("Kavita Rao")
    one_holder = [m for m in members if m.member_id != "fx-0021"]

    before = resolve_questions(records, one_holder)
    after = resolve_questions(records, members)

    (qid,) = _status(before.questions)
    assert _status(before.questions)[qid] is ResolutionStatus.RESOLVED
    assert _status(after.questions)[qid] is ResolutionStatus.AMBIGUOUS

    assert before.questions[0].asking_members == ("fx-0020",)
    assert after.questions[0].asking_members == (), "the published join is gone"
    # ...and the question itself is still there (FR-004, guarantee 2).
    assert len(after.questions) == len(before.questions) == 1

    assert _transitions_out_of_resolved(before.questions, after.questions) == (qid,)


def test_resolved_becomes_unresolved_when_the_written_form_changes_to_an_unmatchable_one(
    members,
):
    """The edge `data-model.md` does not draw, reached by the same cause.

    "upstream name change" is the cause it names; the diagram draws only the
    `-> ambiguous` outcome. When the new form matches *nothing* rather than
    matching several, the status is `unresolved` -- which is also out of
    `resolved`, and is the worse of the two for a consumer. Recorded here as
    an edge the diagram omits, not one it forbids.
    """
    one_question_id = 902
    before = resolve_questions(
        _question("Shri Sunil Kumar Singh", ques_no=one_question_id), members
    )
    after = resolve_questions(
        _question("Zzyzx Qwerty Nonexistentname", ques_no=one_question_id), members
    )

    (qid,) = _status(before.questions)
    assert _status(after.questions) == {qid: ResolutionStatus.UNRESOLVED}, (
        "the two passes must describe the SAME question for this to be a transition"
    )
    assert _status(before.questions)[qid] is ResolutionStatus.RESOLVED
    assert _transitions_out_of_resolved(before.questions, after.questions) == (qid,)


# ---------------------------------------------------------------------------
# ...MUST raise a maintainer signal
# ---------------------------------------------------------------------------
def test_a_transition_out_of_resolved_raises_a_degraded_maintainer_signal(members):
    """ "MUST raise a maintainer signal, because it means a previously
    published join has become uncertain" -- and at what severity.

    DEGRADED, not NOTICE: nothing failed and the refresh may even have raised
    the overall rate, so a NOTICE is the severity at which this one goes
    unread. FR-010 is unaffected -- the visitor still sees a coherent dated
    record, which is why this is the maintainer's signal and not an error page.
    """
    records_before = _question("Kavita Rao")
    before = resolve_questions(records_before, [m for m in members if m.member_id != "fx-0021"])
    after = resolve_questions(records_before, members)

    moved = _transitions_out_of_resolved(before.questions, after.questions)
    assert moved, "nothing transitioned, so there is no signal to assert"

    signal = resolved_transitions_out(moved, new_status=ResolutionStatus.AMBIGUOUS.value)

    assert signal.kind is SignalKind.RESOLVED_TRANSITION_OUT
    assert signal.severity is Severity.DEGRADED
    assert signal.severity is not Severity.FAILED, (
        "a transition out of resolved must not stop the publish: the rest of "
        "the refresh is good and withholding it would serve a staler record"
    )
    assert signal.detail["count"] == len(moved)
    assert signal.detail["question_ids"] == list(moved)
    assert signal.detail["new_status"] == "ambiguous"

    # Principle V: a signal is delivered through a CI log or an issue, both of
    # which a third party can reach. Question ids and counts only -- no name
    # form, and nothing from an upstream record.
    rendered = str(signal)
    for leaked in ("Kavita", "Rao", "fx-0020", "fx-0021"):
        assert leaked not in rendered, f"the signal text carries {leaked!r}"
    assert leaked_free(signal.detail)


def leaked_free(detail) -> bool:
    """No member name or identity anywhere in a signal's detail payload."""
    flat = json.dumps(detail)
    return not any(token in flat for token in ("Kavita", "Rao", "fx-00"))


def test_a_refresh_with_no_transition_raises_nothing(members):
    """The control. Two identical passes must produce no signal at all.

    Without this, a detector that signalled on every refresh would pass every
    test above -- and a signal that fires every time is one the maintainer
    learns to ignore, which is Principle II's "silence toward the maintainer"
    arriving by the other road.
    """
    records = _question("Shri Sunil Kumar Singh")
    first = resolve_questions(records, members)
    second = resolve_questions(records, members)

    assert _status(first.questions) == _status(second.questions)
    assert _transitions_out_of_resolved(first.questions, second.questions) == ()


# ---------------------------------------------------------------------------
# The gap, pinned
# ---------------------------------------------------------------------------
def test_nothing_under_src_raises_the_resolved_transition_signal():
    """**NOT PRESENT**, pinned so it is read rather than assumed.

    Measured over `src/sansad/**/*.py` on 2026-10-10: two of the four signals
    have a caller -- `ingestion_failure` (`cli.py`, `ingest/questions.py`) and
    `upstream_shape_change` (`ingest/shape.py`) -- and **two do not**:
    `resolved_transitions_out`, which this test pins, and
    `resolution_rate_below_target`, which is out of T096's scope and is
    recorded against the Upkeep gate in `gate-evidence.md` instead.

    Detecting a transition needs the published statuses of the PREVIOUS
    snapshot compared against this refresh's. `--previous` exists but is wired
    to T054's last-known-good retention only, so nothing compares them.

    **This test fails when the detection is implemented**, which is what it is
    for: at that point delete it and assert the pipeline raises the signal on a
    real transition instead.
    """
    src = Path(__file__).resolve().parents[2] / "src" / "sansad"
    definition = src / "signals" / "alerts.py"

    callers = sorted(
        path.relative_to(src).as_posix()
        for path in src.rglob("*.py")
        if path != definition and "resolved_transitions_out" in path.read_text(encoding="utf-8")
    )
    assert callers == [], (
        f"`resolved_transitions_out` now has a caller ({callers}) -- the fourth "
        f"maintainer signal is implemented. Replace this pin with a test that "
        f"the pipeline raises it on a real transition."
    )
    assert "resolved_transitions_out" in definition.read_text(encoding="utf-8"), (
        "the signal factory itself is gone, which is a different defect"
    )
