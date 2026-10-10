# Spike item 5 — published size, measured from real bytes

**Tasks**: T016 (prototype publish of one real session) · T017 (projection to the window)
· T018 (subject-search index) · T019 (first-page-load budget)
**Date**: 2026-10-09
**Prototypes**: `spike/publish_sample.py`, `spike/index_sample.py` — both throwaway, both writing
to `$SANSAD_SCRATCH` only

`research.md` records three size claims as **ASSUMPTION at low confidence**: added storage from
the duplicated partitions, the subject-search index size, and page load size. All three are
measured below. None of them was the thing that turned out to matter most — see T017.

---

# T016 — prototype publish of one real session

## Verdict: VERIFIED WORKING. Real bytes, every axis the contract names.

**Session published: 18th Lok Sabha, session 7 — 6,975 questions.** The script chose it
automatically as the **largest** session in the slice, so the projection is not flattered by a
quiet one. (Sessions in the term range 3,499–6,975 questions.)

| | |
|---|---|
| Questions | **6,975** |
| Distinct ministries | **55** |
| Distinct members with a file | **437** |
| Resolution status | 6,969 resolved · 6 unresolved · 0 ambiguous |
| **Files written** | **994** (497 names × 2 formats) |
| **Total bytes, both formats** | **25,033,292** (23.87 MiB) |
| Bytes per question, both formats | **3,589** |
| Single copy (by-session alone) | 6,054,721 |
| **Duplication multiple** | **4.135×** |

## Bytes per axis, per format

| Axis | Files | Records | ndjson bytes | CSV bytes |
|---|---|---|---|---|
| **by-member** | 874 | 12,304 | **7,579,715** | 5,097,408 |
| by-ministry | 110 | 6,975 | 3,697,700 | 2,363,663 |
| by-session | 2 | 6,975 | 3,697,700 | 2,357,021 |
| reference (members, ministries, sessions) | 6 | 493 | 163,105 | 76,435 |
| coverage statement | 2 | 1 | 295 | 250 |
| **Total** | **994** | — | **15,138,515** | **9,894,777** |

**The per-member axis is the single largest thing published** — 50.1% of ndjson bytes — and it
exists because `contracts/published-dataset.md` guarantee 6 requires a per-member subset without
downloading everything.

**CSV is consistently ~35% smaller than newline-delimited JSON** (9.89 MB vs 15.14 MB) because it
carries no repeated key names. Both are published; neither is authoritative. The contract's
two-format requirement therefore costs **1.65× a single-format publish**, not 2×.

## Bytes per file — the distribution, not just the total

| Axis | Files | Smallest | Median | Largest | Records/file (min · median · max) |
|---|---|---|---|---|---|
| by-session | 1 | 3,697,700 | 3,697,700 | 3,697,700 | 6,975 · 6,975 · 6,975 |
| by-ministry | 55 | **8,117** | 56,369 | **234,055** | 11 · 111 · 451 |
| by-member | 437 | **347** | 11,490 | **66,429** | 1 · 27 · 76 |
| reference | 3 | 139 | 6,821 | 156,145 | 1 · 55 · 437 |

(ndjson only, one session.) **A 28× spread between the median and largest ministry file** is the
figure T019 needs — a visitor's first load depends on *which* ministry, not on an average.

## Two prototype decisions recorded so they are not mistaken for settled format

1. **CSV cannot hold a list.** `asking_members` and `name_variants` are pipe-separated in the
   CSV output. That is a prototype choice; the real publisher must state it in the contract,
   because a consumer splitting on the wrong character silently loses co-askers — exactly the
   failure FR-003 exists to prevent.
2. **`question_id` is the composite `ls-<lokNo>-<sessionNo>-<quesNo>`**, per `route-capture.md`
   T006. No upstream single id exists.

---

# T017 — projection to the full covered window

## Verdict: the dataset FITS the free tier. The repository does not.

T017 requires the arithmetic shown, from the three inputs `research.md` records as unmeasured.
**All three are now measured:**

| Input | Value | Source |
|---|---|---|
| The real session's question count | **6,975** | T016 |
| The window's question count | **95,269** | `route-capture.md` (17th 60,549 + 18th 34,720) |
| Per-member duplication factor (mean asker count) | **1.6453** | T013, over the complete 18th LS term |

```
SCALE FACTOR = 95,269 / 6,975 = 13.6586
```

### Method A — scale the measured total linearly

```
25,033,292 bytes x 13.6586 = 341,920,673 bytes = 326.1 MiB = 0.318 GiB
```

### Method B — rebuild from per-copy cost, substituting T013's term-mean asker count

```
by-session  :   868.1 B/question x 1 copy
by-ministry :   869.0 B/question x 1 copy
by-member   :  1030.3 B/record x 1.6453 copies = 1695.2 B/question
              --------------------------------------------------
subtotal    :  3432.3 B/question x 95,269 questions = 326,988,670
reference   :    239,540 x (900/493 members)        =     437,294
              --------------------------------------------------
TOTAL       :  327,425,964 bytes = 312.3 MiB = 0.305 GiB
```

**The two methods agree within 4.4%** (326.1 vs 312.3 MiB). They differ because the published
session is **1.072× more co-asked than the term average** — its own multiplicity is 1.7640
(12,304 records / 6,975 questions) against the term's 1.6453. Method A inherits the session's
figure; Method B substitutes the term's. **Method A is quoted as the headline because it is the
more conservative**, and because scaling a measured total introduces fewer assumptions than
rebuilding one.

### Against T015's published limits

| Limit | Value | Projection | Verdict |
|---|---|---|---|
| **GitHub Pages published site** | 1 GiB (hard) | 326 MiB | **FITS — 31.8% of the ceiling** |
| GitHub Pages bandwidth | 100 GB/month (soft) | — | see T019 |
| Pages per-file maximum | 100 MiB (hard) | largest projected file ~2.1 MiB (a by-session partition) | **FITS, with 48× headroom** |
| File count | **not published by GitHub** | ~2,000 files | **UNVERIFIED against an unpublished limit** |

**No published axis needs to be dropped.** Principle I's remedy — reduce demand or drop a
capability — is not triggered by the dataset size.

