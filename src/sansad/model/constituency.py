"""The Constituency entity.

Validation rule, quoted verbatim from
`specs/001-resolved-metadata-layer/data-model.md` → Constituency:

- "a constituency represented by different members across the two covered
  terms MUST list both with their periods, not merged (US3 scenario 3)."

The covered window spans two Lok Sabhas, so a seat changing hands between them
is the ordinary case rather than the exception. Merging the two would make the
constituency entry point -- User Story 3's whole premise, that a visitor can
start from their own seat -- answer with one member's record where two are
owed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sansad.model._common import NOT_STATED

PUBLISHED_FIELDS: tuple[str, ...] = ("constituency_id", "name", "state", "representations")

#: The slug rule. Deliberately the SAME rule as
#: `sansad.ingest.questions.ministry_id_for` -- lowercase, every run of
#: non-alphanumerics to one hyphen, no leading or trailing hyphen -- and
#: deliberately NOT imported from it: `sansad.model` does not depend on
#: `sansad.ingest`, and an entity's identity rule belongs with the entity.
#: `tests/contract/test_constituency_reference.py` asserts the two agree, so
#: the copy cannot drift silently.
_SLUG = re.compile(r"[^a-z0-9]+")


def _slug(value: str) -> str:
    return _SLUG.sub("-", (value or "").strip().lower()).strip("-")


def constituency_id_for(name: str, state: str) -> str:
    """The published `constituency_id`: the state's slug, then the seat's.

    **The state is part of the identity, not decoration.** Three constituency
    names in the covered window name a *different seat* in each of two states --
    `Aurangabad` (Bihar / Maharashtra), `Hamirpur` (Himachal Pradesh / Uttar
    Pradesh) and `Maharajganj` (Bihar / Uttar Pradesh). Keyed on the name alone
    they merge, and the merge was not cosmetic. MEASURED against the dataset
    built on 2026-10-10, before this fix: the published `aurangabad` row carried
    `state: "Hyderabad"` and **22** representations drawn from both seats, so a
    visitor in Maharashtra looking up their own constituency was shown Bihar's
    members as their representatives. That is the failure US3 exists to prevent,
    arriving through the id rather than through the merge rule.

    **State first**, because the view's own order is state then constituency
    (owner decision 2026-10-10: "constituency names repeat across states, so a
    typed name must always show its state"), and because it sorts the whole set
    into state blocks.

    A seat whose state the source does not record gets `not-stated` as the state
    half rather than a bare name slug. Uniform on purpose: a reader sees the gap
    in the id, and two no-state seats sharing a name still merge -- which cannot
    be helped without a state, and is stated here rather than hidden.

    The one place the two halves collapse to one is where they are the **same
    slug**: a single-seat state or union territory whose seat carries the
    territory's own name would otherwise read `sikkim-sikkim`. **8 of the
    window's 545 seats** are like that (Andaman and Nicobar Islands, Chandigarh,
    Ladakh, Lakshadweep, Mizoram, Nagaland, Puducherry, Sikkim). Nothing is
    disambiguated by repeating an identical slug, so it is not repeated.
    """
    seat = _slug(name)
    if not seat:
        return NOT_STATED
    region = _slug(state) or _slug(NOT_STATED)
    return seat if region == seat else f"{region}-{seat}"


@dataclass(frozen=True, slots=True)
class Representation:
    """One member's period representing a constituency.

    A pair, not a single current holder: "MUST list both with their periods,
    not merged."

    **The member's name, party and sitting status ride here** (owner decision
    2026-10-10). They are a copy -- `reference/members.jsonl` is where they are
    defined -- and the copy exists because the page's entry point for the state
    and constituency axes is this set, and a representation that carried only a
    `member_id` could not answer US3 scenario 1, "listed with their party and
    term", without the 3.4 MB member set. Measured: 887 members are reachable
    across the window's 545 seats; 796 have a name in `search/asker-names.jsonl`
    but **91 asked no question in the window**, so for them `reference/members`
    was the only published source -- and they appear on **89 of the 545 seats**.
    Carrying the three fields costs **+104,983 B** and takes the view's first
    fetch from 3,595,037 B to 252,226 B.

    **Nothing outside the FR-008 set is here**, and that bound is what makes the
    copy permissible rather than merely convenient: name, party and sitting
    status are three of the seven published member fields, and the same three
    reasoning applies that `search/asker-names.jsonl` was published under -- a
    field is copied into a page-serving file when the page actually shows it.
    `tests/contract/test_constituency_reference.py` asserts every carried value
    equals the one in `reference/members.jsonl`, so the copy cannot drift from
    the definition.

    `sitting_status` is a MEMBER-level fact as of the last refresh, not a fact
    about this term -- a former member's historical representation still reads
    `former`. The page must say "as of" rather than implying the status belonged
    to the term.
    """

    member_id: str
    #: `Member.canonical_name`. The display form, not a name variant.
    member_name: str = NOT_STATED
    #: The term's own party where the source records one, else the member's.
    #: Verified 2026-10-10: the two are identical for all 1,103 in-window
    #: member-terms, so this is a copy today -- but a member who changed party
    #: between terms is an Edge Case the data model names, and reading the
    #: term's value first means the set improves by itself if the roster ever
    #: records the change.
    party: str = NOT_STATED
    #: `Member.sitting_status`, as of the last refresh. See the class docstring.
    sitting_status: str = NOT_STATED
    #: Term number as the House numbers it, so a reader can see which of the
    #: two covered terms this representation belongs to.
    term_number: int | None = None
    #: A declared gap, not an omission: see the `sansad.publish.reference`
    #: module docstring. Defaulted so the published field order can put the
    #: identity first; it has never been anything but NOT_STATED.
    start_date: str = NOT_STATED
    end_date: str | None = None


@dataclass(frozen=True, slots=True)
class Constituency:
    """One constituency, with every representation inside the covered window."""

    constituency_id: str
    name: str
    state: str = NOT_STATED
    #: "Member and period pairs within the covered window." Plural, always.
    representations: tuple[Representation, ...] = ()

    def __post_init__(self) -> None:
        if not self.constituency_id:
            raise ValueError("constituency_id is required and MUST NOT be empty")
        # The key includes `term_number`, and that is the whole correction.
        #
        # It was `(member_id, start_date)`. Every `start_date` is NOT_STATED --
        # the module docstring's declared gap, and the session enumeration has
        # not supplied one -- so the key reduced to `member_id`, and ONE
        # representation per member was all this rule would admit. A member who
        # served BOTH covered terms in one seat therefore had a term silently
        # dropped by the publisher's dedup, which was keyed to match this.
        # MEASURED against the dataset built on 2026-10-10: the published set
        # carried 558 in-window representations where the roster records
        # **1,103** (member, term) pairs. "MUST list both with their periods"
        # includes the case where both periods are one person's.
        seen = [(r.member_id, r.term_number, r.start_date) for r in self.representations]
        if len(set(seen)) != len(seen):
            raise ValueError(
                f"{self.constituency_id}: duplicate representation in "
                f"{seen!r}. Representations are listed, not merged (US3 scenario 3)."
            )

    @property
    def changed_hands_in_window(self) -> bool:
        """True when more than one member represented this seat in the window."""
        return len({r.member_id for r in self.representations}) > 1

    @property
    def term_numbers(self) -> tuple[int, ...]:
        """The terms this seat has a representation for, ascending.

        Stated rather than counted: a seat with two representations may be one
        member across two terms or two members in one term, and the page has to
        say which.
        """
        return tuple(sorted({r.term_number for r in self.representations if r.term_number}))
