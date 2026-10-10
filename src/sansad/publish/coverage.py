"""T053 -- the Coverage Statement. One per House, always present (FR-013).

`quickstart.md` scenario 11 via `make coverage`. FR-013 makes coverage a
user-visible requirement rather than metadata, so this is a published entity,
not a log line.

## Two resolution rates, never one

Owner decision 2026-10-09. The **automatic** rate is what the matcher achieves
unaided, with no maintainer assertion counted. The **assisted** rate is what is
published. Both are labelled and neither is presented as the other, for a
reason that is specific rather than tidy-minded: the automatic rate is
**below** SC-002's 95% (94.78%) and the assisted rate is above it (96.36%). A
single blended figure would present four hand corrections as matcher
performance, and would hide a future matcher regression behind them.

Both carry their denominator. "`resolution_rate` MUST be published, not merely
computed, so SC-002 is externally checkable" -- and a rate without its
denominator is not checkable, which is the whole point of publishing it.

## What else this statement has to say out loud

Each of these is here because it would otherwise be invisible to a consumer:

- **Lok Sabha only.** `research.md` records `GET /api_rs/members` returning 403
  where every sibling path returns 404, cause UNVERIFIED. A statement that
  omitted the Rajya Sabha silently would imply coverage this project has not
  demonstrated.
- **Assertions in effect, and how many override an automatic match.** Today
  four and **zero**. The zero matters: T048 lets an assertion win
  unconditionally, including over a confident automatic match, and measured
  over the window **no assertion does** -- all four land on forms the matcher
  left unresolved. So that rule is **untested in practice**, and the number is
  published rather than described so a consumer can watch it.
- **The declared duplicate record.** The upstream serves one record of the
  window twice, byte-identical. It is reduced to one, and declaring it is what
  stops the published total differing from the upstream's own count with no
  explanation.
- **Ministry identity's human-review backlog** and **every name group
  normalisation merged**, so a merge can never be silent (owner's condition on
  approving the fold).
- **The three session anomalies already found**, which would otherwise look
  like bugs in any per-sitting-day rate a consumer computed.
- **Question and answer text is absent entirely** -- Principle III forbids
  opening the document files it sits behind, so it is a field-level gap
  applying to every record in every session.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from sansad.model._common import House
from sansad.model.coverage_statement import (
    SC_002_TARGET,
    CoverageStatement,
    Freshness,
    ResolutionRate,
)
from sansad.publish.attribution import WHOLE_DATASET_FIELDS
from sansad.publish.formats import write_both

__all__ = [
    "COVERAGE_STEM",
    "KNOWN_GAP_NO_DOCUMENT_TEXT",
    "SESSION_ANOMALIES",
    "CoverageInputs",
    "build_coverage_statement",
    "coverage_row",
    "write_coverage_statements",
]

COVERAGE_STEM = "coverage"

#: The field-level gap Principle III creates. Not a session or a date, which is
#: why `data-model.md`'s `known_gaps` was widened to admit this shape.
KNOWN_GAP_NO_DOCUMENT_TEXT = (
    "question-and-answer-text: absent for every record in every session. "
    "`questionText` and `answerText` are null on the route and the text sits "
    "behind document pointers, which Principle III forbids opening."
)

#: Anomalies measured in the covered window, declared rather than smoothed.
#:
#: Each is a real divergence between the sitting-day enumeration and the
#: question route, and each would corrupt a per-sitting-day rate a consumer
#: computed without being told. Causes are UNVERIFIED and are not guessed at.
SESSION_ANOMALIES: tuple[str, ...] = (
    "lok-sabha/18/1: 7 sitting days recorded and ZERO questions served. Cause UNVERIFIED.",
    "lok-sabha/18/8: ZERO sitting days recorded and 4,500 questions served. "
    "The session was current when the enumeration was read, so the date array "
    "is plausibly not yet populated -- but 'plausibly' is not a finding and the "
    "cause is UNVERIFIED. A sitting-day denominator of 0 would divide by zero "
    "in any per-sitting-day rate.",
    "lok-sabha/17/13: 4 sitting days recorded and ZERO questions served. Cause UNVERIFIED.",
)


@dataclass(frozen=True, slots=True)
class CoverageInputs:
    """Everything the statement reports, gathered by the caller.

    A single explicit input object rather than a dozen parameters, so a caller
    cannot publish a statement that quietly omits one of the figures FR-013
    requires.
    """

    house: House
    period_start: str
    period_end: str
    sessions_covered: Sequence[str]
    last_refreshed: str
    total_questions: int
    resolved_automatic: int
    resolved_assisted: int
    assertions_in_effect: int = 0
    assertions_overriding_an_automatic_match: int = 0
    duplicate_records_declared: Sequence[str] = ()
    ministry_ids: int = 0
    ministry_names_observed: int = 0
    ministry_names_without_confirmed_mapping: int = 0
    ministry_name_groups_merged_by_normalisation: Sequence[Sequence[str]] = ()
    ministry_names_in_reference_set_with_no_questions: int = 0
    #: Per term: fetched live, resumed from a checkpoint (with the date that
    #: checkpoint was written), or read from the cached window. A resumed term
    #: is OLDER than `last_refreshed`, and a consumer cannot tell unless the
    #: statement says so -- which is the whole reason this field exists.
    #: The published sets this statement covers, by directory/file stem. T067
    #: adds `aggregates`. Published because a consumer otherwise has to
    #: discover the dataset's shape by listing directories, and a set that
    #: stopped being written would be invisible rather than missing.
    published_sets: Sequence[str] = ()
    question_source_by_term: Sequence[Mapping[str, object]] = ()
    extra_known_gaps: Sequence[str] = ()
    freshness: Freshness = Freshness.CURRENT
    unobtainable_reason: str | None = None
    notes: Mapping[str, object] = field(default_factory=dict)


def build_coverage_statement(inputs: CoverageInputs) -> CoverageStatement:
    """The entity, with every known gap assembled into `known_gaps`."""
    # Gaps belong to the House that declares them. A Rajya Sabha statement
    # listing Lok Sabha session anomalies would be claiming to know things
    # about a House it has no route to -- so the anomalies are filtered by the
    # session-id prefix they carry, which keeps the filter correct as anomalies
    # are added. An uncovered House declares only why it is uncovered.
    gaps: list[str] = []
    if inputs.unobtainable_reason is None:
        gaps.append(KNOWN_GAP_NO_DOCUMENT_TEXT)
        gaps.extend(a for a in SESSION_ANOMALIES if a.startswith(f"{inputs.house.value}/"))
    for question_id in inputs.duplicate_records_declared:
        gaps.append(
            f"upstream-duplicate-record: {question_id} was served more than once "
            f"by the upstream; identical copies were reduced to one and this is "
            f"the declaration (FR-013)."
        )
    for entry in inputs.question_source_by_term:
        if entry.get("mode") == "resumed":
            gaps.append(
                f"resumed-term: Lok Sabha {entry.get('term')}'s questions were NOT "
                f"fetched in this refresh. They were reused from a checkpoint "
                f"written {entry.get('checkpoint_written_at')}, so that part of the "
                f"record is older than last_refreshed (FR-016)."
            )
    gaps.extend(inputs.extra_known_gaps)

    return CoverageStatement(
        house=inputs.house,
        period_start=inputs.period_start,
        period_end=inputs.period_end,
        sessions_covered=tuple(inputs.sessions_covered),
        known_gaps=tuple(gaps),
        resolution_rate=ResolutionRate(
            resolved_automatic=inputs.resolved_automatic,
            resolved_assisted=inputs.resolved_assisted,
            total_questions=inputs.total_questions,
        ),
        last_refreshed=inputs.last_refreshed,
        last_known_good=inputs.freshness,
        unobtainable_reason=inputs.unobtainable_reason,
    )


def coverage_row(statement: CoverageStatement, inputs: CoverageInputs) -> dict[str, object]:
    """The published row: the entity's fields plus the figures T053 adds.

    Flat, with lists JSON-encoded by the CSV writer, so the two formats carry
    the same record. The rate fields are spelled out -- numerator, denominator
    and percentage for both rates -- rather than left as a nested object a CSV
    consumer would have to parse.
    """
    rate = statement.resolution_rate
    return {
        # Every House's statement carries them, including a House with no
        # route: an unobtainable-House statement is still part of the dataset,
        # and a consumer reading only it must still be told the terms of the
        # added work, that the source's own terms were never determined, and
        # where to send a correction.
        **WHOLE_DATASET_FIELDS,
        "house": statement.house.value,
        "houses_covered": statement.house.value,
        "period_start": statement.period_start,
        "period_end": statement.period_end,
        "sessions_covered": list(statement.sessions_covered),
        "sessions_covered_count": len(statement.sessions_covered),
        "total_questions": rate.total_questions,
        "resolved_automatic": rate.resolved_automatic,
        "resolution_rate_automatic": round(rate.automatic, 6),
        "resolved_including_assertions": rate.resolved_assisted,
        "resolution_rate_including_assertions": round(rate.assisted, 6),
        "sc_002_target": SC_002_TARGET,
        "sc_002_met_on_published_rate": statement.meets_sc_002,
        "sc_002_met_on_automatic_rate": rate.automatic >= SC_002_TARGET,
        "assertions_in_effect": inputs.assertions_in_effect,
        "assertions_overriding_an_automatic_match": (
            inputs.assertions_overriding_an_automatic_match
        ),
        "duplicate_records_declared": list(inputs.duplicate_records_declared),
        "ministry_ids": inputs.ministry_ids,
        "ministry_names_observed": inputs.ministry_names_observed,
        "ministry_names_without_confirmed_mapping": (
            inputs.ministry_names_without_confirmed_mapping
        ),
        "ministry_name_groups_merged_by_normalisation": [
            list(group) for group in inputs.ministry_name_groups_merged_by_normalisation
        ],
        "ministry_names_in_reference_set_with_no_questions": (
            inputs.ministry_names_in_reference_set_with_no_questions
        ),
        "known_gaps": list(statement.known_gaps),
        "published_sets": list(inputs.published_sets),
        "question_source_by_term": [dict(e) for e in inputs.question_source_by_term],
        "resumed_terms": [
            e.get("term") for e in inputs.question_source_by_term if e.get("mode") == "resumed"
        ],
        "last_refreshed": statement.last_refreshed,
        "last_known_good": statement.last_known_good.value,
        "unobtainable_reason": statement.unobtainable_reason,
    }


def write_coverage_statements(
    directory: Path, inputs: Sequence[CoverageInputs]
) -> tuple[Path, ...]:
    """Write one Coverage Statement per House, both formats.

    **Every House gets a statement, including one with no route.** If the Rajya
    Sabha is absent, its statement says so in `unobtainable_reason` rather than
    being omitted -- an omitted statement reads as "not looked at", and
    `data-model.md` requires the opposite: "MUST say so explicitly rather than
    implying both Houses are covered".
    """
    statements = [(build_coverage_statement(i), i) for i in inputs]
    rows = [coverage_row(statement, i) for statement, i in statements]
    ndjson_path, csv_path = write_both(Path(directory), COVERAGE_STEM, rows)
    return (ndjson_path, csv_path)


def render(statement: CoverageStatement, inputs: CoverageInputs) -> str:
    """The maintainer-facing text `make coverage` prints."""
    rate = statement.resolution_rate
    lines = [
        f"Coverage Statement -- {statement.house.value}",
        f"  period                : {statement.period_start} .. {statement.period_end}",
        f"  sessions covered      : {len(statement.sessions_covered)}",
        f"  questions             : {rate.total_questions:,}",
        f"  resolution (automatic): {rate.resolved_automatic:,} / {rate.total_questions:,}"
        f"  = {rate.automatic:.2%}"
        f"  [{'meets' if rate.automatic >= SC_002_TARGET else 'BELOW'} the {SC_002_TARGET:.0%} target]",
        f"  resolution (assisted) : {rate.resolved_assisted:,} / {rate.total_questions:,}"
        f"  = {rate.assisted:.2%}"
        f"  [{'meets' if statement.meets_sc_002 else 'BELOW'} the {SC_002_TARGET:.0%} target]",
        f"  assertions in effect  : {inputs.assertions_in_effect}"
        f"  (overriding an automatic match: "
        f"{inputs.assertions_overriding_an_automatic_match})",
        f"  ministry ids          : {inputs.ministry_ids}"
        f"  from {inputs.ministry_names_observed} observed name(s)",
        f"  ministry review backlog: "
        f"{inputs.ministry_names_without_confirmed_mapping} name(s) with no confirmed mapping",
        f"  reference-only names  : "
        f"{inputs.ministry_names_in_reference_set_with_no_questions} (no id, not published)",
        f"  published sets       : {', '.join(inputs.published_sets) or 'not stated'}",
        f"  freshness             : {statement.last_known_good.value}",
        "  question source       : "
        + (
            ", ".join(
                f"LS{e.get('term')}={e.get('mode')}"
                + (f"@{e.get('checkpoint_written_at')}" if e.get("mode") == "resumed" else "")
                for e in inputs.question_source_by_term
            )
            or "not stated"
        ),
    ]
    for group in inputs.ministry_name_groups_merged_by_normalisation:
        lines.append(f"  normalisation merged  : {json.dumps(list(group), ensure_ascii=False)}")
    for gap in statement.known_gaps:
        lines.append(f"  known gap             : {gap}")
    if statement.unobtainable_reason:
        lines.append(f"  NOT COVERED           : {statement.unobtainable_reason}")
    return "\n".join(lines)
