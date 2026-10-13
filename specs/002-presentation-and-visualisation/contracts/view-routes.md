# Contract: View Routes and Fetch Timing

**Feature**: `002-presentation-and-visualisation` | **Date**: 2026-10-10

The enforceable form of FR-126, FR-127, FR-128, FR-146, FR-147, FR-151, FR-152 and FR-153. Every `id` below is a **public URL** and may not change once published.

## The eight views

| `#id` | Heading | Module | Data, read on first open only |
|---|---|---|---|
| `coverage` | Coverage | shell | — (its four files *are* the first load) |
| `search` | Subject search | `./views/search.js` | `search/subject-index.json`, `search/asker-names.jsonl`, `reference/ministries.jsonl` → then `search/digest/<session>.jsonl`, one per session a query touches |
| `seat` | Your state and constituency | `./views/seat.js` | `reference/constituencies.jsonl`, `aggregates/state-subjects.jsonl` → then `by-member/<id>.jsonl`, one per member opened |
| `ministry` | Ministry profile | `./views/ministries.js` | `aggregates/ministry-profile.jsonl`, `reference/ministries.jsonl` |
| `compare` | Compare two ministries | `./views/ministries.js` | — (shares `ministry`'s two files) |
| `load` | Question load by session | `./views/ministries.js` | — (shares `ministry`'s two files) |
| `composition` | House composition | `./views/composition.js` | `aggregates/composition.jsonl` |
| `licence` | Licence and source terms | shell | — (`manifest.json` is on the first load) |

`ministry`, `compare` and `load` share one module and one pair of files: opening any of the three loads them, and the other two then cost nothing. `reference/ministries.jsonl` is shared with `search`, which needs it to name a ministry on a result row; it is read once between them, not twice.

## What the first load may contain

Exactly this, and nothing else (FR-126, FR-151; measured in [research.md](../research.md) R14):

```
index.html
style.css
fonts/newsreader-600.woff2
fonts/ibm-plex-sans-400.woff2
fonts/ibm-plex-sans-600.woff2
app.js
lib/fetch.js   lib/coverage.js   lib/format.js   lib/licence.js
data/published/coverage.jsonl
data/published/reference/sessions.jsonl
data/published/aggregates/counting-basis.jsonl
data/published/manifest.json
```

14 requests. **Anything else on the first load is a failure**, including:

- any file under `search/`, by-member, `constituencies`, `state-subjects` — already asserted at boot today, and that assertion stays
- `aggregates/ministry-profile.jsonl` or `reference/ministries.jsonl` — **newly forbidden** by FR-151; these are on the first load today
- `aggregates/composition.jsonl` — forbidden by FR-127
- `lib/search.js`, `lib/constituency.js`, `lib/profile.js`, `lib/tokenise.js`, `lib/chart.js` — **newly forbidden**; all five are on the first load today
- anything under `views/` — FR-128
- `aggregates/subject-trends.jsonl` — forbidden **always**, at 13,178,975 B raw; the trend is derived from the search index instead

## Boot assertions

`boot()` already refuses if a search or seat file was requested before it renders. That mechanism extends to the full set:

```
boot() throws if, before first render, any of these has been requested:
  searchAssetsRequested()        — exists today
  seatAssetsRequested()          — exists today
  ministryAssetsRequested()      — NEW (FR-151)
  compositionAssetsRequested()   — NEW (FR-127)
  any module under views/        — NEW (FR-128)
```

The assertion must **throw**, not warn: feature 001 chose a thrown error here so a discipline breach fails loudly rather than appearing as a slightly larger number nobody reads.

## Routing

| Rule | Requirement |
|---|---|
| Switch mechanism | `hashchange`, over a static `id → {heading, module, loaders}` map. No router library (FR-148). |
| One at a time | Exactly one view rendered (FR-146). |
| Deep link | Opening `#<id>` in a fresh tab renders that view (FR-147, SC-017). |
| Back / forward | Moves between views, never off the page (FR-147). |
| Unknown or empty hash | Resolves to `coverage` — not an error, not an empty view (FR-153, SC-017). |
| Current view cue | `aria-current="page"` **plus** a non-colour cue (FR-149). |
| Focus on switch | Moves to the new view's `<h2>`, `tabIndex = -1`. Without this a keyboard user is left where the old view was. The page already uses this pattern on `.result-subject`. |
| Return to a view | Renders from retained state; refetches nothing (FR-152, SC-018). |
| Navigation geometry | ≥44 px targets, no horizontal scroll at 390 px (FR-150). |

## Module loading

```js
// Required form: relative specifier, awaited once, memoised.
const mod = viewModules[id] ??= await import(`./views/${name}.js`);
```

- Specifiers MUST be relative (`./…`) for dynamic imports as well as static ones.
- **The existing check does not cover this form.** `test_no_page_file_imports_anything_but_a_relative_path` matches `(?:from|import)\s+["']…["']`, which requires whitespace after `import` and so never matches `import("./x.js")` — verified in [research.md](../research.md) R6. The pattern must be widened before any dynamic import is added, or the first one lands unchecked.
- A failed `import()` MUST degrade to a visible, worded message in that view and MUST NOT break the shell or the other views.

## Degradation

A view whose data or module fails to load shows a worded message naming what is missing, and the rest of the page keeps working. This is FR-010's quiet degradation, unchanged — the shell and its coverage view depend on nothing a view module fetches, so a view failing can never blank the coverage statement.
