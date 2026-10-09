# Spike item 3 — the measured resolution rate and its correction cost

**Tasks**: T012 (the rate) · T013 (the hand-correction cost)
**Date**: 2026-10-09
**Prototype**: `spike/resolve_rate.py` (T011), deliberately outside `src/`
**Slice fetched by**: `spike/fetch_slice.py` into `$SANSAD_SCRATCH`

---

# T012 — the resolution rate

## Verdict: VERIFIED WORKING. SC-002's 95% is met, with room, under both configurations.

| Configuration | Resolved (by question) | Ambiguous | Unresolved | vs SC-002's 95% |
|---|---|---|---|---|
| **18th-Lok-Sabha candidate pool** (the operative one) | **99.68%** | 0.00% | 0.31% | **met, +4.68 points** |
| **Full-roster pool** (the pessimistic bound) | **98.06%** | 1.62% | 0.31% | **met, +3.06 points** |

`plan.md` Risk 3 calls identity resolution the recommendation's least defensible assumption, and
the assessment records a practitioner who needed fuzzy matching and still called it difficult.
**On this route, for this slice, it was not difficult.** The reason is specific and is the single
most useful finding in this file:

> **460 of 467 distinct asker name forms matched the roster EXACTLY, verbatim, with no
> normalisation at all. The approximate-matching tier resolved nothing whatsoever — zero forms,
> zero instances.**

## The slice

| | |
|---|---|
| House | Lok Sabha |
| Term | 18th |
| **Sessions actually present** | **2, 3, 4, 5, 6, 7, 8 — session 1 is ABSENT** (see the coverage gap below) |
| Questions in slice | **34,720** — the complete term; `totalRecordSize` was 34,720 and 34,720 records were written (`complete=YES`) |
| Date span | **2024-07-22 → 2026-08-12**, 751 days, **107.3 weeks** |
| Questions per session | 2: 3,499 · 3: 4,749 · 4: 6,250 · 5: 5,248 · 6: 3,499 · 7: 6,975 · 8: 4,500 |
| Asker name instances | **57,124** |
| Distinct asker name forms | **467** |
| Roster, full | 5,426 members → 16,135 indexed name variants → 10,470 normalised keys |
| Roster, 18th-LS pool | **544** members → 1,629 indexed name variants → 1,090 normalised keys |

### A defect in my own tooling, corrected rather than published

`spike/resolve_rate.py` reports `date_min` and `date_max` by **string** comparison. The upstream
serves dates as `DD.MM.YYYY`, so a string sort is meaningless on them — it returned
`01.04.2025` and `31.07.2026`, which are neither the earliest nor the latest date in the slice.

The figures in the table above are the **parsed** minimum and maximum: **2024-07-22** and
**2026-08-12**. The difference is not cosmetic — the string-sorted span is 487 days against a
true 751, so every per-week rate derived from it would have been overstated by about 54%. The
script's own output is left uncorrected in the verbatim block below, with this note attached,
because editing a tool's recorded output to match a later correction is how a defect gets lost.

### Closed by this slice: the date format (T006 open item 1)

**Every one of the 34,720 records uses the single shape `NN.NN.NNNN`** — zero exceptions, zero
unparseable values. The format is **`DD.MM.YYYY`, not ISO-8601.**

This matters more than a format note. FR-013 requires questions dated outside the covered window
to be excluded and the exclusion reflected in the Coverage Statement rather than passing
silently. `DD.MM.YYYY` parsed as ISO or as `MM/DD/YYYY` does not raise — it silently yields the
wrong date for every day ≤ 12, which is 40% of dates. That is precisely a silent mis-scoping of
the FR-013 exclusion. Phase 3 must assert the format rather than infer it.

### A coverage gap found by measuring: session 1 of the 18th Lok Sabha has ZERO questions

