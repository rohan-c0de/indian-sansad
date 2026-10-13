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

To be filled by T109 before any densification work, so the result-list
reduction is measured against this harness rather than against the ~6,000 px
estimate the spec carries.

| Measurement | Pre-work | Target | Measured after |
|---|---|---|---|
| Result list, 25 results at 390 px | *(T109)* | ≤ 2,800 px | *(T145)* |
| First load, wire | 88,961 B | ≤ 160,000 B | *(T185)* |
| First load excluding fonts, wire | 88,961 B | ≤ 60,000 B | *(T185)* |
| First-load requests | 18 | ≤ 16 | *(T185)* |
| Font payload, wire | 0 B | ≤ 95,000 B | 60,684 B (T102) |
