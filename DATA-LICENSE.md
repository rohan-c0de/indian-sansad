# Licence for the published dataset

**Owner decision, 2026-10-10.** This file covers `data/published/` — the
dataset served from the `published` branch. The code that builds it is covered
separately by [LICENSE](./LICENSE) (MIT).

## Two layers, and only one of them is ours to license

The published dataset is a derivative work over records this project did not
create. Those are two different things and they carry different terms.

### The added work — CC BY 4.0

Everything this project contributes is licensed
**[Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)**:

- **the identity resolution** — the stable `member_id` layer, the name-variant
  groupings behind it, the five matching tiers and their outcomes, and the
  maintainer-confirmed assertions in `data/assertions/`;
- **the joins** — the link from each question to its asking members, and the
  per-name-form resolution records that make each link auditable;
- **the ministry identity layer** — `ministry_id`, the confirmed rename
  mappings, and the former-name history attached to each ministry;
- **the aggregates** — composition, subject trends, ministry profiles, and the
  counting-basis statements published beside them;
- **the indexes** — the subject-search index, including its tokenisation and
  its encoding;
- **the partition scheme and schemas** — the subset axes, field definitions and
  file layouts described in
  `specs/001-resolved-metadata-layer/contracts/published-dataset.md`;
- **the coverage statement**, and the prose of this and the other published
  documentation.

You may share and adapt it, including commercially, under those terms. The
attribution to use, verbatim:

> Contains data from Indian Sansad (https://github.com/rohan-c0de/indian-sansad), licensed CC BY 4.0, built over records published by the Lok Sabha.

It names the source layer as well as this project, because an attribution that
credited only this project would imply the records themselves are ours.

### This line points at the repository, not at a published site

There is no public site yet: the `published` branch does not exist until the
first workflow run, and GitHub Pages can only be pointed at it afterwards. The
URL above is the repository, which does exist.

**Once a Pages URL exists, every one of these needs updating. The list is here
so none is missed, and none of them is done.**

| Where | What changes |
|---|---|
| `DATA-LICENSE.md` — the attribution line above | the canonical link becomes the site, or names both |
| `README.md` | carries **no URL at all** today; wants the site link, at least in the Licence section |
| `contracts/published-dataset.md` → "Where it is published" | says paths resolve "relative to wherever the branch is served"; can name the origin |
| `spike/free-tiers.md` lines ~258-259 | `https://rohan-c0de.github.io/indian-sansad/...` is written there as a **prediction**; T015's verdict is "VERIFIED by construction, not by execution" and becomes observed |
| `spike/free-tiers.md` line ~287 | records that the URL is derived from the maintainer's handle — the live Attribution deviation; the decision to transfer to an organisation would change the URL again |
| `specs/001-resolved-metadata-layer/mockup/README.md` lines ~224-225 | the same predicted URLs |
| `data/published/coverage.jsonl` and `manifest.json` | **neither carries a project URL or this attribution string today.** A consumer who takes only the files therefore has no link to attribute, which is a gap in CC BY compliance, not a cosmetic one. Needs a field added in `src/sansad/publish/coverage.py` and `partitions.py` → `write_manifest`, plus a contract test |
| `web/index.html`, `web/app.js` (T074, T076) | not built; the page should display the attribution rather than leave a visitor to find this file |

Changing the URL later does not invalidate anything already distributed under
CC BY 4.0 — the licence does not expire — but a stale link is a broken
attribution for anyone following it.

### The underlying parliamentary records — not ours, terms unknown to us

The question metadata and the member roster come from the Lok Sabha's own
published sources. **This project asserts no licence over them, and CC BY 4.0
above does not and cannot extend to them.** They remain subject to whatever
terms their source applies.

**We do not know what those terms are.** This is a recorded gap, not an
oversight and not a judgement that reuse is permitted:

> *"Terms of use, licensing and copyright were excluded from the assessment by
> owner decision. This feature is specified without any determination of what
> may lawfully be re-published. That is a deferred question, not a cleared
> one."*
> — `specs/001-resolved-metadata-layer/spec.md`, Assumptions

The same exclusion is recorded in
`.specify/assessments/indian-sansad/intake.md` ("Out of scope for this
assessment. Do not research terms of use, licensing or copyright"),
`problem.md` ("This defers a risk; it does not establish that none exists"),
`decision.md` ("Licensing stays scoped out — deferred, not cleared"),
`research.md` ("this document makes **no claim** about what may lawfully be
re-hosted or redistributed") and `.specify/memory/constitution.md`.

**What this means for you.** If you reuse the underlying records — as opposed
to the resolution, joins and aggregates layered over them — satisfying CC BY
4.0 is not sufficient, because this project has no standing to grant you
anything over material it does not own. Establishing the source's terms is
your responsibility and ours; neither has been done.

## Where the line falls, concretely

Field names below are the ones the dataset actually publishes, read off the
built files rather than from the schema prose.

**A question record** (`by-session/`, `by-ministry/`, `by-member/`):

| Field | Layer | Licence |
|---|---|---|
| `question_id`, `subject`, `type`, `date`, `session`, `house` | source record | the source's terms — **unknown**, see above |
| `asking_members` — the resolved `member_id` list, which is the whole point of this project | added | CC BY 4.0 |
| `resolution_status` | added | CC BY 4.0 |
| `ministry_id` | added | CC BY 4.0 |
| `source_record_ref`, `last_refreshed` | added | CC BY 4.0 |

Note that a question record carries **no ministry name and no asker name** —
only ids. The source-derived names sit in the reference and resolution sets:

| Where | Field | Layer |
|---|---|---|
| `resolution-records.jsonl` | `name_as_written` | source record |
| `resolution-records.jsonl` | `member_id`, `method`, `status`, `candidates`, `asserted_by` | added |
| `reference/members.jsonl` | `canonical_name`, `party`, `state`, `constituency`, `sitting_status`, `terms` | source record |
| `reference/members.jsonl` | `member_id`; and the *grouping* of `name_variants` under one identity | added |
| `reference/ministries.jsonl` | `canonical_name`, the individual `name_variants` spellings | source record |
| `reference/ministries.jsonl` | `ministry_id`, `former_names`; and the *grouping* | added |
| `reference/sessions.jsonl` | `number`, `term`, `house`, `sitting_days`, `start_date`, `end_date` | source record |
| `reference/sessions.jsonl` | `session_id` | added |
| everything under `aggregates/` and `search/` | — | added |
| `coverage.jsonl` | — | added |

The distinction that recurs is **spelling versus grouping**: each name variant
is the source's text, while the claim that several variants are one person or
one ministry is this project's work. The same holds for `former_names`, where
the names are the source's and the assertion that they are the same ministry is
a maintainer's.

A single published row therefore mixes both layers. That is in the nature of a
resolved-metadata layer, and saying so plainly is better than a single licence
header that would overclaim.

## What is deliberately absent

No document-derived content is published — nothing extracted from a PDF or any
other document file (FR-015). Debate text and answer text are not here, so
whatever terms attach to them do not arise.

Members' personal attributes are restricted at the ingest boundary to the
published field list (FR-008) and the dataset carries no phone number, personal
email address, postal address, date of birth, marital status or family
composition, whatever the upstream serves.
