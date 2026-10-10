"""T046 -- the matcher. Five tiers, in order, carried forward from the spike.

    exact -> normalised -> normalised-reordered -> approximate -> token-containment

**The configuration is carried forward, not re-chosen.** T012's rule was "Do
not tune the matcher to reach 95% -- the figure is an invented default and the
measurement's job is to test it, not to satisfy it", so every threshold below
came from `spike/resolve_rate.py`, where it was fixed on stated grounds before
the first run:

| Constant | Value | Why that value |
|---|---|---|
| `APPROX_THRESHOLD` | **0.90** | "the conventional 'near-identical string' cut, high enough that it will not merge two different people sharing a surname. NOT chosen by trying several and keeping the best" |
| `APPROX_MARGIN` | **0.02** | Below this gap to the runner-up the result is ambiguous, not resolved -- required by `data-model.md` |
| similarity | `difflib.SequenceMatcher.ratio` on normalised forms | **A constraint, not a preference** -- see below |
| honorifics | `HONORIFICS`, with `md`/`mohd` **unstripped** | `sansad.resolve.normalise` |

**Why the similarity metric is fixed.** `pyproject.toml` records it as a
constraint on this task: "the production `approximate` tier MUST use
difflib.SequenceMatcher.ratio at 0.90/0.02 on normalised forms. Swapping the
similarity metric re-opens SC-002 and requires a fresh holdout." A third-party
matcher scores differently -- rapidfuzz's `ratio` is a normalised Indel
similarity, not SequenceMatcher's longest-matching-block ratio -- so 0.90 would
mean something else under it and the holdout validation would be void.

**The containment tier, adopted by owner decision 2026-10-09.** Implemented as
`spike/resolve_rate.py` implements it: a form resolves if its canonical token
set is a strict subset **or** strict superset of exactly one candidate member's
token set; it is reached **only** when every earlier tier has failed to produce
a single member; and more than one distinct member leaves the form
unresolved/ambiguous rather than collapsing a genuine ambiguity. Measured
effect: **+6.31 points on a blind holdout** of 15,082 questions that did not
exist on disk when the rule was written, against +6.35 on the derivation data
-- no measurable overfitting. Window rate **90.64% -> 94.78%**.

It is **not** an alias handler. Three of its 19 matches are parenthetical
aliases caught incidentally, by coincidence of token sets; aliases remain among
the residual forms and any alias rule needs its own evidence and its own
holdout.

**The default differs from the spike's, deliberately.** `--containment` is OFF
by default in `spike/resolve_rate.py` so that "the unchanged matcher remains
runnable and directly comparable, so the before/after is a measurement rather
than a replacement". That reason is specific to the spike. Here the tier is
adopted, so it is ON -- and the parameter is kept so the automatic rate T053
publishes can be reproduced with it off.

----

**One departure from `spike/resolve_rate.py`, recorded rather than silently
fixed.** Its `resolve_form` calls `fallback(...)` from the exact, normalised and
normalised-reordered tiers at a point **above** the `def fallback` statement, so
those three paths raise `UnboundLocalError` rather than reaching the containment
tier. VERIFIED by running the construction:

    UnboundLocalError: cannot access local variable 'fallback' where it is not
    associated with a value

The measured runs completed, so **no form in the measured window reached
ambiguity at one of those three tiers** -- which is why the figures in
`spike/resolution-rate.md` are unaffected by this and are carried forward
unchanged. This module implements the intended behaviour (those tiers do reach
the containment fallback), which means it can resolve a form the spike script
would have crashed on. That is a difference in reachable behaviour, not in any
published number.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from difflib import SequenceMatcher

from sansad.model._common import ResolutionStatus
from sansad.model.member import Member
from sansad.model.resolution_record import ResolutionMethod
from sansad.resolve.ambiguity import collapse_or_flag
from sansad.resolve.normalise import canon, canon_sorted, token_set

__all__ = [
    "APPROX_MARGIN",
    "APPROX_THRESHOLD",
    "TIER_ORDER",
    "MatchOutcome",
    "MemberIndex",
    "resolve_form",
]

#: Carried over unchanged from `spike/resolve_rate.py`. See the module docstring.
APPROX_THRESHOLD = 0.90
APPROX_MARGIN = 0.02

TIER_ORDER: tuple[ResolutionMethod, ...] = (
    ResolutionMethod.EXACT,
    ResolutionMethod.NORMALISED,
    ResolutionMethod.NORMALISED_REORDERED,
    ResolutionMethod.APPROXIMATE,
    ResolutionMethod.TOKEN_CONTAINMENT,
)


@dataclass(frozen=True, slots=True)
class MatchOutcome:
    """What the matcher concluded about one written name form."""

    status: ResolutionStatus
    #: The tier that produced the result, or None when nothing did.
    method: ResolutionMethod | None
    #: One id when resolved; every candidate when ambiguous; empty when not.
    member_ids: tuple[str, ...]
    #: 1.0 for the deterministic tiers, the SequenceMatcher ratio for
    #: `approximate`, 0.0 when nothing matched.
    score: float = 0.0
    #: Diagnostic label for how far the matcher got, including the two
    #: no-match outcomes the six `method` values cannot express.
    tier_reached: str = "none"
    #: From `sansad.resolve.ambiguity` -- what tells the candidates apart.
    distinguished_on: tuple[str, ...] = ()

    @property
    def is_resolved(self) -> bool:
        return self.status is ResolutionStatus.RESOLVED


class MemberIndex:
    """The candidate pool, indexed four ways -- one per deterministic tier.

    **On the candidate pool.** `spike/resolve_rate.py` measured the rate both
    ways and recorded restricting the pool to one term's members as "a
    CORRECTNESS constraint, not a tuning knob -- a question asked in the 18th
    Lok Sabha cannot have been asked by a member whose service ended in the
    9th". The roster is every Lok Sabha member since the 1st (5,426 people), so
    matching an 18th-Lok-Sabha question against all of them "puts 4,882 people
    in the pool who could not possibly have asked it, which manufactures
    ambiguity that the real pipeline would never face".

    This class does **not** apply that restriction itself: the caller builds an
    index over the pool it means to match against (`Member.terms` carries the
    membership `lsExpr` gives). Hiding a pool filter inside the index would
    make the two measured configurations indistinguishable from the outside,
    and `spike/resolution-rate.md` reports both.
    """

    __slots__ = (
        "_exact",
        "_normalised",
        "_normalised_keys",
        "_reordered",
        "_token_sets",
        "members_by_id",
    )

    def __init__(self, members: Iterable[Member]) -> None:
        self.members_by_id: dict[str, Member] = {}
        self._exact: dict[str, set[str]] = {}
        self._normalised: dict[str, set[str]] = {}
        self._reordered: dict[str, set[str]] = {}
        self._token_sets: dict[frozenset[str], set[str]] = {}

        for member in members:
            self.members_by_id[member.member_id] = member
            forms = {member.canonical_name, *member.name_variants}
            for form in forms:
                written = (form or "").strip()
                if not written:
                    continue
                self._exact.setdefault(written, set()).add(member.member_id)
                key = canon(written)
                if not key:
                    continue
                self._normalised.setdefault(key, set()).add(member.member_id)
                self._reordered.setdefault(canon_sorted(written), set()).add(member.member_id)
                self._token_sets.setdefault(frozenset(key.split()), set()).add(member.member_id)

        #: Materialised once: the approximate tier walks every normalised key
        #: per form, and the full pool is ~30M comparisons.
        self._normalised_keys: tuple[str, ...] = tuple(self._normalised)

    def __len__(self) -> int:
        return len(self.members_by_id)

    def _verdict(self, member_ids: Iterable[str]):
        return collapse_or_flag(member_ids, self.members_by_id)

    def containment_candidates(self, form: str) -> tuple[str, ...]:
        """Member ids whose token set strictly contains, or is contained by, `form`'s.

        Strict in both directions, exactly as the spike implements it. Equality
        is excluded because an equal token set is what the
        `normalised-reordered` tier already matched -- crediting it here would
        attribute an earlier tier's work to this one.
        """
        form_tokens = token_set(form)
        if not form_tokens:
            return ()
        hits: set[str] = set()
        for pool_tokens, ids in self._token_sets.items():
            if not pool_tokens:
                continue
            if form_tokens < pool_tokens or pool_tokens < form_tokens:
                hits |= ids
        return tuple(sorted(hits))


def _containment_fallback(
    form: str,
    index: MemberIndex,
    current: MatchOutcome,
    *,
    enabled: bool,
) -> MatchOutcome:
    """The last tier. Reached only on a non-resolved outcome.

    "it is reached **only** when every earlier tier has failed to produce a
    single member; and more than one distinct member leaves the form
    `unresolved`/`ambiguous` rather than collapsing a genuine ambiguity."
    """
    if not enabled or current.is_resolved:
        return current
    verdict = index._verdict(index.containment_candidates(form))
    if verdict.status is not ResolutionStatus.RESOLVED:
        # Several distinct members, or none. The earlier tier's outcome stands:
        # containment must not turn a specific ambiguity into a wider one.
        return current
    return MatchOutcome(
        status=ResolutionStatus.RESOLVED,
        method=ResolutionMethod.TOKEN_CONTAINMENT,
        member_ids=verdict.member_ids,
        score=1.0,
        tier_reached=ResolutionMethod.TOKEN_CONTAINMENT.value,
    )


def _deterministic_tier(
    form: str,
    index: MemberIndex,
    keyed: Mapping[str, set[str]],
    key: str,
    method: ResolutionMethod,
) -> MatchOutcome | None:
    """One of the three exact-key tiers, or None if the key is not present."""
    if not key or key not in keyed:
        return None
    verdict = index._verdict(keyed[key])
    return MatchOutcome(
        status=verdict.status,
        method=method,
        member_ids=verdict.member_ids,
        score=1.0,
        tier_reached=method.value,
        distinguished_on=verdict.distinguished_on,
    )


def _approximate_tier(form: str, index: MemberIndex) -> MatchOutcome:
    """difflib.SequenceMatcher.ratio on normalised forms, at 0.90/0.02.

    `real_quick_ratio` and `quick_ratio` are documented **upper bounds** on
    `ratio`, so skipping a candidate that fails them cannot change any result;
    it only avoids the full comparison. `set_seq2` once and `set_seq1` per
    candidate is the cheap direction, because SequenceMatcher caches an index
    of seq2. Both are speed, not semantics -- carried over from the spike,
    which notes the full-pool run is ~30M comparisons without them.

    Measured contribution: **0 forms** on the 18th Lok Sabha and **18 forms /
    3,465 instances** on the 17th.
    """
    key = canon(form)
    if not key:
        return MatchOutcome(
            status=ResolutionStatus.UNRESOLVED, method=None, member_ids=(), tier_reached="none"
        )

    scored: list[tuple[float, str]] = []
    matcher = SequenceMatcher(None)
    matcher.set_seq2(key)
    for candidate in index._normalised_keys:
        matcher.set_seq1(candidate)
        if matcher.real_quick_ratio() < APPROX_THRESHOLD:
            continue
        if matcher.quick_ratio() < APPROX_THRESHOLD:
            continue
        ratio = matcher.ratio()
        if ratio >= APPROX_THRESHOLD:
            scored.append((ratio, candidate))

    if not scored:
        return MatchOutcome(
            status=ResolutionStatus.UNRESOLVED,
            method=None,
            member_ids=(),
            tier_reached="approximate-none",
        )

    scored.sort(reverse=True)
    best_score, best_key = scored[0]
    best_ids = index._normalised[best_key]

    verdict = index._verdict(best_ids)
    if verdict.status is not ResolutionStatus.RESOLVED:
        return MatchOutcome(
            status=verdict.status,
            method=ResolutionMethod.APPROXIMATE,
            member_ids=verdict.member_ids,
            score=best_score,
            tier_reached=ResolutionMethod.APPROXIMATE.value,
            distinguished_on=verdict.distinguished_on,
        )

    # The margin rule: a best candidate that barely beats a DIFFERENT member is
    # not a resolution. "an ambiguous match MUST NOT be silently collapsed to
    # the first candidate."
    runner_up = next(
        (s for s, k in scored[1:] if index._normalised[k] != best_ids),
        None,
    )
    if runner_up is not None and (best_score - runner_up) < APPROX_MARGIN:
        tied = {
            member_id
            for score, key_ in scored
            if score >= best_score - APPROX_MARGIN
            for member_id in index._normalised[key_]
        }
        tied_verdict = index._verdict(tied)
        return MatchOutcome(
            status=tied_verdict.status,
            method=ResolutionMethod.APPROXIMATE,
            member_ids=tied_verdict.member_ids,
            score=best_score,
            tier_reached=ResolutionMethod.APPROXIMATE.value,
            distinguished_on=tied_verdict.distinguished_on,
        )

    return MatchOutcome(
        status=ResolutionStatus.RESOLVED,
        method=ResolutionMethod.APPROXIMATE,
        member_ids=verdict.member_ids,
        score=best_score,
        tier_reached=ResolutionMethod.APPROXIMATE.value,
    )


def resolve_form(
    form: str,
    index: MemberIndex,
    *,
    containment: bool = True,
) -> MatchOutcome:
    """Resolve one written name form against the pool.

    "Tiers run exact -> normalised -> approximate, in that order, and stop at
    the first tier that produces any candidate. A later tier never overrides an
    earlier one." The containment tier is the single exception, and only
    upward: it may turn a non-resolution into a resolution, never the reverse.
    """
    written = (form or "").strip()

    outcome = _deterministic_tier(written, index, index._exact, written, ResolutionMethod.EXACT)
    if outcome is None:
        outcome = _deterministic_tier(
            written, index, index._normalised, canon(written), ResolutionMethod.NORMALISED
        )
    if outcome is None:
        outcome = _deterministic_tier(
            written,
            index,
            index._reordered,
            canon_sorted(written),
            ResolutionMethod.NORMALISED_REORDERED,
        )
    if outcome is None:
        outcome = _approximate_tier(written, index)

    return _containment_fallback(written, index, outcome, enabled=containment)
