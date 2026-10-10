"""T047 -- several equally-good matches, and near-identical distinct members.

Two rules, pulling in opposite directions, which is why they live in one module.

**Never collapse.** `data-model.md`: "`ambiguous` MUST list its candidates; an
ambiguous match MUST NOT be silently collapsed to the first candidate." The
failure this forbids is specific and cheap to commit: a matcher that sorts its
candidates and takes `[0]` publishes a join that looks exactly like a correct
one. `contracts/published-dataset.md` guarantee 2 is the consumer's side of it.

**Never merge.** `data-model.md`: "Two members with identical or near-identical
names MUST NOT be merged; distinctness is decided on attributes beyond the
name." The fixture `near_identical_members.json` carries the hard case: two
members sharing name, party **and** state, differing only by constituency --
"which the question route does not carry -- so nothing in the question record
can break the tie". The right outcome there is **two members and an ambiguous
question**, not one member.

The two rules meet here: a form matching two distinct identities is ambiguous
*because* they must not be merged. Collapsing the form and merging the members
are the same mistake entering from different directions.

**What is NOT this module's job.** Deciding that two upstream records are one
person. That is `sansad.resolve.identity`, on upstream record identity, and
there is no name-similarity test anywhere in this file -- `Member` carries
`is_merge_candidate_by_name_alone`, which always returns False, for the same
reason.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from sansad.model._common import ResolutionStatus
from sansad.model.member import Member

__all__ = [
    "ATTRIBUTES_BEYOND_THE_NAME",
    "CandidateVerdict",
    "are_distinct_identities",
    "collapse_or_flag",
    "distinguishing_attributes",
]

#: The published attributes on which distinctness may be decided -- i.e. the
#: FR-008 set minus the name forms. `terms` is included because a member whose
#: party or House changed is ONE person with two terms, so the term list is
#: evidence about identity; `sitting_status` and `last_refreshed` are not,
#: because they change under a person rather than distinguishing people.
ATTRIBUTES_BEYOND_THE_NAME: tuple[str, ...] = ("constituency", "party", "state")


@dataclass(frozen=True, slots=True)
class CandidateVerdict:
    """What to do with the candidate set a tier produced."""

    status: ResolutionStatus
    #: One id when resolved; **every** candidate when ambiguous, sorted.
    member_ids: tuple[str, ...]
    #: The attributes that tell the candidates apart, for the maintainer's
    #: worklist. Empty when they cannot be told apart on published attributes
    #: -- which is a fact worth surfacing, not a reason to merge them.
    distinguished_on: tuple[str, ...] = ()


def distinguishing_attributes(a: Member, b: Member) -> tuple[str, ...]:
    """The published attributes on which two members differ, sorted.

    Sorted rather than in declaration order so the output is a stable set
    description: a maintainer comparing two worklist rows should not have to
    care which member was passed first.

    An empty result does **not** mean "the same person". It means these two
    identities are indistinguishable on everything this project publishes --
    the case `near_identical_members.json` calls "the harder case" one step
    further on. Merging on that basis is the forbidden merge.
    """
    differing = [
        name
        for name in ATTRIBUTES_BEYOND_THE_NAME
        if getattr(a, name, None) != getattr(b, name, None)
    ]
    return tuple(sorted(differing))


def are_distinct_identities(a: Member, b: Member) -> bool:
    """Whether these are two people.

    Decided on upstream record identity, never on name similarity. Two
    `member_id` values are two identities even when every published attribute
    matches, because `member_id` is assigned from the upstream record and "a
    `member_id` refers to the same person permanently".
    """
    return a.member_id != b.member_id


def collapse_or_flag(
    member_ids: Iterable[str],
    members_by_id: Mapping[str, Member] | None = None,
) -> CandidateVerdict:
    """Turn a tier's candidate ids into a verdict. The only place that decides.

    One distinct identity resolves -- including when several *name forms*
    matched, since several forms of one person is still one person. More than
    one distinct identity is `ambiguous` carrying all of them. Zero is
    `unresolved`.

    There is deliberately no tie-break parameter. A function that could be
    asked to pick a winner is a function that will be, and FR-004's "MUST NOT
    be dropped or assigned a guessed member" is the thing that would be lost.
    """
    distinct = sorted(set(member_ids))

    if not distinct:
        return CandidateVerdict(status=ResolutionStatus.UNRESOLVED, member_ids=())
    if len(distinct) == 1:
        return CandidateVerdict(status=ResolutionStatus.RESOLVED, member_ids=(distinct[0],))

    distinguished_on: tuple[str, ...] = ()
    if members_by_id:
        members = [members_by_id[i] for i in distinct if i in members_by_id]
        if len(members) > 1:
            attributes: set[str] = set()
            for other in members[1:]:
                attributes.update(distinguishing_attributes(members[0], other))
            distinguished_on = tuple(sorted(attributes))

    return CandidateVerdict(
        status=ResolutionStatus.AMBIGUOUS,
        member_ids=tuple(distinct),
        distinguished_on=distinguished_on,
    )
