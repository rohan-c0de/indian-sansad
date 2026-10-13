"""What the previous publication said, for the two signals that compare. T172.

Both signals FR-011 promises and nothing raises today are **comparisons**:

* `resolved_transitions_out` -- a question that WAS `resolved` and is not now.
* `resolution_rate_below_target` -- a rate that DROPPED against the last
  publication, which is the trigger the owner chose over an absolute threshold.

Neither can be computed from the current build alone, so both need the previous
snapshot read before it is overwritten. The workflow already checks it out for
exactly this reason, and says so::

    # (a) Read the PREVIOUS snapshot before overwriting anything. FR-010's
    # last-known-good and FR-011's signal for a question leaving `resolved`
    # both need the prior record to compare against, and after the publish
    # step it is gone -- the branch is one commit deep.

So this module reads, and nothing more. It does not decide whether a change is
a finding -- `sansad.signals.alerts` does that -- because "what the previous
record said" and "what that means" are different questions and conflating them
is how a reader loses the ability to check either.

**Absence is a RESULT, not an error.** The first run has no previous
publication, and the workflow's checkout is `continue-on-error: true` for that
reason. Every function here returns an explicit "not available" rather than
raising, so a valid first run and a broken comparison stay distinguishable --
which is what FR-136 requires.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "PreviousPublication",
    "read_previous",
]

#: The partition whose rows carry a per-question resolution status.
BY_SESSION_DIR = "by-session"

#: The manifest field names the rates are published under. Read rather than
#: recomputed: the comparison must be against what the previous run PUBLISHED,
#: not against what this code would calculate from its files today.
RATE_AUTOMATIC = "resolution_rate_automatic"
RATE_PUBLISHED = "resolution_rate_including_assertions"


@dataclass(frozen=True)
class PreviousPublication:
    """The previous snapshot, or an explicit record that there was not one."""

    available: bool
    #: Why it is not available, when it is not. Empty when it is.
    reason: str = ""
    #: `question_id` -> `resolution_status`, from the previous `by-session` set.
    statuses: dict[str, str] = field(default_factory=dict)
    #: The rates the previous run published, or None where the manifest did
    #: not carry them. None is not 0.0 and must never be compared as if it is.
    rate_automatic: float | None = None
    rate_published: float | None = None
    #: What was actually read, for the log.
    session_files: int = 0

    def describe(self) -> str:
        """One line for the maintainer's log."""
        if not self.available:
            return f"previous publication: NOT AVAILABLE -- {self.reason}"
        return (
            f"previous publication: {len(self.statuses):,} question status(es) from "
            f"{self.session_files} session file(s); automatic "
            f"{_rate(self.rate_automatic)}, published {_rate(self.rate_published)}"
        )


def _rate(value: float | None) -> str:
    return "not stated" if value is None else f"{value:.2%}"


def _read_manifest_rates(root: Path) -> tuple[float | None, float | None, str]:
    """The two published rates, or `(None, None, why)`."""
    manifest = root / "manifest.json"
    if not manifest.is_file():
        return None, None, "no manifest.json"
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, None, f"manifest.json could not be read ({type(exc).__name__})"

    def value(key: str) -> float | None:
        raw = payload.get(key)
        return float(raw) if isinstance(raw, (int, float)) else None

    return value(RATE_AUTOMATIC), value(RATE_PUBLISHED), ""


def _read_statuses(root: Path) -> tuple[dict[str, str], int]:
    """`question_id` -> `resolution_status` across the previous by-session set.

    A row missing either field is skipped rather than guessed at: a question
    with no recorded status cannot have transitioned out of one.
    """
    directory = root / BY_SESSION_DIR
    if not directory.is_dir():
        return {}, 0
    statuses: dict[str, str] = {}
    files = 0
    for path in sorted(directory.glob("*.jsonl")):
        files += 1
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            question_id = row.get("question_id")
            status = row.get("resolution_status")
            if isinstance(question_id, str) and isinstance(status, str):
                statuses[question_id] = status
    return statuses, files


def read_previous(previous: Path | None) -> PreviousPublication:
    """Read the previous publication, or say why there is none.

    Args:
        previous: the directory holding it -- `.previous-snapshot` in CI, or
            whatever `--previous` names locally. `None` is the ordinary first
            run, not a failure.
    """
    if previous is None:
        return PreviousPublication(
            available=False,
            reason="no --previous directory was given, so no comparison is possible",
        )
    root = Path(previous)
    if not root.is_dir():
        return PreviousPublication(
            available=False,
            reason=f"{root} is not a directory (the first run has no `published` branch)",
        )

    # The published tree may sit at the root of the checkout, or under
    # `data/published/` -- the publish step writes the page at the branch root
    # and the dataset beneath it. Both layouts are tried, and which one was
    # found is not interesting enough to report; what matters is whether a
    # manifest was there at all.
    for candidate in (root / "data" / "published", root):
        if (candidate / "manifest.json").is_file():
            root = candidate
            break

    rate_automatic, rate_published, why = _read_manifest_rates(root)
    statuses, files = _read_statuses(root)

    if why and not statuses:
        return PreviousPublication(
            available=False,
            reason=f"{why}, and no by-session rows either",
        )
    if not statuses and rate_automatic is None and rate_published is None:
        return PreviousPublication(
            available=False,
            reason=f"{root} carries neither published rates nor by-session rows",
        )

    return PreviousPublication(
        available=True,
        statuses=statuses,
        rate_automatic=rate_automatic,
        rate_published=rate_published,
        session_files=files,
    )
