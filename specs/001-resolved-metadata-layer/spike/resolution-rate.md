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

---

# ADDENDUM — the 17th Lok Sabha, and what it overturns

**Date**: 2026-10-09, after the sections above
**Slice**: 17th Lok Sabha, **sessions 1–10 only — 45,467 of the term's 60,549 questions (75.1%)**
**Matcher**: byte-identical configuration to the sections above. No threshold changed.

> ## The headline above is wrong for the window. SC-002 is NOT met.
>
> T012 above concluded "VERIFIED WORKING, SC-002's 95% is met, with room". That conclusion was
> drawn from the 18th Lok Sabha alone and carried its own refutation as the first of five things
> it did not establish: *"The 17th Lok Sabha is unmeasured. It is 60,549 questions, 1.75× this
> slice, and 64% of the covered window."* The 17th has now been measured and the verdict flips.

## The numbers

| Slice | Questions | Resolved | Rate | Ambiguous | Unresolved |
|---|---|---|---|---|---|
| 18th LS, complete term (term pool, 544 members) | 34,720 | 34,610 | **99.68%** | 0 | 106 |
| **17th LS, sessions 1–10 (term pool, 559 members)** | **45,467** | **38,837** | **85.42%** | **0** | **6,630** |
| **WINDOW, measured so far** | **80,187** | **73,447** | **91.59%** | 0 | 6,736 |

Pessimistic full-roster bound for the 17th: **83.76%** by question (835 ambiguous, 6,549
unresolved). Per name instance: 89.44% (term pool) / 88.35% (full pool). Per distinct form:
91.35% / 89.94%.

**The window figure is the sum of per-term numerators and denominators**, because each question
is matched against its own term's members. That is arithmetically identical to per-question
pooling and required no change to the prototype.

### Why the slice is 10 sessions and not 15

The fetch was **killed partway through session 11**, after sessions 1–10 had completed. Every one
of those ten sessions matches its declared `totalRecordSize` exactly. **Session 11's 973 partial
rows were discarded**, not counted — a partial session is a biased sub-sample of that session, and
including it would corrupt the denominator in an unknowable direction.

So this is a **real measurement over a real denominator**, not an extrapolation — but it is 75.1%
of the term and the window figure covers **84.2% of the window**. The five missing sessions
(11–15) could move 91.59% either way.

## The pool correction that had to happen first

The pool was previously selected by `lastLoksabha == N`. That is **wrong for any term but the
latest**: a member who served in the 17th and continued into the 18th carries
`lastLoksabha == 18`. The roster's `lsExpr` field enumerates every term served
(`"11,12,14,16,17"`), so the pool is now `lsExpr contains N`.

| | `lsExpr` contains N | `lastLoksabha == N` | |
|---|---|---|---|
| **18th LS** | 544 | 544 | **identical sets** |
| **17th LS** | **559** | 343 | **216 members missing** |

**The control that makes this safe**: re-running the 18th under the new definition reproduces
99.68% / 34,610 of 34,720 / 467 forms / tiers 460-6-1 **exactly**, so nothing above is affected.
Measuring the 17th with the old test would have withheld 216 of its own sitting members and
manufactured unresolved forms the real pipeline never sees.

## The fuzzy matcher is load-bearing after all

T012 above recorded that the approximate tier "resolved nothing whatsoever — zero forms, zero
instances", and explicitly declined to conclude fuzzy matching was unnecessary, giving as its
first reason that the 17th was unmeasured and "an older term is exactly where upstream name
hygiene is likelier to be worse." **That is what happened.**

| Tier | 18th forms | 18th instances | **17th forms** | **17th instances** |
|---|---|---|---|---|
| exact | 460 | 56,241 | 383 | 55,771 |
| normalised | 6 | 777 | **42** | **7,240** |
| normalised-reordered | **0** | **0** | **11** | **1,443** |
| **approximate (fuzzy)** | **0** | **0** | **18** | **3,465** |
| reached approximate and failed | 1 | 106 | **43** | **8,020** |

