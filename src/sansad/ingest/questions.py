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
    "iso_date",
    "load_question_records",
    "ministry_fold_key",
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

#: The upstream's observed date format. **Asserted, not assumed.**
#:
#: `spike/route-capture.md` T006 open item 1 recorded the format as unasserted:
#: "The field is a string and was not parsed, because parsing it would mean
#: reading values. The pipeline must assert the format on first ingest rather
#: than assume ISO-8601 -- FR-013 excludes questions outside the covered
#: window, and a misparsed date silently mis-scopes that exclusion."
#:
#: Asserted on 2026-10-09 over the full window: `DD.MM.YYYY` on 34,720 of
#: 34,720 and 60,549 of 60,549 records, no other shape and no empty value.
_UPSTREAM_DATE = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4})$")


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
    #: The ministry name **exactly as written**, for the same reason
    #: `asker_forms` is here: `Question.ministry_id` holds the *minted* id, and
    #: deciding ministry identity needs the name plus the whole window's
    #: first-seen order (`sansad.publish.reference.MinistryRegistry`). A slug
    #: cannot be un-slugged.
    ministry_name: str = ""


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


def iso_date(value: str) -> str:
    """Convert the upstream's `DD.MM.YYYY` to ISO-8601, or raise.

    **Published dates are ISO-8601, and that is a deliberate conversion.** Three
    reasons, in order of weight:

    1. `DD.MM.YYYY` is **ambiguous to a consumer**: `01.04.2022` reads as 1
       April or 4 January depending on where the reader is from. ISO-8601 has
       one reading.
    2. It **sorts wrongly as a string**. Taking the min and max of the window's
       dates lexicographically returns `01.04.2022 .. 31.07.2026` where the
       truth is `2019-06-21 .. 2026-08-12`. That was a real defect in the
       Coverage Statement's period, found by reading the first dry run's output,
       and fixing it at every comparison site instead of at the boundary would
       leave the next site to get it wrong.
    3. FR-013 excludes questions outside the covered window, and
       `route-capture.md` names a misparsed date as the way that exclusion gets
       silently mis-scoped.

    An unparseable date **raises**. The format is asserted over 95,269 records,
    so a value that does not match it is an upstream shape change and belongs in
    a maintainer signal (FR-011), not in a published record as-is.
    """
    text = (value or "").strip()
    match = _UPSTREAM_DATE.match(text)
    if match is None:
        raise ValueError(
            f"question date {text!r} is not the asserted upstream format DD.MM.YYYY. "
            f"The format was asserted over all 95,269 records of the covered window; "
            f"a divergence is an upstream shape change (FR-011), not something to "
            f"coerce."
        )
    day, month, year = match.groups()
    return f"{year}-{month}-{day}"


def session_id_for(house: House, lok_no: str, session_no: str) -> str:
    """A House-scoped session id: `lok-sabha/18/1`.

    "Lok Sabha and Rajya Sabha number sessions independently; `session_id` MUST
    be scoped by House so the two series are never conflated." The term number
    is included as well as the session number, because session 1 of the 17th and
    session 1 of the 18th are different sessions.
    """
    return f"{house.value}/{lok_no}/{session_no}"


def question_type_slug(value: str) -> str:
    """The question type as an id segment.

    Stripped before slugging, because the 17th Lok Sabha serves the type with
    **trailing whitespace** (`'UNSTARRED '`) where the 18th does not. Two ids
    differing by invisible padding would be two ids for one question.

    An absent type becomes `not-stated` rather than an empty segment: an id
    with a hole in it collides with every other id that has the same hole.
    """
    slug = _SLUG_STRIP.sub("-", (value or "").strip().lower()).strip("-")
    return slug or "not-stated"


def question_id_for(
    house: House, lok_no: str, session_no: str, question_type: str, ques_no: str
) -> str:
    """The composite identity `(House, session, type, quesNo)`.

    **`type` is part of the identity, and that is a correction** (2026-10-09).
    The composite was `(lokNo, sessionNo, quesNo)`, on the strength of
    `spike/route-capture.md`'s "`quesNo` is unique *within* a session -- 250
    sampled records, 0 duplicate `quesNo`", which that document itself flagged
    as observed "within one session only".

    Measured over the full 95,269-record window it is **false**: 7,431 records
    collided onto an already-used id. `quesNo` is numbered **per (session,
    type)** -- `STARRED` and `UNSTARRED` are separate series -- and of 2,775
    colliding composites in the 18th Lok Sabha, **zero** had records sharing a
    type. Adding `type` removes every collision in the 18th and all but one in
    the 17th, and that one is a byte-identical duplicate row the upstream
    serves twice (see `dedupe_question_records`).

    Why this matters beyond tidiness: `contracts/published-dataset.md`
    guarantee 6 tells a consumer to "de-duplicate on `question_id` rather than
    sum across" partitions. Under the old composite, a consumer following that
    instruction merged a starred question with an unstarred one.

    Still "stable as long as the upstream does not renumber", about which it
    makes no promise -- it carries no contract, versioning or deprecation
    notice.
    """
    return (
        f"{session_id_for(house, lok_no, session_no)}/{question_type_slug(question_type)}/{ques_no}"
    )


