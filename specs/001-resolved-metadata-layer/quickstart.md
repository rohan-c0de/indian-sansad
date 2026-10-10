# Quickstart: Validating the Resolved Metadata Layer

**Feature**: `specs/001-resolved-metadata-layer` | **Date**: 2026-10-09

How to prove this feature works end to end. Scenarios map to `spec.md` user stories and success criteria. This is a validation guide — implementation belongs in `tasks.md`.

## Prerequisites

- Python 3.13 and `pytest`.
- Network access to the upstream host. Both Lok Sabha data routes are now verified end to end — the member roster and the question-metadata route; see [spike/route-capture.md](./spike/route-capture.md).
- **One-time repository setting**: GitHub Pages must be pointed at the **`published` branch**, not `main`. The dataset is force-pushed there as a single commit on every successful refresh (owner decision 2026-10-09, [spike/size-budget.md](./spike/size-budget.md)); `data/published/` is git-ignored on `main`. Nothing in the pipeline can set this, and until it is set the site serves the wrong branch.
- No credentials, no API key, no paid service. If any step appears to need one, that is a defect against FR-014.

## Setup

```
make setup      # create the environment and install dependencies
make refresh    # run one full ingestion and publish locally
```

`make refresh` must complete without prompting for anything. A prompt is a failure against FR-009.

`make refresh` writes `data/published/` **locally only** — that directory is git-ignored on `main`. Publishing is the scheduled workflow's job (T058): it force-pushes a single commit to the `published` branch on success, and pushes nothing at all on a failed or partial refresh so the previous snapshot keeps being served.

## Scenario 1 — Identity resolution across name variants (US1, FR-002)

**Run**: `pytest tests/resolution -k variants`

**Expected**: the fixture containing both `Shri Sunil Kumar Singh` and `Singh, Sunil K.` yields **one** `member_id` for both. Two members with genuinely different identities and similar names remain separate.

**Why this first**: it is the feature's foundation and the obstacle the assessment records as having stopped a prior attempt.

## Scenario 2 — Nothing is silently dropped (US1, FR-004, contract guarantee 2)

**Run**: `pytest tests/resolution -k unresolved`

**Expected**: a deliberately unresolvable asking name produces a published question with `resolution_status` of `unresolved` or `ambiguous`. The question count before and after resolution is **identical**. An ambiguous match lists its candidates rather than picking one.

**Fails if**: any question disappears, or an ambiguous name is assigned a single member without a maintainer assertion.

## Scenario 3 — Co-asked questions (US1, FR-003)

**Run**: `pytest tests/resolution -k co_asked`

**Expected**: one question record carrying several `member_id` values. Not several records.

## Scenario 4 — Joins are independently verifiable (FR-005)

**Run**: `make verify-joins`

**Expected**: for every published join, a resolution record exists giving the name form as written and the source record reference. The check recomputes nothing — it confirms a consumer could audit the join without re-deriving it.

## Scenario 5 — Subsets without the whole, on every axis FR-007 names (US2, US3, FR-007, contract guarantee 6)

**Run** — one call per axis:

```
make extract HOUSE=lok-sabha SESSION=8
make extract MINISTRY=<name>
make extract MEMBER=<member_id>
make extract STATE=<name>
make extract CONSTITUENCY=<name>
```

**Expected**: each call returns that subset alone, in both formats, with the reference sets available separately. No axis may require downloading the whole record.

- **Session, ministry and member** each come from their own published partition — one fetch per subset.
- **State and constituency** resolve through the member reference set. The check must confirm the extract fetched the member set plus only the matching members' files — not the whole question record, and not a per-state partition, which this dataset deliberately does not publish.
- **Totals must agree across axes.** The questions returned for a ministry in session 8 must equal the intersection of the ministry and session partitions. Because partitions republish the same records under different keys, **de-duplicate on `question_id` before comparing** (guarantee 6).

**Fails if**: any axis FR-007 names requires taking the whole record, or the same question is counted twice when two partitions are combined.

## Scenario 6 — Counts are reproducible and the basis is stated (US2, FR-012, SC-007)

**Run**: `make report MINISTRY=<name> SESSIONS=5-8`

**Expected**: a ministry question profile whose totals can be reproduced by counting the published question records by hand, and which states the counting basis alongside the numbers.

