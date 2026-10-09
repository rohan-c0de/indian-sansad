# Spike Report — the Phase 2 gate

**Feature**: `specs/001-resolved-metadata-layer`
**Date**: 2026-10-09
**Task**: T020

> **This file is the gate. No Phase 3 task may begin until it exists.** It now exists.

Every verdict carries one of `VERIFIED WORKING | VERIFIED BROKEN | UNVERIFIED | UNTESTABLE |
NOT PRESENT`, with the producing output pasted in the linked file. No figure here is a
paraphrase. A single successful observation is recorded as **observed once**, never as a general
property.

---

## One verdict per spike item

| # | Spike item | Verdict | The figure that settles it |
|---|---|---|---|
| **1** | Capture the question-metadata route | **VERIFIED WORKING** | `GET /api_ls/question/qetFilteredQuestionsAns` → HTTP 200, retrieved first-hand from the browser *and* programmatically. No credential, and with `User-Agent` and `Accept` stripped, **no required header at all**. [`route-capture.md`](./route-capture.md) |
| **4a** | Name the free CI tier | **VERIFIED WORKING** | GitHub Actions, public repository: *"GitHub Actions usage is free ... for public repositories that use standard GitHub-hosted runners."* **Unmetered — no overage is possible.** [`free-tiers.md`](./free-tiers.md) |
| **2** | Can a free CI runner reach the route | **VERIFIED WORKING** | HTTP 200 on both routes from an Azure `westus3` runner, run `37973110849`. No 403, no 429, no geo-block. **FR-009 is not blocked.** [`ci-reachability.md`](./ci-reachability.md) |
| **3** | Measure the resolution rate and correction cost | **VERIFIED WORKING** | **99.68%** of 34,720 questions resolve to exactly one member (98.06% on the pessimistic pool) against SC-002's 95%. Correction cost **0.168 min/week** against a 120 min/week ceiling. [`resolution-rate.md`](./resolution-rate.md) |
| **4b** | Name the free static hosting tier | **VERIFIED, one part by construction** | GitHub Pages: 1 GiB site, soft 100 GB/month, soft 10 builds/hour, 100 MiB hard per-file. One-origin service of `web/` + `data/published/` holds **by construction, not by execution** — no page exists yet. [`free-tiers.md`](./free-tiers.md) |
| **5** | Measure bytes per partition and per first page load | **VERIFIED WORKING** | **25,033,292 bytes** for one real session → **326 MiB** projected for the window (31.8% of the 1 GiB ceiling). First page load **883 KiB** (ministry) / **479 KiB** (constituency). [`size-budget.md`](./size-budget.md) |

**All five items pass. No capability is being reduced or dropped.**

T020 requires that where an item failed, the capability being reduced or dropped is named. **No
item failed**, so nothing is dropped. Two reductions are nonetheless *pre-authorised* under
Principle I, so the decision is already made if a limit is ever reached:

- **If the published file count proves a problem** against GitHub's unpublished ceiling → drop
  the **per-member axis** (49.4% of published bytes), not buy hosting.
- **If the subject index proves too costly** → it is fetched **lazily, only on an actual search**,
  so no visitor who never searches pays its 3.13 MiB.

---

## Principle I evidence — every component, its tier, and the behaviour at the limit

The Cost gate requires: *"Every component named, with the free tier it lands on and the behaviour
at that tier's limit. No paid service, trial, or promotional credit anywhere."*

**Three components. No others. No paid service, no trial, no promotional credit.**

| Component | Free tier | Limit | **Behaviour at the limit** | Overage charge? |
|---|---|---|---|---|
| **Refresh compute** | GitHub Actions, public repo, standard GitHub-hosted runners | **Unmetered** — usage is free, not quota'd | No meter exists to exceed | **No** |
| | | Job duration **6 h** | *"the job is terminated and fails."* | **No** — hard stop |
| | | Workflow run 35 days | *"the workflow run is cancelled."* | **No** — hard stop |
| | | Concurrency 20 | Jobs queue | **No** |
| | | **60 days without repository activity** | **Schedule silently disabled** | **No**, but a silent functional failure — see below |
| **Published dataset hosting** | GitHub Pages | Site **1 GiB** (hard) | Site may not be served | **No** |
| | | Bandwidth **100 GB/month** (soft) | *"we may not be able to serve your site, or you may receive a polite email from GitHub Support"* | **No** |
| | | Builds **10/hour** (soft) | as above | **No** |
| | | Per file **100 MiB** (hard) | *"GitHub blocks files larger than 100 MiB."* | **No** |
| | | **File count** | **NOT PUBLISHED by GitHub** | unknown |
| **Reader front end** | GitHub Pages — **the same site**, adding no component and no second tier | as above | as above | **No** |