def ministry_id_for(name: str) -> str:
    """The **minted** `ministry_id` for a ministry name: its slug.

    Owner decision 2026-10-09 (`spike/ministry-identity.md`): `ministry_id` is
    the slug of the **first** name a ministry was seen under, assigned once and
    never changed. This function mints the per-name candidate; deciding which
    name was first, and which minted ids collapse together, is
    `sansad.publish.reference.MinistryRegistry`, because that needs the whole
    window to see first-seen dates and the confirmed rename mappings.

    **`minCode` is deliberately not used.** The reference set does serve one,
    but it is per-term: 10 of the 52 names present in both terms carry a
    different code, and 14 of the 56 shared codes name a different ministry in
    each term. Question records carry only the name in any case.

    The slug is kept **unfolded** -- see `ministry_fold_key` for why the fold is
    a matching device rather than the published id.
    """
    slug = _SLUG_STRIP.sub("-", (name or "").strip().lower()).strip("-")
    return slug or NOT_STATED


#: Tokens shorter than this keep their trailing `s`. Four is chosen so `ports`
#: folds; no name in the window depends on the boundary either way.
_FOLD_MIN_TOKEN = 4


def ministry_fold_key(name: str) -> str:
    """A matching key that folds a trailing plural off each token.

    **A matching device, not an identity.** The published `ministry_id` is the
    unfolded slug of the first name seen; this key only decides *which names
    are the same ministry*. Keeping the two apart is the discipline
    `sansad.resolve.normalise` holds to for member names -- "normalisation is
    for matching only" -- and it keeps published ids readable
    (`agriculture-and-farmers-welfare`, not `agriculture-and-farmer-welfare`).

    Approved by owner decision 2026-10-09. Measured over the window's **64**
    distinct ministry names it merges exactly **four** groups and creates **no
    false merge**:

    | Variant A | Variant B | Difference | Resolved by |
    |---|---|---|---|
    | `EDUCATION` | `Education` | case | the slug alone |
    | `MICRO, SMALL ...` | `MICRO,SMALL ...` | punctuation | the slug alone |
    | `COMMUNICATIONS` | `COMMUNICATION` | trailing plural | **this fold** |
    | `ENVIRONMENT,  FORESTS ...` | `ENVIRONMENT, FOREST ...` | plural + space | **this fold** |

    The last two carry 325 and 3,010 questions, and neither needs a maintainer
    assertion as a result.

    **Its limit, stated rather than discovered later**: a trailing-`s` rule, not
    lemmatisation. It does not resolve an abbreviation (`AYUSH` against its long
    form), a reordering, or a word substitution -- those need a confirmed
    mapping, and four such mappings exist.

    **No merge is silent**: `MinistryRegistry` reports every group this key
    merged and the Coverage Statement publishes the list (T053).
    """
    slug = ministry_id_for(name)
    return "-".join(
        token[:-1] if len(token) >= _FOLD_MIN_TOKEN and token.endswith("s") else token
        for token in slug.split("-")
    )


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

    ministry_name = _text(filtered, _MINISTRY_KEYS, default="")
    question_type = _text(filtered, _TYPE_KEYS)
    question_id = question_id_for(house, lok_no, session_no, question_type, ques_no)
    question = Question(
        question_id=question_id,
        house=house,
        session=session_id_for(house, lok_no, session_no),
        date=iso_date(_text(filtered, _DATE_KEYS, default="")),
        type=question_type,
        subject=_text(filtered, _SUBJECT_KEYS),
        ministry_id=ministry_id_for(ministry_name),
        # Empty and `unresolved` until `sansad.resolve` says otherwise. The
        # entity never holds a name string in place of an identity.
        asking_members=(),
        resolution_status=ResolutionStatus.UNRESOLVED,
        source_record_ref=f"{source_route}#{question_id}",
        last_refreshed=last_refreshed or NOT_STATED,
    )
    return QuestionRecord(
        question=question,
        asker_forms=_asker_forms(filtered),
        ministry_name=ministry_name,
    )


