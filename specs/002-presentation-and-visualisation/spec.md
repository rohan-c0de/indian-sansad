# Feature Specification: Presentation and Visualisation for the Published Lok Sabha Question Record

**Feature Branch**: `002-presentation-and-visualisation`

**Created**: 2026-10-10

**Status**: Draft — clarifications resolved 2026-10-10

**Input**: User description: "Presentation and visualisation for the published Lok Sabha question record." Feature 001 produced a correct, complete published record and a page that proves the user stories work. That page is now the only thing a visitor ever sees, and it is both hard to read and generated-looking. The published aggregates also support views nobody has built.

## Scope and Numbering

**This feature changes `web/` only**, plus the three named maintainer-side defects in User Story 8. **Nothing in `data/published/` changes** — not a file, not a field, not a figure, not a counting basis.

**Requirements here are numbered FR-101 upward** so that references to feature 001's `FR-008` (the member-field set), `FR-010` (quiet degradation) and `FR-011` (maintainer signals) stay unambiguous. Where this spec says FR-008 or FR-011 it means feature 001's.

Two blocks are numbered out of sequence, deliberately: **FR-145** sits with FR-116 because it was added when clarification resolved what "question load over twenty-one sessions" meant, and **FR-146 to FR-153** appear before FR-116 because they were added when clarification chose switchable views. They keep the numbers they were assigned rather than being renumbered, so that anything already citing an FR still cites the same requirement. FR numbers are identifiers, not an ordering.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A reader can scan a result list instead of scrolling past it (Priority: P1)

Someone searches a subject and gets back a list they can read down. Today a single search runs about six thousand pixels tall because every result is a five-row label-and-value block — `Question`, `Date`, `Ministry`, `Link status`, `Asked by` — and the asking members under one question are stacked one per line, so a question asked by twenty members is twenty lines of its own.

**Why this priority**: This is the functional half of the stated problem, and it is the thing a visitor hits on their first useful interaction with the record. Search is the most-used view; the result list is where the page is least readable.

**Independent Test**: Run the query the current page is measured on, count the rendered height of the result list at 390 px, and confirm it is under the stated ceiling with the same information still reachable. Can be tested with no palette, typography or structural change at all.

**The shape the owner selected**, as an illustration of FR-101, FR-102, FR-113 and FR-114 together — the information, not the markup:

```
* Drinking Water in Rural Areas
  2021-03-11 · Jal Shakti · linked
  asked by 4 of 4 identified

  Potable Water Supply Schemes
  2021-03-09 · Jal Shakti · linked
  asked by 1 of 1 identified
```

The asterisk is Parliament's own mark for a starred question; the unstarred row below it carries none. The askers are a figure against their denominator on one line, not a stack.

**Acceptance Scenarios**:

1. **Given** a query returning 25 results, **When** the list renders at 390 px, **Then** the list occupies no more than 2,800 px and every result still shows its subject, its date, its ministry, its link status and who asked it.
2. **Given** a question asked by twenty members, **When** its result renders, **Then** the askers are presented inline rather than one per line, and the number of askers is stated as a figure next to its total.
3. **Given** a result whose askers are abbreviated for length, **When** a reader looks at it, **Then** the count not shown is stated — never silently truncated — and the full set is reachable.
4. **Given** a result whose ministry id is not in the reference set, or whose link status is partial, **When** it renders in the denser form, **Then** the flag is still carried by a word and not by colour, position or density alone.

---

### User Story 2 - The record looks like a record, not a template (Priority: P1)

A visitor arriving at the page sees an institutional record of the Lok Sabha rather than something a tool generated. Today the page carries thirteen uppercase letter-spaced label rules, an eyebrow line above the first heading, headings built as "X — Y", one identical bordered card for every kind of content, and a neutral grey ramp taken from a CSS framework's defaults.

**Why this priority**: This is the other half of the stated problem, and it is foundational to the rest — the palette, the type and the starred-question device are the vocabulary the denser result list and the new charts are drawn in. It is P1 alongside User Stories 1 and 3 because the feature exists to fix exactly these things.

**Independent Test**: Load the page, confirm the four named tells are gone, confirm every colour resolves to the recorded palette, confirm the two self-hosted families are serving from this host, and confirm every computed contrast ratio is recorded and clears its floor. Needs no new view.

**Acceptance Scenarios**:

