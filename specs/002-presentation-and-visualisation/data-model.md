# Data Model: Presentation and Visualisation

**Feature**: `002-presentation-and-visualisation` | **Date**: 2026-10-10

Every entity here is a **presentation** entity. Nothing in this feature adds, removes or reshapes anything in `data/published/` (FR-140). Where an entity carries a published field, the published name is given so the copy cannot drift from its source.

---

## View

One switchable region of the page. Eight of them.

| Field | Type | Notes |
|---|---|---|
| `id` | string | The hash, without `#`. Stable: it is a public URL. |
| `heading` | string | The `<h2>` focus lands on when the view opens. |
| `module` | path or `null` | `null` for the shell's own views (coverage, licence). Otherwise a relative path loaded by `import()`. |
| `data` | list of published paths | What the view may fetch. May be empty. |
| `opened` | boolean | False until a reader first opens it. Gates every fetch. |
| `state` | object or `null` | The reader's work in this view. Survives switching away (FR-152). |

**Validation rules**

- `id` MUST be unique and MUST NOT change once published — it is a linkable address (FR-147).
- Exactly one view is rendered at any moment (FR-146).
- A view whose `opened` is false MUST have fetched nothing, data or code (FR-151, SC-016).
- A hash matching no `id`, and an empty hash, MUST resolve to `coverage` (FR-153).
- `module` MUST be a relative specifier (`./…`), for the deferred and the static form alike (research R6).

**State transitions**

```
unopened ──first open──> loading ──data ready──> ready
                            │                      │
                            └──fetch failed──> degraded
                                                   │
   (switch away and back: ready|degraded ──> same, no refetch)   FR-152
```

`degraded` is a visitor-facing state and MUST say what is missing in words (FR-010 is unchanged by this feature). It MUST NOT fall back to `unopened`, because that would refetch on every return.

**The eight views** — the enforceable detail is in [contracts/view-routes.md](./contracts/view-routes.md).

| `id` | View | `module` | Fetches on first open |
|---|---|---|---|
| `coverage` | Coverage statement — **the landing view** | — (shell) | nothing: its 4 files are the first load |
| `search` | Subject search + the subject trend | `./views/search.js` | subject index, asker names, ministries; then one digest per session touched |
| `seat` | State and constituency | `./views/seat.js` | constituencies, state subjects; then one `by-member` file per member opened |
| `ministry` | Single ministry profile | `./views/ministries.js` | ministry profile, ministries |
| `compare` | Two-ministry comparison | `./views/ministries.js` | — (shares the above) |
| `load` | Question load across the 21 sessions | `./views/ministries.js` | — (shares the above) |
| `composition` | House composition, 17th vs 18th | `./views/composition.js` | composition |
| `licence` | Licence, source terms, corrections | — (shell) | nothing: `manifest.json` is the first load |

---

## Result row

One question as presented in a list. Replaces the five-pair `<dl>` block (FR-101).

| Field | Published source | Presented as |
|---|---|---|
| `subject` | `subject` | The row's heading. `not stated` as a word when absent. |
| `date` | `date` | ISO, in the meta line. |
| `ministry` | `ministry_id` → `reference/ministries` `canonical_name` | Name in the meta line; the raw id plus a flag word when unrecognised. |
| `type` | `type` | **The asterisk, for `STARRED` only** (FR-113), with the word "starred" for assistive technology. `UNSTARRED` carries no mark. |
| `linkStatus` | `resolution_status` | A word in the meta line, from the same list the ministry view uses. |
| `askers` | `asking_members` → `search/asker-names` | Inline, as a figure against its denominator (FR-102). |
| `flags` | derived | Each flag is a **word** (FR-104). |

**Validation rules**

- All seven MUST remain present and reachable in the denser form (FR-101).
- Askers MUST be inline, never one per line (FR-102).
- Where askers are abbreviated, the number not shown MUST be stated and the full set reachable (FR-103).
- No flag may be carried by colour, position or density alone (FR-104).
- 25 rows MUST render within 2,800 px at 390 px (SC-006).

---

## Figure-and-denominator pairing

A count shown against the total it was drawn from, as one typographic unit (FR-114). The page's most-repeated element.

| Field | Type | Notes |
|---|---|---|
| `value` | integer | The count. |
| `total` | integer | The denominator. |
| `unit` | `question` \| `member` \| `state-question` | Keys `aggregates/counting-basis.jsonl`. |
| `label` | string | What is counted, in words. |

**Validation rules**

