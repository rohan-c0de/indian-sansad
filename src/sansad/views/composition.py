"""T065 — the per-term House composition breakdown.

Party, state and number of terms served. **Nothing else.**

`spec.md` User Story 4, Note: "Composition is limited to party, state and number
of terms served. Gender, age band, profession and qualification are out of scope
here; publishing any of them requires an explicit recorded decision."

Principle V names **derived statistics** in the same breath as published files:
an aggregate is the easiest route by which an excluded attribute reaches a
reader, because a count feels less personal than a record. It is not — a
breakdown by date of birth publishes dates of birth. So the permitted set is a
value this module refuses to work outside of, rather than a convention:
`compose` raises `UnsupportedDimensionError` on anything else.

**"Not stated" is a category, never a smaller denominator.** `data-model.md`:
"Missing attributes MUST be represented as an explicit 'not stated' value, never
silently dropped." A breakdown that quietly omits members with a missing party
still sums to something — it sums to a smaller total, and every percentage taken
from it is wrong in the flattering direction. The categories here always sum to
the term's stated total membership, and the total is published beside them so
the reconciliation is checkable rather than asserted.

**Terms served counts every Lok Sabha the source records**, including ones
outside the covered window, because that is what `lsExpr` gives and silently
clipping it to the window would make "number of terms served" mean something
other than its name. The basis says so.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from sansad.model._common import NOT_STATED
from sansad.model.member import Member
from sansad.views.basis import BASIS_VERSION, member_basis

__all__ = [
    "COMPOSITION_DIMENSIONS",
    "Composition",
    "UnsupportedDimensionError",
    "compose",
]

#: The three permitted dimensions. A fourth entry here is a decision about what
#: this project publishes about named people, and `tests/unit/
#: test_composition_fields.py` fails if the tuple changes.
COMPOSITION_DIMENSIONS: tuple[str, ...] = ("party", "state", "terms_served")


class UnsupportedDimensionError(ValueError):
    """Raised for any dimension outside the permitted three.

    A distinct type so no caller can catch it alongside ordinary validation and
    carry on with a dimension FR-008 excludes.
    """


@dataclass(frozen=True, slots=True)
class Composition:
    """One term's breakdown, with its total and its basis."""

    term: int
    total_members: int
    #: dimension -> category -> member count. Every dimension sums to
    #: `total_members`.
    breakdown: Mapping[str, Mapping[object, int]]
    counting_basis: str = field(default="")
    basis_version: str = BASIS_VERSION

    def as_rows(self) -> list[dict[str, object]]:
        """One published row per (dimension, category).

        Long rather than wide: a wide row would need a column per party, which
        changes between refreshes and would break a CSV consumer every time a
        party appeared or vanished.
        """
        rows: list[dict[str, object]] = []
        for dimension in COMPOSITION_DIMENSIONS:
            buckets = self.breakdown.get(dimension, {})
            for category in sorted(buckets, key=lambda c: (isinstance(c, str), str(c))):
                rows.append(
                    {
                        "term": self.term,
                        "dimension": dimension,
                        "category": category,
                        "members": buckets[category],
                        "total_members": self.total_members,
                        # The prose lives once in `aggregates/counting-basis`;
                        # see `views.basis.basis_rows` for why it is not inline.
                        "counting_basis_unit": "member",
                        "basis_version": self.basis_version,
                    }
                )
        return rows


def _served(member: Member, term: int) -> bool:
    return any(t.number == term for t in member.terms)


def _category(member: Member, dimension: str) -> object:
    if dimension == "party":
        return member.party or NOT_STATED
    if dimension == "state":
        return member.state or NOT_STATED
    if dimension == "terms_served":
        # A count, not a list. 0 would mean the roster recorded no term at all,
        # which is a missing attribute rather than a member who served none.
        return len(member.terms) or NOT_STATED
    raise UnsupportedDimensionError(f"{dimension!r} is not a permitted dimension")


def compose(
    members: Iterable[Member],
    *,
    term: int,
    dimensions: Sequence[str] = COMPOSITION_DIMENSIONS,
) -> Composition:
    """Break one term's membership down on the permitted dimensions.

    Raises:
        UnsupportedDimensionError: for any dimension outside
            `COMPOSITION_DIMENSIONS`. Checked **before** any counting, so a
            refused request produces nothing at all rather than a partial
            breakdown a caller might publish.
    """
    for dimension in dimensions:
        if dimension not in COMPOSITION_DIMENSIONS:
            raise UnsupportedDimensionError(
                f"{dimension!r} is not a permitted composition dimension. "
                f"Composition is limited to {', '.join(COMPOSITION_DIMENSIONS)} "
                f"(spec.md User Story 4 Note; FR-008; Principle V names derived "
                f"statistics explicitly). Publishing another attribute requires a "
                f"recorded decision naming it, the reason and the date."
            )

    serving = [m for m in members if _served(m, term)]
    breakdown: dict[str, dict[object, int]] = {}
    for dimension in dimensions:
        buckets: dict[object, int] = {}
        for member in serving:
            category = _category(member, dimension)
            buckets[category] = buckets.get(category, 0) + 1
        breakdown[dimension] = buckets

    return Composition(
        term=term,
        total_members=len(serving),
        breakdown=breakdown,
        counting_basis=member_basis(),
    )
