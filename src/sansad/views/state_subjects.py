"""T088 — the subjects a state's members have raised (US3 acceptance scenario 2).

> **Given** a state, **When** a user looks it up, **Then** the subjects its
> members have raised are summarised and individual questions are reachable.
> -- `spec.md` User Story 3, acceptance scenario 2

**Why this file exists at all.** Nothing already published lets a page
summarise a state's subjects. The constituency reference set carries
`member_id` and `term_number`; the subjects live on the question records. The
three routes that do not need a new file were measured (`spike/size-budget.md`
-> T086):

| Route | Cost |
|---|---|
| The state's `by-member` files | **Maharashtra 10,489,198 B** (85 members); median state 958,942 B |
| All 21 search digests, filtered | 20,782,206 B |
| Every (state, subject) pair published | 119,175 rows, 16,181,100 B |

Owner decision 2026-10-10: publish the **top 25 subjects per state** —
**900 rows, 118,297 B** — so the summary is one small fetch and no per-state
*question* partition is created. `contracts/published-dataset.md` forbids the
latter; this is a derived statistic, like composition and subject trends.

**It is a ranking, and the owner lifted the phase's no-rankings rule for this
one case.** Recorded here rather than left as an inference: the rule stands for
members, ministries and anything the page draws.

----

## The attribution rule, published in the counting basis

A question is attached to askers, and an asker holds a seat in a state, so
"a state's questions" is a derived claim and the rule has to be stated where
the numbers are. `sansad.views.basis.state_subject_basis` carries it, and these
rows reference it the way every other aggregate row references its basis.

1. **A question counts ONCE toward a state** if at least one *identified* asker
   holds a seat there. Not once per asker: a question asked by three members of
   one state is one question for that state.
2. **A question co-asked across two states counts for BOTH.** Summing the
   states therefore exceeds the window's question total, and the basis says so
   with the figure, because a reader who adds up the states and compares with
   the published total will otherwise think something is missing.
3. **A question with no identified asker cannot be attributed at all** and is
   EXCLUDED. Its number is stated separately in the basis. Excluding it is the
   opposite of what `subject_trends` does — there, a question with no identified
   asker still has a subject and a session, so dropping it would make the
   subject totals disagree with the published record. Here there is no state to
   attribute it to, and inventing one would be worse than declaring the gap.

## Subjects are exact subject lines, not topics

No stemming, no case folding, no merging of near-identical lines — the same
rule `subject_trends` holds to, and for the same reason: a count a consumer
cannot reproduce from the published records by string equality is a count whose
basis they were not told. So "Drinking Water Supply" and "Drinking water
supply" are two subjects here, and a reader who expects topics will find the
list noisier than a human would group it. Grouping is a reader's judgement and
would not be reproducible. The basis states this too.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from sansad.model.question import Question
from sansad.views.basis import BASIS_VERSION, state_subject_basis

__all__ = ["DEFAULT_TOP_N", "StateSubjects", "state_subjects", "states_by_member"]

#: Owner decision 2026-10-10. 25 rather than 10 (46,628 B) or 50 (237,445 B).
DEFAULT_TOP_N = 25

#: The published basis unit. A third unit beside `question` and `member`,
#: because neither of those states the attribution rule above.
BASIS_UNIT = "state-question"


def states_by_member(constituencies: Iterable[object]) -> dict[str, str]:
    """`member_id` -> the state of the seat they hold, from the seat set.

    Built from `Constituency` values rather than from `Member.state` so the
    aggregate and the page agree **by construction**: the page reaches a state's
    members through this same set. The two are identical today -- verified, 0 of
    1,103 in-window member-terms carry a state differing from the member's -- so
    this is a choice about which definition is authoritative, not a correction.

    A member holding seats in two states across the two terms would appear under
    the later one; no member in the window does (the roster records one seat per
    member), and that limitation is declared in `sansad.publish.reference`.
    """
    out: dict[str, str] = {}
    for constituency in constituencies:
        state = getattr(constituency, "state", "")
        for representation in getattr(constituency, "representations", ()) or ():
            member_id = getattr(representation, "member_id", "")
            if member_id and state:
                out[member_id] = state
    return out


@dataclass(frozen=True, slots=True)
class StateSubjects:
    """Per-state subject-line counts, the top N of each, with the basis."""

    #: (state, subject) -> questions attributed to that state on that subject.
    series: Mapping[tuple[str, str], int]
    #: state -> every question attributed to it, the denominator for the top N.
    state_totals: Mapping[str, int]
    #: state -> how many DISTINCT subject lines it has, so a reader can see
    #: what fraction of them the top N is.
    state_subject_counts: Mapping[str, int]
    #: Questions with no identified asker, so no state. Declared, not hidden.
    unattributable: int = 0
    #: How many of the series' questions are counted for more than one state.
    multi_state: int = 0
    top_n: int = DEFAULT_TOP_N
    counting_basis: str = field(default="")
    basis_version: str = BASIS_VERSION

    def as_rows(self) -> list[dict[str, object]]:
        """One published row per (state, subject), the top N of each state.

        Ordered by state, then by descending count, then by subject -- the
        subject breaks the tie so two refreshes over the same data produce a
        byte-identical file. The dataset is force-pushed as one commit, so an
        unexplained reordering cannot be diffed against anything.

        **The rank is not published.** The order carries it and the count is
        beside every row, so a position number would be a third copy of the
        same fact and the one a reader would quote as though the data asserted
        it. `search`'s results take the same line.
        """
        by_state: dict[str, list[tuple[int, str]]] = {}
        for (state, subject), questions in self.series.items():
            by_state.setdefault(state, []).append((questions, subject))

        rows: list[dict[str, object]] = []
        for state in sorted(by_state):
            ordered = sorted(by_state[state], key=lambda pair: (-pair[0], pair[1]))
            for questions, subject in ordered[: self.top_n]:
                rows.append(
                    {
                        "state": state,
                        "subject": subject,
                        "questions": questions,
                        # The state's whole attributable total and its distinct
                        # subject count travel with every row: a top-25 figure
                        # read without its denominator is a figure a reader will
                        # mistake for the state's whole record.
                        "state_questions": self.state_totals.get(state, 0),
                        "state_subjects": self.state_subject_counts.get(state, 0),
                        "subjects_shown": min(self.top_n, self.state_subject_counts.get(state, 0)),
                        # The prose lives once in `aggregates/counting-basis`.
                        "counting_basis_unit": BASIS_UNIT,
                        "basis_version": self.basis_version,
                    }
                )
        return rows

    def for_state(self, state: str) -> list[tuple[str, int]]:
        """One state's subjects, most questions first. For a test or a report."""
        items = [
            (subject, questions) for (st, subject), questions in self.series.items() if st == state
        ]
        return sorted(items, key=lambda pair: (-pair[1], pair[0]))


