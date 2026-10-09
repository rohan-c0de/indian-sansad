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