## But: the constraint T015 did not look at, and it is the binding one

**`data/published/` is version-controlled** (`plan.md` → Storage: "version-controlled files"), so
**every refresh writes a new copy of ~326 MiB into git history.** The *working tree* stays at
326 MiB; the *repository* does not.

```
  2 refreshes -> 0.64 GiB cumulative
  3 refreshes -> 0.96 GiB cumulative
  5 refreshes -> 1.59 GiB cumulative   (past GitHub's 1 GiB "ideally less than")
 10 refreshes -> 3.18 GiB cumulative
 16 refreshes -> 5.09 GiB cumulative   (past the 5 GiB "strongly recommended")
```

T015 quotes GitHub's own guidance: *"We recommend repositories remain small, ideally less than
1 GB, and less than 5 GB is strongly recommended."* **At a weekly refresh this project passes
1 GiB in about five weeks and 5 GiB within four months.**

**This compounds with the T008 finding rather than merely sitting beside it.** T008 found that
scheduled workflows are disabled after 60 days without repository activity, and concluded the
refresh must **commit on every run** to stay alive. So commits are simultaneously *mandatory* for
FR-009 and *the thing that grows the repository without bound*. The two constraints pull against
each other, and neither was visible before this spike.

### Remedies, with their costs — a Phase 3 decision, not settled here

| Remedy | Effect | Cost |
|---|---|---|
| **Publish only changed partitions** | History grows by what actually changed, not by 326 MiB. Between sessions almost nothing changes. | Requires change detection at partition granularity. Does not bound growth, only slows it. |
| **Publish to an orphan branch with one rolling commit** (force-pushed) | History never accumulates. Pages serves only the current tree, so nothing is lost to a visitor. | **Discards the provenance `research.md` relies on**: "Files also give FR-005 provenance and FR-016 refresh dating for free, since history is inherent." It would no longer be free; FR-005 would need explicit resolution records (which `data-model.md` already requires) and FR-016 an explicit date field. |
| **Drop the per-member axis** | Removes 49.4% of published bytes (1,695 of 3,432 B/question). | Breaks `contracts/published-dataset.md` guarantee 6. This is Principle I's prescribed remedy if one is needed — but the dataset fits, so it is not needed for *size*. It would only be a response to the *history* problem, and a poor one. |
| **Drop CSV** | Removes ~39% of bytes. | The assessment's evidenced audience is CSV-shaped. Dropping the format the evidence points at to save space the tier has is the wrong trade. |

**The orphan-branch remedy is the only one that bounds growth**, and its cost is a documented
re-derivation of FR-005 and FR-016 rather than a loss of capability. **No choice is made here.**
Phase 2 measures; choosing the publication mechanism is Phase 3's work, and it should be made
knowing that `research.md`'s "provenance for free" rationale does not survive it.

---

# T018 — the subject-search index

## Verdict: VERIFIED WORKING. 1.14 MiB measured, 3.13 MiB projected.

Measured over **all 34,720 questions** of the 18th Lok Sabha slice — the real subjects, not a
sample.

| Variant | Distinct terms | Postings | **Bytes** | B/question | Projected to 95,269 |
|---|---|---|---|---|---|
| **`subjects_only` — MEASURED AND CHOSEN** | 11,145 | 143,020 | **1,195,277** (1.14 MiB) | **34.43** | **3,279,748 (3.13 MiB)** |
| `subjects_plus_ministry_and_member` — also measured, for comparison | 11,895 | 380,537 | 1,895,621 (1.81 MiB) | 54.60 | 5,201,438 (4.96 MiB) |

T018 requires recording which of the two options `research.md` leaves open was measured, and the
other as **unmeasured**. Both were in fact measured, so the record is stronger than T018 asks
for — but the distinction T018 is protecting still holds and is stated explicitly:

> **`subjects_only` is the CHOSEN variant.** The wider variant is **measured but not adopted**,
> and adopting it is **not** a free change: it adds **1.83 MiB** to every visitor's download
> (+58.6%) for search over fields the page already has in its ministry and member reference sets.
> It is recorded as a measured alternative, not as an equivalent.

### Tokeniser configuration — deliberately unaggressive

| | |
|---|---|
| Case | lowercased |
| Split | on non-alphanumeric |
| Minimum token length | 3 |
| Stopwords | 36 common English terms |
| Stemming | **none** |
| Postings | delta-encoded ascending doc ids |

**A smaller index is achievable, and that is the reason this one was not made smaller.** Stemming
and a larger stopword list would both shrink it. The measurement should reflect what a maintainer
at ~2h/week would actually ship and keep working, not the floor an optimiser could reach.
Postings *are* delta-encoded, because measuring an un-encoded index would overstate the budget
and make the page look less viable than it is.

### The projection is linear and slightly pessimistic

3.13 MiB assumes bytes scale with question count. **Postings do scale linearly; the term
dictionary does not** — adding the 17th Lok Sabha's 60,549 questions will add far fewer than
11,145 new distinct terms, since parliamentary subject vocabulary repeats heavily. The real
window index is therefore **somewhat smaller** than 3.13 MiB. The pessimistic figure is kept
because T019's budget should not rest on an unmeasured sub-linearity.

---

# T019 — the first-page-load byte budget

## Verdict: both reader views fit. Subject search is 4.6× the cost of everything else combined.

Derived from T015 (the tier), T017 (partition bytes) and T018 (the index), using the
**window-scaled per-file sizes** rather than the one-session measurements:

| Published file | Window-scaled size |
|---|---|
| one by-ministry file | **842,496 B** (823 KiB) |
| one by-member file | **107,290 B** (105 KiB) |
| one by-session file | 2,197,814 B (2,146 KiB) |
| members reference set | **321,580 B** (314 KiB) |
| coverage statement | 295 B |
| subject index (`subjects_only`) | **3,279,748 B** (3.13 MiB) |

**The page shell is an ESTIMATE, not a measurement: 60 KiB** for hand-written HTML, CSS and ES
modules with no build step. `web/` does not exist yet. It is the only non-measured input below
and it is small enough not to change any conclusion.

## The two views `quickstart.md` scenarios 6 and 7 describe

### First ministry-profile view (User Story 2)

