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

**The blocking spike is complete; the pipeline is not built.** This repository contains the
specification artefacts, the Phase 1 guard rails, and the Phase 2 spike with its measurements.
`src/sansad/`, `web/` and `data/published/` do not exist yet.

**Phase 3 is blocked on one owner decision** — see
[`spike/spike-report.md`](specs/001-resolved-metadata-layer/spike/spike-report.md).

### What the spike established

- **The question-metadata route is retrieved and documented.** Three earlier passes failed to
  obtain it; it is `GET /api_ls/question/qetFilteredQuestionsAns` (the upstream's own spelling —
  `qet`, not `get`), reachable with no credential and no required header, from a laptop and from
  a free CI runner alike.
- **The full covered window is fetched and measured**: 95,269 questions across the 17th Lok
  Sabha (60,549) and the 18th (34,720), plus the 5,426-member roster.
- **Identity resolution works, unevenly.** 99.68% of the 18th Lok Sabha's questions resolve to
  exactly one member — but only **85.45%** of the 17th's, for **90.64% across the window**
  against a 95% target. That shortfall is the decision Phase 3 waits on.
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

`specs/`, `tools/`, `spike/` and the `Makefile` exist. `src/sansad/`, `web/`,
`data/published/`, `data/assertions/` and `tests/` do not — they are created by
the phase that first needs them.
