"""T079's dataset side: the per-session search digest and the asker-name lookup.

**Owner decision 2026-10-10.** T079 resolves a search hit through a purpose-built
per-session digest, not through the `by-session` question partitions. The gate
result that forced it stands: the first 25 results for a common word cost
**4,348,529 B** with one partition — **+3.9%** over T019's 4,183,979 B budget —
and **+73.0%** for a two-partition query. The digest exists to make a search
result affordable, and nothing else.

What these tests protect, in order of how badly each would fail:

1. **No question is lost.** The digest must carry every published question.
2. **No record drifts.** Every digest record must still equal the question
   record it was derived from — checked by reading the published `by-session`
   files, not by calling the builder, so a builder bug cannot validate itself.
3. **Principle V.** The name lookup publishes four fields about real people. A
   fifth would be a new personal-attribute route that never passed the ingest
   allowlist, because the lookup is built from already-published records rather
   than from the upstream payload.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLISHED = REPO_ROOT / "data" / "published"
DIGEST_DIR = PUBLISHED / "search" / "digest"
NAMES = PUBLISHED / "search" / "asker-names.jsonl"

#: Exactly what a digest record may carry. Anything else is a finding.
DIGEST_FIELDS = frozenset(
    {"question_id", "subject", "date", "ministry_id", "resolution_status", "asking_members"}
)

#: Exactly what the name lookup may carry. Four fields, all inside the FR-008
#: published set; `member_id` is this project's own.
NAME_FIELDS = frozenset({"member_id", "canonical_name", "party", "state"})


def _rows(path: Path) -> list[dict]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


@pytest.fixture(scope="module")
def digest_rows() -> list[dict]:
    if not DIGEST_DIR.is_dir():
        pytest.fail("data/published/search/digest/ does not exist")
    rows: list[dict] = []
    for path in sorted(DIGEST_DIR.glob("*.jsonl")):
        rows.extend(_rows(path))
    return rows


@pytest.fixture(scope="module")
def published_questions() -> dict[str, dict]:
    """Every published question, read INDEPENDENTLY of the digest builder."""
    out: dict[str, dict] = {}
    for path in sorted((PUBLISHED / "by-session").glob("*.jsonl")):
        for row in _rows(path):
            out[row["question_id"]] = row
    return out


@pytest.fixture(scope="module")
def name_rows() -> list[dict]:
    if not NAMES.is_file():
        pytest.fail("data/published/search/asker-names.jsonl does not exist")
    return _rows(NAMES)


# ---------------------------------------------------------------------------
# 1. Nothing is lost
# ---------------------------------------------------------------------------


def test_the_digest_carries_every_published_question(digest_rows, published_questions) -> None:
    assert len(published_questions) == 95268, (
        f"the published window is {len(published_questions)}, not 95,268"
    )
    assert len(digest_rows) == len(published_questions)
    assert len(digest_rows) == 95268


def test_every_question_id_appears_exactly_once(digest_rows) -> None:
    ids = [row["question_id"] for row in digest_rows]
    assert len(set(ids)) == len(ids), "a question_id is duplicated across digest files"


def test_there_is_one_digest_file_per_published_session(digest_rows) -> None:
    files = sorted(DIGEST_DIR.glob("*.jsonl"))
    sessions = {"/".join(row["question_id"].split("/")[:3]) for row in digest_rows}
    assert len(files) == len(sessions), f"{len(files)} files for {len(sessions)} sessions"
    assert len(files) == 21


# ---------------------------------------------------------------------------
# 2. Nothing drifts — checked against the published records, not the builder
# ---------------------------------------------------------------------------


def test_every_digest_record_equals_its_published_question(
    digest_rows, published_questions
) -> None:
    mismatches = []
    for row in digest_rows:
        source = published_questions.get(row["question_id"])
        if source is None:
            mismatches.append(f"{row['question_id']}: not in by-session")
            continue
        for field in ("subject", "date", "ministry_id", "resolution_status"):
            if row[field] != source[field]:
                mismatches.append(f"{row['question_id']}.{field}")
        if list(row["asking_members"]) != list(source["asking_members"] or []):
            mismatches.append(f"{row['question_id']}.asking_members")
    assert mismatches == [], f"{len(mismatches)} digest record(s) drifted: {mismatches[:5]}"


def test_a_digest_record_carries_no_field_outside_the_allowed_set(digest_rows) -> None:
    extra: set[str] = set()
    for row in digest_rows:
        extra |= set(row) - DIGEST_FIELDS
    assert extra == set(), f"fields outside the allowed set: {sorted(extra)}"
    for row in digest_rows[:200]:
        assert set(row) == DIGEST_FIELDS, f"missing fields: {sorted(DIGEST_FIELDS - set(row))}"


def test_each_digest_file_is_sorted_so_two_builds_are_byte_identical(digest_rows) -> None:
    for path in sorted(DIGEST_DIR.glob("*.jsonl")):
        ids = [row["question_id"] for row in _rows(path)]
        assert ids == sorted(ids), f"{path.name} is not sorted by question_id"


# ---------------------------------------------------------------------------
# 3. Principle V — the name lookup
# ---------------------------------------------------------------------------


def test_every_asking_member_resolves_in_the_lookup(digest_rows, name_rows) -> None:
    known = {row["member_id"] for row in name_rows}
    askers = {m for row in digest_rows for m in row["asking_members"]}
    unresolved = sorted(askers - known)
    assert unresolved == [], f"{len(unresolved)} asker id(s) do not resolve: {unresolved[:5]}"


def test_the_lookup_contains_no_member_who_is_not_an_asker(digest_rows, name_rows) -> None:
    """Principle V is a bound on what is published, so a lookup that shipped
    every member would publish names the search can never show."""
    askers = {m for row in digest_rows for m in row["asking_members"]}
    listed = {row["member_id"] for row in name_rows}
    surplus = sorted(listed - askers)
    assert surplus == [], f"{len(surplus)} member(s) listed but never an asker: {surplus[:5]}"
    assert listed == askers


def test_the_lookup_carries_no_field_outside_the_allowed_four(name_rows) -> None:
    extra: set[str] = set()
    for row in name_rows:
        extra |= set(row) - NAME_FIELDS
    assert extra == set(), f"fields outside the allowed set: {sorted(extra)}"
    for row in name_rows:
        assert set(row) == NAME_FIELDS


def test_every_lookup_field_is_inside_the_member_published_set() -> None:
    """The four fields are not chosen here; they are a subset of the FR-008 set."""
    from sansad.model.member import PUBLISHED_FIELDS

    allowed = set(PUBLISHED_FIELDS)
    assert allowed >= NAME_FIELDS, f"not published Member fields: {sorted(NAME_FIELDS - allowed)}"


def test_the_lookup_is_sorted_and_unique(name_rows) -> None:
    ids = [row["member_id"] for row in name_rows]
    assert ids == sorted(ids)
    assert len(set(ids)) == len(ids)


def test_the_lookup_matches_the_published_member_reference_set(name_rows) -> None:
    """Checked against reference/members.jsonl rather than against the builder."""
    members = {row["member_id"]: row for row in _rows(PUBLISHED / "reference" / "members.jsonl")}
    for row in name_rows:
        source = members.get(row["member_id"])
        assert source is not None, f"{row['member_id']} is not in the member reference set"
        for field in ("canonical_name", "party", "state"):
            assert row[field] == source[field], f"{row['member_id']}.{field} drifted"


# ---------------------------------------------------------------------------
# Formats
# ---------------------------------------------------------------------------


def test_both_formats_match_where_both_exist() -> None:
    """The digest and the lookup are NDJSON only — see the module docstring in
    `src/sansad/publish/search_digest.py` for why. If a CSV is ever added, it
    must carry the same records."""
    from sansad.publish.formats import read_csv, read_ndjson

    for ndjson in [*sorted(DIGEST_DIR.glob("*.jsonl")), NAMES]:
        csv_path = ndjson.with_suffix(".csv")
        if not csv_path.is_file():
            continue
        assert len(read_csv(csv_path)) == len(read_ndjson(ndjson)), f"{csv_path.name} differs"


def test_the_digest_is_cheaper_than_the_partition_it_replaces() -> None:
    """The whole reason it exists. If a digest file ever costs more than the
    by-session partition it stands in for, it is doing harm."""
    worse = []
    for digest in sorted(DIGEST_DIR.glob("*.jsonl")):
        partition = PUBLISHED / "by-session" / digest.name
        if not partition.is_file():
            continue
        if digest.stat().st_size >= partition.stat().st_size:
            worse.append(f"{digest.name}: {digest.stat().st_size} >= {partition.stat().st_size}")
    assert worse == [], f"digest files no cheaper than the partition: {worse}"
