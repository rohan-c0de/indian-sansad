# Matcher equivalence — does `src/sansad/resolve` reproduce the spike's numbers?

**Date**: 2026-10-09
**Task**: verification of T046 (and T042–T049 in passing), before T051
**Tool**: [`tools/check_equivalence.py`](../../../tools/check_equivalence.py)
**Command**: `SANSAD_SCRATCH=<scratch> python tools/check_equivalence.py`
**Data**: the window already fetched into `$SANSAD_SCRATCH` — roster 5,426 members,
17th LS 60,549 questions, 18th LS 34,720 questions = **95,269**. **No live fetch.**
**Writes**: none. The tool reads `$SANSAD_SCRATCH` only, resolves the path with symlinks and
`..` collapsed, and refuses if it lands inside the repository. Everything below is an
aggregate or a name form; no record is reproduced and no attribute outside Principle V's
permitted set appears.

---

## Verdict in one line

**Two of the three figures reproduce exactly and the matcher port is exact. The third differs
by +89 questions, and the cause is in the spike's own uncommitted recount, not in the
matcher.** SC-002 is met under either figure (96.36% against 96.26%; target 95%).

## The three result lines

| Configuration | Produced | Rate | Spike | Rate | Agrees |
|---|---:|---:|---:|---:|:--:|
| containment OFF | 86,352 / 95,269 | **90.64%** | 86,352 / 95,269 | 90.64% | **YES** |
| containment ON | 90,299 / 95,269 | **94.78%** | 90,299 / 95,269 | 94.78% | **YES** |
| containment ON + four assertions | 91,797 / 95,269 | **96.36%** | 91,708 / 95,269 | 96.26% | **NO (+89)** |

## Per form: zero disagreements

**0 disagreements over 972 distinct name forms**, in both the OFF and ON configurations,
compared against the spike's own per-form detail artefacts
(`resolution_detail_ls{17,18}_term{,_containment}.json`) on **status, member ids and tier
reached**. Per-term resolved counts match exactly as well:

| Term | Pool (`lsExpr`) | Questions | No asker field | OFF | spike | ON | spike |
|---|---:|---:|---:|---:|---:|---:|---:|
| 18th LS | 544 | 34,720 | 4 | 34,610 | 34,610 | 34,716 | 34,716 |
| 17th LS | 559 | 60,549 | 0 | 51,742 | 51,742 | 55,583 | 55,583 |

**Pool-rule control: 0 of 1,103 pooled members** where `sansad.ingest.members`' term list
differs from the spike's `lsExpr` parse. The pool is selected on `lsExpr` here, exactly as
`--pool term` does, *not* through `Member.terms` — which falls back to `lastLoksabha` when
`lsExpr` is empty, a fallback the production ingest adds and the spike does not. Replicating
the spike means replicating its pool rule; the control shows the two agree anyway on this
roster, so the fallback is not masking a difference.

This is the evidence that **the latent `UnboundLocalError` in `spike/resolve_rate.py` changed
nothing measured** (see `resolution-rate.md` → *NOTE — a latent defect…*). The production
matcher reaches the containment fallback from the three deterministic tiers where the script
would have raised, and over 95,269 real questions **not one form takes that path** — the
`ambiguous` count is 0 at those tiers, so the fixed branch is still unreached on this data.

## The +89, decomposed

The spike's stated rule is *"counting those whose **every** residual asker is one of the four
confirmed forms"*. That is exactly what `sansad.resolve.status_for_question` implements. Run on
this data it recovers **1,498** questions, not 1,409:

| Questions recovered, by how many of the four block them | Count |
|---|---:|
| exactly one asserted form residual | 1,411 |
| two asserted forms residual | 87 |
| **total recovered** | **1,498** |

- spike's published recovered figure: **1,409**
- recovered by exactly one assertion: **1,411** — these sets are disjoint, so this is what a
  per-form method can reach
- recoverable **only** by two assertions together: **87** — a question co-asked by two of the
  four. A method that scores one asserted form at a time cannot recover these, because neither
  form alone unblocks the question.
- **unaccounted remainder: 2**

**The probable cause, stated as probable.** 1,411 − 1,409 = 2, and 1,411 + 87 = 1,498. The
spike's figure sits 2 below the per-form-reachable count and 89 below the per-question count,
which is the signature of a recount performed one asserted form at a time rather than one
question at a time — the very error the spike's own text warns about three paragraphs earlier
("blocked counts overlap and cannot be summed"). It is recorded as the probable cause and not
the confirmed one, because **the code that produced 1,409 was never committed**: no script
under `spike/` applies maintainer assertions (`grep` over `spike/*.py` finds only the
scratch-path assertion in `fetch_slice.py`), so the remaining 2 cannot be traced to a line.
Settling it would need that uncommitted recount.