| Component | Bytes |
|---|---|
| page shell *(estimate)* | 61,440 |
| coverage statement | 295 |
| one by-ministry file | 842,496 |
| **TOTAL** | **904,231 B = 883 KiB = 0.86 MiB** |

**Visitors/month inside the 100 GB soft bandwidth: ~110,591**

### First ministry-profile view **with subject search**

| Component | Bytes |
|---|---|
| page shell *(estimate)* | 61,440 |
| coverage statement | 295 |
| one by-ministry file | 842,496 |
| **subject index** | **3,279,748** |
| **TOTAL** | **4,183,979 B = 3.99 MiB** |

**Visitors/month inside the 100 GB soft bandwidth: ~23,901**

### First constituency view (User Story 3)

The contract reaches state and constituency in **two fetches** — the member reference set, then
the matching members' files — rather than a per-state partition:

| Component | Bytes |
|---|---|
| page shell *(estimate)* | 61,440 |
| coverage statement | 295 |
| members reference set | 321,580 |
| one by-member file | 107,290 |
| **TOTAL** | **490,605 B = 479 KiB = 0.47 MiB** |

**Visitors/month inside the 100 GB soft bandwidth: ~203,830**

**The two-fetch design is vindicated by measurement**: the constituency view is the *cheapest*
of the three at 479 KiB, and a per-constituency question partition would have added ~543 × 2
files to republish records the member set already addresses.

## What this budget says

1. **Both reader views load in under 1 MiB without subject search**, and the constituency view
   in under half a MiB. Not latency-driven, per `plan.md`, and comfortably so.
2. **Subject search costs 3.13 MiB and is 78% of its view's total.** Loading the index eagerly
   cuts the sustainable audience from ~110,000 to ~24,000 visitors/month — a **4.6× reduction in
   reach** to serve one feature. The remedy is a design constraint for Phase 6, recorded here
   before the page is written: **fetch the index lazily, only when a visitor actually searches.**
   No one who never searches should pay 3.13 MiB.
3. **Bandwidth is not the binding limit on the dataset side**, but it *is* worth stating that a
   whole-dataset download is 326 MiB, so the 100 GB soft limit allows only **~305 full-dataset
   downloads per month**. A consumer taking everything is 1,000× more expensive than a visitor
   reading one ministry. FR-006 invites exactly that, and SC-009 hopes for it.

## What T016–T019 do not establish

1. **Everything here is the 18th Lok Sabha only.** The 17th — 60,549 questions, 64% of the
   window — has never been fetched. Every window figure is a projection from the smaller term.
2. **The page shell's 60 KiB is an estimate**, the single unmeasured input.
3. **No page exists**, so no first page load has been *observed*. T083 and T090 measure the real
   page against this budget; that is what `tasks.md` Ordering Decision 3 exists for.
4. **The by-ministry figure assumes ~60 ministries across the window**, extrapolated from 55
   observed in one session. If ministries fragment across terms the per-file size falls and the
   file count rises.
5. **No compression is accounted for anywhere.** GitHub Pages serves gzip/brotli, which on
   newline-delimited JSON of this shape would plausibly cut transfer by 70–85%. **Every figure
   above is uncompressed bytes**, so the real page loads and bandwidth consumption will be
   materially lower. The budget is deliberately stated uncompressed because the compression ratio
   has not been measured, and a budget resting on an assumed ratio is the kind of unverified
   figure this spike exists to eliminate.

---

# ADDENDUM — T016/T017 re-measured on a whole term

**Date**: 2026-10-09, after the sections above

T016 above measured **one session** (18th LS session 7, 6,975 questions) and T017 scaled it to the
window. The whole 18th term has now been published in `--window` mode, which replaces the scaled
estimate with a measurement for that term.

| Basis | Questions | Total bytes (both formats) | **B/question** | Duplication | Files |
|---|---|---|---|---|---|
| One session (T016 above) | 6,975 | 25,033,292 | **3,589.0** | 4.135× | 994 |
| **18th LS, whole term** | **34,720** | **113,425,115** | **3,266.9** | **3.872×** | **1,066** |

**The single-session basis overstated bytes per question by 9.9%.** The cause is measurable: that
session's own asker multiplicity was **1.7640** against the term's **1.6453**, and the by-member
axis republishes once per asker. Choosing the *largest* session made the estimate conservative,
which is what it was for.

### T017's window projection, revised

```
whole-term basis : 3,266.9 B/question x 95,269 = 311,222,000 B = 296.8 MiB
single-session   : 3,589.0 B/question x 95,269 = 341,920,673 B = 326.1 MiB  (what T017 published)
```

**~297 MiB, not 326 MiB — 27.6% of the 1 GiB GitHub Pages ceiling** rather than 31.8%. Every
conclusion T017 drew is unchanged: the dataset fits, no axis needs dropping, and **repository
growth through git history remains the binding constraint** rather than site size.

### T015's file count: measured for one term

T015 recorded the published file count as **UNVERIFIED against an unpublished GitHub limit**, and
estimated ~1,800–2,200 window-wide from ~900 member identities. Measured for the 18th alone:

| Axis | Files |
|---|---|
| by-member | **932** (466 members with ≥1 resolved question × 2 formats) |
| by-ministry | 112 |
| by-session | 14 |
| reference | 6 |
| coverage | 2 |
| **Total, one term** | **1,066** |

**Largest single published file: 3,697,700 B (3.53 MiB)** against the 100 MiB hard per-file limit
— 28× headroom, better than T016's single-session figure suggested.

The window total will be lower than 2 × 1,066, because the by-member and by-ministry axes span the
whole window rather than being per-term: the 887-member window union (`lsExpr` contains 17 or 18)
gives ~1,774 by-member files, plus ~120 by-ministry, 46 by-session, and ~8 reference and coverage
— on the order of **1,950 files**. That is within T015's estimated range, still against a limit
GitHub does not publish.

## What this addendum does NOT establish

**The window publish and the window-wide index were not run.** Both need the complete 17th Lok
Sabha, and sessions 11–15 were never fetched. So:

- **T017's ~297 MiB is still a projection**, now from a whole-term measurement rather than a
  single session — better grounded, but not the window measured.