The session enumeration (`route-capture.md`) lists the 18th Lok Sabha as sessions **1–8** with
sitting days 7, 15, 20, 27, 21, 15, 28, 0. The question route, asked for the whole term, returns
**no session-1 records at all** — the 34,720 are distributed across sessions 2–8 only.

Session 1 of a new Lok Sabha is the constitutive sitting — members sworn in, Speaker elected —
and plausibly holds no Question Hour. **Plausibly is not a finding, and this is not recorded as
one.** The cause is **UNVERIFIED**.

Two anomalies now sit at the two ends of this term and they point opposite ways:

| Session | Sitting days | Questions | |
|---|---|---|---|
| 1 | 7 | **0** | days but no questions |
| 8 | **0** | 4,500 | questions but no days |

Both must be declared under FR-013 rather than smoothed over. A coverage statement that says
18th Lok Sabha, sessions 1–8 while holding nothing for session 1 is the kind of implied coverage
FR-013 exists to prevent.

## Matcher configuration — fixed before the first run

T012 says: do not tune the matcher to reach 95%. Every value below was chosen on stated grounds
in the prototype's docstring **before any rate was observed**, and none was changed afterwards.
`tuned_after_seeing_results` is emitted as `false` by the script itself.

| Setting | Value | Why this value |
|---|---|---|
| Tier order | exact → normalised → normalised-reordered → approximate | Stops at the first tier producing a candidate; a later tier never overrides an earlier one. |
| `APPROX_THRESHOLD` | **0.90** | `difflib.SequenceMatcher` ratio on normalised forms. The conventional near-identical cut, high enough not to merge two people sharing a surname. Not selected by trying several. |
| `APPROX_MARGIN` | **0.02** | If the best candidate beats the runner-up by less than this, the result is `ambiguous`. Required by `data-model.md`: an ambiguous match MUST NOT be silently collapsed to the first candidate. |
| Honorifics stripped | 39 forms (`shri`, `shrimati`, `smt`, `dr`, `prof`, `kumari`, `thiru`, …) | 98.1% of asker forms carry one (`route-capture.md`) and an honorific is not part of an identity. |
| Honorifics **not** stripped | **`md`, `mohd`** | Deliberate. These are frequently part of a given name rather than a title; stripping them would corrupt real names to flatter the rate. |
| Name variants indexed per member | `mpFirstLastName`, `mpLastFirstName`, `initial+firstName+lastName`, `firstName+lastName` | The roster's own forms plus two constructions. |
| `member_id` | `ls-<mpsno>` | `data-model.md` requires an id never derived from a name. |

### Why two candidate pools, and which one counts

The roster is **every Lok Sabha member since the 1st — 5,426 people, of whom 544 sat in the
18th.** Matching an 18th-Lok-Sabha question against all 5,426 puts 4,882 people in the pool who
could not possibly have asked it.

Both were measured and both are reported, so neither can be picked after the fact. **The
restricted pool is the operative figure** and the reason is not performance:

> All five ambiguous forms in the full-pool run are **genuinely two different people**, and the
> term restriction separates them correctly.

| Name form | Candidate A | Candidate B |
|---|---|---|
| `Dr. Bhola Singh` | `ls-4475` — 16th LS, Died, **Bihar, Begusarai**, 2 terms | `ls-4605` — **18th LS, Sitting**, Uttar Pradesh, Bulandshahr, 3 terms |
| `Shri Rajesh Verma` | `ls-510` — 17th LS, Former, **Uttar Pradesh, Sitapur**, 4 terms | `ls-5605` — **18th LS, Sitting**, Bihar, Khagaria, 1 term |
| `Shri Virendra Singh` | `ls-3608` — 17th LS, Former, Uttar Pradesh, **Ballia**, 4 terms | `ls-5651` — **18th LS, Sitting**, Uttar Pradesh, Chandauli, 1 term |
| `Shri Manoj Kumar` | `ls-4162` — 14th LS, Former, **Jharkhand, Palamu**, 1 term | `ls-5578` — **18th LS, Sitting**, Bihar, Sasaram, 1 term |
| `Smt. Veena Devi` | `ls-4684` — 16th LS, Former, Bihar, **Munger**, 1 term | `ls-5223` — **18th LS, Sitting**, Bihar, Vaishali, 2 terms |