- `total` MUST be present wherever `value` is shown. A figure without its denominator is a breach (FR-114, FR-120).
- `unit` MUST be one of the three published units, and MUST NOT be invented here (FR-140 forbids redefining a basis).
- `value <= total` MUST hold, **except** where the published basis says otherwise and says why: `counting-basis.jsonl` records that a partly-resolved question is counted both in its identified askers' files and in the unresolved total, "so a per-member total and the unresolved total deliberately overlap, and adding them is wrong". Where a pairing crosses that overlap it MUST carry the basis statement, not a quietly impossible percentage.

---

## Chart

A hand-built SVG series with its table (FR-121, FR-123). Obligations in [contracts/chart-contract.md](./contracts/chart-contract.md).

| Field | Type | Notes |
|---|---|---|
| `form` | `stacked` \| `grouped` \| `horizontal` | `stacked` exists; the other two are new. |
| `series` | list of `{name, fill}` | `name` is text, always rendered (FR-122). |
| `columns` | list of `{label, total, parts}` | `label` is a session or category; `total` is the denominator. |
| `basis` | counting-basis record | Rendered, not summarised. |
| `title`, `description` | string | The SVG's `<title>` and `<desc>`. |
| `table` | element | The authoritative form (FR-121). |

**Validation rules**

- `series` MUST be at most 2 against the two measured fills; a third MUST use the hatch, never a lighter colour.
- Adjacent segments MUST be stroked in the surface colour — **required, not preferred**: no colour can be ≥3:1 from both the ground and `--house` (research R8).
- Every chart MUST have a `table`, and the table MUST be what a keyboard and screen reader reach (FR-121).
- Removing all colour MUST lose nothing (FR-122).
- No chart may require a term or session date (FR-124) — every one reads "not stated".
- No chart may carry a member attribute outside the FR-008 set (FR-125).

**The four new charts**

| Chart | View | Source | Form | Denominator |
|---|---|---|---|---|
| Question load, 21 sessions | `load` | `ministry-profile`, summed over ministries | stacked by type | 95,268 window total |
| Subject trend | `search` | the loaded search index — **zero further fetches** (SC-019) | stacked by type | matched total / window total |
| Two-ministry comparison | `compare` | `ministry-profile` | grouped | each ministry's own total |
| House composition | `composition` | `composition` | horizontal, paired by term | `total_members` per term |
| State subjects | `seat` | `state-subjects` | horizontal | `state_questions` |

**How the subject trend is derived** (research R3, verified): the index carries `prefixes` (session + starred/unstarred), `doc_prefix` (per document), and gap-encoded `postings`. `web/lib/search.js::positionsFor` already runs the cumulative sum; `prefixes[doc_prefix[position]]` then yields each matched document's session and type. Confirmed against the published index — the term `under` resolves to 6,254 documents across all 21 sessions and 41 buckets.

---

## Palette token and Type face

Presentation constants. Values and every measured ratio are fixed in [contracts/design-tokens.md](./contracts/design-tokens.md), which is the single definition; they are not restated here.

**Validation rules**

- Text MUST clear 4.5:1 and meaning-carrying marks 3:1, against every ground used (FR-107).
- `--house` MUST NOT appear as a background field (FR-106).
- `--paper` vs `--sheet` is 1.13:1, so a needed surface distinction MUST NOT rest on that fill difference (FR-108).
- `--house` vs `--mark` is 1.03:1, so those two MUST NOT be the only difference between two meanings (FR-109).
- Only the shipped weights — 400 and 600 — may be used (research R13).
- Every `url()` MUST be a relative path to an existing file inside `web/` (FR-112).
- No font file may carry a codepoint in U+0900–U+097F (FR-111).

---

## Signal comparison

What the two newly wired signals read from the previous publication. Full detail in [contracts/maintainer-signals.md](./contracts/maintainer-signals.md).

| Field | Type | Read from |
|---|---|---|
| `previousAvailable` | boolean | whether `.previous-snapshot` exists |
| `previousStatuses` | map `question_id` → status | previous `by-session/*.jsonl` `resolution_status` |
| `currentStatuses` | map `question_id` → status | current build |
| `previousRateAutomatic` | float or `null` | previous `manifest.json` `resolution_rate_automatic` |
| `previousRatePublished` | float or `null` | previous `manifest.json` `resolution_rate_including_assertions` |
| `currentRateAutomatic`, `currentRatePublished` | float | current build |

**Validation rules**

- `resolved_transitions_out` fires where `previousStatuses[id] == "resolved"` and `currentStatuses[id] != "resolved"` (FR-134). Payload is **question ids only** — no name, no value.
- `resolution_rate_below_target` fires on a **drop**: `current < previous`. Never on an absolute threshold (FR-135) — the automatic rate is 94.78% against a 95% target, so an absolute trigger would fire on every run and mean nothing.
- Where `previousAvailable` is false, both MUST record **"no comparison made"** — not a pass, not a signal (FR-136).
- No signal may change what a visitor sees (FR-139).
