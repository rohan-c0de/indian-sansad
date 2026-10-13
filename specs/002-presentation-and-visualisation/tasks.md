---

description: "Task list for 002-presentation-and-visualisation"
---

# Tasks: Presentation and Visualisation for the Published Lok Sabha Question Record

**Input**: Design documents from `/specs/002-presentation-and-visualisation/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel — different files, no dependency on an incomplete task
- **[Story]**: `[US1]`–`[US8]`, mapping to the eight user stories in `spec.md`
- Exact file paths are given in every task

## Numbering

**Task IDs start at T101.** Feature 001 used T001–T100, and this spec and `gate-evidence.md` both cite 001's tasks by number (T082, T091, T094). Continuing rather than restarting keeps every reference unambiguous — the same reason the requirements here are numbered FR-101 upward.

## Tests

Test and check tasks are included because the spec requires them as requirements, not as a methodology choice: FR-112 requires an automated check *changed*, FR-137 requires a *production caller*, FR-138 requires a check that classifies *mechanically*, and all 25 success criteria are framed as things to run. The constitution is explicit: "A gate is passed by evidence — an executed check and its output — not by assertion."

## Path Conventions

Page work is in `web/` (page root on the published branch). Pipeline work is in `src/sansad/`, checks in `tools/`, tests in `tests/`. `data/published/` is **read-only for this entire feature** (FR-140).

## Ordering Decisions

Three stories are P1 and the tie is broken by rework cost, not by importance:

1. **US2 (tokens and type) first** — it restyles in place and moves nothing structural. Done after US1, the new result row would have to be restyled too.
2. **US3 (router and split) second** — every chart needs a view to live in, and splitting 2,307 lines of `app.js` is the riskiest change in the feature. Do it while the page is still simple.
3. **US1 (density) third** — it then lands in the new vocabulary and the new structure once, rather than twice.

Each remains independently testable, and US1 can be pulled forward if the readability fix is wanted soonest — at the cost of restyling the new row in US2.

**US8 is independent of every page story** and can run at any point, or in parallel by a second person.

---

## Phase 1: Setup

**Purpose**: the dependency, the font files, and the baseline that makes SC-024 checkable

- [X] T101 Add `fonttools[woff]` to the **dev** extra only in `pyproject.toml` (never to `dependencies`, which stays exactly `httpx>=0.28,<1.0` and `polars>=1.17,<2.0`); add a comment stating it exists solely so `tools/check_font_scope.py` can read a `woff2` `cmap`, that `.woff2` is in the guard's `UNSCANNABLE_SUFFIXES` so no existing check sees inside a font, and that it never reaches the serving path (Constitution Principle I)
- [X] T102 Download the three Latin-subset `woff2` files into `web/fonts/` from the exact URLs recorded in `research.md` R1, naming them `newsreader-600.woff2`, `ibm-plex-sans-400.woff2` and `ibm-plex-sans-600.woff2`; verify each byte count against the recorded figures — **23,888 / 17,604 / 19,192 B, totalling 60,684 B** — and fail rather than proceed if any differs
- [X] T103 [P] Copy the two SIL Open Font License 1.1 texts to `web/fonts/OFL-Newsreader.txt` and `web/fonts/OFL-IBMPlexSans.txt` from `github.com/google/fonts/ofl/{newsreader,ibmplexsans}/OFL.txt`; confirm each opens with its recorded copyright line ("Copyright 2020 The Newsreader Project Authors" and "Copyright © 2017 IBM Corp. with Reserved Font Name \"Plex\"")
- [X] T104 [P] Write `web/fonts/PROVENANCE.md` recording, per file: the `fonts.gstatic.com` URL, the `css2` query that produced it, the subset (`latin`), the byte count, the acquisition date, and the licence file beside it. Record that the files are redistributed **as Google publishes them**, unmodified, which is why IBM Plex's Reserved Font Name clause is not engaged
- [X] T105 Record the pre-work baseline in `specs/002-presentation-and-visualisation/baseline.md`: `git rev-parse HEAD`, and `git status --porcelain data/published/` (expected empty), so SC-024 can be checked at the end against a known starting point rather than against memory

**Checkpoint**: the fonts and their licences are in the tree; no page file has changed yet

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the measurement harness every story is verified with. US1's height ceiling, US7's tap targets, and SC-011's screenshots all read off this.

**⚠️ CRITICAL**: no story can be *verified* until this phase is done, and a story that cannot be verified is not done.

- [ ] T106 Change `SCREENS` in `tools/drive_page.mjs` from `{390, 1280}` to the four widths SC-011 requires — `{width: 390, height: 844, handheld: true}`, `{width: 768, height: 1024, handheld: true}`, `{width: 1024, height: 768, handheld: false}`, `{width: 1440, height: 900, handheld: false}` — keeping CDP device-metric emulation rather than window resizing, and keeping scale 1 for the reason already recorded in that file (`captureBeyondViewport` at 390 px and scale 2 never returned)
- [ ] T107 Add a tap-target sweep to `tools/drive_page.mjs`: at each width, for every `a, button, input, select, [tabindex]:not([tabindex="-1"])`, read `getBoundingClientRect()` and report every element under **44 px in either dimension** with its selector and measured box. Report, do not throw — the sweep must enumerate *all* failures in one run, not stop at the first
- [ ] T108 [P] Add a horizontal-scroll assertion to `tools/drive_page.mjs`: at each width assert `document.documentElement.scrollWidth <= document.documentElement.clientWidth`, reporting the overflowing element when it fails (SC-007)
- [ ] T109 [P] Add a result-list height measurement to `tools/drive_page.mjs`: after a 25-result query at 390 px, report the rendered height of the result list in CSS px (SC-006). Record the **current** figure before any densification work, so the reduction is measured against a number from this harness rather than against the ~6,000 px estimate
- [ ] T110 Attempt `prefers-reduced-motion` emulation in `tools/drive_page.mjs` via CDP `Emulation.setEmulatedMedia` with `features: [{name: "prefers-reduced-motion", value: "reduce"}]`, and assert no element reports a non-`none` `transition-duration` or `animation-name`. **If the call proves unreachable, record that in `research.md` and fall back** to a static assertion that every `transition` and `animation` in `web/style.css` sits inside a `@media (prefers-reduced-motion: reduce)` guard — then report SC-010 as a stylesheet assertion, never as a browser check
- [ ] T111 Extend `tools/drive_page.mjs` to capture a screenshot **per view per width** once the router exists, naming them `<nn>-<view>-<width>.png` in `page-screens/`; until Phase 4 lands, capture per section as today so the harness stays runnable
- [ ] T112 Add a `--json` summary to `tools/drive_page.mjs`'s report covering the three new sweeps, so `make validate` can read pass/fail without parsing prose

**Checkpoint**: `make test-page` runs at four widths and reports tap targets, horizontal scroll and list height. The pre-work figures are recorded.

---

## Phase 3: User Story 2 — The record looks like a record, not a template (Priority: P1) 🎯 First shippable increment

**Goal**: the palette, the self-hosted type, the starred asterisk, the figure-and-denominator pairing, and the removal of the four tells — with every contrast ratio recomputed and recorded.

**Independent Test**: load the page; confirm the four named tells are gone, every colour resolves to a recorded token, both families serve from this host, and every computed ratio is recorded and clears its floor. Needs no new view and no structural change.

### Checks for User Story 2

- [ ] T113 [P] [US2] Write `tools/check_contrast.py`: parse the `:root` token values out of `web/style.css`, recompute every pair with the WCAG relative-luminance formula, and assert text pairs ≥4.5:1 and meaning-carrying marks ≥3:1. Any pair **below** a floor is a pass only if the stylesheet records it together with what carries the meaning instead; an unrecorded sub-floor pair fails. Expected figures per `contracts/design-tokens.md`: `--ink` 13.38:1 / 15.19:1, `--ink-soft` 6.48 / 7.36, `--house` 6.75 / 7.66, `--mark` 6.95 / 7.88, `--series-2` 3.75 / 4.25; recorded sub-floor pairs `--paper`/`--sheet` 1.13:1, `--house`/`--mark` 1.03:1, `--series-2`/`--house` 1.80:1
- [ ] T114 [P] [US2] Write `tools/check_font_scope.py`: for each file in `web/fonts/*.woff2`, use `fontTools` to read the `cmap` and assert **no codepoint in U+0900–U+097F** (FR-111); assert the family name and weight match the `@font-face` declaration; assert an `OFL-*.txt` sits in the same directory; and assert the total payload is ≤95,000 B across ≤4 files (SC-002). Print each file's byte count and codepoint range
- [ ] T115 [US2] Add `check-contrast` and `check-fonts` targets to `Makefile` invoking the two tools above with `$(VENV_PY)`, and add both to the `validate` target's check list so they gate alongside the existing ones

### Implementation for User Story 2

- [ ] T116 [US2] Replace the `:root` palette in `web/style.css` with the seven recorded tokens — `--paper #EEEFEA`, `--sheet #FDFDFB`, `--ink #15253A`, `--ink-soft #4A5663`, `--house #1F5D3E`, `--mark #8C3325`, `--series-2 #5F7D94` — and rewrite the file's header comment with every ratio from `contracts/design-tokens.md`, including the three sub-floor pairs and what carries the meaning instead. Delete the superseded `--ground`, `--surface`, `--muted`, `--accent` and `--bar-unstarred` tokens rather than aliasing them, so no rule can keep using the old ramp unnoticed
- [ ] T117 [US2] Add the three `@font-face` blocks to `web/style.css` with `font-display: swap`, relative `url(fonts/…)` paths, and the `unicode-range` recorded in `contracts/design-tokens.md`; set `--font-head: "Newsreader", Charter, "Iowan Old Style", "Palatino Linotype", Georgia, serif` and `--font-body: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`, keeping the current system stacks as the fallbacks (FR-110). `--font-mono` ships no file and stays on system faces
- [ ] T118 [US2] Normalise every `font-weight` in `web/style.css` to the two shipped weights, **400 and 600**: the file uses `600` ×19, `700` ×17 and `400` ×1 today, and each `700` must become `600` or the browser synthesises a bold that reads as a defect on a serif heading (research R13)
- [ ] T119 [US2] Delete all thirteen uppercase letter-spaced label rules from `web/style.css` — at lines 236, 295, 326, 403, 496, 574, 701, 818, 842, 880, 1228, 1327 and 1553 as the file stands — replacing each label's role with size, weight, colour or family rather than with a new variant of the same device (FR-115)
- [ ] T120 [US2] Remove the `.eyebrow` rule from `web/style.css` and the eyebrow element from `web/index.html` ("Read from the published record, not typed into this page"), moving that statement into the coverage view's own prose where it is a sentence rather than a label (FR-115)
- [ ] T121 [US2] Replace the single uniform `.card` treatment in `web/style.css` with per-content treatments, and make every surface distinction a reader needs carry on a rule, a boundary or space — **never on the `--paper`/`--sheet` fill difference, which is 1.13:1** (FR-108). Assert `--house` appears in no `background` or `background-color` declaration (FR-106)
- [ ] T122 [US2] Replace the three italic rules in `web/style.css` — `.not-stated` (line 425), `.result-subject-missing` (1313), `.result-no-asker` (1376) — with `--ink-soft` plus the word that already carries each, since no italic face ships and synthetic oblique must not be used. All three mark absence and all three are already worded, so the italic was a third redundant cue
- [ ] T123 [US2] Add the starred-question device: the asterisk Parliament itself prints, rendered for `type == "STARRED"` only, with the word "starred" present for assistive technology and `aria-hidden` on the glyph; unstarred questions carry **no** mark (FR-113). Implement once in `web/app.js` as a shared helper so the search, seat and chart views all render it identically
- [ ] T124 [US2] Add a shared figure-and-denominator helper to `web/app.js` and a matching rule in `web/style.css`, rendering a count against its total as one typographic unit with its `unit` from `aggregates/counting-basis.jsonl` (FR-114). Per `data-model.md`, `value <= total` must hold **except** across the published overlap the `question` basis declares — a partly-resolved question is counted both in its identified askers' files and in the unresolved total — where the pairing must carry the basis statement rather than a quietly impossible percentage
- [ ] T125 [US2] Narrow `test_the_stylesheet_fetches_nothing` in `tests/unit/test_page_fetch_layer.py` per FR-112: replace `assert "url(" not in body` with assertions that every `url()` is a **relative** path, resolves inside `web/`, and names a file that **exists**; keep `assert "@import" not in body`. Update the test's docstring to say why the invariant narrowed rather than disappeared. Leave `test_no_page_file_names_another_host` untouched — it matches hosts, and a relative path names none

**Checkpoint**: the page is restyled in place, serving three same-origin fonts, with every ratio recorded and checked. Nothing structural has moved. **Deployable.**

---

## Phase 4: User Story 3 — A reader moves between views instead of scrolling past them (Priority: P1)

**Goal**: eight switchable hash-routed views; `app.js` split so no unopened view's code or data is on the first load.

**Independent Test**: load the page and confirm exactly one view renders; switch to each view and confirm the others do not render; open each hash in a fresh tab and confirm it renders; press back and confirm it returns to the previous view rather than leaving the page.

**⚠️ Riskiest phase in the feature**: 2,307 lines move. Move code without editing it, then edit, and run `make test-page` after each move.

### Checks for User Story 3

- [ ] T126 [US3] Widen `test_no_page_file_imports_anything_but_a_relative_path` in `tests/unit/test_page_fetch_layer.py` to match the **call** form of `import`. The current pattern `(?:from|import)\s+["']([^"']+)["']` requires whitespace after `import` and so never matches `await import("./x.js")` — verified in `research.md` R6. **This task must land before T130 adds the first dynamic import**, or the first one lands unchecked
- [ ] T127 [P] [US3] Write `tests/unit/test_view_routes.py` asserting the static view map in `web/app.js` carries exactly the eight ids in `contracts/view-routes.md` (`coverage`, `search`, `seat`, `ministry`, `compare`, `load`, `composition`, `licence`), that every `module` value is a relative specifier or `null`, and that `coverage` is the landing view (FR-153)
- [ ] T128 [US3] Extend `boot()`'s pre-render assertions in `web/app.js` beyond today's `searchAssetsRequested()` and `seatAssetsRequested()` to add `ministryAssetsRequested()` (FR-151), `compositionAssetsRequested()` (FR-127) and a check that no module under `views/` has been requested (FR-128). It must **throw**, not warn — feature 001 chose a thrown error here so a discipline breach fails loudly instead of appearing as a slightly larger number nobody reads

### Implementation for User Story 3

- [ ] T129 [US3] Add the view navigation and eight view containers to `web/index.html`, each container holding an `<h2>` with `tabIndex = -1`; keep the skip link pointing at the view container so it works per view. Remove the five stacked `<section>` wrappers' always-rendered status paragraphs for views that are no longer on the first load
- [ ] T130 [US3] Implement the router in `web/app.js`: a static `id → {heading, module, loaders}` map, a `hashchange` listener, exactly one view rendered at a time (FR-146), memoised `import()` with relative specifiers, an unknown or empty hash resolving to `coverage` (FR-153), and a failed `import()` degrading to a worded message in that view without breaking the shell or the other views
- [ ] T131 [US3] Add view-switch accessibility to `web/app.js`: move focus to the newly rendered view's `<h2>` on switch — without it a keyboard user is left where the old view was — and set `aria-current="page"` on the active navigation item (FR-149). Use the same `tabIndex = -1` focus-move pattern the page already uses on `.result-subject`
- [ ] T132 [US3] Style the view navigation in `web/style.css`: a non-colour cue for the current view in addition to `aria-current` (FR-149), ≥44 px targets, and no horizontal scroll at 390 px with eight items (FR-150) — the one geometry in this feature that is new rather than inherited
- [ ] T133 [US3] Move `web/app.js` lines 772–1188 to a new `web/views/ministries.js` — `renderProfileResult`, `renderCompareResult`, `sessionOptions`, `ministryOptions`, `buildProfileView`, `buildCompareView`, `bootViews` — exporting a mount function per view and importing its shared helpers from the shell. Measured at 14,859 B raw / 4,560 B compressed. **Move without editing**, then run `make test-page`
- [ ] T134 [US3] Move `web/app.js` lines 1189–1672 to a new `web/views/search.js` — the `search` state, `resultItem`, `ignoredBlock`, `searchOrderNote`, `renderSearchEmpty`, `searchSummary`, `renderSearchResults`, `searchDigestError`, `showMore`, `ensureSearchData`, `runSearch`, `buildSearchView`. Measured at 16,685 B raw / 5,516 B compressed. **Move without editing**, then run `make test-page`
- [ ] T135 [US3] Move `web/app.js` lines 1673–2307 to a new `web/views/seat.js` — the `seatView` state through `buildConstituencyView`. Measured at 22,724 B raw / 6,412 B compressed. **Move without editing**, then run `make test-page`
- [ ] T136 [US3] Keep lines 1–771 in `web/app.js` as the shell — the DOM helpers, `renderCoverage`, `renderSessions`, `renderLicence`, `renderUnavailable`, `boot`, and the shared view helpers at 581–771 (`views` state, `option`, `labelledSelect`, `basisBlock`, `changeText`, `statusStrip`, `mixTable`) — and export those helpers for the view modules. Lines 89–580 were verified to reference **none** of `stackedColumns`, `legend`, `seatById`, `seatsInState`, `stateSubjects`, `positionsFor`, `loadSearchIndex`, `profileSessions`, `selectSpan` or `subjectTally`, so the seam needs no untangling. Target: 8,103 B compressed, from the monolith's 21,372 B
- [ ] T137 [US3] Move `aggregates/ministry-profile.jsonl` and `reference/ministries.jsonl` off the first load in `web/lib/fetch.js`, to first open of whichever of `ministry`, `compare`, `load` or `search` comes first — read **once** between all four, not per view (FR-151). These two are 17,552 + 1,856 B on the wire today and are 20% of the current first load
- [ ] T138 [US3] Implement per-view state retention in `web/app.js` so a reader's query, chosen state or chosen ministry survives switching away and back, and nothing already fetched is fetched again (FR-152, SC-018). Per `data-model.md`, a `degraded` view must stay `degraded` rather than reverting to `unopened`, which would refetch on every return

- [ ] T190 [US3] Add router assertions to `tools/drive_page.mjs` (SC-017, SC-018, FR-147, FR-153): for each of the eight hashes, load it **directly in a fresh page** and assert that view renders and the others do not; assert an unknown hash (`#nonsense`) and an empty hash both render `coverage`; assert the back button returns to the previous view rather than leaving the page; and assert that switching away from a view with results and returning issues **no new request** and retains the results. This is the browser-level counterpart to T127, which checks the static view map in pytest and cannot see whether a hash actually renders anything. **Numbered T190 rather than T139 to avoid renumbering 51 downstream tasks — the same convention the spec uses for FR-145**

**Checkpoint**: eight deep-linkable views, one rendered at a time, with the first load reduced to the 14 requests in `contracts/view-routes.md`, and T190 asserting all of it in a browser. **Deployable.**

---

## Phase 5: User Story 1 — A reader can scan a result list instead of scrolling past it (Priority: P1)

**Goal**: the five-pair label-and-value block becomes a scannable row; twenty askers stop being twenty lines.

**Independent Test**: run a 25-result query, measure the list height at 390 px against the 2,800 px ceiling, and confirm the subject, date, ministry, link status and askers are all still present.

- [ ] T139 [US1] Replace the five-pair `<dl class="result-meta">` in `resultItem` in `web/views/search.js` with a subject heading plus a single meta line carrying the date, the ministry name and the link status, and the starred asterisk from T123 (FR-101). All five fields stay present and reachable — this is a change of presentation, not of content
- [ ] T140 [US1] Render a question's asking members **inline** in `web/views/search.js` rather than one per line, as a figure-and-denominator pairing from T124 (FR-102). A question asked by twenty members is currently twenty lines of its own; the published record has one asked by 47
- [ ] T141 [US1] Where askers are abbreviated for length in `web/views/search.js`, state how many are not shown and keep the full set reachable (FR-103). Silent truncation is a breach; the existing `by-member` list already does this correctly and its wording is the model
- [ ] T142 [US1] Keep every flag carried by a **word** in the denser row in `web/views/search.js` — an unrecognised ministry id, a partial link, a missing subject, a question the digest does not carry — never by colour, position or density alone (FR-104). Density is the new risk this requirement did not previously face
- [ ] T143 [US1] Add the denser result-row rules to `web/style.css`, handling the long-subject case: a subject line that wraps to three or four lines at 390 px must not break the row, and a one-result or zero-result list must not look broken
- [ ] T144 [US1] Apply the same denser treatment to the member-questions list in `web/views/seat.js` (`renderMemberQuestions`, the second five-pair `<dl class="question-meta">` in the codebase), so the two lists do not diverge into two vocabularies
- [ ] T145 [US1] Measure the result-list height with the T109 sweep and record it in `specs/002-presentation-and-visualisation/baseline.md` beside the pre-work figure. **If the built row cannot reach 2,800 px, report the measured figure and stop** — the ceiling is derived, not measured, and retargeting it is the owner's call, not a quiet widening to match what was built

**Checkpoint**: the two problems the feature exists to fix are both fixed. **This is the full MVP.** Deployable.

---

## Phase 6: User Story 7 — Every control can actually be reached and operated (Priority: P2)

**Goal**: the four measured tap-target defects fixed, focus visible everywhere, reduced motion respected.

**Independent Test**: run the T107/T108/T110 sweeps at all four widths and tab through every view.

- [ ] T146 [US7] Fix the skip link in `web/style.css`: `min-height: var(--tap)` at line 185 **cannot apply** — the `<a>` is a non-replaced inline element with no `display` change, which is why it measures 25 px on the live site. Give it `display: inline-block` (or grid centring) so the 44 px takes effect, and keep it visible only on focus
- [ ] T147 [US7] Fix the three footer links measured at 38 px, 17 px and 17 px in `web/style.css`: `.licence-links li` and its anchors carry no height rule at all. Give the anchors a 44 px minimum touch box without forcing 44 px of visual line-height on a list of links (FR-130)
- [ ] T148 [P] [US7] Audit every remaining interactive element against the T107 sweep at all four widths and fix each failure in `web/style.css` — the view navigation from T132, the selects, the search inputs, "Show 25 more", and the member-open controls (FR-130, SC-008)
- [ ] T149 [P] [US7] Ensure a visible focus ring on every interactive element in `web/style.css`, against **whichever ground it sits on** — `--mark` is 6.95:1 on `--paper` and 7.88:1 on `--sheet`, so one ring colour serves both, but a ring on a `--house` rule or a chart mark needs checking separately (FR-131)
- [ ] T150 [P] [US7] Add a `@media (prefers-reduced-motion: reduce)` block to `web/style.css` disabling every transition and animation, view switching included (FR-132), and confirm it with T110's emulation — or with T110's recorded fallback, reported as a stylesheet assertion rather than a browser check
- [ ] T151 [US7] Fix every horizontal-scroll failure the T108 assertion reports at 390 px in `web/style.css`, keeping wide content scrolling inside its own `.table-wrap`-style container rather than letting the page scroll (FR-133). The `overflow-x: hidden` on `html` is belt-and-braces and must not be the thing doing the work

**Checkpoint**: every control reachable and operable at four widths, with the measured evidence.

---

## Phase 7: User Story 4 — Question load across the covered sessions, as a shape (Priority: P2)

**Goal**: the whole-House session series, the matched-subject trend, and the two-ministry comparison as a chart.

**Independent Test**: read each series off its chart and confirm every value matches the table beside it and reproduces by hand from the published record.

### Chart primitives

- [ ] T152 [US4] Add `--series-2 #5F7D94` to the chart series in `web/lib/chart.js`, replacing `--bar-unstarred #6F88BD`, with series 1 as `--house #1F5D3E`. Record in the file's header that `--series-2` is **1.80:1 against `--house`** and that the surface-colour stroke is therefore **required, not preferred**: no colour can clear 3:1 against both the near-white grounds and `--house`, proved in `contracts/design-tokens.md`. Keep the existing hatch for any third series — never a lighter colour
- [ ] T153 [P] [US4] Add `groupedColumns` to `web/lib/chart.js` for two independent totals side by side, where stacking would imply a sum that means nothing. Same accessibility contract as `stackedColumns`: `role="img"` with `<title>`/`<desc>`, internals hidden from assistive technology, HTML column labels rather than SVG text so they scale with the reader's font size
- [ ] T154 [P] [US4] Add `horizontalBars` to `web/lib/chart.js` for category sets too long to label vertically at 390 px — 25 subject lines, 42 party categories. Same accessibility contract

### Implementation for User Story 4

- [ ] T155 [US4] Add the whole-House question-load view to `web/views/ministries.js`, summing `aggregates/ministry-profile.jsonl` across ministries per session into a 21-column stacked series by question type, with the `question` basis rendered from `aggregates/counting-basis.jsonl` and **95,268** as the window denominator (FR-116, FR-120)
- [ ] T156 [US4] Add the matched-subject trend to `web/views/search.js`, derived from the search index **already in memory** with **zero further fetches** (FR-145, SC-019): `positionsFor` already runs the cumulative sum over the gap-encoded postings, and `prefixes[doc_prefix[position]]` yields each matched document's session and starred/unstarred type. Verified against the published index — `under` resolves to 6,254 documents across all 21 sessions and 41 buckets. Denominators: the matched total and 95,268. **`aggregates/subject-trends.jsonl` must never be fetched** — it is 13,178,975 B raw
- [ ] T157 [US4] Add a grouped chart to the two-ministry comparison in `web/views/ministries.js`, on one scale with the same counting basis stated once for both and each ministry's own total as its denominator (FR-117). The comparison is text and a table only today — the sole charted view in the current page is the single-ministry profile
- [ ] T158 [US4] Render a table beside each of the three new charts — the House series and comparison in `web/views/ministries.js`, the subject trend in `web/views/search.js` — as the form a keyboard and screen reader reach (FR-121), reusing `mixTable`'s shape from `web/app.js` so the charted views do not grow four separate table styles
- [ ] T159 [US4] Handle the three data hazards these charts actually hit, each a real property of the record: session `lok-sabha/18/8` has `sitting_days: 0` and must render as a labelled zero rather than a gap and must not divide by zero; a single-column subject trend must not read as a broken chart; and a chart drawn before its data arrives needs worded loading and degraded states
- [ ] T160 [US4] Add chart assertions to `tools/drive_page.mjs`: for every chart, the counting basis is rendered, every figure has a denominator, a table beside it carries the same figures, and every series is named in text (SC-014, SC-015)

**Checkpoint**: three new series, each reproducible by hand, each with its table.

---

## Phase 8: User Story 5 — How the House composition changed between the two terms (Priority: P2)

**Goal**: party, state and terms-served for the 17th and 18th Lok Sabha — the three dimensions the aggregate carries and the three FR-008 permits.

**Independent Test**: request one term's breakdown and confirm the categories sum to that term's total membership, with any absent attribute in an explicit "not stated" category.

- [ ] T161 [US5] Add a `composition` loader to `web/lib/fetch.js` reading `aggregates/composition.jsonl` on **first open of the composition view only** (FR-127) — 25,237 B raw, 1,835 B on the wire, and fetched by nothing in `web/` today. Add the `compositionAssetsRequested()` predicate T128 asserts against
- [ ] T162 [US5] Create `web/views/composition.js` rendering the three published dimensions as horizontal bars paired by term, with `total_members` as the denominator — **559 for the 17th, 544 for the 18th**, verified — and the `member` counting basis rendered from `aggregates/counting-basis.jsonl` (FR-118, FR-120)
- [ ] T163 [US5] Count a member whose party, state or terms-served is absent in an explicit **"not stated"** category in `web/views/composition.js`, never omitted — omitting it would make the categories stop summing to the total (FR-118)
- [ ] T164 [US5] Handle the long category list in `web/views/composition.js`: **42 party categories per term** cannot all show at 390 px. Show a head and state the remainder as a counted group, matching what `make composition LS_TERM=18` already prints — twelve categories, then "and 30 further categories" carrying 51 members, reconciling to 544 (FR-103). The chart matches that treatment rather than inventing its own
- [ ] T165 [US5] Keep the `terms_served` dimension readable in `web/views/composition.js` where one category holds most of the total — **282 of 544** members in the 18th served exactly one term, which flattens every other bar, and the long tail must not round to an invisible zero-width bar
- [ ] T166 [US5] Add a test in `tests/unit/test_composition_view.py` asserting the view's categories reconcile to `total_members` for both terms and that it requires **no term or session date** — every one reads "not stated", across 9,986 term records and all 21 sessions (FR-124)

**Checkpoint**: composition on the page for the first time, reconciling to the published totals.

---

## Phase 9: User Story 6 — What a state's members actually ask about (Priority: P3)

**Goal**: a state's 25 most-asked subject lines as a shape rather than a 25-row table.

**Independent Test**: pick a state and confirm each count and denominator matches the published rows for it.

- [ ] T167 [US6] Render a state's 25 published subject lines as horizontal bars in `web/views/seat.js` using T154's primitive, each against `state_questions` as the denominator, reading the `aggregates/state-subjects.jsonl` already fetched on first open of the seat view — **no new bytes** (FR-119, FR-120)
- [ ] T168 [US6] State the `state-question` counting basis explicitly in `web/views/seat.js`, rendered from `aggregates/counting-basis.jsonl`, and make clear it is **not the same unit** as the question counts elsewhere on the page (FR-120)
- [ ] T169 [US6] Give the subject ordering a stated tie-break in `web/views/seat.js` — several of a state's 25 lines share a count, so order is not determined by count alone — following the search view's existing practice of rendering its ordering statement from the comparator rather than retyping it
- [ ] T170 [US6] Keep the table beside the chart in `web/views/seat.js` as the authoritative form (FR-121), replacing nothing: the table that exists today stays and the chart is added beside it

**Checkpoint**: all five charts built. Every reader-facing story complete.

---

## Phase 10: User Story 8 — The maintainer is told when the record's quality slips (Priority: P3)

**Goal**: the two dead FR-011 signals wired, and the field-scope check strengthened.

**Independent Test**: for each of the four signals, confirm a production caller outside the definition module and outside the test suite. Run the field-scope diff and confirm `representations.member_name` is classified mechanically.

**Independent of every page story** — can run in parallel from the start.

- [ ] T171 [US8] Change `resolution_rate_below_target` in `src/sansad/signals/alerts.py` to trigger on a **drop against a previous rate** rather than against an absolute target: add the previous value as a parameter and fire only when `current < previous`. The automatic rate is **0.947831** against an `sc_002_target` of **0.95**, with `sc_002_met_on_automatic_rate: false` already published — so an absolute trigger fires on every run for a state the owner has accepted, which is no information and is exactly the routine upkeep Principle II forbids. Keep the existing `is_automatic_rate` severity split: `NOTICE` for automatic, `DEGRADED` for published
- [ ] T172 [US8] Add a previous-publication reader to `src/sansad/publish/` returning, from a `--previous` directory: whether it exists, `resolution_rate_automatic` and `resolution_rate_including_assertions` from its `manifest.json`, and a `question_id → resolution_status` map from its `by-session/*.jsonl`. All three fields are published and verified present. Return an explicit "absent" result rather than raising, because `continue-on-error: true` on the workflow's checkout makes absence a valid state
- [ ] T173 [US8] Call `resolved_transitions_out` from `src/sansad/cli.py` at the existing `--previous` site beside `retain_previous` (around line 304), for every question whose previous `resolution_status` was `resolved` and whose current status is not (FR-134). Payload is **question ids only** — no name, no value — matching `excluded_keys_in`'s rule that the offending path is reported and never the value. The workflow already checks this snapshot out and its own comment names this exact purpose
- [ ] T174 [US8] Call `resolution_rate_below_target` from `src/sansad/cli.py` at the same site, once per rate, passing the previous value from T172 (FR-135)
- [ ] T175 [US8] Record **"no comparison made"** in `src/sansad/cli.py` when the previous publication is absent or carries no `manifest.json`/`by-session/`, naming which comparison was skipped and why (FR-136). It must not report a pass and must not raise a signal — a valid first run and a broken comparison have to be distinguishable in the log
- [ ] T176 [US8] Invert the assertion in `tests/unit/test_state_transitions.py` that `resolved_transitions_out` has **no** caller, so it now asserts a caller exists — **inverted, not deleted**, the same treatment feature 001 gave the "Not built yet" assertion when the search view was finally built. A deleted assertion lets the fact silently revert; an inverted one keeps it under test. Add the equivalent for `resolution_rate_below_target` (FR-137, SC-020)
- [ ] T177 [P] [US8] Add tests in `tests/unit/test_signals.py` against two seeded snapshots: a `resolved` → `ambiguous` transition raises with the right ids and no personal attribute; an unchanged 94.78% raises nothing; a dropped rate raises naming both rates; an absent snapshot records "no comparison made"; and the visitor-facing record is unchanged across a run that raised a signal (FR-139, SC-021)
- [ ] T178 [US8] Add a declared name-form synonym set to `src/sansad/model/member.py` alongside `PUBLISHED_FIELDS` and resolve `representations.member_name` through it in the field-scope diff in `tools/guard_no_raw_payloads.py` (FR-138). **Renaming the published key is not available** — FR-140 forbids changing `data/published/` and the key is pinned by `tests/contract/test_constituency_reference.py` — so the synonym is the only remedy of the two `gate-evidence.md` names. Note the ingest allowlist is **not** the defect: `field_allowlist.py` already carries `membername`
- [ ] T179 [P] [US8] Add a test in `tests/unit/test_guard_scopes.py` asserting the field-scope diff reports `representations.member_name` as an FR-008 name form rather than as an unclassified field, so the classification stops resting on a human reading the contract (SC-022)

**Checkpoint**: all four FR-011 signals wired; the field-scope check as strong as it reads.

---

## Phase 11: Polish, Measurement & Gate Evidence

**Purpose**: the figures FR-129 requires, the gate evidence the constitution requires, and the claims a green run does not support

- [ ] T180 Capture screenshots at 390, 768, 1024 and 1440 px for all eight views via `make test-page SCREENS=1` into `page-screens/`, replacing the two-width set (SC-011). A screenshot proves a layout rendered, never that it reads well — note that where they are reported
- [ ] T181 Re-run the Language gate's codepoint scan over the whole repository **including the three font binaries** and record it in `specs/002-presentation-and-visualisation/gate-evidence.md` (SC-013). The existing scan covered `.jsonl` and the search index; `.woff2` is in `UNSCANNABLE_SUFFIXES` so the guard gives fonts no coverage and `check_font_scope.py` is the only thing that sees inside one. Feature 001's Language evidence **cannot be inherited** for files that did not exist then **Runs before T184 deploys**: this is the only check that sees inside a font, and a font reaching the published branch unchecked cannot be un-published
- [ ] T182 Re-run the Member-fields gate against what will actually be published and record it in `gate-evidence.md` (SC-022, SC-023). `aggregates/composition.jsonl` is the one newly reachable set: confirm its member attributes are `state` and `party` as **categories, not as attributes of a named person** — no member id and no name form — and note that FR-151 **narrows** the page's reachable surface rather than widening it **Runs before T184 deploys**: the constitution requires this gate "re-run against what will actually be published" *before publishing*, and Principle V's "published" covers "any interactive page"
- [ ] T183 [P] Verify `data/published/` is untouched with `git status --porcelain data/published/` against the T105 baseline commit (SC-024, FR-140). If a refresh ran during the work, diff against that commit and confirm every change is the refresh's own output Runs before T184, because the publish step copies `data/published/` to the branch root
- [ ] T184 Deploy and read the **live** first-load figures from the deployment's response headers — `Content-Length` and `Content-Encoding` per first-load file (FR-129, SC-001, SC-003, SC-004). This **cannot be done locally**: `make serve-local` compresses nothing and `tools/measure_first_load.py` asserts that from the recorded headers every run **Blocked by T181, T182 and T183**
- [ ] T185 Record the measured figures in `spec.md` beside the 2026-10-10 baseline table, against the four ceilings — first load ≤160,000 B, fonts ≤95,000 B, non-font ≤60,000 B, ≤16 requests — with the projection for comparison (~101,537 B across 14 requests, 1.14× the 88,961 B baseline). **A non-font first load that merely holds at 88,961 B fails SC-003 even if SC-001 passes**: that is the criterion's whole purpose
- [ ] T186 Record the Cost, Upkeep and Sources gate evidence in `gate-evidence.md`: the GitHub Pages free tier with the build's share of the 1 GiB ceiling after the fonts; that this feature adds zero recurring manual work and that FR-135's trigger is designed so the signal does not fire on every run; and that no document was opened and no ingest added
- [ ] T187 Add every new check to `make validate` — `check-contrast`, `check-fonts`, the three `drive_page.mjs` sweeps — keeping its four existing design points: it refuses on an unbuilt dataset, runs every check even after one fails, calls the same entry points `quickstart.md` tells a reader to type, and **says what it does not cover on success**
- [ ] T188 Update `quickstart.md` with the measured figures replacing the projections, and update `README.md`'s status section: it still records that "GitHub Pages has not been observed serving the site", which the 2026-10-10 measurements superseded
- [ ] T189 Record the carried UNVERIFIED items in `gate-evidence.md` rather than letting a green run imply them: whether the live font bytes match the `gstatic` `content-length` figures; whether `prefers-reduced-motion` proved reachable through the driver or fell back to a stylesheet assertion; SC-025 (zero cost), observable only over a billing period; and SC-012 locally, which proves only that no off-host request was made *in that run*

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)** — no dependencies
- **Phase 2 (Foundational)** — needs Phase 1; **blocks verification of every story**, so it blocks every story being *done*
- **Phase 3 (US2)** — needs Phase 2
- **Phase 4 (US3)** — needs Phase 3 in practice, not in principle: the router could be built on the old palette, but then every new rule is written twice
- **Phase 5 (US1)** — needs Phase 4, because the result row moves into `views/search.js`
- **Phase 6 (US7)** — needs Phase 4 for the navigation geometry; the four known tap-target fixes (T146, T147) need only Phase 3
- **Phase 7 (US4)** — needs Phase 4 for the views and T152–T154 for the primitives
- **Phase 8 (US5)** — needs Phase 4 and T154
- **Phase 9 (US6)** — needs Phase 4 and T154
- **Phase 10 (US8)** — **needs nothing from Phases 2–9.** Independent of all page work
- **Phase 11 (Polish)** — needs every story that will ship

### Critical path

```
T101-T105  ->  T106-T112  ->  T113-T125 (US2)  ->  T126-T138 (US3)  ->  T139-T145 (US1)
                                                            |
                                   +------------------------+------------------------+
                                   |              |              |                  |
                              T146-T151      T152-T160      T161-T166         T167-T170
                                (US7)          (US4)          (US5)             (US6)
                                   |              |              |                  |
                                   +------------------------+------------------------+
                                                            |
                                                      T180-T189
T171-T179 (US8) ------------------- independent, joins at T184 ------------------->
```

### Within a story

Checks before the implementation they check, except where the check needs the thing to exist. Two orderings are load-bearing rather than stylistic:

- **T126 before T130** — the widened `import()` check must land before the first dynamic import, or the first one is unchecked.
- **T152 before T153/T154/T155/T157/T167** — the series tokens before anything drawn in them.
- **T123 and T124 before T139/T140** — the asterisk and the figure pairing are shared helpers; the denser row consumes them.
- **T130 before T190** — the router must exist before it can be asserted against.

### Parallel Opportunities

- **T103, T104** — licences and provenance, different files
- **T108, T109** — different sweeps in `drive_page.mjs`; **T106, T107, T110, T111, T112 touch the same file and must not run in parallel with them or each other**
- **T113, T114** — the two new check tools, different files
- **T148, T149, T150** — different concerns, though all in `web/style.css`: coordinate or serialise
- **T153, T154** — the two new chart forms, same file: serialise
- **T177, T179** — different test files
- **Phase 10 entire** — runs alongside any page phase, by a second person
- **T181, T182, T186** — three gate-evidence sections, same file: serialise, not parallel

### Same-file conflicts to respect

`web/style.css` is touched by T116–T122, T132, T143, T146–T151; `web/app.js` by T123, T124, T128, T130, T131, T136, T138; `tools/drive_page.mjs` by T106–T112, T160 and T190; `gate-evidence.md` by T181, T182, T186, T189. Within each group, serialise.

---

## Implementation Strategy

### The MVP is Phases 1–5

The feature exists to fix two stated problems: the page is hard to read, and it looks generated. Phase 3 fixes the second, Phase 5 fixes the first, and Phase 4 sits between them because every later view needs somewhere to live. Stop after T145 and both complaints are answered.

1. Phases 1–2 — fonts in the tree, harness measuring at four widths
2. Phase 3 (US2) — **deployable**: restyled in place, nothing structural moved
3. Phase 4 (US3) — **deployable**: eight views, first load cut to 14 requests
4. Phase 5 (US1) — **deployable**: the MVP complete
5. **STOP and VALIDATE** against `quickstart.md` scenarios 1–4

### Incremental delivery after the MVP

Phases 6–9 each add one increment without touching another's files, so any subset ships. Phase 10 ships at any time. Phase 11 runs last, because T184 needs a deployment to read headers from — and inside it the three gates run before that deploy, not after.

### If a ceiling is missed

Three figures in this feature are derived rather than measured, and each has a defined failure behaviour rather than a fudge:

- **SC-006's 2,800 px** — T145 reports the measured height and stops. Retargeting is the owner's call.
- **SC-002's 95,000 B** — T102 fails if any font differs from its recorded byte count. The three faces total 60,684 B, so there is 34,316 B of headroom; a fourth face fits, a fifth probably does not.
- **SC-003's 60,000 B** — T182 reports the measured non-font first load. A figure that holds at 88,961 B is a failure of FR-128 and FR-151, not a rounding matter.

### Notes

- `[P]` means different files and no incomplete dependency — check the same-file conflict list before running two in parallel
- Commit after each task or logical group
- Every checkpoint is a working page; none requires the next phase to have happened
- `data/published/` is read-only for this entire feature. A task that would change it is a task written wrong
