"""The four maintainer-facing signals.

`contracts/published-dataset.md` → "Maintainer-facing signals (not part of the
consumer contract)", quoted verbatim:

    "Required by FR-011 and listed here so they are not mistaken for
    consumer-facing behaviour: ingestion failure, upstream shape change,
    resolution rate falling below target, and any transition of a question out
    of `resolved`. Visitors see a coherent dated record throughout (FR-010);
    only the maintainer is alerted."

**Why this module is separate from everything visitor-facing.** FR-010 and
FR-011 pull in opposite directions. FR-010 wants a visitor to see a coherent,
dated record even when the last refresh failed -- quietly, with no error page
and no broken view. FR-011 wants the maintainer to hear about that same failure
loudly. One code path serving both ends up either alarming visitors or
silencing the maintainer, and the second is the one that goes unnoticed. So the
two live apart: `sansad.publish` keeps the visitor's record coherent, and this
module is the only thing that raises.

**Signals are raised, not handled, here.** This module decides *what is worth
telling the maintainer* and records it. How a signal reaches a person -- a
failed CI job, an issue, a log line -- is the scheduled workflow's business
(T058), because the delivery mechanism is constrained by Principle I's free
tier and this module must not depend on which one was chosen.

A signal is raised even when the refresh as a whole succeeds. `UPSTREAM_SHAPE_CHANGE`
in particular is the one that catches an upstream carrying no contract,
versioning or deprecation notice: a field being renamed is not an error, it is
a silent change of meaning, and it is exactly the case where nothing fails.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from enum import StrEnum

__all__ = [
    "Severity",
    "Signal",
    "SignalKind",
    "SignalLog",
    "ingestion_failure",
    "resolution_rate_below_target",
    "resolved_transitions_out",
    "upstream_shape_change",
]


class SignalKind(StrEnum):
    """The four signals. Exactly four -- the contract names four.

    A fifth kind is a change to the contract's maintainer-signal list, not a
    convenience to be added here.
    """

    #: A refresh could not complete. The previous snapshot keeps being served
    #: (FR-010) and nothing is pushed to the published branch.
    INGESTION_FAILURE = "ingestion-failure"
    #: The upstream's field-name set diverged from the recorded one -- a field
    #: disappeared, was renamed, or was added. Raised by `sansad.ingest.shape`.
    UPSTREAM_SHAPE_CHANGE = "upstream-shape-change"
    #: The resolution rate fell below SC-002's target.
    RESOLUTION_RATE_BELOW_TARGET = "resolution-rate-below-target"
    #: A question that was previously `resolved` no longer is.
    RESOLVED_TRANSITION_OUT = "resolved-transition-out"


class Severity(StrEnum):
    """How much of the record is affected.

    Severity is about the maintainer's response, not the visitor's experience:
    the visitor's experience is unchanged at every level (FR-010).
    """

    #: Something to look at. The published record is still correct.
    NOTICE = "notice"
    #: The published record is stale or a published join has become uncertain.
    DEGRADED = "degraded"
    #: Nothing was published and the previous snapshot is being served.
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Signal:
    """One thing the maintainer needs to know.

    `detail` carries field *names*, counts and identifiers only. Never a value
    from an upstream record: a signal is delivered through a CI log or an
    issue, both of which a third party can reach, and Principle V's "published"
    covers "everything a third party can reach". An alert that pastes the
    payload it is warning about has published the payload.
    """

    kind: SignalKind
    severity: Severity
    summary: str
    detail: dict[str, object] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"[{self.severity.value}] {self.kind.value}: {self.summary}"


@dataclass(slots=True)
class SignalLog:
    """Collected signals for one refresh.

    A list rather than an immediate raise, because a refresh that hits three
    problems should tell the maintainer about three problems. Exiting on the
    first one hides the rest until the next run.
    """

    signals: list[Signal] = field(default_factory=list)

    def add(self, signal: Signal) -> Signal:
        self.signals.append(signal)
        return signal

    def extend(self, signals: Iterable[Signal]) -> None:
        self.signals.extend(signals)

    def __iter__(self) -> Iterator[Signal]:
        return iter(self.signals)

    def __len__(self) -> int:
        return len(self.signals)

    @property
    def should_publish(self) -> bool:
        """Whether this refresh may be published.

        False when any signal is `FAILED`. "pushes nothing at all on a failed
        or partial refresh so the previous snapshot keeps being served"
        (quickstart.md) -- so a partial dataset never replaces a complete one.
        """
        return not any(s.severity is Severity.FAILED for s in self.signals)

    def render(self) -> str:
        """The maintainer-facing text. Names and counts only, never values."""
        if not self.signals:
            return "no signals"
        return "\n".join(str(s) for s in self.signals)


def ingestion_failure(stage: str, reason: str, *, house: str | None = None) -> Signal:
    """A refresh could not complete.

    `reason` is an error class and message, never a response body.
    """
    return Signal(
        kind=SignalKind.INGESTION_FAILURE,
        severity=Severity.FAILED,
        summary=f"ingestion failed at {stage}: {reason}",
        detail={"stage": stage, "reason": reason, "house": house},
    )


def upstream_shape_change(
    *,
    missing: tuple[str, ...] = (),
    added: tuple[str, ...] = (),
    route: str | None = None,
) -> Signal:
    """The upstream's field-name set diverged from the recorded one.

    Field NAMES only -- which is all `spike/route-capture.md` recorded, and all
    `sansad.ingest.shape` compares.

    Severity is DEGRADED rather than NOTICE when a field went missing, because
    a disappeared field means a published field is now being derived from
    nothing. An ADDED field is a NOTICE: the allowlist already drops it
    (unknown fields default to excluded), so nothing is published from it --
    but it still needs a human to decide whether it should be.
    """
    severity = Severity.DEGRADED if missing else Severity.NOTICE
    parts: list[str] = []
    if missing:
        parts.append(f"{len(missing)} field(s) missing: {', '.join(sorted(missing))}")
    if added:
        parts.append(f"{len(added)} field(s) added: {', '.join(sorted(added))}")
    return Signal(
        kind=SignalKind.UPSTREAM_SHAPE_CHANGE,
        severity=severity,
        summary=f"upstream shape changed on {route or 'an upstream route'} -- "
        + ("; ".join(parts) if parts else "no field-name divergence"),
        detail={"missing": list(missing), "added": list(added), "route": route},
    )


def resolution_rate_below_target(
    *,
    resolved: int,
    total: int,
    target: float,
    is_automatic_rate: bool = False,
) -> Signal:
    """The resolution rate fell below target.

    Both rates are checked, and they are not the same check. The owner's
    decision of 2026-10-09 left the **automatic** rate at 94.78% -- already
    below SC-002's 95% -- with the published rate carried over the line to
    96.36% by four maintainer assertions. So an automatic rate below target is
    the KNOWN AND ACCEPTED state, raised as a NOTICE, while the published rate
    falling below target is a real regression against a met criterion.

    Reporting both at the same severity would mean either a permanent false
    alarm on the automatic rate, or silence when the published rate slipped.
    """
    rate = (resolved / total) if total else 0.0
    severity = Severity.NOTICE if is_automatic_rate else Severity.DEGRADED
    which = "automatic" if is_automatic_rate else "published"
    return Signal(
        kind=SignalKind.RESOLUTION_RATE_BELOW_TARGET,
        severity=severity,
        summary=(
            f"{which} resolution rate {rate:.2%} ({resolved}/{total}) is below target {target:.0%}"
        ),
        detail={
            "rate": rate,
            "resolved": resolved,
            "total": total,
            "target": target,
            "which_rate": which,
        },
    )


def resolved_transitions_out(question_ids: tuple[str, ...], *, new_status: str) -> Signal:
    """Questions that were `resolved` and no longer are.

    "A transition out of `resolved` MUST raise a maintainer signal, because it
    means a previously published join has become uncertain" (`data-model.md` →
    State Transitions).

    This is the signal most likely to be the only sign of a real problem. It
    fires on a *successful* refresh -- nothing failed, nothing is stale, the
    rate may even have gone up -- while a join a consumer already took has
    silently become uncertain. Question ids only; no names, no values.
    """
    return Signal(
        kind=SignalKind.RESOLVED_TRANSITION_OUT,
        severity=Severity.DEGRADED,
        summary=(
            f"{len(question_ids)} question(s) transitioned out of 'resolved' to '{new_status}'"
        ),
        detail={
            "count": len(question_ids),
            "new_status": new_status,
            "question_ids": list(question_ids),
        },
    )
