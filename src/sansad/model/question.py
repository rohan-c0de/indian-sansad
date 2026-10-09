"""The Question entity.

One question put to a ministry.

Validation rules, quoted verbatim from
`specs/001-resolved-metadata-layer/data-model.md` → Question:

- "A co-asked question MUST carry every asking member and MUST NOT be
  duplicated per asker (FR-003, US1 scenario 2)."
- "A question whose asker cannot be resolved MUST be retained with
  `resolution_status` set to `ambiguous` or `unresolved`, and MUST NOT be
  dropped or assigned a guessed member (FR-004, US1 scenario 3)."
- "A question dated outside the covered window MUST be excluded, and its
  exclusion reflected in the Coverage Statement rather than passing silently
  (FR-013)."
- "A question attributed to a member not sitting on its date MUST be flagged
  rather than silently re-attributed (Edge Cases)."
- "Answer text is explicitly **not** part of this entity. No document file is
  opened (FR-015)."

The last rule is why this module has no answer field and no field that could
hold one. FR-015 is not a preference about scope: opening the answer documents
is the step that would put the project's cost and upkeep outside both
Principle I and Principle II.

The co-asking rule is also what makes resolution rates non-additive. A question
resolves only when *all* its askers resolve (FR-003), which is why the spike
had to re-walk all 95,269 records to compute the effect of four assertions
rather than summing their per-form figures -- 1,409 recovered, not the naive
sum of 1,572.
"""

from __future__ import annotations

from dataclasses import dataclass

from sansad.model._common import NOT_STATED, House, ResolutionStatus

PUBLISHED_FIELDS: tuple[str, ...] = (
    "question_id",
    "house",
    "session",
    "date",
    "type",
    "subject",
    "ministry_id",
    "asking_members",
    "resolution_status",
    "source_record_ref",
    "last_refreshed",
)


@dataclass(frozen=True, slots=True)
class Question:
    """One question put to a ministry.

    Answer text is explicitly **not** part of this entity.
    """

    question_id: str
    house: House
    #: Session it belongs to -- a House-scoped `session_id`, never a bare
    #: number, because the two Houses number sessions independently.
    session: str
    date: str
    #: "Question type as recorded (e.g. starred, unstarred)."
    type: str
    subject: str
    ministry_id: str
    #: "One or more `member_id` values, or empty with `resolution_status` set."
    #:
    #: One Question record carries every asker. The question is NOT duplicated
    #: per asker -- duplicating it is how a per-member count silently becomes a
    #: question count.
    asking_members: tuple[str, ...] = ()
    resolution_status: ResolutionStatus = ResolutionStatus.UNRESOLVED
    source_record_ref: str = NOT_STATED
    last_refreshed: str = NOT_STATED
    #: Set when "a question attributed to a member not sitting on its date"
    #: is found. Flagged, never silently re-attributed -- the attribution
    #: stands as the source gave it and the flag travels with it.
    flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.question_id:
            raise ValueError("question_id is required and MUST NOT be empty")

        # "A question whose asker cannot be resolved MUST be retained with
        # `resolution_status` set to `ambiguous` or `unresolved`, and MUST NOT
        # be dropped or assigned a guessed member."
        #
        # The model cannot stop a caller dropping a record, but it can refuse
        # the two incoherent shapes that would let a drop or a guess pass as
        # resolved: resolved-with-no-askers, and unresolved-presented-as-fact.
        if self.resolution_status is ResolutionStatus.RESOLVED and not self.asking_members:
            raise ValueError(
                f"{self.question_id}: resolution_status is 'resolved' with no "
                f"asking_members. An unresolvable asker MUST be retained with "
                f"status 'ambiguous' or 'unresolved' (data-model.md -> Question), "
                f"never recorded as resolved to nobody."
            )
        if len(set(self.asking_members)) != len(self.asking_members):
            raise ValueError(
                f"{self.question_id}: asking_members contains a duplicate "
                f"{self.asking_members!r}. A co-asked question MUST NOT be "
                f"duplicated per asker (FR-003)."
            )

    @property
    def is_co_asked(self) -> bool:
        """True when more than one member asked this question."""
        return len(self.asking_members) > 1

    @property
    def counts_as_resolved(self) -> bool:
        """Whether this question counts toward the SC-002 resolution rate.

        A question resolves only when every asker resolves. This property is
        the single definition of that, so a view cannot arrive at a different
        resolution rate from the published one by counting it its own way.
        """
        return self.resolution_status is ResolutionStatus.RESOLVED
