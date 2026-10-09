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
| **3** | Measure the resolution rate and correction cost | **VERIFIED WORKING, by owner decision** | Matcher alone: **90.64%** over the complete 95,269-question window (18th LS 99.68%; 17th LS 85.45%) — **below** the 95% target. With the adopted containment tier: **94.78%** — still below. With four seeded assertions: **96.26% — SC-002 met** with a 1.26-point margin, target unchanged at 95%. Correction cost **12 min** for the four. **The automatic rate remains below 95%**, which T053 requires be published separately. [`resolution-rate.md`](./resolution-rate.md) |
| **4b** | Name the free static hosting tier | **VERIFIED, one part by construction** | GitHub Pages: 1 GiB site, soft 100 GB/month, soft 10 builds/hour, 100 MiB hard per-file. One-origin service of `web/` + `data/published/` holds **by construction, not by execution** — no page exists yet. [`free-tiers.md`](./free-tiers.md) |
| **5** | Measure bytes per partition and per first page load | **VERIFIED WORKING** | **227,007,149 bytes (216.5 MiB) MEASURED across the full window** — **21.1%** of the 1 GiB ceiling, **1,750 files**, largest file 3.53 MiB against a 100 MiB limit. Subject index **2.86 MiB measured**. First page load **587 KiB** median ministry / **401 KiB** median constituency / **2.50 MiB** largest ministry. [`size-budget.md`](./size-budget.md) |

**All five items pass. No capability is reduced or dropped.**

T020 requires that where an item failed, the capability being reduced or dropped is named. Spike
item 3 did fail against SC-002 as measured, and the owner's decision of 2026-10-09 resolved it
**without reducing anything**: SC-002 stays at 95%, and the gap was closed by improving
resolution — a holdout-validated matcher tier plus four hand assertions — rather than by lowering
the target or dropping a published axis.

**What is conceded rather than reduced**: the pipeline does not reach 95% unaided. Four
maintainer assertions are load-bearing for SC-002, and T053 requires the automatic rate be
published alongside the assisted one so that dependence is visible to consumers instead of
blended away.

Two reductions remain pre-authorised under Principle I, so the decision is already made if a
limit is ever reached:

- **If the published file count proves a problem** against GitHub's unpublished ceiling → drop
  the **per-member axis** (49.4% of published bytes), not buy hosting.
- **If the subject index proves too costly** → it is fetched **lazily, only on an actual search**,
  so no visitor who never searches pays its **2.86 MiB** (measured).

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
| | | **File count** | **NOT PUBLISHED by GitHub** | unknown — **1,750 files measured**, an ordinary number for a static site, but against an unpublished ceiling |
| **Reader front end** | GitHub Pages — **the same site**, adding no component and no second tier | as above | as above | **No** |

Every figure is quoted from GitHub's own current published pages with the URL and the retrieval
date (**2026-10-09**) in [`free-tiers.md`](./free-tiers.md).

**Measured demand against those limits:**

| Limit | Ceiling | Measured / projected | Headroom |
|---|---|---|---|
| Pages site size | 1 GiB | **216.5 MiB measured** (227,007,149 B, both formats, full window) | **4.7×** |
| Pages per-file | 100 MiB | **3.53 MiB largest, measured** | 28× |
| Job duration | 6 h | full ingest **~75–80 min**, from measured wall times (18th: 797 s; 17th: ~60 min) | ~4.5× |
| Bandwidth | 100 GB/mo | **587 KiB median visitor → ~166,000 visitors**; 441 whole-dataset downloads | — |

### Two Principle I exposures that are not size, and were invisible before this spike

**1. Repository growth, not dataset size, is the binding constraint.** `data/published/` is
version-controlled, so every refresh writes a new **216.5 MiB** copy into git history — a measured
figure, not a projection. The working tree stays at 216.5 MiB; the repository passes GitHub's
*"ideally less than 1 GB"* in about **five refreshes** and its *"less than 5 GB is strongly
recommended"* within **twenty-four**.

**This remains the constraint that binds first.** The Pages site ceiling has 4.7× headroom and
the per-file limit 28×, while the repository guidance is breached on the fifth refresh.

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

### First-pass cost, measured across the full window

