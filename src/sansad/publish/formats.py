"""T050 -- the two published formats. Neither authoritative over the other.

`contracts/published-dataset.md`: "Each set is published in both
newline-delimited JSON and CSV. The two are the same records; neither is
authoritative over the other." This is the form FR-006 names -- "the form a
third party consumes without re-deriving the resolution" -- so these writers
are the external interface of the whole feature, not an export convenience.

**"The same records" is made checkable, not asserted.** Both writers project a
row through `text_projection`, and `read_csv` returns that same projection. So
`[text_projection(r) for r in read_ndjson(p)] == list(read_csv(q))` is an
equality between the writers rather than a reimplementation of one of them in a
test. CSV has no types; the projection is where that fact is handled once.

**Two encoding rules for non-scalar values, each stated.**

1. A list of **scalars** (`name_variants`, `asking_members`) becomes a
   `|`-separated string. And an element containing `|` makes this writer
   **raise** rather than emit a row that would silently re-split wrongly on
   read. `route-capture.md` measured 0 non-ASCII characters and no parentheses
   across 376 name instances, so a `|` in a name is not an observed case -- but
   "not observed" is not "cannot happen", and the failure mode of guessing is a
   corrupted published join.
2. A **structured** value (`terms`, a nested record) becomes compact JSON in the
   cell. Awkward for a spreadsheet, unambiguous for a program, and
   round-trippable -- which a flattened approximation would not be.

**Why `polars` is not used here**, given `pyproject.toml` takes it for "the
publish side". These two writers have to guarantee that the CSV and the NDJSON
carry *the same records*, and a dataframe round-trip introduces dtype inference
between the rows and the file: a column of integers with one null comes back
differently from one without, and `None` versus empty string is exactly the
distinction `data-model.md` makes load-bearing ("absent for Rajya Sabha" is not
the same fact as "not stated"). The stdlib writers make the projection explicit
and the output byte-deterministic. `polars` remains the right tool for the
partition and aggregate layers (T051, T060+), where the work is grouping rather
than guaranteeing a projection.

**Byte-determinism matters beyond tidiness.** The dataset is force-pushed to the
`published` branch as a single commit on every successful refresh, so a
reordered or re-quoted file is an unexplained diff in a one-commit-deep history
that nobody can diff against anything.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

__all__ = [
    "CSV_SUFFIX",
    "LIST_SEPARATOR",
    "NDJSON_SUFFIX",
    "columns_for",
    "read_csv",
    "read_ndjson",
    "rows_for",
    "text_projection",
    "write_both",
    "write_csv",
    "write_ndjson",
]

LIST_SEPARATOR = "|"
NDJSON_SUFFIX = ".jsonl"
CSV_SUFFIX = ".csv"


def _scalar(value: Any) -> Any:
    """One value, reduced to something JSON can carry.

    Enum members become their `value` -- a published record must carry
    `"resolved"`, not `"ResolutionStatus.RESOLVED"`, or a consumer filtering on
    `resolution_status == "resolved"` (contract guarantee 2) finds nothing.
    """
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: _scalar(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, (list, tuple)):
        return [_scalar(item) for item in value]
    if isinstance(value, Mapping):
        return {str(k): _scalar(v) for k, v in value.items()}
    return value


def columns_for(entity_type: type) -> tuple[str, ...]:
    """The published columns for an entity type, in `data-model.md`'s order.

    A `PUBLISHED_FIELDS` tuple in the entity's own module wins, because that
    tuple **is** the machine-readable form of "Published fields MUST be limited
    to those above" (FR-008) -- the field scope and the column list must be one
    decision, not two. Entities without one fall back to their dataclass
    fields.
    """
    import sys

    module = sys.modules.get(entity_type.__module__)
    published = getattr(module, "PUBLISHED_FIELDS", None)
    if published:
        return tuple(published)
    if is_dataclass(entity_type):
        return tuple(f.name for f in fields(entity_type))
    raise TypeError(f"{entity_type.__name__} declares no published columns")


def rows_for(
    entities: Iterable[Any],
    *,
    columns: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    """Project entities onto published rows, columns in declared order.

    Only the published columns appear. An entity attribute outside
    `PUBLISHED_FIELDS` -- `Question.flags`, for instance -- does not reach the
    published record by being present on the object, which is the "absence of a
    prohibition is NOT permission" default applied at the publish boundary as
    well as the ingest one.
    """
    items = list(entities)
    if not items:
        return []

    kinds = {type(item) for item in items}
    if len(kinds) > 1:
        raise TypeError(
            f"rows_for takes entities of ONE type; got {sorted(k.__name__ for k in kinds)}. "
            f"Mixed types in one published set would give the two formats different "
            f"column sets."
        )
    names = tuple(columns) if columns else columns_for(items[0].__class__)
    return [{name: _scalar(getattr(item, name)) for name in names} for item in items]


def text_projection(row: Mapping[str, Any]) -> dict[str, str]:
    """A row as text -- the shared definition of "the same record".

    Used by the CSV writer and returned by `read_csv`, so the two formats are
    compared on one definition rather than on two readings of the contract.
    """
    out: dict[str, str] = {}
    for key, value in row.items():
        out[key] = _as_text(key, value)
    return out


def _as_text(key: str, value: Any) -> str:
    if value is None:
        # Empty cell. `None` ("absent for Rajya Sabha") and the explicit
        # "not stated" string are different facts, and they stay different:
        # "not stated" survives as its own text.
        return ""
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        if all(isinstance(item, (str, int, float, bool)) or item is None for item in value):
            parts = ["" if item is None else _as_text(key, item) for item in value]
            offending = [p for p in parts if LIST_SEPARATOR in p]
            if offending:
                raise ValueError(
                    f"{key}: a value contains the list separator {LIST_SEPARATOR!r} "
                    f"and cannot be published in CSV without ambiguity. Refusing "
                    f"rather than emitting a row that re-splits wrongly on read; "
                    f"the separator is a published-format decision and changing it "
                    f"is a breaking change to consumers."
                )
            return LIST_SEPARATOR.join(parts)
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return json.dumps(_scalar(value), ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def write_ndjson(path: Path, rows: Iterable[Mapping[str, Any]]) -> int:
    """One JSON object per line, UTF-8, `\\n`-terminated. Returns the row count.

    `ensure_ascii=False` because the published record reproduces source forms
    as written (Principle IV: no transliteration), and escaping them to ASCII
    would be a silent transformation of a name. `sort_keys=False` keeps the
    declared column order, which makes the file readable next to the CSV.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")
            count += 1
    return count


