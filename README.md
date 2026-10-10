# Indian Sansad

A resolved metadata layer over the Indian parliamentary record.

Published under a project name rather than a maintainer's name, per the project
constitution (Scope of Authority → Attribution).

## What this is meant to be

The Indian parliamentary question record for the covered period, with each
question already attached to a **single stable identity** for the Member who
asked it — consistent across every name form the source uses. Four reader-facing
views sit on that joined record.

The external interface is **a published dataset, not a service**: partitioned
static files in newline-delimited JSON and CSV, plus a static page that reads
exactly the files a third-party consumer takes. No server, no database, no
document file opened at any point.

See [`specs/001-resolved-metadata-layer/`](specs/001-resolved-metadata-layer/)
for the specification, plan, data model, dataset contract and task list, and
[`.specify/memory/constitution.md`](.specify/memory/constitution.md) for the
five principles that gate the work.

## Current status

**73 of 100 tasks are done** ([`tasks.md`](specs/001-resolved-metadata-layer/tasks.md)). The
pipeline is built and the dataset is built. **The reader page is not built, and nothing has been
published to GitHub.**

### Done

- **Phases 1–5 complete** — guard rails (T001–T003), the blocking spike (T004–T020), the
  foundational layer (T021–T035), User Story 1 (T036–T061) and User Story 4 (T062–T069).
- **Phase 6's dataset side complete** — T070–T073: per-ministry profiles and the subject-search
  index, with their contract tests.
- **The pipeline has been run end to end once against the live upstream** — 2026-10-10,
  **52m 38s measured**, fetching, resolving and publishing all **95,268** questions. That is the
  only end-to-end timing that exists.
- **The dataset is built**: **1,768 files, 257,804,931 bytes (245.9 MiB)** — 24.0% of the 1 GiB
  GitHub Pages ceiling — across the by-session, by-ministry and by-member partitions, the
  reference sets, the aggregates, the 2.37 MiB subject-search index and the coverage statement,
  each in both NDJSON and CSV.
- **Resolution meets SC-002**: **96.36%** (91,796 of 95,268 questions) with four owner-confirmed
  maintainer assertions; **94.78%** automatic. Both are published separately, because the
  automatic rate is below the 95% target.
- **159 tests pass**; `make guard`, `make lint` and `make audit-fields` are clean.

### Not done

- **The reader page does not exist.** `web/` is empty. T074–T085 — the page shell, the fetch
  layer, the coverage display, the ministry-profile and subject-search views, two-ministry
  comparison and `make serve-local` — are open. A static mockup of the intended page sits at
  [`mockup/`](specs/001-resolved-metadata-layer/mockup/) and is wired to nothing.
- **The refresh workflow has never run on GitHub.** `.github/workflows/refresh.yml` is written
  and statically checked (`make yamllint`, 0 findings) but unproven: the daily schedule, the
  force-push to the `published` branch and the 60-day keep-alive are all unobservable locally.
  **The `published` branch does not exist**, so GitHub Pages cannot be pointed at it yet.
- **`main` must stay unprotected.** The workflow pushes a keep-alive commit directly to `main` on
  every run, against GitHub's rule that a public repository's scheduled workflows are disabled
  after 60 days without repository activity. Branch protection blocking direct pushes would make
  the job fail every run — **loudly, by design**, rather than leaving the 60-day protection
  silently void. See
  [`spike/free-tiers.md`](specs/001-resolved-metadata-layer/spike/free-tiers.md) →
  *`main` must stay unprotected*.
- **Lok Sabha only.** No Rajya Sabha data is published — see *What is still unknown* below. The
  coverage statement declares this rather than implying both Houses.
- **Phases 7, 8 and 9 have not started** — the state and constituency entry point (T086–T090),
  polish and gate evidence (T091–T097), and the Rajya Sabha route investigation (T098–T100).
  `make validate` is still a deliberately-failing stub, owned by T091.

### What the spike established

- **The question-metadata route is retrieved and documented.** Three earlier passes failed to
  obtain it; it is `GET /api_ls/question/qetFilteredQuestionsAns` (the upstream's own spelling —
  `qet`, not `get`), reachable with no credential and no required header, from a laptop and from
  a free CI runner alike.
- **The full covered window is fetched and measured**: 95,269 questions across the 17th Lok
  Sabha (60,549) and the 18th (34,720), plus the 5,426-member roster.