In every pair exactly one candidate sat in the 18th Lok Sabha. This is `data-model.md`'s rule
working as written — two members with identical or near-identical names MUST NOT be merged;
distinctness is decided on attributes beyond the name — and `lastLoksabha` is such an attribute.

**So the 98.06% full-pool figure is an artefact of deliberately withholding a disambiguator the
real pipeline will obviously have**, not a measurement of the achievable rate. It is kept as the
pessimistic bound because a bound derived by removing information is honest, whereas quietly
reporting only the better number would not be. `data-model.md` already requires the stronger
version of this restriction — a question attributed to a member not sitting on its date MUST be
flagged rather than silently re-attributed — which is date-scoped rather than term-scoped and
would resolve these five without any name matching at all.

## Which tier did the work — the finding that reframes the problem

Identical under both pools:

| Tier | Distinct forms | Name instances |
|---|---|---|
| **exact** (verbatim, no normalisation) | **460** | **56,241** |
| **normalised** (honorifics and punctuation stripped) | 6 | 777 |
| normalised-reordered | 0 | 0 |
| **approximate** (fuzzy, ≥0.90) | **0** | **0** |
| reached approximate and still failed | 1 | 106 |

**The fuzzy matcher that FR-002 makes load-bearing, and that `research.md` chose Python for,
resolved nothing.** 98.5% of forms matched byte-for-byte; the remaining 1.3% needed nothing more
than honorific stripping.

**This does not mean fuzzy matching is unnecessary — it means its necessity is unevidenced on
this route.** Three reasons not to delete it on the strength of this:

1. This is the **18th Lok Sabha only**. The 17th is 60,549 questions — 1.75× larger — and has
   not been measured at all. An older term is exactly where upstream name hygiene is likelier to
   be worse.
2. `route-capture.md` found **zero comma-inverted forms** on the question route, while the
   roster's `mpLastFirstName` is comma-inverted in **5,423 of 5,426** records. The two sources
   use different conventions; a route or term that mixes them is where fuzzy matching would earn
   its place.
3. One form failed *because* the approximate threshold was too strict — see T013.

## SC-002 and FR-002, as the spec words them

SC-002 requires at least 95% of in-scope questions to resolve to exactly one member identity,
and 100% of the remainder to be visibly marked unresolved rather than absent.

- **First clause: met.** 99.68% (operative) / 98.06% (pessimistic).
- **Second clause: not measured here.** Nothing has been published yet, so nothing has been
  marked anything. It is a publication property, tested by `quickstart.md` scenario 2 in Phase 4.

**SC-002 is ambiguous for co-asked questions** and the three readings differ, so all three are
reported rather than one being chosen silently:

| Reading | Denominator | Pool `ls18` | Pool `full` |
|---|---|---|---|
| per **question**, all askers must resolve | 34,720 | **99.68%** | **98.06%** |
| per **name instance** | 57,124 | 99.81% | 98.83% |
| per **distinct name form** | 467 | 99.79% | 98.72% |

The per-question reading is the strictest and is the one quoted as the headline. A question with
46 askers counts as unresolved if any single one of them fails — the conservative treatment, and
it matches FR-003's insistence that a co-asked question carry *every* asker.

## Asker multiplicity — the factor `research.md` records as never measured, now measured

| | |
|---|---|
| Questions | 34,720 |
| Name instances | 57,124 |
| **Mean askers per question** | **1.6453** |
| Median | **1** |
| **Maximum** | **46** |
| Questions with no asker at all | **4** |

