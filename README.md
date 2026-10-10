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

## Using the published dataset

This section is for a consumer — someone taking the files rather than building
them. [`contracts/published-dataset.md`](specs/001-resolved-metadata-layer/contracts/published-dataset.md)
is the contract and the authority: it lists every published set, the ten
guarantees, and what this project explicitly does **not** promise. What follows
is the short form, plus the two rules a consumer will get wrong if they are
left in the contract alone.

**Where it is.** The dataset lives on the orphan branch **`published`**, which
every successful refresh force-pushes as a **single commit** — so its history
is one commit deep at all times and you cannot fetch a previous snapshot from
it. Keep your own copy if you need one. The layout on that branch:

```
/                        the reader page
/data/published/...      the dataset
/LICENSE                 the code licence, MIT
/DATA-LICENSE.md         the dataset licence, CC BY 4.0 on the added work
/.nojekyll
```

So a set the contract names `reference/members.jsonl` is fetched at
`/data/published/reference/members.jsonl`. **Start at
`/data/published/manifest.json`**: it carries the rebuild date, the licence and
source-terms fields, and the file and record count of every set, so you can
tell a complete snapshot from a truncated one before parsing anything.

**What it holds.** Questions partitioned three ways — by session, by ministry
and by member; the member, ministry, session and constituency reference sets;
one resolution record per name form encountered; precomputed aggregates;
the subject-search index, per-session search digest and asker-name lookup under
`search/`; and one Coverage Statement per House. Every set is published in both
newline-delimited JSON and CSV — the same records, neither authoritative over
the other — **except the three under `search/`**, which are JSON only and
carry nothing that is not already published in both formats elsewhere.

**Rule 1 — de-duplicate on `question_id` before totalling anything across
partitions** (guarantee 6). The three question partitions republish the *same*
records under different keys, so a `question_id` appearing in several files is
**one** question, not several. Adding the `by-member` files up gives a larger
number than there are questions, because a question co-asked by 47 members
appears in 47 files. A `question_id` is the composite
`(House, session, type, quesNo)` — **`type` included**, because `quesNo` is
numbered per (session, type) and a starred and an unstarred question in one
session share one. Dropping `type` from the composite collides on 7,431 of the
window's records and merges a starred question with an unstarred one.

**Rule 2 — `resolution_status` is not a filter you can ignore** (guarantee 2).
A question whose asker could not be resolved to one identity is still
published, carrying `resolution_status` of `unresolved` or `ambiguous`.
Filtering on `resolution_status == "resolved"` is an explicit choice to drop
them, not a default: **3,472 questions of the covered window are in that
state**, 1,231 of them *partly* resolved — some askers identified, some not —
so they appear in the identified askers' `by-member` files **and** count as
unresolved. A per-member total and the unresolved total deliberately overlap;
adding them is wrong. The published counting basis in
`aggregates/counting-basis.jsonl` states this beside the figures.

**Breaking changes.** A change is breaking if it **removes a published field,
changes the meaning of `resolution_status`, or reassigns an existing
`member_id`**. Breaking changes are **announced in the Coverage Statement
before they take effect** — so a consumer who reads `coverage.jsonl` on each
fetch gets the notice without watching this repository. Adding a field, adding
a partition, and improving a canonical name are **not** breaking, and will
happen without notice. Two identifiers are promised stable and never reused:
`member_id` and `ministry_id`. Canonical names, party names, ministry names and
constituency names are reproduced as the source records them and may be
revised.

**What is not here.** No server and no query endpoint — filtering happens in
your code or in the page's browser (FR-014, zero running cost). No question or
answer text: it is served only behind document files, which this project never
opens (Principle III). No Rajya Sabha data yet. Read the Coverage Statement as
the authority on which Houses are present rather than assuming both.

**Licence and source terms.** CC BY 4.0 on this project's added work only; the
underlying parliamentary records are **not** covered, and their terms have
never been determined — see the top of this file,
[`DATA-LICENSE.md`](./DATA-LICENSE.md), and the `license`, `attribution`,
`license_scope`, `source_terms` and `corrections_url` fields that travel on
`manifest.json` and every Coverage Statement.

## Current status

**The ticked boxes in [`tasks.md`](specs/001-resolved-metadata-layer/tasks.md) are the count** —
no total is typed here, because the one that was went stale by seven tasks. The pipeline is built,
the dataset is built, all four reader-page views are built, and **the workflow has now run green on
GitHub and published the `published` branch** — by hand, not on its schedule. **GitHub Pages has
not been observed serving the site**, and no unattended run has happened.

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
- **All four reader-page views are built, and the page has been driven in a real browser.**
  The shell, the stylesheet, the fetch layer, the coverage display, the licence and
  source-terms footer, the ministry-profile view (T078), **subject search (T079)**,
  two-ministry comparison (T080), **the state and constituency entry point (T088)**,
  `make serve-local` (T081), `make test-page` (T082), `make report` (T085) and
  `make lookup` (T089) are done. T079's gate was **re-measured against the published search
  digest and passed**, where the earlier attempt through the `by-session` partitions had
  failed it; the figures are in
  [`spike/size-budget.md`](specs/001-resolved-metadata-layer/spike/size-budget.md) → *T079*,
  → *T083* and → *T090*, which is where they stay rather than being retyped here — the last
  two figures quoted in this bullet went stale within a day. The remaining first-load unknown
  is the real **compressed** figure, which can only be read from the live site's response
  headers once Pages is serving the `published` branch.
