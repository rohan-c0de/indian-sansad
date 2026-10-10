"""T066 — the per-session frequency series for each subject.

`spec.md` User Story 4 acceptance scenario 2: "Given a subject, When a user
requests its trend, Then a per-session series is returned with the counting
basis stated."

**The unit is the question, counted once.** A question asked jointly by 47
members is one question on its subject's series, not 47. That is the single
thing a reader of these numbers can most easily get wrong — the by-member
partition republishes each joint question once per asker, so a reader who builds
a subject series from those files gets 1.63x the real figure. The basis carried
on every row says so.

**Subjects are reproduced as the source records them.** No stemming, no case
folding, no merging of near-identical subject lines. `route-capture.md` records
`subjects` as a single string per question, and two subjects differing by a word
are two subjects here. That makes the series reproducible by counting the
published records — which FR-012 and SC-007 require — and it means the series is
noisier than a human would group it. Grouping is a reader's judgement and would
not be reproducible; `tests/contract/test_aggregates.py` counts a series
independently of this module to prove the reproducibility rather than assert it.

**Unresolved questions are included.** A question whose asker could not be
identified still has a subject and a session, and excluding it would make the
subject totals disagree with the published question record. The basis states it.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from sansad.model.question import Question
from sansad.views.basis import BASIS_VERSION, question_basis

__all__ = ["SubjectTrends", "subject_trends"]


@dataclass(frozen=True, slots=True)
class SubjectTrends:
    """Per-subject, per-session question counts, with the basis."""

    #: (subject, session) -> question count.
    series: Mapping[tuple[str, str], int]
    counting_basis: str = field(default="")
    basis_version: str = BASIS_VERSION

    def as_rows(self) -> list[dict[str, object]]:
        """One published row per (subject, session).

        Sorted, so two refreshes over the same data produce a byte-identical
        file — the dataset is force-pushed as one commit and an unexplained
        reordering cannot be diffed against anything.
        """
        return [
            {
                "subject": subject,
                "session": session,
                "questions": self.series[(subject, session)],
                # The prose lives once in `aggregates/counting-basis`. Inline
                # it cost 179 MiB over 92,942 rows -- see views.basis.basis_rows.
                "counting_basis_unit": "question",
                "basis_version": self.basis_version,
            }
            for subject, session in sorted(self.series)
        ]

    def for_subject(self, subject: str) -> list[tuple[str, int]]:
        """One subject's series, session by session."""
        return [
            (session, count)
            for (subj, session), count in sorted(self.series.items())
            if subj == subject
        ]


def subject_trends(
    questions: Iterable[Question],
    *,
    unresolved: int | None = None,
    partly_resolved: int | None = None,
    co_asked: int | None = None,
    max_askers: int | None = None,
) -> SubjectTrends:
    """Count questions per (subject, session). One question counts once.

    The basis figures are passed through so a refresh states its own numbers
    rather than the ones true when the stamp was written. `None` lets them
    default; a caller with the real counts should supply them.
    """
    materialised = list(questions)
    series: dict[tuple[str, str], int] = {}
    for question in materialised:
        key = (question.subject, question.session)
        series[key] = series.get(key, 0) + 1

    return SubjectTrends(
        series=series,
        counting_basis=question_basis(
            unresolved=unresolved,
            partly_resolved=partly_resolved,
            co_asked=co_asked,
            max_askers=max_askers,
        ),
    )
