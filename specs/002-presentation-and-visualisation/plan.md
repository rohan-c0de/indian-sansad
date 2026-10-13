# Implementation Plan: Presentation and Visualisation for the Published Lok Sabha Question Record

**Branch**: `002-presentation-and-visualisation` | **Date**: 2026-10-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-presentation-and-visualisation/spec.md`

## Summary

Restyle and restructure the page in `web/` so the published record reads as an institutional record rather than a generated template, make its result list scannable, turn five stacked sections into switchable views, add four visualisations the published aggregates already support, fix four measured tap-target defects, and close the three recorded open defects from feature 001. `data/published/` does not change.

The technical approach, settled in [research.md](./research.md):

- **Three pinned static font faces, 60,684 B** — not two variable fonts, which measure 98,392 B and break SC-002. Downloaded once from the Google Fonts `latin` subset, committed to `web/fonts/` with their OFL licences.
- **`app.js` splits at its existing seams** into a shell (8,103 B compressed) plus three view modules loaded by native `import()`, which is what lets FR-128 and FR-151 hold.
- **Hash routing over a static view map** — no router, no build step, deep-linkable on a static host.
- **The projected first load is ~101,537 B on the wire across 14 requests** — 1.14× the measured baseline, against SC-001's 160,000 B ceiling. The fonts do not double the first load, because deferring unopened views' code and data pays for them.
- **The two dead maintainer signals wire into an existing site**: the refresh workflow already checks out the previous published snapshot and passes `--previous` to the CLI, with a comment naming this exact purpose.

## Technical Context

**Language/Version**: ES modules (no transpilation, no polyfill), CSS (hand-written, no preprocessor), HTML5. Python 3.13 for the maintainer-side changes and the checks.

**Primary Dependencies**: None added at runtime — the page has none and keeps none. One **dev-only** addition: `fonttools[woff]`, solely so `tools/check_font_scope.py` can read a `woff2` `cmap` and prove FR-111. Runtime deps stay `httpx` and `polars`.

**Storage**: Static files. The page reads only `data/published/` over same-origin `fetch`. No browser storage of any kind is introduced.

**Testing**: `pytest` for the repository-side checks; `tools/drive_page.mjs` driving real Chrome over CDP for the page, extended with three measurement sweeps; `make validate` as the gate.

**Target Platform**: Static hosting on GitHub Pages (free tier), served from the `published` orphan branch. Modern evergreen browsers; the page requires `type="module"` support, which it already does.

**Project Type**: Static web page over a published dataset, plus the Python pipeline that builds the dataset.

**Performance Goals**: First load ≤160,000 B on the wire in ≤16 requests (SC-001, SC-004); non-font first load ≤60,000 B and *falling* from the measured 88,961 B (SC-003); a 25-result list ≤2,800 px tall at 390 px (SC-006); nothing fetched for an unopened view (SC-016).

**Constraints**: Zero running cost. No new infrastructure. No framework, no router library, no build step, no charting library. No request to any host but the serving one. English only, Latin codepoints only. No member attribute outside the FR-008 set. No view may need a term or session date — every one reads "not stated". `data/published/` is byte-identical before and after.

**Scale/Scope**: 12 files in `web/` today becoming ~20 (4 view modules, 3 fonts, 2 licence files, a provenance note); `app.js` 2,307 lines splitting four ways; 8 views; 4 new charts; 53 requirements; 25 success criteria.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution v1.0.0. Each gate maps to exactly one principle; a gate is passed by evidence, not assertion.

### Pre-Phase-0 evaluation — PASS (5 of 5)

| Gate | Principle | Evidence at planning |
|---|---|---|
| **Cost** | I | No component added. The three fonts are self-hosted on the **GitHub Pages free tier already in use**; at its limit (1 GiB per site, 100 GiB/month soft bandwidth) the remedy is to reduce payload, never to upgrade — the last measured build sat at 26% of the 1 GiB ceiling and 60,684 B of fonts does not move that. Hash routing is chosen specifically so no redirect configuration or server is needed (research R7). `fonttools[woff]` is a **dev** extra on free PyPI, never installed in the serving path. No trial, no credit. |
| **Upkeep** | II | Adds **zero** recurring manual work. FR-135's trigger is a drop against the previous publication precisely so the signal does *not* fire on every run — an absolute threshold against the 94.78% automatic rate would fire every time and manufacture upkeep. FR-139 keeps visitor-facing degradation quiet. Font acquisition is one-time and committed, not a scheduled step. |
| **Sources** | III | No document is opened. No ingest is added. The feature reads only files `data/published/` already carries. The fonts are font binaries, not document files, and nothing is extracted *from* them — `check_font_scope.py` reads a `cmap` to prove a negative. |
| **Language** | IV | FR-111, FR-144, SC-013. Latin-only is **provably sufficient**, not merely chosen: all 13 distinct non-ASCII codepoints in the published dataset fall inside the subset's `unicode-range`, and that range does not intersect U+0900–U+097F (research R3). No translation or transliteration path is introduced. |
| **Member fields** | V | FR-125 and SC-023 bound every new visualisation to the FR-008 set. The four new charts read `ministry-profile`, `composition`, `state-subjects` and the search index; the census in feature 001's `gate-evidence.md` records those sets as carrying `state` as their only member attribute, plus the name forms in the search index. FR-138 **strengthens** the enforcing check, which is the one place this feature improves Principle V rather than merely respecting it. |

### Post-Phase-1 re-evaluation — PASS (5 of 5)

Re-checked against the design in [data-model.md](./data-model.md) and [contracts/](./contracts/). Three things the design surfaced, none of them a violation:

1. **Principle I, re-checked against the dev dependency.** `fonttools[woff]` is the only dependency this feature adds anywhere. It is dev-only, free, and never reaches the serving path. The alternative — hand-rolling a brotli-plus-woff2 `cmap` reader — was rejected on risk, not on cost (research R4).
2. **Principle IV, re-checked against the binaries.** The existing guard gives the fonts **no coverage at all**: `.woff2` is in `UNSCANNABLE_SUFFIXES`, so `make guard` and `make audit-fields` skip them. Left alone, a font could carry anything with every check green. `check_font_scope.py` exists because of this, and the Language gate's evidence must be re-run over the font files rather than inherited from feature 001.
3. **Principle V, re-checked against `web/`.** The page's reachable attribute surface is bounded by what it fetches, and FR-151 *narrows* that surface on first load rather than widening it. The one addition is `aggregates/composition.jsonl`, whose member attributes are `state` and `party` as **categories, not as attributes of a named person** — no member id and no name form appears in it. Re-verified before publication per the constitution's "Before publishing" rule.

**No violations. The Complexity Tracking table below is therefore empty, as intended.**

## Project Structure

### Documentation (this feature)

```text
specs/002-presentation-and-visualisation/
├── spec.md              # Phase -1 (/speckit-specify)
├── plan.md              # This file (/speckit-plan)
├── research.md          # Phase 0 (/speckit-plan)
├── data-model.md        # Phase 1 (/speckit-plan)
├── quickstart.md        # Phase 1 (/speckit-plan)
├── contracts/
│   ├── view-routes.md       # the 8 views: hash, data, code, fetch timing
│   ├── design-tokens.md     # palette with measured ratios, faces with measured bytes
│   ├── chart-contract.md     # what every chart must carry
│   └── maintainer-signals.md # the 4 FR-011 signals, triggers, callers
├── checklists/
│   └── requirements.md  # spec quality + constitution gates
└── tasks.md             # Phase 2 (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
web/                               # the only directory this feature's page work touches
├── index.html                     # CHANGED: view nav, view containers, no eyebrow
├── style.css                      # CHANGED: new palette, @font-face, view/nav rules,
│                                  #   denser result rows, 13 uppercase rules deleted
├── app.js                         # CHANGED: 2,307 lines -> shell only (helpers,
│                                  #   coverage, sessions, licence, boot, router)
├── views/                         # NEW: loaded by import() on first use
│   ├── ministries.js              #   NEW (from app.js 772-1188) + House series chart
│   ├── search.js                  #   NEW (from app.js 1189-1672) + subject trend chart
│   ├── seat.js                    #   NEW (from app.js 1673-2307) + state subjects chart
│   └── composition.js             #   NEW: House composition, the one new fetch
├── fonts/                         # NEW: same-origin, Latin subset, committed
│   ├── newsreader-600.woff2       #   23,888 B
│   ├── ibm-plex-sans-400.woff2    #   17,604 B
│   ├── ibm-plex-sans-600.woff2    #   19,192 B
│   ├── OFL-Newsreader.txt         #   SIL OFL 1.1
│   ├── OFL-IBMPlexSans.txt        #   SIL OFL 1.1
│   └── PROVENANCE.md              #   source URL, subset, bytes, date per file
└── lib/                           # unchanged in purpose; chart.js gains series/forms
    ├── chart.js                   # CHANGED: grouped + horizontal bars, --series-2
    ├── fetch.js                   # CHANGED: composition loader, per-view assertions
    └── (coverage, format, licence, search, tokenise, constituency, profile).js