- **T018's 3.13 MiB index figure is still a linear projection.** The sub-linearity asserted there
  — that the term dictionary grows far slower than the postings — remains **unmeasured**.
- **T019's page-load budget still rests on window-scaled per-file sizes**, not on real
  window-partitioned files.

---

## Status after the 17th Lok Sabha was completed

The complete 17th Lok Sabha is now fetched (60,549 questions), so the window is fully in hand at
95,269 questions. **The window publish and the window-wide index were NOT re-run**, because the
owner's instruction scoped this pass to resolution measurement and record updates.

So every size figure in this file stands as recorded, with its basis restated plainly:

| Figure | Status |
|---|---|
| 18th LS whole term: 113,425,115 B, 3,266.9 B/question, 1,066 files, largest file 3.53 MiB | **MEASURED** |
| One session (18th LS session 7): 25,033,292 B | **MEASURED** |
| Window total ~297 MiB | **PROJECTED** from the 18th's whole-term B/question |
| Window file count ~1,950 | **PROJECTED** from 887 window member identities |
| Subject index 3.13 MiB | **PROJECTED** linearly from the 18th's measured 1.14 MiB |
| First page load 883 KiB / 479 KiB | **PROJECTED** from window-scaled per-file sizes |

One input to those projections did improve: **asker multiplicity is now converged** at
1.645 (18th), 1.670 and 1.711 (17th sub-slices) — so the ~1.67 the window projection assumes is
measured across two terms rather than one, and the early drifting samples (1.32, 1.504) are
superseded.

**What would turn the projections into measurements**: `spike/publish_sample.py --window
--loksabha 17,18` and `spike/index_sample.py --loksabha 17,18`. Both are implemented and both
need only the data already on disk. Neither was run in this pass.

---

# MEASURED — the full window, published and indexed

**Date**: 2026-10-09. `spike/publish_sample.py --window --loksabha 17,18 --pool term` and
`spike/index_sample.py --loksabha 17,18`, over both complete terms already on disk.
**Every projection in this file is now superseded by a measurement.**

**Correctness cross-check**: the publish reports **86,352 resolved / 8,917 unresolved**, matching
`resolve_rate.py`'s independently computed window figure of 86,352 resolved + 8,913 unresolved +
4 no-asker exactly. The two code paths agree.

## T016/T017 — measured window publish

| | Projected (18th-LS basis) | **MEASURED (both terms)** | Error in the projection |
|---|---|---|---|
| Total bytes, both formats | ~311,222,000 (~297 MiB) | **227,007,149 (216.5 MiB)** | projection **37% high** |
| Bytes per question | 3,266.9 | **2,382.8** | projection 37% high |
| File count | ~1,950 | **1,750** | projection 11% high |
| Duplication multiple | 3.872× | **3.725×** | |
| Largest single file | — | **3,697,700 (3.53 MiB)** | |
| vs 1 GiB Pages ceiling | 27.6% | **21.1%** (4.7× headroom) | |

**Why the projection was 37% high**: it scaled the 18th Lok Sabha's bytes-per-question to the
window. The 17th is cheaper per question — its records carry shorter subject lines and the
per-member duplication lands differently — so the combined figure is well below the 18th's rate.
**Scaling one term to a window overstated it**, exactly as scaling one *session* to a term
overstated that (9.9%). The lesson is consistent: each level of aggregation is cheaper per
question than the level below it suggests.

### Measured bytes and files per axis

| Axis | Files | Records | ndjson bytes | CSV bytes |
|---|---|---|---|---|
| **by-member** | **1,576** | 148,158 | **66,954,627** | 37,720,338 |
| by-ministry | 124 | 95,269 | 39,603,343 | 21,349,962 |
| by-session | 42 | 95,269 | 39,603,343 | 21,344,919 |
| reference | 6 | 871 | 292,851 | 136,831 |
| coverage | 2 | 1 | 520 | 415 |
| **Total** | **1,750** | — | **146,454,684** | **80,552,465** |

21 sessions, 62 ministries, **788 members with at least one published file**.

### Measured per-file size distributions (ndjson)

| Axis | n | Min | Median | Mean | Max |
|---|---|---|---|---|---|
| by-session | 21 | 541,931 | 1,836,170 | 1,885,873 | **3,697,700** |
| by-ministry | 62 | 350 | **539,249** | 638,763 | **2,564,507** |
| by-member | 788 | 333 | **66,914** | 84,967 | **519,859** |
| reference | 3 | 2,929 | 7,879 | 97,617 | 282,043 |

**Largest published file is 3.53 MiB against the 100 MiB hard limit — 28× headroom.**

### T015's file-count risk, now quantified

T015 recorded the file count as **UNVERIFIED against a limit GitHub does not publish**. Measured:
**1,750 files**. The limit remains unpublished, so the risk is unchanged in kind — but the
quantity is no longer an estimate, and 1,750 is a wholly ordinary number for a static site.

### Repository growth — the binding constraint, re-measured

At **216.5 MiB per published snapshot**, a version-controlled `data/published/` passes GitHub's
*"ideally less than 1 GB"* in **4.7 refreshes** and its *"less than 5 GB is strongly
recommended"* in **23.6**. Less acute than the ~297 MiB projection implied (4.0 and 18.0), and
still the constraint that binds first — the Pages site ceiling has 4.7× headroom while the
repository guidance is breached on the fifth refresh.

## OWNER DECISION — 2026-10-09: publish to a rolling orphan branch

**Decided. The T051 gate is discharged.**

The pipeline publishes the dataset to an **orphan branch named `published`**, as a **single commit
force-pushed on every successful refresh**. GitHub Pages serves that branch.

- **`main` never holds published data.** `data/published/` is **git-ignored on `main`**, because
  it is a build output.
- **`data/assertions/` stays on `main`** — maintainer corrections are an input, not output, and
  must survive a refresh that rewrites the published branch wholesale.
- **Before overwriting, the pipeline reads the previous snapshot from the `published` branch.**
  That read is load-bearing twice: FR-010's last-known-good needs the prior record, and FR-011's
  signal for a question leaving `resolved` needs something to compare against.
- **On any failed or partial refresh nothing is pushed**, so the previous snapshot keeps being
  served. Quiet degradation for visitors (FR-010) falls out of the mechanism rather than needing
  separate handling.
