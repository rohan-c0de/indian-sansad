# Constitution gate evidence

**Feature**: `specs/001-resolved-metadata-layer` | **T094** | **Date**: 2026-10-10

The Constitution's rule for this file, verbatim:

> A gate is passed by evidence — an executed check and its output — not by assertion.

So every claim below is a command and what it printed. Where a gate's clause
cannot be checked by running something today, it says **UNVERIFIED** or
**PENDING** and names the observation that would settle it. Nothing here is
upgraded to a pass because the rest of the gate passed.

## Verdicts

| Gate | Principle | Verdict |
|---|---|---|
| **Cost** | I | **UNVERIFIED** — no paid service and no overage path anywhere in the configuration used, both executed and documented; but the Pages **serving** clause has never been observed, so the bandwidth tier's real consumption is unmeasured |
| **Upkeep** | II | **PENDING** — not yet observed, needs two unattended scheduled runs |
| **Sources** | III | **PASSED** |
| **Language** | IV | **PASSED** |
| **Member fields** | V | **PASSED**, with one defect recorded in the *check* rather than in the data |

**Three things are unobserved and no gate below treats any of them as settled**:
GitHub Pages serving this site, any **compressed** transfer size, and any
**unattended** (scheduled) run. Two manual runs have happened on GitHub and are
reported as such.

---

# Gate 1 — Cost (Principle I)

**What must be shown**: "Every component named, with the free tier it lands on
and the behaviour at that tier's limit. No paid service, trial, or promotional
credit anywhere."

## Verdict: UNVERIFIED

Clause by clause, because the gate has three and they do not share a verdict:

| Clause | Verdict | Why |
|---|---|---|
| Every component named, with its free tier | **PASSED** | Four components, each on a named tier, every figure quoted from the provider's own published page with the URL and retrieval date — `spike/free-tiers.md` T007, T008, T015 |
| Behaviour at each tier's limit | **PASSED for compute and storage** | Every documented limit is a hard stop, a throttle, a queue or an email. No overage charge applies to the configuration in use |
| No paid service, trial or promotional credit | **PASSED** | Executed below: 20 Python packages, all free and open-source; **no** npm dependency tree at all; no credential, no API key, no account beyond a free GitHub one |
| The storage tier, measured | **PASSED** | 25.9% of the 1 GiB Pages ceiling, executed below |
| **The bandwidth tier, measured** | **UNVERIFIED** | **GitHub Pages has never been observed serving this site.** Every transfer figure below is RAW bytes measured over loopback. The real figure depends on `Content-Encoding`, which is readable only from the live site's response headers |

## The four components and their tiers

| Component | Free tier | Documented behaviour at the limit | Overage charge? |
|---|---|---|---|
| **Scheduled compute** — the refresh | GitHub Actions, **public** repository, standard GitHub-hosted runners. *"GitHub Actions usage is free … for public repositories that use standard GitHub-hosted runners"* — no monthly minute allowance applies, because usage is **not metered** | Job duration 6 h: *"the job is terminated and fails."* Workflow run 35 days: *"the workflow run is cancelled."* Concurrency 20: jobs queue | **No** |
| **Static hosting** — the dataset and the page | GitHub Pages, same repository. 1 GB site, 100 GB/month **soft** bandwidth, 10 builds/hour **soft**, 100 MiB maximum single file | *"If your site exceeds these usage quotas, we may not be able to serve your site, or you may receive a polite email from GitHub Support"* | **No** |
| **Source data** | The Lok Sabha's own JSON routes. No credential, no API key, no quota published | No published rate limit; the pipeline is one sequential pass | **No** |
| **Everything the pipeline runs on** | Python 3.13 plus two runtime libraries, both free and open-source | n/a | **No** |

**One exposure, recorded rather than glossed** (`spike/free-tiers.md` T008):
public-repository Actions usage is unmetered, but **private**-repository usage
is metered and *does* charge above quota when a payment method is on file. This
project is safe because the repository is public — not because the account is
configured safely. **"Keep the repository public" is therefore a cost
constraint here, not a publishing preference.**

## Executed: no paid service, no dependency that could become one

```
$ ls package.json node_modules
ls: node_modules: No such file or directory
ls: package.json: No such file or directory
```

The page has **no build step and no npm dependency tree**, and the browser
driver behind `make test-page` is `tools/cdp.mjs` plus `tools/drive_page.mjs`
over Node's built-in WebSocket and fetch — no Puppeteer, no Playwright, no
registry in the loop.

