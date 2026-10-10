# T060 — User Story 1 validated against the REAL published dataset

**Date**: 2026-10-10
**Dataset**: produced by `make refresh SOURCE=upstream` — a live fetch of the full window,
**52m 38s** wall clock, exit 0. Not the cached window: `manifest.json` records
`"source": "upstream"`.
**Dataset figures**: 95,269 records fetched, 1 declared duplicate, **95,268 published
questions**, 1,759 files, 235,965,570 bytes.
**Scope**: `quickstart.md` scenarios 1, 2, 3, 4, 5, 9, 10, 11.

Every verdict below is backed by output pasted from running it. Where a scenario **cannot** be
run against a successful live publish, that is said plainly and the substitute is named — it is
not recorded as a pass for the thing that was not run.

---

## Verdicts

| Scenario | What it checks | Verdict |
|---|---|---|
| 1 | Identity resolution across name variants (FR-002) | **PASS** |
| 2 | Nothing silently dropped (FR-004, guarantee 2) | **PASS** |
| 3 | Co-asked questions on one record (FR-003) | **PASS** |
| 4 | Every join independently verifiable (FR-005) | **PASS** |
| 5 | Subsets on all five FR-007 axes | **PASS** |
| 9 | Degrade quietly, alert the maintainer (FR-010, FR-011, SC-006) | **PASS by substitution — NOT run against the live publish.** See below. |
| 10 | Field scope bounded (FR-008, SC-010) | **PASS for `data/published/` and `tests/`. NOT a pass for `web/`, which is empty.** |
| 11 | Coverage honesty (FR-013) | **PASS** |

### SC-002 — both rates, both verdicts

| Rate | Figure | Against the 95% target |
|---|---|---|
| **Automatic** (matcher alone, no assertion counted) | 90,298 / 95,268 = **94.78%** | **NOT MET — short by 0.22 points** |
| **Including maintainer assertions** (published) | 91,796 / 95,268 = **96.36%** | **MET — +1.36 points** |

The automatic rate is **below target on live data**, as it was on the cached window. It is
recorded as not met. Only the assisted rate meets SC-002, and it does so on the strength of four
owner-confirmed assertions.

---
## Scenario 1 — identity resolution across name variants (US1, FR-002)

**Run as `quickstart.md` defines it**: `pytest tests/resolution -k variants`
```
.........                                                                [100%]
9 passed, 11 deselected in 0.06s
```

**And re-checked as a property of the live published dataset**, because the pytest run
uses hand-written fixtures by policy (T034) and therefore proves the matcher, not the
published output:
```
-- Scenario 1 (FR-002): one member_id per person across name variants --
   identities reached by MORE THAN ONE written form : 155
   most forms collapsed onto one identity           : ls-4489 <- 2 forms
     ['(Smt.) Kakoli Ghosh Dastidar', 'Dr. Kakoli Ghosh Dastidar']
   member_id unique across the reference set        : True (5426 members)
   canonical names shared by >1 identity, NOT merged: 54

```
**Verdict: PASS.** 155 published identities are reached by more than one written name form, so
variants really are collapsing. `member_id` is unique across all 5,426 members. And the other
half of the scenario holds too: **54 canonical names are shared by more than one distinct
identity and were NOT merged** — the scenario fails if similar names are merged, and nothing
merged them.

## Scenario 2 — nothing is silently dropped (US1, FR-004, guarantee 2)

**Run**: `pytest tests/resolution -k unresolved`
```
.......                                                                  [100%]
7 passed, 13 deselected in 0.04s
```

**Live published dataset**:
```
-- Scenario 2 (FR-004): nothing silently dropped --
   published questions                             : 95,268
   95,269 fetched - 1 declared duplicate = 95,268  : True
   by status                                       : {'resolved': 91796, 'unresolved': 3472}
   every question carries a status                 : True
   ambiguous records                               : 0
   every ambiguous lists >=2 candidates, no id     : True
   PARTLY resolved (unresolved, >=1 asker kept)    : 1,231
   no asker at all                                 : 2,241

```
**Verdict: PASS.** The count is preserved exactly: 95,269 fetched minus the one declared
duplicate gives 95,268 published, and every one carries a `resolution_status`. 3,472 questions
are `unresolved` and all 3,472 are still published.

