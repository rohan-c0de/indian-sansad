"""Values shared across more than one entity in this package.

Why this module exists, given tasks.md names one file per entity: `House` is
referenced by Member, Question, Session and Coverage Statement, and
`data-model.md` requires that the two Houses' session series "are never
conflated". Four independently-defined copies of the House value is the most
direct route to exactly that conflation, so it is defined once here. The
leading underscore marks it as internal to `sansad.model`.
"""

from __future__ import annotations

from enum import StrEnum

#: The explicit "not stated" value.
#:
#: `data-model.md` (Member): "Missing attributes MUST be represented as an
#: explicit 'not stated' value, never silently dropped (User Story 4
#: acceptance scenario 1)."
#:
#: A sentinel string rather than `None`, because `None` is indistinguishable
#: from "we never looked" once serialised, and User Story 4's composition
#: breakdown has to be able to show a "not stated" bucket rather than quietly
#: shrinking its denominator.
NOT_STATED = "not stated"


class House(StrEnum):
    """Which House of Parliament.

    `data-model.md` (Session): "Lok Sabha and Rajya Sabha number sessions
    independently; `session_id` MUST be scoped by House so the two series are
    never conflated (Key Entities, House)."
    """

    LOK_SABHA = "lok-sabha"
    RAJYA_SABHA = "rajya-sabha"


class SittingStatus(StrEnum):
    """Sitting or former, as of the last refresh (`data-model.md` → Member)."""

    SITTING = "sitting"
    FORMER = "former"


class ResolutionStatus(StrEnum):
    """The status shared by Question and Resolution Record.

    `data-model.md` gives the same three values for `Question.resolution_status`
    and `ResolutionRecord.status`. They are one vocabulary and are defined once.
    """

    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"
