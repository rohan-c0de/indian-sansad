"""The FR-008 field allowlist. The ingest boundary's only gate.

Constitution Principle V, **NON-NEGOTIABLE**, quoted verbatim:

    "Published member data MUST be limited to this set: name forms, party,
    state, constituency, House, term, and sitting status."

    "Any other personal attribute the source serves — including personal
    phone, Delhi phone, email, present and permanent address, date of birth,
    marital status, and number of sons and daughters — MUST NOT be published
    unless its publication is an explicitly recorded decision."

    "'Published' covers everything a third party can reach: the published
    dataset files, any extract, any interactive page, any derived statistic,
    and any fixture, sample, or test file in the repository."

    "The absence of a prohibition is NOT permission. An attribute reaching the
    published record because nothing stopped it is a breach, whether or not
    anyone intended to publish it."

    "Widening the set requires a recorded decision naming the attribute, the
    reason, and the date — recorded before publication, not after."

**Why this runs in memory, before any write.** The member endpoint returns
personal contact, address, date of birth, marital status and family
composition fields for **5,426 named people without authentication**,
and the owner declined to adopt a guardrail against republishing it. Because
"published" reaches as far as a log line's worth of a test fixture, filtering
after a write is not filtering: an excluded attribute that has touched a cache,
a log, an exception message or a test artefact has already reached somewhere a
third party can get to. So `filter_record` is applied at the boundary, to the
decoded body, before anything persists.

**Unknown fields default to excluded.** A new upstream field nobody has seen is
dropped, not passed. This is the direct implementation of "the absence of a
prohibition is NOT permission" -- the opposite default would mean the upstream
could add an attribute and this project would start publishing it with no code
change and no decision. `sansad.ingest.shape` raises a maintainer signal when
an unknown field appears, so dropping it is not the same as ignoring it.

This module does not widen its own set. Widening requires a recorded decision
naming the attribute, the reason and the date.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "EXCLUDED_EXAMPLES",
    "PERMITTED_ATTRIBUTES",
    "excluded_keys_in",
    "filter_record",
    "is_permitted",
    "normalise_key",
]

#: The seven permitted attribute classes, verbatim from Principle V:
#: "name forms, party, state, constituency, House, term, and sitting status."
PERMITTED_ATTRIBUTES: tuple[str, ...] = (
    "name forms",
    "party",
    "state",
    "constituency",
    "House",
    "term",
    "sitting status",
)

#: Upstream key spellings that map onto the permitted set.
#:
#: Matching is on a normalised key (see `normalise_key`), so `memberName`,
#: `member_name` and `MEMBER NAME` all arrive here as `membername`. Spellings
#: are listed explicitly rather than pattern-matched: a pattern like
#: `*name*` would admit any future field whose name happens to contain "name",
#: which is the permissive default Principle V forbids.
_PERMITTED_KEYS: frozenset[str] = frozenset(
    {
        # -- name forms --
        "name",
        "membername",
        "memberfullname",
        "fullname",
        "firstname",
        "lastname",
        "middlename",
        "salutation",
        "title",
        "namehindi",
        "membernamehindi",
        "alias",
        "nickname",
        # -- party --
        "party",
        "partyname",
        "partyabbreviation",
        "partyabbr",
        "politicalparty",
        # -- state --
        "state",
        "statename",
        "statecode",
        "stateid",
        # -- constituency --
        "constituency",
        "constituencyname",
        "constituencyid",
        "constituencycode",
        "pcname",
        "pcid",
        # -- House --
        "house",
        "housename",
        "housenumber",
        "sabha",
        # -- term --
        "term",
        "terms",
        "termnumber",
        "lokshabhaterm",
        "loksabhano",
        "termstart",
        "termend",
        "termfrom",
        "termto",
        "fromdate",
        "todate",
        "electedyear",
        # -- sitting status --
        "sittingstatus",
        "status",
        "issitting",
        "sitting",
        "membershipstatus",
        # -- non-personal record plumbing: an upstream identifier and a
        #    session/question reference are not personal attributes and are
        #    needed for `source_record_ref` and the question joins. They
        #    publish no fact about a person beyond the permitted set.
        "memberid",
        "memberno",
        "membercode",
        "id",
        "questionid",
        "questionno",
        "quesno",
        "sessionno",
        "sessionnumber",
        "session",
        "questiontype",
        "type",
        "subject",
        "subjectname",
        "ministry",
        "ministryname",
        "ministryid",
        "questiondate",
        "date",
        "answerdate",
    }
)

#: Attributes Principle V names explicitly as excluded, in its own words:
#: "personal phone, Delhi phone, email, present and permanent address, date of
#: birth, marital status, and number of sons and daughters".
#:
#: This tuple is documentation and test material. It is NOT the mechanism --
#: the mechanism is that anything outside `_PERMITTED_KEYS` is dropped, so an
#: excluded attribute absent from this list is still dropped. A denylist as the
#: mechanism would be exactly the "absence of a prohibition is permission"
#: posture Principle V forbids.
EXCLUDED_EXAMPLES: tuple[str, ...] = (
    "personal phone",
    "Delhi phone",
    "email",
    "present address",
    "permanent address",
    "date of birth",
    "marital status",
    "number of sons and daughters",
)


def normalise_key(key: str) -> str:
    """Reduce an upstream key to a comparable form.

    Lowercased with separators and spaces removed, so `sittingStatus`,
    `sitting_status` and `Sitting Status` compare equal. Normalising before the
    membership test is what stops a casing or separator variant walking past
    the allowlist -- in either direction: it is also what stops a prohibited
    attribute slipping through in a spelling the allowlist did not anticipate,
    since the normalised form of an unknown key is still not in the permitted
    set.
    """
    return "".join(ch for ch in key.lower() if ch.isalnum())


def is_permitted(key: str) -> bool:
    """Whether `key` maps onto the FR-008 permitted set.

    Unknown keys return False. That is the point: the default is excluded.
    """
    return normalise_key(key) in _PERMITTED_KEYS


def excluded_keys_in(record: dict[str, Any]) -> tuple[str, ...]:
    """The keys of `record` that the allowlist drops, as written upstream.

    Returns key **names** only. Never values -- a function that reported what
    it was excluding would print the thing it exists to contain, and the
    guard's own interface rule is "it prints the offending path and key, never
    the value".
    """
    return tuple(k for k in record if not is_permitted(k))


def filter_record(record: dict[str, Any]) -> dict[str, Any]:
    """Drop every attribute outside the FR-008 set.

    Applied at the ingest boundary, in memory, to the decoded body, before
    anything is written. Nested dicts and lists of dicts are filtered
    recursively -- an excluded attribute one level down is still published if
    its parent is published.
    """
    filtered: dict[str, Any] = {}
    for key, value in record.items():
        if not is_permitted(key):
            continue
        if isinstance(value, dict):
            filtered[key] = filter_record(value)
        elif isinstance(value, list):
            filtered[key] = [
                filter_record(item) if isinstance(item, dict) else item for item in value
            ]
        else:
            filtered[key] = value
    return filtered
