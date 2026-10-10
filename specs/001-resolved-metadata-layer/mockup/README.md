# Question-explorer mockup — the Phase 6 visual target

Static HTML and CSS. No JavaScript, no framework, no build step, no web font,
no request to any host.

## Purpose

This is a **visual target for Phase 6** (User Story 2 — ministry question load
and prior occurrences of a subject). It is **not** the page, and it is **not**
task T074. Nothing here is loaded, imported or copied by anything that ships;
`web/` is untouched and still reports `[EMPTY]` under `make audit-fields`,
which is the correct state until a real page exists there.

It exists so the layout, the flag treatment, the counting-basis placement and
the responsive behaviour can be argued about before any page code is written —
and so the questions in the last section get answered against the real data
model rather than discovered halfway through T078.

## What is real, and what is not

**Real — one block only.** The coverage statement on `index.html`, and the
one-line coverage strip on `search.html`, are read from
**`data/published/coverage.jsonl`**, the row where `house` is `"lok-sabha"`.
That file's `last_refreshed` is **2026-10-10**. The fields used are
`houses_covered`, `period_start`, `period_end`, `sessions_covered_count`,
`total_questions`, `duplicate_records_declared`, `resolution_rate_automatic`,
`resolution_rate_including_assertions`, `assertions_in_effect`,
`sc_002_target` and `last_refreshed`. An HTML comment above each block says so
on the page itself.

**Placeholder — everything else.** Every other figure on both pages is
made up: `Sample Ministry A`/`B`, 1,234 questions, the 12.2% starred share, the
54 not-fully-linked, the four session rows, the bar chart, the comparison
column, the 14 search hits. Session dates are the literal string
`[dd Mon yyyy – dd Mon yyyy]` because the published record does not have them
(see assumption 5). Every page carries a banner saying this.

**No real person appears anywhere** (Constitution Principle V). Members are
`Member A`, `Member B`, `Member C`; the party is `Party X`; states are
`State Y` and `State Z`. The only member attribute classes shown are name
form, party and state — all inside the FR-008 set.

## How to view it

Open `index.html` in a browser — it needs no server. Or serve the folder:

```
python3 -m http.server -d specs/001-resolved-metadata-layer/mockup 8000
```

**On the no-outside-request check.** `index.html`, `search.html` and
`style.css` contain zero matches for `http`, `@import` or `url(` — verified by
grep. Three matches do exist in **this README**: the serve command just above,
and the two URLs quoted verbatim from `spike/free-tiers.md` in assumption 6.
All three are documentation text. No page in this folder references any other
file, any font service, any CDN or any host.

`screens/` holds full-page renders at 1280 px and 390 px, captured with the
locally installed Chrome.

## Out of scope here

- **State and constituency entry** — that is User Story 3 and Phase 7 (T086–T090),
  not this view.
- **Rajya Sabha** — not covered by the dataset at all; the coverage block says so.
- **Dark mode** — one light theme only.

---

# Assumptions the mockup makes that the build must confirm

Each was checked against `spec.md`, `data-model.md`,
`contracts/published-dataset.md`, the `spike/*.md` records and the real files
under `data/published/`.

## 1. Match grading — **OPEN**

The result cards show two grades, `Near-identical` and `Similar`. That assumes
the T071 subject index can **grade** a match, not merely return it.

Nothing measured supports grading yet. `spike/index_sample.py` — the T018
prototype whose tokenisation and scope T071 is told to adopt — builds a plain
inverted index: term → **delta-encoded ascending doc ids**. It stores no score,
no term weight and no similarity metric, and `spike/size-budget.md` records its
tokeniser as "lowercased, split on non-alphanumeric, minimum token length 3,
36 stopwords, **no stemming**". T079 asks only for "prior occurrences of a
subject listed with dates, ministries and asking members". "Near-identical"
appears in `spec.md` and in Phase 6's Independent Test as a description of what
should come back — never as a label a reader sees, and never as one of two
named tiers.

So the index as measured can rank by how many query terms a subject matched,
but the **two-grade labelling in this mockup is not yet specified or measured**.
Either T071 must publish something a grade can be computed from, or the page
drops the badges and shows a ranked list.

## 2. Per-session resolution-status counts — **OPEN**

The table's `Partly linked` and `Not linked` columns, the per-session flag
chips and the flagged stat card all need per-session counts of how completely
each question was linked to a member, for one ministry.

