# Pre-work baseline

**Recorded**: 2026-10-13 · **Task**: T105

So that SC-024 ("`data/published/` is byte-identical before and after") can be
checked at the end against a known starting point rather than against memory.

## Starting commit

```
$ git rev-parse HEAD
27399b3c24220a89737f3519026637fbf408086d
```

## `data/published/` at the start

```
$ git status --porcelain data/published/
(empty — clean)
```

Clean. **Any** change here at the end of the feature is either a scheduled
refresh's own output or a breach of FR-140, and T183 must say which.

## Figures this feature is measured against

Measured on the live GitHub Pages deployment **2026-10-10**, superseding
feature 001's estimates. `data/published/` has had no commit since, so every
figure below is still current as of this baseline — verified, not assumed.

| Measurement | On the wire | Raw | Requests |
|---|---|---|---|
| First load | 88,961 B | 515,367 B | 18 |
| First load + a search touching two session digests | 1,254,715 B | 5,682,482 B | — |

Component breakdown at `gzip -6`, summing to 87,781 B against the 88,961 B
observed (the difference being response headers):

| Component | Raw | `gzip -6` | Share |
|---|---|---|---|
| `lib/*.js` (9 modules) | 85,675 B | 31,614 B | 36% |
| `app.js` | 80,105 B | 21,372 B | 24% |
| `aggregates/ministry-profile.jsonl` | 284,685 B | 17,552 B | 20% |
| `style.css` | 35,954 B | 8,539 B | 10% |
| everything else (6 files) | 28,971 B | 8,704 B | 10% |

## Pre-work page measurements

Measured 2026-10-13 by the T106–T112 harness against the **unmodified** page,
with 25 results on screen. These supersede the spec's estimates, which were not
measured by this harness.

| Measurement | Pre-work | Target | Measured after |
|---|---|---|---|
| Result list, 25 results at 390 px | **9,720 px** (388.8 px each) | ≤ 2,800 px | **2,672 px** (106.9 px each) ✓ |
| Result list, 25 results at 768 px | 6,047 px (241.9 px each) | — | **2,162 px** (86.5 px each) |
| Result list, 25 results at 1024/1440 px | 6,047 px | — | **2,080 px** (83.2 px each) |
| Interactive elements under 44 px | **4**, at every width | 0 | *(T148)* |
| Horizontal scroll, all four widths | **none** | none | *(T151)* |
| `prefers-reduced-motion` honoured | **yes** | yes | *(T150)* |
| First load, wire | 88,961 B | ≤ 160,000 B | *(T185)* |
| First load excluding fonts, wire | 88,961 B | ≤ 60,000 B | *(T185)* |
| First-load requests | 18 | ≤ 16 | *(T185)* |
| Font payload, wire | 0 B | ≤ 95,000 B | 60,684 B (T102) |

### The result list is worse at 390 px than the spec estimated

The spec carries "about six thousand pixels tall" for a 25-result list. Measured,
**6,047 px is the figure at 768 px and wider**; at 390 px it is **9,720 px**, 61%
taller. Each result is **388.8 px** at 390 px against 241.9 px at 768 px, because
every one of the five label-and-value pairs wraps onto its own extra line in a
narrow column.

So SC-006's 2,800 px ceiling is a **3.5× reduction at 390 px**, not the 2.1× the
spec's arithmetic implied. The ceiling is unchanged — it was derived from a target
row height (25 × ~90 px + ~400 px of summary), not from the starting figure — but
US1 is a larger job than the spec's framing suggested, and T145 reports the
measured figure rather than quietly widening the ceiling to meet it.

### Tap targets: the same four elements, different heights

The harness finds **exactly the four elements the spec names**, at all four
widths:

```
a.skip-link "Skip to content"                       109.8 x 24.8
a "https://github.com/rohan-c0de/indian-sansad..."  333.3 x 16
a "DATA-LICENSE.md"                                 120.06 x 16
a "https://github.com/rohan-c0de/indian-sansad..."  289.25 x 16
```

The spec records 25, 38, 17 and 17 px from the live site at 375 px. The identity
and the count match; three of the heights do not. The likely cause is
line-wrapping: at 375 px one footer link wraps to two lines (2 × 19 = 38), and at
390 px and above all three sit on one line at 16 px. Recorded rather than
reconciled — both figures are real measurements of different widths, and the
defect is the same defect either way.

