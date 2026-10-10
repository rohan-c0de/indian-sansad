# Ministry identity — the finding, the owner decision, and the PROPOSED rename table

**Date**: 2026-10-09
**Raised by**: the T052 gate (`/api_ls/question/getMinistry` — stable id, or names only?)
**Status**: decision recorded; the rename table below is **PROPOSED and awaiting owner confirmation**.
Nothing has been written to `data/assertions/ministries.json`.

**No payload is committed.** Every figure here is a ministry *name*, a record *count* or a
*date*. The two probe bodies were written only under `$SANSAD_SCRATCH/t052/`, outside the
repository tree.

---

## The finding: the route returns an id, and the id is not an identity

`GET /api_ls/question/getMinistry?lkNo=<n>&locale=en` returns an array of records with **three**
field names: `minCode` (int), `minName` (str), `minNameHindi` (str). 56 records for the 18th Lok
Sabha, 69 for the 17th. `minCode` is dense, non-null and unique **within a term**.

It is **not** an identity, in both directions:

- **10 of the 52 ministry names present in both terms carry a different `minCode` in each.**
  `COMMUNICATIONS` is 62 in the 17th and 1 in the 18th; `YOUTH AFFAIRS AND SPORTS` is 59 and 19.
- **14 of the 56 codes shared between the terms name a different ministry in each.** Some of
  those are genuine renames (code 12: `HUMAN RESOURCE DEVELOPMENT` → `EDUCATION`) and some are
  the code being reused for an unrelated ministry (code 59: `YOUTH AFFAIRS AND SPORTS` →
  `ELECTRONICS AND INFORMATION TECHNOLOGY`; code 62: `COMMUNICATIONS` → `JAL SHAKTI`).
  **Separating the two requires human judgement; it is not derivable from the payload.**

Measured cost of each automatic scheme over all 95,269 records:

| Scheme | Failure mode | Questions affected |
|---|---|---:|
| slug of the name | **splits** one ministry into two ids on rename | 20,920 under a split identity |
| `minCode` | **merges** unrelated ministries under one id | 22,521 under a shared code, plus 325 records whose ministry name is absent from its term's reference set and would get no code at all |

Two further hazards for `minCode`: `HOUSING AND URBAN AFFAIRS` appears twice in the 17th's
reference set, under codes 64 **and** 71, so name→code is ambiguous *within* a term; and the
question route carries only the ministry **name**, never a code, so a name is the only join key
available in the first place.

## The decision (owner, 2026-10-09)

1. **`ministry_id` is the slug of the FIRST name under which a ministry was seen.** Assigned
   once, never changed, never reused.
2. **`minCode` is NOT used for identity.** It is per-term and reused for unrelated ministries,
   and question records carry only the name.
3. **A rename is recorded by a maintainer-confirmed mapping** in `data/assertions/ministries.json`
   that attaches the new name to the existing id. The older id is kept; the new name becomes the
   display name and the old one goes into `former_names`. Same discipline as the member
   assertions: **only owner-confirmed pairs, never generated.**
4. **A name with no mapping mints its own id.** The Coverage Statement reports how many ministry
   names are awaiting adjudication. **No fifth maintainer signal** is added.
5. **Trivial spelling variants are handled by name normalisation, not by assertion** — where
   normalisation resolves them. See the next section for exactly which.
6. **`minCode` stays out of the published data** unless it turns out to be needed.

### What this means for the promise to consumers

An id **never changes once assigned**, but **one ministry can carry two ids until a rename is
mapped**, and mapping keeps the older id. That is weaker than "renaming upstream MUST NOT create
a second ministry identity" and the wording in `data-model.md` and
`contracts/published-dataset.md` has been softened to match rather than left overstating what
the pipeline can do unaided.

## Which variants normalisation resolves, and which it does not

Measured over the **64 distinct ministry names** the question route serves across the window.
Adding a **singular fold** (drop a trailing `s` from any token longer than three characters,
after the existing lowercase-and-collapse-punctuation slug) merges exactly **four** groups and
creates **no false merge**:

| Variant A | Qs | Variant B | Qs | Difference | Resolved by |
|---|---:|---|---:|---|---|
| `EDUCATION` | 1,586 | `Education` | 2,115 | case only | **existing slug — already resolved, no change needed** |
| `MICRO, SMALL AND MEDIUM ENTERPRISES` | 676 | `MICRO,SMALL AND MEDIUM ENTERPRISES` | 925 | punctuation only | **existing slug — already resolved, no change needed** |
| `COMMUNICATIONS` | 1,650 | `COMMUNICATION` | 325 | trailing plural | **singular fold — NEW, to be added in T052** |
| `ENVIRONMENT,  FORESTS AND CLIMATE CHANGE` | 2,083 | `ENVIRONMENT, FOREST AND CLIMATE CHANGE` | 927 | trailing plural + double space | **singular fold — NEW, to be added in T052** |

So the 325-record `COMMUNICATION` / `COMMUNICATIONS` case the owner named **is** resolved by
normalisation, and needs no assertion. So is the `ENVIRONMENT … FORESTS` / `FOREST` pair, which
is a larger case (3,010 questions) and would otherwise have needed one.

**The limit of the fold, stated rather than hidden**: it is a trailing-`s` rule, not
lemmatisation. It resolves these four because the variance here happens to be plural-vs-singular
and punctuation. It would not resolve an abbreviation (`AYUSH` against the long form), a word
order change, or a word substitution — those are exactly the rows left in Table 1 below.

## How the candidates were picked

The rule, applied to the question route's own data and **not** to `minCode`:

1. every ministry name that appears in **only one** of the two terms; **or**
2. every name that **starts or stops appearing partway through a term** — measured against the
   sessions that actually carry questions, so the 18th's session 1 (zero questions) and the
   17th's session 13 (zero questions) do not make every name look discontinued; **plus**
3. every name in one of the 14 **shared-code pairs**, included as a candidate because the owner
   asked for them — but the shared code is **not used as evidence** for any proposed mapping.

That gives 19 candidates from rules 1–2, plus the shared-code names.

**A mapping is proposed only where the dates hand off**: the old name's last question strictly
precedes the new name's first, with no overlap. This is the whole of the evidence.

**The rule independently discredits `minCode` as evidence.** Of the 14 shared-code pairs, the
ones whose dates hand off are the genuine renames, and **four pairs overlap in time** — both
names carrying questions simultaneously for years — which is the signature of code reuse. Had
the shared code been treated as evidence, those four would have been proposed as renames and
would have merged unrelated ministries.

---

## Table 1 — PROPOSED renames (date handoff). Owner confirmation required.

| # | Status | Old name (stops) | Qs | first..last | New name (starts) | Qs | first..last | Gap | Proposed `ministry_id` kept |
|---:|---|---|---:|---|---|---:|---|---|---|
| 1 | **PROPOSED** | `SHIPPING` | 144 | 2019-06-27..2020-09-22 | `PORTS, SHIPPING AND WATERWAYS` | 848 | 2021-02-04..2026-08-07 | 135 d | `shipping` |
| 2 | **PROPOSED** | `HEAVY INDUSTRIES AND PUBLIC ENTERPRISES` | 177 | 2019-06-25..2021-03-23 | `HEAVY INDUSTRIES` | 508 | 2021-07-20..2026-08-11 | 119 d | `heavy-industries-and-public-enterprises` |
| 3 | **PROPOSED** | `HUMAN RESOURCE DEVELOPMENT` | 888 | 2019-06-24..2020-03-23 | `Education` | 2,115 | 2020-09-14..2024-02-05 | 175 d | `human-resource-development` |
| 4 | **PROPOSED** | `AYURVEDA,YOGA & NATUROPATHY,UNANI,SIDDHA AND HOMEOPATHY (AYUSH)` | 1,211 | 2019-06-21..2024-02-09 | `AYUSH` | 658 | 2024-07-26..2026-08-07 | 168 d | `ayurveda-yoga-naturopathy-unani-siddha-and-homeopathy-ayush` |

Every row: the old name's **last** question predates the new name's **first** by the gap shown, with no overlap. `ministry_id` kept is the slug of the **first** name seen, per the decision — so on row 3 the id stays `human-resource-development` while the display name becomes the current one, and `HUMAN RESOURCE DEVELOPMENT` moves to `former_names`.

**Row 3's successor spans two written forms.** `Education` (2,115 Qs, 17th LS) and `EDUCATION` (1,586 Qs, 18th LS) differ only by case and already normalise to one id (Table 2), so the successor side of row 3 is **3,701** questions once normalised. The date shown is the first of the pair.

## Table 2 — resolved by name normalisation. No assertion required.

