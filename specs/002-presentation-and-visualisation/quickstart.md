# Quickstart: Validating Presentation and Visualisation

**Feature**: `002-presentation-and-visualisation` | **Date**: 2026-10-10

One runnable scenario per success criterion that can be checked by running something. Four criteria cannot be — they are listed at the end rather than quietly counted as passing.

## Prerequisites

```bash
make setup                       # the .venv, including the new fonttools[woff] dev extra
test -f data/published/manifest.json || make refresh
command -v node                  # drive_page.mjs needs Node
```

A built `data/published/` is required. Run against an absent one, the page checks report NOT PRESENT and a naive reading of the suite looks green — which is the one wrong signal these checks must never send. `make validate` refuses up front for that reason.

## The gate

```bash
make validate
```

Runs every scenario below plus the full test suite. It runs **all** checks even after one fails and prints each failure's captured output at the end, because stopping at the first hides the rest until the next run.

---

## Scenario 1 — The palette (SC-005, FR-105 to FR-109)

```bash
make check-contrast
```

Recomputes every pair from the stylesheet's own token values, so the recorded figures cannot drift from what is served.

**Expected**: eight text pairs at or above 4.5:1 — `--ink` 13.38:1 / 15.19:1, `--ink-soft` 6.48 / 7.36, `--house` 6.75 / 7.66, `--mark` 6.95 / 7.88; `--series-2` at 3.75 / 4.25 above the 3:1 mark floor. The three sub-floor pairs — `--paper`/`--sheet` 1.13:1, `--house`/`--mark` 1.03:1, `--series-2`/`--house` 1.80:1 — are reported **with what carries the meaning instead**, and are a pass only because each is recorded. An unrecorded sub-floor pair fails.

## Scenario 2 — The fonts (SC-002, SC-013, FR-110 to FR-112)

```bash
make check-fonts
```

**Expected**: three files totalling **60,684 B**, under SC-002's 95,000 B across at most 4 files. Per file: no `cmap` codepoint in U+0900–U+097F; the declared family and weight; an OFL licence beside it. The existing `make guard` and `make audit-fields` **skip** `.woff2` — it is in `UNSCANNABLE_SUFFIXES` — so this is the only check that sees inside a font.

```bash
.venv/bin/python -m pytest tests/unit/test_page_fetch_layer.py -k "stylesheet or host or import"
```

**Expected**: every `url()` in the stylesheet is a relative path to a file that exists inside `web/`; no `@import`; no off-host reference anywhere in `web/`; and **every dynamic `import()` uses a relative specifier** — the last of these is a new assertion, because the current pattern requires whitespace after `import` and never matches the call form.

## Scenario 3 — Views, routing and fetch timing (SC-016 to SC-018, FR-146 to FR-153)

```bash
make test-page
```

**Expected, from the network log**:

- The first load is exactly the **15** requests in [contracts/view-routes.md](./contracts/view-routes.md) — fifteen, not the fourteen first planned: `lib/shared.js` is the extra, a module that did not exist until the shared helpers had to leave `app.js` to break a dependency cycle. **Any other file is a failure** — including `ministry-profile.jsonl`, `ministries.jsonl` and the five view-only `lib/` modules, all of which were on the first load before this feature.
- `boot()` throws if any search, seat, ministry, composition or `views/` asset was requested before first render.
- Opening `#search`, `#seat`, `#ministry`, `#compare`, `#load`, `#composition` each renders that view; `#nonsense` and an empty hash render `coverage`. **Seven views, not eight**: the licence and the source-terms disclosure stay in the footer, outside `<main>`, so they show on every view rather than behind a choice.
- Back and forward move between views, never off the page.
- Switching away from a view with results and returning **refetches nothing** and the results are still there.
- The subject trend draws with **zero** requests after the search that produced it.
- Every request goes to the serving host. One request elsewhere is a failure.

## Scenario 4 — Result-list density (SC-006, FR-101 to FR-104)

```bash
make test-page            # the list-height sweep runs inside it
```

