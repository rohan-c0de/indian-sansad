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
| Result list, 25 results at 390 px | **9,720 px** (388.8 px each) | ≤ 2,800 px | *(T145)* |
| Result list, 25 results at 768/1024/1440 px | **6,047 px** (241.9 px each) | — | *(T145)* |
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