Two things the live data shows that the fixtures could not:

- **1,231 questions are *partly* resolved** — status `unresolved`, but the askers that did
  resolve are retained. Dropping those joins to punish an unrelated one would lose true
  information; keeping the question at `resolved` would claim a join it does not have.
- **0 ambiguous records.** Every residual form came out `unresolved`, not `ambiguous`,
  consistent with the `ambiguous` column being 0 in every table in `resolution-rate.md`. So the
  "ambiguous lists its candidates" clause is **vacuously true on this dataset** — it is enforced
  by `ResolutionRecord.__post_init__` and tested on fixtures, but the live window exercises no
  case of it. Recorded as vacuous rather than as evidence.

## Scenario 3 — co-asked questions (US1, FR-003)

**Run**: `pytest tests/resolution -k co_asked`
```
....                                                                     [100%]
4 passed, 16 deselected in 0.03s
```

**Live published dataset**:
```
-- Scenario 3 (FR-003): co-asked carried on ONE record --
   question_id unique in by-session                 : True
   co-asked questions                              : 23,385 (24.5%)
   max askers on one record                        : 47
   no record repeats an asker                      : True
   total joins 155,003 over 95,268 questions -> mean 1.6270 askers/question
```
**Verdict: PASS.** `question_id` is unique in `by-session`, 23,385 questions (24.5%) carry more
than one asker on a single record, and no record repeats an asker.

**Two new measurements the spike did not have.** `route-capture.md` observed a maximum of **20**
askers on one question from a 250-record sample and recorded asker multiplicity as "observed
twice, not converged". Over the full window: the maximum is **47** and the mean is **1.6270**.
The spike's term-mean for the 18th was 1.6453, so the window mean is slightly lower, and the
maximum is 2.35× what the sample suggested.

## Scenario 4 — joins are independently verifiable (FR-005)

**Run**: `make verify-joins`, against the live output.
```
verify-joins: 95,268 published question(s) in by-session/
              155,003 join(s) to 796 member identity/ies
              972 resolution record(s)
              796 identity/ies reachable through a record

verify-joins: PASS -- every published join is auditable (FR-005).
```
**Verdict: PASS.** 155,003 published joins reach 796 member identities, and all 796 are
reachable through a resolution record carrying the name as written and a source record
reference. The check recomputes nothing — it reads the published files only.

## Scenario 5 — subsets without the whole, on every axis FR-007 names

**Run**: `make extract` once per axis, against the live output.
```
=== scenario 5: make extract, all five FR-007 axes (live dataset) ===

--- make extract HOUSE=lok-sabha/17 SESSION=1
extract: axis=house value='lok-sabha/17'
  one partition file: lok-sabha-17-1
  files opened          : 1
  questions (deduped)   : 6,198
  budget                : 1 partition file -- within FR-007

--- make extract MINISTRY=defence
extract: axis=ministry value='defence'
  one partition file: defence
  files opened          : 1
  questions (deduped)   : 982
  budget                : 1 partition file -- within FR-007

--- make extract MEMBER=ls-5199
extract: axis=member value='ls-5199'
  one partition file: ls-5199
  files opened          : 1
  questions (deduped)   : 631
  budget                : 1 partition file -- within FR-007

--- make extract STATE=Maharashtra
extract: axis=state value='Maharashtra'
  the member reference set matched 432 member(s), of which 77 had a published file; the whole question record was NOT read
  files opened          : 78
  questions (deduped)   : 13,742
  budget                : 1 reference set + n member file(s) -- within FR-007

--- make extract CONSTITUENCY=Raigad
extract: axis=constituency value='Raigad'
  the member reference set matched 2 member(s), of which 1 had a published file; the whole question record was NOT read
  files opened          : 2
  questions (deduped)   : 631
  budget                : 1 reference set + n member file(s) -- within FR-007
```
**Cross-axis totals, de-duplicated on `question_id` before comparison (guarantee 6)**:
```
distinct question_id   by-session=95,268  by-ministry=95,268  by-member=93,027
by-session == by-ministry : True
by-member is a subset     : True
union of all three        : 95,268
```
**Verdict: PASS.** Session, ministry and member each come from **one** partition file. State and
constituency resolve through the member reference set plus only the matching members' files —
`STATE=Maharashtra` opened 78 files (1 reference set + 77 member files) out of 1,759, and the
tool asserts the whole question record was not read.