**MEASURED 2026-10-13: 2,672 px at 390 px**, from **9,720 px** before — a 3.64× reduction, under the ceiling at every width (2,162 at 768; 2,080 at 1024 and 1440). The spec's "about six thousand pixels" turned out to be the figure at 768 px and wider; nobody had measured the narrow case the page was designed for. The subject, date, ministry, link status and askers are all still present. Askers are inline, not one per line; a question asked by twenty members states the count against its total; anything abbreviated states how many are not shown.

The ceiling was **derived, not measured** — 25 rows at about 90 px plus about 400 px of summary — and it was met at 106.9 px per row. Two responsive decisions got it the last 321 px, both forced by measurement: below 768 px the asker's party is hidden, and so are the asker names, leaving the count — which is the shape the owner's own preview shows.

## Scenario 5 — Operability (SC-007 to SC-010, SC-011, FR-130 to FR-133)

```bash
make test-page SCREENS=1
```

**Expected**, at each of 390, 768, 1024 and 1440 px:

- No interactive element under **44 px** in either dimension. **Measured: 0 under the floor at all four widths.** The four known failures — the skip link at 25 px and three footer links at 38, 17 and 17 px — are fixed. The skip link's `min-height` was already there and inert: `min-height` does not apply to a non-replaced inline `<a>`, so it needed a `display` change, not a larger number.
- `documentElement.scrollWidth <= clientWidth` — no horizontal scroll, the new view navigation included.
- Every interactive element shows a visible focus ring when tabbed. **Measured: 14 stops tabbed against 14 focusable in the DOM, all ringed** — the sweep asserts it reached every one, because its first version passed while covering a third of the page.
- A screenshot per view per width, in `page-screens/`.

With `prefers-reduced-motion: reduce`, no transition and no animation runs. **`Emulation.setEmulatedMedia` IS reachable** — this is a genuine browser check, not the fallback stylesheet assertion the spec allowed for.

## Scenario 6 — The charts (SC-014, SC-015, SC-019, FR-116 to FR-125)

```bash
make test-page
```

**Expected**, for each of the five charts in [contracts/chart-contract.md](./contracts/chart-contract.md):

- Its counting basis is rendered from `aggregates/counting-basis.jsonl` — the `question`, `member` or `state-question` statement, as published, not paraphrased.
- Every figure sits against its denominator: 95,268 for the window, `total_members` per term, `state_questions` per state, each ministry's own total.
- A table beside it carries the same figures and is what the keyboard reaches.
- With colour removed, every series is still identifiable from text.
- No chart requests a term or session date. Every one reads "not stated" — 9,986 term records and all 21 sessions.

Reproduce one by hand to confirm the chart agrees with the CLI that already prints the same aggregate:

```bash
make composition LS_TERM=18
```

**Expected** (executed 2026-10-10, abridged):

```
=== House composition, 18th Lok Sabha ===
total membership published for this term: 544

--- party (42 categories) ---
     240  Bharatiya Janata Party
     100  Indian National Congress
      ...
      51  ... and 30 further categories
  RECONCILE: 240 + 100 + 37 + ... (30 more) = 544
             = 544  against published total 544  -> OK
```

The composition chart must agree with this, category for category and total for total, and must show 282 of 544 for a single term served. Note what the CLI already does and the chart must match: it shows twelve categories, states the remainder as **"and 30 further categories"** with their 51 members counted, and reconciles to 544. That is FR-103's rule — state what is not shown — already in practice, and it is also how the party dimension survives 42 categories at 390 px.

## Scenario 7 — Member field scope (SC-022, SC-023, FR-125, FR-138)

```bash
make audit-fields
```

**Expected**: all three scopes present and clean, and **`representations.member_name` reported as an FR-008 name form** rather than as an unclassified field. It is a genuine name form whose spelling is absent from `PUBLISHED_FIELDS`, so the diff currently classifies a correct field as "not a member attribute" and its membership rests on a human reading the contract. Renaming the published key is not available — FR-140 forbids changing `data/published/` — so the check resolves a declared synonym instead.