```
$ .venv/bin/python -m pip list --format=freeze
anyio==4.15.1          httpx==0.28.1        pluggy==1.6.0      ruff==0.17.0
certifi==2026.7.22     idna==3.20           polars==1.44.2     sansad==0.1.0
h11==0.16.0            iniconfig==2.3.1     polars-runtime-32==1.44.2
httpcore==1.0.9        packaging==26.3      Pygments==2.21.0   typing_extensions==4.16.0
                       pathspec==1.1.1      pytest==8.4.2      yamllint==1.38.0
                       pip==26.2.1          PyYAML==6.0.3
```

Two of these are runtime dependencies (`httpx`, `polars`); the rest are the
test and lint toolchain or their transitive requirements. The approximate
matcher is the standard library's `difflib`, deliberately — a recorded
departure in `pyproject.toml`, not an omission.

## Executed: the storage tier, measured against the published ceiling

```
$ .venv/bin/python -c '...sum of every file under data/published/...'
files                : 1,792
total bytes          : 278,370,499 B = 265.5 MiB = 0.2593 GiB
% of 1 GiB ceiling   : 25.9%
largest single file  : aggregates/subject-trends.jsonl = 13,178,975 B (12.6% of the 100 MiB per-file block)
```

**Fits, with 3.9× headroom on the site ceiling and 8× on the per-file block.**

**One clause of T015 is UNVERIFIED against an unpublished limit, and stays
so.** GitHub publishes **no file-count ceiling** for a Pages site, and this
dataset publishes 1,792 files — one per ministry and one per member, in both
formats. "Almost certainly fine" is not the evidence this gate asks for. The
remedy is named in advance per Principle I: if the file count proves a problem,
**drop the per-member axis** and let consumers filter the session partitions.
Never buy hosting.

## Executed on GitHub: what the two manual runs establish

Owner-observed, not reproducible from this machine:

| | |
|---|---|
| **Run #1** (manual) | **FAILED at `verify-joins`** — the runner had no `.venv`. Fixed in the workflow. |
| **Run #2** (manual, 2026-10-10) | **GREEN in 55m 0s.** `verify-joins` passed on the runner. |
| **The publish step** | **Proven.** The `published` branch exists, one commit deep — *"Published dataset 2026-10-10T19:12:01Z"* — carrying `index.html`, `app.js`, `style.css`, `lib/`, `data/published/`, `LICENSE`, `DATA-LICENSE.md` and `.nojekyll`. |
| **Run #3** | From `main` with Phase 7 in it. **In progress.** Run #2 was built *before* Phase 7. |

**55m 0s against the 6-hour job ceiling is 15.3%** — the first end-to-end
timing taken on the runner rather than on a laptop, and it is close to the
52m 38s measured locally on 2026-10-10. The 6-hour limit is a hard stop with no
charge, so a run that outgrew it would fail loudly rather than bill.

## What the Cost gate does NOT establish

- **Pages serving.** Not observed. The site has never been fetched over HTTPS
  from GitHub, so **no bandwidth has been measured at all** and the behaviour
  at the 100 GB soft limit is documented, not demonstrated.
- **Any compressed transfer size.** Every figure in this project is RAW. The
  arithmetic below is therefore an upper bound on transfers and a lower bound
  on visitors, and it is **not** a measurement of what Pages would send:

  ```
  $ 100 GB / the T090 wire figures
  cold page load, no search                           518,565 B ->   192,839 per month
  cold load + first search (one word, 1 digest)     4,112,854 B ->    24,314 per month
  cold load + first use of the state view             952,488 B ->   104,988 per month
  cold load + state view + one member opened        1,034,403 B ->    96,674 per month
  ```

  Those four figures are from `spike/size-budget.md` → T090, measured in a real
  browser over a loopback static host. **`gzip -6` locally gives 87,781 B for the
  518,565 B cold load — −83.1% — and that number is an assumption**: the encoder, the
  level, and whether a given file is compressed at all are all decided by
  Pages, and none of it has been seen.
- **The file-count ceiling**, as above: unpublished by the provider, so
  unverifiable rather than cleared.
- **The 60-day inactivity rule.** Quoted from GitHub's documentation, never
  observed. The keep-alive commit to `main` exists to defeat it and has never
  been tested against 60 days of silence.