def state_subjects(
    questions: Iterable[Question],
    *,
    member_states: Mapping[str, str],
    top_n: int = DEFAULT_TOP_N,
    states_total: int | None = None,
) -> StateSubjects:
    """Tally subject lines per state, by the rule in this module's docstring.

    `member_states` comes from `states_by_member(constituencies)`.
    """
    if top_n < 1:
        raise ValueError("top_n MUST be at least 1; a top-0 summary is not a summary")

    series: dict[tuple[str, str], int] = {}
    totals: dict[str, int] = {}
    subjects_seen: dict[str, set[str]] = {}
    unattributable = 0
    multi_state = 0

    for question in questions:
        # A SET: a question asked by three members of one state is one question
        # for that state, which is rule 1.
        states = {
            member_states[member_id]
            for member_id in question.asking_members
            if member_id in member_states
        }
        if not states:
            # No identified asker holds a seat we know of, so there is no state
            # to attribute this to. Rule 3.
            unattributable += 1
            continue
        if len(states) > 1:
            multi_state += 1
        subject = question.subject
        for state in states:
            series[(state, subject)] = series.get((state, subject), 0) + 1
            totals[state] = totals.get(state, 0) + 1
            subjects_seen.setdefault(state, set()).add(subject)

    return StateSubjects(
        series=series,
        state_totals=totals,
        state_subject_counts={state: len(seen) for state, seen in subjects_seen.items()},
        unattributable=unattributable,
        multi_state=multi_state,
        top_n=top_n,
        counting_basis=state_subject_basis(
            unattributable=unattributable,
            multi_state=multi_state,
            states=states_total if states_total is not None else len(totals),
            top_n=top_n,
        ),
    )