Distribution: 1 asker 27,473 · 2 askers 3,745 · 3 askers 1,178 · 4 askers 642 · 5 askers 445 ·
then a long thin tail out to 46.

**The mean has risen at every sample size and only now has a complete denominator:**

| Sample | Mean | Max |
|---|---|---|
| 50 records (`route-capture.md`) | 1.32 | 6 |
| 250 records (`route-capture.md`) | 1.504 | 20 |
| **34,720 records — the whole term** | **1.6453** | **46** |

1.6453 is a **measurement over a complete term**, not another sample, so T017 may use it for the
18th Lok Sabha. It is **not** established for the 17th, which has not been fetched.

**The maximum, 46, is the number that matters for published size**, not the mean: a 46-asker
question is written into 46 per-member files in each of two formats, i.e. 92 copies.

**Four questions carry no asker field at all.** `route-capture.md` reported `member` non-null on
250 of 250 and inferred nothing further; over the full term the empty case does exist, at
4/34,720. `data-model.md` already handles it — `asking_members` may be empty with
`resolution_status` set — and these four are counted as `no_asker_field`, neither dropped nor
counted as resolved.

## Verbatim output — restricted pool (operative)

```
 "roster": {
  "members": 544,
  "distinct_name_variants_indexed": 1629,
  "distinct_normalised_keys": 1090
 },
 "matcher_config": { ... "candidate_pool": "18th Lok Sabha only (lastLoksabha == 18)",
  "tuned_after_seeing_results": false },
 "asker_multiplicity": {
  "questions": 34720,
  "name_instances": 57124,
  "mean_askers_per_question": 1.6453,
  "median_askers_per_question": 1.0,
  "max_askers_per_question": 46
 },
 "rate_by_distinct_name_form": {
  "denominator": 467, "resolved": 466, "resolved_pct": "99.79%",
  "ambiguous": 0, "ambiguous_pct": "0.00%",
  "unresolved": 1, "unresolved_pct": "0.21%"
 },
 "rate_by_name_instance": {
  "denominator": 57124, "resolved": 57018, "resolved_pct": "99.81%",
  "ambiguous": 0, "ambiguous_pct": "0.00%",
  "unresolved": 106, "unresolved_pct": "0.19%"
 },
 "rate_by_question_all_askers_resolved": {
  "denominator": 34720, "resolved": 34610, "resolved_pct": "99.68%",
  "ambiguous": 0, "ambiguous_pct": "0.00%",
  "unresolved": 106, "unresolved_pct": "0.31%",
  "no_asker_field": 4
 },
 "which_tier_did_the_work": {
  "by_distinct_form": { "exact": 460, "normalised": 6, "approximate-none": 1 },
  "by_name_instance": { "exact": 56241, "normalised": 777, "approximate-none": 106 }
 },
 "sc_002_comparison": {
  "target": "95% of in-scope questions resolve to exactly one member identity",
  "measured_by_question": "99.68%",
  "measured_by_name_instance": "99.81%",
  "measured_by_distinct_form": "99.79%"
 }
```

Note the `slice` block as the script emitted it, **with its defect**:

```
 "slice": { "house": "Lok Sabha", "loksabha": 18,
  "sessions_present": ["2","3","4","5","6","7","8"],
  "questions_in_slice": 34720,
  "date_min": "01.04.2025",
  "date_max": "31.07.2026" }
```

`date_min` / `date_max` are **wrong** — string-sorted `DD.MM.YYYY`. True span 2024-07-22 →
2026-08-12. Left as emitted, per the note above.

## Verbatim output — full-roster pool (pessimistic bound)

