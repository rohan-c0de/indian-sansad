<!--
SYNC IMPACT REPORT — temporary scratch material for review of this amendment.
Remove this comment block before committing the amended constitution.

Version change: (unfilled template, no version) → 1.0.0
Bump rationale: Initial ratification. The prior file was the unmodified core
scaffold with every [PLACEHOLDER] intact, so there is no earlier governance to
compare against. First concrete constitution = 1.0.0.

Principles defined (all five new; none renamed, none removed):
  - I. Zero Running Cost
  - II. Two Hours a Week of Upkeep
  - III. Structured Sources Only — No Document Is Ever Opened
  - IV. English Only
  - V. Published Member Fields Are Limited to the FR-008 Set

Added sections (template slots filled):
  - [PROJECT_NAME] → Indian Sansad
  - [SECTION_2_NAME/CONTENT] → Scope of Authority
  - [SECTION_3_NAME/CONTENT] → Compliance Gates
  - [GOVERNANCE_RULES] → Governance body text
  - Version 1.0.0 | Ratified 2026-10-09 | Last Amended 2026-10-09

Removed sections: none.

Provenance note (flagged for the owner, not a change of content):
  Principles I, II and IV are owner decisions recorded in
  `.specify/assessments/indian-sansad/problem.md`. Principles III and V are not
  in problem.md: III is recorded in `decision.md` ("No document is opened";
  "structured sources only") and as FR-015 in the feature spec; V is FR-008 in
  the feature spec, which exists because problem.md records the owner DECLINING
  a guardrail — publication permitted, but only deliberately. Sources are cited
  per principle below.

Follow-up TODOs: none. No placeholder was deferred.
-->

# Indian Sansad Constitution

## Core Principles

### I. Zero Running Cost (NON-NEGOTIABLE)

Running cost MUST be zero. Free tiers only; no paid service of any kind may be introduced —
not hosting, not storage, not compute, not a managed database, not a third-party API on a paid
plan, not a paid tier of an otherwise free service.

- Every design that incurs recurring cost is non-compliant regardless of how small the amount is.
- A plan or spec MUST name the free tier each component lands on, and MUST state what happens
  when that tier's limit is reached.
- A free tier whose limit the design is expected to exceed does NOT satisfy this principle. The
  remedy is to reduce demand or drop the capability — never to upgrade the plan.
- A free trial, promotional credit, or anything that becomes chargeable later is a paid service.

**Rationale**: Owner-stated ceiling — "Money: **none per month**; first deployment as cheap as
possible, free tiers wherever possible" (`problem.md`, Success Metrics). The project earns no
revenue by owner decision, so any recurring charge falls on the maintainer personally. Note that
the owner lifted this limit for the ideation pass only; it applies in full to anything built.

### II. Two Hours a Week of Upkeep (NON-NEGOTIABLE)

Routine upkeep by the maintainer MUST stay within about 2 hours per week, in total, across
everything the project runs.

- Occasional manual intervention is tolerated. Routine manual work is NOT.
- Any capability whose normal operation depends on the maintainer acting on a schedule —
  re-running an ingest, hand-correcting a mapping, watching a dashboard, approving a refresh —
  MUST be automated or dropped.
- Newly published in-scope material MUST be detected and processed without a manual step.
- When upstream breaks, the system MUST degrade quietly for visitors and flag the problem to the
  maintainer. Silence toward the maintainer and a wrong answer toward visitors are both breaches.
- The budget is shared: a new feature that fits in 2 hours a week on its own but pushes the total
  past the ceiling is non-compliant.

**Rationale**: Owner-stated ceilings — "Owner maintenance: **about 2 hours per week**" and
"Manual steps: **occasional** is tolerated; routine manual work is not" (`problem.md`, Success
Metrics). The project is solo with no team expected, so the ceiling is a hard capacity limit, not
a preference.

### III. Structured Sources Only — No Document Is Ever Opened (NON-NEGOTIABLE)

No document file MUST ever be opened, parsed, extracted from, or depended on — PDF or any other
document format. All material MUST come from already-structured sources.

- No OCR, no text-layer extraction, no document-to-text conversion, at any stage, including
  one-off local work whose output is then published.
- Permitted inputs are the already-structured sources: published question metadata, the published
  member roster, and Rajya Sabha question text.
- If a required fact exists only inside a document file, that fact is out of scope. It MUST be
  recorded as a known gap in the coverage statement, not obtained by parsing.
- No design may assume document parsing would be cheap. Whether in-scope documents even carry a
  text layer is an open question, and the in-scope document volume is estimated at the order of
  one million pages.

**Rationale**: Recorded in `decision.md` for the chosen option — "**No document is opened**";
"structured sources only — question metadata, the member roster, Rajya Sabha question text" — and
carried into the feature spec as FR-015. This is also what makes Principles I and II attainable:
it keeps the ~1,000,000-page extraction estimate off the critical path entirely.

### IV. English Only

All material ingested, processed, and published MUST be English.

- Hindi is a non-goal, by owner decision superseding the earlier "English and Hindi" scope.
- All other languages, including the wider Bhashini language surface, are out of scope.
- No translation or transliteration capability may be added under this constitution. Preserving a
  source name form exactly as written is not translation and remains required for provenance.

**Rationale**: Owner decision 2026-10-08, recorded in `problem.md` under both Goals and
Non-Goals, superseding intake's "English and Hindi". A Hindi test returned garbled or partial
text with the cause unverified, so Hindi is excluded rather than deferred on quality grounds.

