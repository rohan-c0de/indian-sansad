"""T052 -- the published reference sets, and the ministry identity that decides them.

`data/published/reference/` carries members, ministries, sessions and
constituencies as **whole sets**. State and constituency are member attributes,
so `contracts/published-dataset.md` publishes no per-state or per-constituency
question partition: those subsets are reached in two fetches -- a reference set,
then the matching members' files -- which is only possible if the reference set
carries the state and constituency a consumer filters on.

**Two reference sets can start that walk, and they are not interchangeable.**
`members` carries every attribute but is 3.4 MB over all 5,426 members the
roster has ever recorded. `constituencies` is the window's 545 seats with their
representations, and T086 made it the cheaper entry point for the state and
constituency axes -- but it carries `member_id` and term only, so a page that
starts there still needs a name and a party from somewhere.

----

## Ministry identity (owner decision 2026-10-09, `spike/ministry-identity.md`)

`ministry_id` is **the slug of the first name a ministry was seen under**.
Assigned once, never changed, never reused.

**`minCode` is not used and not published.** The reference route does serve one,
and the T052 gate was answered by capturing it: `minCode`, `minName`,
`minNameHindi`. It is per-term. 10 of the 52 names present in both terms carry a
different code; 14 of the 56 shared codes name a different ministry in each
term, part genuine rename and part the code reused for something unrelated --
four such pairs have both names carrying questions simultaneously for years.
Question records carry only the **name**, so a name is the only join key there
has ever been.

**Three mechanisms, in order, and each visible in the output:**

1. **The slug** collapses case and punctuation variants (`EDUCATION`/`Education`,
   `MICRO, SMALL …`/`MICRO,SMALL …`).
2. **The singular fold** (`ministry_fold_key`) collapses a trailing plural
   (`COMMUNICATION`/`COMMUNICATIONS`, 325 questions;
   `ENVIRONMENT, FORESTS …`/`ENVIRONMENT, FOREST …`, 3,010). Measured to merge
   exactly four groups over the window's 64 names with no false merge.
   **Every group it merges is reported and published** (`fold_groups`), so a
   merge can never be silent -- owner's condition on approving it.
3. **Owner-confirmed rename mappings** from `data/assertions/ministries.json`
   close what normalisation cannot: an abbreviation, a reordering, a word
   substitution. Four are confirmed. Each keeps the older id, makes the new name
   the `canonical_name`, and moves the previous name into `former_names`.

**A name with no mapping mints its own id** rather than being guessed into an
existing one, and the count of such names is published as the adjudication
backlog (T053). It is **not** a maintainer signal -- the four signals stay four.

**Names in the reference set that carry zero questions get no id and are not
published**; their count is reported. `REFERENCE_ONLY_MINISTRY_NAMES` records
the four observed on 2026-10-09 so an offline run can report the figure; a run
that fetches the reference set should recount rather than trust it.

----

## Declared gap: session and term periods

`Session.start_date` / `end_date` and `Term.start_date` / `end_date` are left
`NOT_STATED` unless the session enumeration
(`/api_ls/business/getAllLoksabhaAndSession`) supplies them. **No date is
guessed.** In particular a session's period is **not** derived from the dates of
the questions inside it: the first and last question of a session are facts
about questions, not the period the House sat, and publishing one as the other
would be an invented date in a published record.

`sitting_days` comes from the enumeration as recorded in
`spike/route-capture.md` and is carried here as a recorded measurement with its
provenance, not re-derived.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from sansad.ingest.questions import ministry_fold_key, ministry_id_for
from sansad.model._common import NOT_STATED, House
from sansad.model.constituency import Constituency, Representation, constituency_id_for
from sansad.model.member import Member
from sansad.model.ministry import Ministry
from sansad.model.question import Question
from sansad.model.session import Session
from sansad.publish.formats import rows_for, write_both
from sansad.resolve.assertions import MinistryRename

__all__ = [
    "REFERENCE_DIR_NAME",
    "REFERENCE_ONLY_MINISTRY_NAMES",
    "SITTING_DAYS",
    "MinistryObservation",
    "MinistryRegistry",
    "assign_ministry_ids",
    "constituencies_from",
    "ministry_observations",
    "sessions_from",
    "write_reference_sets",
]

REFERENCE_DIR_NAME = "reference"

#: Sitting days per session, from `/api_ls/business/getAllLoksabhaAndSession`
#: as recorded in `spike/route-capture.md` -> "Sitting days, from the session
#: route". A recorded measurement carried forward, not re-derived.
#:
#: 17th LS totals 279 and 18th LS 133 -- **412 measured**, against `plan.md`'s
#: estimate of ~428. Session 8 of the 18th lists **0** sitting days while
#: carrying 4,500 questions; that is recorded as an anomaly, not corrected
#: here, and T053 declares it.
SITTING_DAYS: Mapping[int, Mapping[int, int]] = {
    17: {1: 37, 2: 20, 3: 23, 4: 10, 5: 25, 6: 18, 7: 18, 8: 28,
         9: 16, 10: 13, 11: 27, 12: 17, 13: 4, 14: 14, 15: 9},
    18: {1: 7, 2: 15, 3: 20, 4: 27, 5: 21, 6: 15, 7: 28, 8: 0},
}  # fmt: skip

#: Ministry names present in a reference set but carrying **zero** questions in
#: the covered window, observed 2026-10-09. They get no `ministry_id` and are
#: not published; only the count is reported (owner decision 2026-10-09).
#:
#: Names, not codes. Two of them look like real-world renames
#: (`AGRICULTURE` -> `AGRICULTURE AND FARMERS WELFARE`) but carry no date
#: evidence either way, so nothing is proposed and nothing is mapped.
REFERENCE_ONLY_MINISTRY_NAMES: tuple[str, ...] = (
    "AGRICULTURE",
    "COMMUNICATIONS AND INFORMATION TECHNOLOGY",
    "NITI AYOG",
    "SKILL DEVELOPMENT, ENTREPRENEURSHIP,YOUTH AFFAIRS AND SPORTS",
)


@dataclass(frozen=True, slots=True)
class MinistryObservation:
    """One ministry name as the question route served it."""

    name: str
    questions: int
    first_date: str
    last_date: str


def ministry_observations(records: Iterable[object]) -> tuple[MinistryObservation, ...]:
    """Collapse question records into one observation per ministry **name**.

    Takes `sansad.ingest.questions.QuestionRecord` values, which carry the name
    as written beside the mapped Question. The name is needed because identity
    is decided on first-seen order and a slug cannot be un-slugged.
    """
    counts: dict[str, int] = {}
    first: dict[str, str] = {}
    last: dict[str, str] = {}
    for record in records:
        name = (getattr(record, "ministry_name", "") or "").strip()
        if not name:
            continue
        date = record.question.date  # type: ignore[attr-defined]
        counts[name] = counts.get(name, 0) + 1
        if name not in first or date < first[name]:
            first[name] = date
        if name not in last or date > last[name]:
            last[name] = date
    return tuple(
        MinistryObservation(
            name=name, questions=counts[name], first_date=first[name], last_date=last[name]
        )
        for name in sorted(counts)
    )


@dataclass(frozen=True, slots=True)
class MinistryRegistry:
    """Which ministry names are one ministry, and which id they carry.

    Built once per refresh from the whole window, because "the first name a
    ministry was seen under" is not knowable from a single record.
    """

    #: minted id (slug of a name) -> the canonical `ministry_id` it belongs to.
    canonical_by_minted: Mapping[str, str]
    #: canonical id -> the Ministry entity.
    ministries: Mapping[str, Ministry]
    #: Groups the **singular fold** merged, as sorted name tuples. Published by
    #: T053 so no merge is silent. Groups merged by the slug alone (case,
    #: punctuation) are not listed -- the fold is the new mechanism and the one
    #: the owner asked to see.
    fold_groups: tuple[tuple[str, ...], ...]
    #: Ministry names that **no confirmed mapping touches**. Named precisely
    #: rather than "awaiting adjudication", because most of them need no
    #: mapping at all -- a ministry seen under one name only is already
    #: correct. It is an **upper bound on outstanding human review**, and it
    #: falls as mappings are confirmed; it is not a count of defects.
    names_without_confirmed_mapping: tuple[str, ...]
    #: Names in a reference set with zero questions in the window.
    reference_only: tuple[str, ...] = REFERENCE_ONLY_MINISTRY_NAMES

    @classmethod
    def build(
        cls,
        observations: Sequence[MinistryObservation],
        renames: Sequence[MinistryRename] = (),
        *,
        reference_only: Sequence[str] = REFERENCE_ONLY_MINISTRY_NAMES,
    ) -> MinistryRegistry:
        """Decide ministry identity for one window.

        Order matters and is the order the decision names: normalise first
        (slug, then fold), then apply the confirmed mappings on top. Applying
        mappings first would let a mapping's own name variants mint separate ids
        before the mapping could claim them.
        """
        # --- 1. group by fold key; the earliest-seen name gives the id ---
        by_fold: dict[str, list[MinistryObservation]] = {}
        for observation in observations:
            by_fold.setdefault(ministry_fold_key(observation.name), []).append(observation)

        canonical_by_minted: dict[str, str] = {}
        names_by_canonical: dict[str, list[MinistryObservation]] = {}
        fold_groups: list[tuple[str, ...]] = []

        for group in by_fold.values():
            # Earliest first question wins; the name itself breaks a tie so the
            # outcome does not depend on input order.
            ordered = sorted(group, key=lambda o: (o.first_date, o.name))
            canonical_id = ministry_id_for(ordered[0].name)
            for observation in group:
                canonical_by_minted[ministry_id_for(observation.name)] = canonical_id
            names_by_canonical[canonical_id] = ordered
            # Report only groups the FOLD merged -- i.e. more than one distinct
            # slug collapsed. Several names sharing one slug were already one
            # name as far as the published id is concerned.
            if len({ministry_id_for(o.name) for o in group}) > 1:
                fold_groups.append(tuple(sorted(o.name for o in group)))

        # --- 2. apply the confirmed rename mappings on top ---
        mapped_names: set[str] = set()
        for rename in renames:
            mapped_names.update(rename.names)
            for name in rename.names:
                minted = ministry_id_for(name)
                absorbed = canonical_by_minted.get(minted)
                canonical_by_minted[minted] = rename.ministry_id
                # Re-point every minted id that had pooled under the absorbed
                # canonical, or a rename would strand the variants of the name
                # it absorbed.
                if absorbed is not None and absorbed != rename.ministry_id:
                    for key, value in list(canonical_by_minted.items()):
                        if value == absorbed:
                            canonical_by_minted[key] = rename.ministry_id
                    observations_absorbed = names_by_canonical.pop(absorbed, [])
                    names_by_canonical.setdefault(rename.ministry_id, []).extend(
                        observations_absorbed
                    )

        # --- 3. build the Ministry entities ---
        ministries: dict[str, Ministry] = {}
        for canonical_id, group in names_by_canonical.items():
            rename = next((r for r in renames if r.ministry_id == canonical_id), None)
            observed = sorted({o.name for o in group})
            if rename is not None:
                display = rename.canonical_name
                former = tuple(rename.former_names)
            else:
                # No mapping: the most recently seen name is the display form.
                display = sorted(group, key=lambda o: (o.last_date, o.name))[-1].name
                former = tuple(n for n in observed if n != display)
            ministries[canonical_id] = Ministry(
                ministry_id=canonical_id,
                canonical_name=display,
                name_variants=tuple(observed),
                former_names=former,
            )

        unmapped = tuple(sorted(o.name for o in observations if o.name not in mapped_names))
        return cls(
            canonical_by_minted=canonical_by_minted,
            ministries=ministries,
            fold_groups=tuple(sorted(fold_groups)),
            names_without_confirmed_mapping=unmapped,
            reference_only=tuple(reference_only),
        )

    def id_for_minted(self, minted_id: str) -> str:
        """The canonical id for a minted one. Unknown ids pass through."""
        return self.canonical_by_minted.get(minted_id, minted_id)


def assign_ministry_ids(
    questions: Iterable[Question], registry: MinistryRegistry
) -> tuple[Question, ...]:
    """Rewrite each question's `ministry_id` to its canonical id.

    A rebuild rather than a mutation, because Question is frozen -- and frozen
    for the reason this function has to exist as a separate step: the identity
    cannot be known when the record is first mapped.
    """
    out: list[Question] = []
    for question in questions:
        canonical = registry.id_for_minted(question.ministry_id)
        if canonical == question.ministry_id:
            out.append(question)
            continue
        out.append(
            Question(
                question_id=question.question_id,
                house=question.house,
                session=question.session,
                date=question.date,
                type=question.type,
                subject=question.subject,
                ministry_id=canonical,
                asking_members=question.asking_members,
                resolution_status=question.resolution_status,
                source_record_ref=question.source_record_ref,
                last_refreshed=question.last_refreshed,
                flags=question.flags,
            )
        )
    return tuple(out)


def sessions_from(
    questions: Iterable[Question], *, house: House = House.LOK_SABHA
) -> tuple[Session, ...]:
    """The Session reference set, from the sessions that carry questions.

    Periods are `NOT_STATED` -- see the module docstring's declared gap. A
    session that carries questions but has no recorded sitting-day count gets
    `None`, "a known gap for the Coverage Statement, not a zero".
    """
    seen: set[tuple[int, int]] = set()
    for question in questions:
        parts = question.session.split("/")
        if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
            seen.add((int(parts[1]), int(parts[2])))
    return tuple(
        Session(
            house=house,
            term=term,
            number=number,
            start_date=NOT_STATED,
            end_date=None,
            sitting_days=SITTING_DAYS.get(term, {}).get(number),
        )
        for term, number in sorted(seen)
    )


def constituencies_from(
    members: Iterable[Member], *, window: Sequence[int]
) -> tuple[Constituency, ...]:
    """The Constituency reference set: one row per seat, in the covered window.

    "A constituency represented by different members across the two covered
    terms MUST list both with their periods, not merged." Periods come from
    `Member.terms`, whose dates are `NOT_STATED` until the session enumeration
    supplies them -- so a representation carries the **term number**, which is
    known, rather than a guessed date.

    T086 corrected three things here, each of which had reached the published
    set. All three are MEASURED against the dataset built on 2026-10-10.

    1. **The id merged two different seats.** It was `ministry_id_for(name)` --
       the seat name alone -- and three names in this window name a different
       seat in each of two states. The `aurangabad` row carried
       `state: "Hyderabad"` and 22 representations from both seats. The id is
       now `constituency_id_for(name, state)`; see its docstring.

    2. **A member serving both covered terms lost one.** The dedup below
       matched `Constituency.__post_init__`'s key, `(member_id, start_date)`,
       and every `start_date` is NOT_STATED -- so it reduced to `member_id` and
       admitted one representation per member. The published set carried 558
       in-window representations where the roster records **1,103** (member,
       term) pairs. Representations are now keyed on `(member_id, term_number)`
       by the grouping itself, not by a dedup pass afterwards, so the rule is
       structural: a second term cannot be dropped by a loop that stops
       matching.

    3. **Out-of-window terms were published as the covered record.** Every term
       on a member's record was listed -- 5,361 representations across terms 1
       to 18 -- so the set claimed representations from the 1st Lok Sabha as
       part of a window covering the 17th and 18th. `window` now bounds it, and
       a seat with no representation inside the window gets no row at all,
       because there is nothing this record can say about it. 897 rows become
       the **545** seats the window actually covers.

    `window` is REQUIRED and keyword-only, with no default. A default would let
    a caller fall back to the unbounded behaviour silently, which is the defect
    in item 3 -- and this project's rule is that a step refuses rather than
    guesses which window it is publishing.

    **An upstream limitation, recorded not worked around**: the roster gives one
    constituency per member, and `Term.constituency` is a copy of it -- verified,
    0 of 9,986 member-terms differ. So a member who moved seats between terms
    would be recorded by the upstream against one seat only, and this function
    cannot see the move. The term's own value is read first anyway, so the set
    improves by itself if the roster ever carries per-term seats.
    """
    terms_in_window = frozenset(int(number) for number in window)
    if not terms_in_window:
        raise ValueError(
            "constituencies_from: `window` MUST name at least one term. "
            "An empty window would publish every term on every member's record "
            "as part of the covered window, which is the defect T086 fixed."
        )

    #: id -> {name, state, reps: {(member_id, term_number): Representation}}
    grouped: dict[str, dict[str, object]] = {}
    for member in members:
        for term in member.terms or ():
            if term.number not in terms_in_window:
                continue
            # The term's own seat and state first, the member's as the fallback.
            seat = (term.constituency or member.constituency or "").strip()
            if not seat or seat == NOT_STATED:
                continue
            state = term.state if term.state and term.state != NOT_STATED else member.state
            state = (state or NOT_STATED).strip() or NOT_STATED
            key = constituency_id_for(seat, state)
            entry = grouped.setdefault(key, {"name": seat, "state": state, "reps": {}})
            if entry["state"] != state:
                # Two states under one id means the id rule collided. Refusing
                # beats publishing the merge this function exists to prevent.
                raise ValueError(
                    f"constituency_id {key!r} covers two states: "
                    f"{entry['state']!r} and {state!r}. The id is built from both, "
                    "so this is a slug collision, not a repeated name."
                )
            reps: dict[tuple[str, int], Representation] = entry["reps"]  # type: ignore[assignment]
            reps[(member.member_id, term.number)] = Representation(
                member_id=member.member_id,
                start_date=term.start_date,
                end_date=term.end_date,
                term_number=term.number,
            )

    out: list[Constituency] = []
    for key in sorted(grouped):
        entry = grouped[key]
        reps: dict[tuple[str, int], Representation] = entry["reps"]  # type: ignore[assignment]
        # Term first, then member id: a seat reads chronologically, and the
        # order does not depend on the order `members` arrived in.
        ordered = tuple(reps[pair] for pair in sorted(reps, key=lambda p: (p[1], p[0])))
        out.append(
            Constituency(
                constituency_id=key,
                name=str(entry["name"]),
                state=str(entry["state"]),
                representations=ordered,
            )
        )
    return tuple(out)


@dataclass(frozen=True, slots=True)
class ReferenceWriteResult:
    """What was written, for the manifest and the dry-run report."""

    files: tuple[Path, ...] = ()
    records: Mapping[str, int] = field(default_factory=dict)


def write_reference_sets(
    directory: Path,
    *,
    members: Sequence[Member],
    ministries: Sequence[Ministry],
    sessions: Sequence[Session],
    constituencies: Sequence[Constituency],
) -> ReferenceWriteResult:
    """Write all four reference sets, both formats, whole.

    Whole sets, never partitioned: `contracts/published-dataset.md` promises
    "Ministries, Sessions, Constituencies | Reference sets, whole", and the
    member set is what the state and constituency axes resolve through.
    """
    root = Path(directory) / REFERENCE_DIR_NAME
    files: list[Path] = []
    records: dict[str, int] = {}
    for stem, entities in (
        ("members", members),
        ("ministries", ministries),
        ("sessions", sessions),
        ("constituencies", constituencies),
    ):
        rows = rows_for(entities)
        ndjson_path, csv_path = write_both(root, stem, rows)
        files.extend((ndjson_path, csv_path))
        records[stem] = len(rows)
    return ReferenceWriteResult(files=tuple(files), records=records)