```
 "roster": {
  "members": 5426,
  "distinct_name_variants_indexed": 16135,
  "distinct_normalised_keys": 10470
 },
 "matcher_config": { ... "candidate_pool": "FULL roster, no term restriction (5,426 members)" },
 "rate_by_distinct_name_form": {
  "denominator": 467, "resolved": 461, "resolved_pct": "98.72%",
  "ambiguous": 5, "ambiguous_pct": "1.07%",
  "unresolved": 1, "unresolved_pct": "0.21%"
 },
 "rate_by_name_instance": {
  "denominator": 57124, "resolved": 56453, "resolved_pct": "98.83%",
  "ambiguous": 565, "ambiguous_pct": "0.99%",
  "unresolved": 106, "unresolved_pct": "0.19%"
 },
 "rate_by_question_all_askers_resolved": {
  "denominator": 34720, "resolved": 34046, "resolved_pct": "98.06%",
  "ambiguous": 564, "ambiguous_pct": "1.62%",
  "unresolved": 106, "unresolved_pct": "0.31%",
  "no_asker_field": 4
 },
 "sc_002_comparison": {
  "measured_by_question": "98.06%",
  "measured_by_name_instance": "98.83%",
  "measured_by_distinct_form": "98.72%"
 }
```

## What T012 does not establish

1. **The 17th Lok Sabha is unmeasured.** It is 60,549 questions, 1.75× this slice, and 64% of
   the covered window. The headline rate is for the 18th only.
2. **Rajya Sabha: not attempted.** Unchanged.
3. **No fuzzy matching was exercised**, so the 0.90 threshold is untested in the direction that
   matters: nothing was accepted by it, and exactly one thing was rejected by it (T013).
4. **A single run.** The upstream carries no contract or versioning; name hygiene could change.
5. **The rate is of matching against the roster, not of correctness.** A form that matched
   exactly to one member is counted resolved. **No sample was checked by hand against the real
   person**, so the *precision* of the 99.68% is unverified — only its coverage. A systematic
   mis-join (for instance two members whose roster entries are themselves wrong) would be
   invisible here.

---

# T013 — the hand-correction cost

## Verdict: VERIFIED WORKING. Neither figure breaches Principle II's ~2 hours per week.

| Figure | Measured | Against Principle II's 120 min/week |
|---|---|---|
| **First-pass total** (one time) | **18 minutes** (0.30 h) | 15% of a single week's budget, once |
| **Steady state**, flat average | **0.168 min/week** (0.0028 h) | **0.14%** of the budget |
| **Steady state**, burst-period rate | 0.846 min/week (0.0141 h) | 0.71% of the budget |

**Neither of the two numbers breaches the ceiling.** T013 asks which of them does if either does:
**neither**, by three orders of magnitude.

## Correction timings — measured by the maintainer, not estimated

The maintainer performed the corrections and timed them end to end:

| | |
|---|---|
| **Median per correction** | **3 minutes** |
| **Maximum per correction** | **7 minutes** |
| Corrections timed | **6** |

### T013 asks for at least 20 timed corrections. Only 6 exist.

This is not a shortfall in the measurement — it is the measurement's result. Across the
**entire 34,720-question term**, the number of distinct name forms requiring a hand correction is:

| Configuration | Distinct forms needing correction | Name instances they block |
|---|---|---|
| **Full-roster pool** (pessimistic) | **6** | 671 |
| **18th-LS pool** (operative) | **1** | 106 |

T013's "at least 20" presupposes a correction burden more than three times larger than the one
that exists. **The sample is n=6, and every figure derived from it inherits that.** A median over
six observations is a weak median; it is reported as the measured value because it is the only
real one available, not because six is sufficient.

**What was measured and what was not.** The maintainer reported the *time* each correction took,
which is what T013 asks for. The *outcomes* — which `member_id` each form was assigned to — were
not reported back and are **not recorded here**. They belong in `data/assertions/` and are
Phase 3 work (the assertion store must survive unattended refreshes, per FR-009 + FR-011). No
assertion value is invented in this file.

## First-pass total

```
6 distinct forms x 3 min median = 18 min = 0.300 h
6 distinct forms x 7 min max    = 42 min = 0.700 h   (worst case, if every one were a hard case)
```