On the 17th, 114 forms (19,168 instances) need *something beyond exact matching* — against 7
forms (883 instances) on the 18th. FR-002's fuzzy requirement is justified by the 17th, and the
0.90 threshold is now exercised in the direction that matters: **it accepted 18 forms**.

## Why the 17th fails — three causes, diagnosed rather than guessed

The 43 unresolved forms classify cleanly by token-set relationship against the candidate pool:

| Cause | Forms | Instances | Example |
|---|---|---|---|
| Question form's tokens are a strict **subset** of a roster name | 10 | 2,167 | `Shrirang Appa Barne` vs `shrirang appa chandu barne` |
| Roster name is a strict **subset** of the question form | 8 | 1,709 | `Supriya Sadanand Sule` vs `supriya sule` |
| **No containment relationship** | 25 | 4,144 | `D.K. Suresh`; `Poonam (Mahajan) Vajendla Rao`; `Balubhau (Alias Suresh Narayan) Dhanorkar` |

The first two classes share one mechanism — a differing count of name components, almost always
a middle name present on one side and absent on the other. The third is initials, parenthetical
aliases, and genuinely divergent orderings.

**A bidirectional token-containment tier** — resolve if the form's token set is a strict subset or
superset of exactly one pool member's — was **simulated against the recorded failures**:

| | Window rate | vs 95% | Hand corrections remaining |
|---|---|---|---|
| as measured | 91.59% | NOT MET | 44 forms (2.2 h) |
| + containment tier | **95.33%** | **MET** | **25 forms (1.2 h)** |

**It has not been implemented and no matcher change has been made.** Adding a tier after seeing
the rate fall short is the move T012 forbids, and whether this counts as a structural rule for an
evidenced pattern or as tuning is the owner's judgement, not the measurement's. The option, its
gain and its three objections are set out in `spike-report.md` T014.

## T013 revised — the correction cost has grown by 7×

| | 18th LS only (as recorded above) | **Window (measured so far)** |
|---|---|---|
| Distinct forms needing correction | 6 (full pool) / 1 (term pool) | **44** |
| **First-pass total** at the measured 3-min median | 18 min (0.30 h) | **132 min (2.2 h)** |
| First-pass worst case at the 7-min maximum | 42 min (0.70 h) | **308 min (5.1 h)** |

**The first-pass figure now exceeds Principle II's ~2 hours per week** for the week it is
performed. It remains a **one-time** cost, and the steady-state arrival rate is what the
principle's "routine" language actually targets — but the earlier claim that the burden sits at
"0.14% of the budget, three orders of magnitude inside the ceiling" described the 18th Lok Sabha
and does not describe the window.

The correction timings themselves (median 3 min, maximum 7 min, n=6) are unchanged and were
measured on 18th-LS forms. **Whether the 17th's harder cases — initials, aliases, parentheticals
— cost the same 3 minutes is UNVERIFIED.** They are plausibly slower, which would make 2.2 h an
underestimate.

## Asker multiplicity, now across two terms

| Slice | Questions | Instances | Mean | Median | **Max** |
|---|---|---|---|---|---|
| 18th LS, complete term | 34,720 | 57,124 | 1.6453 | 1 | 46 |
| 17th LS, sessions 1–10 | 45,467 | 75,939 | **1.6702** | 1 | **49** |

The two terms agree closely on the mean (1.645 vs 1.670), which is the first evidence that the
multiplier is **stable across terms** rather than still drifting with sample size. The maximum
rose 46 → 49.

## The session-1 hypothesis is contradicted

T012 above recorded that the 18th Lok Sabha's session 1 has **zero** questions against 7 sitting
days, and offered as a plausible mechanical cause that a constitutive session — members sworn in,
Speaker elected — holds no Question Hour, while explicitly labelling it a hypothesis rather than a
finding.

