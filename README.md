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

**Nothing is built yet.** This repository currently contains the specification
artefacts and the Phase 1 guard rails only. The pipeline, the published dataset
and the reader page do not exist.

Two facts about the upstream source bound what can honestly be promised, and
both are recorded rather than resolved:

- **The question-metadata route has never been retrieved first-hand.** Three
  passes have failed to obtain it; the service base path returns a HAL index
  exposing only `self`, `health`, `health-path` and `metrics`, and `GET /api_ls`
  returns 404. User Story 1 depends on this route entirely. Phase 2 is a
  blocking spike against exactly this question.
- **Rajya Sabha member data is not yet obtainable.** `GET /api_rs/members`
  returns HTTP 403 where every sibling path returns 404; the cause is
  **UNVERIFIED**. First release is therefore **Lok Sabha only**, and the
  coverage statement will say so rather than implying both Houses.

The one data route verified end to end anywhere in this project is the Lok Sabha
member roster, `GET /api_ls/member`.

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

Most of these directories do not exist yet. They are created by the phase that
first needs them.