- **Identity resolution works, unevenly — and SC-002 is met.** 99.68% of the 18th Lok Sabha's
  questions resolve to exactly one member, but only **85.45%** of the 17th's, for **90.64%**
  across the window with the original matcher. The adopted containment tier lifts that to
  **94.78% automatic**, and **four owner-confirmed maintainer assertions** carry it to
  **96.36%** (91,796 of 95,268 questions) — a **+1.36-point** margin over the 95% target, which
  was kept unchanged. The automatic rate remains **below** 95%, so the coverage statement
  publishes both figures separately. *The assisted figure was corrected from 96.26% on
  2026-10-09: the original recount scored one asserted form at a time and so missed 87 questions
  co-asked by two of them, which resolve only when both assertions are applied.*
- **Zero running cost is evidenced**, not asserted: every component sits on a named free tier
  with its behaviour at the limit quoted from the provider's own published pages.

### What is still unknown

- **Rajya Sabha material is not obtainable yet.** `GET /api_rs/members` returns HTTP 403 where
  every sibling path returns 404. The cause is narrowed — a request-shape or path filter rather
  than authorisation or IP reputation — but **unverified**. First release is **Lok Sabha only**,
  and the coverage statement will say so rather than implying both Houses.
- **Question and answer text is out of scope by principle.** It is served only behind document
  files, which this project never opens. It is a declared gap, not an omission.
- **Three session-level coverage anomalies**, all causes unverified: the 18th Lok Sabha's session
  1 has 7 sitting days and no questions; its session 8 has no sitting days and 4,500 questions;
  the 17th's session 13 has 4 sitting days and no questions.

## Constraints that shape every decision here

| | |
|---|---|
| **Cost** | Zero. Free tiers only — no paid service, trial or promotional credit. A tier the design is expected to exceed does not satisfy this; the remedy is to drop a capability, never to upgrade the plan. |
| **Upkeep** | About 2 hours per week in total. Routine manual work must be automated or dropped. |
| **Sources** | Already-structured sources only. No document file is ever opened, parsed or depended on — no PDF, no OCR, no text-layer extraction, at any stage. |
| **Language** | English only. No translation or transliteration path. |
| **Member fields** | Published member data is limited to name forms, party, state, constituency, House, term and sitting status. |

## A note on personal data

The upstream member endpoint serves personal phone numbers, a Delhi phone,
email, present and permanent addresses, date of birth, marital status and number
of sons and daughters — for 5,426 named people, without authentication.

**None of it is published here.** Publication is bounded to the field list above
and enforced by `tools/guard_no_raw_payloads.py`, which fails the tree if any
file carries an attribute outside that set. "The absence of a prohibition is not
permission": an attribute reaching the published record because nothing stopped
it is a breach whether or not anyone intended it.

No raw upstream payload is written inside this tree — not as a cache, not as a
fixture, not as a test file. Fetched bodies are transformed in memory behind the
field allowlist, or written under `$SANSAD_SCRATCH` outside the repository.

Terms of use, licensing and copyright were scoped out of the assessment by owner
decision. That **defers** the question of what may lawfully be re-published; it
does not clear it.

## Repository layout

```
src/sansad/        the pipeline — ingest, resolve, model, publish, views, signals
web/               the static reader page; no build step
data/published/    the dataset consumers take
data/assertions/   maintainer resolution corrections, surviving refreshes
tests/             resolution, resilience, contract, unit
tools/             maintainer-facing checks
spike/             throwaway spike code (Phase 2); not production
specs/             specification artefacts
```

Everything above exists except `web/`, which is empty. `data/published/` is a build output,
git-ignored on `main` and served from the `published` branch.

## Licence

Two licences, because there are two layers (owner decision, 2026-10-10).

- **Code — MIT.** See [LICENSE](./LICENSE). Copyright © 2026 Indian Sansad
  Maintainer.
- **Published dataset — CC BY 4.0 on the added work.** See
  [DATA-LICENSE.md](./DATA-LICENSE.md). The identity resolution, the joins, the
  aggregates and the indexes are this project's contribution and are licensed
  CC BY 4.0. **The underlying parliamentary records are not**, and remain
  subject to their source's terms.

Those terms are **unknown to this project**, because terms of use, licensing
and copyright were scoped out of the assessment by owner decision — as the
section above records, that defers the question rather than clearing it.
`DATA-LICENSE.md` says where the line falls field by field, so a consumer can
see which parts of a published row this project can license and which it
cannot.
