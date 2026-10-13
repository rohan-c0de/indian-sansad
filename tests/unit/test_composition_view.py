"""The composition view's claims, checked against the published aggregate. T166.

Three things, and the third is the one the published record makes awkward.

1. **The categories reconcile.** Every dimension, every term, sums to that
   term's `total_members` — including the split the view draws, where twelve
   categories are shown and the rest are stated as a counted group. A chart
   that shows a head and a remainder is only honest if the two add up.

2. **No date is required, and none appears.** Not a style rule: every one of
   the 9,986 term records in the published member reference reads
   `start_date: "not stated"`, and so do all 21 sessions (FR-124). Terms can be
   ordered and counted; they cannot be placed on a calendar.

3. **"Not stated" is a case the published aggregate does not currently have.**
   FR-118 requires a member whose party, state or terms-served is absent to be
   counted in an explicit "not stated" category rather than omitted. Measured:
   **there is no such category in the aggregate, and every dimension sums
   exactly to `total_members`** — so no member is missing any of the three.

   The requirement is therefore satisfied by the data rather than by code that
   runs. What is asserted instead is the property that makes it safe if that
   ever changes: the view **filters no category out**, so a "not stated" row
   appearing in the aggregate would render without an edit. Inventing a
   "not stated" row that is not in the record would be worse than not having
   one.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
AGGREGATE = REPO_ROOT / "data" / "published" / "aggregates" / "composition.jsonl"
VIEW = REPO_ROOT / "web" / "views" / "composition.js"

#: The three dimensions the aggregate publishes, which are also the three
#: FR-008 permits. Gender, age band, profession and qualification are not in
#: the aggregate and may not be published without a recorded decision.
DIMENSIONS = ("party", "state", "terms_served")


@pytest.fixture(scope="module")
def rows() -> list[dict]:
    if not AGGREGATE.is_file():
        pytest.skip(f"{AGGREGATE} is not built; run `make refresh`")
    return [json.loads(line) for line in AGGREGATE.read_text(encoding="utf-8").splitlines()]


def shown_limit() -> int:
    """The view's own `SHOWN` constant, read from the source.

    Read rather than duplicated: a test carrying its own copy of this number
    would keep passing after someone changed the view, which is the one thing
    it exists to prevent.
    """
    match = re.search(r"^const SHOWN = (\d+);", VIEW.read_text(encoding="utf-8"), re.M)
    assert match, "views/composition.js no longer declares a SHOWN constant"
    return int(match.group(1))


def test_the_aggregate_carries_exactly_the_three_permitted_dimensions(rows) -> None:
    assert {r["dimension"] for r in rows} == set(DIMENSIONS)


def test_every_dimension_sums_to_that_terms_total_membership(rows) -> None:
    """FR-118. The categories account for the whole House, not most of it."""
    for term in sorted({r["term"] for r in rows}):
        total = next(r["total_members"] for r in rows if r["term"] == term)
        for dimension in DIMENSIONS:
            selected = [r for r in rows if r["term"] == term and r["dimension"] == dimension]
            assert selected, f"no {dimension} rows for term {term}"
            assert sum(r["members"] for r in selected) == total, (
                f"term {term} {dimension} does not sum to {total}"
            )


def test_the_head_and_the_stated_remainder_reconcile(rows) -> None:
    """The split the view actually draws.

    Twelve categories are charted and the rest are stated as a counted group
    (FR-103). This asserts the figure on screen — "and 42 further categories,
    carrying 65 of 559" — adds up with the twelve drawn above it. Verified for
    the dataset of 2026-10-13: party 494 + 65 = 559 and 488 + 56 = 544; state
    435 + 124 = 559 and 424 + 120 = 544; terms_served has 8 categories and so
    no remainder at all.
    """
    limit = shown_limit()
    for dimension in DIMENSIONS:
        weight: dict[str, int] = {}
        for row in rows:
            if row["dimension"] == dimension:
                weight[row["category"]] = weight.get(row["category"], 0) + row["members"]
        order = sorted(weight, key=lambda c: (-weight[c], str(c)))
        head, rest = order[:limit], order[limit:]

        for term in sorted({r["term"] for r in rows}):
            per = {
                r["category"]: r["members"]
                for r in rows
                if r["dimension"] == dimension and r["term"] == term
            }
            total = next(r["total_members"] for r in rows if r["term"] == term)
            drawn = sum(per.get(c, 0) for c in head)
            remainder = sum(per.get(c, 0) for c in rest)
            assert drawn + remainder == total, (
                f"{dimension} term {term}: {drawn} shown + {remainder} in the "
                f"remainder is {drawn + remainder}, not {total}"
            )


def test_the_view_filters_no_category_out(rows) -> None:
    """Nothing is dropped — only undrawn.

    The chart shows a head; the TABLE must carry every category, which is what
    makes the head honest and what FR-121 requires of the authoritative form.
    Asserted on the source because it is a property of the code rather than of
    the data: the table is built from the full `categories` list, not from the
    `shown` slice.
    """
    source = VIEW.read_text(encoding="utf-8")
    assert "for (const category of categories)" in source, (
        "the table no longer iterates every category, so the chart's head "
        "would be the only place a category appears"
    )
    assert "const shown = categories.slice(0, SHOWN);" in source
    assert "const rest = categories.slice(SHOWN);" in source


def test_a_not_stated_category_would_render_if_one_ever_appeared(rows) -> None:
    """The case FR-118 names, which the data does not currently produce.

    There is no "not stated" category in the aggregate today and every
    dimension sums exactly to its total, so no member is missing any of the
    three attributes. This records that measurement and asserts the property
    that keeps the requirement met if it changes: the view ranks and slices
    categories but never filters them, so a "not stated" row would appear in
    the table and, if large enough, in the chart.
    """
    not_stated = [r for r in rows if "not stated" in str(r["category"]).lower()]
    assert not_stated == [], (
        "the aggregate now carries a 'not stated' category. That is not a "
        "failure -- it is the case FR-118 is about -- but this test records "
        "its absence, so update it deliberately and check the view shows it."
    )
    source = VIEW.read_text(encoding="utf-8")
    assert "filter" not in source.split("const categories")[1].split("]")[0], (
        "the category list is filtered where it used to be collected, so a "
        "category could now be dropped before it reaches either form"
    )


def test_the_view_requires_no_term_or_session_date(rows) -> None:
    """FR-124, and it is a property of the record rather than a preference.

    Every published term and session `start_date` reads "not stated", so a view
    that placed a term on a calendar would be inventing one.
    """
    assert not any("date" in key for row in rows for key in row), (
        "the composition aggregate now carries a date field; FR-124 assumed none"
    )
    source = VIEW.read_text(encoding="utf-8")
    code = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    for forbidden in ("start_date", "end_date", "isoDate", "new Date("):
        assert forbidden not in code, (
            f"views/composition.js reads {forbidden}; every published term and "
            f"session date is 'not stated' (FR-124)"
        )


def test_the_counting_basis_unit_is_member_and_is_read_not_typed(rows) -> None:
    """The unit is `member`, and the view takes it from the row rather than
    hardcoding it -- the same discipline the rest of the page keeps."""
    assert {r["counting_basis_unit"] for r in rows} == {"member"}
    source = VIEW.read_text(encoding="utf-8")
    assert "counting_basis_unit" in source, (
        "the view no longer reads the unit from the published row"
    )