Every figure is quoted from GitHub's own current published pages with the URL and the retrieval
date (**2026-10-09**) in [`free-tiers.md`](./free-tiers.md).

**Measured demand against those limits:**

| Limit | Ceiling | Measured / projected | Headroom |
|---|---|---|---|
| Pages site size | 1 GiB | **326 MiB** | 3.1× |
| Pages per-file | 100 MiB | ~2.1 MiB largest | 48× |
| Job duration | 6 h | full ingest **20–50 min** (UNVERIFIED range) | ≥7× |
| Bandwidth | 100 GB/mo | 883 KiB/visitor → ~110,000 visitors | — |

### Two Principle I exposures that are not size, and were invisible before this spike

**1. Repository growth, not dataset size, is the binding constraint.** `data/published/` is
version-controlled, so every refresh writes a new ~326 MiB copy into git history. The working
tree stays at 326 MiB; the repository passes GitHub's *"ideally less than 1 GB"* in about **five
refreshes** and its *"less than 5 GB is strongly recommended"* within **sixteen**.

This **compounds** with the 60-day rule rather than sitting beside it: T008 concluded the refresh
must **commit on every run** to keep the schedule alive, so commits are simultaneously mandatory
for FR-009 and the mechanism that grows the repository without bound. Remedies and their costs
are tabled in [`size-budget.md`](./size-budget.md) T017. The only one that *bounds* growth — an
orphan branch with one rolling commit — costs the provenance `research.md` claims comes "for
free ... since history is inherent". **No choice is made here. It is Phase 3's, and it should be
made knowing that rationale does not survive it.**

**2. "Keep the repository public" is a cost constraint, not a publishing preference.** Public
Actions usage is unmetered; the private tier is 2,000 min/month and *"You pay for any additional
use above your quota"* when a payment method is on file. Making this repository private would
move the project onto a metered tier whose overage behaviour depends on account billing state.

---

## Principle II figure — the recurring manual work

The Upkeep gate requires: *"The recurring manual work this change adds, in hours per week, and
the project total after it."*

| | Measured | vs ~2 h/week (120 min) |
|---|---|---|
| **Identity corrections, steady state** | **0.168 min/week** (0.0028 h) | **0.14% of the budget** |
| Identity corrections, during the arrival burst | 0.846 min/week (0.0141 h) | 0.71% |
| Identity corrections, first pass | **18 min once** (0.30 h) | 15% of one week, one time |

Measured by the maintainer timing real corrections end to end: **median 3 minutes, maximum 7
minutes**, over **6** corrections — every distinct name form needing correction across the entire
34,720-question term.

**T013 asks which of the two figures breaches Principle II: neither, by three orders of
magnitude.**

### Three honest limits on that figure

1. **n=6.** T013 specifies timing *at least 20* corrections. Only six exist. The task presupposed
   a burden more than 3× larger than the real one — which is a result, not a measurement failure,
   but every derived number carries n=6.
2. **The arrival rate is front-loaded, and the average misdescribes it.** All six forms first
   appeared within the first 21.3 weeks of a 107.3-week span — four in the term's first eight
   days — and **zero in the 86 weeks since**. The flat average overstates ongoing work (zero for
   86 weeks) and understates the initial burst (5× higher). A mechanical cause is plausible (a new
   Lok Sabha seats ~543 members at once) but is recorded as a **hypothesis**; it predicts a fresh
   burst each general election and near-zero between, which would make the right planning unit
   "about 20 minutes per election" rather than any per-week rate.
3. **THE PROJECT TOTAL IS NOT ESTABLISHED, and this figure must not be read as it.** Principle II's
   gate asks for the project total after this change. What is measured here is **identity
   corrections only**. `plan.md` Risk 6 records the expectation that the 2h/week budget "is
   expected to go mostly on breakage", and the upstream carries no contract, versioning or
   deprecation notice. **Breakage upkeep is unquantified and cannot be quantified before the
   pipeline has run on a schedule.** The Upkeep gate is therefore **partly evidenced, not passed**
   — the component this feature adds is measured; the total is not.