De-duplicated totals agree: `by-session` and `by-ministry` hold the identical 95,268 ids, and
`by-member` is a strict subset at 93,027 — the 2,241 absent are the questions with no resolved
asker at all. 91,796 resolved + 1,231 partly resolved = 93,027, which reconciles exactly.

## Scenario 9 — degrade quietly, alert the maintainer (FR-010, FR-011, SC-006)

**This scenario CANNOT be run against the live publish, and that is not a technicality.** It
requires the upstream to be "simulated as unavailable, shape-changed, and truncated in turn".
The live run **succeeded**, so none of those three states occurred. Injecting them into the real
upstream is not possible, and deliberately corrupting a successful publish to manufacture the
evidence would destroy the thing T059 exists to produce.

**How it was exercised instead**, with what each substitute does and does not establish:

**Run**: `pytest tests/resilience`
```
.................                                                        [100%]
17 passed in 0.07s
```
All three failure modes are driven through the **real** transport and ingest code paths against
a scripted upstream (`httpx.MockTransport`) — not a mocked-out pipeline:

| Clause | How exercised | Establishes |
|---|---|---|
| Upstream unavailable | `ConnectError` and HTTP 503 injected | `ingestion-failure` signal raised, `should_publish` False |
| Shape changed | asking-member field renamed | `upstream-shape-change` signal carrying the missing and added names |
| Truncated | envelope claims 4,500, one record served | refused; `expected`/`received` recorded; nothing published |
| Last-known-good | a complete snapshot retained and re-dated | `last_known_good` flips, `last_refreshed` **keeps the last successful date** |
| Visitor sees no error | retained statement re-read | every field still populated, both formats in step |
| No value in a signal | marker string planted in a 500 body | marker absent from the rendered signal |

**What the live run DOES contribute to this scenario**, as real evidence rather than simulated:

- The **truncation check ran for real, twice, and passed**: term 17's sidecar records
  `expected: 60549, records: 60549`, and term 18 likewise. A short fetch would have been refused.
- The **upstream-duplicate declaration fired on live data** —
  `lok-sabha/17/4/unstarred/2204` was served twice, reduced to one, and declared in the Coverage
  Statement's `known_gaps`. That is FR-013's "reflected rather than passing silently", observed
  rather than simulated.
- **No shape-change signal fired**, so the live field set still matches the recorded baseline.

**What remains unestablished.** The visitor-facing half of FR-010 has never been observed on a
real failure: no refresh has yet failed against the live upstream, so the last-known-good path
has run only against hand-built snapshots. It will first be exercised for real the first time a
scheduled run fails, and the workflow step that feeds it
(`.previous-snapshot/`) has itself never run on GitHub.

**Verdict: PASS BY SUBSTITUTION. NOT a pass for "run against the live publish".**

## Scenario 10 — field scope is bounded (FR-008, SC-010)

**Run**: `make audit-fields`, against the live output.
```
audit-fields: the three scopes of quickstart.md scenario 10
  repository root: /Users/rohanupalekar/claudecode/indian-sansad

  [PASS] data/published/ -- 1759 file(s) scanned, size ceiling NOT applied (published files are legitimately large)
  [EMPTY] web/ -- 0 file(s) to scan
          nothing audited -- this is NOT a pass for this scope
  [PASS] tests/ -- 19 file(s) scanned, size ceiling 65536 B

audit-fields: 2 of 3 scope(s) audited and clean. NOT AUDITED: web (present but empty).
audit-fields: PASS for what exists. This is NOT a clean bill of health for the absent scope(s) above.
```
And `make guard` over the whole tree including the live dataset:
```
guard: PASS -- 1894 file(s) scanned under /Users/rohanupalekar/claudecode/indian-sansad; no prohibited attribute, no payload over 65536 bytes
```
**Verdict: PASS for `data/published/` and `tests/`. NOT a pass for `web/`.**

`data/published/` — all **1,759** live files, both formats, every partition, the reference sets,
the coverage statement and the resolution records — carries **no** attribute outside the FR-008
set. `tests/` is clean on 19 files. `make guard` scans 1,893 files across the whole tree and
finds no prohibited attribute.