Under the operative pool it is **one** correction: 3 minutes median, 7 minutes worst case.

**This is a one-time cost, not a recurring one**, and it is well inside a single week's budget
either way. Note it covers the 18th Lok Sabha only; the 17th is 60,549 questions and unmeasured,
so the project-wide first pass is **not** established by this figure.

## Steady state — the arrival rate of *new* correction-needing forms

T013 asks for "the steady-state hours per week implied by the rate at which **new** unresolved
forms arrive across the slice's span". Measured by taking each correction-needing form's
**earliest appearance date** in the slice:

```
SLICE SPAN      2024-07-22 -> 2026-08-12  = 751 days = 107.3 weeks
ARRIVAL DATES   2024-07-22, 2024-07-22, 2024-07-22, 2024-07-29, 2024-12-16, 2024-12-18
ARRIVAL WINDOW  2024-07-22 -> 2024-12-18 = 149 days = 21.3 weeks
SILENCE SINCE   2024-12-18 -> 2026-08-12 = 602 days = 86.0 weeks, ZERO new forms
```

| Rate | Forms/week | × 3 min median | vs 120 min/week |
|---|---|---|---|
| Flat average over the whole span | 0.0559 | **0.168 min/week** | 0.140% |
| During the 21.3-week arrival window | 0.2819 | 0.846 min/week | 0.705% |
| Over the 86.0 weeks since | **0.0000** | 0 min/week | 0% |

### The distribution is front-loaded, and averaging it away would misreport it

**All six forms first appeared within the first 21.3 weeks of a 107.3-week span. None has
appeared in the 86 weeks since.** Four of the six appeared in the term's first eight days.

The flat average of 0.0559 forms/week is a real figure over a real denominator, and it is
reported as the headline because it is the one T013's wording asks for. But it describes a
steady trickle that **the data does not show**:

- it **overstates** the ongoing work, which has been zero for 86 consecutive weeks;
- it **understates** the initial burst, which ran 5× higher.

The shape has a plausible mechanical cause — a new Lok Sabha seats ~543 members at once, so the
unfamiliar name forms arrive together at the start of a term and then stop. **That is a
hypothesis, not a finding.** It predicts a fresh burst at the start of the 19th Lok Sabha and
near-zero in between, which would make the right planning figure "about 20 minutes once per
general election" rather than any per-week rate at all. **Testing it needs the 17th Lok Sabha
slice**, which would show whether that term's corrections also cluster at its start. Unmeasured.

## Asker multiplicity — the multiplier T017 needs

T013 requires the mean and maximum asker count per question from this slice, which
`research.md` records as never measured:

| | |
|---|---|
| **Mean askers per question** | **1.6453** |
| **Maximum askers per question** | **46** |

Full distribution and the sample-size progression are in the T012 section above. T017 uses the
**mean** for total published bytes and must use the **maximum** for the worst-case per-member
file count — a 46-asker question is written into 46 per-member files in each of two formats.

## What T013 does not establish

1. **n=6.** Both the median and the maximum come from six corrections, not the 20 T013 specifies,
   because only six exist. Every derived figure carries that.
2. **The 17th Lok Sabha is unmeasured** — 64% of the covered window. Both the first-pass total
   and the arrival rate are 18th-LS-only.
3. **The clustering hypothesis is untested.** Whether corrections cluster at the start of every
   term, or whether this term was unusual, is not known from one term.
4. **No correction was verified as correct.** The maintainer's time was measured; the accuracy of
   the resulting assignments was not checked against any independent source.
5. **Breakage upkeep is not in these figures at all.** `plan.md` Risk 6 records the expectation
   that the 2h/week budget "is expected to go mostly on breakage", and the upstream carries no
   contract, versioning or deprecation notice. This measurement covers **identity corrections
   only** — it says nothing about the cost of the upstream changing shape, which is the larger
   half of Principle II's budget and remains unquantified.
