# Implementation Plan: Resolved Metadata Layer for the Indian Parliamentary Record

**Branch**: `001-resolved-metadata-layer` | **Date**: 2026-10-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-resolved-metadata-layer/spec.md`

## Summary

Publish the Indian parliamentary question record for the covered period with each question already attached to a single stable identity for the Member who asked it, consistent across every name form the source uses — the obstacle that the assessment records as having stopped a prior attempt after under a month of coverage. Four reader-facing views sit on that joined record. Three — ministry question-load and mix, prior occurrences of a subject, and a state/constituency entry point — are delivered on an interactive page running in the visitor's browser. The fourth, House composition plus subject trends, ships for the first release as precomputed files in the published dataset rather than on that page.

**Technical approach**: a scheduled pipeline that reads only already-structured upstream sources, reconciles identities, and publishes a partitioned static dataset. No server, no database, no document files opened. The shape follows from three spec constraints rather than from preference — zero recurring cost (FR-014), unattended refresh (FR-009), and third-party re-use of the output (FR-006). See [research.md](./research.md) for the decisions and the alternatives rejected.

## Technical Context

**Language/Version**: Python 3.13

**Primary Dependencies**: *Pipeline* — two third-party: an HTTP client; a tabular/serialisation library for publishing. Identity reconciliation uses the standard library's `difflib` rather than a third-party approximate string-matching library, so the holdout-validated 0.90/0.02 similarity thresholds carry into `src/` unchanged. *Front end* — minimal, with no build step if one can be avoided: hand-written HTML, CSS and ES modules served as-is, a dependency added only where the browser has no equivalent. Deliberately minimal on both sides — every dependency is upkeep against a ~2h/week ceiling, and a build step is upkeep twice over.

**Storage**: version-controlled files. No database. **The published dataset lives on a rolling orphan branch, not on `main`** (owner decision 2026-10-09, [spike/size-budget.md](./spike/size-budget.md)): every successful refresh force-pushes a single commit to a branch named `published`, which GitHub Pages serves, while `data/published/` is git-ignored on `main` as a build output. `data/assertions/` stays on `main`. The dataset is therefore still version-controlled, but its history is one commit deep by design — at the measured 216.5 MiB per snapshot, full history breaches GitHub's repository-size guidance on about the fifth refresh. **Published partitions cover every subset axis FR-007 names**: House, House+session, one file per ministry, and one file per member — with state and constituency resolved through the member reference set rather than duplicated as question partitions. Justified by scale: ~5,426 member records and ~10^5 question records, three to four orders of magnitude smaller in bytes than the ~1,000,000-page document corpus that demoted the alternative options. The per-ministry and per-member partitions republish the same question records under additional keys. Both quantities are now **measured** rather than unmeasured: the duplication multiple is **3.725×** and the whole window publishes at **227,007,149 bytes (216.5 MiB) across 1,750 files**, with the subject-search index at **3,002,356 bytes (2.86 MiB)** — see [spike/size-budget.md](./spike/size-budget.md). `research.md`'s UNVERIFIED markers on both are superseded.

**Testing**: pytest, with reconciliation fixtures built from real recorded name variants, co-asked questions, and a deliberately unresolvable name.

**Target Platform**: free-tier scheduled CI runner for refresh; free static hosting for the published dataset **and** for the reader front end, on the same host and the same origin. **One-time repository setting required**: GitHub Pages must be pointed at the `published` branch rather than `main`, since that is where the dataset and `web/` are served from. Nothing in the pipeline can set this, and until it is set the site serves the wrong branch. The front end's runtime is the visitor's browser; there is no server-side rendering and no server.

**Project Type**: scheduled data pipeline producing a static published dataset, plus a static client-side front end over that dataset. Not a web service, not a library — the front end is files, not a process.

**Front End**: a static page in `web/`, delivering User Stories 2 and 3 — and those two only. It runs entirely in the visitor's browser, fetches only the published dataset files from the same static host, and makes **no** request to the upstream source. Minimal dependencies, and no build step if one can be avoided. **Story 4 is not on the page for the first release**: its composition breakdown and subject trends ship as precomputed files in the published dataset, and the page may add them later. See [research.md](./research.md) for the decision and the alternatives rejected.

**Performance Goals**: not latency-driven. A full refresh must complete within one scheduled run; an incremental refresh well inside it.

**Constraints**: zero running cost (FR-014); ~2h/week maintainer attention; no document file opened at any point (FR-015); the upstream permits no cross-origin browser requests, so the front end makes no call to it and reads only the published dataset files from its own static host — same-origin, so that block does not apply; quiet degradation for visitors with maintainer alerting (FR-010, FR-011).

**Scale/Scope**: ~5,426 members; ~10^5 questions; ~428 Lok Sabha sitting days in the covered window; English only; 17th–18th Lok Sabha, with Rajya Sabha bounded by the same calendar window **and at risk — see the gate below**.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Constitution**: `.specify/memory/constitution.md` v1.0.0, ratified 2026-10-09, five principles.

**What this check is.** It evaluates the *approach*, which is what the constitution's planning gate asks for: "a plan whose approach cannot pass a gate MUST be replaced, not annotated." It is **not** a passed gate in the constitution's own evidentiary sense — "a gate is passed by evidence — an executed check and its output — not by assertion" — because nothing here has been built or run. Each row names where that evidence will come from.

| # | Principle | Plan position | Approach verdict |
|---|---|---|---|
| I | Zero Running Cost | Three components, no others: refresh on a free-tier scheduled CI runner; the published dataset on free static hosting; the `web/` front end on **the same** static host, adding no component and no second tier. No database, no server, no paid plan, no trial or promotional credit. | **evidenced — every quantity now measured**: 216.5 MiB published against a 1 GiB Pages ceiling (21.1%), 1,750 files, largest file 3.53 MiB against 100 MiB, ~71 min ingest against a 6-hour job ceiling, and no overage charge anywhere ([spike/free-tiers.md](./spike/free-tiers.md), [spike/size-budget.md](./spike/size-budget.md)) |
| II | Two Hours a Week of Upkeep | Unattended detection and processing (FR-009); quiet degradation for visitors with a maintainer signal (FR-010, FR-011; quickstart scenario 9). The front end **adds** upkeep — a second artefact to keep working against dataset shape changes, browser regressions and its own dependencies — which is why it carries minimal dependencies and no build step, and why it is **sequenced after** the resolution-rate measurement (Risk 3). | **partly evidenced** — the required hand work is measured at ≈12 min one-time (four confirmed assertions), well inside the ceiling; but the steady-state rate covers one of two terms at n=6, the 3-min median comes from the easy class of forms, and **the project total is unestablished** until the pipeline has run on a schedule ([spike/spike-report.md](./spike/spike-report.md)) |
| III | Structured Sources Only | Inputs are the three already-structured sources only: question metadata, the member roster, Rajya Sabha question text. No document file opened, parsed or depended on (FR-015). The front end reads this feature's own published JSON/CSV, which is output, not a source document. Debate and answer text are recorded as gaps in the contract and the coverage statement, not obtained by parsing. | **compliant** |
| IV | English Only | No translation or transliteration path anywhere, pipeline or front end. Front-end interface strings are English. Source name forms are rendered exactly as written, which FR-005 requires for provenance and which is not translation. | **compliant** |
| V | Published Member Fields | FR-008 and SC-010 bound publication to name forms, party, state, constituency, House, term and sitting status; quickstart scenario 10 (`make audit-fields`) enforces it. Story 4's composition breakdown is limited to party, state and terms served, consistent with this principle. | **compliant — audit scope must widen** |

**Two things this check surfaces rather than waves through:**

1. **Principle I's gate wants "the behaviour at that tier's limit", and page load size is now MEASURED rather than assumed.** From the real window publish: **587 KiB** for a median ministry profile, **401 KiB** for a median constituency view, **2.50 MiB** for the largest ministry, and **3.44 MiB** with the subject index loaded — allowing roughly 166,000 median visitors a month inside the 100 GB soft bandwidth ([spike/size-budget.md](./spike/size-budget.md) T019). `research.md`'s UNVERIFIED marker is superseded. Two inputs remain unobserved rather than unmeasured: the page shell is a 60 KiB estimate because `web/` does not exist, and every figure is uncompressed because the gzip/brotli ratio was not measured. **Budget against the largest partition, not the median** — ministry files span 350 B to 2.56 MiB.
2. **Principle V's gate names "pages" and "derived statistics" explicitly, so `make audit-fields` must cover `web/` and everything it renders — not just `data/published/`.** A front end is a new way for an unlisted attribute to reach a reader. The audit as currently described in quickstart scenario 10 targets published output; its scope has to include the page.

**Principle II's gate also wants the recurring manual work in hours per week and the project total after it.** The manual increment is now measured — ≈12 minutes one-time for the four confirmed assertions, with 21 optional forms at ≈63 minutes more — but **the project total still cannot be given** before the pipeline has run on a schedule even once, because `plan.md` Risk 6 expects the budget to go mostly on breakage. The total is tracked as a risk below rather than asserted here.

**Post-Phase-1 re-check**: the design raises no violation of any principle, and no deviation is being requested. Two items are carried forward unchanged by the design — the Rajya Sabha shortfall, which is an upstream access fact rather than a design choice, and the accepted personal-data risk, bounded by FR-008/SC-010 and enforced by quickstart scenario 10. Note what the constitution says about the latter: Principle V "constrains what may be published; it does not establish what may lawfully be published." Licensing remains deferred, not cleared.

## Project Structure

### Documentation (this feature)

```text
specs/001-resolved-metadata-layer/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── published-dataset.md   # Phase 1 output
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/sansad/
├── ingest/           # read already-structured upstream sources
├── resolve/          # identity reconciliation; name variants; ambiguity handling
├── model/            # the entities in data-model.md
├── publish/          # partitioned dataset output, coverage statement
├── views/            # precomputed aggregates for the P2-P3 reader views
└── signals/          # maintainer alerting; last-known-good handling

