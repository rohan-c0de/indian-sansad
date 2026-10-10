"""Identity resolution: the join between written asker names and member identities.

The pieces are one module each -- `normalise` (T044), `identity` (T045),
`match` (T046), `ambiguity` (T047), `assertions` (T048), `records` (T049) --
and `resolve_questions` below composes them.

**Why the composition lives here rather than in a task of its own.** FR-003's
rule that "a question resolves only when *all* its askers do" has no other home
in Phase 4 part 1: it is a property of the question, not of any single tier, and
leaving it in the test suite would put a functional requirement's logic outside
`src/`. It is recorded as a deliberate placement rather than an unlabelled
extra. T055 (the CLI) calls it; T053 reads its two counts.

**The non-additivity this function exists to get right.** The spike had to
re-walk all 95,269 question records to compute the effect of four assertions
rather than summing their per-form figures:

    recovered when one assertion unblocks the question  : 1,411
    recovered only when TWO assertions unblock it       :    87
    total recovered                                     : 1,498

Any shortcut that counts per form rather than per question misses the 87 --
neither assertion unblocks those questions alone, so a per-form method credits
them to neither. The spike published **1,409** and this is the correction
(2026-10-09); 2 questions of the difference remain unexplained, because the
code that produced 1,409 was never committed. `spike/matcher-equivalence.md`,
and `tests/unit/test_assertion_co_asking.py` for the mechanism on two records.

**What a partly-resolved question publishes.** The asker that resolved is kept
in `asking_members`, and the status stays `unresolved` or `ambiguous`. Both
halves matter: dropping the resolved asker would lose a true join to punish an
unrelated one, and marking the question resolved would claim a join the record
does not have. The unresolved form is still auditable -- it has its own
Resolution Record, keyed to the same question's `source_record_ref`.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from sansad.model._common import ResolutionStatus
from sansad.model.member import Member
from sansad.model.question import Question
from sansad.model.resolution_record import ResolutionRecord
from sansad.resolve.assertions import Assertion, apply_assertion
from sansad.resolve.match import MatchOutcome, MemberIndex, resolve_form
from sansad.resolve.records import records_for

__all__ = ["ResolvedQuestions", "resolve_questions", "status_for_question"]


@dataclass(frozen=True, slots=True)
class ResolvedQuestions:
    """The result of one resolution pass.

    Carries **two** resolved counts, not one. T053 publishes the automatic rate
    and the assisted rate separately so SC-002 is checkable against what the
    pipeline does unaided -- the automatic rate is the one that regresses when
    the upstream changes, and a blended figure would hide a matcher regression
    behind accumulated hand corrections.
    """

    questions: tuple[Question, ...]
    records: tuple[ResolutionRecord, ...]
    #: Per distinct written form, after assertions. Keyed by the form as written.
    outcomes: Mapping[str, MatchOutcome]
    #: Per distinct written form, before assertions. Kept so the automatic rate
    #: is derivable from the same pass rather than needing a second one.
    automatic_outcomes: Mapping[str, MatchOutcome]
    total_questions: int
    resolved_automatic: int
    resolved_assisted: int

    @property
    def rate_automatic(self) -> float:
        return self.resolved_automatic / self.total_questions if self.total_questions else 0.0

    @property
    def rate_assisted(self) -> float:
        return self.resolved_assisted / self.total_questions if self.total_questions else 0.0


def status_for_question(
    asker_forms: Sequence[str],
    outcomes: Mapping[str, MatchOutcome],
) -> tuple[ResolutionStatus, tuple[str, ...]]:
    """The question-level status, and the member ids to publish on it.

    "A question resolves only when *all* its askers do." The precedence when
    they do not all resolve is `unresolved` over `ambiguous`, matching
    `spike/resolve_rate.py` (`if "unresolved" in sts`): an asker nothing matched
    is a harder failure than one that matched several candidates, and reporting
    the softer of the two would understate what a maintainer has to fix.
    """
    if not asker_forms:
        # "or empty with `resolution_status` set". `route-capture.md` found the
        # asker field non-null on 250 of 250 sampled records, so this is the
        # unobserved case -- recorded, not assumed away.
        return ResolutionStatus.UNRESOLVED, ()

    statuses: set[ResolutionStatus] = set()
    member_ids: list[str] = []
    for form in asker_forms:
        outcome = outcomes[form]
        statuses.add(outcome.status)
        if outcome.status is ResolutionStatus.RESOLVED:
            for member_id in outcome.member_ids:
                if member_id not in member_ids:
                    member_ids.append(member_id)

    if statuses == {ResolutionStatus.RESOLVED}:
        return ResolutionStatus.RESOLVED, tuple(member_ids)
    if ResolutionStatus.UNRESOLVED in statuses:
        return ResolutionStatus.UNRESOLVED, tuple(member_ids)
    return ResolutionStatus.AMBIGUOUS, tuple(member_ids)


def resolve_questions(
    records: Iterable,
    members: Iterable[Member],
    *,
    assertions: Mapping[str, Assertion] | None = None,
    containment: bool = True,
) -> ResolvedQuestions:
    """Join a batch of `QuestionRecord`s to member identities.

    `records` are `sansad.ingest.questions.QuestionRecord` values -- a mapped
    Question plus its asker forms as written. Taken as a duck type rather than
    an import so this module does not depend on the ingest layer; the resolver
    works the same on records that came from a fixture as on ones that came
    from the route.

    Every distinct written form is resolved **once** and the result reused.
    That is how the spike counted (513 questions behind one form), and it is
    what keeps a 95,269-record window tractable.
    """
    question_records = list(records)
    index = MemberIndex(members)

    forms: list[str] = []
    refs: dict[str, str] = {}
    for record in question_records:
        for form in record.asker_forms:
            if form not in refs:
                forms.append(form)
                # The first question that carried the form. One ref per form,
                # because one record is emitted per form; a consumer auditing a
                # specific join reaches the rest through the question itself.
                refs[form] = record.question.source_record_ref

    automatic = {form: resolve_form(form, index, containment=containment) for form in forms}
    applied = {form: apply_assertion(form, automatic[form], assertions) for form in forms}

    published: list[Question] = []
    resolved_automatic = 0
    resolved_assisted = 0
    for record in question_records:
        status, member_ids = status_for_question(record.asker_forms, applied)
        auto_status, _ = status_for_question(record.asker_forms, automatic)
        if auto_status is ResolutionStatus.RESOLVED:
            resolved_automatic += 1
        if status is ResolutionStatus.RESOLVED:
            resolved_assisted += 1

        question = record.question
        published.append(
            Question(
                question_id=question.question_id,
                house=question.house,
                session=question.session,
                date=question.date,
                type=question.type,
                subject=question.subject,
                ministry_id=question.ministry_id,
                # An ambiguous question publishes no chosen asker: listing one
                # would be the collapse Edge Cases forbids. An `unresolved`
                # question keeps whichever askers did resolve.
                asking_members=() if status is ResolutionStatus.AMBIGUOUS else member_ids,
                resolution_status=status,
                source_record_ref=question.source_record_ref,
                last_refreshed=question.last_refreshed,
                flags=question.flags,
            )
        )

    return ResolvedQuestions(
        questions=tuple(published),
        records=records_for(applied, refs),
        outcomes=applied,
        automatic_outcomes=automatic,
        total_questions=len(question_records),
        resolved_automatic=resolved_automatic,
        resolved_assisted=resolved_assisted,
    )