src/sansad/
├── cli.py                         # CHANGED: wire the two signals at the --previous site
├── model/member.py                # CHANGED: declared name-form synonyms (FR-138)
└── signals/alerts.py              # CHANGED: rate trigger becomes a drop, not a threshold

tools/
├── drive_page.mjs                 # CHANGED: 4 widths, per-view screenshots,
│                                  #   tap-target + list-height + h-scroll sweeps
├── check_font_scope.py            # NEW: woff2 cmap vs Devanagari, family, licence
├── check_contrast.py              # NEW: recompute every palette pair from the tokens
└── guard_no_raw_payloads.py       # CHANGED: field-scope diff resolves the synonyms

tests/
├── unit/test_page_fetch_layer.py  # CHANGED: url() invariant narrowed, import() covered
├── unit/test_state_transitions.py # CHANGED: the "has no caller" assertion inverts
└── (new tests for the router, the views, the signals, the fonts)

Makefile                           # CHANGED: check-fonts, check-contrast targets;
                                   #   validate gains them
pyproject.toml                     # CHANGED: fonttools[woff] in the dev extra only
```

**Structure Decision**: the existing layout is kept and extended; nothing moves. Two directories are new, both under `web/`: `views/` for the deferred view modules and `fonts/` for the three faces and their licences. `web/lib/` keeps its meaning — shared, view-agnostic modules — while `web/views/` holds the per-view render code that used to be inside `app.js`. That boundary is what makes "is this on the first load?" answerable by looking at the path.

The publish step needs **no change**: it runs `cp -R "${GITHUB_WORKSPACE}/web/." .`, so `web/fonts/` and `web/views/` land at the branch root alongside `app.js`, and `tests/unit/test_published_branch_layout.py` already asserts that nested page directories survive the copy.

## Phase 1 Design Artifacts

| Artifact | What it fixes in place |
|---|---|
| [data-model.md](./data-model.md) | The eight views and their state; the result row's fields; the figure-and-denominator pairing; the chart series model; the signal comparison inputs. |
| [contracts/view-routes.md](./contracts/view-routes.md) | Each view's hash, heading, module, data files, and the exact moment each fetch is permitted. The enforceable form of FR-126, FR-127, FR-151 and FR-153. |
| [contracts/design-tokens.md](./contracts/design-tokens.md) | The six palette tokens with every computed ratio, the three faces with measured bytes and `unicode-range`, the two series marks with the emptiness proof, and the weight set. |
| [contracts/chart-contract.md](./contracts/chart-contract.md) | The five obligations every chart carries — basis, denominator, table, text-identifiable series, stroke separation — and the four charts against them. |
| [contracts/maintainer-signals.md](./contracts/maintainer-signals.md) | All four FR-011 signals: trigger, severity, payload, caller, and what each reads from the previous publication. |
| [quickstart.md](./quickstart.md) | The runnable validation scenarios, one per success criterion that can be checked by running something. |

## Implementation Sequence

Dependency-ordered. Each step leaves the page working; none requires the next to have happened.

1. **Tokens and type** (US2) — palette, `@font-face`, the three faces committed, weight normalisation, the 13 uppercase rules and the eyebrow deleted, `check_contrast.py`, `check_font_scope.py`, the narrowed `url()` invariant. *Nothing structural moves; the page is restyled in place.*
2. **The router and the split** (US3) — view nav, hash map, `app.js` → shell + three view modules, `import()` on first use, the widened import check, the per-view fetch assertions. *This is the riskiest step and the one everything after it sits on.*
3. **The denser result row** (US1) — the five-pair block becomes subject + meta line + inline askers, the asterisk device, figure-and-denominator pairings, the height measurement.
4. **Operability** (US7) — tap targets including the four known failures, focus rings per ground, reduced motion, the three driver sweeps at four widths.
5. **The charts** (US4, US5, US6) — `chart.js` gains grouped and horizontal forms and `--series-2`; then the House series, the subject trend, the two-ministry comparison, composition, state subjects.
6. **The maintainer side** (US8) — the two signals at the `--previous` site, the rate trigger change, the name-form synonyms, the inverted "no caller" test.
7. **Measure and record** (FR-129) — deploy, read the live wire figures, record them beside the 2026-10-10 numbers, capture screenshots at four widths per view.

Step 1 before 2 so the restyle is not entangled with the split. Step 2 before 5 so each chart lands in a view that exists. Step 6 is independent of 1–5 and can run in parallel. **Step 7 cannot be faked from a local run** — `make serve-local` compresses nothing and `measure_first_load.py` says so every run.

## Risks

| Risk | Why it matters | Mitigation |
|---|---|---|
| The `app.js` split regresses a working view | 2,307 lines move; the page is the only thing a visitor sees, and all four views are proven working today | Split at the measured seams (research R5), which were checked to share no view-only library; move code without editing it, then edit; `make test-page` drives every view after each move |
| One variable too many at once | Palette, type, density, structure and four charts in one feature | The sequence above changes one layer per step and leaves the page working at each; the step-1 restyle moves nothing structural |
| SC-006's 2,800 px ceiling is wrong | It is derived, not measured | Measure after step 3 and report the figure; if the denser row cannot reach it, say so and let the owner retarget rather than hiding the miss |
| A font byte figure is a `gstatic` `content-length`, not this site's | SC-002 is measured on the wire | Re-measure after deploy under FR-129; `woff2` is pre-compressed so it should carry across, but that is UNVERIFIED |
| `prefers-reduced-motion` may not be reachable through the driver | SC-010 would become a static check | Try `Emulation.setEmulatedMedia`; if unavailable, record SC-010 as a stylesheet assertion and mark it weaker rather than claiming a browser check |
| The first run has no previous publication | FR-134/135 have nothing to diff | FR-136: record "no comparison made". The workflow's checkout is already `continue-on-error: true` |

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified.

**No violations.** All five gates pass pre-Phase-0 and post-Phase-1. No entry is required, and none is invented to fill the table.