**The 17th Lok Sabha's session 1 carries 6,198 questions.** It was equally constitutive. So the
hypothesis is **refuted**, and the 18th's session-1 gap is a genuine anomaly to declare under
FR-013 rather than an explicable artefact. Cause remains **UNVERIFIED**.

## Upstream cost: the 17th is ~3× more expensive per page, and it is not pagination

| Fetch mode | Median s/page | Page depth | Result set |
|---|---|---|---|
| 18th LS, whole term (35 pages) | **~22** | to 35 | 34,720 |
| 17th LS, whole term (11 pages, control) | **66.5** | to 61 | 60,549 |
| 17th LS, per session | **~54** | to 7 | ~6,198 |

Per-session fetching caps page depth at 7 and each result set at ~6,198 rows, and bought only
**~19%**. So neither offset depth nor result-set size is the dominant cost.

**Time of day is ruled out by direct control**: the identical 18th-LS request re-timed during the
17th's fetch returned in 19.0 s and 32.8 s, matching its original 17.8–22 s. The service was not
generally slower. **The cost is specific to the 17th Lok Sabha's records**, cause **UNVERIFIED**.

**This revises the ingest-duration projection upward.** `free-tiers.md` T008 estimated a full
window ingest at 20–50 minutes from measured per-record cost. Measured: the 18th took **797 s
(13.3 min)** for 34,720 questions, and the 17th's 10 sessions took roughly **45 min** for 45,467.
A full-window ingest is therefore on the order of **75–80 minutes**, not 20–50. Still comfortably
inside the 6-hour job ceiling — about 22% of it — but the earlier figure was low by roughly 2×.

**A correction to something asserted during this work**: a linear trend fitted to five 17th-LS
page times (59 → 68 → 72 → 75 s) was used to project 171 minutes on a "deeper offsets are slower"
reading. Page 7 then returned in 50.2 s and page 11 in 62.2 s. **The fit was fitting noise across
five points and the next observation contradicted it.** Both the projection and the hypothesis
are withdrawn.

## What this addendum does not establish

1. **Sessions 11–15 of the 17th Lok Sabha are unfetched** — 15,082 questions, 15.8% of the
   window. 91.59% could move either way.
2. **The containment tier is simulated, not implemented.** 95.33% comes from applying a stated
   rule to recorded failures, not from a matcher re-run.
3. **The 25 non-containment failures have no proposed remedy** — 4,144 instances needing
   individual judgement or further rules.
4. **Correction timings were measured on 18th-LS forms only.** The 17th's harder cases may cost
   more than 3 minutes each.
5. **Published bytes and file counts were not re-measured for the window** — the whole-window
   publish and index need the complete 17th. Those figures remain 18th-LS projections.
6. **Precision is still unverified.** No join, in either term, was hand-checked against the real
   person. Every rate here measures the coverage of matching, not its correctness.

---

# FINAL — the complete window, and the Option C holdout test

**Date**: 2026-10-09, superseding the figures in the addendum above
**Slices**: 18th Lok Sabha complete (34,720) + **17th Lok Sabha complete (60,549)** = **95,269**
**Matcher**: configuration unchanged. The containment tier is a separate, flagged run.

Sessions 11–15 of the 17th Lok Sabha were fetched (15,082 rows, `complete=YES`, matching
`totalRecordSize` exactly) **without refetching sessions 1–10**. 34,720 + 60,549 = 95,269 equals
the sum of the two terms' declared totals, so **no projection remains in any rate below.**

## Step 2 — the window, with the matcher unchanged

| Slice | Questions | Resolved | Rate | Unresolved | Ambiguous |
|---|---|---|---|---|---|
| 18th LS, complete term | 34,720 | 34,610 | **99.68%** | 106 | 0 |
| **17th LS, complete term** | **60,549** | **51,742** | **85.45%** | 8,807 | 0 |
| 17th LS, sessions 11–15 (holdout) alone | 15,082 | 12,905 | **85.57%** | 2,177 | 0 |
| **FULL WINDOW** | **95,269** | **86,352** | **90.64%** | 8,913 | 0 |