---

# Gate 2 — Upkeep (Principle II)

**What must be shown**: "The recurring manual work this change adds, in hours
per week, and the project total after it. Automated detection and processing of
new material. Quiet degradation for visitors plus a signal to the maintainer."

## Verdict: PENDING — not yet observed, needs two unattended scheduled runs

**This is T095, and T095 is deliberately not done.** The owner chose not to wait
for two unattended scheduled runs. No figure is estimated in its place and no
estimate below is promoted to an observation.

## What IS measured: the hand-correction cost (T013)

From `spike/resolution-rate.md`. The maintainer performed and timed the
corrections; this is not an estimate.

| Figure | Measured | Against Principle II's ~120 min/week |
|---|---|---|
| Median per correction | **3 minutes** | — |
| Maximum per correction | **7 minutes** | — |
| Corrections timed | **6** (not the 20 T013 asks for — only 6 existed) | — |
| **First-pass total**, window, after the containment tier | **25 forms × 3 min = 75 min = 1.2 h**, one time | 63% of one week's budget, **once** |
| First-pass total, window, matcher unchanged | 44 forms × 3 min = 132 min = 2.2 h | would have **exceeded** it for that week |
| **Steady state**, flat average over the 18th LS span | **0.168 min/week** | **0.14%** |
| Steady state, during the 21.3-week arrival window | 0.846 min/week | 0.71% |
| Steady state, over the 86 weeks since | **0.000 min/week** | 0% |
| What was actually spent | **four owner-confirmed assertions × 3 min = 12 minutes** | 10% of one week, once |

**Project total**: this feature is the whole project, so the total is the same
figure — **a one-time 12 minutes already spent, plus a steady-state rate that
has been zero for 86 consecutive weeks on the only term where it was measured.**

## What is NOT measured, and why the verdict is PENDING not PASSED

1. **No unattended run has happened.** Every run so far was triggered by hand.
   Until the schedule fires on its own, the upkeep of *operating* this thing is
   unobserved — which is the half of Principle II that matters, because the
   principle is about work that recurs.
2. **Breakage upkeep is not in any figure above.** `plan.md` Risk 6 expects most
   of the budget to go on upstream breakage, and the upstream carries no
   contract, versioning or deprecation notice. T013 measured identity
   corrections only. **The larger half of the budget is unquantified.**
3. **The steady-state rate was never computed for the 17th Lok Sabha** — 64% of
   the window — so no window-wide steady-state figure exists.
4. **Correction timings are n=6 and 18th-LS-only.** The 25 residual forms are
   the harder class (initials, parenthetical aliases, divergent orderings);
   whether they cost 3 minutes each is **UNVERIFIED**, so 1.2 h may be low.

## Executed: the automated half — detection, and the signals

`make validate` scenario 9 (`pytest tests/resilience`) passes: with the upstream
simulated unavailable, shape-changed and truncated in turn, the published record
stays coherent and dated, the maintainer signal fires, and no partial record is
presented as complete.

**But two of the four contract-named maintainer signals are raised by nothing.**
Measured over `src/sansad/**/*.py` on 2026-10-10:

```
$ for each signal factory in sansad.signals.alerts, which modules call it
resolved_transitions_out         -> []
ingestion_failure                -> ['cli.py', 'ingest/questions.py']
upstream_shape_change            -> ['ingest/shape.py']
resolution_rate_below_target     -> []
```

- **`resolved_transitions_out`** — FR-011's "any transition of a question out of
  `resolved`". Detecting it needs the previous snapshot's statuses compared
  against this refresh's; `--previous` exists but is wired to T054's
  last-known-good retention only. **NOT PRESENT**, pinned by
  `tests/unit/test_state_transitions.py::test_nothing_under_src_raises_the_resolved_transition_signal`.
- **`resolution_rate_below_target`** — FR-011's "when resolution quality falls
  below its stated threshold". The factory exists, with both the automatic and
  the published rate distinguished by severity. **No caller anywhere** —
  `src/`, `tools/`, `tests/` or `.github/`. **NOT PRESENT.**

Both are maintainer-facing only, so neither affects FR-010: a visitor sees a
coherent dated record either way. Both are gaps against FR-011, and neither is
in scope for any task in Phase 8.

---

# Gate 3 — Sources (Principle III, FR-015)