**`web/` is EMPTY and is reported `[EMPTY]`, not `[PASS]`.** The tool says so itself: "nothing
audited -- this is NOT a pass for this scope". No task in T051–T058 writes `web/`; the page is
T074–T081, and T084 is the task that runs this audit over `web/` and `web/lib/`. **SC-010 is
therefore satisfied for the dataset and unestablished for the page**, because the page does not
exist. A placeholder file written to turn the check green would be worse than the red.

## Scenario 11 — coverage honesty (FR-013)

**Run**: `make coverage`, against the live output.
```
=== lok-sabha ===
  houses_covered: lok-sabha
  period_start: 2019-06-21
  period_end: 2026-08-12
  sessions_covered:
    - lok-sabha/17/1
    - lok-sabha/17/10
    - lok-sabha/17/11
    - lok-sabha/17/12
    - lok-sabha/17/14
    - lok-sabha/17/15
    - lok-sabha/17/2
    - lok-sabha/17/3
    - lok-sabha/17/4
    - lok-sabha/17/5
    - lok-sabha/17/6
    - lok-sabha/17/7
    - lok-sabha/17/8
    - lok-sabha/17/9
    - lok-sabha/18/2
    - lok-sabha/18/3
    - lok-sabha/18/4
    - lok-sabha/18/5
    - lok-sabha/18/6
    - lok-sabha/18/7
    - lok-sabha/18/8
  sessions_covered_count: 21
  total_questions: 95268
  resolved_automatic: 90298
  resolution_rate_automatic: 0.947831
  resolved_including_assertions: 91796
  resolution_rate_including_assertions: 0.963555
  sc_002_target: 0.95
  sc_002_met_on_published_rate: True
  sc_002_met_on_automatic_rate: False
  assertions_in_effect: 4
  assertions_overriding_an_automatic_match: 0
  duplicate_records_declared:
    - lok-sabha/17/4/unstarred/2204
  ministry_ids: 56
  ministry_names_observed: 64
  ministry_names_without_confirmed_mapping: 56
  ministry_name_groups_merged_by_normalisation:
    - ['COMMUNICATION', 'COMMUNICATIONS']
    - ['ENVIRONMENT,  FORESTS AND CLIMATE CHANGE', 'ENVIRONMENT, FOREST AND CLIMATE CHANGE']
  ministry_names_in_reference_set_with_no_questions: 4
... (known_gaps and the Rajya Sabha statement follow; both shown below)
```
The two clauses the scenario turns on:
```
57:=== rajya-sabha ===
58:  houses_covered: rajya-sabha
59-  period_start: not stated
60-  period_end: not stated
61-  sessions_covered: (none)
...
55:  unobtainable_reason: None
82:  unobtainable_reason: No Rajya Sabha route has been identified. GET /api_rs/members returns 403 where every sibling path returns 404, cause UNVERIFIED. This release covers the Lok Sabha ONLY (FR-001, FR-013).
```
**Verdict: PASS.** A statement exists for **both** Houses. The Lok Sabha statement names the
period (2019-06-21 .. 2026-08-12), all 21 sessions, the known gaps, and **both** resolution
rates with their denominators. The Rajya Sabha statement is present and says explicitly that no
route has been identified and that this release covers the Lok Sabha only — it is not omitted,
which is what `data-model.md` requires ("MUST say so explicitly rather than implying both
Houses are covered").

`tools/show_coverage.py` exits non-zero if any House lacks a statement; it exited 0.

---

## What this validation does NOT establish

- **Scenario 9's visitor-facing half on a real failure.** Never observed; see above.
- **Scenarios 6, 7, 8 and 12** were out of scope for T060 and are not claimed. 6, 7 and 12 need
  the reader page (T074–T081); 8 needs the composition aggregates (T068).
- **`web/`** is empty, so SC-010 is unestablished for the page.
- **The `ambiguous` branch** of scenario 2 is vacuously true on this window — 0 ambiguous
  records live.
- **Nothing has been pushed to GitHub.** The `published` branch does not exist, the workflow has
  never run, and the one-commit-deep orphan-branch mechanism is unproven in operation.