**SC-002: NOT MET.** Short by **4.36 points** = **4,153 questions**.

The addendum above reported 91.59% over 80,187 questions (84.2% of the window). Completing the
17th moved the window figure **down** to 90.64%, because the added sessions resolve at 85.57% —
in line with the rest of that term and far below the 18th.

**The 17th's failure rate is strikingly stable across its own sessions**: 85.42% (sessions 1–10),
85.57% (sessions 11–15), 85.45% (whole term). Whatever causes it is uniform across the term, not
concentrated in particular sessions.

Tiers, 17th LS complete term: exact 391 · normalised 42 · normalised-reordered 11 ·
**approximate 18** · reached approximate and failed 43.

## Step 3 — the Option C tier, implemented and holdout-tested

Implemented in **`spike/resolve_rate.py` only — never in `src/`** — behind `--containment`, off
by default, exactly as described in `spike-report.md` T014 Option C: *a form resolves if its
canonical token set is a strict subset or strict superset of exactly one pool member's token
set*, reached only when every earlier tier has failed to produce a single member.

**It was written, tested and committed while sessions 11–15 were still being fetched**, so those
sessions could not have informed any rule or threshold. **No rule or threshold was altered after
seeing the holdout result.**

### Holdout: sessions 11–15, 15,082 questions, unseen

| | Resolved | Rate | Unresolved |
|---|---|---|---|
| matcher unchanged | 12,905 | **85.57%** | 2,177 |
| + containment tier | 13,857 | **91.88%** | 1,225 |
| **gain on unseen data** | **+952** | **+6.31 points** | −952 |

**The rule generalises essentially perfectly.** On the data it was derived from (sessions 1–10)
the gain was **+6.35 points**; on unseen data **+6.31**. A 0.04-point difference across a
15,082-question holdout is no measurable overfitting. 16 holdout forms resolved via the new tier.

### Full window, both configurations

| Configuration | Resolved | Rate | vs 95% |
|---|---|---|---|
| matcher unchanged | 86,352 / 95,269 | **90.64%** | NOT MET |
| **+ containment tier** | **90,299 / 95,269** | **94.78%** | **STILL NOT MET** |
| gain | +3,947 | +4.14 points | |

**Short by 207 questions — 0.22 points.**

**The simulation overstated it, and this report had flagged exactly that risk.** The addendum's
estimate was 95.33% on 84.2% of the window, with the recorded objection that *"95.33% clears 95%
by 0.33 points … the five unfetched sessions, or the 17th's full term, could put it back under."*
They did. The implemented tier on the complete window gives 94.78%.

### Residual burden after the tier

| | Forms needing correction | × 3-min median |
|---|---|---|
| matcher unchanged | **44** | 132 min = **2.2 h** |
| + containment tier | **25** | 75 min = **1.2 h** |

**All 25 residual forms are in the 17th Lok Sabha; the 18th has zero after the tier.** They block
5,472 name instances and 4,970 questions. Correcting all 25 reaches **100%**. Reaching merely 95%
needs **207** questions, and the largest residual form alone blocks 528 name instances — so one or
two corrections clear the threshold.

The 25 are the non-containment class: initials (`D.K. Suresh`, `V. Kalanidhi`), parenthetical
aliases (`Poonam (Mahajan) Vajendla Rao`, `Balubhau (Alias Suresh Narayan) Dhanorkar`), and
divergent orderings (`Sunil Dattatray Tatkare`, `Ganesan Selvam`, `Kumbakudi Sudhakaran`).

## A fourth coverage anomaly, found by completing the term

