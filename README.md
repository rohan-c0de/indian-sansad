# Indian Sansad

A resolved metadata layer over the Indian parliamentary record.

Published under a project name rather than a maintainer's name, per the project
constitution (Scope of Authority → Attribution).

## Source terms: not determined

**The terms under which the Lok Sabha publishes the underlying records have
never been established, and this dataset is published without that
determination** (owner decision, 2026-10-10). The CC BY 4.0 licence here covers
this project's added work only — the identity resolution, the joins, the
aggregates and the indexes; **no rights are granted over the parliamentary
records themselves**, so check the source's terms before relying on them. None
of this is a legal conclusion in either direction and none of it is legal
advice. **Corrections and removal requests — including from a rightsholder —
go through the issue tracker:**
[github.com/rohan-c0de/indian-sansad/issues](https://github.com/rohan-c0de/indian-sansad/issues).
[`DATA-LICENSE.md` → *Source terms: not determined*](./DATA-LICENSE.md#source-terms-not-determined)
is the full statement, and the same two lines travel inside the dataset as
`source_terms` and `corrections_url` on `manifest.json` and every Coverage
Statement.

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

**The ticked boxes in [`tasks.md`](specs/001-resolved-metadata-layer/tasks.md) are the count** —
no total is typed here, because the one that was went stale by seven tasks. The pipeline is built
and the dataset is built. **The reader page is built except subject search, and nothing has been
published to GitHub.**

### Done

- **Phases 1–5 complete** — guard rails (T001–T003), the blocking spike (T004–T020), the
  foundational layer (T021–T035), User Story 1 (T036–T061) and User Story 4 (T062–T069).
- **Phase 6's dataset side complete** — T070–T073: per-ministry profiles and the subject-search
  index, with their contract tests; and T079's dataset side, the per-session search digest and
  the asker-name lookup, which are built and published even though the view they were built for
  is not (see below).
- **The pipeline has been run end to end once against the live upstream** — 2026-10-10,
  **52m 38s measured**, fetching, resolving and publishing all **95,268** questions. That is the
  only end-to-end timing that exists.
- **The dataset is built** — the by-session, by-ministry and by-member partitions, the reference
  sets, the aggregates, the subject-search index, the per-session search digest and the coverage
  statement, each in both NDJSON and CSV except the three `search/` sets, which say so in the
  manifest. **The file and record counts live in `data/published/manifest.json` → `sets`**,
  written by the refresh that built the tree and described in
  [the dataset contract](specs/001-resolved-metadata-layer/contracts/published-dataset.md).
  `make refresh` prints the total it wrote; the bytes are `du -sh data/published/`. Neither is
  typed here: both moved as sets were added, and the figures that were typed here went stale
  within a day. The headroom is the part worth stating, and it is not close — the last measured
  build sat at **26% of the 1 GiB GitHub Pages ceiling** (2026-10-10), against T017's 31.8%
  projection; both are in
  [`spike/size-budget.md`](specs/001-resolved-metadata-layer/spike/size-budget.md).
- **Resolution meets SC-002**: **96.36%** (91,796 of 95,268 questions) with four owner-confirmed
  maintainer assertions; **94.78%** automatic. Both are published separately, because the
  automatic rate is below the 95% target.
- **The test suite passes** — `.venv/bin/python -m pytest` — and `make guard`, `make lint` and
  `make audit-fields` are clean. No count is quoted here on purpose: a hand-typed
  figure beside a growing suite went stale twice in two days, and a number nobody
  re-measures is worse than no number.

### Not done

- **One of the reader page's views is missing, and that is a measurement result rather than
  unfinished work.** The shell, the stylesheet, the fetch layer, the coverage display, the
  licence and source-terms footer, the ministry-profile view (T078), two-ministry comparison
  (T080) and `make serve-local` (T081) are all done. **Subject search (T079) is NOT** — it
  **STOPPED at its own gate**: rendering the first 25 results for a common word costs
  4,348,529 B against T019's 4,183,979 B first-load budget, and a two-word query 7,236,751 B.
  Its dataset side is built and published (the per-session digest and the asker-name lookup);
  the view is not, and the page shows one region saying so. The browser proof and the real
  first-load measurement (T082–T085) have not been run.
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
web/               the static reader page; no build step (T074-T077, T081 done)
data/published/    the dataset consumers take
data/assertions/   maintainer resolution corrections, surviving refreshes
tests/             resolution, resilience, contract, unit
tools/             maintainer-facing checks
spike/             throwaway spike code (Phase 2); not production
specs/             specification artefacts
```

Everything above exists. `data/published/` is a build output, git-ignored on `main` and served
from the `published` branch; `make serve-local` serves the page and the dataset together from
one origin, in the same layout the `published` branch carries.

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

**The dataset is published without that determination, with the gap disclosed
and a corrections path** — owner decision 2026-10-10, stated at the top of this
file and in full in
[`DATA-LICENSE.md` → *Source terms: not determined*](./DATA-LICENSE.md#source-terms-not-determined).