## Scenario 7 — Constituency entry point (US3, SC-008)

**Run**: `make lookup CONSTITUENCY=<name>`

**Expected**: the members representing it within the covered period, each with party and term, and their questions reachable. A constituency held by different members across the two terms lists both with periods, not merged.

## Scenario 8 — Composition totals reconcile (US4)

**Run**: `make composition LS_TERM=18`

**Expected**: category counts sum to that term's total membership. Members with missing attributes appear under an explicit "not stated" category, never omitted.

## Scenario 9 — Degrade quietly, alert the maintainer (FR-010, FR-011, SC-006)

**Run**: `pytest tests/resilience`

**Expected**, with the upstream simulated as unavailable, shape-changed, and truncated in turn:

- the published record remains coherent and dated, and the coverage statement flags it as last-known-good;
- the maintainer signal fires;
- no empty or partial record is ever presented as complete.

**Fails if**: visitors see an error, or a shape change passes without a signal. These are the failure modes the owner explicitly asked to be inverted — quiet for visitors, loud for the maintainer.

## Scenario 10 — Field scope is bounded (FR-008, SC-010)

**Run**: `make audit-fields`

**Expected**: no member attribute outside the FR-008 list appears anywhere in:

- **`data/published/`** — every partition and both formats, including the precomputed aggregates and the subject-search index;
- **`web/` and everything it renders** — the page source, any vendored file under `web/lib/`, and any attribute that reaches a reader only through an aggregate or index the page fetches;
- **every fixture, sample and test file in the repository** — `tests/`, and any sample or recorded upstream response committed anywhere in the tree.

The check **fails** if an unlisted personal attribute is present in any of those without a recorded authorising decision.

**Why this scope**: Constitution Principle V names pages, derived statistics and repository fixtures explicitly, and requires the audit to be re-run against what will actually be published rather than what was specified. A committed fixture of a raw upstream response is the likeliest route by which the full personal-data payload enters the repository, and the page is the likeliest route by which an attribute reaches a reader without passing through `data/published/`.

**Why this exists at all**: the assessment records that the upstream serves personal contact details, home addresses, dates of birth, marital status and family composition for 5,426 named people without authentication, and that no guardrail was adopted. This check is the only automated thing standing between that payload and publication.

## Scenario 11 — Coverage honesty (FR-013)

**Run**: `make coverage`

**Expected**: a coverage statement per House naming the period, sessions, known gaps, and current resolution rate. **If Rajya Sabha data is absent, the statement says Lok Sabha only** — it must not imply coverage it does not have.

## Scenario 12 — The reader page runs over the published files with no access to the upstream (US2, US3, FR-004, FR-013)

**Run**:

```
make serve-local   # serve web/ and data/published/ from one local static host
                   # (locally both come from the working tree; in production both come
                   #  from the `published` branch, which is what keeps them same-origin)
make test-page     # drive the page in a browser with the upstream blocked at the network level
```

**Expected**, with the upstream unreachable from the browser for the whole run:

- the page loads and both reader views work from files fetched off that one host — ministry and session counts with their type mix, subject search for prior occurrences, and the state/constituency entry point;
- **no request to the upstream is attempted.** The browser's network log must show requests to the static host only. One upstream request is a failure, not a warning;
- questions whose asker is `unresolved` or `ambiguous` are **visibly flagged in the page**, not filtered out of the counts and not quietly dropped from a member's list;
- the **coverage statement is visible on the page**, naming which Houses are covered — and saying Lok Sabha only while Rajya Sabha data is absent.

**Fails if**: the page needs the upstream to render anything, or an unresolved question is absent from a view it belongs in, or the coverage statement is reachable only by reading the dataset files directly.

**Why this exists**: Stories 2 and 3 are specified as a page running entirely in the visitor's browser over the published files, and each clause of that is independently checkable. The two things a UI most easily loses are the unresolved flag and the coverage statement — the same two the dataset contract makes load-bearing (guarantees 2 and 5).

## Full gate

```
make validate   # scenarios 1-12 plus the full test suite
```

Passing `make validate` means every functional requirement with an automatable criterion is met. It does **not** cover the measured-over-time criteria: SC-003 (unattended pickup), SC-004 (~2h/week upkeep), SC-005 (zero cost) and SC-009 (use by someone else) can only be observed in operation.
