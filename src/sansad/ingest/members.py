"""T042 -- the Lok Sabha member roster, through the transport and the allowlist.

Reads `/api_ls/member` via `sansad.ingest.transport` (so no raw body is ever
written inside the tree) and `sansad.ingest.field_allowlist` (so no attribute
outside the FR-008 set survives the boundary), and maps what is left onto the
Member entity.

**What the control group measured, and why it shapes this module.**
`spike/route-capture.md` fetched this route first-hand: **5,197,598 bytes
(≈5.0 MiB) in 46.504 s**, of which 42.8 s was pure transfer, unpaginated, in
one response. "One unpaginated fetch spending three quarters of a minute is a
material fraction of a free runner's job budget before any question page is
fetched, and it is the *control*, not the workload." So this module fetches the
roster **once per refresh** and hands back an immutable tuple; nothing here
re-fetches per lookup.

**Two spelling families are accepted, and that is not defensive coding.**
`route-capture.md` records two member sources -- `/api_ls/member` (the roster,
whose fields `spike/fetch_slice.py` enumerates: `mpsno`, `mpFirstLastName`,
`partyFname`, `constName`, `lsExpr`, …) and
`/api_ls/question/getMembers?lkNo=<n>`, "a second name-form source to diff
against the roster". A mapper that only understood one of them would silently
return nothing from the other.

**What this module does NOT do.** It does not decide which questions were asked
by whom -- that is `sansad.resolve`. It does not merge two members who share a
name: "distinctness is decided on attributes beyond the name", and this module
has no similarity test in it at all.

**Known gap, stated rather than smoothed over.** `Term.start_date` and
`end_date` are left `NOT_STATED` here. The roster gives term *membership*
(`lsExpr`, `noOfTerms`, `lastLoksabha`) but no term *periods*; the periods come
from `/api_ls/business/getAllLoksabhaAndSession`, which is the Session reference
set (T052, outside Phase 4 part 1). Writing a guessed period would put an
invented date in a published record.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import httpx

from sansad.ingest.field_allowlist import filter_record, normalise_key
from sansad.ingest.transport import DEFAULT_TIMEOUT_SECONDS, fetch_json
from sansad.model._common import NOT_STATED, House, SittingStatus
from sansad.model.member import Member, Term
from sansad.resolve.identity import IdentityRegistry

__all__ = [
    "BASE_URL",
    "ROSTER_PATH",
    "ROSTER_RECORDS_KEY",
    "fetch_members",
    "load_members",
    "member_from_record",
    "sitting_status_from",
]

BASE_URL = "https://sansad.in"
ROSTER_PATH = "/api_ls/member"
#: The roster's records key, verbatim from `spike/fetch_slice.py`.
ROSTER_RECORDS_KEY = "membersDtoList"

# ---------------------------------------------------------------------------
# Field mapping
# ---------------------------------------------------------------------------
# Candidate upstream keys per model field, in PREFERENCE ORDER -- the first one
# present wins. Keys are compared through `normalise_key`, so `mpFirstLastName`,
# `mp_first_last_name` and `MPFIRSTLASTNAME` all resolve to the same entry.
#
# Every key here is already inside the FR-008 allowlist. If a key were added
# that the allowlist drops, the field would silently map to nothing -- which is
# precisely the failure the Phase 4 allowlist amendment was made to close.

_MEMBER_ID_KEYS: Sequence[str] = ("memberId", "memberNo", "memberCode")
_RECORD_SERIAL_KEYS: Sequence[str] = ("mpsno", "id")
#: Preferred canonical display form first.
_CANONICAL_NAME_KEYS: Sequence[str] = (
    "mpFirstLastName",
    "memberFullName",
    "memberName",
    "fullName",
    "name",
)
#: Every key that carries a *written name form*. All of them become variants.
_NAME_FORM_KEYS: Sequence[str] = (
    "mpFirstLastName",
    "mpLastFirstName",
    "memberFullName",
    "memberName",
    "fullName",
    "name",
    "alias",
    "nickname",
)
_PARTY_KEYS: Sequence[str] = ("partyFname", "partyName", "party", "partySname", "politicalParty")
_STATE_KEYS: Sequence[str] = ("stateName", "state")
_CONSTITUENCY_KEYS: Sequence[str] = ("constName", "constituencyName", "constituency", "pcName")
_SITTING_KEYS: Sequence[str] = ("sittingStatus", "membershipStatus", "status", "isSitting")
_TERM_LIST_KEYS: Sequence[str] = ("lsExpr",)
_TERM_NUMBER_KEYS: Sequence[str] = ("lastLoksabha", "termNumber", "term", "loksabhaNo")
_REFRESHED_KEYS: Sequence[str] = ("updatedAt", "createdAt")

#: Roster `status` vocabulary. **UNVERIFIED** -- `route-capture.md` records
#: field names, counts and sizes only, so no value of this field has ever been
#: observed. Anything unmatched becomes `NOT_STATED` rather than being guessed
#: into one of the two real values.
_SITTING_WORDS: frozenset[str] = frozenset(
    {"sitting", "active", "current", "serving", "yes", "y", "true", "1"}
)
_FORMER_WORDS: frozenset[str] = frozenset(
    {"former", "ex", "exmember", "retired", "expired", "ceased", "past", "no", "n", "false", "0"}
)


def _pick(record: Mapping[str, Any], keys: Sequence[str]) -> Any:
    """The first present, non-empty value among `keys`, matched on normalised keys."""
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
    text = str(value).strip()
    return text or default


def sitting_status_from(value: Any) -> SittingStatus:
    """Map the roster's sitting-status value, or say it is not stated.

    The third outcome is the point. The roster's vocabulary for this field has
    never been observed, and `data-model.md` requires a missing attribute be
    "an explicit 'not stated' value, never silently dropped" -- so an
    unrecognised value becomes `NOT_STATED` rather than whichever of the two
    real values happens to be the dataclass default.
    """
    if value is None:
        return SittingStatus.NOT_STATED
    if isinstance(value, bool):
        return SittingStatus.SITTING if value else SittingStatus.FORMER
    token = normalise_key(str(value))
    if not token:
        return SittingStatus.NOT_STATED
    if token in _SITTING_WORDS:
        return SittingStatus.SITTING
    if token in _FORMER_WORDS:
        return SittingStatus.FORMER
    return SittingStatus.NOT_STATED


def _terms_served(record: Mapping[str, Any]) -> tuple[int, ...]:
    """Lok Sabha numbers this member served in.

    `lsExpr` first -- "a comma-separated enumeration of every Lok Sabha a member
    served in ("11,12,14,16,17"), which is exact membership rather than the
    approximation `lastLoksabha` gives" (`spike/resolve_rate.py`). That
    distinction was a correctness fix in the spike, not a tuning change: for the
    17th Lok Sabha `lsExpr` selects 559 members where `lastLoksabha == 17`
    selects 343, because the 216 who continued into the 18th carry
    `lastLoksabha == 18`.
    """
    expr = _pick(record, _TERM_LIST_KEYS)
    if expr is not None:
        numbers = sorted({int(part) for part in str(expr).split(",") if part.strip().isdigit()})
        if numbers:
            return tuple(numbers)
    single = _pick(record, _TERM_NUMBER_KEYS)
    if single is not None and str(single).strip().isdigit():
        return (int(str(single).strip()),)
    return ()


def _name_variants(record: Mapping[str, Any], canonical: str) -> tuple[str, ...]:
    """Every written name form on the record, canonical first, order preserved.

    Also assembles the two composed forms `spike/resolve_rate.py` built --
    `initial firstName lastName` and `firstName lastName` -- because the roster
    serves name *components* as well as whole forms, and a component-only member
    would otherwise carry no matchable form at all.
    """
    index = {normalise_key(k): v for k, v in record.items()}
    forms: list[str] = []
    seen: set[str] = set()

    def add(form: Any) -> None:
        text = str(form or "").strip()
        if text and text not in seen:
            forms.append(text)
            seen.add(text)

    add(canonical)
    for key in _NAME_FORM_KEYS:
        add(index.get(normalise_key(key)))

    parts = [str(index.get(k) or "").strip() for k in ("initial", "firstname", "lastname")]
    add(" ".join(p for p in parts if p))
    add(" ".join(p for p in parts[1:] if p))

    return tuple(forms)


def member_from_record(
    record: Mapping[str, Any],
    *,
    house: House = House.LOK_SABHA,
    last_refreshed: str | None = None,
    registry: IdentityRegistry | None = None,
    source_route: str = ROSTER_PATH,
    already_filtered: bool = False,
) -> Member:
    """Map one upstream roster record onto a Member.

    The record is passed through the FR-008 allowlist first unless the caller
    states it already has been (`fetch_members` filters at the transport). An
    unfiltered record reaching the model is the breach this whole layer exists
    to prevent, so the default is to filter again rather than to trust.
    """
    filtered = dict(record) if already_filtered else filter_record(dict(record))

    serial = _pick(filtered, _RECORD_SERIAL_KEYS)
    explicit_id = _pick(filtered, _MEMBER_ID_KEYS)
    if serial is None and explicit_id is None:
        raise ValueError(
            "roster record carries no upstream identifier. A member_id cannot be "
            "minted from a name (FR-002), so this record cannot be ingested; its "
            "absence is an upstream shape change and belongs in a signal (FR-011)."
        )
    source_key = str(explicit_id if serial is None else serial).strip()

    registry = registry if registry is not None else IdentityRegistry()
    member_id = registry.member_id_for(
        source_key,
        house=house,
        # An id the source itself names as a member identifier is taken
        # verbatim; a bare record serial is prefixed. See identity.py.
        member_id=str(explicit_id).strip() if explicit_id is not None else None,
    )

    canonical = _text(filtered, _CANONICAL_NAME_KEYS, default="")
    if not canonical:
        raise ValueError(f"{member_id}: roster record carries no name form at all")

    party = _text(filtered, _PARTY_KEYS)
    state = _text(filtered, _STATE_KEYS)
    constituency_text = _text(filtered, _CONSTITUENCY_KEYS, default="")
    # "Lok Sabha members only; absent for Rajya Sabha" -- absent is None, which
    # is a different fact from a Lok Sabha constituency the source left blank.
    constituency = None if house is House.RAJYA_SABHA else (constituency_text or NOT_STATED)

    terms = tuple(
        Term(
            house=house,
            number=number,
            # Periods come from the session reference set (T052), not the
            # roster. NOT_STATED rather than an invented date -- see the module
            # docstring's known gap.
            start_date=NOT_STATED,
            end_date=None,
            party=party,
            constituency=constituency,
            state=state,
        )
        for number in _terms_served(filtered)
    )

    return Member(
        member_id=member_id,
        canonical_name=canonical,
        name_variants=_name_variants(filtered, canonical),
        house=house,
        party=party,
        state=state,
        constituency=constituency,
        terms=terms,
        sitting_status=sitting_status_from(_pick(filtered, _SITTING_KEYS)),
        # An identifier, never the record.
        source_record_ref=f"{source_route}#{source_key}",
        last_refreshed=last_refreshed or _text(filtered, _REFRESHED_KEYS),
    )


def load_members(
    records: Iterable[Mapping[str, Any]],
    *,
    house: House = House.LOK_SABHA,
    last_refreshed: str | None = None,
    source_route: str = ROSTER_PATH,
    already_filtered: bool = False,
) -> tuple[Member, ...]:
    """Map a roster into Members, under one identity registry.

    One registry across the whole roster is what makes "never reused" hold: a
    per-record registry would check nothing.
    """
    registry = IdentityRegistry()
    return tuple(
        member_from_record(
            record,
            house=house,
            last_refreshed=last_refreshed,
            registry=registry,
            source_route=source_route,
            already_filtered=already_filtered,
        )
        for record in records
    )


def fetch_members(
    *,
    base_url: str = BASE_URL,
    client: httpx.Client | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    house: House = House.LOK_SABHA,
    last_refreshed: str | None = None,
) -> tuple[Member, ...]:
    """Fetch the roster once and map it. Writes nothing, anywhere.

    The 46.5-second control measurement is why `timeout` is a parameter with a
    caller-visible default rather than a constant: the roster is the slowest
    single request this pipeline makes, and the transport's 30 s default is
    **below** the time the roster was observed to take. A caller fetching the
    roster must raise it deliberately.
    """
    body = fetch_json(f"{base_url}{ROSTER_PATH}", timeout=timeout, client=client)
    if not isinstance(body, Mapping):
        raise TypeError(
            f"roster: expected a mapping carrying {ROSTER_RECORDS_KEY!r}, got "
            f"{type(body).__name__}. An unexpected envelope is a maintainer "
            f"signal (FR-011), not something to coerce."
        )
    raw = body.get(ROSTER_RECORDS_KEY) or []
    return load_members(
        (filter_record(dict(r)) for r in raw if isinstance(r, Mapping)),
        house=house,
        last_refreshed=last_refreshed,
        already_filtered=True,
    )
