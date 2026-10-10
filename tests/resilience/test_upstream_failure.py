"""T040 -- `quickstart.md` scenario 9: degrade quietly, alert the maintainer.

> **Expected**, with the upstream simulated as unavailable, shape-changed, and
> truncated in turn:
>
> - the published record remains coherent and dated, and the coverage statement
>   flags it as last-known-good;
> - the maintainer signal fires;
> - no empty or partial record is ever presented as complete.
>
> **Fails if**: visitors see an error, or a shape change passes without a
> signal. These are the failure modes the owner explicitly asked to be
> inverted -- quiet for visitors, loud for the maintainer.

**No network call.** The three failures are simulated with
`httpx.MockTransport`, so this file exercises the real transport and ingest
code paths against a scripted upstream. Nothing is fetched and nothing is
recorded from the real one.

**The clauses about the published record are expected to FAIL until T053
(coverage statement) and T054 (last-known-good) exist.** They fail by
`ModuleNotFoundError` rather than being skipped: FR-010 is the requirement a
visitor actually experiences, and a skipped test for it would read as a pass.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from sansad.signals.alerts import Severity, SignalKind, SignalLog

QUESTION_ROUTE = "/api_ls/question/qetFilteredQuestionsAns"


def _envelope(records: list[dict], total: int) -> list[dict]:
    """The upstream's own envelope: a JSON array of length 1 (`route-capture.md`)."""
    return [{"listOfQuestions": records, "totalRecordSize": total, "_metadata": None}]


def _record(ques_no: int) -> dict:
    return {
        "quesNo": ques_no,
        "lokNo": "18",
        "sessionNo": "1",
        "date": "01.07.2024",
        "type": "UNSTARRED",
        "subjects": "Placeholder subject",
        "ministry": "Ministry of Placeholder Affairs",
        "member": ["Shri Sunil Kumar Singh"],
    }


# ---------------------------------------------------------------------------
# 1. Upstream unavailable
# ---------------------------------------------------------------------------
def test_an_unavailable_upstream_raises_the_maintainer_signal_and_blocks_publication():
    from sansad.ingest.questions import IngestionFailed, fetch_question_records

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated: upstream unavailable", request=request)

    signals = SignalLog()
    client = httpx.Client(transport=httpx.MockTransport(handler))

    with pytest.raises(IngestionFailed):
        fetch_question_records(loksabha=18, session=1, client=client, signals=signals)

    kinds = [s.kind for s in signals]
    assert SignalKind.INGESTION_FAILURE in kinds, (
        f"the upstream was unavailable and no maintainer signal fired: {signals.render()}"
    )
    assert signals.should_publish is False, (
        "a failed refresh must not be publishable -- the previous snapshot keeps being served"
    )


def test_an_http_error_from_the_upstream_is_also_an_ingestion_failure():
    from sansad.ingest.questions import IngestionFailed, fetch_question_records

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "simulated outage"})

    signals = SignalLog()
    client = httpx.Client(transport=httpx.MockTransport(handler))

    with pytest.raises(IngestionFailed):
        fetch_question_records(loksabha=18, session=1, client=client, signals=signals)

    assert any(s.severity is Severity.FAILED for s in signals)


def test_a_signal_never_carries_a_value_from_the_upstream():
    """ "An alert that pastes the payload it is warning about has published the
    payload." The simulated body below contains a marker string; it must not
    reach the rendered signal, which is delivered through a CI log."""
    from sansad.ingest.questions import IngestionFailed, fetch_question_records

    marker = "MARKER-THAT-MUST-NOT-BE-LOGGED"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text=marker)

    signals = SignalLog()
    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(IngestionFailed):
        fetch_question_records(loksabha=18, session=1, client=client, signals=signals)

    rendered = signals.render()
    assert marker not in rendered
    assert marker not in repr([s.detail for s in signals])


# ---------------------------------------------------------------------------
# 2. Upstream shape changed
# ---------------------------------------------------------------------------
def test_a_renamed_field_raises_a_shape_change_signal_with_both_halves():
    """A rename is one field missing and one added in the same refresh, which is
    why `sansad.ingest.shape` compares sets rather than counting fields."""
    from sansad.ingest.shape import QUESTION_ROUTE as ROUTE
    from sansad.ingest.shape import QUESTION_ROUTE_FIELDS, check_shape

    renamed = dict.fromkeys(QUESTION_ROUTE_FIELDS, None)
    renamed["memberNames"] = None
    del renamed["member"]

    signal = check_shape(ROUTE, [renamed])

    assert signal is not None, "a renamed asking-member field passed without a signal"
    assert signal.kind is SignalKind.UPSTREAM_SHAPE_CHANGE
    assert signal.detail["missing"] == ["member"]
    assert signal.detail["added"] == ["memberNames"]
    assert signal.severity is Severity.DEGRADED


