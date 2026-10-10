"""In-band licence and attribution, on the manifest and the coverage statement only.

**Owner decision 2026-10-10.** CC BY 4.0 requires a consumer to attribute, and
until now nothing *inside* the dataset said what to attribute or where to link.
`DATA-LICENSE.md` reaches a consumer who takes the whole `published` branch; it
does not reach one who takes a single file. So five fields now travel with the
dataset -- `license`, `attribution`, `project_url`, `license_file` and
`license_scope`.

**They go on `manifest.json` and `coverage.jsonl`/`.csv` and NOWHERE else.** Not
on question rows, not on aggregate rows, not in the search index. Two reasons,
and the second is the load-bearing one:

1. **Bytes.** The attribution string plus the scope note is about 300 bytes. On
   92,942 subject-trend rows that is the 179 MiB mistake T064 already made once
   by carrying the counting basis inline; the fix there was a reference, and the
   lesson is not to repeat the cause.
2. **Meaning.** A per-row licence field would assert that *that row* is CC BY
   4.0, and `DATA-LICENSE.md` says the opposite: a published row mixes this
   project's added work with source records this project cannot license. The
   claim is true of the dataset as a whole and false of a row, so it belongs on
   the two files that describe the whole.

`src/sansad/publish/attribution.py` is the single definition. These tests exist
to stop three things drifting apart: the constant, the two published files, and
the human-readable line in `DATA-LICENSE.md`.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_LICENCE = REPO_ROOT / "DATA-LICENSE.md"

#: The files permitted to carry the licence fields. Everything else must not.
WHOLE_DATASET_FILES = ("manifest.json", "coverage.jsonl", "coverage.csv")


@pytest.fixture
def members():
    from sansad.ingest.members import load_members

    rows = json.loads(
        (REPO_ROOT / "tests" / "fixtures" / "roster.json").read_text(encoding="utf-8")
    )["members"]
    return load_members(rows, last_refreshed="2026-10-09")


@pytest.fixture
def coverage_dir(tmp_path):
    """A real coverage statement, written by the real publish layer."""
    from sansad.model._common import House
    from sansad.publish.coverage import CoverageInputs, write_coverage_statements

    write_coverage_statements(
        tmp_path,
        [
            CoverageInputs(
                house=House.LOK_SABHA,
                period_start="2019-06-21",
                period_end="2026-08-12",
                sessions_covered=("lok-sabha/17/1",),
                last_refreshed="2026-10-09",
                total_questions=10,
                resolved_automatic=9,
                resolved_assisted=10,
            )
        ],
    )
    return tmp_path


@pytest.fixture
def manifest_path(tmp_path):
    """A real manifest, written by the real publish layer."""
    from sansad.publish.partitions import write_manifest

    return write_manifest(
        tmp_path / "m",
        last_refreshed="2026-10-09",
        sets={"by-session": {"files": 2, "records": 10}},
    )


# ---------------------------------------------------------------------------
# (a) both whole-dataset files carry every field, and the values ARE the
#     constant -- not a copy that happens to match today.
# ---------------------------------------------------------------------------


def _expected() -> dict[str, str]:
    from sansad.publish.attribution import LICENCE_FIELDS

    return dict(LICENCE_FIELDS)


def test_the_constant_module_defines_exactly_the_five_fields() -> None:
    from sansad.publish import attribution

    assert set(attribution.LICENCE_FIELDS) == {
        "license",
        "attribution",
        "project_url",
        "license_file",
        "license_scope",
    }
    assert attribution.LICENCE_FIELDS["license"] == "CC-BY-4.0"
    assert attribution.LICENCE_FIELDS["license_file"] == "DATA-LICENSE.md"
    assert attribution.LICENCE_FIELDS["project_url"].startswith("https://")
    # The scope note must actually say the records are not covered, and point
    # somewhere a reader can go.
    scope = attribution.LICENCE_FIELDS["license_scope"]
    assert "added work" in scope
    assert "DATA-LICENSE.md" in scope
    assert len(scope.splitlines()) == 1, "one line, so it survives a CSV cell"


def test_the_manifest_carries_every_licence_field(manifest_path) -> None:
    body = json.loads(manifest_path.read_text(encoding="utf-8"))
    for field, value in _expected().items():
        assert field in body, f"manifest.json is missing {field!r}"
        assert body[field] == value, f"manifest.json {field!r} != the constant"


def test_the_coverage_statement_carries_every_licence_field(coverage_dir) -> None:
    from sansad.publish.formats import read_csv, read_ndjson

    for rows in (
        read_ndjson(coverage_dir / "coverage.jsonl"),
        read_csv(coverage_dir / "coverage.csv"),
    ):
        assert rows
        for row in rows:
            for field, value in _expected().items():
                assert field in row, f"coverage is missing {field!r}"
                assert row[field] == value, f"coverage {field!r} != the constant"


def test_every_house_gets_the_fields_including_one_with_no_route(tmp_path) -> None:
    """A House with nothing published still carries the licence: its statement
    is part of the dataset, and a consumer reading only it must still be told."""
    from sansad.model._common import House
    from sansad.publish.coverage import CoverageInputs, write_coverage_statements
    from sansad.publish.formats import read_ndjson

    write_coverage_statements(
        tmp_path,
        [
            CoverageInputs(
                house=House.RAJYA_SABHA,
                period_start="2019-06-21",
                period_end="2026-08-12",
                sessions_covered=(),
                last_refreshed="2026-10-09",
                total_questions=0,
                resolved_automatic=0,
                resolved_assisted=0,
                unobtainable_reason="route returns HTTP 403; cause unverified",
            )
        ],
    )
    row = read_ndjson(tmp_path / "coverage.jsonl")[0]
    assert row["house"] == "rajya-sabha"
    for field, value in _expected().items():
        assert row[field] == value


# ---------------------------------------------------------------------------
# (b) DATA-LICENSE.md and the constant cannot drift.
# ---------------------------------------------------------------------------


def test_the_attribution_line_in_data_licence_equals_the_constant() -> None:
    """The human-readable licence and the machine-readable field are one string.

    If they drift, a consumer following the file attributes differently from one
    following the data, and neither is wrong.
    """
    from sansad.publish.attribution import ATTRIBUTION

    text = DATA_LICENCE.read_text(encoding="utf-8")
    quoted = [
        line[2:].strip()
        for line in text.splitlines()
        if line.startswith("> ") and "Contains data from" in line
    ]
    assert quoted, "DATA-LICENSE.md has no blockquoted attribution line"
    assert len(quoted) == 1, f"expected one attribution line, found {len(quoted)}"
    assert quoted[0] == ATTRIBUTION


def test_the_project_url_and_licence_file_appear_in_data_licence() -> None:
    from sansad.publish.attribution import LICENSE_FILE, PROJECT_URL

    text = DATA_LICENCE.read_text(encoding="utf-8")
    assert PROJECT_URL in text
    assert DATA_LICENCE.name == LICENSE_FILE


def test_the_spdx_id_matches_the_licence_the_file_grants() -> None:
    from sansad.publish.attribution import LICENSE_SPDX

    assert LICENSE_SPDX == "CC-BY-4.0"
    text = DATA_LICENCE.read_text(encoding="utf-8")
    assert "CC BY 4.0" in text
    assert "creativecommons.org/licenses/by/4.0" in text


# ---------------------------------------------------------------------------
# (c) no row-level file carries any of them.
# ---------------------------------------------------------------------------


@pytest.fixture
def row_level_tree(tmp_path, members, question_records):
    """Every row-producing published set, written by the real publish layer.

    Deliberately NOT the manifest and NOT the coverage statement -- this is the
    set of files the fields must stay out of.
    """
    from sansad.model.ministry import Ministry
    from sansad.publish.aggregates import write_aggregates
    from sansad.publish.partitions import write_partitions
    from sansad.publish.reference import (
        constituencies_from,
        sessions_from,
        write_reference_sets,
    )
    from sansad.publish.search_index import write_search_index
    from sansad.resolve import resolve_questions
    from sansad.views.composition import compose
    from sansad.views.ministry_profile import ministry_profiles
    from sansad.views.subject_trends import subject_trends

    records = []
    for name in ("co_asked.json", "unresolvable.json", "ambiguous.json", "shared_ques_no.json"):
        records.extend(question_records(name))
    resolved = resolve_questions(records, members)

    write_partitions(tmp_path, resolved.questions)
    write_reference_sets(
        tmp_path,
        members=members,
        ministries=[
            Ministry(ministry_id=q.ministry_id, canonical_name=q.ministry_id)
            for q in {q.ministry_id: q for q in resolved.questions}.values()
        ],
        sessions=sessions_from(resolved.questions),
        constituencies=constituencies_from(members),
    )
    write_aggregates(
        tmp_path,
        compositions=[compose(members, term=18)],
        trends=subject_trends(resolved.questions),
        profiles=ministry_profiles(resolved.questions),
    )
    write_search_index(tmp_path, resolved.questions)
    return tmp_path


def _declared_field_names(path: Path) -> set[str]:
    """Every name in a FIELD-NAME position in one published file.

    Parses rather than greps, and the difference is not academic. `license` is a
    real parliamentary subject word -- "Licensing of Private Security Agencies"
    -- so it is a genuine TERM in `search/subject-index.json`, where the string
    `"license"` appears in VALUE position. A substring scan for `"license"`
    reports that as a violation; it is not one, and the index format was
    deliberately changed at T072 to put every token in value position precisely
    so that key and value could be told apart. A test that could not tell them
    apart would either fail on clean data or, worse, pass by accident -- the
    first draft of this test read only the first 4096 bytes of each file and
    passed because the sorted terms array reaches `license` long after that.
    """
    if path.suffix == ".jsonl":
        names: set[str] = set()
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    names |= set(json.loads(line))
        return names
    if path.suffix == ".json":
        body = json.loads(path.read_text(encoding="utf-8"))
        return set(body) if isinstance(body, dict) else set()
    if path.suffix == ".csv":
        with path.open(encoding="utf-8", newline="") as fh:
            return set(next(csv.reader(fh), []))
    return set()


def _scan_row_level(root: Path) -> tuple[int, dict[str, list[str]]]:
    fields = set(_expected())
    offenders: dict[str, list[str]] = {}
    scanned = 0
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if path.name in WHOLE_DATASET_FILES:
            continue
        scanned += 1
        hits = sorted(fields & _declared_field_names(path))
        if hits:
            offenders[str(path.relative_to(root))] = hits
    return scanned, offenders


def test_no_row_level_file_carries_a_licence_field(row_level_tree) -> None:
    """Field-name scan over every published file that is not whole-dataset."""
    scanned, offenders = _scan_row_level(row_level_tree)
    assert scanned > 5, f"only {scanned} row-level files scanned; the tree is too thin"
    assert offenders == {}, f"licence fields leaked into row-level files: {offenders}"


def test_the_scan_would_catch_a_leak(row_level_tree) -> None:
    """The scan above must be able to fail. Plant one field in one row file."""
    victim = next(iter(sorted((row_level_tree / "by-session").glob("*.jsonl"))))
    rows = [json.loads(ln) for ln in victim.read_text(encoding="utf-8").splitlines() if ln.strip()]
    rows[0]["license"] = "CC-BY-4.0"
    victim.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    _, offenders = _scan_row_level(row_level_tree)
    assert offenders, "the scan did not notice a planted licence field"
    assert offenders[
        victim.name if victim.parent == row_level_tree else f"by-session/{victim.name}"
    ] == ["license"]


def test_the_question_row_schema_does_not_declare_them(members, question_records) -> None:
    """The structural half: the row dicts themselves, before any file exists."""
    from sansad.publish.formats import rows_for
    from sansad.resolve import resolve_questions

    resolved = resolve_questions(question_records("co_asked.json"), members)
    rows = rows_for(resolved.questions)
    assert rows
    for row in rows:
        assert set(row) & set(_expected()) == set()


def test_a_licence_word_in_value_position_is_not_a_violation() -> None:
    """The counter-example, pinned against the LIVE index so it stays true.

    `license` is an ordinary subject word and a legitimate index term. This test
    asserts it is present in the index's terms -- i.e. in value position -- and
    that the scan above still reports the index clean. If the index format ever
    moves terms back into key position, this fails and so does the guard.
    """
    index = REPO_ROOT / "data" / "published" / "search" / "subject-index.json"
    if not index.is_file():
        pytest.skip("search index not built -- NOT AUDITED, not a pass")

    body = json.loads(index.read_text(encoding="utf-8"))
    assert "license" in set(body["terms"]), "expected `license` as a real subject term"
    assert set(_expected()) & set(body) == set(), "a licence field reached the index's keys"


def test_the_live_published_tree_is_clean_if_one_has_been_built() -> None:
    """The same scan against the REAL dataset, which the fixtures cannot stand
    in for: 1,768 files across every axis. Absent means NOT AUDITED, which is
    reported rather than passed -- a dataset that was never built cannot be
    asserted about."""
    root = REPO_ROOT / "data" / "published"
    if not root.is_dir() or not any(root.rglob("*.jsonl")):
        pytest.skip("data/published/ not built -- NOT AUDITED, not a pass")

    scanned, offenders = _scan_row_level(root)
    assert scanned > 100, f"only {scanned} files scanned"
    assert offenders == {}, f"licence fields leaked into the live dataset: {offenders}"