---

# T014 — the SC-002 decision

## Decision: **SC-002 is MET. No amendment to `spec.md` is required and none is requested.**

| Configuration | Measured (per question) | Target | Outcome |
|---|---|---|---|
| **18th-LS candidate pool** — operative | **99.68%** | 95% | **MET, +4.68 points** |
| **Full-roster pool** — pessimistic bound | **98.06%** | 95% | **MET, +3.06 points** |

Met under both configurations, including the one that deliberately withholds a disambiguator the
real pipeline will have. T014 requires a stop for the owner's decision only if the rate is
*below* 95%; it is above under all three readings of the metric, so no decision is owed and
T014's two remedies — amend SC-002 downward, or close a gap with assertions — are moot.

Denominator **34,720 questions**, the complete 18th Lok Sabha, not a sample. Matcher thresholds
were fixed before the first run; the prototype emits `tuned_after_seeing_results: false`.

| Reading of SC-002 | Denominator | `ls18` | `full` |
|---|---|---|---|
| per **question**, every asker must resolve (strictest, quoted above) | 34,720 | **99.68%** | **98.06%** |
| per name instance | 57,124 | 99.81% | 98.83% |
| per distinct name form | 467 | 99.79% | 98.72% |

### The decision this spike actually surfaces, for the owner

`spec.md` Assumptions says SC-002's 95% *"should be revisited once real resolution rates are
known."* They are now known, and they are **4.7 points above** it — so the target may be too
**lenient**, not too strict. A 95% floor permits 1,736 of these 34,720 questions to go
unresolved; the measurement leaves **106**. A target 16× looser than measured performance would
let an order-of-magnitude regression pass unnoticed.

**Not actioned here**, for two reasons: T014's mandate is to record or stop, not to raise a
criterion; and the 17th Lok Sabha — 64% of the window — is unmeasured, so a floor raised on 36%
of the data would be an invented default again. **Recorded as an owner decision for after the
17th Lok Sabha is measured.**

### SC-002's second clause is not measured and is not claimed

*"...and 100% of the remainder are visibly marked unresolved rather than absent."* **NOT
MEASURED** — nothing is published, so nothing is marked. It is a property of published output,
tested by `quickstart.md` scenario 2 in Phase 4.

### And one limit on the rate itself

**It measures the coverage of matching, not its correctness.** A form that matched exactly to one
member is counted resolved; **no join was hand-checked against the real person.** The *precision*
of 99.68% is **UNVERIFIED**. `quickstart.md` scenario 4 (`make verify-joins`) is the check that
addresses it, in Phase 4.

---

## What Phase 3 inherits — findings that change the build

Each of these came out of the spike and is not in `plan.md`, `research.md` or `data-model.md`.

1. **The route path is `qetFilteredQuestionsAns` — `qet`, not `get`.** The upstream's own typo.
   Correcting it yields 404.
2. **Omitting `sessionNumber` returns the whole term.** Undocumented upstream and the most useful
   property of the route. `loksabhaNo` is required (400 without it); `pageNo` is 1-based and
   `pageNo=0` returns **HTTP 500**.
3. **`HEAD` returns 403 where `GET` returns 200.** FR-009's change detection **cannot** use a
   `HEAD` + `Content-Length` probe; it must `GET` a small page and compare `totalRecordSize`.
4. **Dates are `DD.MM.YYYY`**, one shape across all 34,720 records. Parsed as ISO or US format it
   does not raise — it silently yields the wrong date for the 40% of days ≤ 12, which is exactly
   a silent mis-scoping of FR-013's window exclusion. **Assert the format; never infer it.**
5. **Question and answer text is a declared gap.** Both are null inline and sit behind four
   document-path fields that Principle III forbids opening. `data-model.md`'s Coverage Statement
   has **no field for a field-level gap** — its `known_gaps` is typed for sessions and dates. A
   real FR-013 shortfall to fix in Phase 3.
6. **Two session anomalies to declare under FR-013**: 18th LS session **1** has 7 sitting days and
   **zero** questions; session **8** has **zero** sitting days and 4,500 questions. Both causes
   **UNVERIFIED**.
7. **Four questions carry no asker field at all** (4 of 34,720). The empty case is real.
8. **Ministry arrives as a name string, not an id.** A `ministry_id` must be minted and reconciled
   — a second, smaller instance of the identity problem.