**The distinction is real and is already derivable from the published record.**
`by-session/*.jsonl` and `by-ministry/*.jsonl` carry both `resolution_status`
and `asking_members` per question, and `src/sansad/resolve/__init__.py`
(`status_for_question`) sets a co-asked question to `unresolved` while
**keeping the askers that did resolve** — so "partly linked" is
`resolution_status != "resolved" AND asking_members is non-empty`, and
"not linked" is `resolution_status != "resolved" AND asking_members is empty`.
`src/sansad/cli.py` already computes exactly that pair window-wide, and
`aggregates/counting-basis.jsonl` publishes the result in words: 3,472
unresolved, "Of those, 1,231 are PARTLY resolved". Counted directly off one
real partition, `by-ministry/agriculture-and-farmers-welfare.jsonl` gives
4,645 resolved, 59 partly linked and 120 not linked.

**What is open is whether the aggregate carries it.** T070's current wording,
quoted exactly from `tasks.md`:

> - [ ] T070 [US2] Implement `src/sansad/views/ministry_profile.py`: precomputed per-ministry × per-session question counts and question-type mix, each carrying its T064 counting basis, written to `data/published/aggregates/` — precomputed rather than browser-computed because `research.md` records that fetching ~10^5 records into a page is not viable

**It does not cover this.** "question counts and question-type mix" names the
starred/unstarred split and nothing about resolution status. T078 separately
requires that "unresolved and ambiguous questions [are] visibly flagged rather
than filtered out of the counts", and T073 tests only that "the profile's
totals match a direct count of the published question records" — neither
obliges the aggregate to carry the split, so as written the page would have to
re-derive it in the browser from the by-ministry partition. That is affordable
(T019 budgets 842,496 B for exactly that file) but it leaves the flag counts
outside the T064 counting-basis stamp and outside T073's contract test, which
is the one place a wrong flag count would be caught.

**Proposed amendment to T070** (proposal only — `tasks.md` is not edited by
this mockup):

> - [ ] T070 [US2] Implement `src/sansad/views/ministry_profile.py`: precomputed per-ministry × per-session question counts, question-type mix, **and resolution-status counts split three ways — fully linked, partly linked (at least one asking member identified and at least one not) and not linked (none identified)** — each carrying its T064 counting basis, written to `data/published/aggregates/` — precomputed rather than browser-computed because `research.md` records that fetching ~10^5 records into a page is not viable. **The three resolution-status counts MUST sum to the question count for that ministry and session**, because T078 requires unresolved and ambiguous questions to be visibly flagged rather than filtered out of the counts (FR-004, FR-012), and an aggregate that carries the total but not the split forces the page to re-derive the flags outside the T064 basis stamp and outside T073's contract test.

## 3. `former_names` on the ministry reference set — **CONFIRMED for the name, OPEN for the date**

The result line reads: *Formerly "Sample Former Name" (renamed [date])*.

**The name half is confirmed.** `former_names` is a published field — it is in
`PUBLISHED_FIELDS` in `src/sansad/model/ministry.py` and in every row of
`data/published/reference/ministries.jsonl`. 7 of 56 ministries carry one, and
they include genuine renames, not only spelling merges: `HUMAN RESOURCE
DEVELOPMENT` → `EDUCATION`, `SHIPPING` → `PORTS, SHIPPING AND WATERWAYS`,
`HEAVY INDUSTRIES AND PUBLIC ENTERPRISES` → `HEAVY INDUSTRIES`, alongside
normalisation merges such as `COMMUNICATION` → `COMMUNICATIONS`. The claim
that questions under both names are counted together is also sound: the
rename keeps the **older** `ministry_id`, so one partition holds both.

**The date half is not.** The published ministry record has exactly four
fields — `ministry_id`, `canonical_name`, `name_variants`, `former_names` —
and **none of them is a date**. `MinistryRename` in
`src/sansad/resolve/assertions.py` carries `confirmed_on`, but that is the date
the **owner confirmed the mapping**, it lives in `data/assertions/ministries.json`
which is not published, and it is not the date the ministry was renamed
upstream. There is no source for a rename date in the structured record, and
Principle III forbids going to a document for one. The page must therefore
either drop "(renamed [date])" or render it "renamed on a date the record does
not state" — the same treatment assumption 5 needs.

A second caveat the mockup hides: `src/sansad/model/ministry.py` states that
until a rename is mapped, "one ministry's question history is split across two
ids", and the coverage statement currently reports
`ministry_names_without_confirmed_mapping: 56`. A profile can under-report
itself, and the page should surface that count rather than imply the merge is
always complete.

## 4. The source-record line — **CONFIRMED, with the exact field named**