| Variant A | Qs | Variant B | Qs | Difference | Resolved by |
|---|---:|---|---:|---|---|
| `EDUCATION` | 1,586 | `Education` | 2,115 | case only | existing slug |
| `MICRO, SMALL AND MEDIUM ENTERPRISES` | 676 | `MICRO,SMALL AND MEDIUM ENTERPRISES` | 925 | punctuation only | existing slug |
| `COMMUNICATIONS` | 1,650 | `COMMUNICATION` | 325 | trailing plural | singular fold (NEW) |
| `ENVIRONMENT,  FORESTS AND CLIMATE CHANGE` | 2,083 | `ENVIRONMENT, FOREST AND CLIMATE CHANGE` | 927 | trailing plural + double space | singular fold (NEW) |

## Table 3 — candidates with NO proposed mapping

| Name | Qs | first..last | Candidate rule | Why no mapping proposed |
|---|---:|---|---|---|
| `AGRICULTURE AND FARMERS WELFARE` | 4,824 | 2019-06-25..2026-08-11 | shared-code pair | Shared-code pair, but **overlaps in time** with its pair. Code reuse, not a rename. |
| `JAL SHAKTI` | 3,291 | 2019-06-27..2026-08-06 | shared-code pair | Shared-code pair, but **overlaps in time** with its pair. Code reuse, not a rename. |
| `HOUSING AND URBAN AFFAIRS` | 2,704 | 2019-06-27..2026-08-06 | shared-code pair | Shared-code pair, but its counterpart carries **zero** questions in the window (Table 4). No date evidence either way. |
| `FISHERIES, ANIMAL HUSBANDRY AND DAIRYING` | 1,751 | 2019-06-25..2026-08-11 | shared-code pair | Shared-code pair, but **overlaps in time** with its pair. Code reuse, not a rename. |
| `ELECTRONICS AND INFORMATION TECHNOLOGY` | 1,563 | 2019-06-26..2026-08-12 | shared-code pair | Shared-code pair, but **overlaps in time** with its pair. Code reuse, not a rename. |
| `YOUTH AFFAIRS AND SPORTS` | 1,380 | 2019-06-27..2026-08-10 | shared-code pair | Shared-code pair, but **overlaps in time** with its pair — both active at once. Code reuse, not a rename. |
| `COOPERATION` | 508 | 2021-08-03..2026-08-11 | starts partway LS17 (s6 not s1); shared-code pair | No predecessor stops when it starts. A ministry that began mid-term, not a rename. |
| `DEVELOPMENT OF NORTH EASTERN REGION` | 217 | 2019-07-03..2026-08-12 | stops partway LS17 (s14 not s15) | Present in both terms throughout; the partway flag is a session with no questions from it, not a handoff. |
| `PARLIAMENTARY AFFAIRS` | 53 | 2019-07-03..2026-08-05 | stops partway LS17 (s14 not s15) | Present in both terms throughout; sparse rather than discontinued. |
| `PRIME MINISTER` | 1 | 2019-07-10..2019-07-10 | one-term; stops partway LS17 (s1 not s15) | One question, one session. No successor and nothing to map. |

## Table 4 — shared-code candidates with NO question evidence

| Reference-set name (no questions in the window) | Counterpart | Counterpart Qs |
|---|---|---:|
| `COMMUNICATIONS AND INFORMATION TECHNOLOGY` | `COMMUNICATIONS` | 1,650 |
| `SKILL DEVELOPMENT, ENTREPRENEURSHIP,YOUTH AFFAIRS AND SPORTS` | `YOUTH AFFAIRS AND SPORTS` | 1,380 |
| `AGRICULTURE` | `AGRICULTURE AND FARMERS WELFARE` | 4,824 |
| `NITI AYOG` | `HOUSING AND URBAN AFFAIRS` | 2,704 |

These four appear in a reference set but carry **zero** questions in the covered window, so there is no date evidence either way. They cannot be adjudicated from this data and are listed so they are not mistaken for absent.

---

## What happens next

Nothing in this file is in effect. On confirmation:

- the confirmed rows go into `data/assertions/ministries.json` with `asserted_by: maintainer`,
  the same discipline as `data/assertions/lok-sabha.json`;
- T052 implements the mapping and the singular fold;
- T053 reports the count of unmapped ministry names awaiting adjudication in the Coverage
  Statement.

**Unconfirmed rows are not assertions.** A row in Table 1 is a proposal with its evidence
attached, exactly as the member assertions' table was before the owner confirmed four of five.