1. **Given** the restyled page, **When** its stylesheet is inspected, **Then** no uppercase letter-spaced label rule, no eyebrow element, no em-dash heading construction and no single uniform card class applied to every kind of content remain.
2. **Given** the restyled page, **When** any colour is resolved, **Then** it is one of the recorded palette tokens, and `--house` is used only on rules and marks and never as a background field.
3. **Given** a starred question anywhere on the page, **When** it renders, **Then** it carries the asterisk Parliament itself prints, **and** the word "starred" is still present for assistive technology; an unstarred question carries no mark.
4. **Given** any figure on the page, **When** it renders, **Then** its denominator is shown beside it as a consistent typographic pairing, not relegated to a footnote.
5. **Given** a visitor whose browser has not yet loaded the web fonts, **When** the page paints, **Then** text is readable immediately in the current system stacks and reflows once to the web fonts.

---

### User Story 3 - A reader moves between views instead of scrolling past them (Priority: P1)

A visitor reaches the view they want by choosing it, not by scrolling through the four they did not. The page has five sections today, stacked in one continuous scroll, and this feature adds three more; left as a single scroll it would get longer precisely as the complaint is that it is already too long to read.

**Why this priority**: This is the structural half of the readability problem, and it is the container the three new views live in. Built first, each new view lands in a place that already exists. It is also what makes the first-load budget hold: a view that is not rendered has no reason to have fetched its data or its code.

**Independent Test**: Load the page, confirm exactly one view renders, switch to each view in turn and confirm the others are not rendered, open a view's hash URL directly in a fresh tab and confirm that view loads, and confirm the browser's back button returns to the previous view.

**Acceptance Scenarios**:

1. **Given** the page, **When** it loads, **Then** exactly one view is rendered, and it is the coverage statement — what the record claims to cover is read before anything drawn from it.
2. **Given** a reader on one view, **When** they choose another, **Then** the new view renders, the previous one does not, and the address updates so the view can be linked to.
3. **Given** a view's hash URL opened directly in a fresh tab, **When** the page loads, **Then** that view renders.
4. **Given** a reader who has switched views several times, **When** they press the browser's back button, **Then** they return to the previous view rather than leaving the page.
5. **Given** a reader who has run a search and then looked at another view, **When** they return to the search view, **Then** their query and its results are still there and nothing already fetched is fetched again.
6. **Given** a view a reader has never opened, **When** the network log is read, **Then** neither its data nor its code has been requested.
7. **Given** the view navigation at 390 px, **When** it renders, **Then** it does not cause the page to scroll horizontally, every item meets the 44 px tap target, and the current view is indicated by something other than colour alone.

---

### User Story 4 - Question load across the covered sessions, as a shape (Priority: P2)

A journalist or researcher sees how the question load moves across the twenty-one covered sessions as a chart rather than a column of numbers — both for the House as a whole, and for whatever subject they just searched — and sees how two ministries diverge over the same span as two series rather than two tables side by side.

**Why this priority**: All three sit on data the page already has in memory — `aggregates/ministry-profile.jsonl` for the House total and the ministry comparison, and the search index for the subject trend — so none costs a new byte. Today exactly one view on the page draws a chart: the single-ministry profile. The two-ministry comparison is text and a table only.

**Independent Test**: Pick a span of sessions, read the series off each chart, and confirm every value matches the table rendered beside it and can be reproduced by hand from the published record.

**Acceptance Scenarios**:

1. **Given** the covered window, **When** a reader views question load for the House, **Then** a per-session series across all twenty-one sessions is drawn, its counting basis is stated, and each figure is shown against its denominator.
2. **Given** a search that returned results, **When** a reader views that subject's trend, **Then** a per-session series for the matched questions is drawn with its starred and unstarred split, against the matched total and the window total as denominators, and **nothing further is fetched to draw it**.
3. **Given** two ministries and the same span of sessions, **When** a reader compares them, **Then** both are drawn on one chart with the same counting basis and the same scale, and the basis is stated once for both.
4. **Given** any chart on the page, **When** a reader reaches it by keyboard or screen reader, **Then** the same figures are available in a table, which is the authoritative form.
5. **Given** any chart, **When** all colour is removed from it, **Then** every series is still identifiable from text.

---

### User Story 5 - How the House composition changed between the two terms (Priority: P2)

A researcher sees how the composition of the House differs between the 17th and the 18th Lok Sabha — by party, by state and by number of terms served, which are the three dimensions the published aggregate carries and the three that FR-008 permits.

**Why this priority**: Feature 001 delivered this as a precomputed file and explicitly deferred the page ("the page may add it later; nothing here requires it to"). `aggregates/composition.jsonl` is 25,237 bytes raw and 1,835 bytes on the wire, so the view is nearly free — but it is fetched by nothing today, so this is the only story here that adds a request.

**Independent Test**: Request a composition breakdown for one term and confirm the categories sum to that term's total membership, with any missing attribute counted in an explicit "not stated" category rather than dropped.