The cards show `Source record: lok-sabha/17/8/unstarred/[no.]`, assuming it
follows the question id's composite of House, term, session, type and number.

Checked against the real published records in `data/published/by-session/*.jsonl`.
The fields are:

`question_id`, `house`, `session`, `date`, `type`, `subject`, `ministry_id`,
`asking_members`, `resolution_status`, `source_record_ref`, `last_refreshed`

A real record reads `"question_id": "lok-sabha/17/1/starred/500"` — so the id
is exactly that composite, with the **type lower-cased inside the id** while
the separate `type` field is upper-case (`"STARRED"`). The page would read
**`question_id`** for this line.

There is also a distinct **`source_record_ref`** field, which on real data is
`"/api_ls/question/qetFilteredQuestionsAns#lok-sabha/17/1/starred/500"` — the
upstream route plus the id. FR-005 asks for "an identifier for the source
record it came from", so a page that wants to show provenance rather than a
local key should show `source_record_ref`, or both. The mockup shows the
`question_id` form; which of the two the real page shows is a decision T079
should make explicitly rather than inherit from this layout.

## 5. Session dates are "not stated" — **CONFIRMED, and it is the rule, not the edge case**

The mockup leaves every Dates cell as the literal `[dd Mon yyyy – dd Mon yyyy]`
on the assumption that a session's dates may be unavailable and must never be
guessed.

The real position is worse than the assumption. In
`data/published/reference/sessions.jsonl`, **all 21 sessions** have
`"start_date": "not stated"` and `"end_date": null`. Not one session in the
published record has a date range. So a "not stated" display is not an edge
case to handle — it is the **only** state the Dates column can currently be in,
and a layout that reserves a wide column for it is spending space on nothing.

Two things follow for the build. First, the page needs a real "not stated"
rendering, visibly different from an empty cell, and it must never substitute
a guess. Second, per-**question** dates *are* present and real (`"date":
"2019-07-26"`), so a session's span could be shown as the **observed first and
last question date** for that session — but that is a derivation with its own
counting basis, not the session's actual sitting dates, and it must be labelled
as such under FR-012 if it is used at all. Related and already declared in the
coverage statement's `known_gaps`: `lok-sabha/18/8` has **zero** sitting days
recorded against 4,500 questions, so any per-sitting-day rate divides by zero.

## 6. Where the published files actually live — **OPEN, and two repo artifacts contradict each other**

The page is specified to read from `data/published/` (T076: "reads **only**
same-origin published files under `data/published/`").

`spike/free-tiers.md` T015 asserts this live layout:

```
https://rohan-c0de.github.io/indian-sansad/            -> web/index.html
https://rohan-c0de.github.io/indian-sansad/data/...    -> data/published/...
```

`.github/workflows/refresh.yml` publishes something different. Its "Publish to
the rolling orphan branch" step does:

```
find . -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
cp -R "${GITHUB_WORKSPACE}/data/published/." .
```

So the contents of `data/published/` land at the **root** of the `published`
branch, and **nothing from `web/` is copied at all**. Against the workflow as
written, the coverage statement would be served at `/coverage.jsonl`, not at
`/data/published/coverage.jsonl`; `/data/...` would 404; and there would be no
page at `/` to do the fetching. Both halves of T015's asserted layout are
wrong against it.

These two records disagree and neither is authoritative over the other. The
mismatch has not yet been observed in production — T058 is ticked as "written,
statically checked, **NOT yet run on GitHub**" — so this is a contradiction
between artifacts, not a reproduced failure.

**What must change, for the two to line up.** One of:

- **(a) The workflow.** Copy the page to the branch root and the dataset under
  `data/published/`, replacing the single `cp -R` with a copy of `web/.` to `.`
  plus `data/published/.` to `data/published/`. This keeps T076's path wording,
  the contract and the consumer documentation untouched, and makes the live
  layout match what T015 already claims. It does change the layout a consumer
  of the `published` branch sees today, so the breaking-change note in
  `contracts/published-dataset.md` applies.
- **(b) The paths.** Keep the workflow and have the page fetch from `./`, which
  contradicts T076 as written and would need T076 amended.

**(a) is the smaller change** — it touches one workflow step rather than a
requirement — but the choice is the owner's, not this mockup's.

**Which task should own it: T081.** It is open, and its own wording —
"serve `web/` and `data/published/` from one local static host on one origin,
**as the T015 host does**" — cannot be completed correctly until it is settled
which layout the T015 host actually has. T058 owns the workflow file but is
already ticked and has never run, so it will not catch this on its own; T082's
network-log assertion is what would catch any layout mismatch that survives.
