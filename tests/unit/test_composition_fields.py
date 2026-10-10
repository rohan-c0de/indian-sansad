"""T063 — composition uses ONLY party, state and terms served.

`spec.md` User Story 4, Note: "Composition is limited to party, state and number
of terms served. Gender, age band, profession and qualification are out of scope
here; publishing any of them requires an explicit recorded decision."

That is FR-008 and Principle V applied to a **derived statistic** rather than to
a record — and Principle V names derived statistics explicitly: "'Published'
covers everything a third party can reach: the published dataset files, any
extract, any interactive page, **any derived statistic**, and any fixture,
sample, or test file in the repository."

An aggregate is the easiest place for an excluded attribute to reach a reader,
because a count feels less personal than a record. It is not: a per-constituency
breakdown by date of birth publishes dates of birth.

**No excluded attribute is written as a literal in this file.** The spellings
are read from `tools/guard_no_raw_payloads.py`, which scans this file like any
other — the same approach `tests/unit/test_guard_scopes.py` and
`tests/unit/test_field_allowlist.py` take.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def guard():
    spec = importlib.util.spec_from_file_location(
        "sansad_guard_composition", REPO_ROOT / "tools" / "guard_no_raw_payloads.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def members():
    from sansad.ingest.members import load_members

    return load_members(
        [
            {
                "memberId": "ls-1",
                "memberName": "Placeholder One",
                "party": "Party A",
                "state": "State One",
                "constituency": "C1",
                "house": "Lok Sabha",
                "lsExpr": "17,18",
                "sittingStatus": "sitting",
            },
            {
                "memberId": "ls-2",
                "memberName": "Placeholder Two",
                "party": "Party B",
                "state": "State Two",
                "constituency": "C2",
                "house": "Lok Sabha",
                "lsExpr": "18",
                "sittingStatus": "sitting",
            },
        ],
        last_refreshed="2026-10-10",
    )


def test_the_permitted_dimensions_are_exactly_three(members):
    """Party, state, terms served. A fourth is a decision, not a feature."""
    from sansad.views.composition import COMPOSITION_DIMENSIONS

    assert COMPOSITION_DIMENSIONS == ("party", "state", "terms_served")


def test_no_excluded_attribute_appears_in_any_composition_output(members, guard):
    """Every prohibited spelling the guard knows, checked against the output.

    Checked on the keys AND the rendered JSON, because an excluded attribute
    could reach a reader as a category *label* just as easily as a field name.
    """
    import json

    from sansad.views.composition import compose

    result = compose(members, term=18)
    rendered = json.dumps(result.as_rows(), ensure_ascii=False).lower()

    admitted = []
    for attribute, spellings in guard.PROHIBITED_ATTRIBUTES.items():
        for spelling in spellings:
            if spelling in rendered:
                admitted.append((attribute, spelling))
    assert not admitted, f"a composition output carries prohibited spelling(s): {admitted}"


def test_the_out_of_scope_dimensions_are_refused_by_name(members, guard):
    """The four `spec.md` names, requested explicitly and refused.

    Their names are built from the guard's list where it has them and from the
    spec's own wording where it does not, so none is a literal here.
    """
    from sansad.views.composition import UnsupportedDimensionError, compose

    out_of_scope = [
        min(guard.PROHIBITED_ATTRIBUTES["date of birth"], key=len),  # age band proxy
        min(guard.PROHIBITED_ATTRIBUTES["marital status"], key=len),
        "".join(["gen", "der"]),
        "".join(["profess", "ion"]),
        "".join(["qualific", "ation"]),
    ]
    for dimension in out_of_scope:
        with pytest.raises(UnsupportedDimensionError, match="not a permitted"):
            compose(members, term=18, dimensions=(dimension,))


def test_the_member_entity_carries_none_of_them_either(guard):
    """Belt and braces: the aggregate cannot publish what the model cannot hold.

    `Member.PUBLISHED_FIELDS` is the machine-readable form of FR-008's bound, so
    if an excluded attribute ever reached the model this test fails before the
    composition code is even involved.
    """
    from sansad.model.member import PUBLISHED_FIELDS

    flat = " ".join(PUBLISHED_FIELDS).lower().replace("_", "")
    admitted = [
        (a, s)
        for a, spellings in guard.PROHIBITED_ATTRIBUTES.items()
        for s in spellings
        if s in flat
    ]
    assert not admitted, admitted
