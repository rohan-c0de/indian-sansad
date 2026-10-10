"""T045 -- `member_id` assignment (FR-002).

The four properties `data-model.md` requires, and where each is enforced:

| Property | Enforced by |
|---|---|
| Assigned once | `IdentityRegistry.member_id_for` returns the same id for the same upstream record, forever |
| Never reused | `IdentityRegistry.claim` refuses to hand one `member_id` to a second upstream record |
| Never derived from a name | `mint_member_id` takes an upstream record **id**; there is no name parameter |
| Stable when a variant is added | `add_name_variants` returns a new Member with the same `member_id` |
| One identity across a party or House change | `with_term`, which appends to `terms` and never mints a second id |

**Why "never derived from a name" is structural rather than a convention.** A
name-derived id changes the moment a variant is added, which is the one thing
FR-002 forbids by name. So the minting function below cannot accept a name: it
is not that it declines to use one, it is that there is nowhere to pass it.

**Why a bare roster serial is prefixed.** `spike/resolve_rate.py` minted
`ls-{mpsno}` and every figure in `spike/resolution-rate.md` carries that form,
so it is carried forward unchanged. The prefix matters beyond convention: the
roster serial is scoped to one House's own numbering, and an unprefixed serial
would let a Lok Sabha member and a Rajya Sabha member collide on one identity
-- the same conflation `data-model.md` forbids for session ids.

**Why an explicit member-id field is taken verbatim instead.** A field the
source itself names as a member identifier is already a stable, non-name-derived
identity, and re-minting it would mean this project's ids disagreed with the
source's for no gain. `/api_ls/member` serves `mpsno` (a record serial) and the
question UI's `getMembers` route is a second member source; tolerating both is
required, not a convenience.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from sansad.model._common import House
from sansad.model.member import Member, Term

__all__ = [
    "HOUSE_ID_PREFIX",
    "IdentityRegistry",
    "add_name_variants",
    "mint_member_id",
    "with_term",
]

#: Per-House prefix for a minted id. `ls-` is carried over from the spike.
HOUSE_ID_PREFIX: Mapping[House, str] = {
    House.LOK_SABHA: "ls",
    House.RAJYA_SABHA: "rs",
}


def mint_member_id(source_record_id: str | int, *, house: House = House.LOK_SABHA) -> str:
    """Mint a `member_id` from an upstream record id. Never from a name.

    There is deliberately no `name` parameter. See the module docstring.
    """
    serial = str(source_record_id).strip()
    if not serial:
        raise ValueError(
            "cannot mint a member_id from an empty upstream record id. A member "
            "with no stable upstream identifier has nothing to be stable ACROSS, "
            "and minting from its name is what FR-002 forbids."
        )
    return f"{HOUSE_ID_PREFIX[house]}-{serial}"


class IdentityRegistry:
    """Assigned once, never reused.

    Deliberately not persisted here. Persistence is the published member
    reference set's job (T052) plus `data/assertions/` for maintainer
    corrections; this object is the in-refresh guarantee that one upstream
    record gets one identity and one identity gets one upstream record.
    """

    __slots__ = ("_by_member_id", "_by_source")

    def __init__(self) -> None:
        self._by_source: dict[str, str] = {}
        self._by_member_id: dict[str, str] = {}

    def member_id_for(
        self,
        source_record_id: str | int,
        *,
        house: House = House.LOK_SABHA,
        member_id: str | None = None,
    ) -> str:
        """The identity for this upstream record, minted on first sight.

        `member_id` lets a caller supply an identity the source already carries
        (see the module docstring); omit it and one is minted from the record
        id.
        """
        source = str(source_record_id).strip()
        existing = self._by_source.get(source)
        if existing is not None:
            if member_id is not None and member_id != existing:
                raise ValueError(
                    f"upstream record {source!r} already holds member_id "
                    f"{existing!r}; refusing to reassign it to {member_id!r}. "
                    f"A member_id MUST be stable across refreshes (FR-002)."
                )
            return existing
        assigned = member_id if member_id is not None else mint_member_id(source, house=house)
        self.claim(assigned, source_record_id=source)
        return assigned

    def claim(self, member_id: str, *, source_record_id: str | int) -> None:
        """Bind `member_id` to one upstream record, or refuse.

        Refusing is the whole function. "A `member_id` refers to the same
        person permanently. It is never reused" -- and a reused id is
        undetectable downstream, because both records look perfectly valid.
        """
        source = str(source_record_id).strip()
        held_by = self._by_member_id.get(member_id)
        if held_by is not None and held_by != source:
            raise ValueError(
                f"member_id {member_id!r} is already held by upstream record "
                f"{held_by!r} and cannot be reused for {source!r}. "
                f"A member_id is never reused (FR-002, contract guarantee 1)."
            )
        self._by_member_id[member_id] = source
        self._by_source[source] = member_id

    def __len__(self) -> int:
        return len(self._by_source)

    @property
    def assigned(self) -> Mapping[str, str]:
        """upstream record id -> member_id, for this refresh."""
        return dict(self._by_source)


def add_name_variants(member: Member, variants: Iterable[str]) -> Member:
    """A Member carrying additional written name forms. **Same `member_id`.**

    `member_id` "MUST NOT change when a name variant is added (FR-002)". This
    function is the only sanctioned way to widen a member's name forms, so that
    rule has one place to hold rather than being re-obeyed at each call site.

    Order is preserved and duplicates are dropped: the variant list is an audit
    surface, and its first entry is the form the roster served first.
    """
    seen = list(member.name_variants)
    known = set(seen)
    for variant in variants:
        form = (variant or "").strip()
        if form and form not in known:
            seen.append(form)
            known.add(form)
    return Member(
        member_id=member.member_id,
        canonical_name=member.canonical_name,
        name_variants=tuple(seen),
        house=member.house,
        party=member.party,
        state=member.state,
        constituency=member.constituency,
        terms=member.terms,
        sitting_status=member.sitting_status,
        source_record_ref=member.source_record_ref,
        last_refreshed=member.last_refreshed,
    )


def with_term(member: Member, term: Term) -> Member:
    """A Member carrying one more term. **Same `member_id`.**

    "A member whose party or House changes within the covered period MUST
    retain one `member_id` with the change represented in `terms`, not split
    into two identities." So a party change is this call, not a second Member
    -- and `Member.party` keeps whatever the source currently records while the
    history lives in `terms`.
    """
    if any(t.house is term.house and t.number == term.number for t in member.terms):
        return member
    return Member(
        member_id=member.member_id,
        canonical_name=member.canonical_name,
        name_variants=member.name_variants,
        house=member.house,
        party=member.party,
        state=member.state,
        constituency=member.constituency,
        terms=(*member.terms, term),
        sitting_status=member.sitting_status,
        source_record_ref=member.source_record_ref,
        last_refreshed=member.last_refreshed,
    )