**Acceptance Scenarios**:

1. **Given** a term and a dimension, **When** a reader views the breakdown, **Then** the categories sum to that term's total membership and the total is shown as the denominator beside every figure.
2. **Given** the two covered terms, **When** a reader compares them on one dimension, **Then** both are drawn on the same basis and the counting unit is stated as `member`.
3. **Given** a member whose party, state or terms-served is absent upstream, **When** the breakdown renders, **Then** that member appears in an explicit "not stated" category and is not omitted.
4. **Given** this view, **When** its data is fetched, **Then** nothing is requested until a reader first opens it.

---

### User Story 6 - What a state's members actually ask about (Priority: P3)

Someone who has picked their state sees what its members ask about as a shape they can read, rather than as a twenty-five-row table.

**Why this priority**: `aggregates/state-subjects.jsonl` is already fetched on first use of the state and constituency view, so this costs no new bytes. P3 because it refines a view that already works and answers a question the table already answers.

**Independent Test**: Pick a state, read the subjects off the chart, and confirm each count and each denominator matches the published rows for that state.

**Acceptance Scenarios**:

1. **Given** a state, **When** a reader views its subjects, **Then** the twenty-five published subject lines are drawn with their counts, each against the state's own question total as the denominator.
2. **Given** a state whose subject rows are drawn, **When** the counting basis is read, **Then** it states the `state-question` unit, which is not the same unit as the question counts elsewhere on the page.
3. **Given** this view, **When** a reader has not opened the state and constituency view, **Then** nothing for it has been fetched.

---

### User Story 7 - Every control can actually be reached and operated (Priority: P2)

A visitor using a touch screen, a keyboard, or a reduced-motion setting can reach and operate every control on the page. Four links on the live site are under the 44 px tap-target height today: the skip link at 25 px, and three footer links at 38 px, 17 px and 17 px.

**Why this priority**: These are measured defects on the live site, not preferences, and the restyle touches every one of the rules involved. Fixing them during the restyle is cheap; fixing them afterwards means touching the same rules twice.

**Independent Test**: Drive the page at 390, 768, 1024 and 1440 px; measure every interactive element's rendered box; tab through every view; and confirm no element is under 44 px, every focused element shows a visible ring, and no page scrolls horizontally.

**Acceptance Scenarios**:

1. **Given** the page at any of the four measured widths, **When** every interactive element's box is measured, **Then** none is under 44 px in either dimension — the skip link, the three footer links and the new view navigation included.
2. **Given** a keyboard user, **When** they tab through a view, **Then** every interactive element shows a visible focus ring against whichever ground it sits on.
3. **Given** a visitor with `prefers-reduced-motion: reduce`, **When** the page renders and views are switched, **Then** no transition and no animation runs.
4. **Given** the page at 390 px, **When** any view renders, **Then** the page itself never scrolls horizontally, and any content that cannot shrink scrolls inside its own container.

---

### User Story 8 - The maintainer is told when the record's quality slips (Priority: P3)

The maintainer is signalled when a join a consumer already took becomes uncertain, and when resolution quality drops against the last publication. Two of feature 001's four FR-011 signals — `resolved_transitions_out` and `resolution_rate_below_target` — are defined with docstrings and tests but called by nothing in `src/` or `tools/`. Visitors still get the quiet degradation FR-010 requires; the maintainer half of the promise is not kept. Separately, the automated field-scope check cannot see `representations.member_name`, a legitimate FR-008 name form, so it classifies a genuine member field as "not a member attribute".

**Why this priority**: This is not page work and nothing a visitor sees depends on it. It is in this feature because these are the three recorded open defects against the published record and the gate evidence already names the remedy for each. P3 because the reader-facing stories deliver value without it.

**Independent Test**: For each of the four FR-011 signals, confirm a production caller exists outside the signal definition module and outside the test suite. Run the field-scope diff and confirm `representations.member_name` is classified as an FR-008 name form mechanically rather than by a human reading the contract.

**Acceptance Scenarios**:

1. **Given** a refresh in which a question's `resolution_status` was `resolved` in the previous publication and is not now, **When** the refresh completes, **Then** `resolved_transitions_out` is raised to the maintainer with the affected question ids and the visitor-facing record still serves.
2. **Given** a refresh whose automatic resolution rate is 94.78% — below the 95% target but unchanged from the last publication — **When** the refresh completes, **Then** no rate signal fires, because the trigger is a drop against the previous publication and not an absolute threshold.
3. **Given** a refresh whose rate has fallen against the rate recorded on the previously published `manifest.json`, **When** the refresh completes, **Then** `resolution_rate_below_target` is raised, naming both rates.
4. **Given** the field-scope check, **When** it runs against `reference/constituencies.jsonl`, **Then** `representations.member_name` is reported as an FR-008 name form and not as an unclassified field.

