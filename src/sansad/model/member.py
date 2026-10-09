"""The Member entity.

One person who has served during the covered period.

Validation rules, quoted verbatim from
`specs/001-resolved-metadata-layer/data-model.md` → Member:

- "`member_id` MUST be stable across refreshes and MUST NOT change when a name
  variant is added (FR-002)."
- "Two members with identical or near-identical names MUST NOT be merged;
  distinctness is decided on attributes beyond the name (FR-002, Edge Cases)."
- "A member whose party or House changes within the covered period MUST retain
  one `member_id` with the change represented in `terms`, not split into two
  identities (Edge Cases)."
- "Published fields MUST be limited to those above. Any further personal
  attribute available upstream MUST NOT appear unless a recorded decision
  authorises it (FR-008, SC-010)."
- "Missing attributes MUST be represented as an explicit 'not stated' value,
  never silently dropped (User Story 4 acceptance scenario 1)."

The last two are the ones with teeth. The upstream serves personal contact
details, home addresses, dates of birth, marital status and family composition
for 5,426 named people without authentication. `PUBLISHED_FIELDS` below is the
machine-readable form of "MUST be limited to those above", so that rule is
checkable rather than merely stated.
"""

from __future__ import annotations

from dataclasses import dataclass

from sansad.model._common import NOT_STATED, House, SittingStatus

#: The complete set of published Member fields.
#:
#: "Published fields MUST be limited to those above." This tuple IS "those
#: above" -- in the order data-model.md lists them -- so FR-008's bound is a
#: value the code can be tested against instead of a sentence in a document.
#: Adding a name here is a decision about what this project publishes about
#: 5,426 named people, and `sansad.ingest.field_allowlist` must agree.
PUBLISHED_FIELDS: tuple[str, ...] = (
    "member_id",
    "canonical_name",
    "name_variants",
    "house",
    "party",
    "state",
    "constituency",
    "terms",
    "sitting_status",
    "source_record_ref",
    "last_refreshed",
)


@dataclass(frozen=True, slots=True)
class Term:
    """One term served, with its own period.

    Terms carry `party` and `house` because of the Edge Case rule: "A member
    whose party or House changes within the covered period MUST retain one
    `member_id` with the change represented in `terms`, not split into two
    identities." A change is therefore represented by two Term records under
    one `member_id`, never by a second Member.
    """

    house: House
    #: Term number as the House numbers it (e.g. 17, 18 for Lok Sabha).
    number: int
    start_date: str
    end_date: str | None = None
    party: str = NOT_STATED
    constituency: str | None = None
    state: str = NOT_STATED


@dataclass(frozen=True, slots=True)
class Member:
    """One person who has served during the covered period."""

    #: "Stable internal identity. Assigned once, never reused, never derived
    #: from a name." Not derived from a name is load-bearing: a name-derived id
    #: would change when a variant is added, which the rule above forbids.
    member_id: str
    #: "One display form chosen per member."
    canonical_name: str
    #: "Every form the source record uses for this person."
    name_variants: tuple[str, ...]
    house: House
    party: str = NOT_STATED
    state: str = NOT_STATED
    #: "Lok Sabha members only; absent for Rajya Sabha." Absent means `None`
    #: here rather than NOT_STATED: a Rajya Sabha member has no constituency to
    #: state, which is a different fact from a Lok Sabha member whose
    #: constituency the source did not record.
    constituency: str | None = None
    terms: tuple[Term, ...] = ()
    sitting_status: SittingStatus = SittingStatus.SITTING
    #: "Identifier of the upstream record this was built from." An identifier,
    #: never the record -- no raw upstream payload inside the repository tree.
    source_record_ref: str = NOT_STATED
    last_refreshed: str = NOT_STATED

    def __post_init__(self) -> None:
        if not self.member_id:
            raise ValueError("member_id is required and MUST NOT be empty")
        if self.canonical_name in ("", None):
            raise ValueError(f"{self.member_id}: canonical_name MUST NOT be empty")
        if self.house is House.RAJYA_SABHA and self.constituency is not None:
            raise ValueError(
                f"{self.member_id}: constituency is absent for Rajya Sabha "
                f"members (data-model.md -> Member), got {self.constituency!r}"
            )

    @property
    def is_merge_candidate_by_name_alone(self) -> bool:
        """Always False. Named so the rule is visible at the call site.

        "Two members with identical or near-identical names MUST NOT be merged;
        distinctness is decided on attributes beyond the name." There is no
        name-similarity test on this entity, deliberately: the decision to
        treat two records as one person belongs to `sansad.resolve`, on
        attributes beyond the name, and never to the model.
        """
        return False
