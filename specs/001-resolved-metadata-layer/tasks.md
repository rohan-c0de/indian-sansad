# Tasks: Resolved Metadata Layer for the Indian Parliamentary Record

**Input**: Design documents from `/specs/001-resolved-metadata-layer/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/published-dataset.md, quickstart.md, `.specify/memory/constitution.md` v1.0.0

**Tests**: Included. Tests are requested explicitly — `plan.md` names pytest with reconciliation fixtures, and `quickstart.md` defines twelve validation scenarios as `pytest` and `make` invocations.

**Organization**: Tasks are grouped by user story so each story can be implemented, tested and delivered independently — with two deliberate exceptions stated under *Ordering Decisions* below.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4). Spike, foundational and polish tasks carry no story label.
- Include exact file paths in descriptions

## Path Conventions

Single project with a static front end, per `plan.md` → Project Structure: `src/sansad/` for the pipeline, `web/` for the page, `data/published/` for output, `data/assertions/` for maintainer corrections, `tests/` for tests, `tools/` for maintainer-facing checks, `spike/` for throwaway spike code.

---

## Ordering Decisions

Four orderings here depart from the template's default. Each is recorded so a reviewer can disagree with it.

1. **A spike is the first phase and a hard gate.** `plan.md` Risk 2 records that the question-metadata route has never been retrieved first-hand in three passes, and Risk 3 names identity resolution at ~2h/week the recommendation's least defensible assumption. User Story 1 depends on the first entirely and the whole feature on the second. No Phase 3+ task may begin until `spike/spike-report.md` exists.

2. **Spike item "can a free CI runner reach the route" follows "name the free CI tier", inverting the stated order.** The check has no runner to run on until a provider is chosen. Naming the tier is T007-T008; the reachability check is T009-T010.

3. **Spike item "measure bytes per partition and per first page load" runs twice, not once.** It is measured in the spike as a projection from a real prototype publish of one real session (T016–T019), and confirmed against the actual published dataset before any page code is written (T061) and against the actual page once it renders (T083, T090). A projection is not a measurement of the thing itself, and saying so is cheaper than discovering the gap after the page exists.

4. **User Story 4 (P3) is built before User Stories 2 and 3 (P2, P3).** This inverts spec priority and is done for one reason: you directed that the interactive reader page be built last. US4 ships as precomputed files in the published dataset and touches no page (`plan.md` → Front End), whereas US2 and US3 *are* the page. Building US4 first also establishes the `src/sansad/views/` aggregation layer and the FR-012 counting-basis stamp that US2's ministry profile reuses. The cost of the inversion: a P2 story lands after a P3 story. If that is the wrong trade, swap Phase 6 and Phase 7 — US4 has no dependency on US2 or US3.

**Standing constraint across every phase**: **no raw upstream payload is ever written inside the repository tree.** Not as a cache, not as a fixture, not as a spike artefact, not in a test. Every fetched body is transformed in memory behind the FR-008 field allowlist, or written under `$SANSAD_SCRATCH` outside the tree. T002 builds the automated guard, T004 is the first task permitted to touch the upstream at all, and T031 extends the guard to the three scopes `quickstart.md` scenario 10 names. This is Constitution Principle V — "'Published' covers everything a third party can reach: ... and any fixture, sample, or test file in the repository" — and `quickstart.md`'s own note that a committed raw-response fixture is the likeliest route by which the full personal-data payload enters the repo.

---

## Phase 1: Guard Rails Before the First Fetch

**Purpose**: The three things that must exist before anything fetches anything. Nothing here touches the upstream.

- [X] T001 Initialize the repository: run `git init` at repo root, and create `.gitignore` excluding `spike/out/`, `data/raw/`, `*.payload.json`, `*.raw.json`, `*.raw.csv`, `.env`, `.venv/`, `__pycache__/`; create `README.md` naming the project under a project name rather than the maintainer's name (Constitution → Scope of Authority → Attribution)
- [X] T002 Create the raw-payload guard in `tools/guard_no_raw_payloads.py`: exits non-zero if any file in the repo tree contains, as a field name or value-bearing key, any attribute outside the FR-008 set — specifically personal phone, Delhi phone, email, present address, permanent address, date of birth, marital status, and number of sons and daughters (Constitution Principle V verbatim list), matched case-insensitively across common spellings (`mobileNo`, `mobile_no`, `phoneNo`, `emailId`, `dob`, `dateOfBirth`, `maritalStatus`, `noOfSons`, `noOfDaughters`); and non-zero if any file matching a payload pattern exceeds 64 KB. Exit code is the whole interface — it prints the offending path and key, never the value
- [X] T003 Create `Makefile` at repo root with `SANSAD_SCRATCH ?= $(TMPDIR)sansad-scratch`, a `make scratch` target that creates it and **asserts the resolved path is not inside the repo root**, and a `make guard` target running `tools/guard_no_raw_payloads.py`. Every later fetch target depends on `scratch`

**Checkpoint**: `make guard` passes on an empty tree and `make scratch` refuses a path inside the repo. Fetching may now begin.

---

## Phase 2: Spike — Blocking Gate

**Purpose**: Settle the five questions that the rest of the plan rests on, before building anything that would have to be thrown away. Five spike items, in dependency order rather than stated order (see Ordering Decision 2).

**Gate rule**: every finding in this phase carries one verdict from `VERIFIED WORKING | VERIFIED BROKEN | UNVERIFIED | UNTESTABLE | NOT PRESENT`, with the output that produced it pasted verbatim. No figure is recorded as a paraphrase. A single empty or single successful result is recorded as "observed once", not as a general property.

**⚠️ CRITICAL**: No task from Phase 3 onward may start until `spike/spike-report.md` (T020) exists.

### Spike item 1 — capture the question-metadata route (`plan.md` Risk 2, spec Open Question 2)

- [X] T004 Capture the Lok Sabha question-metadata route by driving a browser against the source site's own question-listing pages and reading the network log — the method `research.md` establishes, because `GET /api_ls/question` returns a HAL index exposing only `self`, `health`, `health-path`, `metrics` and `GET /api_ls` returns 404. Record in `specs/001-resolved-metadata-layer/spike/route-capture.md`: method, exact path, every query parameter with its observed range, the pagination parameter and page-size ceiling, required headers, the response envelope shape, the total-record field and its value, and whether any credential is required. **Record field *names* and record *counts* only — no field values, and no payload committed** (T002 will fail the tree otherwise)
- [X] T005 Issue one programmatic request to the route captured in T004 and append to `spike/route-capture.md`: HTTP status line, `Content-Type`, response byte size, elapsed seconds, and the response header set — body written only under `$SANSAD_SCRATCH`. Repeat for `GET /api_ls/member`, the one route `research.md` records as verified end-to-end, as the control group. Paste both status lines
- [X] T006 Record in `spike/route-capture.md` whether the captured route serves the fields the pipeline needs — question id, house, session, date, type, subject, ministry, and the asking-member name form(s) per `data-model.md` → Question — naming each upstream field that maps to each, and listing any Question field that has **no** upstream source. A missing asking-member field is a VERIFIED BROKEN gate on User Story 1, not a detail

### Spike item 4a — name the free CI tier (Constitution Principle I; must precede item 2)

- [X] T007 Enumerate the candidate free CI providers that offer **scheduled** jobs, in `specs/001-resolved-metadata-layer/spike/free-tiers.md`, and choose one. No trial, no promotional credit, no free tier of a plan that becomes chargeable — Principle I and FR-014 count all three as paid
- [X] T008 For the chosen CI provider, record in `spike/free-tiers.md`, each figure quoted from that provider's own current published limits page with the URL and the date retrieved: scheduled-job support, minutes or runs per month, maximum single job duration, concurrency, whether schedules are disabled on repository inactivity, and **the documented behaviour at each limit** — hard stop, throttle, queue, or overage charge. An overage charge disqualifies the provider under Principle I; record the disqualification and return to T007 rather than accepting it

### Spike item 2 — confirm a free CI runner can reach the route

- [X] T009 Add a throwaway reachability workflow at the path the T007 provider uses (e.g. `.github/workflows/spike-reachability.yml` for GitHub Actions) that issues one request to the T004 route and one to `GET /api_ls/member` from the runner, printing status code, elapsed and response headers, asserting HTTP 200, and **writing no response body anywhere**
- [X] T010 Run the T009 workflow and record the result in `specs/001-resolved-metadata-layer/spike/ci-reachability.md` with the runner's log pasted verbatim. This is not a formality: `research.md` records `GET /api_rs/members` returning **403 where every sibling path returns 404**, cause UNVERIFIED, and a datacentre IP is one of the candidate causes. A 403 or 429 from the runner where the laptop got 200 is a VERIFIED BROKEN gate on FR-009's unattended refresh. Delete or disable the workflow once recorded

### Spike item 3 — measure the resolution rate and the hand-correction cost (`plan.md` Risk 3, spec Open Question 3)

- [X] T011 Build a throwaway resolver prototype at `spike/resolve_rate.py` — **not** in `src/`, because it is measurement scaffolding and keeping it out of `src/` stops it becoming the production matcher by default. It reads the member roster and a real slice of Lok Sabha question metadata from `$SANSAD_SCRATCH`, normalises name forms, and attempts exact → normalised → approximate matching in that order. It writes only its aggregate report into the repo
- [X] T012 Measure the resolution rate on that real slice and record in `specs/001-resolved-metadata-layer/spike/resolution-rate.md`: percentage resolving to **exactly one** member identity, percentage `ambiguous`, percentage `unresolved`, the absolute denominator, the slice definition (sessions and date span), and the matcher configuration including every threshold. Compare against **SC-002's 95%** and state the verdict. **Do not tune the matcher to reach 95%** — the figure is an invented default (spec Assumptions; checklist note 5) and the measurement's job is to test it, not to satisfy it
- [X] T013 From the same run, count the **distinct name forms** — not questions — that came out `unresolved` and `ambiguous`, and convert them to maintainer time in `spike/resolution-rate.md`: time a sample of at least 20 real corrections end to end and report median and maximum minutes per correction; first-pass total hours as distinct forms × median; and the steady-state hours per week implied by the rate at which *new* unresolved forms arrive across the slice's span. Compare both against **Principle II's ~2 hours per week**, and state which of the two numbers breaches it if either does. Also record the **mean and maximum asker count per question** from this slice — the multiplier `research.md` flags as never measured and which T017 needs
- [X] T014 Record the SC-002 decision in `spike/spike-report.md`: if the measured rate meets or exceeds 95%, record it met, with the figure. If it is below, record the gap and the two options — amend SC-002 in `spec.md` to the measured rate, citing T012 as the evidence, or close the gap with maintainer assertions at the cost T013 measured — and **stop for the owner's decision**. Do not choose, and do not proceed into Phase 3 on an assumed answer

### Spike item 4b — name the free static hosting tier (Constitution Principle I)

- [X] T015 For the chosen static host, record in `spike/free-tiers.md` — each figure quoted from the host's own current published limits page with URL and date retrieved: bandwidth per month, total storage, file-count ceiling, maximum single file size, requests per month, and **the documented behaviour at each limit** (hard stop, throttle, or overage charge — an overage charge disqualifies it). Separately confirm the host can serve **both** `data/published/` and `web/` from one origin, since the plan's same-origin argument — which is the whole reason the page is viable given the upstream's cross-origin block — depends on it

### Spike item 5 — measure bytes per partition and per first page load

- [X] T016 Build a prototype publish at `spike/publish_sample.py`, writing to `$SANSAD_SCRATCH`, that emits **one real session** from the T011 slice across every axis `contracts/published-dataset.md` names — by-session, by-ministry, by-member, and the reference sets — in **both** newline-delimited JSON and CSV. Record in `specs/001-resolved-metadata-layer/spike/size-budget.md` the bytes per file, per axis, per format, and the total
- [X] T017 Project the T016 measurement to the full covered window in `spike/size-budget.md`, showing the arithmetic: the real session's question count, the window's question count, and the per-member duplication factor from T013's measured **mean asker count** — the three inputs `research.md` records as unmeasured. State the projected total against T015's storage and bandwidth limits. If it exceeds them, the remedy under Principle I is to **drop published axes**, and the task records which axis goes; it is never to upgrade the plan
- [X] T018 Build a prototype subject-search index at `spike/index_sample.py` over the real subjects in the T011 slice, measure its bytes, and project to the full window in `spike/size-budget.md`. Record which of the two options `research.md` leaves open was measured — subjects only, or subjects plus ministry and member names — and record the other as **unmeasured**, not as equivalent
- [X] T019 Derive the first-page-load byte budget in `spike/size-budget.md`: from T015, T017 and T018, state the bytes a visitor must fetch to render the first ministry-profile view and the first constituency view, and the monthly visitor count the static tier's bandwidth allows at that size. This budget is what T083 and T090 measure the real page against
- [X] T020 Write `specs/001-resolved-metadata-layer/spike/spike-report.md`: one verdict per spike item with the producing output pasted, the SC-002 decision from T014, the Principle I evidence from T008 and T015 (every component, its tier, and its behaviour at the limit), and the Principle II figure from T013. Where an item failed, name the capability being reduced or dropped. **This file is the gate. Phase 3 does not start without it**

**Checkpoint**: the route is retrieved first-hand or the feature is blocked; the CI runner reaches it or FR-009 is blocked; the resolution rate and its correction cost are measured figures rather than assumptions; both free tiers are named with their limit behaviour; published size is projected from real bytes.

---

## Phase 3: Foundational (Blocking Prerequisites)

**Purpose**: The pipeline skeleton, the entity models, and the two safety mechanisms that must exist before any ingest code — the field allowlist and the non-persisting transport.

**⚠️ CRITICAL**: No user story work begins until this phase is complete.

- [X] T021 Create `pyproject.toml` pinning Python 3.13 with the two third-party pipeline dependencies `plan.md` names — an HTTP client and a tabular/serialisation library — plus `pytest` as a dev dependency, with identity reconciliation using the standard library's `difflib` rather than a third-party approximate string-matching library so the holdout-validated 0.90/0.02 thresholds carry into `src/` unchanged, and wire `make setup` in `Makefile` to create the environment and install them
- [X] T022 [P] Configure linting and formatting in `pyproject.toml` and add a `make lint` target
- [X] T023 Create the source tree per `plan.md` → Project Structure: `src/sansad/{ingest,resolve,model,publish,views,signals}/__init__.py`, `tests/{resolution,resilience,contract,unit}/`, `data/assertions/.gitkeep`, `web/`, `tools/`. **`data/published/` is created on disk but NOT committed on `main`** (owner decision 2026-10-09, `spike/size-budget.md`): add `data/published/` to `.gitignore`, and do **not** create `.gitkeep` files under it — a committed `.gitkeep` is exactly how a git-ignored build-output directory ends up tracked on `main`. The published dataset lives only on the rolling orphan branch `published`. `data/assertions/` **does** stay on `main` and keeps its `.gitkeep`, because maintainer corrections are an input that must survive a refresh rewriting the published branch wholesale
- [X] T024 [P] Create `src/sansad/model/member.py` with the Member entity from `data-model.md`, quoting its validation rules verbatim in the module docstring: `member_id` "MUST be stable across refreshes and MUST NOT change when a name variant is added"; two near-identical names "MUST NOT be merged; distinctness is decided on attributes beyond the name"; a party or House change "MUST retain one `member_id` with the change represented in `terms`, not split into two identities"; published fields "MUST be limited to those above"; missing attributes "MUST be represented as an explicit 'not stated' value, never silently dropped". Fields exactly: `member_id`, `canonical_name`, `name_variants`, `house`, `party`, `state`, `constituency` (absent for Rajya Sabha), `terms`, `sitting_status`, `source_record_ref`, `last_refreshed`
- [X] T025 [P] Create `src/sansad/model/question.py` with the Question entity from `data-model.md`, quoting verbatim: a co-asked question "MUST carry every asking member and MUST NOT be duplicated per asker"; an unresolvable asker "MUST be retained with `resolution_status` set to `ambiguous` or `unresolved`, and MUST NOT be dropped or assigned a guessed member"; a question outside the window "MUST be excluded, and its exclusion reflected in the Coverage Statement rather than passing silently"; a question attributed to a member not sitting on its date "MUST be flagged rather than silently re-attributed"; "Answer text is explicitly **not** part of this entity." `resolution_status` is exactly one of `resolved`, `ambiguous`, `unresolved`
- [X] T026 [P] Create `src/sansad/model/resolution_record.py` with fields `name_as_written`, `member_id` (nullable), `status` (`resolved`|`ambiguous`|`unresolved`), `method` — **all six values T046 can produce**, so any join shows which tier produced it (FR-005): `exact` | `normalised` | `normalised-reordered` | `approximate` | `token-containment` | `manual-assertion`, `candidates`, `source_record_ref`, `asserted_by` (`automatic`|`maintainer`), quoting verbatim: every join "MUST have a corresponding Resolution Record enabling independent verification"; a manual assertion "MUST survive subsequent refreshes and MUST NOT be overwritten by automatic matching"; `ambiguous` "MUST list its candidates; an ambiguous match MUST NOT be silently collapsed to the first candidate"
- [X] T027 [P] Create `src/sansad/model/ministry.py`, `src/sansad/model/session.py` and `src/sansad/model/constituency.py` per `data-model.md`, quoting verbatim: renaming a ministry upstream "MUST NOT create a second ministry identity"; `session_id` "MUST be scoped by House so the two series are never conflated"; a constituency held by different members across the two terms "MUST list both with their periods, not merged"
- [X] T028 [P] Create `src/sansad/model/coverage_statement.py` with fields `house`, `period_start`, `period_end`, `sessions_covered`, `known_gaps`, `resolution_rate`, `last_refreshed`, `last_known_good`, quoting verbatim: `resolution_rate` "MUST be published, not merely computed, so SC-002 is externally checkable"; on failure `last_known_good` "MUST indicate it and the record MUST remain coherent and dated rather than empty or partial"; if Rajya Sabha proves unobtainable the statement "MUST say so explicitly rather than implying both Houses are covered"
- [X] T029 Create the FR-008 field allowlist in `src/sansad/ingest/field_allowlist.py`: the only attributes that pass are name forms, party, state, constituency, House, term and sitting status. Everything else is dropped **in memory, at the ingest boundary, before any write** — so an excluded attribute never reaches a cache, a log line, an error message, or a test artefact. Name the excluded set in the module docstring from Constitution Principle V. Unknown new upstream fields default to **excluded**: "The absence of a prohibition is NOT permission"
- [X] T030 Create the non-persisting transport in `src/sansad/ingest/transport.py`: fetches, decodes and hands records straight to the T029 allowlist, and persists no raw body inside the repo tree. Any on-disk cache is rooted at `$SANSAD_SCRATCH` with an assertion that the resolved path lies outside the repo root, and the process exits non-zero if the assertion fails rather than falling back to a repo path
- [X] T031 Extend `tools/guard_no_raw_payloads.py` into a `make audit-fields` target covering the three scopes `quickstart.md` scenario 10 names: `data/published/` including every partition, both formats, the aggregates and the search index; `web/` and everything it renders including `web/lib/`; and every fixture, sample and test file under `tests/`. This is the only automated check standing between the upstream's personal-data payload and publication (SC-010), and it widens the audit beyond published output, which the plan's own Constitution Check flags as required ("Principle V's gate names 'pages' and 'derived statistics' explicitly")
- [X] T032 Create `src/sansad/signals/alerts.py` for the four maintainer signals `contracts/published-dataset.md` names — ingestion failure, upstream shape change, resolution rate below target, and any transition of a question **out of** `resolved` — kept separate from visitor-facing behaviour because FR-010 and FR-011 pull in opposite directions (quiet for visitors, loud for the maintainer)
- [X] T033 Create `src/sansad/ingest/shape.py`: compares the observed upstream field-name set against the set recorded in `spike/route-capture.md` and raises a T032 signal on any divergence — a field disappearing, being renamed, or being added (FR-011, Edge Cases)
- [X] T034 Create hand-authored fixtures under `tests/fixtures/` and the policy in `tests/fixtures/README.md`: **fixtures are hand-written or redacted, never a recorded upstream response**, because a committed raw response is the likeliest route by which the personal-data payload enters the repo (`quickstart.md` scenario 10). Must include the real variant pair `Shri Sunil Kumar Singh` / `Singh, Sunil K.`, a co-asked question, a deliberately unresolvable asking name, an ambiguous form matching several members equally, and two genuinely distinct members with near-identical names
- [X] T035 Add `Makefile` targets, stubbed to fail loudly until implemented, for every `quickstart.md` entry point: `refresh`, `verify-joins`, `extract`, `report`, `lookup`, `composition`, `coverage`, `serve-local`, `test-page`, `validate` — so each of the twelve scenarios has an address from the start

**Checkpoint**: entities carry their constraints verbatim, nothing can fetch without passing the allowlist, and nothing can persist a raw body in the tree. User story work may begin.

---

## Phase 4: User Story 1 — Questions already joined to the right member (Priority: P1) 🎯 MVP

**Goal**: Publish the Lok Sabha question record with each question attached to a single stable member identity across every name form the source uses, every unresolvable asker retained and visibly marked, and every join independently verifiable — consumable as files without re-deriving the resolution.

**Independent Test**: Take questions whose askers are written in several different name forms, read the published record, and confirm each resolves to exactly one member identity carrying party, state, constituency and term, or is visibly flagged unresolved. Delivers value with no reader page built at all.

### Tests for User Story 1

> Write these first and confirm they fail before implementing.

- [X] T036 [P] [US1] `tests/resolution/test_variants.py` — `quickstart.md` scenario 1: the fixture holding both `Shri Sunil Kumar Singh` and `Singh, Sunil K.` yields **one** `member_id`, and the two near-identical distinct members from T034 stay separate
- [X] T037 [P] [US1] `tests/resolution/test_unresolved.py` — scenario 2: an unresolvable asking name produces a published question with `resolution_status` of `unresolved` or `ambiguous`; the question count before and after resolution is **identical**; an ambiguous match lists its candidates rather than picking one
- [X] T038 [P] [US1] `tests/resolution/test_co_asked.py` — scenario 3 (FR-003): one question record carrying several `member_id` values, not several records
- [X] T039 [P] [US1] `tests/contract/test_published_dataset.py` — the nine guarantees in `contracts/published-dataset.md`, including guarantee 6's rule that a `question_id` appearing in several partitions is **one** question and a consumer combining partitions must de-duplicate rather than sum
- [X] T040 [P] [US1] `tests/resilience/test_upstream_failure.py` — scenario 9, with the upstream simulated unavailable, shape-changed and truncated in turn: the published record stays coherent and dated, the coverage statement flags `last_known_good`, the maintainer signal fires, and no partial record is presented as complete (SC-006)
- [X] T041 [P] [US1] `tests/unit/test_field_allowlist.py` — an upstream record carrying every excluded attribute from Principle V passes through T029 with all of them absent from the output, and an unrecognised new field is excluded by default

### Implementation for User Story 1

- [X] T042 [US1] Implement `src/sansad/ingest/members.py` reading the Lok Sabha roster through T030 and T029, mapping upstream fields to the T024 Member entity
- [X] T043 [US1] Implement `src/sansad/ingest/questions.py` reading the route recorded in `spike/route-capture.md` through T030 and T029, with the pagination parameters and page-size ceiling T004 observed, mapping to the T025 Question entity
- [X] T044 [US1] Implement `src/sansad/resolve/normalise.py`: name-form normalisation covering the forms T004 and T012 actually observed — honorific prefixes, surname-first inversion, initials, punctuation and spacing. Source forms are preserved exactly as written for FR-005 provenance; normalisation is for matching only and is not transliteration (Principle IV)
- [X] T045 [US1] Implement `src/sansad/resolve/identity.py`: `member_id` assignment (FR-002) — assigned once, never reused, never derived from a name, stable when a variant is added, and one identity retained across a party or House change with the change represented in `terms`
- [X] T046 [US1] Implement `src/sansad/resolve/match.py`: exact → normalised → normalised-reordered → approximate → **bidirectional token-containment**, in that order, carrying forward the matcher configuration T012 measured rather than a fresh guess, and recording the `method` per match for the Resolution Record. The containment tier is **adopted by owner decision 2026-10-09** and MUST be implemented as `spike/resolve_rate.py` implements it, **plus one fix** (note added 2026-10-09): that script's `resolve_form` calls `fallback(...)` from the exact, normalised and normalised-reordered tiers **above** the `def fallback` statement, so those three paths raise `UnboundLocalError: cannot access local variable 'fallback' where it is not associated with a value` instead of reaching the containment tier. **It never fired in the measured runs** — they completed, and the `ambiguous` column is 0 in every table — so **every measured figure stands unchanged**; `src/sansad/resolve/match.py` implements the intended behaviour and those three tiers do reach the fallback. So this task is **"as the spike, plus that fix"**, not "exactly as the spike" (`spike/resolution-rate.md` → *NOTE — a latent defect in `spike/resolve_rate.py`*). The semantics to implement: a form resolves if its canonical token set is a strict subset **or** strict superset of exactly one candidate member's token set; it is reached **only** when every earlier tier has failed to produce a single member; and more than one distinct member leaves the form `unresolved`/`ambiguous` rather than collapsing a genuine ambiguity (`data-model.md`). Thresholds carry over unchanged — `APPROX_THRESHOLD` 0.90, `APPROX_MARGIN` 0.02 — and the honorific list keeps `md`/`mohd` **unstripped**. Measured effect: +6.31 points on a blind holdout, 90.64% → 94.78% across the window (`spike/resolution-rate.md`)
- [X] T047 [US1] Implement `src/sansad/resolve/ambiguity.py`: several equally-good matches produce `ambiguous` with every candidate listed, never a collapse to the first; distinctness between near-identical names is decided on attributes beyond the name
- [X] T048 [US1] Implement `src/sansad/resolve/assertions.py` reading maintainer assertions from `data/assertions/`: an assertion survives every subsequent refresh and is never overwritten by automatic matching — which is why `data/assertions/` sits outside `data/published/` (`plan.md` → Structure Decision). **The first assertions are the four owner-confirmed pairs** from `spike/spike-report.md` → *Proposed assertions* (owner decision 2026-10-09), which take the window from 94.78% to **96.26%** — a 1.26-point margin over SC-002's 95%, and what carries it. A fifth pair was **dropped by the owner**; its form stays among the residual forms, now **21**. Each MUST be written with `asserted_by: maintainer` and its `name_as_written` exactly as the question route serves it. **Seed only pairs the owner has confirmed** — the spike's table is marked PROPOSED and an unconfirmed row is not an assertion
- [X] T049 [US1] Implement `src/sansad/resolve/records.py` emitting one Resolution Record per name form encountered, carrying the name as written and the source record reference, so a consumer can verify any join without re-deriving it (FR-005)
- [X] T050 [US1] Implement `src/sansad/publish/formats.py`: newline-delimited JSON and CSV writers emitting the same records, with neither authoritative over the other — the form a third party consumes without re-deriving the resolution (FR-006; `contracts/published-dataset.md`)
- [ ] T051 [US1] **Publish to the rolling orphan branch `published` (owner decision 2026-10-09, `spike/size-budget.md`).** The reasoning this gate carried: writing the partitions is what begins committing **216.5 MiB measured** per refresh, which breaches GitHub's "ideally less than 1 GB" guidance on about the **fifth** refresh and the 5 GB figure within twenty-four — so full history was rejected, and publishing only changed partitions slows growth without bounding it. The orphan branch bounds it because the dataset's history is one commit deep at all times. Concretely: write the partitions to a worktree of `published`, commit as a **single commit force-pushed** on success, and **push nothing on a failed or partial refresh** so the previous snapshot keeps being served (FR-010). `data/published/` is git-ignored on `main` — it is a build output and must never be committed there. Implement `src/sansad/publish/partitions.py` writing `data/published/by-session/` (House + session), `data/published/by-ministry/` (one file per ministry), and `data/published/by-member/` (one file per `member_id`, a co-asked question appearing in each asker's file, never duplicated per asker — FR-003) — in both formats
- [ ] T052 [US1] Implement `src/sansad/publish/reference.py` writing `data/published/reference/` for members, ministries, sessions and constituencies — whole sets, carrying the state and constituency a consumer filters on, since those two axes resolve through the member set rather than as question partitions
- [ ] T053 [US1] Implement `src/sansad/publish/coverage.py` writing one Coverage Statement per House to `data/published/`, carrying the period, sessions covered, known gaps, `last_refreshed`, and `last_known_good` — and stating **Lok Sabha only** while no Rajya Sabha route exists (FR-001, FR-013; `quickstart.md` scenario 11 via `make coverage`). **Publish TWO resolution rates separately, not one** (owner decision 2026-10-09): the **automatic** rate, resolved by the matcher alone with no maintainer assertion counted, and the rate **including maintainer assertions**. Both are labelled and neither is presented as the other. This exists so SC-002's 95% is externally checkable against what the pipeline does unaided: the automatic rate is the one that regresses when the upstream changes, and a single blended figure would hide a matcher regression behind accumulated hand corrections
- [ ] T054 [US1] Implement `src/sansad/publish/last_known_good.py`: on a failed or shape-changed refresh, the previously published record is retained and re-dated as last-known-good rather than replaced by an empty or partial one (FR-010)
- [ ] T055 [US1] Implement `src/sansad/cli.py` and wire `make refresh` to run one full ingestion and publish **without prompting for anything** — a prompt is a failure against FR-009 (`quickstart.md` Setup)
- [ ] T056 [US1] Implement `tools/verify_joins.py` and wire `make verify-joins` — scenario 4: for every published join a Resolution Record exists giving the name form as written and the source record reference. The check recomputes nothing; it confirms a consumer could audit the join
- [ ] T057 [US1] Implement `tools/extract.py` and wire `make extract` for all five FR-007 axes — scenario 5: `HOUSE`/`SESSION`, `MINISTRY` and `MEMBER` each from their own partition in one fetch; `STATE` and `CONSTITUENCY` through the member reference set plus only the matching members' files, asserting the whole question record was **not** downloaded; and de-duplication on `question_id` before any cross-axis total comparison
- [ ] T058 [US1] Add the scheduled refresh **and publish** workflow at the T007 provider's workflow path (e.g. `.github/workflows/refresh.yml` for GitHub Actions) with the signal wiring from T032, inside the job-duration and monthly-minute limits T008 recorded (FR-009). **This task owns the publish mechanism and the 60-day keep-alive** (owner decision 2026-10-09, `spike/size-budget.md`) — no other task did, which is why both land here rather than in a new one. The workflow MUST: (a) **read the previous snapshot from the `published` branch before overwriting it**, because FR-010's last-known-good and FR-011's signal for a question leaving `resolved` both need the prior record to compare against; (b) on success, **force-push a single commit to the orphan branch `published`**, which GitHub Pages serves; (c) on a failed or partial refresh, **push nothing**, so the previous snapshot keeps being served; (d) on **every** run including one that finds nothing new, **commit a small run-timestamp file to `main`** — this is the keep-alive against the rule T008 recorded, *"In a public repository, scheduled workflows are automatically disabled when no repository activity has occurred in 60 days"*, and it exists on `main` because **whether a push to a non-default branch counts as repository activity is UNVERIFIED** and FR-009 must not rest on that reading; (e) hold the `contents: write` permission the force-push and the timestamp commit require, which the T009 spike workflow deliberately did not
- [ ] T059 [US1] Run one real publish via `make refresh`, then run `make guard` and `make audit-fields` against the actual published output and paste both outputs — the Constitution requires the Member-fields gate be re-run "against what will actually be published, not against what was specified" (SC-010)
- [ ] T060 [US1] Run `quickstart.md` scenarios 1, 2, 3, 4, 5, 9, 10 and 11 against the real published dataset and paste each output into `specs/001-resolved-metadata-layer/spike/us1-validation.md`, with a verdict per scenario
- [ ] T061 [US1] **Size gate before any page code**: re-measure the real published dataset — bytes per partition, per axis, per format, and the total — against T015's tier limits and T017's projection, and record both figures side by side in `spike/size-budget.md`. If the projection was wrong, say by how much. If the total exceeds the tier, drop published axes per Principle I and re-run T060; do not upgrade the plan

**Checkpoint**: User Story 1 is complete and independently useful — a third party can take the joined record as files. SC-001 is satisfiable, SC-002's real figure is published in the coverage statement, and the dataset's measured size is known before a line of page code exists.

---

## Phase 5: User Story 4 — Composition and subject trends as published files (Priority: P3)

**Goal**: Precomputed House-composition and subject-trend files in the published dataset, limited to party, state and terms served, each stating its counting basis. No page (`plan.md` → Front End: "Story 4 is not on the page for the first release").

**Independent Test**: Request a composition breakdown for one term and confirm the categories sum to that term's total membership, with missing attributes under an explicit "not stated" category. Separately request a subject's per-session series and confirm it can be reproduced by counting the published question records.

**Why before US2 and US3**: see Ordering Decision 4 — the page is built last, and this phase establishes the aggregation layer and counting-basis stamp US2 reuses.

### Tests for User Story 4

- [ ] T062 [P] [US4] `tests/contract/test_aggregates.py` — composition categories sum to the term's total membership; a member with a missing attribute appears under "not stated" and is never omitted; every aggregate file carries a counting basis
- [ ] T063 [P] [US4] `tests/unit/test_composition_fields.py` — the composition breakdown uses **only** party, state and terms served; gender, age band, profession and qualification are absent (FR-008, Principle V, spec US4 Note)

### Implementation for User Story 4

- [ ] T064 [US4] Implement `src/sansad/views/basis.py`: the counting-basis stamp every aggregate carries, stating what was counted and how (FR-012, SC-007)
- [ ] T065 [US4] Implement `src/sansad/views/composition.py`: per-term breakdown by party, state and number of terms served only, with an explicit "not stated" category for missing attributes
- [ ] T066 [US4] Implement `src/sansad/views/subject_trends.py`: per-session frequency series per subject, each carrying its T064 basis
- [ ] T067 [US4] Write both to `data/published/aggregates/` in both formats via T050, and add them to the Coverage Statement's set list
- [ ] T068 [US4] Wire `make composition TERM=18` and run `quickstart.md` scenario 8, pasting the output and the hand reconciliation of the totals
- [ ] T069 [US4] Run `make audit-fields` over `data/published/aggregates/` and paste the output — Principle V's gate names derived statistics explicitly

**Checkpoint**: US4 ships as files. US1 and US4 are both complete with no page in existence.

---

## Phase 6: User Story 2 — Ministry question load and prior occurrences of a subject (Priority: P2)

**Goal**: An interactive page running entirely in the visitor's browser over the published files, showing a ministry's question counts and type mix across a span of sessions, and whether a subject has been asked before. Every figure states its counting basis, unresolved and ambiguous questions are visibly flagged rather than hidden, and the coverage statement is on the page.

**Independent Test**: Pick a ministry and a period, read its profile on the page, and reproduce the counts and type mix by hand from the published records. Separately search a subject and confirm prior near-identical subjects come back with their dates, ministries and asking members.

**Prerequisite**: `spike/spike-report.md` exists (T020) **and** the published dataset exists and has been size-measured (T061). This is the "page last" constraint.

### Dataset side

- [ ] T070 [US2] Implement `src/sansad/views/ministry_profile.py`: precomputed per-ministry × per-session question counts and question-type mix, each carrying its T064 counting basis, written to `data/published/aggregates/` — precomputed rather than browser-computed because `research.md` records that fetching ~10^5 records into a page is not viable
- [ ] T071 [US2] Implement `src/sansad/publish/search_index.py` writing the subject-search index to `data/published/search/`, using the tokenisation and scope T018 actually measured — and recording in the module docstring that the unmeasured alternative scope was not adopted on the basis of measurement
- [ ] T072 [US2] Measure the real search index's bytes against T018's projection and T019's page-load budget, recording both in `spike/size-budget.md`. If it exceeds the budget, narrow the index scope before writing any page code
- [ ] T073 [P] [US2] `tests/contract/test_search_index.py` and `tests/contract/test_ministry_profile.py` — the index resolves a known subject to its real prior occurrences with dates, ministries and askers; the profile's totals match a direct count of the published question records after de-duplicating on `question_id`

### Page side

- [ ] T074 [US2] Create `web/index.html`: the page shell with no build step, loading `web/app.js` as an ES module and `web/style.css`, and carrying the coverage statement region that T077 fills
- [ ] T075 [P] [US2] Create `web/style.css` — hand-written, no framework, no build step
- [ ] T076 [US2] Create `web/app.js` with a fetch layer that reads **only** same-origin published files under `data/published/` and makes no request to the upstream — the restriction is load-bearing: `research.md` records that cross-origin browser requests to the upstream are not permitted, and the page's viability rests on reading this project's own files from its own host
- [ ] T077 [US2] Implement the coverage-statement display in `web/app.js`, visible on the page itself rather than reachable only by reading the dataset files, and saying **Lok Sabha only** while Rajya Sabha data is absent (scenario 12, FR-013)
- [ ] T078 [US2] Implement the ministry profile view in `web/app.js`: pick a ministry and a span of sessions, show question counts and type mix and how both changed, with the counting basis shown beside every figure, and **unresolved and ambiguous questions visibly flagged rather than filtered out of the counts** (FR-004, FR-012, scenario 12)
- [ ] T079 [US2] Implement the subject-search view in `web/app.js` over the T071 index: prior occurrences of a subject listed with dates, ministries and asking members
- [ ] T080 [US2] Implement two-ministry comparison in `web/app.js` using the same counting basis for both and stating what that basis is (US2 acceptance scenario 3)
- [ ] T081 [US2] Wire `make serve-local` to serve `web/` and `data/published/` from one local static host on one origin, as the T015 host does
- [ ] T082 [US2] Wire `make test-page` to drive the page in a browser **with the upstream blocked at the network level** and run scenario 12, asserting: both views work from that one host; the browser network log shows requests to the static host **only** — one upstream request is a failure, not a warning; unresolved and ambiguous questions are visibly flagged; the coverage statement is visible. Paste the network log summary
- [ ] T083 [US2] Measure the **actual** first-page-load bytes from the browser network log against T019's budget, and record the measured figure beside the projected one in `spike/size-budget.md`. This closes spike item 5 against the real thing rather than a projection
- [ ] T084 [US2] Run `make audit-fields` over `web/` and `web/lib/` and paste the output — a page is a new route by which an unlisted attribute reaches a reader without passing through `data/published/`, which the plan's Constitution Check names as the reason the audit scope had to widen
- [ ] T085 [US2] Run `quickstart.md` scenario 6 via `make report MINISTRY=<name> SESSIONS=5-8`, reproduce the totals by hand from the published records, and paste both

**Checkpoint**: US1, US4 and US2 all work. The page exists and has been proven to need nothing but this project's own files.

---

## Phase 7: User Story 3 — State and constituency entry point (Priority: P3)

**Goal**: A visitor who knows only where they live reaches their members and their questions, with a constituency held by different members across the two terms showing both rather than one merged entry.

**Independent Test**: Enter a constituency name, confirm the members who represented it in the covered period are listed with party and term, and confirm their questions are reachable from there.

- [ ] T086 [US3] Extend `src/sansad/publish/reference.py` to write the constituency reference set with `representations` as member-and-period pairs within the covered window, so a seat held by different members across the two terms lists both with their periods rather than merged (US3 acceptance scenario 3)
- [ ] T087 [P] [US3] `tests/contract/test_constituency_reference.py` — a constituency with two different holders across the covered terms lists both with periods; a state resolves to its members; every member reached this way has party and term
- [ ] T088 [US3] Implement the state and constituency entry view in `web/app.js` using the published two-fetch path — read the member reference set, filter to the state or constituency, then fetch only those members' files — never the whole question record, and never a per-state partition, which this dataset deliberately does not publish
- [ ] T089 [US3] Wire `make lookup CONSTITUENCY=<name>` and run `quickstart.md` scenario 7, pasting the output including a constituency with two holders across the terms
- [ ] T090 [US3] Re-measure first-page-load bytes with the third view present, against T019's budget, and record it in `spike/size-budget.md` — adding a view adds fetches, and the budget is per page load, not per view

**Checkpoint**: all four user stories are independently functional. SC-008 is satisfiable.

---

## Phase 8: Polish, Gate Evidence & Cross-Cutting Concerns

- [ ] T091 Wire `make validate` to run `quickstart.md` scenarios 1–12 plus the full test suite, and record in `README.md` what it does **not** cover: SC-003 (unattended pickup), SC-004 (~2h/week upkeep), SC-005 (zero cost) and SC-009 (use by someone else) are observable only in operation
- [ ] T092 [P] Write the consumer-facing dataset documentation in `README.md`, pointing at `contracts/published-dataset.md` for the guarantees, and stating guarantee 6's de-duplication rule and the breaking-change policy where a consumer will actually see them
- [ ] T093 Confirm FR-016 end to end: every published set under `data/published/` carries the date it was last rebuilt, and add the assertion to `tests/contract/test_published_dataset.py`
- [ ] T094 Write `specs/001-resolved-metadata-layer/gate-evidence.md` with the executed-check output for all five Constitution gates: Cost (every component, its named free tier, and its behaviour at the limit, from T008 and T015); Upkeep (the measured hours per week from T013 plus the observed figure after the first scheduled runs, and the project total); Sources (Principle III, FR-015: every input identified as already-structured, no document file opened, parsed or depended on, and any fact available only in a document recorded as a gap in the coverage statement); Language (English only, no translation path); Member fields (the published field list diffed against the FR-008 set across dataset, page, aggregates and fixtures). A gate is passed by evidence, not by assertion
- [ ] T095 Record the measured upkeep figure against Principle II after the scheduled refresh has run unattended for at least two cycles, in `gate-evidence.md`, including what the time was actually spent on — `plan.md` Risk 6 expects most of it to go on upstream breakage
- [ ] T096 [P] Add `tests/unit/test_state_transitions.py` covering the `resolution_status` transitions in `data-model.md`, including that a transition **out of** `resolved` raises a maintainer signal because a previously published join has become uncertain
- [ ] T097 Delete the spike's throwaway code — `spike/resolve_rate.py`, `spike/publish_sample.py`, `spike/index_sample.py` and the T009 reachability workflow — keeping only the recorded findings under `specs/001-resolved-metadata-layer/spike/`. Measurement scaffolding left in the tree becomes production code by accident

---

## Phase 9: Rajya Sabha — Route Investigation Only (Deferred)

**Purpose**: Settle `plan.md` Risk 1 and spec Open Question 1. **This phase investigates and stops.** It builds no ingest, no partition and no page. Nothing downstream of the finding is in scope here — that is a separate feature.

**Why separate**: `research.md` records `GET /api_rs/members` returning HTTP 403 where `GET /api_rs/member` and `GET /api_rs/question` both return 404, cause **UNVERIFIED**. Three causes are consistent with that observation — a bot or WAF rule, a path-specific block, or genuine authorisation — and `research.md` is explicit that settling it needs browser network capture, not more path probing. A Lok Sabha-only release already satisfies FR-001 by declaring itself as such; what is unmet is the owner's wider scope decision.

- [ ] T098 Drive a browser against the Rajya Sabha member pages and capture the network log, recording in `specs/001-resolved-metadata-layer/spike/rs-route.md` the exact requests those pages make, their status lines pasted verbatim, and any header or cookie that differs from the Lok Sabha requests T004 captured. Lok Sabha is the control group: diff against it rather than theorising about the 403
- [ ] T099 Record in `specs/001-resolved-metadata-layer/spike/rs-route.md` which of the three candidate causes the T098 evidence supports, and mark it **UNVERIFIED** if the evidence does not distinguish them. Do not declare one cause authoritative to resolve the ambiguity. If a route is found, confirm it is reachable from the T007 CI runner too, since T010 may have shown a laptop and a runner are not equivalent
- [ ] T100 Record the outcome and stop: if a reachable route exists, open a follow-on feature for Rajya Sabha ingestion rather than extending this one; if not, confirm the Coverage Statement still says Lok Sabha only and that `contracts/published-dataset.md`'s Rajya Sabha note remains accurate. Widening scope inside this phase is a breach of the Constitution's at-implementation gate

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Guard Rails)**: no dependencies. Must precede every fetch.
- **Phase 2 (Spike)**: depends on Phase 1. **Blocks everything after it.** Internally: T004 → T005, T006; T007 → T008 → T009 → T010; T004 + T005 → T011 → T012 → T013 → T014; T015 independent of the route work; T013 → T016 → T017; T018 → T019; all → T020.
- **Phase 3 (Foundational)**: depends on `spike/spike-report.md` (T020). Blocks all user stories.
- **Phase 4 (US1, P1)**: depends on Phase 3. Blocks US2, US3 and US4 — all three read the published dataset US1 produces.
- **Phase 5 (US4, P3)**: depends on Phase 4. No dependency on US2 or US3.
- **Phase 6 (US2, P2)**: depends on Phase 4 and on T061's size gate; reuses T064 from Phase 5.
- **Phase 7 (US3, P3)**: depends on Phase 4 and on Phase 6's `web/app.js` fetch layer (T076) and coverage display (T077).
- **Phase 8 (Polish)**: depends on every story phase intended for the release.
- **Phase 9 (Rajya Sabha)**: independent of every other phase and deliberately last. It can start any time without blocking anything, and nothing blocks on it.

### User Story Dependencies

- **US1 (P1)**: depends only on the spike and the foundation. The MVP.
- **US4 (P3)**: depends on US1's published records. Independently testable via `make composition`.
- **US2 (P2)**: depends on US1's published records and reuses US4's counting-basis stamp. Independently testable via `make test-page` and `make report`.
- **US3 (P3)**: depends on US1's member and constituency reference sets and on US2's page shell. Independently testable via `make lookup`. This is the one genuine cross-story page dependency — US3 adds a view to a page US2 creates.

### Parallel Opportunities

- Phase 2: T015 (static hosting tier) runs alongside the whole route-and-resolution line — it depends on nothing the route work produces.
- Phase 3: T024–T028 (the six model files) are all `[P]`; T022 runs alongside them.
- Phase 4: T036–T041 (all six test files) are `[P]` and should be written together and seen to fail before T042 starts.
- Phase 5: T062 and T063 are `[P]`.
- Phase 6: T073 and T075 are `[P]`; the dataset side (T070–T073) can proceed while the page shell (T074–T075) is written.
- Phase 9 runs in parallel with any phase, by any hand.

### Within Each User Story

- Tests are written and seen to fail before implementation.
- Models before resolution; resolution before publication; publication before any aggregate; aggregates before any page view that reads them.
- A measurement gate (T061, T072, T083, T090) is passed before the work downstream of it begins — that is what makes it a gate rather than a note.

---

## Parallel Example: User Story 1 Tests

```bash
# Write all six US1 test files together, then confirm every one fails:
Task: "tests/resolution/test_variants.py — one member_id across both recorded name forms"
Task: "tests/resolution/test_unresolved.py — question count identical before and after resolution"
Task: "tests/resolution/test_co_asked.py — one record, several member_ids"
Task: "tests/contract/test_published_dataset.py — the nine contract guarantees"
Task: "tests/resilience/test_upstream_failure.py — unavailable, shape-changed, truncated"
Task: "tests/unit/test_field_allowlist.py — every excluded attribute absent from output"
```

---

## Implementation Strategy

### The spike is not optional and not parallel

Phases 1 and 2 run to completion first, alone. Three figures come out of them that the rest of the plan has been assuming: whether the question-metadata route exists and is reachable from a free runner, what the real resolution rate is against SC-002's invented 95%, and what the published output actually weighs. If the resolution rate comes in materially below 95%, T014 stops for the owner's decision rather than tuning the matcher until the number looks right.

### MVP (User Story 1 only)

1. Phase 1 — guard rails
2. Phase 2 — spike, to a written report
3. Phase 3 — foundation
4. Phase 4 — US1
5. **Stop and validate**: `quickstart.md` scenarios 1–5, 9, 10, 11 against real published output, outputs pasted
6. Publish the dataset. It is useful with no page in existence — which is what US1's independent test asserts

### Incremental delivery

1. Spike report → the three assumptions are measured facts or named blockers
2. US1 → the published dataset (MVP, no page)
3. US4 → composition and subject-trend files in that dataset (still no page)
4. US2 → the page's first two views, with first-page-load bytes measured against the budget
5. US3 → the page's third view, bytes re-measured
6. Rajya Sabha route investigation, any time, blocking nothing

### Notes

- `[P]` tasks touch different files and have no incomplete dependency.
- `[Story]` labels map tasks to spec user stories; spike, foundational, polish and Rajya Sabha tasks carry none by design.
- Every spike and validation task records a verdict and pastes the output that produced it. Reading the code is not evidence that it works.
- No raw upstream payload is ever written inside the repo tree — `make guard` enforces it, and `make audit-fields` enforces the wider Principle V field scope across dataset, page and fixtures.
- Where a measurement contradicts a figure in `spec.md`, `plan.md` or `research.md`, the measurement is recorded and the document corrected. The figures those documents carry are labelled assumptions, not findings.
