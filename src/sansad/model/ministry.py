"""The Ministry entity.

Validation rule, quoted verbatim from
`specs/001-resolved-metadata-layer/data-model.md` → Ministry:

- "ministries are reconciled by the same stability rule as members -- renaming
  upstream MUST NOT create a second ministry identity."

This is not hypothetical bookkeeping. Ministries are renamed, split and merged
between terms, and the covered window spans two Lok Sabhas. A rename that
forges a second `ministry_id` would silently split one ministry's question
history in two across the window -- and the per-ministry partition (FR-007) is
the axis User Story 2 is built on, so the split would surface as a ministry
profile that under-reports itself with no error anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass

PUBLISHED_FIELDS: tuple[str, ...] = ("ministry_id", "canonical_name", "name_variants")


@dataclass(frozen=True, slots=True)
class Ministry:
    """One ministry questions are put to."""

    #: "Stable identity." Stable across renames, and never derived from the
    #: name -- a name-derived id is precisely what turns a rename into a
    #: second identity.
    ministry_id: str
    canonical_name: str
    #: "Forms used by the source." A rename adds a variant here. It does not
    #: create a Ministry.
    name_variants: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.ministry_id:
            raise ValueError("ministry_id is required and MUST NOT be empty")
        if not self.canonical_name:
            raise ValueError(f"{self.ministry_id}: canonical_name MUST NOT be empty")
