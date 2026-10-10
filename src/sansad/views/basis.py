"""T064 — the counting-basis stamp every aggregate carries (FR-012, SC-007).

FR-012 requires a published count to state its basis **alongside the numbers**,
and SC-007 requires the count be reproducible by hand from the published
records. Those two are one requirement: a figure you cannot reproduce is a
figure whose basis you were not told.

**Written for a visitor, not for a maintainer.** The basis is published text in
the dataset, so it says what was counted in words someone can read without this
repository open. It names the three things that would otherwise make an honest
reader reach a different number from the same files:

1. **What the unit is** — questions, or members. A ministry's "1,000" means
   nothing until you know whether it counts questions or question-asker pairs.
2. **That a co-asked question counts ONCE.** The live window has **23,385
   co-asked questions (24.5%), with up to 47 askers on one question**, and the
   by-member partition republishes each of them once per asker. Someone summing
   the by-member files gets 155,003 -- 1.63x the true total. This is also
   `contracts/published-dataset.md` guarantee 6, stated where the numbers are
   rather than only in the contract.
3. **How unresolved and partly resolved questions are treated.** The live window
   has **3,472 unresolved questions, of which 1,231 are *partly* resolved** —
   status `unresolved`, but the askers that did resolve are retained. Those 1,231
   are in a member's file *and* counted as unresolved, which is the one case a
   reader cannot guess. Leaving it implicit is how two correct-looking totals
   disagree.

The figures above are from the 2026-10-10 live window and are quoted in the
stamp itself, because a basis that describes the shape of the data without
saying how much of it there is leaves the reader to find out.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "BASIS_VERSION",
    "CountingBasis",
    "basis_rows",
    "member_basis",
    "question_basis",
]

#: Bumped when the wording changes in a way that changes what the numbers mean.
#: Published with the basis so a consumer comparing two refreshes can tell a
#: changed definition from a changed dataset.
BASIS_VERSION = "1"


@dataclass(frozen=True, slots=True)
class CountingBasis:
    """One basis stamp: the prose, its version, and the unit counted."""

    unit: str
    text: str
    version: str = BASIS_VERSION


def question_basis(
    *,
    unresolved: int | None = None,
    partly_resolved: int | None = None,
    co_asked: int | None = None,
    max_askers: int | None = None,
) -> str:
    """The basis for any count whose unit is a **question**.

    The counts are parameters so a refresh states its own figures rather than
    the ones that happened to be true when this was written. They default to
    the 2026-10-10 live window, and a caller that has the real numbers should
    pass them.
    """
    unresolved = 3_472 if unresolved is None else unresolved
    partly_resolved = 1_231 if partly_resolved is None else partly_resolved
    co_asked = 23_385 if co_asked is None else co_asked
    max_askers = 47 if max_askers is None else max_askers

    return (
        "What is counted: QUESTIONS, not question-asker pairs. "
        "A question asked jointly by several members counts ONCE, not once per "
        f"asker. {co_asked:,} questions in this window were asked jointly, one of "
        f"them by {max_askers} members. The by-member files republish each joint "
        "question once per asker, so adding those files up gives a larger number "
        "than there are questions; de-duplicate on question_id before totalling "
        "anything across them. "
        f"Unresolved questions: {unresolved:,} questions in this window could not "
        "be attached to a member with confidence. They are INCLUDED in every "
        "count of questions here, because dropping them would make the totals "
        f"disagree with the published record. Of those, {partly_resolved:,} are "
        "PARTLY resolved: some of their askers were identified and some were not. "
        "A partly resolved question appears in the files of the askers who were "
        "identified AND is still counted as unresolved -- so a per-member total "
        "and the unresolved total deliberately overlap, and adding them is wrong. "
        "Counts of members never include a member twice."
    )


def member_basis(*, not_stated_is_a_category: bool = True) -> str:
    """The basis for any count whose unit is a **member**."""
    tail = (
        "A member whose party or state the source does not record is counted "
        "under an explicit 'not stated' category, never left out. So the "
        "categories always add up to the stated total membership for the term. "
        if not_stated_is_a_category
        else ""
    )
    return (
        "What is counted: MEMBERS, once each. A member who served in more than "
        "one of the covered terms is counted once in each term they served, and "
        "once only within a term. "
        + tail
        + "Only party, state and number of terms served are broken down; no other "
        "personal attribute is published or counted here, and publishing one "
        "would require a recorded decision. "
        "'Number of terms served' counts every Lok Sabha the source records for "
        "that member, including terms outside this dataset's covered window."
    )


def basis_rows(
    *,
    unresolved: int | None = None,
    partly_resolved: int | None = None,
    co_asked: int | None = None,
    max_askers: int | None = None,
) -> list[dict[str, object]]:
    """The basis stamps as published records -- one per unit counted.

    **Why the prose is published ONCE per unit rather than on every row.**
    Measured: carrying the question basis inline on all 92,942 subject-trend
    rows cost **179 MiB of the 195 MiB** the aggregates added -- 91% of them, to
    repeat one sentence 92,942 times, taking the dataset from 225 MiB to 420 MiB
    and from 22% to 41% of the 1 GiB Pages ceiling.

    So every aggregate row instead carries `counting_basis_unit` and
    `basis_version`, which name the row of this set that applies to it. The
    basis is published in the same directory as the numbers it describes, and
    FR-012's requirement that the basis be stated alongside the numbers is met
    by a reference that always resolves rather than by 179 MiB of duplication.
    A consumer reading one aggregate row needs one extra small file.

    `basis_version` is on every row deliberately: it is what lets a consumer
    comparing two refreshes tell a changed definition from a changed dataset,
    and it is two bytes.
    """
    return [
        {
            "unit": "question",
            "basis_version": BASIS_VERSION,
            "counting_basis": question_basis(
                unresolved=unresolved,
                partly_resolved=partly_resolved,
                co_asked=co_asked,
                max_askers=max_askers,
            ),
        },
        {
            "unit": "member",
            "basis_version": BASIS_VERSION,
            "counting_basis": member_basis(),
        },
    ]