No member attribute outside the FR-008 set is reachable from the page, re-verified against what the page actually fetches, which FR-151 **narrows** rather than widens.

## Scenario 8 — Maintainer signals (SC-020, SC-021, FR-134 to FR-139)

```bash
.venv/bin/python -m pytest tests/unit/test_state_transitions.py tests/unit/test_signals.py
```

**Expected**: all four FR-011 signals have a production caller outside `signals/alerts.py` and outside the test suite. The existing assertion that `resolved_transitions_out` has *no* caller is **inverted**, not deleted.

Against two seeded snapshots:

- A question going `resolved` → `ambiguous` raises `resolved_transitions_out` with that question's id, and **no name and no value** in the payload.
- An automatic rate unchanged at 94.78% raises **nothing** — the trigger is a drop against the previous publication, not the 95% threshold, which would otherwise fire on every run.
- A rate that fell against the previously published figure raises `resolution_rate_below_target`, naming both rates.
- An absent `.previous-snapshot` records **"no comparison made"** — not a pass, not a signal.
- The visitor-facing record is unchanged across a run that raised a signal.

## Scenario 9 — The published record is untouched (SC-024, FR-140)

```bash
git status --porcelain data/published/
```

**Expected**: empty. Not a file, not a field, not a figure, not a counting basis. If a refresh ran during the work, diff against the pre-work commit instead and confirm every change is that refresh's own output.

## Scenario 10 — The first load, on the wire (SC-001, SC-003, SC-004, FR-129)

This one **cannot be done locally**. `make serve-local` compresses nothing, and `tools/measure_first_load.py` asserts that from the recorded headers rather than assuming it. The wire figures come only from the live deployment's response headers.

```bash
# local: the raw and gzip -6 estimate, for a regression signal only
make test-page

# live, after deploy: the figure SC-001 is actually read off
curl -sI -H 'Accept-Encoding: gzip, br' https://<pages-host>/ | grep -i 'content-length\|content-encoding'
# repeat per first-load file; sum the content-lengths
```

**MEASURED 2026-10-13 on the live deployment** — all four criteria met:

```
  criterion                              ceiling      measured    verdict
  ---------------------------------------------------------------------
  SC-001  first load, wire              160,000       106,916     PASS
  SC-002  fonts, wire                    95,000        60,684     PASS
  SC-003  non-font, wire                 60,000        46,232     PASS
  SC-004  first-load requests                16            15     PASS
```

**1.20× the 88,961 B baseline**, where the ceiling allowed 1.80× and the brief
expected "approximately double". The non-font load is **0.52× — a 48% cut** —
which is what paid for the fonts. The per-file figures are in `spec.md` →
*MEASURED on the live deployment*.

A non-font first load that holds at 88,961 B **fails SC-003 even if SC-001 passes**. That is the criterion's purpose: it is what makes FR-128 and FR-151 checkable rather than aspirational.

---

## What a green run does NOT prove

Stated here because the moment this claim is most likely to be made is immediately after a green run.

| Criterion | Why running something cannot settle it | What would |
|---|---|---|
| **SC-012** (no off-host request) locally | A local run proves the page makes none *in that run*. A reference reachable only on a path not exercised would not appear. | The live network log, plus the static off-host assertions over all of `web/` |
| **SC-025** (zero cost, no new infrastructure) | Observable only in operation, over time | A billing period with no charge |
| ~~**SC-002 as served by this site**~~ | **RESOLVED 2026-10-13.** All three fonts return `content-encoding: none` and byte-for-byte the `gstatic` figure: 23,888 + 17,604 + 19,192 = 60,684 B. `woff2` does not re-compress | — |
| **SC-011**'s screenshots | They are captured, not judged. A screenshot proves a layout rendered, never that it reads well | A person looking at them |

Three further UNVERIFIED items are carried in [research.md](./research.md): whether `prefers-reduced-motion` is reachable through the driver, whether a third test asserts the no-web-font property, and the 2,800 px ceiling itself.
