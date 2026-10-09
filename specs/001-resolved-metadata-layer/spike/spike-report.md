# Spike Report — the Phase 2 gate

**Feature**: `specs/001-resolved-metadata-layer`
**Date**: 2026-10-09
**Status**: **this file is the gate. No Phase 3 task may begin until it exists.** It does.

Every verdict below carries one of `VERIFIED WORKING | VERIFIED BROKEN | UNVERIFIED | UNTESTABLE
| NOT PRESENT`, with the producing output pasted in the linked file. No figure here is a
paraphrase, and a single successful observation is recorded as "observed once" rather than as a
general property.

---

# T014 — the SC-002 decision

## Decision: **SC-002 is MET. No amendment to `spec.md` is required and none is requested.**

SC-002: *"At least 95% of in-scope questions resolve to exactly one member identity, and 100% of
the remainder are visibly marked unresolved rather than absent."*

| Configuration | Measured (per question) | SC-002 target | Outcome |
|---|---|---|---|
| **18th-LS candidate pool** — the operative configuration | **99.68%** | 95% | **MET, +4.68 points** |
| **Full-roster pool** — the pessimistic bound | **98.06%** | 95% | **MET, +3.06 points** |

**The target is met under both configurations, including the one that deliberately withholds a
disambiguator the real pipeline will have.** T014 requires a stop for the owner's decision only
if the measured rate is *below* 95%; it is above under every reading of the metric, so no
decision is owed and the two remedies T014 names — amend SC-002 downward, or close a gap with
maintainer assertions — are both moot.

Evidence: [`resolution-rate.md`](./resolution-rate.md) T012. Denominator **34,720 questions** —
the complete 18th Lok Sabha, not a sample. Measured against a matcher whose thresholds were fixed
before the first run, with the prototype emitting `tuned_after_seeing_results: false`.

### All three readings of SC-002 clear the bar

SC-002's wording is ambiguous for co-asked questions, so all three readings are reported rather
than one being chosen silently:

| Reading | Denominator | `ls18` pool | `full` pool |
|---|---|---|---|
| per **question**, every asker must resolve (strictest) | 34,720 | **99.68%** | **98.06%** |
| per **name instance** | 57,124 | 99.81% | 98.83% |
| per **distinct name form** | 467 | 99.79% | 98.72% |

The strictest reading is quoted as the headline.

### What the spec should arguably still change — flagged, not actioned

`spec.md` Assumptions records that *"The 95% resolution threshold in SC-002 is a
reasonable-default assumption ... it should be revisited once real resolution rates are known."*
Real rates are now known, and they are **4.7 points above** the invented default.

That cuts the opposite way from the gap T014 was written to handle: the target may be too
**lenient**, not too strict. A 95% floor permits 1,736 of these 34,720 questions to go
unresolved; the measured figure leaves **106**. Publishing against a target 16× looser than
measured performance means a future regression could degrade resolution by an order of magnitude
and still pass.

**No change is made here**, for two reasons, and both are reasons rather than hesitation:

1. **T014's mandate is narrow** — record met or stop for a decision. Raising a success criterion
   is not within it, and tightening a target to match one term's measurement would be the mirror
   image of the tuning T012 forbids.
2. **The 17th Lok Sabha is unmeasured** — 60,549 questions, 64% of the covered window. A floor
   raised on 36% of the data would be an invented default again, just a better-informed one.

Recorded for the owner as an open item: **once the 17th Lok Sabha is measured, SC-002's 95%
should be revisited upward.** That is the decision this spike actually surfaces, and it is the
owner's, not this report's.

### The second clause of SC-002 is not measured and is not claimed

*"...and 100% of the remainder are visibly marked unresolved rather than absent."*

**NOT MEASURED.** Nothing has been published, so nothing has been marked anything. This is a
property of published output, tested by `quickstart.md` scenario 2 in Phase 4. The 99.68% figure
speaks only to the first clause.

### One limit on the figure itself, stated plainly

**The rate measures the coverage of matching, not its correctness.** A name form that matched
exactly to one member is counted resolved; **no sample was hand-checked against the real
person.** So the *precision* of 99.68% is **UNVERIFIED** — only its coverage is measured. A
systematic mis-join, such as two roster entries that are themselves wrong, would be invisible to
this measurement. `quickstart.md` scenario 4 (`make verify-joins`) is the check that addresses
it, and it is Phase 4 work.
