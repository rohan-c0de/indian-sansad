"""Fixture loading for the Phase 4 tests.

Everything here reads `tests/fixtures/`, which is hand-authored by policy
(T034, `tests/fixtures/README.md`). **No test in this suite fetches anything.**
There is no network call in this directory and no recorded upstream response
behind any of these fixtures.

Two member sets are exposed rather than one, and the difference between them is
load-bearing:

* `roster_members` -- built from `roster.json` alone. Each member carries the
  one canonical name form the roster gives and no extra variants. This is the
  set that exercises the matcher's later tiers, because a form the roster does
  not spell out has to be *matched* rather than looked up.

* `variant_members` -- `roster.json` enriched with the `name_variants` from
  `variants.json`. This models a roster that serves several name forms per
  person, which the real one does (`mpFirstLastName` and `mpLastFirstName` are
  two forms of the same person, `spike/fetch_slice.py`). It is the set
  `quickstart.md` scenario 1 describes, where the required pair
  `Shri Sunil Kumar Singh` / `Singh, Sunil K.` is present as two forms of one
  identity.

Using one set for everything would hide which mechanism did the work -- the
same reason `sansad.resolve.match` records a `method` per join.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

#: A fixed refresh date, so FR-016's "every published set carries the date it
#: was last rebuilt" is asserted against a real date rather than against the
#: NOT_STATED placeholder a dateless fixture would otherwise produce -- which
#: is truthy and would pass the check while testing nothing.
FIXTURE_REFRESHED_ON = "2026-10-09"


def _read(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture(scope="session")
def roster_records() -> list[dict[str, Any]]:
    """The raw (hand-written) roster records, as an ingest boundary sees them."""
    return list(_read("roster.json")["members"])


@pytest.fixture(scope="session")
def variant_pairs() -> list[dict[str, Any]]:
    return list(_read("variants.json")["variant_pairs"])


@pytest.fixture(scope="session")
def roster_members(roster_records):
    """Members with the roster's single name form each."""
    from sansad.ingest.members import load_members

    return load_members(roster_records, last_refreshed=FIXTURE_REFRESHED_ON)


@pytest.fixture(scope="session")
def variant_members(roster_records, variant_pairs):
    """Members carrying every name form `variants.json` records for them."""
    from sansad.ingest.members import load_members
    from sansad.resolve.identity import add_name_variants

    members = load_members(roster_records, last_refreshed=FIXTURE_REFRESHED_ON)
    by_id = {m.member_id: m for m in members}
    for pair in variant_pairs:
        member = by_id[pair["member_id"]]
        by_id[member.member_id] = add_name_variants(member, pair["name_variants"])
    return tuple(by_id[m.member_id] for m in members)


@pytest.fixture
def question_records():
    """Map a fixture file of question-route records to `QuestionRecord`s.

    Returns a callable so one test can load several fixtures.
    """
    from sansad.ingest.questions import load_question_records

    def _load(name: str):
        body = _read(name)
        return load_question_records(body["listOfQuestions"], last_refreshed=FIXTURE_REFRESHED_ON)

    return _load