**A separate inconsistency inside the spike's own artefacts, found on the way.** The assertions
table in `spike-report.md` gives "Questions blocked" as 513 / 414 / 372 / 273 (sum **1,572**,
the "naive sum" the 1,409 figure is set against). The spike's own correction worklist
(`correction_worklist_ls17_term_containment.md`) gives **528 / 443 / 396 / 296** for the same
four forms, which is what this tool measures for both instances and distinct questions
(528 / 443 / **395** / 296 — `D.K. Suresh` appears twice on one question). Neither 1,572 nor its
per-form parts is reproducible from the data. The 1,572 figure is not load-bearing for anything
— it exists in the report only to be rejected — but it is wrong by more than rounding.

**What is NOT the cause**, each checked:

- not the matcher — 0 form-level disagreements, and both unassisted figures reproduce exactly;
- not the pool — 0 of 1,103 members differ;
- not cross-term leakage — none of the four forms appears in the 18th LS's questions, and the
  18th's assisted gain is **0**;
- not an assertion pointing outside its term's pool — all four asserted members are in the
  17th LS pool;
- not the four `no_asker_field` records — they are in the 18th LS and are excluded from the
  resolved count by both methods.

## Would any assertion have overridden a different automatic match?

T048 lets a maintainer assertion win unconditionally, including over a *confident* automatic
match. That was flagged as the least defensible claim in the Phase 4 part 1 report. It is now
measured:

| Assertion form | asserted member | automatic outcome | conflict |
|---|---|---|---|
| `D.K. Suresh` | ls-4585 | unresolved via approximate-none → () | none |
| `Ganesan Selvam` | ls-4963 | unresolved via approximate-none → () | none |
| `Sunil Dattatray Tatkare` | ls-5199 | unresolved via approximate-none → () | none |
| `V. Kalanidhi` | ls-4959 | unresolved via approximate-none → () | none |

**Assertions overriding a different resolved member: 0.** All four land on forms the matcher
left `unresolved`, so the unconditional-override rule is **untested in practice** on this
window. It is a rule whose behaviour has never been exercised, which is a weaker position than
"verified correct" and should be read as such.

## Blocking finding for T051: the derived `question_id` is not unique

Not a matcher property, but this is the first pass over all 95,269 records and the check was
free. `route-capture.md` left it open: *"`quesNo` uniqueness is observed **within one session
only** (250 records, 0 duplicates)."* Over the full window it does not hold.

| Term | Records | distinct `(lokNo, sessionNo, quesNo)` | + `type` | + `type` + `date` |
|---|---:|---:|---:|---:|
| 18th LS | 34,720 | 31,945 (**2,775** collisions) | 34,720 (0) | 34,720 (0) |
| 17th LS | 60,549 | 55,893 (**4,656** collisions) | 60,548 (1) | 60,548 (1) |

**7,431 records collide onto an already-used `question_id`.** `sansad.ingest.questions`
derives identity as `(lokNo, sessionNo, quesNo)`, so 7.8% of the window currently shares an id
with a different question.

**Cause, VERIFIED**: `quesNo` is numbered **per (session, type)** — `STARRED` and `UNSTARRED`
are separate series. Of 2,775 colliding composites in the 18th LS, **0** have records sharing
the same `type`; adding `type` to the composite removes every collision there and all but one
in the 17th.

**The one residual collision is a genuine upstream duplicate**: `(17, 4, 2204, UNSTARRED,
23.09.2020)` is served **twice as a byte-identical record**. Two copies of one question, not
two questions.

**Why this blocks T051 rather than merely annoying it.** Contract guarantee 6 is *"a
`question_id` appearing in several files is **one** question: a consumer combining partitions
must de-duplicate on `question_id` rather than sum across them."* With a non-unique id, a
consumer following that instruction merges two different questions, and the by-member and
by-ministry partitions T051 writes would overwrite or conflate 7,431 records. T039's
`test_guarantee_6_…` is one of the tests still failing on the missing partitions module, so
nothing currently catches it.

**Not fixed here.** Fixing it means changing `question_id_for` and `session_id_for`'s
composite, which changes every published id — a breaking change under the dataset's own
breaking-change policy ("A change is breaking if it … reassigns an existing `member_id`"; the
same logic applies to `question_id`), and `data/published/` has never been written, so now is
the cheapest possible moment to make it. It is the owner's call and it belongs with T051, not
smuggled into a verification run.

## Reproducing this

```
export SANSAD_SCRATCH=<a path outside the repository>
python tools/check_equivalence.py
```

