"""T067 — write the User Story 4 aggregates to `data/published/aggregates/`.

Both formats, through the T050 writers, so the aggregates are the same records
in NDJSON and CSV with neither authoritative — the same promise
`contracts/published-dataset.md` makes for every other published set.

`plan.md` → Front End: "Story 4 is not on the page for the first release." So
these files **are** the deliverable. There is no view that renders them and no
page that fetches them; a consumer reads them directly, which is why every row
carries its counting basis rather than relying on a caption somewhere.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from sansad.publish.formats import write_both
from sansad.views.basis import basis_rows
from sansad.views.composition import Composition
from sansad.views.subject_trends import SubjectTrends

__all__ = [
    "AGGREGATES_DIR_NAME",
    "COMPOSITION_STEM",
    "COUNTING_BASIS_STEM",
    "SUBJECT_TRENDS_STEM",
    "AggregateWriteResult",
    "write_aggregates",
]

AGGREGATES_DIR_NAME = "aggregates"
COMPOSITION_STEM = "composition"
SUBJECT_TRENDS_STEM = "subject-trends"
#: The counting basis, published ONCE per unit and referenced by every
#: aggregate row via `counting_basis_unit` + `basis_version`.
COUNTING_BASIS_STEM = "counting-basis"


@dataclass(frozen=True, slots=True)
class AggregateWriteResult:
    files: tuple[Path, ...]
    records: dict[str, int]


def write_aggregates(
    directory: Path,
    *,
    compositions: Sequence[Composition],
    trends: SubjectTrends,
    unresolved: int | None = None,
    partly_resolved: int | None = None,
    co_asked: int | None = None,
    max_askers: int | None = None,
) -> AggregateWriteResult:
    """Write `composition` and `subject-trends`, both formats.

    Compositions for several terms go into **one** file keyed by `term`, not one
    file per term: the set is small, a consumer comparing terms wants them
    together, and a per-term file would add a partition axis the contract does
    not name.
    """
    root = Path(directory) / AGGREGATES_DIR_NAME
    files: list[Path] = []
    records: dict[str, int] = {}

    composition_rows = [row for c in compositions for row in c.as_rows()]
    files.extend(write_both(root, COMPOSITION_STEM, composition_rows))
    records[COMPOSITION_STEM] = len(composition_rows)

    trend_rows = trends.as_rows()
    files.extend(write_both(root, SUBJECT_TRENDS_STEM, trend_rows))
    records[SUBJECT_TRENDS_STEM] = len(trend_rows)

    # The basis, once per unit. Every row above names the unit that applies to
    # it, so this file is what those references resolve to.
    rows = basis_rows(
        unresolved=unresolved,
        partly_resolved=partly_resolved,
        co_asked=co_asked,
        max_askers=max_askers,
    )
    files.extend(write_both(root, COUNTING_BASIS_STEM, rows))
    records[COUNTING_BASIS_STEM] = len(rows)

    return AggregateWriteResult(files=tuple(files), records=records)
