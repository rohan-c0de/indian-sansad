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
so none is missed.** A row marked **DONE** is done; the rest are not. The count
is deliberately not stated — it moved twice in two days.

| Where | What changes |
|---|---|
| `DATA-LICENSE.md` — the attribution line above | the canonical link becomes the site, or names both |
| `README.md` | carries one URL today — the corrections link in *Source terms: not determined* — and **no site link at all**; wants the site link, at least in the Licence section |
| `contracts/published-dataset.md` → "Where it is published" | says paths resolve "relative to wherever the branch is served"; can name the origin |
| `spike/free-tiers.md` lines ~258-259 | `https://rohan-c0de.github.io/indian-sansad/...` is written there as a **prediction**; T015's verdict is "VERIFIED by construction, not by execution" and becomes observed |
| `spike/free-tiers.md` line ~287 | records that the URL is derived from the maintainer's handle — the live Attribution deviation; the decision to transfer to an organisation would change the URL again |
| `specs/001-resolved-metadata-layer/mockup/README.md` lines ~224-225 | the same predicted URLs |
| `data/published/coverage.jsonl`/`.csv` and `manifest.json` | **DONE 2026-10-10.** Both now carry `license`, `attribution`, `project_url`, `license_file` and `license_scope` — and, since the source-terms decision of the same date, `source_terms` and `corrections_url` — so a consumer who takes a single file has the terms, the gap in them, the link and the corrections channel in hand. **The update site is now one module — `src/sansad/publish/attribution.py`** — which both writers spread and which `tests/contract/test_attribution.py` asserts is character-for-character the attribution line above, so the file and the data cannot drift. Changing the URL means changing that module; the published files follow on the next refresh. Cost: **+2,549 bytes**, 0.001% of the dataset; the two source-terms fields added **+1,155 bytes** more (manifest +281, `coverage.jsonl` +369, `coverage.csv` +505), **0.000414%** of the 278,684,386-byte dataset, measured by re-emitting the three files without them |
| `src/sansad/publish/attribution.py` — `SOURCE_TERMS` and `CORRECTIONS_URL` | **NOT DONE, and easy to miss.** Both are built from `PROJECT_URL`: `corrections_url` is `{PROJECT_URL}/issues`, so a Pages URL or a transfer to an organisation **moves the corrections channel a rightsholder is told to use**. Re-check both when the URL changes — the issue tracker may well stay on the repository while the canonical link becomes the site, which is a decision rather than a find-and-replace. `source_terms` names `DATA-LICENSE.md` by filename, which the refresh workflow copies to the branch root, so that half holds as long as the file keeps its name |
| `web/index.html`, `web/app.js`, `web/lib/licence.js` (T074, T076) | **DONE 2026-10-10.** The footer renders the licence, the attribution, the `source_terms` line and the corrections link, every one of them read from `manifest.json` at runtime rather than typed into the page — so the URL changes in `attribution.py` and the page follows on the next refresh |

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

## Source terms: not determined

**Owner decision 2026-10-10: publish without determining the source's terms,
with this disclosure and a corrections path.** The decision is to publish, not
a finding that publishing is permitted. Nothing below is a legal conclusion in
either direction, and **none of it is legal advice.**

- **What is licensed here is the added work only.** CC BY 4.0 above covers the
  identity resolution, the joins, the ministry identity layer, the aggregates,
  the indexes, the schemas and this prose. **No rights are granted over the
  underlying parliamentary records** — this project does not hold any to grant.
- **The terms the Lok Sabha publishes those records under have never been
  established.** They were excluded from the assessment by owner instruction
  and were never researched; that exclusion is recorded in the five places
  listed in the section above. So the terms are not "permissive", not
  "restrictive", and not "unclear after review" — they are **undetermined**,
  because nobody looked.
- **Check the source's terms yourself before relying on the records.**
  Satisfying CC BY 4.0 is not sufficient for the source layer, and this
  project's silence about those terms is not permission.
- **Corrections and removal requests go through the issue tracker**:
  <https://github.com/rohan-c0de/indian-sansad/issues>. That includes a
  rightsholder who believes material here should not be published, a Member
  whose record is wrong, and anyone who has established what the source's terms
  actually are. It is the only channel: no address is published here, because
  the work is published under a project name rather than a maintainer's name.

The same two statements travel inside the dataset, so a consumer who takes a
single file is told as well: `manifest.json` and every Coverage Statement carry
`source_terms` and `corrections_url`, defined once in
`src/sansad/publish/attribution.py` and asserted against this file by
`tests/contract/test_attribution.py`. The page footer renders both from the
manifest at runtime rather than from anything typed into the page.

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