- **Every run also commits a small run-timestamp file to `main`**, including a run that finds
  nothing new, to stop the 60-day inactivity rule disabling the schedule.

### Why this, at the measured size

At the **measured 216.5 MiB per snapshot** — not the earlier **326 MiB projection**, which was
37% high — full history breaches GitHub's *"ideally less than 1 GB"* on about the **fifth**
refresh and *"less than 5 GB is strongly recommended"* within **twenty-four**. Publishing only
changed partitions slows that without bounding it. A rolling orphan branch is the only option on
the table that **bounds** growth, because the dataset's history is one commit deep at all times.

### The cost, accepted explicitly

**Provenance that `research.md` said came free from git history no longer does.** That file's
rationale read "Files also give FR-005 provenance and FR-016 refresh dating for free, since
history is inherent." Force-pushing a single commit destroys exactly that history:

| | Was to come from | **Now met by** |
|---|---|---|
| **FR-005** — any join independently verifiable | git history of the published files | **Resolution Records (T049)** |
| **FR-016** — every published set carries its rebuild date | git commit dates | **An explicit rebuilt-date field on every published set (T093)** |

Neither is a new requirement — `data-model.md` already specifies the Resolution Record and a
`last_refreshed` field. What changes is that they are now **the only** mechanism rather than a
belt alongside git's braces.

### Two things UNVERIFIED about this decision

1. **Whether GitHub counts a push to a non-default branch as repository activity** for the 60-day
   scheduled-workflow rule. The published wording is *"no repository activity ... in 60 days"*
   and does not enumerate what counts. **This is exactly why the run-timestamp commit to `main`
   exists** — it makes the keep-alive independent of that reading instead of betting FR-009 on
   it. If a push to `published` does count, the timestamp commit is harmless redundancy; if it
   does not, the timestamp commit is the only thing keeping the schedule alive.
2. **How quickly GitHub reclaims the dropped history on its side.** A force-push makes the old
   commits unreachable, but unreachable objects persist until the remote garbage-collects, and
   GitHub publishes no interval for that. So the *stored* repository may not shrink when the
   working tree does, and a force-push does not guarantee a bounded remote size on any stated
   schedule. **The check is repository size after the first few refreshes** — `gh api
   repos/{owner}/{repo} --jq .size` reports it in KB. If it climbs monotonically across refreshes,
   the orphan branch is bounding the working tree but not the repository, and this decision needs
   revisiting.

## T018 — measured window index

| Variant | Distinct terms | Postings | **Bytes** | B/question |
|---|---|---|---|---|
| **`subjects_only` — chosen** | 16,979 | 352,738 | **3,002,356 (2.86 MiB)** | **31.51** |
| `subjects_plus_ministry_and_member` | 18,152 | 972,521 | 4,860,719 (4.64 MiB) | 51.02 |

**Projected 3,279,748 B; measured 3,002,356 B — the projection was 9.2% high**, and the
**asserted sub-linearity is confirmed**: question count grew 2.74× (34,720 → 95,269) while the
term dictionary grew only **1.52×** (11,145 → 16,979). Postings scaled nearly linearly
(143,020 → 352,738 = 2.47×). The dictionary is the sub-linear part, as claimed.

## T019 — first page load, from measured window files

The page shell remains the **only estimated input** at 60 KiB; `web/` does not exist.

| View | Total | Visitors/month inside 100 GB |
|---|---|---|
| Constituency entry, median member | **401 KiB** | 243,358 |
| Ministry profile, median ministry | **587 KiB** | 166,332 |
| Constituency entry, **largest** member | 844 KiB | 115,759 |
| Ministry profile, **largest** ministry | **2.50 MiB** | 38,074 |
| Ministry profile + subject search | **3.44 MiB** | 27,750 |

**The spread matters more than the median.** T019 previously quoted 883 KiB for a ministry
profile from a window-scaled average. Measured, the median ministry is **587 KiB** but the
largest is **2.50 MiB** — a 4.4× spread, so a visitor's first load depends on *which* ministry
they open. Any page-weight budget must be set against the largest, not the median.

Subject search remains the dominant single cost at **2.86 MiB — 83% of its view's total**, and
loading it eagerly cuts sustainable reach from ~166,000 to ~27,750 visitors/month. **Fetch it
lazily, only on an actual search.** That conclusion is unchanged and now rests on measurement.

**A whole-dataset download is 216.5 MiB**, so the 100 GB soft bandwidth allows **441 full-dataset
downloads per month** — up from the 305 the projection implied.

## What remains unmeasured

1. **The page shell (60 KiB) is still an estimate.** `web/` does not exist.
2. **No page has been served**, so no first page load has been *observed*. T083 and T090 remain
   the executed checks.
3. **Every figure is uncompressed.** Pages serves gzip/brotli, which on this shape would
   plausibly cut transfer 70–85%. The compression ratio has not been measured, so the budget is
   deliberately stated uncompressed.
4. **These bytes reflect the unadopted current matcher.** With 8,917 questions unresolved, their
   `asking_members` arrays are empty, so adopting Option C or correcting forms would **add**
   per-member records and grow the published total somewhat.

---

## Two window-publish runs disagreed. The cause, and what the figures here reflect.

An **earlier** window-publish run reported figures that differ from the ones recorded above:

| | Earlier run | **The run recorded above** |
|---|---|---|
| Resolved | 83,122 | **86,352** |
| Files written | 1,630 | **1,750** |
| Total bytes, both formats | 224,767,279 | **227,007,149** |
| by-member files / records | 1,456 / 144,392 | **1,576 / 148,158** |
| Members with a published file | 728 | **788** |

**The run recorded above matches `resolve_rate.py` exactly** — its 86,352 resolved equals that
tool's independently computed window figure of 86,352 resolved + 8,913 unresolved + 4 no-asker,
reached by a different code path over the same inputs. The earlier run matched nothing.

### The cause, shown rather than asserted

The per-form detail filename did not vary with the `--questions` argument. Measuring sessions
11–15 as a holdout therefore **overwrote** the full-term detail file for the 17th Lok Sabha, and
the earlier publish consumed that holdout-only file. Inspecting the artefact confirms it:

```
resolution_detail_ls17_term.json -> forms: 432 | slice questions: 15082 | file: questions_ls17_s11-15.jsonl
```

432 forms over 15,082 questions is the holdout, not the 505 forms over 60,549 the full term
carries. Every asker name absent from that truncated dictionary scored as unresolved, which
explains the direction and the shape of all five differences: fewer resolved questions → fewer
members with any resolved question (728 vs 788) → fewer by-member files (1,456 vs 1,576) and
fewer by-member records (144,392 vs 148,158) → fewer total files and bytes.

The filename now carries a slice tag, the full-term details were regenerated (505 and 467 forms),
and the re-run is what is recorded above. **The published rates were never affected** — those
come from each run's own stdout, not from this file.

### What configuration the size figures reflect

**The containment tier was OFF and no maintainer assertion was applied** when these bytes were
measured. The publish used the current unadopted matcher, so 8,917 of 95,269 questions carry an
empty `asking_members` array.

**So these are a floor, not the final size.** Adopting the containment tier and seeding the four
confirmed assertions resolves 9,222 further questions (90,299 − 86,352 = 3,947 from the tier,
plus **1,498** from the assertions, less overlap — corrected 2026-10-09 from 1,409, which
undercounted by 89; the effect on these byte projections is under 0.1% of the window and does not
change any conclusion here), and each newly resolved asker adds that question
to a per-member file in both formats. The published total will **grow** — by roughly the share
those questions represent of the by-member axis, which is 46% of all published bytes. The size
figures above should be re-measured once Phase 3's matcher is in place.

---

# T061 — the real published dataset, MEASURED

**Date**: 2026-10-10
**Basis**: `make refresh SOURCE=upstream` — a live fetch of the full window, 52m 38s wall clock,
exit 0. `manifest.json` records `"source": "upstream"`. **This is no longer a projection.**

Every figure in this file above it that was marked PROJECTED for the window is now superseded by
measurement. The projections are left in place, struck through where quoted, because a report
that silently acquires better numbers cannot be audited.

## Bytes per axis, per format, per partition

| Axis | files | NDJSON | CSV | total |
|---|---:|---:|---:|---:|
| `by-session` | 42 | 38,761,450 | 22,451,842 | 61,213,292 |
| `by-ministry` | 112 | 38,761,450 | 22,456,112 | 61,217,562 |
| `by-member` | 1,592 | 66,505,933 | 39,376,161 | 105,882,094 |
| `reference` | 8 | 3,983,545 | 3,308,363 | 7,291,908 |
| `coverage` | 2 | 3,200 | 2,399 | 5,599 |
| `resolution-records` | 2 | 231,196 | 123,303 | 354,499 |
| `manifest.json` | 1 | — | — | 616 |
| **TOTAL** | **1,759** | **148,246,774** | **87,718,180** | **235,965,570** |

- **235,965,570 bytes = 225.0 MiB = 0.2198 GiB**
- **2,476.9 bytes per question** over 95,268 published questions
- NDJSON is **62.8%** of the bytes, CSV **37.2%**
- duplication across axes: **3.855×** the single-copy `by-session` cost
- largest file: **3,447,794 B (3.29 MiB)** — `reference/members.jsonl`
- largest *question* partition: **2,888,222 B (2.75 MiB)** — `by-session/lok-sabha-18-7.jsonl`
- per-record cost is near-identical between terms: **404.6 B/question** (17th) against
  **410.8** (18th), NDJSON, one copy. The 3× per-*page fetch* cost difference between terms
  does not show up as a size difference at all.

## Against T015's published limits

| Limit | Value | Measured | Verdict |
|---|---|---|---|
| GitHub Pages published site | **1 GiB (hard)** | **0.2198 GiB** | **FITS — 22.0% of the ceiling** |
| Pages per-file maximum | **100 MiB (hard)** | **3.29 MiB** | **FITS — 30× headroom** |
| Pages bandwidth | 100 GB/month (soft) | not exercised | see T019; unmeasured |
| File count | **not published by GitHub** | **1,759** | **still UNVERIFIED against an unpublished limit** |

**The total does not exceed the tier and no axis needs dropping.** Principle I's remedy is not
triggered. T017 said the same thing from a projection; it is now measured.

**The constraint T017 called binding is addressed, not by size but by the publication
mechanism.** T017's finding was that version-controlling `data/published/` grows the
*repository* by ~326 MiB per refresh and passes GitHub's 1 GiB guidance in about five refreshes.
At the measured 225.0 MiB that would have been about seven refreshes rather than five — the
problem was real either way. The owner's orphan-branch decision (T051) bounds it: the dataset's
history is one commit deep at all times. `data/published/` is git-ignored on `main` and the
repository does not carry the dataset at all.

## Against T017's projections — the projection was high by 24.2%

| | Bytes | B/question | Files |
|---|---:|---:|---:|
| ~~T017 Method A (single-session basis)~~ | ~~341,920,673~~ | ~~3,589.0~~ | — |
| ~~T017 Method B (per-copy rebuild)~~ | ~~327,425,964~~ | — | — |
| ~~T017 revised (whole-18th-term basis, operative)~~ | ~~311,222,000~~ | ~~3,266.9~~ | ~~~1,950~~ |
| **MEASURED, live** | **235,965,570** | **2,476.9** | **1,759** |

- against Method A: **−105,955,103 B (−31.0%)**
- against Method B: **−91,460,394 B (−27.9%)**
- against the operative revised projection: **−75,256,430 B (−24.2%)**
- file count: **1,759 against ~1,950 projected (−191)**

### Why it was high — and it is the projection's basis, not the implementation

The projection scaled the **18th Lok Sabha alone** at 3,266.9 B/question to the window. That
basis was unrepresentative, and **the spike's own numbers already showed it** before any
production code existed:

| Measurement of the window | B/question |
|---|---:|
| 18th term alone, extrapolated (what T017 used) | 3,266.9 |
| **The spike's OWN window-mode publish, same code, same format** | **2,382.8** |
| Production, live | 2,476.9 |

