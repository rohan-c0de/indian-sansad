"""T048 -- maintainer assertions. The four that carry SC-002.

`data-model.md` -> Resolution Record: "A manual assertion MUST survive
subsequent refreshes and MUST NOT be overwritten by automatic matching
(implied by FR-009 + FR-011: unattended refresh must not undo maintainer
corrections)."

**Why `data/assertions/` sits outside `data/published/`.** `data/published/` is
a build output: git-ignored on `main` and rewritten wholesale on every refresh,
force-pushed as a single commit to the orphan branch (owner decision
2026-10-09). An assertion is an **input**. Putting it under the output
directory would mean an unattended refresh deleted the maintainer's corrections
and then reported a lower resolution rate as though the matcher had regressed.

**What these four are, and are not.** `spike/spike-report.md` lists five
proposed pairs, ranked by questions blocked -- "the largest-value corrections
available". Four were **CONFIRMED BY OWNER**; row 4,
`Poonam (Mahajan) Vajendla Rao`, was **DROPPED BY OWNER**, with no reason
recorded and none inferred. The spike's table is marked PROPOSED, and "an
unconfirmed row is not an assertion", so only the confirmed four are seeded.

**They are what carries SC-002, and that is a stated dependency rather than a
footnote.**

| | Resolved | Rate | vs 95% |
|---|---|---|---|
| Matcher with the containment tier, no assertions | 90,299 / 95,269 | **94.78%** | fails by 0.22 |
| **+ these four assertions** | **91,796 / 95,268** | **96.36%** | **met, +1.36 points** |

The automatic rate is **below** the target. T053 publishes both figures
separately for exactly that reason: a single blended number would present four
hand corrections as matcher performance, and would hide a future matcher
regression behind them.

**Recovered: 1,498 questions.** 1,411 where one assertion unblocks the
question, plus **87 co-asked by two of the four, which resolve only when both
are applied**. The per-form figures are not additive -- a question resolves
only when *all* its askers do (FR-003).

**This corrects the spike's published 1,409 / 96.26%** (2026-10-09). That
recount scored one asserted form at a time, which cannot reach the 87. Two
questions of the 89-question difference are **not explained**: the code that
produced 1,409 was never committed, so they cannot be traced to a line. See
`spike/matcher-equivalence.md`.

The denominator is **95,268 distinct questions**, not 95,269 records: the
upstream serves one record of the window twice and it is reduced to one, with
the drop declared as a known gap (FR-013).

**Cost**: 4 x the 3-minute measured median = **12 minutes**, one time.
Correcting the remaining 21 residual forms is optional (~63 min).
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from sansad.model._common import NOT_STATED, ResolutionStatus
from sansad.model.resolution_record import ResolutionMethod
from sansad.resolve.match import MatchOutcome

__all__ = [
    "ASSERTIONS_DIR",
    "DROPPED_BY_OWNER",
    "Assertion",
    "apply_assertion",
    "assertions_dir",
    "load_assertions",
]

#: Rejected by the owner on 2026-10-09 and therefore never seeded.
#:
#: Named here, not merely absent, so re-adding it is a deliberate act rather
#: than something a later pass could do by reading the spike's PROPOSED table
#: and taking all five rows. The form stays among the residual forms with its
#: 292 blocked questions.
DROPPED_BY_OWNER: frozenset[str] = frozenset({"Poonam (Mahajan) Vajendla Rao"})


def assertions_dir() -> Path:
    """`data/assertions/` at the repository root."""
    return Path(__file__).resolve().parents[3] / "data" / "assertions"


#: Convenience for callers that want the path without calling the function.
ASSERTIONS_DIR = assertions_dir()


@dataclass(frozen=True, slots=True)
class Assertion:
    """One maintainer-confirmed join between a written form and an identity."""

    #: "its `name_as_written` exactly as the question route serves it" (T048).
    #: Exact, because this is the key the matcher's input is compared against
    #: -- a tidied form would never match the thing it was written to fix.
    name_as_written: str
    member_id: str
    #: Why the owner confirmed it. Required: an assertion with no recorded
    #: basis cannot be reviewed, and these four are load-bearing for SC-002.
    basis: str
    house: str = "lok-sabha"
    #: The roster form it was matched to, for a reviewer's benefit.
    roster_name_form: str = NOT_STATED
    constituency: str = NOT_STATED
    state: str = NOT_STATED
    #: How many questions this one form blocked when it was confirmed. A
    #: snapshot, not a live figure.
    questions_blocked: int | None = None
    confirmed_on: str = NOT_STATED
    source_file: str = NOT_STATED

    def __post_init__(self) -> None:
        if not self.name_as_written.strip():
            raise ValueError("an assertion needs the name form as written")
        if not self.member_id.strip():
            raise ValueError(
                f"{self.name_as_written!r}: an assertion needs a member_id. An "
                f"assertion to nobody is not a correction."
            )
        if not self.basis.strip():
            raise ValueError(
                f"{self.name_as_written!r}: an assertion needs a recorded basis. "
                f"These corrections are what carries SC-002 over its target; one "
                f"nobody can review is not reviewable evidence."
            )
        if self.name_as_written in DROPPED_BY_OWNER:
            raise ValueError(
                f"{self.name_as_written!r} was DROPPED BY THE OWNER on 2026-10-09 "
                f"and MUST NOT be seeded as an assertion. It stays among the "
                f"residual forms (spike/spike-report.md)."
            )


def load_assertions(directory: Path | None = None) -> dict[str, Assertion]:
    """Load every assertion file in `directory`, keyed by `name_as_written`.

    An absent directory is an empty mapping -- a project with no corrections
    yet is a valid state. A **malformed** file is not: it raises, rather than
    being skipped, because a silently-skipped assertion file looks exactly like
    a matcher regression on the next refresh.
    """
    root = directory if directory is not None else assertions_dir()
    if not root.is_dir():
        return {}

    loaded: dict[str, Assertion] = {}
    for path in sorted(root.glob("*.json")):
        body = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(body, Mapping):
            raise ValueError(f"{path}: expected an object carrying 'assertions'")
        rows = body.get("assertions") or []
        house = str(body.get("house") or "lok-sabha")
        confirmed_on = str(body.get("confirmed_on") or NOT_STATED)
        for row in rows:
            assertion = Assertion(
                name_as_written=str(row["name_as_written"]),
                member_id=str(row["member_id"]),
                basis=str(row.get("basis") or ""),
                house=str(row.get("house") or house),
                roster_name_form=str(row.get("roster_name_form") or NOT_STATED),
                constituency=str(row.get("constituency") or NOT_STATED),
                state=str(row.get("state") or NOT_STATED),
                questions_blocked=row.get("questions_blocked"),
                confirmed_on=str(row.get("confirmed_on") or confirmed_on),
                source_file=path.name,
            )
            previous = loaded.get(assertion.name_as_written)
            if previous is not None and previous.member_id != assertion.member_id:
                raise ValueError(
                    f"{assertion.name_as_written!r} is asserted to both "
                    f"{previous.member_id!r} ({previous.source_file}) and "
                    f"{assertion.member_id!r} ({path.name}). Two maintainer "
                    f"assertions disagreeing is a correction to make by hand, not "
                    f"one for this loader to pick a winner from."
                )
            loaded[assertion.name_as_written] = assertion
    return loaded


def apply_assertion(
    form: str,
    automatic: MatchOutcome,
    assertions: Mapping[str, Assertion] | None,
) -> MatchOutcome:
    """The assertion wins, unconditionally. That is the whole requirement.

    Not "wins when the matcher failed" -- wins. The matcher reaching a
    confident wrong answer is one of the cases a maintainer corrects, and a
    rule that deferred to a confident automatic match would leave exactly that
    case uncorrectable. "MUST NOT be overwritten by automatic matching."

    The automatic outcome is not discarded silently: callers keep it so T053
    can publish the automatic rate separately from the assisted one.
    """
    if not assertions:
        return automatic
    assertion = assertions.get(form.strip()) or assertions.get(form)
    if assertion is None:
        return automatic
    return MatchOutcome(
        status=ResolutionStatus.RESOLVED,
        method=ResolutionMethod.MANUAL_ASSERTION,
        member_ids=(assertion.member_id,),
        score=1.0,
        tier_reached=ResolutionMethod.MANUAL_ASSERTION.value,
    )


def seeded_forms(assertions: Iterable[Assertion]) -> tuple[str, ...]:
    """The written forms these assertions cover, sorted."""
    return tuple(sorted(a.name_as_written for a in assertions))