**Session 13 of the 17th Lok Sabha returns `totalRecordSize: 0`** — zero questions — against the
**4 sitting days** the session enumeration records for it. Unlike the 18th's session 1, this is a
**mid-term** session, so no constitutive-sitting explanation is even available.

The FR-013 tally is now four, all causes **UNVERIFIED**:

| Term | Session | Sitting days | Questions |
|---|---|---|---|
| 18th | 1 | 7 | **0** |
| 18th | 8 | **0** | 4,500 |
| **17th** | **13** | **4** | **0** |
| 17th | — | — | sessions 1–15 otherwise all populated |

## Asker multiplicity across both complete terms

| Slice | Questions | Instances | Mean | Max |
|---|---|---|---|---|
| 18th LS, complete term | 34,720 | 57,124 | 1.6453 | 46 |
| 17th LS, sessions 1–10 | 45,467 | 75,939 | 1.6702 | 49 |
| 17th LS, sessions 11–15 | 15,082 | 25,811 | **1.7114** | 20 |

The mean is stable across terms and sub-slices (1.645–1.711), which is the evidence that it has
converged — unlike the early samples (1.32 at n=50, 1.504 at n=250). **T017 may use ~1.67.**

## What this FINAL section does not establish

1. **Published size is still projected, not measured, for the window.** The whole-window publish
   and index were not re-run on the completed 17th. ~297 MiB, ~1,950 files and the 3.13 MiB
   index remain scaled 18th-LS measurements.
2. **The 0.90 approximate threshold is uncalibrated.** It accepted 18 forms and rejected 43.
   Whether a lower value would resolve more of the 25 residual forms without mis-joining anyone
   is untested, deliberately — altering it now is the tuning T012 forbids.
3. **The 25 residual forms have no automated remedy proposed**, and no rule for initials or
   parenthetical aliases was attempted.
4. **Correction timings remain n=6 and 18th-LS-only.** The 25 residual forms are the harder
   class; whether they cost 3 minutes each is **UNVERIFIED**, so 1.2 h may be an underestimate.
5. **Precision is still unverified.** No join in either term was hand-checked against the real
   person. Every rate measures the coverage of matching, not its correctness.
6. **The steady-state arrival rate was never computed for the 17th Lok Sabha**, so no
   window-wide Principle II steady-state figure exists.

---

# Containment-tier matches and the residual forms

**Date**: 2026-10-09. Derived from the `--containment` runs over both complete terms.
Member **name forms only** are shown; no other member field appears, per FR-008.

## (1) Every name form the containment tier resolves, both terms

| Questions | Form as written (question route) | Roster name matched | Term |
|---:|---|---|---:|
| 634 | `Shrirang Appa Barne` | `Shrirang Appa Chandu Barne` | 17th |
| 629 | `Supriya Sadanand Sule` | `Supriya Sule` | 17th |
| 484 | `Ravi Kishan Shukla` | `Ravindra Shukla Alias Ravi Kishan` | 17th |
| 472 | `Prataprao  Jadhav` | `Prataprao Ganpatrao Jadhav` | 17th |
| 395 | `Manoj Kumar Tiwari` | `Manoj Tiwari` | 17th |
| 379 | `L.S. Tejasvi Surya` | `Tejasvi Surya` | 17th |
| 342 | `Midhun Reddy` | `P V Midhun Reddy` | 17th |
| 310 | `Jugal Kishore Sharma` | `Jugal Kishore` | 17th |
| 284 | `Margani Bharat` | `Bharat Ram Margani` | 17th |
| 280 | `Hemant Patil` | `Hemant Shriram Patil` | 17th |
| 238 | `Rajiv Ranjan (Lalan) Singh` | `Rajiv Ranjan Singh` | 17th |
| 181 | `Kanimozhi Karunanidhi` | `Kanimozhi Rajathi Karunanidhi` | 17th |
| 152 | `Prataprao Govindrao  Patil Chikhalikar` | `Prataprao  Patil Chikhalikar` | 17th |
| 106 | `Smt. Kanimozhi Karunanidhi` | `Kanimozhi Rajathi Karunanidhi` | 18th |
| 103 | `Vinod Chavda` | `Chavda Vinod Lakhamshi` | 17th |
| 88 | `Devusinh Jesingbhai Chauhan` | `Devusinh Chauhan` | 17th |
| 75 | `Shiromani Ram` | `Ram Shiromani Verma` | 17th |
| 31 | `Suresh Pujari` | `Suresh Kumar Pujari` | 17th |
| 1 | `Satabdi Roy (Banerjee)` | `Satabdi Roy` | 17th |

