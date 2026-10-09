"""The Resolution Record entity.

The audit link between a written name form and the identity it resolved to.
This entity exists so FR-005 is satisfiable.

Validation rules, quoted verbatim from
`specs/001-resolved-metadata-layer/data-model.md` → Resolution Record:

- "Every join in the published record MUST have a corresponding Resolution
  Record enabling independent verification (FR-005)."
- "A manual assertion MUST survive subsequent refreshes and MUST NOT be
  overwritten by automatic matching (implied by FR-009 + FR-011: unattended
  refresh must not undo maintainer corrections)."
- "`ambiguous` MUST list its candidates; an ambiguous match MUST NOT be
  silently collapsed to the first candidate (Edge Cases)."

The `method` field carries **all six** values the matcher can produce, so any
join shows which tier produced it (FR-005). That matters concretely rather
than abstractly: the spike measured that `approximate` resolved **nothing** on
the 18th Lok Sabha and 18 forms / 3,465 instances on the 17th, and
`token-containment` carries 19 forms. Without the tier recorded per join,
neither figure is recoverable from the published record, and the owner's SC-002
decision -- which rests on exactly that breakdown -- would not be externally
checkable.

`manual-assertion` is a `method` value for the same reason: four assertions are
load-bearing for SC-002 (96.26% assisted against 94.78% automatic), and T053
requires the automatic rate be published separately. A join cannot be counted
into the right rate unless it says which kind it is.
"""

from __future__ import annotations

from dataclasses import dataclass

from sansad.model._common import NOT_STATED, ResolutionStatus
from sansad.model._common import ResolutionStatus as Status  # readability alias

__all__ = [
    "MANUAL_METHODS",
    "ResolutionMethod",
    "ResolutionRecord",
    "Status",
]

from enum import StrEnum


class ResolutionMethod(StrEnum):
    """How a name form was resolved. One of **six** values.

    These match the tiers T046 implements, in the order the matcher tries
    them, so a join's method also records how much work it took.
    """

    #: The written form equals a known form exactly.
    EXACT = "exact"
    #: Equal after normalisation (case, punctuation, honorifics, whitespace).
    NORMALISED = "normalised"
    #: Equal after normalisation and token reordering -- e.g. the roster's
    #: "Tatkare Sunil Dattatrey" against the question route's
    #: "Sunil Dattatray Tatkare".
    NORMALISED_REORDERED = "normalised-reordered"
    #: difflib.SequenceMatcher.ratio on normalised forms at
    #: APPROX_THRESHOLD = 0.90, APPROX_MARGIN = 0.02. Resolved 0 forms on the
    #: 18th Lok Sabha and 18 forms / 3,465 instances on the 17th.
    APPROXIMATE = "approximate"
    #: Bidirectional token containment -- one form's token set is a strict
    #: subset of the other's. Adopted by owner decision 2026-10-09 after
    #: holdout validation on 15,082 unseen questions (+6.31 points, against
    #: +6.35 on the derivation data: no measurable overfitting).
    #:
    #: NOT an alias handler. Three of its 19 matches are parenthetical aliases
    #: it catches incidentally, by coincidence of token sets; aliases remain
    #: among the residual forms and any alias rule needs its own evidence and
    #: its own holdout.
    TOKEN_CONTAINMENT = "token-containment"
    #: A maintainer assertion. Survives refreshes; never overwritten by
    #: automatic matching.
    MANUAL_ASSERTION = "manual-assertion"


#: The methods that represent human judgement rather than automatic matching.
#:
#: T053 requires the automatic resolution rate be published alongside the
#: assisted one, so the project's dependence on hand corrections is visible to
#: consumers instead of blended away. This set is how a counting routine tells
#: the two apart.
MANUAL_METHODS: frozenset[ResolutionMethod] = frozenset({ResolutionMethod.MANUAL_ASSERTION})


class AssertedBy(StrEnum):
    """Who produced this record."""

    AUTOMATIC = "automatic"
    MAINTAINER = "maintainer"


@dataclass(frozen=True, slots=True)
class ResolutionRecord:
    """The audit link between a written name form and the identity it got."""

    #: "The exact form found in the source." Exact -- not normalised, not
    #: tidied. An audit record of what was matched is useless if it stores the
    #: cleaned-up version of the thing that needed matching.
    name_as_written: str
    #: "Identity resolved to, or empty."
    member_id: str | None
    status: ResolutionStatus
    method: ResolutionMethod
    #: "For `ambiguous`, the member identities that matched equally well."
    candidates: tuple[str, ...] = ()
    #: "Where the name form was encountered." A reference, never the record.
    source_record_ref: str = NOT_STATED
    asserted_by: AssertedBy = AssertedBy.AUTOMATIC

    def __post_init__(self) -> None:
        if not self.name_as_written:
            raise ValueError("name_as_written is required: an audit record of nothing is not one")

        # "`ambiguous` MUST list its candidates; an ambiguous match MUST NOT be
        # silently collapsed to the first candidate."
        if self.status is ResolutionStatus.AMBIGUOUS:
            if len(self.candidates) < 2:
                raise ValueError(
                    f"{self.name_as_written!r}: status 'ambiguous' MUST list its "
                    f"candidates, got {self.candidates!r}. An ambiguous match MUST "
                    f"NOT be silently collapsed to the first candidate (Edge Cases)."
                )
            if self.member_id is not None:
                raise ValueError(
                    f"{self.name_as_written!r}: status 'ambiguous' with "
                    f"member_id={self.member_id!r} IS the silent collapse to one "
                    f"candidate that Edge Cases forbids."
                )

        if self.status is ResolutionStatus.RESOLVED and not self.member_id:
            raise ValueError(
                f"{self.name_as_written!r}: status 'resolved' requires a member_id. "
                f"A resolved join with no identity cannot satisfy FR-005."
            )
        if self.status is ResolutionStatus.UNRESOLVED and self.member_id:
            raise ValueError(
                f"{self.name_as_written!r}: status 'unresolved' MUST NOT carry "
                f"member_id={self.member_id!r} -- that is a guessed member (FR-004)."
            )

        # A manual assertion and an automatic match are not interchangeable
        # labels: T053's separate automatic rate depends on the pairing holding.
        if self.method is ResolutionMethod.MANUAL_ASSERTION:
            if self.asserted_by is not AssertedBy.MAINTAINER:
                raise ValueError(
                    f"{self.name_as_written!r}: method 'manual-assertion' MUST be "
                    f"asserted_by 'maintainer', got {self.asserted_by.value!r}."
                )
        elif self.asserted_by is AssertedBy.MAINTAINER:
            raise ValueError(
                f"{self.name_as_written!r}: asserted_by 'maintainer' requires "
                f"method 'manual-assertion', got {self.method.value!r}."
            )

    @property
    def is_manual(self) -> bool:
        """Whether this join came from human judgement (T053's separate rate)."""
        return self.method in MANUAL_METHODS