- **A visitor who knows only where they live can reach their members (SC-008).** Pick a state,
  then a constituency; a seat held by different members across the two covered terms shows
  **both, with their own terms, never merged**, and a constituency name that names a different
  seat in two states shows both with their states rather than picking one. The view fetches
  **nothing on page load** — its two files are read on first use, and one `by-member` file when
  a member is opened. Building it found **three defects already in the published constituency
  reference set**, all fixed in T086 and recorded in
  [`spike/size-budget.md`](specs/001-resolved-metadata-layer/spike/size-budget.md) → *T086*.

### Not done

- **The workflow has run on GitHub, but never on its schedule.** Two manual runs, owner-observed:
  run #1 **failed at `verify-joins`** because the runner had no `.venv` — fixed in the workflow —
  and run #2 (2026-10-10) finished **green in 55m 0s**, with `verify-joins` passing on the runner.
  **The publish step is proven**: the `published` branch exists, one commit deep, *"Published
  dataset 2026-10-10T19:12:01Z"*, carrying `index.html`, `app.js`, `style.css`, `lib/`,
  `data/published/`, `LICENSE`, `DATA-LICENSE.md` and `.nojekyll`. Run #2 was built **before
  Phase 7**; run #3, from `main` with Phase 7 in it, is in progress.
  **Three things are still unobserved**, and none of them follows from the above:
  **GitHub Pages serving the site** (so the real *compressed* first-load figure is still
  unreadable), the **daily schedule firing unattended**, and the **60-day keep-alive**. Until a
  scheduled run happens, FR-009 and SC-003 are UNVERIFIED — see
  [`gate-evidence.md`](specs/001-resolved-metadata-layer/gate-evidence.md).
- **`main` must stay unprotected.** The workflow pushes a keep-alive commit directly to `main` on
  every run, against GitHub's rule that a public repository's scheduled workflows are disabled
  after 60 days without repository activity. Branch protection blocking direct pushes would make
  the job fail every run — **loudly, by design**, rather than leaving the 60-day protection
  silently void. See
  [`spike/free-tiers.md`](specs/001-resolved-metadata-layer/spike/free-tiers.md) →
  *`main` must stay unprotected*.
- **Lok Sabha only.** No Rajya Sabha data is published — see *What is still unknown* below. The
  coverage statement declares this rather than implying both Houses.
- **T095 is deliberately not done, and Phase 9 has not started.** T095 records the *measured*
  upkeep figure after the refresh has run unattended for two cycles; the owner chose not to wait
  for two unattended scheduled runs, so the Upkeep gate carries **PENDING** rather than an
  estimate dressed as a measurement. Phase 9 is the Rajya Sabha route investigation
  (T098–T100), which investigates and stops. **Phases 7 and 8 are otherwise done** — `make
  validate` is implemented (T091) and the gate evidence is written (T094).

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

## Validating this release

```
make validate   # quickstart.md scenarios 1–12, then the full test suite
```

18 checks: the three identity-resolution scenarios, join auditability, all five
FR-007 subset axes, count reproducibility, the constituency entry point,
composition reconciliation, the three upstream-failure modes, the field-scope
audit across all three scopes, coverage honesty, the URL-to-file mapping, the
real page driven in a real browser with every hostname but loopback
unresolvable, and `pytest` over `tests/`. It **refuses to run** against an
unbuilt `data/published/` rather than reporting an absent dataset as a pass,
runs every check even after one fails, and prints the captured output of each
failure. Each scenario is described in
[`quickstart.md`](specs/001-resolved-metadata-layer/quickstart.md).

**What `make validate` does not cover.** Four of the success criteria are
observable only in operation, and a green run is not evidence for any of them:

| | Why a local run cannot show it |
|---|---|
| **SC-003** — newly published material appears with no manual step | Needs a **scheduled** run that nobody started. Every run so far was triggered by hand. |
| **SC-004** — upkeep stays within about 2 hours a week | Needs weeks of operation to measure. The figure that exists is an estimate, not an observation. |
| **SC-005** — running cost stays at zero per month | Needs a billing period to elapse. What is evidenced is that every component sits on a named free tier. |
| **SC-009** — the record is used by at least one person other than the maintainer | Needs another person. No target level has been set for it either. |

`make validate` prints this same list on success, because immediately after a
green run is exactly when the claim is most likely to be overstated. The gate
evidence for all five Constitution principles, including which gates are
**UNVERIFIED** or **PENDING** and why, is in
[`gate-evidence.md`](specs/001-resolved-metadata-layer/gate-evidence.md).

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
spike/             one surviving spike fetcher (fetch_slice.py); not production
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
