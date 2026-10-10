"""The Session entity.

Note, quoted verbatim from
`specs/001-resolved-metadata-layer/data-model.md` → Session:

- "Lok Sabha and Rajya Sabha number sessions independently; `session_id` MUST
  be scoped by House so the two series are never conflated (Key Entities,
  House)."

`session_id` is therefore constructed, not accepted: `make_session_id` is the
only way to build one, so "scoped by House" cannot be forgotten at a call site.
A bare session number is rejected.
"""

from __future__ import annotations

from dataclasses import dataclass

from sansad.model._common import House

PUBLISHED_FIELDS: tuple[str, ...] = (
    "session_id",
    "house",
    "term",
    "number",
    "start_date",
    "end_date",
    "sitting_days",
)


def make_session_id(house: House, term: int, number: int) -> str:
    """Build a House- and term-scoped `session_id`.

    The two Houses number sessions independently, so "session 8" is not an
    identity -- `lok-sabha/8` and `rajya-sabha/8` are different sessions and
    MUST never be conflated.

    **`term` is part of the id, and that is a correction (2026-10-09).** The id
    was `house/number`, which conflates the two Lok Sabhas inside the covered
    window: the 17th and the 18th each number their sessions from 1, and both
    carry questions in sessions 2 through 8 -- **seven collisions**. A session
    reference set keyed on `house/number` would have published one record where
    two sessions exist, and `Question.session` already carried the term, so the
    two were not even joinable.

    Same class of defect as the `question_id` composite corrected on the same
    day, and found the same way: by building the set and counting it.
    """
    if number < 1:
        raise ValueError(f"session number MUST be positive, got {number}")
    if term < 1:
        raise ValueError(f"term number MUST be positive, got {term}")
    return f"{house.value}/{term}/{number}"


@dataclass(frozen=True, slots=True)
class Session:
    """One session of one House."""

    house: House
    #: Which Lok Sabha / Rajya Sabha this session belongs to. Part of the id --
    #: both covered terms number their sessions from 1.
    term: int
    #: "Session number as the House numbers it."
    number: int
    start_date: str
    end_date: str | None = None
    #: "Count, where known." None where the source does not record it -- this
    #: is a known gap for the Coverage Statement, not a zero.
    sitting_days: int | None = None

    @property
    def session_id(self) -> str:
        """ "House plus session number." Derived, so it cannot drift."""
        return make_session_id(self.house, self.term, self.number)

    def __post_init__(self) -> None:
        # Raises for a non-positive number via make_session_id.
        _ = self.session_id
        if self.sitting_days is not None and self.sitting_days < 0:
            raise ValueError(f"{self.session_id}: sitting_days MUST NOT be negative")