**19 forms, 5,184 questions.** Eighteen are in the 17th Lok Sabha and one in the 18th.

Every row is the same mechanism — a differing count of name components. The question route and
the roster disagree about whether a middle name, a patronymic, an initial or an alias belongs in
the name, and the tier resolves the disagreement in whichever direction it runs. `Supriya
Sadanand Sule` adds a middle name the roster omits; `Shrirang Appa Barne` omits one the roster
carries. Three rows (`Ravi Kishan Shukla`, `Rajiv Ranjan (Lalan) Singh`, `Satabdi Roy
(Banerjee)`) are alias forms that happen to satisfy containment; the tier was not designed for
aliases and catches these incidentally, which is why the 25 residual forms still include
parenthetical aliases it misses.

## (2) The 25 residual forms, ranked by questions blocked

A question is blocked if **any** of its askers is unresolved, so the counts below overlap: a
co-asked question with two residual askers appears in both rows.

| Rank | Questions blocked | Form as written | Term |
|---:|---:|---|---:|
| 1 | 513 | `Sunil Dattatray Tatkare` | 17th |
| 2 | 414 | `Ganesan Selvam` | 17th |
| 3 | 372 | `D.K. Suresh` | 17th |
| 4 | 292 | `Poonam (Mahajan) Vajendla Rao` | 17th |
| 5 | 273 | `V. Kalanidhi` | 17th |
| 6 | 270 | `S. Jagathrakshakan` | 17th |
| 7 | 270 | `Vellalath Kochukrishnan Nair. Sreekandan` | 17th |
| 8 | 263 | `Kumbakudi Sudhakaran` | 17th |
| 9 | 258 | `Balubhau (Alias Suresh Narayan) Dhanorkar` | 17th |
| 10 | 255 | `Kani K. Navas` | 17th |
| 11 | 246 | `Andimuthu Raja` | 17th |
| 12 | 225 | `Abdul Majeed Ariff` | 17th |
| 13 | 222 | `M. Selvaraj` | 17th |
| 14 | 208 | `Mitesh Rameshbhai (Bakabhai) Patel` | 17th |
| 15 | 202 | `Shardaben Anilbhai Patel` | 17th |
| 16 | 195 | `Thalikkottai Rajuthevar Baalu` | 17th |
| 17 | 143 | `Thirumaa Valavan Thol` | 17th |
| 18 | 140 | `Nusrat Jahan Ruhi` | 17th |
| 19 | 138 | `S. Ramalingam` | 17th |
| 20 | 122 | `C. R. Patil` | 17th |
| 21 | 47 | `Durga Das Uikey` | 17th |
| 22 | 32 | `Rampreet Mandal` | 17th |
| 23 | 24 | `Mohanbhai Sanjibhai Delkar` | 17th |
| 24 | 23 | `Sakshi Ji Swami Maharaj` | 17th |
| 25 | 2 | `V. Srinivas Prasad` | 17th |

**All 25 are in the 17th Lok Sabha. The 18th has none after the tier.**

## Owner decision 2026-10-09 — four assertions confirmed, one dropped