**What must be shown**: "Every input identified as an already-structured source.
No document file opened, parsed, or depended on. Facts available only in
documents recorded as gaps."

## Verdict: PASSED

## Every input, identified

| Input | Form | Fetched by the pipeline? |
|---|---|---|
| `/api_ls/member` — the member roster | JSON, `Content-Type: application/json` | **Yes.** `sansad.ingest.members.ROSTER_PATH` |
| `/api_ls/question/qetFilteredQuestionsAns` — question metadata | JSON, `Content-Type: application/json` | **Yes.** `sansad.ingest.shape.QUESTION_ROUTE` |
| `/api_ls/business/getAllLoksabhaAndSession` — the session enumeration | JSON | **No.** Read once in the spike and carried as `sansad.publish.reference.SITTING_DAYS`, with its provenance recorded |
| `/api_ls/question/getMinistry` — the ministry reference names | JSON | **No.** Four reference-only names carried as `REFERENCE_ONLY_MINISTRY_NAMES` so an offline run can report the figure; a run that fetches the set recounts |

**Executed — `src/` declares exactly two upstream paths, and both are JSON
routes:**

```
$ grep -rn '"/api' src/sansad/
src/sansad/ingest/members.py:62:ROSTER_PATH = "/api_ls/member"
src/sansad/ingest/shape.py:49:QUESTION_ROUTE = "/api_ls/question/qetFilteredQuestionsAns"
```

## Executed: no document-parsing or OCR library is referenced anywhere

```
$ grep -riEl "pypdf|pdfminer|pdfplumber|tesseract|pytesseract|ocrmypdf|camelot|tabula|fitz|pymupdf|textract" \
    --include="*.py" --include="*.toml" --include="*.yml" --include="*.json" .
pyproject.toml
tools/guard_no_raw_payloads.py
```

**Both hits are false positives and were read rather than counted**: the
pattern `tabula` matches the word *tabular* in `pyproject.toml`'s comment about
polars ("a tabular/serialisation library") and in the guard's
`is_tabular = relpath.endswith((".csv", ".tsv"))`. No PDF, OCR or
document-extraction library is present, and `pip list` above confirms none is
installed.

## Executed: the four document pointers are never followed

The question route serves four document-pointer fields —
`questionsFilePath`, `questionsFilePathHindi`, `questionsDocPath`,
`questionsDocPathHindi` — plus three text fields. They appear in exactly one
place in the codebase:

```
$ grep -rn "questionsFilePath\|questionsDocPath" src/ tools/ web/
src/sansad/ingest/shape.py:75:        "questionsFilePath",
src/sansad/ingest/shape.py:76:        "questionsFilePathHindi",
src/sansad/ingest/shape.py:77:        "questionsDocPath",
src/sansad/ingest/shape.py:78:        "questionsDocPathHindi",
```

That is `QUESTION_ROUTE_FIELDS`, the **shape baseline** — the recorded
field-name set the upstream is diffed against, so that a pointer *disappearing*
is still an upstream change the maintainer hears about. It is the set the
allowlist excludes from publication, not a set anything opens. Nothing reads a
value from these keys, and no HTTP client is given one.

```
$ grep -rl "questionsFilePath\|questionsDocPath\|questionText\|answerText" data/published/
data/published/coverage.csv
data/published/coverage.jsonl
```

**Those two hits are the gap declaration, which is what this gate requires.**
The Coverage Statement's `known_gaps` reads:

> `question-and-answer-text`: absent for every record in every session.
> `questionText` and `answerText` are null on the route and the text sits behind
> document pointers, which Principle III forbids opening.

No published **question row** carries any of them:

```
$ fields present on a published question row
['asking_members', 'date', 'house', 'last_refreshed', 'ministry_id',
 'question_id', 'resolution_status', 'session', 'source_record_ref',
 'subject', 'type']
```

and `tests/contract/test_published_dataset.py::test_guarantee_9_nothing_in_the_dataset_comes_from_a_document_file`
asserts structurally that no published field name could hold such content — the
strongest form of "never followed" is a row with nowhere to put the result.

## Facts available only in documents, recorded as gaps

Five entries in the Coverage Statement's `known_gaps`, executed via
`make coverage`. The first is the Principle III gap; the other four are
coverage anomalies and a duplicate record, all causes **UNVERIFIED** and all
declared rather than smoothed:

