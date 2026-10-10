"""The Coverage Statement entity.

A first-class published entity, because FR-013 makes coverage a user-visible
requirement rather than metadata.

Validation rules, quoted verbatim from
`specs/001-resolved-metadata-layer/data-model.md` → Coverage Statement:

- "`resolution_rate` MUST be published, not merely computed, so SC-002 is
  externally checkable."
- "When a refresh fails, `last_known_good` MUST indicate it and the record
  MUST remain coherent and dated rather than empty or partial (FR-010)."
- "If Rajya Sabha material proves unobtainable, the Coverage Statement MUST
  say so explicitly rather than implying both Houses are covered (Edge Cases;
  Phase 0 route finding)."

The third rule is live, not contingent. `research.md` records
`GET /api_rs/members` returning 403 where every sibling path returns 404, cause
UNVERIFIED, and every figure in the spike is Lok Sabha. A statement that
omitted the Rajya Sabha silently would imply coverage this project has not
demonstrated it has.

The first rule is why `resolution_rate` is a published field with its own
denominator rather than a bare percentage. A rate without the denominator is
not externally checkable, which is the entire point of publishing it; and the
rate carries **two** figures because four maintainer assertions are
load-bearing for SC-002 -- 94.78% automatic against 96.36% assisted. T053
requires both, so a consumer can see the project's dependence on hand
corrections instead of having it blended away.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sansad.model._common import House

PUBLISHED_FIELDS: tuple[str, ...] = (
    "house",
    "period_start",
    "period_end",
    "sessions_covered",
    "known_gaps",
    "resolution_rate",
    "last_refreshed",
    "last_known_good",
)


class Freshness(StrEnum):
    """Whether the published record is current or served from the last good state.

    FR-010's quiet degradation for visitors depends on this being a stated
    value rather than an inference from a date: a visitor cannot tell a stale
    record from a fresh one by looking at it, and FR-010 requires the record
    stay "coherent and dated rather than empty or partial".
    """

    #: The last refresh succeeded; this record is current.
    CURRENT = "current"
    #: The last refresh failed or was partial. This is the previous good
    #: snapshot, still coherent, still dated -- and saying so.
    LAST_KNOWN_GOOD = "last-known-good"


@dataclass(frozen=True, slots=True)
class ResolutionRate:
    """The published resolution rate, with its denominator and both figures.

    Two rates, not one. "Share of questions resolved to exactly one member" is
    reported both as the matcher achieves it unaided and as published after
    maintainer assertions, because the gap between them IS the project's
    dependence on hand correction (T053).
    """

    #: Questions resolved by automatic matching alone.
    resolved_automatic: int
    #: Questions resolved once maintainer assertions are applied. Computed by
    #: re-walking every record, NOT by adding per-form figures: a question
    #: resolves only when all its askers do (FR-003), so co-asked questions
    #: make the per-form counts non-additive.
    resolved_assisted: int
    #: "the absolute denominator" -- without it the rate is not checkable.
    total_questions: int

    def __post_init__(self) -> None:
        if self.total_questions < 0:
            raise ValueError("total_questions MUST NOT be negative")
        for name in ("resolved_automatic", "resolved_assisted"):
            value = getattr(self, name)
            if value < 0:
                raise ValueError(f"{name} MUST NOT be negative, got {value}")
            if value > self.total_questions:
                raise ValueError(f"{name}={value} exceeds total_questions={self.total_questions}")
        if self.resolved_assisted < self.resolved_automatic:
            raise ValueError(
                f"resolved_assisted={self.resolved_assisted} is below "
                f"resolved_automatic={self.resolved_automatic}. Maintainer "
                f"assertions MUST NOT reduce the resolved count -- an assertion "
                f"that un-resolves a join is a transition out of 'resolved' and "
                f"belongs in a maintainer signal (FR-011)."
            )

    @property
    def automatic(self) -> float:
        """The rate the pipeline achieves unaided. Published separately (T053)."""
        if self.total_questions == 0:
            return 0.0
        return self.resolved_automatic / self.total_questions

    @property
    def assisted(self) -> float:
        """The published rate, after maintainer assertions."""
        if self.total_questions == 0:
            return 0.0
        return self.resolved_assisted / self.total_questions


@dataclass(frozen=True, slots=True)
class CoverageStatement:
    """What this project claims to cover, for one House."""

    #: "Which House this statement describes." One statement per House.
    house: House
    period_start: str
    period_end: str
    #: "Session identifiers included." House-scoped ids, never bare numbers.
    sessions_covered: tuple[str, ...]
    #: "Sessions or dates known to be missing or incomplete." An empty tuple
    #: is a claim of no known gaps, so it is never a default -- see below.
    known_gaps: tuple[str, ...]
    resolution_rate: ResolutionRate
    last_refreshed: str
    last_known_good: Freshness = Freshness.CURRENT
    #: Set when a House is not covered at all. "If Rajya Sabha material proves
    #: unobtainable, the Coverage Statement MUST say so explicitly rather than
    #: implying both Houses are covered."
    unobtainable_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.last_refreshed:
            raise ValueError(
                f"{self.house.value}: last_refreshed is required. FR-010 requires the "
                f"record remain 'coherent and dated rather than empty or partial'."
            )
        # An uncovered House must say so, and must not present itself as a
        # covered one with an empty session list.
        if not self.sessions_covered and self.unobtainable_reason is None:
            raise ValueError(
                f"{self.house.value}: sessions_covered is empty with no "
                f"unobtainable_reason. A House that is not covered MUST say so "
                f"explicitly rather than implying coverage it does not have "
                f"(Edge Cases)."
            )
        for session_id in self.sessions_covered:
            if not session_id.startswith(f"{self.house.value}/"):
                raise ValueError(
                    f"{self.house.value}: session_id {session_id!r} is not scoped to "
                    f"this House. The two Houses' session series MUST never be "
                    f"conflated."
                )

    @property
    def is_covered(self) -> bool:
        """Whether this House is covered at all."""
        return self.unobtainable_reason is None and bool(self.sessions_covered)

    @property
    def meets_sc_002(self) -> bool:
        """Whether the published (assisted) rate meets SC-002's 95%.

        SC-002 stands at 95% unchanged -- owner decision 2026-10-09. The
        threshold lives here as a published, checkable property rather than in
        a test, because "MUST be published, not merely computed, so SC-002 is
        externally checkable" is the requirement.
        """
        return self.resolution_rate.assisted >= SC_002_TARGET


#: SC-002's target share of questions resolving to exactly one member.
#:
#: NOT amended. The owner's decision of 2026-10-09 kept it at 95% and closed
#: the measured gap by improving resolution -- a holdout-validated matcher tier
#: plus four hand assertions -- rather than by lowering the target.
SC_002_TARGET = 0.95
