"""The two comparison signals, against seeded snapshots. T177.

`test_state_transitions.py` pins that all four signals have a production
caller. This pins what two of them actually DO, which is a different claim: a
wired signal that fires on the wrong condition is worse than an unwired one,
because it looks like coverage.

The condition that matters most is the **negative** one. The automatic
resolution rate is 0.947831 against a 0.95 target, both published, with
`sc_002_met_on_automatic_rate: false`. A signal triggered by that threshold
would fire on every single run forever. So the first thing asserted here is
that an unchanged rate raises **nothing**.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sansad.publish.previous import read_previous
from sansad.signals.alerts import Severity, resolution_rate_below_target

#: The published figures, so the tests exercise the real state rather than a
#: convenient one. Read from the dataset where it exists.
REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLISHED = REPO_ROOT / "data" / "published"

RATE_AUTOMATIC = 0.947831
RATE_PUBLISHED = 0.963555
TARGET = 0.95
WINDOW_TOTAL = 95_268
RESOLVED_AUTOMATIC = 90_298


def test_the_published_automatic_rate_really_is_below_target() -> None:
    """The premise of every assertion below, checked rather than assumed.

    If this ever stops being true the "would fire on every run" argument
    changes, and the trigger should be revisited rather than quietly kept.
    """
    if not (PUBLISHED / "manifest.json").is_file():
        pytest.skip("data/published/ is not built")
    manifest = json.loads((PUBLISHED / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["resolution_rate_automatic"] == pytest.approx(RATE_AUTOMATIC, abs=1e-6)
    assert manifest["resolution_rate_automatic"] < TARGET


def test_an_unchanged_rate_below_target_raises_NOTHING() -> None:
    """The whole reason the trigger is a drop and not a threshold (FR-135).

    94.78% against a 95% target, unchanged from the previous publication, is
    the known and accepted state. A signal here would fire on every run and
    carry no information -- and chasing it would be exactly the routine manual
    work Principle II forbids.
    """
    assert (
        resolution_rate_below_target(
            resolved=RESOLVED_AUTOMATIC,
            total=WINDOW_TOTAL,
            target=TARGET,
            previous=RATE_AUTOMATIC,
            is_automatic_rate=True,
        )
        is None
    )


def test_a_risen_rate_raises_nothing() -> None:
    assert (
        resolution_rate_below_target(
            resolved=RESOLVED_AUTOMATIC + 500,
            total=WINDOW_TOTAL,
            target=TARGET,
            previous=RATE_AUTOMATIC,
            is_automatic_rate=True,
        )
        is None
    )


def test_no_previous_publication_raises_nothing_and_is_not_treated_as_zero() -> None:
    """FR-136. `None` means "no comparison made", not 0.0.

    Treating an absent previous rate as zero would report a catastrophic drop
    on every first run -- the one run guaranteed to have no previous
    publication.
    """
    assert (
        resolution_rate_below_target(
            resolved=RESOLVED_AUTOMATIC,
            total=WINDOW_TOTAL,
            target=TARGET,
            previous=None,
            is_automatic_rate=True,
        )
        is None
    )


def test_a_dropped_automatic_rate_raises_a_notice_naming_both_rates() -> None:
    signal = resolution_rate_below_target(
        resolved=89_000,
        total=WINDOW_TOTAL,
        target=TARGET,
        previous=RATE_AUTOMATIC,
        is_automatic_rate=True,
    )
    assert signal is not None
    assert signal.severity is Severity.NOTICE
    assert "94.78%" in signal.summary and "93.42%" in signal.summary
    assert signal.detail["previous_rate"] == RATE_AUTOMATIC
    assert signal.detail["drop"] > 0


def test_a_dropped_published_rate_is_DEGRADED_not_a_notice() -> None:
    """The two rates are not the same claim.

    The automatic rate sitting below target is accepted, so a drop in it is a
    NOTICE. The published rate is the one SC-002 is actually met on, so a drop
    in it is a regression against a criterion currently met.
    """
    signal = resolution_rate_below_target(
        resolved=91_000,
        total=WINDOW_TOTAL,
        target=TARGET,
        previous=RATE_PUBLISHED,
        is_automatic_rate=False,
    )
    assert signal is not None
    assert signal.severity is Severity.DEGRADED
    assert "96.36%" in signal.summary


def _snapshot(tmp_path: Path, *, rows: list[dict], rates: dict | None) -> Path:
    """A minimal published snapshot: a manifest and one by-session file."""
    root = tmp_path / "previous"
    (root / "by-session").mkdir(parents=True)
    (root / "by-session" / "lok-sabha-18-8.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8"
    )
    (root / "manifest.json").write_text(json.dumps(rates or {}), encoding="utf-8")
    return root


def test_the_previous_reader_returns_statuses_and_rates(tmp_path: Path) -> None:
    root = _snapshot(
        tmp_path,
        rows=[
            {"question_id": "lok-sabha/18/8/starred/1", "resolution_status": "resolved"},
            {"question_id": "lok-sabha/18/8/starred/2", "resolution_status": "unresolved"},
        ],
        rates={
            "resolution_rate_automatic": RATE_AUTOMATIC,
            "resolution_rate_including_assertions": RATE_PUBLISHED,
        },
    )
    previous = read_previous(root)
    assert previous.available
    assert previous.statuses["lok-sabha/18/8/starred/1"] == "resolved"
    assert previous.rate_automatic == RATE_AUTOMATIC
    assert previous.rate_published == RATE_PUBLISHED
    assert "2 question status(es)" in previous.describe()


def test_an_absent_previous_directory_is_a_result_not_an_error() -> None:
    """FR-136 again, at the reader rather than at the signal.

    The first run has no `published` branch and the workflow's checkout is
    `continue-on-error: true` for that reason. A reader that raised here would
    turn a valid first run into a failed one.
    """
    for candidate in (None, Path("/nonexistent/previous/snapshot")):
        previous = read_previous(candidate)
        assert previous.available is False
        assert previous.reason
        assert previous.statuses == {}
        assert previous.rate_automatic is None
        assert "NOT AVAILABLE" in previous.describe()


def test_a_snapshot_with_neither_rates_nor_rows_is_not_available(tmp_path: Path) -> None:
    """An empty directory is not a previous publication, and reporting it as
    one would mean comparing against nothing and finding nothing wrong."""
    root = tmp_path / "empty"
    root.mkdir()
    previous = read_previous(root)
    assert previous.available is False


def test_the_reader_finds_the_dataset_under_either_published_layout(tmp_path: Path) -> None:
    """The publish step puts the page at the branch root and the dataset under
    `data/published/`, so a checkout of that branch nests one level deeper than
    a local build does. Both are read."""
    root = tmp_path / "checkout"
    nested = root / "data" / "published"
    (nested / "by-session").mkdir(parents=True)
    (nested / "by-session" / "s.jsonl").write_text(
        json.dumps({"question_id": "q1", "resolution_status": "resolved"}) + "\n",
        encoding="utf-8",
    )
    (nested / "manifest.json").write_text(
        json.dumps({"resolution_rate_automatic": RATE_AUTOMATIC}), encoding="utf-8"
    )
    previous = read_previous(root)
    assert previous.available
    assert previous.statuses == {"q1": "resolved"}


def test_rows_missing_either_field_are_skipped_rather_than_guessed(tmp_path: Path) -> None:
    """A question with no recorded status cannot have transitioned out of one."""
    root = _snapshot(
        tmp_path,
        rows=[
            {"question_id": "q1", "resolution_status": "resolved"},
            {"question_id": "q2"},
            {"resolution_status": "resolved"},
            {"question_id": "q3", "resolution_status": None},
        ],
        rates={"resolution_rate_automatic": RATE_AUTOMATIC},
    )
    previous = read_previous(root)
    assert previous.statuses == {"q1": "resolved"}