```
- question-and-answer-text: absent for every record in every session. ...
- lok-sabha/18/1: 7 sitting days recorded and ZERO questions served. Cause UNVERIFIED.
- lok-sabha/18/8: ZERO sitting days recorded and 4,500 questions served. ... Cause UNVERIFIED.
- lok-sabha/17/13: 4 sitting days recorded and ZERO questions served. Cause UNVERIFIED.
- upstream-duplicate-record: lok-sabha/17/4/unstarred/2204 was served more than
  once by the upstream; identical copies were reduced to one and this is the
  declaration (FR-013).
```

Session and term **periods** are a second declared gap of the same kind:
`start_date` and `end_date` stay `NOT_STATED` unless the enumeration supplies
them, and are explicitly **not** derived from the dates of the questions inside
a session — that would publish a fact about questions as a fact about when the
House sat.

---

# Gate 4 — Language (Principle IV)

**What must be shown**: "All ingested and published material is English. No
translation or transliteration path introduced."

## Verdict: PASSED

## Executed: no non-Latin script anywhere in the published dataset

Every `.jsonl` file plus the search index — 907 files — scanned codepoint by
codepoint:

```
files scanned: 907
lines containing a Devanagari codepoint : 0
lines containing any non-ASCII codepoint: 2894
```

**Zero Devanagari.** The 2,894 non-ASCII lines were enumerated rather than
assumed, and every distinct codepoint in the published dataset is punctuation
or a Latin diacritic:

```
'’'  U+2019  RIGHT SINGLE QUOTATION MARK       x1,967
'–'  U+2013  EN DASH                           x724
'‘'  U+2018  LEFT SINGLE QUOTATION MARK        x453
'”'  U+201D  RIGHT DOUBLE QUOTATION MARK       x79
'“'  U+201C  LEFT DOUBLE QUOTATION MARK        x62
'‑'  U+2011  NON-BREAKING HYPHEN               x51
' '  U+00A0  NO-BREAK SPACE                    x35
'ñ'  U+00F1  LATIN SMALL LETTER N WITH TILDE   x23
'è'  U+00E8  LATIN SMALL LETTER E WITH GRAVE   x16
' '  U+202F  NARROW NO-BREAK SPACE             x14
'—'  U+2014  EM DASH                           x13
'é'  U+00E9  LATIN SMALL LETTER E WITH ACUTE   x6
'⁠'  U+2060  WORD JOINER                       x5
```

Each is reproduced **as the source wrote it**, which Principle IV requires:
"Preserving a source name form exactly as written is not translation and remains
required for provenance."

## Executed: the three Hindi-sourced fields are published nowhere

```
$ grep -rl "answerTextHindi\|questionsFilePathHindi\|questionsDocPathHindi" data/published/ web/
(no output)
```

A wider search for the word `Hindi` under `data/published/` **does** return
files, and the cause was checked rather than assumed:

```
44 record(s); every hit is in the `subject` field
   lok-sabha/17/1/unstarred/386    -- Hindi Teaching Institutions
   lok-sabha/17/10/unstarred/479   -- Legal Education in Hindi and other Regional Languages
   lok-sabha/17/11/starred/257     -- Legal Education in Hindi and Regional Languages
   lok-sabha/17/1/unstarred/4070   -- Filing of Petition in Hindi
```

**44 English subject lines about Hindi**, not Hindi content. The three Hindi
fields the route serves are in the shape baseline and excluded from
publication, exactly as the document pointers are.

## Executed: no translation or transliteration path

```
$ grep -riEl "translat|transliterat|indic-nlp|bhashini|googletrans|deep-translator|unidecode" \
    src/ tools/ web/ tests/ pyproject.toml
src/sansad/resolve/normalise.py
src/sansad/publish/formats.py
```

**Both hits are prose forbidding the thing**, read rather than counted:

```
src/sansad/publish/formats.py:187:  as written (Principle IV: no transliteration), and escaping them to ASCII
src/sansad/resolve/normalise.py:32:  2. **This is not transliteration** (Principle IV). No script conversion, no
src/sansad/resolve/normalise.py:36:     observed case to transliterate even if the principle allowed it.
```

No translation or transliteration library is installed (`pip list` above) or
referenced. Name normalisation folds case, punctuation and token order; it
converts no script.

---

# Gate 5 — Member fields (Principle V, FR-008)