### `prefers-reduced-motion` is reachable, and already honoured

Research R12 carried this as UNVERIFIED. It is now settled: CDP
`Emulation.setEmulatedMedia` **works**, the media query matches inside the
driver, and `web/style.css:676` already resets every transition and animation
under it. **SC-010 is a genuine browser check, not the fallback stylesheet
assertion** — so T150's job is to keep that true through the restyle, not to
build it.

One correction worth recording, because trusting the check would have damaged
working code: the first version of the reduced-motion sweep tested
`transitionDuration > 0` and reported every element on the page as still
animating. The stylesheet is right and the check was wrong — the conventional
reset is `0.01ms !important`, not `0s`, because a true zero can break code
waiting on `transitionend`, and `0.01ms` parses to a positive number. The sweep
now compares against a 1 ms floor.


## SC-006 met: 2,672 px against a 2,800 px ceiling (T145)

**A 3.64× reduction at 390 px**, from 9,720 px to 2,672 px — 106.9 px per
result against 388.8. Under the ceiling at every width, measured by the T109
sweep:

| Width | Before | After | Per result |
|---|---|---|---|
| 390 px | 9,720 px | **2,672 px** | 388.8 → 106.9 |
| 768 px | 6,047 px | 2,162 px | 241.9 → 86.5 |
| 1024 px | 6,047 px | 2,080 px | 241.9 → 83.2 |
| 1440 px | 6,047 px | 2,080 px | 241.9 → 83.2 |

### How, and what each step was worth

Measured after each change rather than estimated, which is how the two
responsive decisions at the end got made at all — the first four changes left
it at 3,121 px, still 321 px over.

| Change | 390 px height | Per result |
|---|---|---|
| (start) five-pair `<dl>`, one asker per line, in a bordered card | 9,720 | 388.8 |
| Three-line row; card → a 1 px rule; labels → position and form | 3,466 | 138.6 |
| Row padding 10 px → 8 px; party hidden below 768 px | 3,121 | 124.8 |
| Asker names hidden below 768 px; figure label shortened | **2,672** | **106.9** |

The row now reads as the shape the owner selected:

```
* Drinking Water in Rural Areas
  2021-03-11 · Jal Shakti · unstarred · Fully linked
  asked by 4 of 4 identified
```

### A false flag found by measuring, not by reading

The first measurement after the rewrite showed the meta line at a **constant
78 px** — four lines where one was expected. The cause was not layout: every
single row was carrying the flag *"this ministry id is not in the published
ministry reference set"*, whose explanation is a block element inside the
ministry span.

It was a **real regression from the Phase 4 split**. `bootViews()` used to
fetch `reference/ministries.jsonl` on page load, so `views.ministryNames` was
always populated. T137 took that file off the first load and wired the ministry
views to fetch it — and missed the search view, which reads the map for every
result row. With an empty map, `ministryNameFor` fell through to its
unknown-id branch and flagged all 56 ministries, on a reference set that
contains every one of them.

`ensureMinistryNames()` in `lib/viewkit.js` now loads it for whichever view
needs it first, memoised, fetched in parallel with the search index — 1,856 B
against the index's 794,402, so it adds nothing measurable to a first search.

Worth recording for two reasons: the flag was *plausible* enough to be read as
a data problem rather than a code one, and the row-height figure was
unusable until it was fixed.

### What is hidden below 768 px, and what is not

Two responsive decisions, both forced by measurement and neither dropping a
field FR-101 requires:

- **The asker's party.** Parties in this record run to 48 characters
  (*"Nationalist Congress Party - Sharadchandra Pawar"*), and three inline is
  up to 150 characters for three names.
- **The asker names themselves.** The count stays — *"asked by 4 of 4
  identified"* — which is the shape the owner's own preview shows, and which
  is what FR-102 asks for: the askers inline rather than one per line, with
  the number stated against its total. FR-102 does not ask for every name on
  the row.

Both appear from 768 px, where the list measures 2,162 px against the 2,800 px
ceiling and has room. Every asker of every question remains in the published
`by-member` files, and the seat view names them on the member's own row.