| # | Status | Questions blocked | Form as written |
|---:|---|---:|---|
| 1 | **CONFIRMED BY OWNER** | 513 | `Sunil Dattatray Tatkare` |
| 2 | **CONFIRMED BY OWNER** | 414 | `Ganesan Selvam` |
| 3 | **CONFIRMED BY OWNER** | 372 | `D.K. Suresh` |
| 4 | **DROPPED BY OWNER** | 292 | `Poonam (Mahajan) Vajendla Rao` |
| 5 | **CONFIRMED BY OWNER** | 273 | `V. Kalanidhi` |

**No reason was recorded for dropping row 4, and none is inferred here.** That form **stays among
the residual forms**, which now number **21** (25 after the tier, minus the four seeded).

### The window rate with the four confirmed pairs — computed over the question records

With the tier enabled the window stands at **90,299 / 95,269 = 94.78%** — the **automatic** rate.
Seeding the four confirmed assertions:

| | Resolved | Rate | vs 95% |
|---|---:|---:|---:|
| Automatic (tier only, no assertions) | 90,299 / 95,269 | **94.78%** | fails by 0.22 |
| **+ four confirmed assertions** | **91,708 / 95,269** | **96.26%** | **met, +1.26 points** |

**1,409 questions recovered.** Computed by re-walking all 95,269 question records and counting
those whose *every* residual asker is one of the four confirmed forms. **Not** obtained by adding
the per-form blocked counts, which would be wrong:

```
naive sum of questions the four forms appear in : 1,572
actually recovered                              : 1,409
difference                                      :   163
```

Those **163 questions remain unresolved** because each is co-asked by someone whose form is still
residual. A question resolves only when **all** its askers resolve (FR-003), so blocked counts
overlap and cannot be summed — which is exactly why this figure was recomputed rather than
derived from the earlier five-pair table.

**The earlier record said 96.56% (91,991 resolved) for five pairs. With row 4 dropped the real
figure is 96.26% (91,708)** — 283 questions fewer.

**Cost**: 4 × the measured 3-minute median = **12 minutes**. The remaining 21 residual forms are
optional; correcting all of them would reach 100.00%.


---

# NOTE — a latent defect in `spike/resolve_rate.py`, found 2026-10-09 during T046

**Date**: 2026-10-09 · **Found by**: T046 (`src/sansad/resolve/match.py`), while porting this
script's tier order into `src/`.

**The defect.** In `resolve_form`, the exact, normalised and normalised-reordered tiers call
`fallback(...)` on an ambiguous result. `def fallback` appears **below** those three call sites,
inside the same function, so `fallback` is a local name that is not yet bound when they run.
Python raises rather than falling back to an enclosing scope. VERIFIED by running the same
construction in isolation:

```
UnboundLocalError: cannot access local variable 'fallback' where it is not associated with a value
```

The approximate tier is unaffected — its `fallback` calls sit after the definition.

**Every figure in this report stands.** The measured runs completed and produced the aggregates
recorded above, which they could not have done had any of those three paths executed. So **no
name form in the 95,269-question window reached ambiguity at the exact, normalised or
normalised-reordered tier** — consistent with the `ambiguous` column being **0** in every table
in this report, for both terms and both candidate pools. The defect is in an unreached branch.
It is recorded here anyway: "a failure you didn't capture is a data point you destroyed", and a
future run on different data would hit it.

**What it means for the containment tier's measured gain.** The tier was reachable only from the
approximate tier's failure paths during measurement, which is where all 19 of its matches came
from. The **+6.31-point holdout gain and the 90.64% → 94.78% window figures are therefore
measurements of the tier as it actually ran**, not of a partially-disabled version of it.

**Fixed in `src/`.** `src/sansad/resolve/match.py` implements the intended behaviour: the three
deterministic tiers do reach the containment fallback on an ambiguous result. The consequence is
narrow and worth stating plainly — the production matcher can resolve a form on which this
script would have raised. That is a difference in *reachable* behaviour, not in any figure
published here.

**So T046 is "as this script, plus that fix", not "exactly as this script".** `tasks.md` T046
carries the same correction.