**What must be shown**: "The published field list diffed against the FR-008 set.
Dataset files, pages, derived statistics and repository fixtures all checked. Any
attribute outside the set accompanied by its recorded decision." And, before
publishing: "the Member fields gate MUST be re-run against what will actually be
published, not against what was specified."

## Verdict: PASSED, with one defect recorded in the *check* rather than in the data

## Executed: the three scopes, scanned for every prohibited spelling

```
$ make audit-fields
audit-fields: the three scopes of quickstart.md scenario 10
  repository root: /Users/rohanupalekar/claudecode/indian-sansad

  [PASS] data/published/ -- 1792 file(s) scanned, size ceiling NOT applied (published files are legitimately large)
  [PASS] web/ -- 12 file(s) scanned, size ceiling 65536 B
  [PASS] tests/ -- 42 file(s) scanned, size ceiling 65536 B

audit-fields: PASS -- all 3 scope(s) audited, no prohibited attribute, no oversized payload

$ make guard
guard: PASS -- 1988 file(s) scanned under /Users/rohanupalekar/claudecode/indian-sansad;
no prohibited attribute, no payload over 65536 bytes
```

The prohibited set is `PROHIBITED_ATTRIBUTES` in
`tools/guard_no_raw_payloads.py`: personal phone, Delhi phone, email, present
address, permanent address, date of birth, marital status, and number of sons
and daughters — each with every spelling the upstream or a careless transform
might use. **Not one appears in any of the three scopes.**

## Executed: the full field diff, set by set, against the FR-008 allowlist

Every field name in every published file — the union over **all** records, not
a sample, descending into nested objects and arrays, plus each CSV header —
diffed against `sansad.model.member.PUBLISHED_FIELDS`, which is FR-008 in
machine-readable form:

```
FR-008 set (sansad.model.member.PUBLISHED_FIELDS):
  canonical_name, constituency, house, last_refreshed, member_id,
  name_variants, party, sitting_status, source_record_ref, state, terms
```

| Published set | Fields | Member attributes present | Outside FR-008? |
|---|---|---|---|
| `by-session` | 11 | `house`†, `last_refreshed`†, `source_record_ref`† | none |
| `by-ministry` | 11 | same | none |
| `by-member` | 11 | same | none |
| `reference` | 36 | `member_id`, `canonical_name`, `name_variants`, `house`, `party`, `state`, `constituency`, `terms` (+ `terms.party`, `terms.house`, `terms.state`, `terms.constituency`), `sitting_status`, `source_record_ref`, `last_refreshed`, `representations.member_id`, `representations.party`, `representations.sitting_status`, **`representations.member_name`** | none — see the defect below |
| `aggregates` | 24 | `state` | none |
| `search/asker-names` | 4 | `member_id`, `canonical_name`, `party`, `state` — and nothing else | none |
| `search` (subject index) | 6 | `terms`‡ | none |
| `search/digest` | 6 | (none) | none |
| `coverage` | 39 | `house`†, `last_refreshed`† | none |
| `resolution-records` | 7 | `member_id`, `source_record_ref` | none |
| `manifest.json` | 50 | `last_refreshed`† | none |

**The two aggregates T094 names explicitly:**

- **`aggregates/state-subjects`** (new, 2026-10-10) publishes
  `state`, `subject`, `questions`, `state_questions`, `state_subjects`,
  `subjects_shown`, `counting_basis_unit`, `basis_version`. **One member
  attribute — `state` — and no member name, no member id.** A state's subject
  summary names no person.
- **`reference/constituencies` → `representations`** carries `member_id`,
  `term_number`, `start_date`, `end_date`, `member_name`, `party` and
  `sitting_status`. **Three of those are copies of FR-008 member fields**,
  declared as such in `contracts/published-dataset.md`, and pinned to
  `reference/members.jsonl` by `tests/contract/test_constituency_reference.py`
  so the copy cannot drift from the original. `term_number`, `start_date` and
  `end_date` are facts about a representation, not attributes of a person.

### The defect: `representations.member_name` is a name form the allowlist cannot see

† and ‡ mark **key-name collisions** the diff cannot resolve on its own, and
one real finding:

- **†** `house`, `last_refreshed` and `source_record_ref` on a *question* row
  are question-level fields that happen to share a key spelling with Member
  fields. Not member attributes. Harmless.
- **‡** `terms` in `search/subject-index.json` is the index's **tokenised
  subject words**, which collides with Member's `terms` (terms served). Not a
  member attribute. Harmless.