@dataclass(frozen=True, slots=True)
class DuplicateRecord:
    """One `question_id` the upstream served more than once.

    Carried out of ingest so the Coverage Statement can **declare** it (FR-013:
    a known gap must be "reflected in the Coverage Statement rather than
    passing silently"). A duplicate that is dropped and not declared is a
    silent edit to the record count, and the published total would no longer
    match the upstream's own `totalRecordSize`.
    """

    question_id: str
    #: How many copies arrived, including the one kept.
    copies: int
    #: Whether every copy mapped to an identical published record.
    identical: bool

    @property
    def gap_note(self) -> str:
        """The sentence the Coverage Statement carries for this duplicate."""
        return (
            f"{self.question_id}: the upstream served {self.copies} copies of this "
            f"record; {self.copies - 1} identical copy/copies were dropped and one kept."
        )


#: The kind of known gap `DuplicateRecord` produces, for the Coverage Statement.
#:
#: `data-model.md` types `known_gaps` as "Sessions or dates known to be missing
#: or incomplete", which does not cover a **record-level** gap. The type is
#: widened there; this constant is the label.
KNOWN_GAP_DUPLICATE_RECORDS = "upstream-duplicate-record"


def dedupe_question_records(
    records: Iterable[QuestionRecord],
) -> tuple[tuple[QuestionRecord, ...], tuple[DuplicateRecord, ...]]:
    """Keep one copy of each `question_id`. Refuse if the copies disagree.

    Two outcomes, and the split is the point.

    **Identical copies**: keep the first, declare the rest. Nothing is lost --
    the copies map to the same published record, so which one survives cannot
    matter -- and the drop is reported rather than performed quietly. The
    upstream serves exactly one of these over the 95,269-record window:
    `(17, session 4, UNSTARRED, 2204)`, byte-identical.

    **Copies that differ**: refuse. Two different questions sharing one
    `question_id` cannot both be published under contract guarantee 6 ("a
    `question_id` appearing in several files is **one** question"), and there is
    no safe choice available here -- keeping either drops a real question in
    breach of FR-004, and keeping both hands consumers two different records
    under one id. So this raises, and the maintainer decides. **Measured count
    over the full window after adding `type` to the composite: zero.** The path
    is unreached on today's data and is deliberately loud rather than absent,
    because the next renumbering upstream is the case it exists for.
    """
    kept: dict[str, QuestionRecord] = {}
    copies: dict[str, list[QuestionRecord]] = {}
    order: list[str] = []

    for record in records:
        question_id = record.question.question_id
        if question_id not in kept:
            kept[question_id] = record
            copies[question_id] = [record]
            order.append(question_id)
        else:
            copies[question_id].append(record)

    duplicates: list[DuplicateRecord] = []
    for question_id in order:
        group = copies[question_id]
        if len(group) == 1:
            continue
        identical = all(other == group[0] for other in group[1:])
        if not identical:
            raise ValueError(
                f"{question_id}: the upstream served {len(group)} records under one "
                f"question_id and they are NOT identical. Publishing either would drop "
                f"a real question (FR-004) and publishing both would break contract "
                f"guarantee 6. Refusing rather than choosing: the composite identity "
                f"needs widening, or the upstream has renumbered."
            )
        duplicates.append(
            DuplicateRecord(question_id=question_id, copies=len(group), identical=True)
        )

    return tuple(kept[q] for q in order), tuple(duplicates)


def load_question_records(
    records: Iterable[Mapping[str, Any]],
    *,
    house: House = House.LOK_SABHA,
    last_refreshed: str | None = None,
    source_route: str = QUESTION_PATH,
    already_filtered: bool = False,
    dedupe: bool = True,
    duplicates: list[DuplicateRecord] | None = None,
) -> tuple[QuestionRecord, ...]:
    """Map upstream records, then keep one copy of each `question_id`.

    `duplicates` is an optional collector. Pass a list and it receives one
    `DuplicateRecord` per id the upstream served twice, for the Coverage
    Statement to declare (FR-013). Omitting it does not make the drop silent --
    the de-duplication still happens and is still reportable -- but a caller
    that publishes a coverage statement MUST pass it, or it will declare a
    coverage it has not checked.

    `dedupe=False` returns the records exactly as the upstream served them.
    It exists for the equivalence check in `tools/check_equivalence.py`, which
    has to reproduce the spike's 95,269-record denominator; it is not for the
    pipeline.
    """
    mapped = tuple(
        question_record_from(
            record,
            house=house,
            last_refreshed=last_refreshed,
            source_route=source_route,
            already_filtered=already_filtered,
        )
        for record in records
    )
    if not dedupe:
        return mapped
    kept, found = dedupe_question_records(mapped)
    if duplicates is not None:
        duplicates.extend(found)
    return kept


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
    duplicates: list[DuplicateRecord] | None = None,
) -> tuple[QuestionRecord, ...]:
    """Page through one term (or one session) and map every record.

    `duplicates` collects the ids the upstream served more than once, for the
    Coverage Statement to declare (FR-013). The truncation check below compares
    against the **records received**, not the records kept, so dropping an
    upstream duplicate can never be mistaken for a short fetch.

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
        duplicates=duplicates,
    )