def test_an_unchanged_shape_raises_nothing():
    from sansad.ingest.shape import QUESTION_ROUTE as ROUTE
    from sansad.ingest.shape import QUESTION_ROUTE_FIELDS, check_shape

    assert check_shape(ROUTE, [dict.fromkeys(QUESTION_ROUTE_FIELDS, None)]) is None


def test_a_shape_changed_refresh_fires_the_signal_through_the_ingest_path():
    """The signal must fire from the code that actually fetches, not only from a
    unit call to `check_shape`."""
    from sansad.ingest.questions import fetch_question_records

    def handler(request: httpx.Request) -> httpx.Response:
        record = _record(1)
        record["askingMembers"] = record.pop("member")
        return httpx.Response(200, json=_envelope([record], 1))

    signals = SignalLog()
    client = httpx.Client(transport=httpx.MockTransport(handler))
    fetch_question_records(loksabha=18, session=1, client=client, signals=signals)

    assert SignalKind.UPSTREAM_SHAPE_CHANGE in [s.kind for s in signals], signals.render()


# ---------------------------------------------------------------------------
# 3. Upstream truncated
# ---------------------------------------------------------------------------
def test_a_truncated_response_is_not_presented_as_complete():
    """The envelope says 4,500 records; the upstream serves 1 and then stops.

    `route-capture.md` records that a page past the end returns "200 with 0
    records, not an error", so a truncated term is indistinguishable from a
    complete one unless `totalRecordSize` is compared against what arrived.
    That comparison is the only thing standing between a partial dataset and a
    published one.
    """
    from sansad.ingest.questions import IngestionFailed, fetch_question_records

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(httpx.URL(str(request.url)).params.get("pageNo", 1))
        records = [_record(1)] if page == 1 else []
        return httpx.Response(200, json=_envelope(records, 4500))

    signals = SignalLog()
    client = httpx.Client(transport=httpx.MockTransport(handler))

    with pytest.raises(IngestionFailed):
        fetch_question_records(loksabha=18, session=1, client=client, signals=signals)

    failure = next(s for s in signals if s.kind is SignalKind.INGESTION_FAILURE)
    assert failure.severity is Severity.FAILED
    assert failure.detail.get("expected") == 4500
    assert failure.detail.get("received") == 1
    assert signals.should_publish is False


def test_a_complete_response_is_accepted():
    """The control for the test above: the same path must not refuse a complete
    refresh. A truncation check that fires on everything is not a check."""
    from sansad.ingest.questions import fetch_question_records

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(httpx.URL(str(request.url)).params.get("pageNo", 1))
        records = [_record(n) for n in range(1, 4)] if page == 1 else []
        return httpx.Response(200, json=_envelope(records, 3))

    signals = SignalLog()
    client = httpx.Client(transport=httpx.MockTransport(handler))
    records = fetch_question_records(loksabha=18, session=1, client=client, signals=signals)

    assert len(records) == 3
    assert signals.should_publish is True
    assert SignalKind.INGESTION_FAILURE not in [s.kind for s in signals]


# ---------------------------------------------------------------------------
# The visitor's half of FR-010 -- PENDING T053 / T054
# ---------------------------------------------------------------------------
def _snapshot(root: Path, *, last_refreshed: str) -> Path:
    """A minimal but COMPLETE published snapshot, for the retention tests."""
    from sansad.model._common import House
    from sansad.publish.coverage import CoverageInputs, write_coverage_statements
    from sansad.publish.partitions import write_manifest

    for axis in ("by-session", "by-ministry", "by-member"):
        (root / axis).mkdir(parents=True, exist_ok=True)
        (root / axis / "x.jsonl").write_text('{"question_id":"q1"}\n', encoding="utf-8")
        (root / axis / "x.csv").write_text("question_id\nq1\n", encoding="utf-8")
    write_coverage_statements(
        root,
        [
            CoverageInputs(
                house=House.LOK_SABHA,
                period_start="2019-06-21",
                period_end="2026-08-12",
                sessions_covered=("lok-sabha/17/1",),
                last_refreshed=last_refreshed,
                total_questions=10,
                resolved_automatic=9,
                resolved_assisted=10,
            )
        ],
    )
    write_manifest(
        root,
        last_refreshed=last_refreshed,
        sets={"by-session": {"files": 2, "records": 1}},
    )
    return root