| | Forms needing correction | At the measured 3-min median | At the 7-min maximum |
|---|---|---|---|
| Matcher unchanged | **44** | **132 min = 2.2 h** | 308 min = 5.1 h |
| With the T014 Option C tier | 25 | 75 min = 1.2 h | 175 min = 2.9 h |

**The first-pass cost of 2.2 hours EXCEEDS Principle II's ~2 hours per week** for the week in
which it is performed. With Option C's tier it falls to 1.2 h and fits — but Option C is not
adopted, so **the figure that currently stands is the one that breaches the ceiling.**

It is a **one-time** cost rather than recurring work, and Principle II's operative language is
about *routine* manual work ("Occasional manual intervention is tolerated. Routine manual work is
NOT"). So this is a breach of the weekly ceiling by a non-routine task, which is the mildest form
the breach could take — but it is recorded as a breach rather than argued away, because the gate
asks for hours per week and 2.2 > 2.

### Steady-state arrival rate — **18th Lok Sabha only, and n=6**

| | Measured | vs 120 min/week |
|---|---|---|
| Flat average over the 18th LS's 107.3-week span | **0.168 min/week** | 0.14% |
| During that term's 21.3-week arrival window | 0.846 min/week | 0.71% |
| Over the 86.0 weeks since | 0.000 min/week | 0% |

**These figures describe the 18th Lok Sabha and must not be read as the project's steady state.**
Two limits, both load-bearing:

1. **n=6.** The timings come from six corrections — median 3 min, maximum 7 min — because six
   were all that existed in the 18th term. T013 specifies at least 20.
2. **The arrival rate was never measured for the 17th Lok Sabha.** Its 44-form burden is counted
   in the first-pass figure above, but the *rate at which its forms first appeared* was not
   computed, so no window-wide steady-state figure exists. The 0.168 min/week above is a
   single-term observation.

A further caveat the 17th introduces: the timings were measured on **18th-LS forms**, which were
all token-containment cases. The 17th's residual failures are initials, parenthetical aliases and
divergent orderings — plausibly slower per correction. **Whether 3 minutes holds for them is
UNVERIFIED**, which would make 2.2 h an underestimate.

### The project total is not established

Principle II's gate asks for the project total after this change. What is measured here is
**identity corrections only**. `plan.md` Risk 6 records the expectation that the budget "is
expected to go mostly on breakage", and the upstream carries no contract, versioning or
deprecation notice. **Breakage upkeep is unquantified and cannot be quantified before the
pipeline has run on a schedule.**

**Verdict: the Upkeep gate is NOT passed.** The first-pass figure breaches the weekly ceiling,
the steady-state figure covers one of two terms at n=6, and the project total is unavailable.

---

# T014 — the SC-002 decision

> ## ✅ OWNER DECISION RECORDED — 2026-10-09. SC-002 **stays at 95%** and is **met**.
>
> ### What was decided
>
> **Option C is adopted**: the bidirectional token-containment tier becomes part of the Phase 3
> matcher. **SC-002 is NOT amended** — the 95% threshold stands unchanged. The remaining gap is
> closed by **seeding maintainer assertions for four owner-confirmed residual forms**, not by
> lowering the target. A fifth was proposed and **dropped by the owner**.
>
> ### The evidence it rests on
>
> | | |
> |---|---|
> | Tier's gain on the **blind holdout** (sessions 11–15, 15,082 unseen questions) | **+6.31 points** (85.57% → 91.88%) |
> | Gain on the data the rule was derived from | +6.35 points — a 0.04-point difference, so **no measurable overfitting** |
> | Full window **with the tier** | **94.78%** (90,299 / 95,269) — still 207 questions short |
> | Full window **after the four confirmed assertions** | **96.26%** (91,708 / 95,269) — **SC-002 met with 1.26 points of margin** |
>
> ### Why adopting it after seeing the shortfall is acceptable
>
> This report's own objection stands on the record: adding a matcher tier after a rate falls
> short is the move T012 forbids. The decision accepts it on three stated grounds.
>
> 1. **It is a structural rule for an evidenced pattern, not a threshold tuned to a number.** No
>    threshold changed — `APPROX_THRESHOLD` is still 0.90 and `APPROX_MARGIN` still 0.02. What was
>    added is a rule for a name-variant mechanism observed 19 times across two terms: the question
>    route and the roster disagree about whether a middle name, patronymic or initial belongs in a
>    name. T012's prohibition targets fitting a figure; this rule would be correct even if the
>    rate had already passed.
> 2. **It was validated on a blind holdout.** The tier was written, tested and **committed while
>    sessions 11–15 were still being fetched** — they did not exist on disk, so no rule could be
>    fitted to them. Generalising to within 0.04 points on 15,082 unseen questions is the
>    strongest evidence available that it encodes a real pattern rather than this dataset's noise.
> 3. **It was not sufficient on its own, and that was not hidden.** The tier alone reaches 94.78%
>    and **fails** SC-002. Had the decision been driven by wanting the number to pass, the
>    simulation's earlier 95.33% would have been accepted; instead the measured 94.78% was
>    reported, and the gap is closed by declared hand corrections.
>
> ### One qualification on the tier's scope
>
> **Three of the 19 matches are alias forms the tier catches incidentally** — `Ravi Kishan Shukla`
> → `Ravindra Shukla Alias Ravi Kishan`, `Rajiv Ranjan (Lalan) Singh` → `Rajiv Ranjan Singh`, and
> `Satabdi Roy (Banerjee)` → `Satabdi Roy`. The tier was designed for differing name-component
> counts, not for aliases, and these satisfy containment by coincidence of their token sets.
>
> **So the tier must not be read as handling aliases.** It does not: parenthetical aliases remain
> among the 25 residual forms (`Poonam (Mahajan) Vajendla Rao`, `Balubhau (Alias Suresh Narayan)
> Dhanorkar`). Any future alias handling is a separate rule needing its own evidence and its own
> holdout.

## The measurement — now on the COMPLETE window

| Slice | Questions | Resolved | Rate | vs 95% |
|---|---|---|---|---|
| 18th Lok Sabha, complete term | 34,720 | 34,610 | **99.68%** | met |
| **17th Lok Sabha, complete term** | **60,549** | **51,742** | **85.45%** | **FAILS by 9.55 points** |
| **FULL WINDOW** | **95,269** | **86,352** | **90.64%** | **FAILS by 4.36 points** |

**No projection remains in this figure.** Both terms are fetched whole — the 17th's sessions
11–15 were retrieved after the earlier partial measurement, and 34,720 + 60,549 = 95,269 matches
the sum of the two terms' `totalRecordSize` exactly.

**Closing the gap by resolution requires 4,153 additional questions to resolve.**

The earlier figure in this file was 91.59% over 80,187 questions (84.2% of the window). Completing
the 17th moved it **down** to 90.64%, because the five added sessions resolve at 85.57% — close to
the rest of that term and far below the 18th.

## The second finding: fuzzy matching is load-bearing after all

On the 18th the approximate tier resolved nothing, and this report recorded that as "its
necessity is unevidenced on this route, for this term" rather than as evidence against it. That
caution was warranted:

| Tier | 18th LS forms | 18th LS instances | **17th LS forms** | **17th LS instances** |
|---|---|---|---|---|
| exact | 460 | 56,241 | 391 | — |
| normalised | 6 | 777 | 42 | 7,240 |
| normalised-reordered | 0 | 0 | 11 | 1,443 |
| **approximate (fuzzy)** | **0** | **0** | **18** | **3,465** |
| reached approximate and failed | 1 | 106 | 43 | 8,807 |

FR-002's fuzzy matching is justified — just not by the term that was measured first.

## Why the 17th fails: three causes, diagnosed

The 43 unresolved forms classify by token-set relationship against the candidate pool:

| Cause | Forms | Instances | Example (name forms are FR-008-permitted) |
|---|---|---|---|
| **Question form's tokens are a strict SUBSET of a roster name** | 10 | 2,167 | `Shrirang Appa Barne` vs roster `shrirang appa chandu barne` — a middle name the question omits |
| **Roster name is a strict subset of the question form** | 8 | 1,709 | `Supriya Sadanand Sule` vs roster `supriya sule` — a middle name the question adds |
| **No containment relationship** | 25 | 4,144 | `D.K. Suresh`, `Poonam (Mahajan) Vajendla Rao`, `Balubhau (Alias Suresh Narayan) Dhanorkar` — initials, parentheticals, aliases |

The first two share one mechanism and are mechanically fixable. The third needs judgement.

## Option C was implemented and holdout-tested. It generalises — and it still falls short.

The bidirectional token-containment tier was **implemented in the spike prototype only** (behind
`--containment`, off by default, never in `src/`) and **committed before sessions 11–15 of the
17th Lok Sabha were fetched**, so no rule or threshold could be fitted to them. Those five
sessions are the holdout.

### Holdout result — sessions 11–15, 15,082 questions, never seen

| | Resolved | Rate | Unresolved |
|---|---|---|---|
| matcher unchanged | 12,905 | **85.57%** | 2,177 |
| + containment tier | 13,857 | **91.88%** | 1,225 |
| **gain on unseen data** | **+952** | **+6.31 points** | |

**It generalises essentially perfectly.** The gain on the data the rule was derived from
(sessions 1–10) was **+6.35 points**; on unseen data it is **+6.31**. A 0.04-point difference is
no overfitting at all. 16 holdout forms resolved via the new tier.

### But the full window still fails

| Configuration | Window resolved | Rate | vs 95% |
|---|---|---|---|
| matcher unchanged | 86,352 / 95,269 | **90.64%** | NOT MET |
| **+ containment tier** | **90,299 / 95,269** | **94.78%** | **STILL NOT MET** |
| gain | +3,947 | +4.14 points | |

**Short by 207 questions — 0.22 percentage points.**

**This is the risk this report flagged, and it materialised.** The earlier simulation estimated
95.33% on 84.2% of the window, and objection 2 to Option C read: *"95.33% clears 95% by 0.33
points. That is not a comfortable pass. The five unfetched sessions, or the 17th's full term,
could put it back under."* They did. **Option C alone does not satisfy SC-002.**

Two of the three objections to Option C are now resolved in its favour, and the third stands:

- ~~It is simulated, not implemented~~ → **implemented and holdout-validated.**
- ~~The gain might not generalise~~ → **it does, to within 0.04 points.**
- **It is still a matcher change made after seeing the rate fall short**, which is the move T012
  forbids. That objection is unaffected by the holdout and remains the owner's to weigh.

## Assertions — four **CONFIRMED BY OWNER**, one **DROPPED BY OWNER** (2026-10-09)

These are the pairs T048 will seed. **None has been written to `data/assertions/` yet** — Phase 3
has not started.

Member fields shown are `member_id`, name form, constituency and state — all inside the FR-008
set — included because confirming an identity needs more than a name.

| # | Status | Questions blocked | Form as written (question route) | Member | Roster name form | Constituency, State | Basis |
|---:|---|---:|---|---|---|---|
| 1 | **CONFIRMED BY OWNER** | 513 | `Sunil Dattatray Tatkare` | `ls-5199` | `Tatkare Sunil Dattatrey` | Raigad, Maharashtra | Token reorder plus one spelling variant (`Dattatray` / `Dattatrey`); every token corresponds. |
| 2 | **CONFIRMED BY OWNER** | 414 | `Ganesan Selvam` | `ls-4963` | `Selvam G` | Kancheepuram, Tamil Nadu | The roster's `G` initial expands to `Ganesan`, reordered. Rested on that expansion, which the roster does not spell out. |
| 3 | **CONFIRMED BY OWNER** | 372 | `D.K. Suresh` | `ls-4585` | `Doddalahalli Kempegowda Suresh` | Bangalore Rural, Karnataka | `D.K.` = **D**(oddalahalli) **K**(empegowda); both initials match and the only `Suresh` in a Bangalore constituency this term. |
| 4 | **DROPPED BY OWNER** | 292 | `Poonam (Mahajan) Vajendla Rao` | ~~`ls-4660`~~ | ~~`Poonam  Pramod Mahajan`~~ | ~~Mumbai North Central, Maharashtra~~ | Proposal shared only `Poonam` and `Mahajan`; the question form's `Vajendla Rao` appears nowhere in the roster record and the roster's `Pramod` nowhere in the question form. **No reason for the drop was recorded by the owner, and none is inferred here.** The form **stays among the residual forms.** |
| 5 | **CONFIRMED BY OWNER** | 273 | `V. Kalanidhi` | `ls-4959` | `Kalanidhi Veeraswamy` | Chennai North, Tamil Nadu | `V.` = **V**(eeraswamy), reordered; the only `Kalanidhi` in the term. |

**Why these and not others**: the five were ranked by questions blocked, the largest-value
corrections available. Four were confirmed and one dropped.

### The window rate with the four confirmed pairs — computed, not summed

| | Resolved | Rate | vs 95% |
|---|---:|---:|---:|
| Tier only, no assertions (the **automatic** rate) | 90,299 / 95,269 | **94.78%** | fails by 0.22 |
| **+ the four confirmed assertions** | **91,708 / 95,269** | **96.26%** | **met, +1.26 points** |

**Recovered: 1,409 questions.** This was computed by re-walking all 95,269 question records and
counting those whose every residual asker is one of the four confirmed forms — **not** by adding
the per-form figures, because co-asked questions make them non-additive:

```
naive sum of questions the four forms appear in : 1,572
actually recovered                              : 1,409
difference                                      :   163
```

Those **163 questions stay unresolved** because each is co-asked by someone whose form is still
residual — including, for some, the dropped row 4. A question resolves only when *all* its
askers do (FR-003), so the figures cannot be summed and the earlier five-pair cumulative table
has been replaced by this computation rather than adjusted.

**The previously recorded figure was 96.56% (91,991) for five pairs. With row 4 dropped the real
figure is 96.26% (91,708)** — 283 questions fewer, which is more than row 4's own 292 blocked
count would suggest in isolation and less than it after overlap, for the same reason.

### Residual forms after seeding: **21**

25 residual forms remained after the tier. Four are now assertions, leaving **21** — and
`Poonam (Mahajan) Vajendla Rao` is one of them, carrying its 292 blocked questions.

**Cost**: 4 × 3-minute measured median = **12 minutes**. Correcting the remaining 21 is optional.

## The decision, re-costed against the complete window

### Option A — amend SC-002 to the measured rate

Set the target to **90.64%** (unchanged matcher) or **94.78%** (with the tier). **Cost:** the
published criterion becomes a description of current performance. 8,913 questions stay
unresolved-but-marked, which FR-004 permits.

### Option B — close the gap with maintainer assertions

**44 distinct forms × 3 min median = 132 min (2.2 h) first pass**, which **exceeds Principle II's
weekly ceiling**. Reaches 100%, since correcting every failing form leaves nothing unresolved.

### Option C — adopt the containment tier

**94.78%. Does not reach 95%.** Reduces the correction burden from 44 forms to **25**.

### Option C + B — the only combination that both meets SC-002 and fits the upkeep ceiling

| | Rate | First-pass cost |
|---|---|---|
| C alone | 94.78% (fails) | 1.2 h |
| **C + correcting the 25 residual forms** | **100.00%** | **75 min = 1.2 h** |

All 25 residual forms are in the 17th Lok Sabha; the 18th has **zero** after the tier. Reaching
95% needs only **207** more questions, and the largest single residual form blocks 528 name
instances — so one or two corrections would clear the threshold, with the remainder optional.

**Nothing is adopted. No matcher change is enabled by default. SC-002 is not amended.**

## SC-002's second clause is still not measured

*"...and 100% of the remainder are visibly marked unresolved rather than absent."* **NOT
MEASURED** — nothing is published, so nothing is marked. Phase 4, `quickstart.md` scenario 2.

## And the same limit on the rate itself

**It measures the coverage of matching, not its correctness.** No join was hand-checked against
the real person, so the precision of any figure here is **UNVERIFIED** — only its coverage is
measured.

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
11. **Fetch the subject index lazily.** Measured at **2.86 MiB** — 83% of its view's total.
    Loading it eagerly cuts sustainable reach from ~166,000 to ~27,750 visitors/month to serve
    one feature.
12. **Every published figure is uncompressed.** Pages serves gzip/brotli, which on this shape
    would plausibly cut transfer 70–85%. The budget is deliberately stated uncompressed because
    the ratio has not been measured.
13. **Page weight must be budgeted against the largest partition, not the median.** Measured
    ministry files span **350 B to 2,564,507 B** — the median first load is 587 KiB but the
    largest is **2.50 MiB**, a 4.4× spread.
14. **Projections overstate at every level of aggregation.** One session scaled to a term was
    9.9% high; one term scaled to the window was **37%** high; the index projection was 9.2%
    high. Each larger aggregate is cheaper per question than the level below predicts, so any
    future scope estimate built by scaling should be read as an upper bound.

---

## What the spike did NOT establish

Stated so Phase 3 does not inherit these as settled.

1. **Resolution AND size are both measured on 100% of the window.** Both terms are fetched whole
   (34,720 + 60,549 = 95,269, matching the sum of their `totalRecordSize`), the window publish
   and the window index have been run over them, and the publish's own resolved count (86,352)
   matches `resolve_rate.py`'s independently computed figure exactly. **No projection remains in
   any rate, byte count, file count or index size.** What is still *unobserved* rather than
   unmeasured: the page shell's 60 KiB is an estimate because `web/` does not exist, no page has
   been served, and every byte figure is uncompressed because the gzip/brotli ratio has not been
   measured.
2. **Rajya Sabha remains unobtainable.** `plan.md` Risk 1 stands. **But it is narrowed from three
   candidate causes to one**, on evidence: `HEAD`→403 on a public unauthenticated URL rules out
   *authorisation*, and 200 from an Azure datacentre IP undercuts the *datacentre-IP* candidate.
   A request-shape or path-specific filter is what survives. Nothing was tested against
   `/api_rs/members`, so the verdict stays **UNVERIFIED** — what changes is that T088 has a
   direction instead of more path guessing.
3. **Sustained-ingest rate limiting is unknown.** The CI run made **2** requests; a real refresh
   makes ~191. Whether the upstream throttles is the live question and is **not** answered.
4. **Fuzzy matching is now evidenced as necessary — and still insufficient on its own.** The
   earlier entry here said the approximate tier "resolved zero forms" and that its necessity was
   unevidenced. Across the complete 17th Lok Sabha it resolves **18 forms / 3,465 instances**, and
   114 forms (19,168 instances) need something beyond exact matching, against 7 forms (883
   instances) on the 18th. FR-002's fuzzy requirement is justified. What remains open is the
   opposite question: even with fuzzy matching *plus* the simulated containment tier the window
   reaches only **94.78%**, so the 0.90 threshold's calibration is untested in the one direction
   that would matter — whether a lower threshold would resolve more of the 25 residual forms
   without mis-joining anyone. **No threshold was altered to find out**, because that is the
   tuning T012 forbids.
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
| Cost | I | **Evidenced.** Three components, all free tiers named, every limit behaviour quoted, no overage anywhere. Two non-size exposures recorded. Ingest duration revised upward — see below. |
| Upkeep | II | **Partly evidenced, and the figure has grown.** The steady-state identity-correction cost stays far inside budget, but the **first-pass** cost rose from 18 min (18th LS alone) to **132 min (2.2 h) window-wide**, which exceeds Principle II's weekly ceiling for the week it is done. The project total remains not establishable before a scheduled run. |
| Sources | III | **Evidenced.** Every input is an already-structured route. The four document-path fields are refused, and the text behind them is a declared gap. |
| Language | IV | **Evidenced.** `locale=en`; the two Hindi fields are refused; no translation path exists. |
| Member fields | V | **Evidenced for the spike.** Positive FR-008 allowlist at fetch time; `make guard` passes on every commit; no upstream body was ever written inside the tree. Re-run against real published output before publishing, per the constitution. |

## ✅ Phase 3 is UNBLOCKED.

Both of T020's conditions are satisfied. The gate file exists, and T014's attached condition —
*"stop for the owner's decision. Do not choose, and do not proceed into Phase 3 on an assumed
answer"* — is discharged: **the owner decided on 2026-10-09** (Option C adopted, SC-002 retained
at 95%, four assertions seeded, a fifth dropped). The answer is recorded above, not assumed.

**Carried into Phase 3 by that decision:**

- **T046** — the matcher includes the containment tier, implemented exactly as the spike
  prototype implements it, thresholds unchanged.
- **T048** — the first assertions are the **four** owner-confirmed pairs, and only those; the
  dropped fifth stays among the 21 residual forms.
- **T053** — the Coverage Statement publishes the **automatic** rate and the rate **including
  maintainer assertions** separately, so a matcher regression cannot hide behind accumulated hand
  corrections.

**One thing Phase 3 must not inherit as settled**: SC-002 is met at 96.26% *with* four hand
assertions, and at **94.78% without them**. The automatic rate is **below** the threshold. That is
why T053 publishes both figures, and why the published record will show the shortfall rather than
conceal it.
