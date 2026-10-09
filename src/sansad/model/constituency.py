"""The Constituency entity.

Validation rule, quoted verbatim from
`specs/001-resolved-metadata-layer/data-model.md` → Constituency:

- "a constituency represented by different members across the two covered
  terms MUST list both with their periods, not merged (US3 scenario 3)."

The covered window spans two Lok Sabhas, so a seat changing hands between them
is the ordinary case rather than the exception. Merging the two would make the
constituency entry point -- User Story 3's whole premise, that a visitor can
start from their own seat -- answer with one member's record where two are
owed.
"""

from __future__ import annotations

from dataclasses import dataclass

from sansad.model._common import NOT_STATED

PUBLISHED_FIELDS: tuple[str, ...] = ("constituency_id", "name", "state", "representations")


@dataclass(frozen=True, slots=True)
class Representation:
    """One member's period representing a constituency.

    A pair, not a single current holder: "MUST list both with their periods,
    not merged."
    """

    member_id: str
    start_date: str
    end_date: str | None = None
    #: Term number as the House numbers it, so a reader can see which of the
    #: two covered terms this representation belongs to.
    term_number: int | None = None


@dataclass(frozen=True, slots=True)
class Constituency:
    """One constituency, with every representation inside the covered window."""

    constituency_id: str
    name: str
    state: str = NOT_STATED
    #: "Member and period pairs within the covered window." Plural, always.
    representations: tuple[Representation, ...] = ()

    def __post_init__(self) -> None:
        if not self.constituency_id:
            raise ValueError("constituency_id is required and MUST NOT be empty")
        seen = [(r.member_id, r.start_date) for r in self.representations]
        if len(set(seen)) != len(seen):
            raise ValueError(
                f"{self.constituency_id}: duplicate representation in "
                f"{seen!r}. Representations are listed, not merged (US3 scenario 3)."
            )

    @property
    def changed_hands_in_window(self) -> bool:
        """True when more than one member represented this seat in the window."""
        return len({r.member_id for r in self.representations}) > 1
