"""Upstream shape detection: compare observed field names against the recorded set.

FR-011 and the Edge Cases require a maintainer signal on any divergence in the
upstream's field-name set -- "a field disappearing, being renamed, or being
added". `research.md` records that the upstream carries no contract, versioning
or deprecation notice, so a rename is not announced and does not fail anything.
It simply starts meaning something else.

A rename is the worst of the three cases and the reason this module compares
sets rather than counting fields: a field disappearing AND one appearing in the
same refresh is a rename, and the field count is unchanged. Counting would see
nothing.

**What is compared.** Field NAMES only -- never values, never counts of
values. That is all `spike/route-capture.md` recorded (T004: "Record field
*names* and record *counts* only -- no field values, and no payload
committed"), and it is all that can be compared without holding a payload.

**Scope limit, stated rather than hidden.** Only the question route's field-name
set is recorded in `spike/route-capture.md` -- "17 field names, union across a
250-record sample, every record carrying all 17". The member roster's
field-name set was **never recorded as a list**, so `QUESTION_ROUTE_FIELDS`
below has no member-roster counterpart and `check_shape` cannot be called for
that route until one is recorded. `recorded_fields_for` raises rather than
returning an empty set: an empty baseline would make every observed field look
"added" on the first run and nothing look missing ever after, which is worse
than refusing.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from sansad.signals.alerts import Signal, upstream_shape_change

__all__ = [
    "QUESTION_ROUTE",
    "QUESTION_ROUTE_FIELDS",
    "RECORDED_FIELD_SETS",
    "check_shape",
    "observed_fields",
    "recorded_fields_for",
]

#: The question-metadata route, verbatim from `spike/route-capture.md`.
#: The `qet` spelling is a typo in the source service and is load-bearing --
#: the corrected spelling is not the route.
QUESTION_ROUTE = "/api_ls/question/qetFilteredQuestionsAns"

#: The question route's recorded field-name set: "17 field names, union across a
#: 250-record sample, every record carrying all 17."
#:
#: Four are document pointers and three are text/Hindi fields that the FR-008
#: allowlist and Principles III and IV exclude from publication. They are
#: listed here ANYWAY, because this set is the shape baseline, not the
#: publication set: a document pointer disappearing is still an upstream shape
#: change the maintainer should hear about, and omitting it here would make its
#: disappearance invisible.
QUESTION_ROUTE_FIELDS: frozenset[str] = frozenset(
    {
        "quesNo",
        "lokNo",
        "sessionNo",
        "date",
        "type",
        "subjects",
        "ministry",
        "member",
        "supplementaryType",
        "questionText",
        "answerText",
        "answerTextHindi",
        "supplementaryQuestionResDtoList",
        "questionsFilePath",
        "questionsFilePathHindi",
        "questionsDocPath",
        "questionsDocPathHindi",
    }
)

#: Recorded baselines, by route.
#:
#: The member roster is deliberately ABSENT rather than present-and-empty. Its
#: field-name set was never recorded as a list in `spike/route-capture.md`, and
#: a guessed baseline is worse than a missing one.
RECORDED_FIELD_SETS: Mapping[str, frozenset[str]] = {
    QUESTION_ROUTE: QUESTION_ROUTE_FIELDS,
}


def recorded_fields_for(route: str) -> frozenset[str]:
    """The recorded field-name set for `route`, or raise.

    Raises:
        KeyError: if no baseline is recorded. See the module docstring -- an
            empty baseline would silently disable the check.
    """
    try:
        return RECORDED_FIELD_SETS[route]
    except KeyError:
        raise KeyError(
            f"no recorded field-name set for route {route!r}. Shape checking is "
            f"NOT PRESENT for this route: record its field names in "
            f"spike/route-capture.md and add them to RECORDED_FIELD_SETS. "
            f"Refusing rather than comparing against an empty baseline, which "
            f"would report every field as added once and nothing as missing "
            f"thereafter."
        ) from None


def observed_fields(records: Iterable[Mapping[str, Any]]) -> frozenset[str]:
    """The union of field names across `records`.

    A union, matching how the baseline was recorded ("union across a 250-record
    sample"). Comparing one record's keys against a union baseline would report
    a field as missing whenever that single record happened to omit it.

    Takes records that have NOT been through the FR-008 allowlist -- shape
    detection is the one thing that must see the upstream's own field names,
    including excluded ones, or a prohibited field being added would be
    invisible. Names only: no value is read from any record here.
    """
    names: set[str] = set()
    for record in records:
        names.update(record.keys())
    return frozenset(names)


def check_shape(
    route: str,
    records: Iterable[Mapping[str, Any]],
    *,
    recorded: frozenset[str] | None = None,
) -> Signal | None:
    """Compare the observed field-name set against the recorded one.

    Returns a `upstream-shape-change` signal on any divergence, or None when
    the sets match exactly. A rename surfaces as one missing field and one
    added field in the same signal.
    """
    baseline = recorded if recorded is not None else recorded_fields_for(route)
    seen = observed_fields(records)

    missing = tuple(sorted(baseline - seen))
    added = tuple(sorted(seen - baseline))
    if not missing and not added:
        return None
    return upstream_shape_change(missing=missing, added=added, route=route)