def test_the_coverage_statement_flags_the_record_as_last_known_good(tmp_path):
    """FR-010: the record "MUST remain coherent and dated rather than empty or
    partial", and `last_known_good` must say which it is.

    The date it carries must be the date of the **last successful** refresh, not
    today's. Re-stamping today onto a snapshot that is not from today would make
    stale data look fresh, which is the one thing FR-010 exists to prevent.
    """
    from sansad.publish.formats import read_ndjson
    from sansad.publish.last_known_good import retain_previous

    previous = _snapshot(tmp_path / "previous", last_refreshed="2026-10-01")
    destination = tmp_path / "published"

    found = retain_previous(
        previous, destination, reason="upstream unavailable", today="2026-10-09"
    )

    assert found.usable, found.reason
    row = read_ndjson(destination / "coverage.jsonl")[0]
    assert row["last_known_good"] == "last-known-good"
    assert row["last_refreshed"] == "2026-10-01", "a stale snapshot must keep its own date"
    assert row["last_attempted"] == "2026-10-09"
    assert row["last_known_good_reason"] == "upstream unavailable"


def test_a_failed_refresh_retains_the_previous_snapshot_re_dated(tmp_path):
    """ "the previously published record is retained and re-dated as
    last-known-good rather than replaced by an empty or partial one" (T054)."""
    from sansad.publish.last_known_good import retain_previous

    previous = _snapshot(tmp_path / "previous", last_refreshed="2026-10-01")
    destination = tmp_path / "published"

    retain_previous(previous, destination, reason="shape change", today="2026-10-09")

    # Every question partition survived -- nothing was emptied.
    for axis in ("by-session", "by-ministry", "by-member"):
        assert (destination / axis / "x.jsonl").is_file()
        assert (destination / axis / "x.csv").is_file()
    assert (destination / "manifest.json").is_file()


def test_an_incomplete_previous_snapshot_is_not_promoted(tmp_path):
    """A partial directory is not a snapshot, and serving it would present a
    partial record as complete -- which SC-006 forbids.

    It reports rather than raises: a failed refresh with no good fallback is a
    state to describe, not a second exception on top of the first.
    """
    from sansad.publish.last_known_good import inspect_previous, retain_previous

    half = tmp_path / "half"
    (half / "by-session").mkdir(parents=True)
    (half / "by-session" / "x.jsonl").write_text('{"question_id":"q1"}\n', encoding="utf-8")

    found = inspect_previous(half)
    assert found.exists and not found.usable
    assert "by-ministry" in found.missing and "manifest.json" in found.missing
    assert "SC-006" in found.reason

    destination = tmp_path / "published"
    assert not retain_previous(half, destination, reason="x", today="y").usable
    assert not destination.exists(), "an unusable snapshot must not be copied anywhere"

    # ...and an absent one is simply absent, not an error.
    assert not inspect_previous(tmp_path / "nothing-here").exists
    assert not inspect_previous(None).exists


def test_the_visitor_never_sees_an_error_state(tmp_path):
    """FR-010's quiet half: a failed refresh leaves a coherent, dated record.

    "Fails if: visitors see an error." Asserted on the retained snapshot: every
    field a reader needs is still populated, the statement still parses, and the
    staleness is self-describing rather than an error page.
    """
    from sansad.publish.formats import read_csv, read_ndjson
    from sansad.publish.last_known_good import retain_previous

    previous = _snapshot(tmp_path / "previous", last_refreshed="2026-10-01")
    destination = tmp_path / "published"
    retain_previous(previous, destination, reason="upstream 503", today="2026-10-09")

    rows = read_ndjson(destination / "coverage.jsonl")
    assert len(rows) == 1
    row = rows[0]
    for required in ("house", "period_start", "period_end", "total_questions", "last_refreshed"):
        assert row.get(required) not in (None, ""), required
    # Coherent, not empty or partial.
    assert row["total_questions"] == 10
    assert row["sessions_covered"] == ["lok-sabha/17/1"]
    # Both formats stay in step, so a CSV consumer sees the same staleness.
    assert read_csv(destination / "coverage.csv")[0]["last_known_good"] == "last-known-good"