---

### Edge Cases

- A search returns one result, or none — the denser list must not look broken at either extreme, and a zero-result message must keep the named reason it gives today.
- A question has exactly one asking member, where the inline treatment has no separator to show.
- A subject line is long enough to wrap to three or four lines at 390 px, where a single-line result row cannot hold it.
- A web font fails to load, or is blocked — the page must stay readable in the fallback stack and nothing may depend on a glyph only the web font has.
- A reader has set a large browser font size, which the chart's HTML labels scale with and its SVG text does not.
- A chart has one column, or twenty-one, or a session with zero questions in it (session 18/8 has zero sitting days).
- A composition dimension has one category holding almost all members (282 of 544 members served exactly one term), which flattens every other bar.
- A state's twenty-five subject lines include several with the same count, so the ordering is not determined by count alone.
- A hash names a view that does not exist, or names the subject-trend view before any search has been run — the page must land somewhere coherent rather than on an empty view or an error.
- A reader switches away from a search mid-fetch and returns before it completes.
- JavaScript fails or is disabled. Every view's content is already runtime-filled today, so this is not a regression, but with switchable views there is no longer a scroll that reveals the other sections' headings.
- A term or session date is needed by a view — it must not be, because every one reads "not stated".
- The previous publication is unavailable when the refresh tries to compare rates — the comparison must degrade to "no comparison made" rather than to a false signal or a silent pass.
- `--house` and `--mark` are 1.03:1 against each other, so a reader who cannot separate red from green has no luminance cue between them.
- `--paper` and `--sheet` are 1.13:1, so a surface cannot be told from the page ground by its fill alone.

## Requirements *(mandatory)*

### Functional Requirements

#### Density and readability (User Story 1)

- **FR-101**: The page MUST present a search result in a form that does not use a five-pair label-and-value block. The subject, the date, the ministry, the link status and the asking members MUST all remain present and reachable.
- **FR-102**: The page MUST present multiple asking members for one question inline rather than one per line, and MUST state the number of askers against its total as a figure-and-denominator pairing.
- **FR-103**: Where the page shows fewer than all of a set, it MUST state how many are not shown and MUST keep the full set reachable. Silent truncation is a breach.
- **FR-104**: A flag on a result — a partial link, an unrecognised ministry id, a missing field — MUST continue to be carried by a word, never by colour, position or density alone.

#### The designed surface (User Story 2)

- **FR-105**: The page MUST use exactly this palette, replacing the current framework-default grey ramp: `--paper #EEEFEA` page ground, `--sheet #FDFDFB` surfaces, `--ink #15253A` body text, `--ink-soft #4A5663` notes and meta, `--house #1F5D3E` institutional marker, `--mark #8C3325` links and focus ring.
- **FR-106**: `--house` MUST be used only as an institutional marker on rules and marks. It MUST NOT be used as a background field anywhere.
- **FR-107**: Every contrast ratio in the palette MUST be recomputed with the WCAG relative-luminance formula and recorded in the stylesheet beside the token it describes. Text MUST clear 4.5:1 and marks that carry meaning MUST clear 3:1.
- **FR-108**: Because `--paper` and `--sheet` are 1.13:1 against each other, any surface distinction a reader needs MUST be carried by something other than the difference between those two fills.
- **FR-109**: Because `--house` and `--mark` are 1.03:1 against each other, those two colours MUST NOT be the only difference between two meanings anywhere on the page.
- **FR-110**: The page MUST self-host Newsreader for headings and IBM Plex Sans for body and data, Latin subset only, served same-origin from `web/fonts/`, with `font-display: swap` and the current system stacks retained as fallbacks.
- **FR-111**: No font file MUST contain a Devanagari codepoint. The Latin-only subset is a Principle IV requirement, not a preference: the Language gate scans codepoints and no Devanagari may enter the repository.
- **FR-112**: The stylesheet's recorded invariant that it contains no `url()` and no web font MUST be replaced with a narrower invariant that the fonts satisfy: every `url()` in the stylesheet resolves to a path on this same host, and no reference of any kind to another host appears anywhere in `web/`. The automated check that asserts the old invariant MUST be changed to assert the new one, not removed.
- **FR-113**: A starred question MUST carry the asterisk Parliament itself prints, with the word "starred" still present for assistive technology. An unstarred question MUST carry no mark.
- **FR-114**: Every figure the page shows MUST be shown next to its denominator as a consistent typographic pairing, not as a footnote.
- **FR-115**: The page MUST NOT contain an uppercase letter-spaced label rule, an eyebrow line above a heading, a heading constructed as "X — Y", or a single uniform card treatment applied to every kind of content.