def write_csv(
    path: Path,
    rows: Iterable[Mapping[str, Any]],
    *,
    columns: Sequence[str] | None = None,
) -> int:
    """A header row plus one row per record. Returns the row count.

    `lineterminator="\\n"` rather than the module default `"\\r\\n"`: a
    force-pushed single commit should not differ by line endings between the
    machine that built it and the runner that rebuilds it.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    materialised = [dict(row) for row in rows]
    names = tuple(columns) if columns else tuple(materialised[0]) if materialised else ()

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=names, lineterminator="\n")
        writer.writeheader()
        for row in materialised:
            writer.writerow(text_projection({name: row.get(name) for name in names}))
    return len(materialised)


def write_both(
    directory: Path,
    stem: str,
    rows: Iterable[Mapping[str, Any]],
    *,
    columns: Sequence[str] | None = None,
) -> tuple[Path, Path]:
    """Write both formats of one published set. Returns (ndjson, csv).

    Both, always, in one call -- so a set cannot be published in one format
    only. "neither is authoritative over the other" is unmaintainable if the
    two are written from two call sites that can drift apart.
    """
    directory = Path(directory)
    materialised = [dict(row) for row in rows]
    names = tuple(columns) if columns else tuple(materialised[0]) if materialised else ()

    ndjson_path = directory / f"{stem}{NDJSON_SUFFIX}"
    csv_path = directory / f"{stem}{CSV_SUFFIX}"
    write_ndjson(ndjson_path, materialised)
    write_csv(csv_path, materialised, columns=names)
    return ndjson_path, csv_path


def read_ndjson(path: Path) -> list[dict[str, Any]]:
    """Read back a published NDJSON file. Typed values, as written."""
    rows: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read back a published CSV file. **Text values** -- CSV has no types.

    Returns exactly what `text_projection` produces, which is what makes the
    two formats comparable without either one being treated as the truth.
    """
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]
