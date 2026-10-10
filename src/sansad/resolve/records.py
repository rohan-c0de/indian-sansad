"""T049 -- one Resolution Record per name form encountered (FR-005).

> for every published join a Resolution Record exists giving the name form as
> written and the source record reference. The check recomputes nothing; it
> confirms a consumer could audit the join without re-deriving it.
> -- `quickstart.md` scenario 4

Three properties, each with a reason it is not merely nice to have.

**Per name form encountered, not per resolved join.** An unresolvable asker
gets a record too. FR-004 keeps the question; without a record saying which
written form failed and against what, a consumer sees `unresolved` and has
nothing to check. `contracts/published-dataset.md` guarantee 2 promises the
question survives; this is what makes its status auditable.

**The form is stored exactly as written.** Not normalised, not tidied. "An
audit record of what was matched is useless if it stores the cleaned-up version
of the thing that needed matching."

**The tier is recorded per join.** `spike/resolution-rate.md` measured that
`approximate` resolved **nothing** on the 18th Lok Sabha and 18 forms / 3,465
instances on the 17th, and `token-containment` carries 19 forms. Without the
tier on each join neither figure is recoverable from the published record, and
the owner's SC-002 decision rests on exactly that breakdown. `manual-assertion`
is recorded for the same reason, one level up: T053 publishes the automatic rate
separately, and a join cannot be counted into the right rate unless it says
which kind it is.

**A note on `source_record_ref`.** It is where the form was *encountered* -- the
question record -- not where the member was found. A consumer verifying a join
needs to get back to the question that carried the name, and the member side is
reachable from `member_id` through the published member reference set.
"""

from __future__ import annotations

from collections.abc import Mapping

from sansad.model._common import NOT_STATED, ResolutionStatus
from sansad.model.resolution_record import AssertedBy, ResolutionMethod, ResolutionRecord
from sansad.resolve.match import MatchOutcome

__all__ = ["record_for", "records_for"]


def record_for(
    name_as_written: str,
    outcome: MatchOutcome,
    *,
    source_record_ref: str = NOT_STATED,
) -> ResolutionRecord:
    """Build the audit record for one written form and its outcome.

    `asserted_by` is derived from the method rather than passed in: the two
    must agree (`ResolutionRecord` refuses them when they do not), and deriving
    it removes the only way for a caller to label a maintainer correction as
    automatic -- which would quietly inflate the automatic rate T053 publishes.
    """
    status = outcome.status
    method = outcome.method
    is_manual = method is ResolutionMethod.MANUAL_ASSERTION

    return ResolutionRecord(
        name_as_written=name_as_written,
        # Ambiguous carries no member_id: populating it IS the collapse to one
        # candidate that Edge Cases forbids.
        member_id=(
            outcome.member_ids[0]
            if status is ResolutionStatus.RESOLVED and outcome.member_ids
            else None
        ),
        status=status,
        # None only for `unresolved` -- no tier produced it. The entity
        # enforces that; this is where it arises.
        method=method,
        candidates=(outcome.member_ids if status is ResolutionStatus.AMBIGUOUS else ()),
        source_record_ref=source_record_ref or NOT_STATED,
        asserted_by=AssertedBy.MAINTAINER if is_manual else AssertedBy.AUTOMATIC,
    )


def records_for(
    outcomes: Mapping[str, MatchOutcome],
    refs: Mapping[str, str] | None = None,
) -> tuple[ResolutionRecord, ...]:
    """One record per distinct written form, in sorted form order.

    Distinct **forms**, not instances: the same written form appearing on 513
    questions resolves once and is audited once, which is how the spike counted
    and how the correction worklist is ordered. The per-question join is
    recoverable by matching a question's asker form back to its record.

    Sorted so two refreshes over the same data produce byte-identical output --
    the published dataset is force-pushed as a single commit and a reordered
    file is an unexplained diff.
    """
    refs = refs or {}
    return tuple(
        record_for(form, outcome, source_record_ref=refs.get(form, NOT_STATED))
        for form, outcome in sorted(outcomes.items())
    )