#### Switchable views (User Story 3)

- **FR-146**: The page MUST present its sections as switchable in-page views, with exactly one view rendered at a time.
- **FR-147**: View switching MUST use hash links, so that a view can be linked to directly and the browser's back and forward buttons move between views rather than off the page.
- **FR-148**: View switching MUST introduce no framework, no router library and no build step. It remains hand-written HTML, CSS and ES modules.
- **FR-149**: The current view MUST be indicated by something other than colour alone.
- **FR-150**: The view navigation MUST be reachable and operable by keyboard, MUST meet the 44 px tap target of FR-130, and MUST NOT cause the page to scroll horizontally at 390 px.
- **FR-151**: A view a reader has not opened MUST have fetched nothing — neither its data nor its code.
- **FR-152**: Work a reader has done in a view — a query and its results, a chosen state, a chosen ministry — MUST survive switching away and back, and what has already been fetched MUST NOT be fetched again.
- **FR-153**: The coverage statement MUST be the view a visitor lands on, so that what the record claims to cover is read before anything drawn from it. A hash naming no known view MUST land there too, rather than on an empty view or an error.

#### The new views (User Stories 4, 5, 6)

- **FR-116**: The page MUST draw question load for the House as a per-session series across all twenty-one covered sessions.
- **FR-145**: The page MUST draw the trend of a searched subject across the covered sessions, with its starred and unstarred split, derived from the search index already in memory — fetching nothing further to do it.
- **FR-117**: The page MUST draw a two-ministry comparison as series on one chart, on the same scale and the same counting basis.
- **FR-118**: The page MUST draw House composition for the 17th and 18th Lok Sabha across the three published dimensions — party, state and number of terms served — with a member whose attribute is absent counted in an explicit "not stated" category.
- **FR-119**: The page MUST draw a state's most-asked subject lines with their counts against the state's own question total.
- **FR-120**: Every chart MUST state its counting basis and MUST show every figure against its denominator. A chart that drops the denominator is a breach of the standard the rest of the record holds to.
- **FR-121**: Every chart MUST be accompanied by a table carrying the same figures, and the table MUST be the form a keyboard and a screen reader reach. No chart may be the only form of its data.
- **FR-122**: No chart MUST carry meaning by colour alone. Every series MUST be identifiable from text with all colour removed, and any two adjacent meaning-carrying marks MUST either clear 3:1 against each other or be separated by a stroke in the surface colour, with the separation recorded.
- **FR-123**: All charts MUST remain hand-built SVG. No charting library, no framework, no build step.
- **FR-124**: No view MUST require a term start or end date, or a session start or end date. Every one of those reads "not stated" in the published record: terms and sessions can be ordered and counted but not placed on a calendar.
- **FR-125**: No visualisation MUST introduce a member attribute outside the FR-008 set — name forms, party, state, constituency, House, term, and sitting status.

#### First load and the byte budget

- **FR-126**: Nothing search-related and nothing state-related MUST be fetched on page load. The page MUST continue to assert this at boot before it renders anything, and every new view MUST keep that discipline.
- **FR-127**: The composition aggregate MUST NOT be fetched on page load. It MUST be read on a reader's first use of the view that needs it.
- **FR-128**: The code for a view other than the landing view MUST NOT be loaded on page load. Module code is 53,000 of the measured 88,961 bytes of the current first load, so three views added statically would grow the first load twice over — once for the fonts and again for the code.
- **FR-129**: The first load MUST stay inside the budget recorded in SC-001, and that figure MUST be measured on the live deployment after building and recorded beside the 2026-10-10 measurements.

#### Operability (User Story 7)

- **FR-130**: Every interactive element MUST present a tap target of at least 44 px in both dimensions at every measured width — including the skip link and the three footer links measured at 25 px, 38 px, 17 px and 17 px on the live site.
- **FR-131**: Every interactive element MUST show a visible focus ring when focused by keyboard, against whichever ground it sits on.
- **FR-132**: The page MUST respect `prefers-reduced-motion: reduce` by running no transition and no animation, view switching included.
- **FR-133**: The page MUST NOT scroll horizontally at any measured width. Content that cannot shrink MUST scroll inside its own container.

#### Maintainer signals and checks (User Story 8)