- **The finding**: `representations.member_name` **is** a member name form —
  inside FR-008's "name forms" and declared in the contract — but the spelling
  `member_name` is not in `PUBLISHED_FIELDS`, which carries `canonical_name`
  and `name_variants`. So **the automated diff classifies a genuine FR-008
  field as "not a member attribute"**, and its membership of the set rests on a
  human reading the contract. The data is correct; the check is weaker than it
  looks. **Remedy, not applied here because it is outside Phase 8's scope**:
  either rename the published key to `canonical_name`, or give
  `PUBLISHED_FIELDS` a declared synonym for the constituency set so the diff
  can confirm it mechanically. Recorded now rather than left for the next
  person to re-derive.

## The page (`web/`), and why its attribute surface is bounded

Principle V's "published" covers "any interactive page". The page can only
render what it fetches, and what it fetches is enumerated by `make test-page`'s
network log — every request of a full run, with the upstream blocked at the
network level:

```
load  /  /style.css  /app.js  /lib/{chart,fetch,constituency,profile,search,licence,coverage,format,tokenise}.js
load  /data/published/coverage.jsonl
load  /data/published/reference/sessions.jsonl
load  /data/published/aggregates/counting-basis.jsonl
load  /data/published/manifest.json
load  /data/published/aggregates/ministry-profile.jsonl
load  /data/published/reference/ministries.jsonl
search /data/published/search/subject-index.json
search /data/published/search/asker-names.jsonl
search /data/published/search/digest/lok-sabha-18-8.jsonl
seat   /data/published/reference/constituencies.jsonl
seat   /data/published/aggregates/state-subjects.jsonl
member /data/published/by-member/ls-3928.jsonl
...
[PASS] the network log shows requests to the static host ONLY -- one upstream
       request is a failure -- 67 request(s), all to http://127.0.0.1:58451
```

Every data file there is a set in the census above, so **the page's reachable
attribute set is a subset of the dataset's** — and `web/` is additionally
scanned for every prohibited spelling by `make audit-fields` (12 files, PASS).
The page reaches no attribute the dataset does not publish, because there is no
other origin it can read from.

## Fixtures

```
[PASS] tests/ -- 42 file(s) scanned, size ceiling 65536 B
```

All fixtures are hand-authored by policy (`tests/fixtures/README.md`), every
identity in them fictional, and **no recorded upstream response is committed
anywhere in the tree** — which is the route by which the full personal-data
payload would most likely enter. The 64 KB ceiling is the second guard on that:
a committed raw roster response could not be small.

## Executed before publishing

The Constitution requires this gate to be re-run "against what will actually be
published". The census and both guard runs above were executed against
`data/published/` as built on 2026-10-10 — the tree the publish step copies to
the `published` branch — not against the specification. `make validate`
scenario 10 runs the same audit with `--require-present`, so an **absent**
dataset fails rather than reporting a pass.

---

# What no gate here establishes

Collected in one place so a reader does not have to assemble it from five
sections:

1. **GitHub Pages has never been observed serving this site.** No bandwidth
   figure, no compressed transfer size, no `Content-Encoding`, no live
   first-load measurement. Every byte figure in this project is RAW.
2. **No unattended (scheduled) run has happened.** SC-003 and the operational
   half of FR-009 are **UNVERIFIED**; the Upkeep gate is **PENDING** on exactly
   this, and T095 stays unticked.
3. **The 60-day inactivity rule is documented, not demonstrated.** So is the
   keep-alive that defeats it.
4. **GitHub publishes no file-count ceiling**, and this dataset publishes 1,792
   files. UNVERIFIED against an unpublished limit, with the remedy named.
5. **Breakage upkeep is unquantified** — `plan.md` Risk 6 expects most of
   Principle II's budget to go on it, and no measurement covers it.
6. **Two of the four FR-011 maintainer signals are raised by nothing**:
   `resolved_transitions_out` and `resolution_rate_below_target`. Both are
   maintainer-facing, so FR-010 is unaffected.
7. **Resolution precision is unverified.** Every rate in this project measures
   the *coverage* of matching, not its correctness; no join has been checked
   against the real person.
8. **The source's terms have never been determined.** Principle V bounds what
   is published; it does not establish what may lawfully be published, and the
   Constitution says so itself: "A principle that is silent on a risk has not
   cleared it."
