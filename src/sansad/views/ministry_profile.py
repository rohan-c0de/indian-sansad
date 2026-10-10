"""T070 — the per-ministry x per-session profile: counts, type mix, link status.

**Precomputed, not browser-computed.** `research.md` records that fetching
~10^5 records into a page is not viable, and the window is 95,268 questions. A
page that computed a ministry profile in the browser would have to download the
ministry's whole partition first — 823 KiB for the largest, per T019 — and then
do the work a refresh could have done once.

## The resolution-status split, and why the aggregate carries it

Owner decision 2026-10-10 (T070). The split is **fully linked**, **partly
linked** (at least one asking member identified and at least one not) and **not
linked** (none identified). The reason it belongs here rather than in the page:

> T078 requires unresolved and ambiguous questions to be visibly flagged rather
> than filtered out of the counts (FR-004, FR-012), and an aggregate that
> carries the total but not the split forces the page to re-derive the flags
> outside the T064 basis stamp and outside T073's contract test.

**"Partly linked" is the category a reader cannot guess.**
`sansad.resolve.status_for_question` sets a co-asked question to `unresolved`
while **keeping the askers that did resolve**, so such a question appears in
those members' files *and* counts as unresolved. Over the live window there are
1,231 of them against 3,472 unresolved in total. Without the split, a page
showing "3,472 unresolved" next to per-member files containing some of them
presents two correct numbers that look contradictory.

## A fourth count, so the sum holds

`data-model.md` gives `resolution_status` three values, and **`ambiguous` is
one of them** — but it does not occur in the live window: every residual form
came out `unresolved`, and `resolution-rate.md` records the `ambiguous` column
as 0 in every table, for both terms and both candidate pools.

T070's wording says "three ways", written when that was the whole of the data.
Taking it literally would mean an ambiguous question had nowhere to go, and
since `sansad.resolve` publishes **no** `asking_members` for an ambiguous
question (listing one would be the collapse `data-model.md` forbids), it would
silently fall into "not linked" — which is a different claim: "nobody was
identified" rather than "several people matched equally and the tie was not
broken".

So there is a **fourth count, `ambiguous`**, per the owner's instruction to add
one if the data model already has the status. `STATUS_COUNT_FIELDS` is the
machine-readable list and the invariant asserted in T073 is that **the sum of
all of them equals the question count** — which survives a fifth bucket if the
model ever grows one, where asserting three names would not.

## What this module does not do

It does not order sessions by date. Every `start_date` in the published session
reference set is `"not stated"` — all 21 rows — so a chronological ordering
would have to be invented. Rows are keyed by `session_id`, which carries House,
term and number, and ordering is the consumer's business.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from sansad.model._common import ResolutionStatus
from sansad.model.question import Question
from sansad.views.basis import BASIS_VERSION

__all__ = [
    "STATUS_COUNT_FIELDS",
    "MinistryProfile",
    "ministry_profiles",
]

#: Every resolution-status bucket a profile row carries. The T073 invariant is
#: that these **sum** to the row's question count -- asserted on the sum, not on
#: the three names, so it survives this tuple growing.
STATUS_COUNT_FIELDS: tuple[str, ...] = (
    "fully_linked",
    "partly_linked",
    "not_linked",
    "ambiguous",
)


@dataclass(frozen=True, slots=True)
class MinistryProfile:
    """One ministry's profile for one session."""

    ministry_id: str
    session: str
    questions: int
    #: Question type (as the source records it) -> count. Sums to `questions`.
    question_type_mix: Mapping[str, int]
    fully_linked: int
    partly_linked: int
    not_linked: int
    ambiguous: int

    def as_row(self) -> dict[str, object]:
        return {
            "ministry_id": self.ministry_id,
            "session": self.session,
            "questions": self.questions,
            "question_type_mix": dict(self.question_type_mix),
            "fully_linked": self.fully_linked,
            "partly_linked": self.partly_linked,
            "not_linked": self.not_linked,
            "ambiguous": self.ambiguous,
            # The prose lives once in `aggregates/counting-basis`; see
            # `views.basis.basis_rows` for the measured reason.
            "counting_basis_unit": "question",
            "basis_version": BASIS_VERSION,
        }


def _bucket(question: Question) -> str:
    """Which status bucket one question falls in.

    Order matters: `ambiguous` is tested **before** the asker check, because an
    ambiguous question deliberately publishes no `asking_members` and would
    otherwise be counted as "nobody was identified".
    """
    if question.resolution_status is ResolutionStatus.RESOLVED:
        return "fully_linked"
    if question.resolution_status is ResolutionStatus.AMBIGUOUS:
        return "ambiguous"
    if question.asking_members:
        return "partly_linked"
    return "not_linked"


def ministry_profiles(questions: Iterable[Question]) -> tuple[MinistryProfile, ...]:
    """One profile per (ministry, session), sorted.

    Sorted so two refreshes over the same data produce a byte-identical file:
    the dataset is force-pushed as a single commit, and a reordered file is a
    diff nobody can read.
    """
    counts: dict[tuple[str, str], dict[str, int]] = {}
    mixes: dict[tuple[str, str], dict[str, int]] = {}

    for question in questions:
        key = (question.ministry_id, question.session)
        bucket = counts.setdefault(key, dict.fromkeys(STATUS_COUNT_FIELDS, 0))
        bucket[_bucket(question)] += 1
        mix = mixes.setdefault(key, {})
        mix[question.type] = mix.get(question.type, 0) + 1

    out: list[MinistryProfile] = []
    for key in sorted(counts):
        ministry_id, session = key
        bucket = counts[key]
        total = sum(bucket.values())
        out.append(
            MinistryProfile(
                ministry_id=ministry_id,
                session=session,
                questions=total,
                question_type_mix=dict(sorted(mixes[key].items())),
                fully_linked=bucket["fully_linked"],
                partly_linked=bucket["partly_linked"],
                not_linked=bucket["not_linked"],
                ambiguous=bucket["ambiguous"],
            )
        )
    return tuple(out)