- **FR-134**: The refresh MUST raise `resolved_transitions_out` when a question's `resolution_status` was `resolved` in the previous publication and is not in the current one, naming the affected question ids and no personal attribute.
- **FR-135**: The refresh MUST raise `resolution_rate_below_target` on a **drop against the previous publication's recorded rate**, not on an absolute threshold. The automatic rate is 94.78% against a 95% target, so an absolute trigger would fire on every run and signal nothing.
- **FR-136**: Where no previous publication is available to compare against, the refresh MUST record that no comparison was made. It MUST NOT report a pass and MUST NOT raise a false signal.
- **FR-137**: All four FR-011 maintainer signals MUST have a production caller outside the signal definition module and outside the test suite.
- **FR-138**: The automated field-scope check MUST classify `representations.member_name` as an FR-008 name form mechanically, so that its membership of the set does not rest on a human reading the contract.
- **FR-139**: A signal raised to the maintainer MUST NOT change what a visitor sees. Quiet degradation for visitors, per FR-010, is unchanged.

#### What does not change

- **FR-140**: Nothing in `data/published/` MUST change — not a file, not a field, not a figure, not a counting basis, and not what any existing figure claims.
- **FR-141**: The page MUST make no request to any host other than the one serving it. No CDN, no font host, no analytics, no telemetry, no beacon, no third party of any kind.
- **FR-142**: The page MUST remain hand-written HTML, CSS and ES modules with no framework and no build step.
- **FR-143**: The feature MUST introduce no running cost and no new infrastructure.
- **FR-144**: All published and presented material MUST remain English. No Rajya Sabha, no Hindi, no other language, and no translation or transliteration path.

### Key Entities

- **Palette token**: one named colour with its recorded role, and its computed ratio against each ground it is used on.
- **Type family**: one self-hosted family with its subset, its weights, its fallback stack and its byte cost on the wire.
- **View**: one switchable region of the page, with its hash, its data, its code, whether it has been opened, and the state a reader has built up in it.
- **Result row**: one question as presented in a list — its subject, date, ministry, link status, askers, and any flag, in the denser form FR-101 requires.
- **Figure-and-denominator pairing**: a count shown against the total it was drawn from, as one typographic unit.
- **Chart**: a hand-built SVG series with its counting basis, its denominator, its accompanying table, and its series named in text.
- **Counting basis**: the published statement of what a unit counts, already carried per unit in `aggregates/counting-basis.jsonl` as `question`, `member` and `state-question`.
- **Maintainer signal**: one of the four FR-011 signals, its trigger, its severity, and its production caller.
- **Previous publication**: the last published `manifest.json` and `by-session` set, which is what the two newly wired signals compare against.

## Success Criteria *(mandatory)*

### Measured baseline, 2026-10-10, live GitHub Pages deployment

These supersede feature 001's earlier estimates. Every criterion below is stated against them. The repository's own `README.md` and `spike/size-budget.md` still record that Pages had not been observed serving the site; these measurements supersede that note, and this spec is where the newer figures live.

| Measurement | On the wire | Raw | Requests |
|---|---|---|---|
| First load | 88,961 B | 515,367 B | 18 |
| First load + a search touching two session digests | 1,254,715 B | 5,682,482 B | — |
| `search/subject-index.json` | 794,402 B | 2,491,188 B | — |
| session digest (larger of the two) | 218,550 B | 1,573,939 B | — |
| session digest (smaller) | 140,723 B | 1,016,286 B | — |
| `app.js` | 21,693 B | 80,105 B | — |

**What the first load is made of**, measured offline at `gzip -6` and summing to 87,781 B against the 88,961 B observed on the wire — the difference being response headers, which confirms the figures are like-for-like:

| Component | Raw | `gzip -6` | Share of first load |
|---|---|---|---|
| `lib/*.js` (9 modules) | 85,675 B | 31,614 B | 36% |
| `app.js` | 80,105 B | 21,372 B | 24% |
| `aggregates/ministry-profile.jsonl` | 284,685 B | 17,552 B | 20% |
| `style.css` | 35,954 B | 8,539 B | 10% |
| everything else (6 files) | 28,971 B | 8,704 B | 10% |

**Note for the budget**: `woff2` is already compressed, so font bytes do not shrink on the wire the way these text files do. Module code is 60% of the current first load, which is why FR-128 exists.

### What FR-151 pays for: the fonts do not double the first load

The brief estimated that 80–100 KB of fonts "would approximately double the 88,961-byte first load". That was true of a single-scroll page. It is **not** true once FR-151 takes unopened views' data and code off the landing view, and the difference was measured rather than assumed.

The landing view is the coverage statement. `boot()` already fetches only what it needs — `coverage.jsonl`, `sessions.jsonl`, `counting-basis.jsonl` and `manifest.json`, 4,540 B at `gzip -6`. Everything else on the current first load belongs to a view a reader has not opened:

| Deferrable off the landing view | `gzip -6` |
|---|---|
| `aggregates/ministry-profile.jsonl` (ministry views) | 17,552 B |
| `reference/ministries.jsonl` (ministry and search views) | 1,856 B |
| `lib/search.js` | 6,469 B |
| `lib/constituency.js` | 4,395 B |
| `lib/profile.js` | 3,976 B |
| `lib/tokenise.js` | 2,325 B |
| `lib/chart.js` | 2,246 B |
| **Total** | **38,819 B** |

That is 44% of the current first load, and it is deferrable **without splitting `app.js` at all**. So the non-font first load should *fall* to about 52,000 B, and the fonts land on top of that rather than on top of 88,961 B. The criteria below are set against the measured figures, not the brief's estimate.

### Measurable Outcomes

- **SC-001**: First load is no more than **160,000 B on the wire**, measured on the live deployment and recorded beside the 2026-10-10 figures above. Derived: ~52,000 B (non-font, after FR-151) + 95,000 B (fonts) + ~2,000 B (stylesheet growth) ≈ 149,000 B, with the ceiling set above it. This is **1.80× the measured 88,961 B baseline, not the 2× the brief estimated**.
- **SC-002**: The total font payload is no more than **95,000 B on the wire**, across no more than 4 font files.
- **SC-003**: First load **excluding the fonts** is no more than **60,000 B on the wire** — *down* from the measured 88,961 B, not merely held. The 38,819 B table above is what makes this reachable; this is the criterion that makes FR-128 and FR-151 checkable, and a non-font first load that merely holds at 88,961 B is a failure of this criterion even if SC-001 passes.
- **SC-004**: First load is no more than **16 requests** — *down* from 18: seven deferred by FR-151, with at most four font files added.
- **SC-005**: Every palette pair's contrast ratio is computed and recorded. All eight text pairs clear 4.5:1; the computed figures are `--ink` 13.38:1 on `--paper` and 15.19:1 on `--sheet`, `--ink-soft` 6.48:1 and 7.36:1, `--house` 6.75:1 and 7.66:1, `--mark` 6.95:1 and 7.88:1. Any mark carrying meaning clears 3:1, and any pair that does not is recorded with what carries the meaning instead.
- **SC-006**: A query returning 25 results renders a result list no taller than **2,800 px at 390 px wide**, against about 6,000 px today.
- **SC-007**: No view scrolls horizontally at 390, 768, 1024 or 1440 px.
- **SC-008**: No interactive element measures under **44 px** in either dimension at any of the four widths. The four known failures — 25 px, 38 px, 17 px, 17 px — are at or above 44 px.
- **SC-009**: Every interactive element shows a visible focus ring when focused by keyboard, confirmed by tabbing every view.
- **SC-010**: With `prefers-reduced-motion: reduce` set, no transition and no animation runs, view switching included.
- **SC-011**: A screenshot is captured at 390, 768, 1024 and 1440 px for every view.
- **SC-012**: The network log of a full page run shows requests to the serving host only. One request to any other host is a failure.
- **SC-013**: The repository contains **zero Devanagari codepoints**, font files included, re-measured by the Language gate's codepoint scan.
- **SC-014**: Every figure and every chart on the page states its counting basis and shows its denominator, verifiable by reading the rendered page against `aggregates/counting-basis.jsonl`.
- **SC-015**: Every chart has a table beside it carrying the same figures, and every series is identifiable with all colour removed.
- **SC-016**: On page load, only the landing view's data has been requested. Nothing search-related, state-related, composition-related, or belonging to any unopened view — data or code — has been fetched, asserted at boot before anything renders.
- **SC-017**: Opening any view's hash URL directly in a fresh tab renders that view; a hash naming no known view renders the coverage view.
- **SC-018**: Switching away from a view and back refetches nothing, confirmed from the network log, and the reader's query, state or ministry selection is still there.
- **SC-019**: The subject-trend series is drawn with **zero additional requests** after the search that produced it, confirmed from the network log.
- **SC-020**: All four FR-011 signals have a production caller outside the definition module and outside the test suite.
- **SC-021**: A refresh whose automatic rate is unchanged at 94.78% raises no rate signal; a refresh whose rate has dropped against the previously published figure raises one.
- **SC-022**: The field-scope check classifies `representations.member_name` as an FR-008 name form without a human reading the contract.
- **SC-023**: No member attribute outside the FR-008 set is reachable from the page, re-verified against what the page actually fetches.
- **SC-024**: `data/published/` is byte-identical before and after, excluding a scheduled refresh's own output.
- **SC-025**: Running cost stays at zero per month and no new infrastructure is introduced.

