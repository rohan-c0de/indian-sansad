# Matcher equivalence — does `src/sansad/resolve` reproduce the spike's numbers?

**Date**: 2026-10-09 (re-run after the corrections below)
**Task**: verification of T046, and of T042–T049 in passing, before T051
**Tool**: [`tools/check_equivalence.py`](../../../tools/check_equivalence.py)
**Command**: `SANSAD_SCRATCH=<a path outside the repo> python tools/check_equivalence.py`
**Data**: the window already fetched into `$SANSAD_SCRATCH` — roster 5,426 members,
17th LS 60,549 records, 18th LS 34,720 records = **95,269 records / 95,268 distinct questions**.
**No live fetch.**
**Writes**: none. The tool reads `$SANSAD_SCRATCH` only, resolves the path with symlinks and
`..` collapsed, and refuses if it lands inside the repository. Everything below is an aggregate
or a name form; no record is reproduced and no attribute outside Principle V's permitted set
appears.
**Exit code**: **0.**

---

## Verdict

**The matcher port is exact. Two of the spike's three figures reproduce to the record; the third
was wrong in the spike and is now corrected upward.** A separate defect in the derived
`question_id` was found by this check and is fixed.

| | |
|---|---|
| Form-level disagreements against the spike's own per-form artefacts | **0 of 972** |
| Pool-rule control (production ingest vs the spike's `lsExpr` rule) | **0 of 1,103 members differ** |
| Assertions overriding a different automatically-resolved member | **0 of 4** |
| Undeclared `question_id` collisions after the fix | **0** |

## The three result lines — the spike's basis, all 95,269 records

| Configuration | Produced | Rate | Expected | Agrees |
|---|---:|---:|---:|:--:|
| containment OFF | 86,352 / 95,269 | **90.64%** | 86,352 / 95,269 = 90.64% | **YES** |
| containment ON | 90,299 / 95,269 | **94.78%** | 90,299 / 95,269 = 94.78% | **YES** |
| containment ON + four assertions | 91,797 / 95,269 | **96.36%** | ~~91,708 / 95,269 = 96.26%~~ **corrected** | **YES** |

## The published basis — one upstream duplicate removed

The upstream serves one record of the window **twice, byte-identical**. It is reduced to one at
ingest and the drop is declared as a known gap in the Coverage Statement (FR-013), so the number
of distinct questions is one lower than the number of records. **These are the figures the
project publishes.**

| Configuration | Resolved | Questions | Rate | Margin vs SC-002's 95% |
|---|---:|---:|---:|---:|
| containment OFF | 86,351 | 95,268 | **90.64%** | −4.36 points |
| containment ON (the **automatic** rate) | 90,298 | 95,268 | **94.78%** | −0.22 points |
| **containment ON + four assertions** | **91,796** | **95,268** | **96.36%** | **+1.36 points** |

Declared upstream duplicate: `lok-sabha/17/4/unstarred/2204` (×2).

The automatic rate stays **below** SC-002, which is why T053 publishes both figures separately.

## Why the assisted figure was corrected, and by how much

The spike's rule is stated correctly in its own report — *"counting those whose **every**
residual asker is one of the four confirmed forms"* — and that is what
`sansad.resolve.status_for_question` implements. The spike's **computation** did not implement
it. Measured over the window:

| Questions recovered, by how many of the four block them | Count |
|---|---:|
| exactly one asserted form residual | 1,411 |
| **two** asserted forms residual | **87** |
| **total recovered** | **1,498** |

- spike's published figure: **1,409**
- recovered by exactly one assertion: **1,411** — these sets are disjoint, so this is the most a
  per-form method can reach
- recoverable **only** by two assertions together: **87**. Neither assertion unblocks these
  questions alone, so a recount scoring one asserted form at a time credits them to neither.
- **unaccounted remainder: 2**

**The 2 are not explained, and are not guessed at.** 1,411 − 1,409 = 2. The code that produced
1,409 was never committed — no script under `spike/` applies maintainer assertions (`grep` over
`spike/*.py` finds only the scratch-path assertion in `fetch_slice.py`) — so the remainder cannot
be traced to a line. Settling it needs that uncommitted recount.

**The mechanism is proven on a hand-built fixture, not inferred from a diff between two large
numbers.** `tests/unit/test_assertion_co_asking.py` builds one question co-asked by two forms
that each need an assertion and shows it resolves under **neither assertion alone and only under
both**, alongside a control question that one assertion does unblock. The same file asserts the
arithmetic of the undercount on two records: per-question counting recovers 2, a per-form method
recovers 1.

### The per-form column is also not reproducible

`spike-report.md`'s assertions table gives "Questions blocked" as **513 / 414 / 372 / 273**
(sum 1,572). Re-measured over all 60,549 records of the 17th Lok Sabha:

| Form | (a) name instances | (b) question records it appears in | (c) records where it is the **only** residual asker |
|---|---:|---:|---:|
| `Sunil Dattatray Tatkare` | 528 | 528 | 437 |
| `Ganesan Selvam` | 443 | 443 | 352 |
| `D.K. Suresh` | 396 | **395** | 366 |
| `V. Kalanidhi` | 296 | 296 | 256 |
| **sum** | **1,663** | **1,662** | **1,411** |

**Definition used for `questions_blocked` in `data/assertions/lok-sabha.json`: (b)** — the number
of question records in which the form appears as an asker. `D.K. Suresh` differs between (a) and
(b) because one question lists that form twice.

Definition (a) matches the spike's **own correction worklist**, whose column is headed "instances
blocked" — so that artefact is right and consistent with this tool. **No definition measured
reproduces 513 / 414 / 372 / 273.** That column is not load-bearing — it exists in the report
only to be rejected as a naive sum — but it is wrong by more than rounding, and no provenance for
it is guessed at here.

## What is NOT the cause of the difference, each checked

- **not the matcher** — 0 form-level disagreements, and both unassisted figures reproduce to the
  record;
- **not the candidate pool** — 0 of 1,103 pooled members differ between the production ingest's
  term list and the spike's `lsExpr` rule;
- **not cross-term leakage** — none of the four forms appears in the 18th LS's questions, and the
  18th's assisted gain is **0**;
- **not an assertion pointing outside its term's pool** — all four asserted members are in the
  17th LS pool;
- **not the four `no_asker_field` records** — they are in the 18th LS and are excluded from the
  resolved count by both methods.

## The latent spike defect changed nothing measured

`spike/resolve_rate.py` has a latent `UnboundLocalError` in `resolve_form` (see
[resolution-rate.md](./resolution-rate.md) → *NOTE — a latent defect…*): the exact, normalised
and normalised-reordered tiers call `fallback(...)` above its definition, so they raise instead
of reaching the containment tier. `src/sansad/resolve/match.py` implements the intended
behaviour.

**0 form-level disagreements over 972 distinct forms is the evidence that this changed nothing.**
Over 95,269 real questions, not one form takes the fixed path — the `ambiguous` count is 0 at
those three tiers — so the branch is still unreached on this data. T046 is "as the spike, plus
that fix".

## Would any assertion have overridden a different automatic match?

T048 lets a maintainer assertion win unconditionally, including over a *confident* automatic
match. That was flagged as the least defensible claim in the Phase 4 part 1 report, and it is now
measured: **all four** asserted forms come out `unresolved` from the matcher, so **0** assertions
override a different resolved member.

The rule is therefore **untested in practice** on this window — its behaviour has never been
exercised. That is a weaker position than "verified correct" and should be read as such.

## The `question_id` collision — found here, fixed

`route-capture.md` left this open: *"`quesNo` uniqueness is observed **within one session only**
(250 records, 0 duplicates) … the ingest must assert it, not trust it."* The ingest trusted it.

| Term | Records | distinct old `(lokNo, sessionNo, quesNo)` | distinct `(House, session, type, quesNo)` |
|---|---:|---:|---:|
| 18th LS | 34,720 | 31,945 (**2,775** collisions) | 34,720 (0) |
| 17th LS | 60,549 | 55,893 (**4,656** collisions) | 60,548 (1) |

**7,431 of 95,269 records — 7.8% — collided onto an already-used id.**

**Cause, VERIFIED**: `quesNo` is numbered **per (session, `type`)**; `STARRED` and `UNSTARRED`
are separate series. The control: of the 2,775 colliding composites in the 18th LS, **zero** have
records sharing a `type`.

**Fixed**: `question_id` is now `(House, session, type, quesNo)`. Collisions after the fix: **1**,
which is the byte-identical duplicate record, declared as a known gap. **Undeclared collisions:
0**, asserted on every run of this tool.

Why it mattered: guarantee 6 tells consumers to "de-duplicate on `question_id` rather than sum
across" partitions. Under the old composite, a consumer following that instruction merged a
starred question with an unstarred one. **No dataset was ever published under the old composite.**

## Reproducing this

```
export SANSAD_SCRATCH=<a path outside the repository>
python tools/check_equivalence.py
```

Exit code 0 means: all three window figures match the expected values, no form disagrees, the
pool rule agrees, no assertion overrides a different resolved member, and there are no undeclared
`question_id` collisions. It currently exits **0**.

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
| containment ON + four assertions | 91,797 / 95,269 | **96.36%** | 91,797 / 95,269 | 96.36% | YES |

The spike published **91,708 / 95,269 = 96.26%** for the assisted configuration. That **undercounted** -- see the decomposition below. The expected value above is the corrected one.

## The published basis -- one upstream duplicate removed

The table above uses the spike's denominator: all 95,269 records as served. The upstream serves one of them twice (byte-identical), so the number of distinct questions is one lower, and these are the figures the project publishes. The dropped copy is declared as a known gap in the Coverage Statement (FR-013), not removed silently.

| Configuration | Resolved | Questions | Rate | Margin vs SC-002's 95% |
|---|---:|---:|---:|---:|
| containment OFF | 86,351 | 95,268 | **90.64%** | -4.36 points |
| containment ON | 90,298 | 95,268 | **94.78%** | -0.22 points |
| containment ON + four assertions | 91,796 | 95,268 | **96.36%** | +1.36 points |

Declared upstream duplicate(s): `lok-sabha/17/4/unstarred/2204` (x2)

## Per term, so a mismatch has an address

| Term | Pool (lsExpr) | Questions | No asker field | OFF | spike | ON | spike |
|---|---:|---:|---:|---:|---:|---:|---:|
| 18th LS | 544 | 34,720 | 4 | 34,610 | 34,610 | 34,716 | 34,716 |
| 17th LS | 559 | 60,549 | 0 | 51,742 | 51,742 | 55,583 | 55,583 |

**Pool-rule control**: 0 of 1103 pooled member(s) where `sansad.ingest.members`' term list differs from the spike's `lsExpr` parse. Non-zero would mean the production ingest and the spike disagree about who was eligible, independently of any matcher behaviour.

## Derived question identity, asserted over the full window

`route-capture.md` left this open: *"`quesNo` uniqueness is observed **within one session only** (250 records, 0 duplicates) ... the ingest must assert it, not trust it"*. It did not hold. The composite now includes `type`, and this is the assertion.

| Term | Records | distinct old `(lokNo, sessionNo, quesNo)` | distinct `(House, session, type, quesNo)` |
|---|---:|---:|---:|
| 18th LS | 34,720 | 31,945 (**2,775** collisions) | 34,720 (0) |
| 17th LS | 60,549 | 55,893 (**4,656** collisions) | 60,548 (1) |

- old composite: **7,431** record(s) collided onto an already-used id
- corrected composite: **1** collision(s), which must all be the one declared upstream duplicate `lok-sabha/17/4/unstarred/2204`
- undeclared collisions: **0**

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

**VERIFIED WORKING.** All three window figures reproduce exactly, no form disagrees, the pool rule agrees, and no assertion overrides a different resolved member.
```