**The 18th-term basis overstates the window by 37.1% on the spike's own figures.** Two window
measurements, taken with two different codebases, agree with each other to within 3.9% and both
sit ~24–27% below the projection. So the error is in the extrapolation, not in what was built.

The three candidate explanations, each checked rather than assumed:

- **Not per-record size between terms** — 404.6 against 410.8 B/question, a 1.5% difference.
- **Not the duplication factor** — 3.855× measured against the 3.872× assumed, 0.4%.
- **The 18th-term publish's own single-copy cost** implies 843.7 B/question against the 639.7
  the spike's window publish measured with identical code. Those two spike runs disagree by 32%
  and **the cause is UNVERIFIED** — the 18th-term run is not reproducible from the artefacts
  retained, so nothing more is claimed about it here.

### Where production differs from the prototype (the +3.9%)

Production records are **larger** per record and the total is still only 3.9% above the
prototype's window publish, because fewer files carry them:

| | Prototype | Production | Δ |
|---|---|---|---|
| line length, one `by-session` record | 374 B | 418 B | **+11.8%** |
| `question_id` | 12 ch | 26 ch | +14 — `type` is now in the composite |
| `session` | 8 ch | 14 ch | +6 — the term is now in the id |
| `source_record_ref` | 25 ch | 67 ch | +42 — the full route plus the composite |
| JSON separators | `", "` / `": "` | `","` / `":"` | **−21 B/record** |
| `by-ministry` files | 124 | **112** | 62 slugged names → 56 ids: the fold merged 2, the four confirmed renames merged 4 |
| `by-member` files | 1,576 | **1,592** | 788 → 796 identities, because more questions resolve |
| new published sets | — | `resolution-records` (2), `manifest.json` (1) | FR-005 and FR-016 made explicit, which the orphan branch cost us for free |

The two id fields and `source_record_ref` grew because of correctness fixes — `type` in the
question composite, the term in the session id, the full route in the reference — and each is
worth its bytes. The compact separators pay for about half of it.

## What T061 does NOT establish