9. **Candidate-pool restriction is the real disambiguator.** All five full-pool ambiguities are
   genuinely two different people, and every pair has exactly one member in the 18th Lok Sabha.
   `data-model.md` already requires the stronger date-scoped form of this rule.
10. **A token-containment match tier would resolve the one remaining unresolved form.** The
    question route says `Smt. Kanimozhi Karunanidhi`; the roster says `Kanimozhi Rajathi
    Karunanidhi` — similarity ~0.84 against a 0.90 threshold. **Deliberately not added**, because
    changing the matcher after seeing the result is what T012 forbids. Recorded as a Phase 3
    design recommendation with its evidence.
11. **Fetch the subject index lazily.** Eagerly loading 3.13 MiB cuts sustainable reach from
    ~110,000 to ~24,000 visitors/month to serve one feature.
12. **Every published figure is uncompressed.** Pages serves gzip/brotli, which on this shape
    would plausibly cut transfer 70–85%. The budget is deliberately stated uncompressed because
    the ratio has not been measured.

---

## What the spike did NOT establish

Stated so Phase 3 does not inherit these as settled.

1. **The 17th Lok Sabha has never been fetched.** 60,549 questions — **64% of the covered
   window**. Every window figure in this report is a projection from the 18th alone, and the
   resolution rate, the correction cost and the asker multiplicity are all 18th-LS-only.
2. **Rajya Sabha remains unobtainable.** `plan.md` Risk 1 stands. **But it is narrowed from three
   candidate causes to one**, on evidence: `HEAD`→403 on a public unauthenticated URL rules out
   *authorisation*, and 200 from an Azure datacentre IP undercuts the *datacentre-IP* candidate.
   A request-shape or path-specific filter is what survives. Nothing was tested against
   `/api_rs/members`, so the verdict stays **UNVERIFIED** — what changes is that T088 has a
   direction instead of more path guessing.
3. **Sustained-ingest rate limiting is unknown.** The CI run made **2** requests; a real refresh
   makes ~191. Whether the upstream throttles is the live question and is **not** answered.
4. **No fuzzy matching was ever exercised.** It resolved zero forms. The 0.90 threshold is
   untested in the direction that matters — nothing was accepted by it, and exactly one thing was
   rejected by it. **Not** evidence that fuzzy matching is unnecessary; evidence that its
   necessity is unevidenced *on this route, for this term*.
5. **No page exists.** The one-origin property and both page-load budgets are structural and
   arithmetic, not observed. T083 and T090 are the executed checks.
6. **Whether the server caps `pageSize` above 1,000** — `pageSize=5000` exceeded a 38 s client
   timeout; the server was never observed to refuse it.
7. **The 60-day inactivity rule is documented, not demonstrated.** No 60-day silence was tested.
8. **The project-wide upkeep total** (Principle II) and **licensing** (`plan.md` Risk 5) are both
   untouched. Licensing was scoped out by owner decision: **deferred, not cleared.**

---

## Attribution deviation, recorded

The constitution's Scope of Authority requires the work be *"published under a project name, not
the maintainer's name"*. The repository was created under the maintainer's personal account after
the project-named-organisation alternative was put to the owner with this consequence stated; the
owner chose the personal account. **Content complies** — `README.md` names the project and every
commit is authored as `Indian Sansad Maintainer <maintainer@indian-sansad.invalid>` — but the
published URL embeds a personal handle. **Reversible at any time** by transferring the repository,
with GitHub redirecting the old Pages URL. No amendment is requested. Detail in
[`free-tiers.md`](./free-tiers.md).

---

## Gate status

| Gate | Principle | Status |
|---|---|---|
| Cost | I | **Evidenced.** Three components, all free tiers named, every limit behaviour quoted, no overage anywhere. Two non-size exposures recorded. |
| Upkeep | II | **Partly evidenced.** This feature's component measured at 0.14% of budget; the project total is not establishable before a scheduled run. |
| Sources | III | **Evidenced.** Every input is an already-structured route. The four document-path fields are refused, and the text behind them is a declared gap. |
| Language | IV | **Evidenced.** `locale=en`; the two Hindi fields are refused; no translation path exists. |
| Member fields | V | **Evidenced for the spike.** Positive FR-008 allowlist at fetch time; `make guard` passes on every commit; no upstream body was ever written inside the tree. Re-run against real published output before publishing, per the constitution. |

**Phase 3 may begin.**