## Recorded Owner Decisions

Carried in as decisions already taken, not as open questions.

1. **The palette**, exactly as given in FR-105. The green is the Lok Sabha chamber colour, which also reserves red for the Rajya Sabha if a second House is ever covered. `--mark #8C3325` is unchanged from the current stylesheet.
2. **The typography**: self-host Newsreader for headings and IBM Plex Sans for body and data, Latin subset only, same-origin from `web/fonts/`, `font-display: swap`, current system stacks as fallbacks. Latin-only is a Principle IV consequence, not a preference.
3. **The signature device**: starred questions take the asterisk Parliament itself prints, with the word retained for assistive technology; unstarred take no mark. Every figure sits next to its denominator as a typographic pairing.
4. **Four things go**: the uppercase labels, the eyebrow, the em-dash heading construction, and the uniform card.
5. **The rate signal triggers on a drop against the previous publication**, not on an absolute threshold.
6. **Clarified 2026-10-10 — the page becomes switchable in-page views.** One HTML page still, sections switched by hash links, exactly one view rendered at a time. Chosen over a single scroll with the new views appended, and over a single scroll with the analytical views collapsed. Encoded as FR-146 to FR-153.
7. **Clarified 2026-10-10 — "question load over twenty-one sessions" means both series.** The whole-House per-session total from `aggregates/ministry-profile.jsonl`, *and* the matched-subject trend from the search index. Both cost zero additional bytes and they answer different questions: the first is how busy the House was, the second is the visual answer to "has this been asked before", which was feature 001's User Story 2. Encoded as FR-116 and FR-145.

## Assumptions

- **The result-list ceiling of 2,800 px is a derived default, not an owner figure.** It comes from 25 results at about 90 px each at 390 px wide, plus about 400 px of summary and ordering notes. It exists so FR-101 is testable and should be revisited once the denser row is built and measured.
- **The font budget of 95,000 B across at most 4 files assumes roman faces only** — two variable Latin-subset romans, one per family. Italics would roughly double the payload and are assumed out. If the plan finds a third or fourth face is needed, SC-002 is the constraint it must fit inside, not a figure to raise.
- **The House series and the two-ministry comparison are derived from `aggregates/ministry-profile.jsonl`**, so neither needs a file the record does not already publish. Under FR-151 that file is no longer on the first load: the ministry views read it on first use, and the three views that share it — single ministry, comparison, House series — read it once between them.
- **`aggregates/subject-trends.jsonl` is never fetched.** At 13,178,975 B raw it would blow any budget by an order of magnitude. The matched-subject trend of FR-145 is derived instead from the search index already in memory: `prefixes[doc_prefix[position]]` yields the session and the starred/unstarred split for every matched document. This was confirmed against the published index — the term "under" resolves to 6,254 documents spread across all 21 sessions and 41 session/type buckets, at zero additional bytes.
- **The previous publication is reachable for comparison.** `manifest.json` already publishes `resolution_rate_automatic` and `resolution_rate_including_assertions`, and the `by-session` set publishes `resolution_status` per question, so both newly wired signals have something to diff against. Where that publication is absent, FR-136 governs.
- **The existing measurement tooling is the route to most criteria.** `make test-page` drives a real browser and writes a network log; `tools/measure_first_load.py` reports per-phase bytes; `tools/drive_page.mjs` emulates device metrics and captures screenshots. The screenshot widths change from 390 and 1280 to 390, 768, 1024 and 1440, and the wire figures still come from the live deployment because the local host compresses nothing.
- **Charts that use two series need a second mark colour the recorded palette does not name.** The current stylesheet uses `--accent` and `--bar-unstarred #6F88BD`, recording honestly that the two are only 2.27:1 against each other and are never adjacent because every segment is stroked in the surface colour. Whatever the new second series mark is, FR-122 requires it to be named, measured and recorded on the same terms.
- **The three maintainer-side defects are in scope because they are recorded open defects against feature 001**, each with a remedy already named in `gate-evidence.md`. They are not page work and nothing a visitor sees depends on them.
- **Switchable views are assumed not to need a server.** Hash routing is chosen over path routing precisely because GitHub Pages serves static files and a path-routed view would 404 on a direct load. This keeps Principle I intact with no redirect configuration.

## Out of Scope

- The Rajya Sabha.
- Hindi, or any language other than English.
- Analytics, telemetry, or any third party.
- Any change to what an existing figure claims, or to any counting basis.
- Any change to `data/published/`.
- Any new source, any new ingest.
- A charting library, a framework, a router library, or a build step.
- Any view needing a date inside a term, because no term or session carries one.