Exit code 0 means all three figures reproduce, no form disagrees, the pool rule agrees and no
assertion overrides a different resolved member. It currently exits **1**, on the assertion
figure alone. The expected values in the tool are the spike's **published** figures and are
left unchanged, so the check keeps reporting this discrepancy until the owner decides which
number is the correct one to publish.

---

## Full tool output

```
# Matcher equivalence: `src/sansad/resolve` against `spike/resolve_rate.py`

- scratch root: `/private/var/folders/n7/7grqlws55f5_1cz_kkqzxnjw0000gn/T/sansad-scratch` (outside the repository; nothing written)
- roster records read: **5426**
- assertions loaded from `data/assertions/`: **4**

## The three result lines

| Configuration | Produced | Rate | Spike | Rate | Agrees |
|---|---:|---:|---:|---:|:--:|
| containment OFF | 86,352 / 95,269 | **90.64%** | 86,352 / 95,269 | 90.64% | YES |
| containment ON | 90,299 / 95,269 | **94.78%** | 90,299 / 95,269 | 94.78% | YES |
| containment ON + four assertions | 91,797 / 95,269 | **96.36%** | 91,708 / 95,269 | 96.26% | **NO** |

## Per term, so a mismatch has an address

| Term | Pool (lsExpr) | Questions | No asker field | OFF | spike | ON | spike |
|---|---:|---:|---:|---:|---:|---:|---:|
| 18th LS | 544 | 34,720 | 4 | 34,610 | 34,610 | 34,716 | 34,716 |
| 17th LS | 559 | 60,549 | 0 | 51,742 | 51,742 | 55,583 | 55,583 |

**Pool-rule control**: 0 of 1103 pooled member(s) where `sansad.ingest.members`' term list differs from the spike's `lsExpr` parse. Non-zero would mean the production ingest and the spike disagree about who was eligible, independently of any matcher behaviour.

## Derived question identity, checked over the full window

Not a matcher property, but this is the first run over all 95,269 records and the check costs nothing. `route-capture.md` left it open: *"`quesNo` uniqueness is observed **within one session only** (250 records, 0 duplicates)"*.

| Term | Records | distinct (lokNo, sessionNo, quesNo) | + type | + type + date |
|---|---:|---:|---:|---:|
| 18th LS | 34,720 | 31,945 (2,775 collisions) | 34,720 (0) | 34,720 (0) |
| 17th LS | 60,549 | 55,893 (4,656 collisions) | 60,548 (1) | 60,548 (1) |

**The composite `sansad.ingest.questions` derives is NOT unique: 7,431 record(s) collide onto an already-used id.** Adding `type` leaves 1. Reported, not fixed -- see `spike/matcher-equivalence.md`.

## Per-form disagreements

**containment OFF** -- 0 disagreement(s) over 972 distinct forms.

**containment ON** -- 0 disagreement(s) over 972 distinct forms.

**Total disagreement count: 0.**

## Would any assertion have overridden a different automatic match?

T048 lets a maintainer assertion win unconditionally -- including over a *confident* automatic match. Expected: none of the four lands on a form the matcher already resolved, because all four are residual forms it failed on. This is the check for that.

| Assertion form | asserted member | automatic outcome | conflict |
|---|---|---|---|
| `D.K. Suresh` | ls-4585 | unresolved via approximate-none -> () | none |
| `Ganesan Selvam` | ls-4963 | unresolved via approximate-none -> () | none |
| `Sunil Dattatray Tatkare` | ls-5199 | unresolved via approximate-none -> () | none |
| `V. Kalanidhi` | ls-4959 | unresolved via approximate-none -> () | none |

**Assertions overriding a different resolved member: 0.**

## Where the assertion figure differs, decomposed

The spike's rule, verbatim: *"counting those whose **every** residual asker is one of the four confirmed forms"*. That is the rule implemented in `sansad.resolve.status_for_question`. Below, the questions that rule recovers, grouped by **how many** of the four block each one -- because a method that scores one asserted form at a time cannot recover a question that two of them block together, and that is where a per-form computation and a per-question one part.

| Questions recovered, by how many of the four block them | Count |
|---|---:|
| exactly one asserted form residual | 1,411 |
| 2 asserted forms residual | 87 |
| **total recovered** | **1,498** |

- spike's published recovered figure: **1,409**
- recovered by exactly one assertion: **1,411** (per-form sets are disjoint here)
- recoverable only by two assertions together: **87** -- invisible to a per-form method
- unaccounted remainder: **2**

## Verdict

**MISMATCH.** See the tables above. The matcher is NOT to be changed to close a
gap found here -- a difference is a finding about the port, and its cause belongs
in `spike/matcher-equivalence.md` before anything is edited.
```
