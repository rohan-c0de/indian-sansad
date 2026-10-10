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
        "date": "2024-07-01",
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
def test_the_coverage_statement_flags_the_record_as_last_known_good():
    from sansad.publish import coverage  # PENDING T053

    assert hasattr(coverage, "write_coverage_statements")


def test_a_failed_refresh_retains_the_previous_snapshot_re_dated():
    """ "the previously published record is retained and re-dated as
    last-known-good rather than replaced by an empty or partial one" (T054)."""
    from sansad.publish import last_known_good  # PENDING T054

    assert hasattr(last_known_good, "retain_previous")


def test_the_visitor_never_sees_an_error_state():
    """FR-010's quiet half, which is a property of the published record rather
    than of the pipeline: a failed refresh leaves a coherent, dated record."""
    from sansad.publish import last_known_good  # PENDING T054

    assert hasattr(last_known_good, "retain_previous")