- **The subject-search index** (T018's 3.13 MiB) is still a **linear projection**. It was not
  built; `data/published/` carries no index, and the sub-linearity T018 asserted remains
  unmeasured.
- **T019's first-page-load budget** still rests on window-scaled per-file sizes. No page exists.
- **Bandwidth** against the 100 GB/month soft limit is unexercised — nothing has been served.
- **The orphan branch has never been pushed.** The 1 GiB ceiling is measured against a working
  tree; what GitHub Pages actually accounts for is unobserved.

## T061 addendum — the User Story 4 aggregates (Phase 5, 2026-10-10)

Phase 5 adds `data/published/aggregates/`. Measured, scratch-built from the cached window:

| Set | files | NDJSON | CSV | total |
|---|---:|---:|---:|---:|
| `composition` | 2 | 25,237 | 7,463 | 32,700 |
| `subject-trends` | 2 | 13,178,975 | 5,746,515 | 18,925,490 |
| `counting-basis` | 2 | 1,805 | 1,747 | 3,552 |
| **aggregates total** | **6** | | | **18,961,742** |

- aggregates add **18,961,742 B = 18.08 MiB**
- new total **254,927,427 B = 243.1 MiB**, against the live-built 225.0 MiB — **+8.04%**
- **23.7% of the 1 GiB Pages ceiling**, up from 22.0%. Still fits, with 76% headroom.
- largest aggregate file 13,178,975 B (12.57 MiB) — `subject-trends.jsonl`, against the
  100 MiB per-file limit, 8× headroom. It is now the **largest file in the dataset**, displacing
  `reference/members.jsonl` at 3.29 MiB.

### A 179 MiB mistake, caught by measuring rather than by reasoning

The first implementation carried the full counting-basis prose **inline on every aggregate row**,
which is the literal reading of "every aggregate carries the counting basis". Measured:

| | aggregates | dataset total | of the 1 GiB ceiling |
|---|---:|---:|---:|
| basis inline on every row | **195.1 MiB** | **420.2 MiB** | **41.0%** |
| basis published once per unit | **18.08 MiB** | **243.1 MiB** | **23.7%** |

**179 MiB of the 195 — 91% of the aggregates — was one sentence repeated 92,942 times.** It
would have nearly doubled the dataset.

The basis is now published once per unit in `aggregates/counting-basis.{jsonl,csv}`, and every
aggregate row carries `counting_basis_unit` and `basis_version`, which name the row that applies
to it. FR-012's "stated alongside the numbers" is met by a reference in the same directory that
always resolves — and `tests/contract/test_aggregates.py` asserts the reference **resolves**,
which is a stronger check than an inline copy could fail.

**`basis_version` stays on every row** deliberately, at two bytes: it is what lets a consumer
comparing two refreshes tell a changed definition from a changed dataset.

### What this addendum does not change

- T018's **subject-search index is still not built** and its 3.13 MiB figure is still a linear
  projection. `aggregates/subject-trends` is a per-session frequency series, not a search index;
  T070–T071 own the index.
- The figures here are **scratch-built**. The live-built dataset measured in T061 above is
  preserved at `$SANSAD_SCRATCH/live-publish-2026-10-10/`. The question records are identical;
  the manifest's `source` differs, plus 813 B of `source_record_ref` ordering.

---

# T072 — the real search index, measured against T018 and T019

**Date**: 2026-10-10 · **Basis**: the index `src/sansad/publish/search_index.py` writes over all
95,268 published questions, scratch-built from the cached window. **Not a projection.**

## The gate was failed first, then passed. Both figures.

| | Bytes | MiB | B/question | vs T018's 3,279,748 B |
|---|---:|---:|---:|---:|
| T018 projection (from the 18th LS at 34.43 B/q) | 3,279,748 | 3.13 | 34.43 | — |
| **First build** — document list as plain `question_id` strings | **4,607,033** | **4.39** | 48.36 | **+40.5% — OVER** |
| **After encoding the document list** | **2,484,745** | **2.37** | **26.08** | **−24.2% — WITHIN** |

Against T019's first-load budget for the ministry-profile view **with** subject search
(page shell 61,440 estimated + coverage 295 + one by-ministry file 842,496 + the index):

| | Bytes | MiB | vs T019's 4,183,979 B | Visitors/month inside 100 GB |
|---|---:|---:|---:|---:|
| T019 budget | 4,183,979 | 3.99 | — | 23,901 |
| with the first build | 5,511,264 | 5.26 | **+31.7% — OVER** | 18,145 |
| **with the encoded index** | **3,388,976** | **3.23** | **−19.0% — WITHIN** | **29,507** |

## Why the first build was over — and it was not the index

| Component | First build | Share |
|---|---:|---:|
| document list, as plain `question_id` strings | 3,018,967 | **65.5%** |
| terms and postings | 1,588,027 | 34.5% |

**Both of T018's predictions held.** It said distinct terms would grow sub-linearly and postings
linearly:

- distinct terms: **16,979** measured, where linear scaling from the 18th's 11,145 predicts
  **30,581**. Sub-linear, as recorded — "parliamentary subject vocabulary repeats heavily".
- postings per document: **3.70** measured against the 18th's **4.12**. Not merely linear —
  slightly *better* than linear.

So T018's measurement of the index proper was sound, and its "somewhat smaller than 3.13 MiB"
caveat was right about the terms. What T018 could not have projected is that **`question_id`
would get 2.61× longer**: it gained `type` and the term on 2026-10-09 when the 7,431-record
identity collision was fixed, going from `ls-17-1-500` (11 chars) to
`lok-sabha/17/1/starred/500` (26). The prototype never carried ids at that length.

## What was narrowed, and what was not

**The scope was NOT narrowed, because it could not be.** `subjects_only` is already the narrower
of the two variants T018 measured; the wider one costs +58.6% for search over fields the page
already holds. **The tokeniser was NOT touched** — stemming or a longer stopword list would
shrink the index further, and T018's reason for declining both stands, but changing it now would
void the very measurement this gate compares against.

**What was compacted is the document encoding**, for exactly the reason T018 gave for
delta-encoding postings: "measuring an un-encoded index would overstate the size and make the
page look less viable than it is." Every `question_id` is
`{house}/{term}/{session}/{type}/{number}`, and the first four parts take only **41** distinct
values across the whole window, so the list is stored as a prefix table plus two parallel integer
arrays:

| | Bytes | Share |
|---|---:|---:|
| document list, prefix-encoded | 896,647 | 36.1% |
| terms and postings | 1,588,027 | 63.9% |

**−2,122,288 B, −46.1%**, and nothing is lost: `question_id_at` rebuilds the exact id with two
array reads and a concatenation, and `tests/contract/test_search_index.py` asserts every id
round-trips **against the published question records** rather than against the objects the index
was built from.

## A second finding: the index format failed `make guard`, and the guard was right

The first two builds stored postings as `{"term": [...]}`, the natural shape for an inverted
index. `make guard` failed on **six** attribute violations in `search/subject-index.json`:

    key 'address'  / 'children' / 'daughters' / 'email' / 'marital' / 'mobile'

All six are real subject-line words from parliamentary questions — "Mobile Towers", "Children's
Welfare" — and none is anyone's personal attribute. But the guard treats a prohibited spelling in
a **structured position** (a JSON key, a CSV header, an assignment target) as a payload while
allowing the same word in prose, and it explicitly classifies those six as prose-ambiguous. Its
assumption is that **a JSON key is a field name**. In an inverted index over English subject
lines, every key is an English word, so that assumption breaks.

**The format was changed, not the guard.** Terms now live in a sorted `terms` array with postings
in a parallel `postings` array, which puts every token in value position where the guard's
prose/structured distinction works as designed. Cost: **13 bytes** (2,484,745 → 2,484,758) and a
binary search instead of an object lookup in the browser.

No protection was given up: the guard still scans the file, and a spelling it classifies as
unambiguous is still flagged in value position. The index indexes `Question.subject` only, and
the FR-008 allowlist drops every member attribute at the ingest boundary long before it runs.

**An exemption was considered and rejected.** Adding `data/published/search/` to the guard's
exempt list would have been one line, and would have made the guard blind to that directory
permanently. Changing the data's shape fixes the cause; exempting the check hides it.

(A third build then failed the guard on this spike file's sibling — the module docstring had
listed three of the compound prohibited field names as examples of what *would* still be caught.
Also correct: a module that documents a prohibition by reproducing it is the hole the guard
exists to close.)

## What T072 does not establish

- **This is not a browser measurement.** T083 measures the actual first-page-load bytes from a
  real network log; everything above is file sizes plus T019's 61,440-byte **estimate** for a page
  shell that does not exist yet.
- **Nothing is served.** Bandwidth against the 100 GB soft limit is still unexercised, and the
  visitors/month figures are arithmetic, not observation.
- **The index is not lazily fetched by anything yet.** `contracts/published-dataset.md` says
  consumers "should expect the page to fetch it lazily, only on an actual search"; whether the
  page does that is T079's to honour.

---

# Owner decision 2026-10-10 — the `by-member` axis stays as it is

`by-member` is **1,592 files and 105,882,094 B (100.98 MiB)**, which is **41.1% of the published
dataset** (257,804,931 B = 245.86 MiB total, 1,768 files). It is the largest single axis and
nothing reads it yet — the page reaches a member through the member reference set, not through
`by-member/`. **It stays.** FR-007 names member as a subset axis and a consumer taking one
member's questions in one fetch is exactly what it is for; the page not using it is not evidence
that a dataset consumer will not.

**Revisit only if the total passes 50% of the Pages ceiling** — 536,870,912 B. The total is at
**24.0%**, so the headroom is **279,065,981 B (266.1 MiB)**, and at today's size the whole
dataset would have to more than double before the question arises. If it does arise, the remedy
named in advance (T015, "What T015 does not establish") is to **drop the per-member axis** and let
consumers filter the session partitions — not to buy hosting.

**One correction to the figure this decision was taken on.** The share was reported to the owner
as **43%**, which was wrong: it divided `by-member` in **MB** (105.88) by the total in **MiB**
(245.86). Both correct forms give **41.07%** — 105,882,094 / 257,804,931 bytes, or 100.98 / 245.86
MiB. The decision is unaffected (41% and 43% are both "the largest axis, and far from the 50%
trigger"), but the number recorded here is the measured one.
