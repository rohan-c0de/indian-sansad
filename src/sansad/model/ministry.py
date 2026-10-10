"""The Ministry entity.

Validation rules, quoted verbatim from
`specs/001-resolved-metadata-layer/data-model.md` → Ministry, **as softened by
owner decision 2026-10-09**:

- "A `ministry_id` MUST NOT change once assigned, and MUST NOT be reused."
- "**One ministry MAY carry two ids until a rename is mapped.**"
- "A rename MUST be recorded by a **maintainer-confirmed** mapping in
  `data/assertions/ministries.json`, which **keeps the older id**, makes the new
  name the `canonical_name`, and moves the previous name into `former_names`.
  Only owner-confirmed pairs; never generated."
- "A name with no mapping MUST mint its own id rather than be guessed into an
  existing one."
- "`minCode` is NOT published and is NOT used for identity."

**The earlier rule this replaces, and why it went.** It read: "renaming
upstream MUST NOT create a second ministry identity." That cannot be kept
unaided, and this module previously asserted the opposite of what is now
decided -- that `ministry_id` is "never derived from the name". The reasons are
measured (`spike/ministry-identity.md`):

- Question records carry only the ministry **name**. There is no code on them,
  so a name is the only join key available.
- The reference set's `minCode` is **per-term**: 10 of the 52 names present in
  both terms carry a different code, and 14 of the 56 shared codes name a
  different ministry in each term -- part genuine rename, part the code reused
  for something unrelated. Four of those pairs have both names carrying
  questions simultaneously for years.

So the choice was between splitting renamed ministries while promising not to,
and merging unrelated ones. The decision keeps the split, makes it visible, and
closes it by owner-confirmed mapping -- and the Coverage Statement reports how
many names are still awaiting adjudication (T053), which is a published field
and **not** a fifth maintainer signal.

The cost is real and worth stating: until a rename is mapped, one ministry's
question history is split across two ids, and the per-ministry partition
(FR-007) is the axis User Story 2 is built on. A ministry profile can therefore
under-report itself -- but the backlog count on the Coverage Statement says so,
which the old rule's silent breach would not have.
"""

from __future__ import annotations

from dataclasses import dataclass

PUBLISHED_FIELDS: tuple[str, ...] = (
    "ministry_id",
    "canonical_name",
    "name_variants",
    "former_names",
)


@dataclass(frozen=True, slots=True)
class Ministry:
    """One ministry questions are put to."""

    #: "the slug of the **first** name under which this ministry was seen.
    #: Assigned once, never changed, never reused."
    #:
    #: Name-derived, deliberately, and that is a reversal of this module's
    #: earlier position -- see the module docstring. It is derived from the
    #: **first** name, not the current one, which is what keeps it stable
    #: through a rename: the id outlives the name it came from.
    ministry_id: str
    #: "One display form -- the current name once a rename has been mapped."
    canonical_name: str
    #: "Forms used by the source."
    name_variants: tuple[str, ...] = ()
    #: "Names this ministry was previously seen under, from confirmed rename
    #: mappings." Empty until a mapping is confirmed -- an unmapped rename
    #: shows up as a second Ministry, not as a former name here.
    former_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.ministry_id:
            raise ValueError("ministry_id is required and MUST NOT be empty")
        if not self.canonical_name:
            raise ValueError(f"{self.ministry_id}: canonical_name MUST NOT be empty")
