# Contract: What Every Chart Must Carry

**Feature**: `002-presentation-and-visualisation` | **Date**: 2026-10-10

Five obligations. A chart missing any one of them is not shippable. These restate FR-120 to FR-125 in the form a reviewer can check against a rendered page.

## The five obligations

### 1. Its counting basis, rendered (FR-120)

Every chart renders the counting-basis statement for its unit, read from `aggregates/counting-basis.jsonl` — not paraphrased, not summarised, not linked to. The three published units are `question`, `member` and `state-question`, and they do not mean the same thing. The `question` basis alone is 1,100 characters and says, among other things, that joint questions count once, that the `by-member` files republish a joint question per asker so summing them over-counts, and that partly-resolved questions are counted in both a member's total and the unresolved total so adding those two is wrong.

A chart that shows a figure without the basis that defines it is the defect this obligation exists to prevent.

### 2. Every figure against its denominator (FR-120, FR-114)

No bare count. Each value is paired with the total it was drawn from, as one typographic unit — not a footnote.

| Chart | Denominator |
|---|---|
| Question load, 21 sessions | 95,268 — the window total |
| Subject trend | the matched total, and the window total |
| Two-ministry comparison | each ministry's own total, stated for both |
| House composition | `total_members` for that term (559 for the 17th, 544 for the 18th) |
| State subjects | `state_questions` for that state |

**A chart that drops the denominator breaks the standard the rest of the record holds to.**

### 3. A table beside it, which is the authoritative form (FR-121)

Every chart is accompanied by a table carrying the same figures, and the table is what a keyboard and a screen reader reach. The `<svg>` is `role="img"` with a `<title>` and `<desc>`, and its internals are hidden from assistive technology — a reader is not walked through forty anonymous rectangles.

No chart may be the only form of its data. This also handles the reader with a large browser font size: the table's text scales, and SVG text inside a non-uniform `viewBox` does not, which is why the existing chart puts its column labels in HTML rather than SVG.

### 4. No meaning by colour alone (FR-122)

Remove every colour and the chart still says which series is which. Each series is named in the legend **and** in the table header, and each segment carries its number as text.

Adjacent meaning-carrying marks must either clear 3:1 against each other, or be separated by a stroke in the surface colour with the separation recorded. For this palette the second branch is **forced**: `--series-2` is 1.80:1 against `--house`, and [design-tokens.md](./design-tokens.md) proves no colour can clear 3:1 against both the near-white grounds and `--house`. So:

- every segment is stroked in `--sheet`, as the current chart already does at 0.3 stroke-width
- the series are named in text
- the table is authoritative
- the 1.80:1 figure is recorded in the stylesheet beside the token

A third series uses the existing hatch pattern, never a lighter colour.

### 5. Nothing outside the published record (FR-123, FR-124, FR-125)

| Rule | Why |
|---|---|
| Hand-built SVG only | No charting library, no framework, no build step |
| No term or session date | Every `start_date` and `end_date` in the published member reference *and* in `reference/sessions.jsonl` reads **"not stated"** — 9,986 term records across 5,426 members, and all 21 sessions. Terms and sessions can be ordered and counted, never placed on a calendar. Question dates are fine: they run 2019-06-21 to 2026-08-12. |
| No member attribute outside the FR-008 set | Name forms, party, state, constituency, House, term, sitting status — nothing else |
| An absent attribute is an explicit "not stated" category | Never an omitted row; omitting it would make the categories stop summing to the total |

## The four new charts against the five obligations

| | Basis | Denominator | Table | Colour-free | Published-only |
|---|---|---|---|---|---|
| Question load, 21 sessions | `question` | 95,268 | required | 2 series, named | `ministry-profile` summed over ministries |
| Subject trend | `question` | matched / 95,268 | required | 2 series, named | search index, **zero further fetches** (SC-019) |
| Two-ministry comparison | `question` | per ministry | required | 2 series, named | `ministry-profile` |
| House composition | `member` | `total_members` | required | 2 series (term), named | `composition` |
| State subjects | `state-question` | `state_questions` | required | 1 series | `state-subjects` |

## Chart forms

`web/lib/chart.js` exports `stackedColumns` and `legend` today. Two forms are added:

| Form | Used by | Why not stacked |
|---|---|---|
| `stackedColumns` (exists) | question load, subject trend | starred/unstarred are parts of one total |
| `groupedColumns` (new) | two-ministry comparison | two independent totals; stacking them would imply a sum that means nothing |
| `horizontalBars` (new) | composition, state subjects | 25 subject lines and up to 84 party categories cannot carry readable vertical labels at 390 px |

## Specific hazards these charts must survive

Each is a real property of the published data, not a hypothetical.

- **A session with zero questions.** Session `lok-sabha/18/8` has `sitting_days: 0`. A zero column must render as a labelled zero, not a gap, and must not divide by zero when its share is computed.
- **One category holding most of the total.** 282 of 544 members in the 18th Lok Sabha served exactly one term, which flattens every other bar in the `terms_served` dimension. The chart must stay readable, and the long tail must not round to an invisible zero-width bar.
- **42 party categories per term, 84 rows across the two.** The party dimension cannot show every category at 390 px. Whatever is not shown must be **counted and stated** (FR-103) — never silently dropped — and the categories shown plus the remainder must still sum to `total_members`. `make composition LS_TERM=18` already does exactly this: twelve categories, then "and 30 further categories" carrying 51 members, reconciling to 544. The chart matches that treatment rather than inventing its own.
- **Ties in the state subject ordering.** Several of a state's 25 subject lines share a count, so order is not determined by count alone and needs a stated tie-break, as the search view already states its own ordering.
- **A chart drawn before its data arrives.** Each chart lives in a view that fetches on first open, so every one has a loading and a degraded state, both worded.
- **The subject trend with one matched document.** A single-column trend must not read as a broken chart; below some threshold the table alone is the honest presentation.
