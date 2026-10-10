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
    """Sitting or former, as of the last refresh (`data-model.md` → Member).

    **Three values, not two** (owner decision 2026-10-09). `data-model.md` names
    "Sitting or former", and also requires: "Missing attributes MUST be
    represented as an explicit 'not stated' value, never silently dropped."
    The roster's `status` field was recorded by the spike as a field *name*
    only -- `spike/route-capture.md` records names, counts and sizes and holds
    no values -- so the vocabulary it uses is **UNVERIFIED**.

    With two values, an unrecognised `status` would have to be mapped to
    `sitting` or `former`, which invents a fact about a real person to avoid an
    empty cell. `NOT_STATED` is the alternative the data model already asks
    for, and it keeps User Story 4's composition breakdown able to show a
    "not stated" bucket instead of quietly shrinking its denominator.
    """

    SITTING = "sitting"
    FORMER = "former"
    #: The source did not record it, or recorded it in a form this project has
    #: never observed. Spelled out rather than referencing the module constant
    #: because `NOT_STATED = NOT_STATED` inside an enum body resolves by a
    #: scoping rule subtle enough to be read as a bug; the two are kept in step
    #: by the assertion below instead.
    NOT_STATED = "not stated"


# One spelling of "not stated" across the model, enforced rather than trusted:
# a view that filtered on the constant while the enum carried a different
# string would report an empty "not stated" bucket and look correct doing it.
assert SittingStatus.NOT_STATED.value == NOT_STATED


class ResolutionStatus(StrEnum):
    """The status shared by Question and Resolution Record.

    `data-model.md` gives the same three values for `Question.resolution_status`
    and `ResolutionRecord.status`. They are one vocabulary and are defined once.
    """

    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"