### V. Published Member Fields Are Limited to the FR-008 Set (NON-NEGOTIABLE)

Published member data MUST be limited to this set: name forms, party, state, constituency, House,
term, and sitting status.

- Any other personal attribute the source serves — including personal phone, Delhi phone, email,
  present and permanent address, date of birth, marital status, and number of sons and daughters —
  MUST NOT be published unless its publication is an explicitly recorded decision.
- "Published" covers everything a third party can reach: the published dataset files, any extract,
  any interactive page, any derived statistic, and any fixture, sample, or test file in the
  repository.
- An attribute may be retrieved transiently only where a permitted field cannot be derived
  without it, and MUST NOT be persisted or published; the derivation MUST be stated.
- The absence of a prohibition is NOT permission. An attribute reaching the published record
  because nothing stopped it is a breach, whether or not anyone intended to publish it.
- Widening the set requires a recorded decision naming the attribute, the reason, and the date —
  recorded before publication, not after.

**Rationale**: FR-008 of the feature spec. The owner declined to adopt a guardrail against
republishing members' personal contact data (`problem.md`, Guardrail), so publication is permitted
but MUST be deliberate rather than incidental. The standing risk notes: the member endpoint returns
personal contact, address, date-of-birth, marital-status and family-composition fields for 5,426
named people without authentication; the data-protection framing is an untested assumption; and
terms of use, licensing and copyright were scoped out by the owner, which defers that risk rather
than clearing it.

## Scope of Authority

These five principles are the complete set. They are drawn from recorded owner decisions and the
chosen option's recorded scope; nothing else has constitutional force here.

- **No other constraint is constitutional.** Requirements, success criteria, assumptions and open
  questions live in the feature spec and the assessment, and may change there without an
  amendment. Only this document's principles gate work.
- **Nothing here resolves an open question.** The deferred risks stay deferred and visible: terms
  of use, licensing and copyright were scoped out of the assessment by owner decision; the
  data-protection framing was never researched; and the Rajya Sabha member route is unknown.
  Principle V constrains what may be published; it does not establish what may lawfully be
  published. A principle that is silent on a risk has not cleared it.
- **This constitution does not choose scope.** Which Houses, terms, audiences and uses are covered
  is the feature spec's business. Where the spec and this document conflict, this document wins
  and the spec MUST be corrected.
- **Attribution.** The work is published under a project name, not the maintainer's name
  (owner decision 2026-10-08).

## Compliance Gates

Each gate maps to exactly one principle. These are checks on work already specified — they add no
requirement beyond the principles above.

| Gate | Principle | What MUST be shown |
| --- | --- | --- |
| Cost | I | Every component named, with the free tier it lands on and the behaviour at that tier's limit. No paid service, trial, or promotional credit anywhere. |
| Upkeep | II | The recurring manual work this change adds, in hours per week, and the project total after it. Automated detection and processing of new material. Quiet degradation for visitors plus a signal to the maintainer. |
| Sources | III | Every input identified as an already-structured source. No document file opened, parsed, or depended on. Facts available only in documents recorded as gaps. |
| Language | IV | All ingested and published material is English. No translation or transliteration path introduced. |
| Member fields | V | The published field list diffed against the FR-008 set. Dataset files, pages, derived statistics and repository fixtures all checked. Any attribute outside the set accompanied by its recorded decision. |

- **At specification**: a requirement that cannot pass a gate MUST be changed or removed before
  the spec is accepted.
- **At planning**: a plan whose approach cannot pass a gate MUST be replaced, not annotated.
- **At implementation**: a breach discovered mid-flight is reported and stops that line of work.
  It MUST NOT be resolved by widening scope or by relaxing a principle in passing.
- **Before publishing**: the Member fields gate MUST be re-run against what will actually be
  published, not against what was specified.
- A gate is passed by evidence — an executed check and its output — not by assertion.

## Governance

This constitution supersedes all other practices, defaults and conventions in this project. Where
a skill, template, tool default or habit conflicts with a principle above, the principle wins.

**Amendment procedure**

1. An amendment MUST be proposed in writing, naming the principle affected, the exact text
   changing, and the reason.
2. The maintainer, as sole decider, MUST approve it explicitly. Silence is not approval.
3. The amendment MUST be recorded in this file with its version and date before any work relies
   on it. Work done in anticipation of an amendment is a breach.
4. A principle marked NON-NEGOTIABLE may still be amended, but MUST NOT be waived case by case.
   An exception for one change is an amendment for all of them.
5. Widening the Principle V field set follows this procedure and additionally satisfies that
   principle's recorded-decision requirement.

**Versioning policy** — semantic versioning of governance:

- **MAJOR**: a principle is removed, or redefined in a way that permits what it previously forbade.
- **MINOR**: a principle or section is added, or its guidance is materially expanded.
- **PATCH**: clarification, wording, or typo fixes that change no obligation.

**Compliance review**

- Every specification, plan and implementation pass MUST clear the Compliance Gates above, and
  MUST state which gates were checked and how.
- A breach MUST be recorded, not silently fixed — including which principle, what reached the
  published record, and what was done about it.
- Principle V additionally requires a review of the published field list against the FR-008 set
  before each publication.
- Complexity, cost, or manual upkeep beyond these ceilings is not justifiable by usefulness. The
  capability is reduced or dropped instead.

**Version**: 1.0.0 | **Ratified**: 2026-10-09 | **Last Amended**: 2026-10-09