web/                  # static front end for the P2-P3 reader views; no build step
├── index.html
├── app.js            # ES modules; fetches only this host's published files
├── style.css
└── lib/              # vendored minimal dependencies, if any prove unavoidable

data/
├── published/        # the dataset consumers take
│   ├── by-session/   # House + session question partitions
│   ├── by-ministry/  # one question file per ministry (FR-007)
│   ├── by-member/    # one question file per member_id (FR-007)
│   ├── reference/    # members, ministries, sessions, constituencies; state and
│   │                 #   constituency subsets resolve through the member set
│   ├── aggregates/   # precomputed counts and trends, incl. Story 4's files
│   └── search/       # subject-search index the page fetches; 2.86 MiB MEASURED
└── assertions/       # maintainer resolution assertions, surviving refreshes

tests/
├── resolution/       # name variants, co-asked, unresolved, ambiguous
├── resilience/       # upstream unavailable, shape-changed, truncated
├── contract/         # published dataset conforms to contracts/published-dataset.md
└── unit/
```

**Structure Decision**: single project with a static front end — not a frontend/backend split, because there is no backend to split from. The feature's external interface is a published dataset rather than a service, so `publish/` is the boundary that a web API would otherwise occupy, and `web/` consumes exactly the files a third-party consumer takes. `web/` sits beside `src/` rather than inside it because it shares no code with the pipeline and has no build step coupling the two; the only contract between them is the published dataset itself. `src/sansad/views/` therefore holds precomputed aggregates written at publish time, not rendering code — rendering is the browser's job. `data/assertions/` is separated from `data/published/` deliberately: maintainer corrections must survive an unattended refresh, which means they cannot live inside generated output. `signals/` is separate because FR-010 and FR-011 pull in opposite directions — quiet for visitors, loud for the maintainer — and that asymmetry is easy to lose if it is scattered across the pipeline.

## Complexity Tracking

No violation to record: every principle is met by the approach as planned, and no deviation is being requested, so there is nothing here to justify. **Both quantities that were previously untracked here are now measured** ([spike/size-budget.md](./spike/size-budget.md)): page load size bearing on the static host's free tier is **587 KiB** median / **2.50 MiB** worst case against a 100 GB monthly soft limit (Principle I), and the maintainer increment is **≈12 minutes one-time** (Principle II). One quantity remains genuinely unmeasurable until the pipeline has run on a schedule and is still tracked as a risk: **the project-wide upkeep total**, which Risk 6 expects to go mostly on upstream breakage. The **front end's own** upkeep increment is also still unquantified, since `web/` does not exist.

## Risks Carried Into Implementation

Not a template section; recorded because three of these would otherwise first surface during build.

1. **Rajya Sabha access.** `api_rs/members` returns HTTP 403 where sibling paths return 404; the cause is **UNVERIFIED**. Until settled, delivery is Lok Sabha-only and FR-001 is partly unmet. Settling it needs browser network capture, not more path probing.
2. **The question-metadata route has never been retrieved first-hand** in two assessment passes or this one. Phase 0 established the method — capture what the site's own pages request — but the route is still unconfirmed, and User Story 1 depends on it entirely.
3. **Identity resolution may not be tractable at ~2h/week without ground truth.** The assessment names this the recommendation's least defensible assumption, and the practitioner it cites needed fuzzy matching and still called it difficult. `/speckit-tasks` should sequence a resolution-rate measurement **early**, so SC-002's invented 95% target is tested against reality before the reader views are built on top of it.
4. **SC-002's 95% is an invented default**, labelled as such in the spec and checklist. It exists to make FR-002 and FR-004 testable, not because evidence supports that figure.
5. **Licensing was excluded from the assessment by owner decision.** This plan determines nothing about what may lawfully be re-published. Deferred, not cleared.
   - **Owner decision 2026-10-10**: still not researched, and the dataset is published without that determination — with the gap disclosed as `source_terms` on `manifest.json` and every Coverage Statement, in the page footer, and in `DATA-LICENSE.md` → *Source terms: not determined*, and with corrections and removal requests taken through the issue tracker (`corrections_url`). No legal conclusion either way.
6. **The upstream carries no contract, versioning or deprecation notice**, and three hosts in this family have already stopped resolving. The 2h/week budget is expected to go mostly on breakage, per the assessment's own high-confidence finding.
