"""T055 -- one full ingestion and publish, with no prompting whatsoever.

`quickstart.md` Setup: "`make refresh` must complete without prompting for
anything. A prompt is a failure against FR-009." So every input is an argument
or an environment variable with a stated default, and nothing here reads stdin.

**Two sources, chosen explicitly, never guessed.**

- `--source scratch` (the default) reads the already-fetched window from
  `$SANSAD_SCRATCH` and **makes no network request at all**. This is what the
  offline dry run uses, and it is the default deliberately: a command that
  reaches the upstream unless told otherwise is one that will reach it by
  accident.
- `--source upstream` fetches. It exists so the scheduled workflow has one
  command to call, and it is the only path that touches the network.

**`data/published/` is git-ignored on `main`.** `make refresh` writes it
locally; publishing is the workflow's job (T058), which force-pushes a single
commit to the `published` branch on success and pushes **nothing** on a failed
or partial refresh.

**On failure, the previous snapshot is retained** (T054) and the process exits
non-zero. The exit code is for the runner; the retained snapshot is for the
visitor; the signal log is for the maintainer. Those are three different
audiences and they are not served by one mechanism.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sansad.ingest.members import load_members
from sansad.ingest.questions import (
    DuplicateRecord,
    QuestionRecord,
    load_question_records,
)
from sansad.model._common import House
from sansad.model.coverage_statement import Freshness
from sansad.publish.coverage import (
    CoverageInputs,
    build_coverage_statement,
    render,
    write_coverage_statements,
)
from sansad.publish.formats import rows_for, write_both
from sansad.publish.last_known_good import retain_previous
from sansad.publish.partitions import write_manifest, write_partitions
from sansad.publish.reference import (
    MinistryRegistry,
    assign_ministry_ids,
    constituencies_from,
    ministry_observations,
    sessions_from,
    write_reference_sets,
)
from sansad.resolve import resolve_questions
from sansad.resolve.assertions import load_assertions, load_ministry_renames
from sansad.signals.alerts import SignalLog, ingestion_failure

__all__ = ["main", "run_refresh"]

#: The terms the covered window spans.
WINDOW_TERMS: tuple[int, ...] = (17, 18)
DEFAULT_PUBLISHED_DIR = "data/published"
#: Published set name, shared with `tools/verify_joins.py`.
RESOLUTION_STEM = "resolution-records"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _scratch_root() -> Path:
    raw = os.environ.get("SANSAD_SCRATCH") or ""
    if not raw:
        raise SystemExit(
            "SANSAD_SCRATCH is not set. --source scratch reads the already-fetched "
            "window from it, and this command will not look for upstream bodies "
            "inside the repository tree (Constitution Principle V)."
        )
    resolved = Path(os.path.realpath(Path(raw).expanduser()))
    root = repo_root()
    if resolved == root or root in resolved.parents:
        raise SystemExit(
            f"REFUSED: SANSAD_SCRATCH resolves inside the repository.\n"
            f"  resolved  : {resolved}\n  repo root : {root}"
        )
    return resolved


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _load_from_scratch(
    scratch: Path, last_refreshed: str, duplicates: list[DuplicateRecord]
) -> tuple[list[dict[str, Any]], list[QuestionRecord]]:
    roster_path = scratch / "roster_ls.jsonl"
    if not roster_path.is_file():
        raise SystemExit(f"missing roster at {roster_path}")
    roster = _read_jsonl(roster_path)

    records: list[QuestionRecord] = []
    for term in WINDOW_TERMS:
        path = scratch / f"questions_ls{term}.jsonl"
        if not path.is_file():
            raise SystemExit(f"missing questions for term {term} at {path}")
        records.extend(
            load_question_records(
                _read_jsonl(path), last_refreshed=last_refreshed, duplicates=duplicates
            )
        )
    return roster, records


def _load_from_upstream(last_refreshed: str, duplicates: list[DuplicateRecord], signals: SignalLog):
    """Fetch the window. The only path here that touches the network."""
    from sansad.ingest.members import fetch_members
    from sansad.ingest.questions import fetch_question_records

    members = fetch_members(timeout=120.0, last_refreshed=last_refreshed)
    records: list[QuestionRecord] = []
    for term in WINDOW_TERMS:
        records.extend(
            fetch_question_records(
                loksabha=term,
                last_refreshed=last_refreshed,
                signals=signals,
                duplicates=duplicates,
            )
        )
    return members, records


def run_refresh(
    *,
    source: str = "scratch",
    published_dir: Path | None = None,
    previous_dir: Path | None = None,
    pool_by_term: bool = True,
) -> int:
    """One full ingestion and publish. Returns a process exit code."""
    started = datetime.now(UTC)
    last_refreshed = started.date().isoformat()
    out = Path(published_dir or (repo_root() / DEFAULT_PUBLISHED_DIR))
    signals = SignalLog()
    duplicates: list[DuplicateRecord] = []

    try:
        if source == "scratch":
            roster_records, question_records = _load_from_scratch(
                _scratch_root(), last_refreshed, duplicates
            )
            members = load_members(roster_records, last_refreshed=last_refreshed)
        elif source == "upstream":
            members, question_records = _load_from_upstream(last_refreshed, duplicates, signals)
        else:  # pragma: no cover - argparse constrains this
            raise SystemExit(f"unknown --source {source!r}")
    except SystemExit:
        raise
    except Exception as exc:
        signals.add(ingestion_failure(stage="load", reason=type(exc).__name__))
        print(f"refresh: FAILED during load -- {type(exc).__name__}", file=sys.stderr)
        found = retain_previous(
            previous_dir,
            out,
            reason=f"ingestion failed at load ({type(exc).__name__})",
            today=last_refreshed,
        )
        print(f"refresh: {found.reason}", file=sys.stderr)
        print(signals.render(), file=sys.stderr)
        return 1

    print(f"refresh: loaded {len(members):,} member(s), {len(question_records):,} question(s)")
    if duplicates:
        for duplicate in duplicates:
            print(f"refresh: declared upstream duplicate -- {duplicate.gap_note}")

    # --- resolve ------------------------------------------------------------
    assertions = load_assertions()
    resolved_by_term: list[Any] = []
    published_questions: list[Any] = []
    totals = {"total": 0, "automatic": 0, "assisted": 0}
    overrides = 0

    for term in WINDOW_TERMS:
        term_records = [
            r for r in question_records if r.question.session.split("/")[1] == str(term)
        ]
        if not term_records:
            continue
        pool = (
            [m for m in members if any(t.number == term for t in m.terms)]
            if pool_by_term
            else list(members)
        )
        result = resolve_questions(term_records, pool, assertions=assertions)
        resolved_by_term.append(result)
        published_questions.extend(result.questions)
        totals["total"] += result.total_questions
        totals["automatic"] += result.resolved_automatic
        totals["assisted"] += result.resolved_assisted
        for form in assertions:
            automatic = result.automatic_outcomes.get(form)
            if automatic is not None and automatic.is_resolved:
                asserted = (assertions[form].member_id,)
                if automatic.member_ids != asserted:
                    overrides += 1

    print(
        f"refresh: resolved {totals['assisted']:,}/{totals['total']:,} "
        f"({totals['assisted'] / totals['total']:.2%} assisted; "
        f"{totals['automatic'] / totals['total']:.2%} automatic)"
    )

    # --- ministry identity --------------------------------------------------
    registry = MinistryRegistry.build(
        ministry_observations(question_records), load_ministry_renames()
    )
    published_questions = list(assign_ministry_ids(published_questions, registry))
    observations = ministry_observations(question_records)
    print(
        f"refresh: {len(registry.ministries)} ministry id(s) from "
        f"{len(observations)} observed name(s); "
        f"{len(registry.fold_groups)} group(s) merged by normalisation"
    )

    # --- publish ------------------------------------------------------------
    out.mkdir(parents=True, exist_ok=True)
    partitions = write_partitions(out, published_questions)

    # The resolution records are a published set in their own right --
    # `contracts/published-dataset.md`: "Resolution records | One record per
    # name form encountered, with its outcome (FR-005)." Without them on disk
    # guarantee 3 is a promise with nothing behind it, and `make verify-joins`
    # has nothing to check against.
    resolution_records = [record for result in resolved_by_term for record in result.records]
    resolution_files = write_both(out, RESOLUTION_STEM, rows_for(resolution_records))
    reference = write_reference_sets(
        out,
        members=sorted(members, key=lambda m: m.member_id),
        ministries=[registry.ministries[k] for k in sorted(registry.ministries)],
        sessions=sessions_from(published_questions),
        constituencies=constituencies_from(members),
    )

    dates = sorted(q.date for q in published_questions if q.date)
    sessions_covered = sorted({q.session for q in published_questions})
    coverage_inputs = CoverageInputs(
        house=House.LOK_SABHA,
        period_start=dates[0] if dates else "not stated",
        period_end=dates[-1] if dates else "not stated",
        sessions_covered=sessions_covered,
        last_refreshed=last_refreshed,
        total_questions=totals["total"],
        resolved_automatic=totals["automatic"],
        resolved_assisted=totals["assisted"],
        assertions_in_effect=len(assertions),
        assertions_overriding_an_automatic_match=overrides,
        duplicate_records_declared=[d.question_id for d in duplicates],
        ministry_ids=len(registry.ministries),
        ministry_names_observed=len(observations),
        ministry_names_without_confirmed_mapping=len(registry.names_without_confirmed_mapping),
        ministry_name_groups_merged_by_normalisation=registry.fold_groups,
        ministry_names_in_reference_set_with_no_questions=len(registry.reference_only),
        freshness=Freshness.CURRENT,
    )
    rajya_sabha = CoverageInputs(
        house=House.RAJYA_SABHA,
        period_start="not stated",
        period_end="not stated",
        sessions_covered=(),
        last_refreshed=last_refreshed,
        total_questions=0,
        resolved_automatic=0,
        resolved_assisted=0,
        unobtainable_reason=(
            "No Rajya Sabha route has been identified. GET /api_rs/members returns "
            "403 where every sibling path returns 404, cause UNVERIFIED. This "
            "release covers the Lok Sabha ONLY (FR-001, FR-013)."
        ),
    )
    coverage_files = write_coverage_statements(out, [coverage_inputs, rajya_sabha])

    sets = {p.axis: {"files": p.files, "records": p.records} for p in partitions}
    sets["reference"] = {
        "files": len(reference.files),
        "records": sum(reference.records.values()),
    }
    sets["coverage"] = {"files": len(coverage_files), "records": 2}
    sets[RESOLUTION_STEM] = {
        "files": len(resolution_files),
        "records": len(resolution_records),
    }
    write_manifest(
        out,
        last_refreshed=last_refreshed,
        sets=sets,
        extra={
            "window_questions": totals["total"],
            "resolution_rate_automatic": round(totals["automatic"] / totals["total"], 6),
            "resolution_rate_including_assertions": round(totals["assisted"] / totals["total"], 6),
            "duplicate_records_declared": [d.question_id for d in duplicates],
            "source": source,
        },
    )

    print()
    print(render(build_coverage_statement(coverage_inputs), coverage_inputs))
    print()
    files = sum(s["files"] for s in sets.values()) + 1  # + the manifest
    print(f"refresh: wrote {files:,} file(s) to {out}")
    if not signals.should_publish:
        print(signals.render(), file=sys.stderr)
        return 1
    if len(signals):
        print(signals.render(), file=sys.stderr)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sansad-refresh",
        description="One full ingestion and publish. Prompts for nothing (FR-009).",
    )
    parser.add_argument(
        "--source",
        choices=("scratch", "upstream"),
        default="scratch",
        help=(
            "scratch (default): read the already-fetched window from $SANSAD_SCRATCH "
            "and make no network request. upstream: fetch."
        ),
    )
    parser.add_argument("--published-dir", type=Path, default=None)
    parser.add_argument(
        "--previous",
        type=Path,
        default=None,
        help=(
            "the previous snapshot, for last-known-good on failure. A directory "
            "locally; a checkout of the `published` branch in CI."
        ),
    )
    parser.add_argument(
        "--full-pool",
        action="store_true",
        help=(
            "match against every member ever, not just the term's. The pessimistic "
            "bound; the per-term pool is a correctness constraint and the default."
        ),
    )
    args = parser.parse_args(argv)
    return run_refresh(
        source=args.source,
        published_dir=args.published_dir,
        previous_dir=args.previous,
        pool_by_term=not args.full_pool,
    )


if __name__ == "__main__":
    raise SystemExit(main())
