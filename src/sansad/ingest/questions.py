"""T043 -- the question-metadata route, through the transport and the allowlist.

The route, verbatim from `spike/route-capture.md`:

    GET https://sansad.in/api_ls/question/qetFilteredQuestionsAns

> **The path is spelled `qetFilteredQuestionsAns` — `qet`, not `get`.** That is
> the upstream's own spelling, reproduced here verbatim because a silent
> correction to `get...` yields 404. It is a typo in the source service, and it
> is load-bearing.

**Observed parameter behaviour this module relies on** (T004):

| Parameter | Behaviour |
|---|---|
| `loksabhaNo` | **Required.** Omitted → HTTP 400. A nonexistent value → 200 with `totalRecordSize: 0`, a quiet empty rather than an error |
| `sessionNumber` | Optional. **Omitted → the whole term** |
| `pageNo` | **1-based.** `0` → HTTP 500. Past the end → **200 with 0 records, not an error** |
| `pageSize` | Omitted → defaults to 10. `10`-`500` exercised and honoured exactly |

Two of those shape this module directly.

**Past-the-end returns 200 with 0 records.** So an empty page is the stop
condition and is indistinguishable from a truncated term -- which is why
`fetch_question_records` compares what arrived against the envelope's own
`totalRecordSize` and raises `IngestionFailed` on a mismatch. Without that
comparison a half-fetched term publishes as a complete one and the resolution
rate looks fine on a smaller denominator.

**`pageNo=0` is an HTTP 500, not a validation message.** Pagination starts at 1
and this module never emits 0.

**The page-size ceiling is 500 because 500 is what was verified.**
`route-capture.md`: "No page-size ceiling was observed up to 500. The service
honoured every requested size exactly... **The ceiling above 500 is
UNVERIFIED.** `pageSize=5000` was aborted by *this client* after 38 s; the
server was not observed to refuse it." `spike/fetch_slice.py` used 1000, which
is beyond what T004 verified; this module does not, and refuses a larger
request rather than discovering the limit in production. Cost is linear at
**≈955 bytes and ≈29 ms per record**, so a 500-record page is ~15 s.

**Derived identity.** No single upstream field is a question id. `quesNo` is
unique *within* a session (250 records sampled, 0 duplicates), so identity is
the composite `(lokNo, sessionNo, quesNo)`, House-scoped so the two Houses'
session series are never conflated.

**What this module refuses to read.** The four `*FilePath` / `*DocPath` document
pointers (Principle III: never followed, fetched or published), the two Hindi
fields (Principle IV), and `supplementaryType` -- populated and harmless, but
absent from `data-model.md` and therefore not published without a decision. All
of them are dropped by the FR-008 allowlist before this module sees them; the
list is repeated here so the omission reads as deliberate.

**Declared gap: `ministry_id` is provisional.** `route-capture.md`: `ministry`
arrives as "a name string, not an id. A `ministry_id` must be minted and
reconciled by this feature; `/api_ls/question/getMinistry` is the reference
set." That reconciliation is T052. Until then `ministry_id_for` slugs the name,
which means **`data-model.md`'s rule that "renaming a ministry upstream MUST
NOT create a second ministry identity" is NOT YET SATISFIED.** Recorded as a
gap rather than papered over: a rename today would mint a second id.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import httpx

from sansad.ingest.field_allowlist import filter_record, normalise_key
from sansad.ingest.shape import QUESTION_ROUTE, check_shape
from sansad.ingest.transport import DEFAULT_TIMEOUT_SECONDS, fetch_json
from sansad.model._common import NOT_STATED, House, ResolutionStatus
from sansad.model.question import Question
from sansad.signals.alerts import Signal, SignalLog, ingestion_failure

__all__ = [
    "BASE_URL",
    "DEFAULT_PAGE_SIZE",
    "MAX_VERIFIED_PAGE_SIZE",
    "QUESTION_PATH",
    "IngestionFailed",
    "QuestionRecord",
    "fetch_question_records",
    "load_question_records",
    "ministry_id_for",
    "question_id_for",
    "session_id_for",
]

BASE_URL = "https://sansad.in"
#: `qet`, not `get`. The upstream's own spelling; correcting it yields 404.
QUESTION_PATH = QUESTION_ROUTE
#: The envelope's keys (`route-capture.md`). The root is a JSON array of
#: length 1 and a consumer "must index `[0]` before reading either key".
RECORDS_KEY = "listOfQuestions"
TOTAL_KEY = "totalRecordSize"

#: The largest page size the service was **observed** to honour. Above this is
#: UNVERIFIED -- only a client timeout was seen, which is not a server refusal.
MAX_VERIFIED_PAGE_SIZE = 500
#: ≈15 s per page at the measured ≈29 ms/record. An operating choice about
#: runner time, not a documented limit.
DEFAULT_PAGE_SIZE = 500

_ASKER_KEYS: Sequence[str] = ("member", "members", "memberName")
_SUBJECT_KEYS: Sequence[str] = ("subjects", "subject", "subjectName")
_MINISTRY_KEYS: Sequence[str] = ("ministry", "ministryName")
_TYPE_KEYS: Sequence[str] = ("type", "questionType")
_DATE_KEYS: Sequence[str] = ("date", "questionDate", "answerDate")
_QUES_NO_KEYS: Sequence[str] = ("quesNo", "questionNo", "questionId")
_LOK_NO_KEYS: Sequence[str] = ("lokNo", "houseNumber", "loksabhaNo")
_SESSION_NO_KEYS: Sequence[str] = ("sessionNo", "sessionNumber", "session")

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


class IngestionFailed(RuntimeError):
    """A refresh could not complete, or completed partially.

    Carries the `Signal` that was raised, so a caller cannot handle the
    exception while losing the maintainer's notification. Raised rather than
    returned: a partial result that looks like a complete one is the single
    failure mode FR-010 and SC-006 exist to prevent, and returning it would
    make ignoring it the path of least resistance.
    """

    def __init__(self, signal: Signal) -> None:
        super().__init__(signal.summary)
        self.signal = signal


@dataclass(frozen=True, slots=True)
class QuestionRecord:
    """A mapped Question plus its asker name forms **exactly as written**.

    Two fields rather than one because the Question entity has nowhere to put a
    written name form -- `asking_members` holds `member_id` values -- and FR-005
    needs the written form to survive to the Resolution Record. Keeping it
    beside the entity rather than inside it is what stops an unresolved name
    string being published as if it were an identity.
    """

    question: Question
    asker_forms: tuple[str, ...]


def _pick(record: Mapping[str, Any], keys: Sequence[str]) -> Any:
    index = {normalise_key(k): v for k, v in record.items()}
    for key in keys:
        value = index.get(normalise_key(key))
        if value not in (None, "", [], {}):
            return value
    return None


def _text(record: Mapping[str, Any], keys: Sequence[str], default: str = NOT_STATED) -> str:
    value = _pick(record, keys)
    if value is None:
        return default
    return str(value).strip() or default


def session_id_for(house: House, lok_no: str, session_no: str) -> str:
    """A House-scoped session id: `lok-sabha/18/1`.

    "Lok Sabha and Rajya Sabha number sessions independently; `session_id` MUST
    be scoped by House so the two series are never conflated." The term number
    is included as well as the session number, because session 1 of the 17th and
    session 1 of the 18th are different sessions.
    """
    return f"{house.value}/{lok_no}/{session_no}"


def question_id_for(house: House, lok_no: str, session_no: str, ques_no: str) -> str:
    """The composite identity `(lokNo, sessionNo, quesNo)`, House-scoped.

    "Stable as long as the upstream does not renumber" -- which the upstream
    makes no promise about, carrying no contract, versioning or deprecation
    notice. `quesNo` uniqueness is observed **within one session only** (250
    records, 0 duplicates).
    """
    return f"{session_id_for(house, lok_no, session_no)}/{ques_no}"


def ministry_id_for(name: str) -> str:
    """A provisional `ministry_id` slugged from the ministry name.

    **This does not yet satisfy `data-model.md`'s stability rule** -- see the
    module docstring's declared gap. T052 reconciles against
    `/api_ls/question/getMinistry`, which is the reference set; until then a
    rename upstream mints a second id.
    """
    slug = _SLUG_STRIP.sub("-", (name or "").strip().lower()).strip("-")
    return slug or NOT_STATED


def _asker_forms(record: Mapping[str, Any]) -> tuple[str, ...]:
    """The asking-member name forms, as written, order preserved.

    The field is "array[len=N] of string", non-null on 250 of 250 sampled
    records -- the field T006 names as the User Story 1 gate. A single string
    is accepted too, because the second member source serves one.
    """
    value = _pick(record, _ASKER_KEYS)
    if value is None:
        return ()
    items = value if isinstance(value, list) else [value]
    forms: list[str] = []
    for item in items:
        text = str(item or "").strip()
        if text:
            forms.append(text)
    return tuple(forms)


def question_record_from(
    record: Mapping[str, Any],
    *,
    house: House = House.LOK_SABHA,
    last_refreshed: str | None = None,
    source_route: str = QUESTION_PATH,
    already_filtered: bool = False,
) -> QuestionRecord:
    """Map one upstream question record. Askers are **not** resolved here."""
    filtered = dict(record) if already_filtered else filter_record(dict(record))

    ques_no = _text(filtered, _QUES_NO_KEYS, default="")
    lok_no = _text(filtered, _LOK_NO_KEYS, default="")
    session_no = _text(filtered, _SESSION_NO_KEYS, default="")
    if not (ques_no and lok_no and session_no):
        raise ValueError(
            f"question record is missing part of its composite identity "
            f"(lokNo={lok_no!r}, sessionNo={session_no!r}, quesNo={ques_no!r}). "
            f"No single upstream field is a question id, so an incomplete "
            f"composite cannot be published under a minted one."
        )

    question_id = question_id_for(house, lok_no, session_no, ques_no)
    question = Question(
        question_id=question_id,
        house=house,
        session=session_id_for(house, lok_no, session_no),
        date=_text(filtered, _DATE_KEYS),
        type=_text(filtered, _TYPE_KEYS),
        subject=_text(filtered, _SUBJECT_KEYS),
        ministry_id=ministry_id_for(_text(filtered, _MINISTRY_KEYS, default="")),
        # Empty and `unresolved` until `sansad.resolve` says otherwise. The
        # entity never holds a name string in place of an identity.
        asking_members=(),
        resolution_status=ResolutionStatus.UNRESOLVED,
        source_record_ref=f"{source_route}#{question_id}",
        last_refreshed=last_refreshed or NOT_STATED,
    )
    return QuestionRecord(question=question, asker_forms=_asker_forms(filtered))


def load_question_records(
    records: Iterable[Mapping[str, Any]],
    *,
    house: House = House.LOK_SABHA,
    last_refreshed: str | None = None,
    source_route: str = QUESTION_PATH,
    already_filtered: bool = False,
) -> tuple[QuestionRecord, ...]:
    return tuple(
        question_record_from(
            record,
            house=house,
            last_refreshed=last_refreshed,
            source_route=source_route,
            already_filtered=already_filtered,
        )
        for record in records
    )


def _page(body: Any) -> tuple[list[Mapping[str, Any]], int | None]:
    """Unwrap the length-1 array envelope and return (records, total)."""
    envelope = body[0] if isinstance(body, list) and body else body
    if not isinstance(envelope, Mapping):
        raise TypeError(
            f"expected the length-1 array envelope carrying {RECORDS_KEY!r}, got "
            f"{type(body).__name__}"
        )
    raw = envelope.get(RECORDS_KEY) or []
    total = envelope.get(TOTAL_KEY)
    records = [r for r in raw if isinstance(r, Mapping)]
    return records, (
        int(total) if isinstance(total, (int, float, str)) and str(total).isdigit() else None
    )


def fetch_question_records(
    *,
    loksabha: int,
    session: int | None = None,
    page_size: int = DEFAULT_PAGE_SIZE,
    base_url: str = BASE_URL,
    client: httpx.Client | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    house: House = House.LOK_SABHA,
    last_refreshed: str | None = None,
    signals: SignalLog | None = None,
    check_upstream_shape: bool = True,
) -> tuple[QuestionRecord, ...]:
    """Page through one term (or one session) and map every record.

    Raises:
        IngestionFailed: if the upstream is unreachable, answers with an error
            status, or serves fewer records than its own `totalRecordSize`
            claims. The signal is recorded in `signals` first, so the
            maintainer hears about it whether or not the caller handles the
            exception (FR-011), and `SignalLog.should_publish` goes False so a
            partial dataset cannot replace a complete one (FR-010).
    """
    if page_size > MAX_VERIFIED_PAGE_SIZE:
        raise ValueError(
            f"page_size={page_size} exceeds the largest size the service was "
            f"OBSERVED to honour ({MAX_VERIFIED_PAGE_SIZE}). The ceiling above it is "
            f"UNVERIFIED -- only a client timeout was seen, which is not a server "
            f"refusal -- and production is not where to find out."
        )
    if page_size < 1:
        raise ValueError("page_size must be at least 1")

    log = signals if signals is not None else SignalLog()
    stage = f"questions loksabha={loksabha} session={session if session is not None else 'all'}"
    url = f"{base_url}{QUESTION_PATH}"

    collected: list[Mapping[str, Any]] = []
    expected: int | None = None
    page_no = 1  # 1-based. `pageNo=0` is an HTTP 500 on this service.
    shape_checked = not check_upstream_shape

    while True:
        params: dict[str, Any] = {
            "loksabhaNo": loksabha,
            "pageNo": page_no,
            "pageSize": page_size,
            "locale": "en",
        }
        if session is not None:
            params["sessionNumber"] = session
        try:
            body = fetch_json(url, params=params, timeout=timeout, client=client)
        except Exception as exc:
            # The error CLASS and a short message only. Never a response body:
            # "An alert that pastes the payload it is warning about has
            # published the payload."
            signal = log.add(
                ingestion_failure(
                    stage=f"{stage} page={page_no}",
                    reason=type(exc).__name__,
                    house=house.value,
                )
            )
            raise IngestionFailed(signal) from exc

        records, total = _page(body)
        if expected is None:
            expected = total

        if not shape_checked and records:
            # Shape detection must see the upstream's OWN field names, including
            # excluded ones -- a prohibited field being ADDED is invisible
            # otherwise. Names only; no value is read.
            divergence = check_shape(QUESTION_PATH, records)
            if divergence is not None:
                log.add(divergence)
            shape_checked = True

        collected.extend(records)

        # Past the end is "200 with 0 records, not an error", so an empty page
        # is the stop condition.
        if not records:
            break
        if expected is not None and len(collected) >= expected:
            break
        page_no += 1

    if expected is not None and len(collected) != expected:
        signal = log.add(
            ingestion_failure(
                stage=stage,
                reason=(
                    f"truncated: the envelope claims {expected} record(s) and "
                    f"{len(collected)} arrived"
                ),
                house=house.value,
            )
        )
        # Counts, not content -- the same rule the signal module holds to.
        signal.detail["expected"] = expected
        signal.detail["received"] = len(collected)
        raise IngestionFailed(signal)

    return load_question_records(
        (filter_record(dict(r)) for r in collected),
        house=house,
        last_refreshed=last_refreshed,
        already_filtered=True,
    )
