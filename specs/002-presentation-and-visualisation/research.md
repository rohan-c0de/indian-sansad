# Phase 0 Research: Presentation and Visualisation

**Feature**: `002-presentation-and-visualisation` | **Date**: 2026-10-10

Every figure below was executed, not estimated. Where something was taken on trust it is marked UNVERIFIED and says what would settle it.

---

## R1 — Which font faces, and do they fit SC-002's 95,000 B ceiling?

**Decision**: three pinned static instances from the Google Fonts `latin` subset, **60,684 B total across 3 files**.

| Face | Role | Bytes (woff2, `latin`) |
|---|---|---|
| Newsreader 600 | all headings | 23,888 |
| IBM Plex Sans 400 | body, data, tables | 17,604 |
| IBM Plex Sans 600 | figures, denominators, table heads, emphasis | 19,192 |
| **Total** | | **60,684** |

**Rationale**: SC-002 allows 95,000 B across at most 4 files. This lands 36% under it, with headroom for a fourth face if the build needs one. Headings differentiate by size, not weight, so one Newsreader weight suffices; the body needs two so that a figure can sit against its denominator (FR-114) with weight rather than with the uppercase labels FR-115 deletes.

**Measured, by `content-length` on `fonts.gstatic.com`:**

```
Newsreader:wght@400..700  (variable, latin)   58,152 B
Newsreader:wght@400       (pinned, latin)     22,504 B
Newsreader:wght@500                           23,748 B
Newsreader:wght@600                           23,888 B
Newsreader:wght@700                           23,916 B
IBM+Plex+Sans:wght@400..600 (variable, latin) 40,240 B
IBM+Plex+Sans:wght@400                        17,604 B
IBM+Plex+Sans:wght@500                        19,224 B
IBM+Plex+Sans:wght@600                        19,192 B
```

**Alternatives considered:**

- **Two variable fonts, one per family** — the obvious reading of the spec. **Rejected: 58,152 + 40,240 = 98,392 B, which breaks SC-002 by 3,392 B.** Narrowing the axis does not help: `wght@400..600` and `wght@400..500` both return the identical 58,152 B file, because the whole axis ships regardless of the range requested. This is the single most useful thing this research found, and it would have been discovered at implementation as a blown budget.
- **Four faces** (Newsreader 400 + 600, Plex 400 + 600) — 83,188 B. Fits, but spends 22,504 B on a second heading weight that size contrast already provides.
- **Raising SC-002.** Rejected: the spec states the budget "is the constraint it must fit inside, not a figure to raise", and three faces fit.

---

## R2 — How are the fonts acquired, given "no build step"?

**Decision**: download the three `latin`-subset `woff2` files once, commit them to `web/fonts/`, and commit each family's `OFL.txt` beside them. Record the source URL, the subset, the byte count and the date in `web/fonts/PROVENANCE.md`.

**Rationale**: "No build step" constrains the *serving* path — nothing may be compiled, bundled or generated between the repository and the browser. A one-time acquisition by the maintainer, whose output is committed, is not in that path. Google Fonts already serves per-subset `woff2`, so **no subsetting tool is needed**: the `latin` file is downloaded as-is. This matters because `pyftsubset` would have been a genuine build dependency.

**Licence — VERIFIED**: both families are **SIL Open Font License 1.1**, read from `github.com/google/fonts`:

- Newsreader — "Copyright 2020 The Newsreader Project Authors … licensed under the SIL Open Font License, Version 1.1"
- IBM Plex Sans — "Copyright © 2017 IBM Corp. with Reserved Font Name "Plex" … licensed under the SIL Open Font License, Version 1.1"

OFL 1.1 permits bundling and redistribution provided the licence travels with the font. IBM Plex carries the Reserved Font Name "Plex", which constrains *renaming a modified version* — not relevant here, since the files are redistributed as Google publishes them rather than modified.

**Alternatives considered**: linking `fonts.googleapis.com` (rejected outright — FR-141 and the whole point of T082); vendoring the upstream TTF and subsetting locally (rejected — adds `fonttools` to the acquisition path for no gain, since the subset already exists).

---

## R3 — Is the Latin subset actually sufficient for this record?

**Decision**: yes — no further subset range is needed, and zero Devanagari enters the repository. **But see the correction below**: three of the 13 dataset codepoints are in the declared `unicode-range` and *not* in the fonts, so they do fall back to a system face. The claim originally made here, that none would, was wrong.

**Rationale and evidence**: both families' `latin` `@font-face` carries the identical `unicode-range`:

```
U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC,
U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193,
U+2212, U+2215, U+FEFF, U+FFFD
```

Gate 4 of feature 001 enumerated every distinct non-ASCII codepoint in the published dataset — 13 of them, across 2,894 lines. **All 13 fall inside that range**, checked codepoint by codepoint:

```
U+2019 YES  1967  RIGHT SINGLE QUOTATION MARK
U+2013 YES   724  EN DASH
U+2018 YES   453  LEFT SINGLE QUOTATION MARK
U+201D YES    79  RIGHT DOUBLE QUOTE
U+201C YES    62  LEFT DOUBLE QUOTE
U+2011 YES    51  NON-BREAKING HYPHEN
U+00A0 YES    35  NO-BREAK SPACE
U+00F1 YES    23  n WITH TILDE
U+00E8 YES    16  e WITH GRAVE
U+202F YES    14  NARROW NO-BREAK SPACE
U+2014 YES    13  EM DASH
U+00E9 YES     6  e WITH ACUTE
U+2060 YES     5  WORD JOINER
uncovered: 0 of 13
Devanagari U+0900-U+097F intersects the subset: False
```

So FR-111 is satisfied **by the subset's construction**, and the Latin-only decision is sufficient rather than merely permitted. The en dash at U+2013 is worth noting: FR-115 deletes the em-dash *heading construction*, not the dashes the source itself wrote, and those keep their glyphs.

### CORRECTION, 2026-10-13 (T102) — the declared range is wider than the actual `cmap`

The table above is a check against the **declared `unicode-range`**. Once the
three files were downloaded, their `cmap` tables were read directly, and
**three of the 13 are in none of the three fonts**:

| Codepoint | Occurrences | In any shipped font? |
|---|---|---|
| U+2011 NON-BREAKING HYPHEN | 51 | no |
| U+202F NARROW NO-BREAK SPACE | 14 | no |
| U+2060 WORD JOINER | 5 | no |

70 occurrences across 95,268 questions. A codepoint inside `unicode-range` but
absent from the font causes the browser to select the face, find no glyph, and
continue down the stack for that one character — so these three render from a
system face. Two are invisible (a narrow space, a zero-width joiner); the third
is 51 hyphens set in a slightly different face.

**The sentence "no character in the record falls back to a system font
mid-word", stated in this section and repeated in `contracts/design-tokens.md`,
is wrong.** It was true of the declared range and false of the fonts. The
finding is accepted rather than fixed — rewriting the codepoints at render time
would change what the page shows relative to what the record says — and is
recorded in `web/fonts/PROVENANCE.md` with the rejected alternatives.

FR-111 and SC-013 are **unaffected**: all three fonts carry zero Devanagari,
verified from the `cmap` rather than from the subset's name.

---

## R4 — How is FR-111 / SC-013 actually checked, on a binary?

**Decision**: add `fonttools[woff]` to the **dev** extra only, and write `tools/check_font_scope.py` asserting, per font file: no `cmap` codepoint in U+0900–U+097F; the expected family name and weight; and that an `OFL.txt` sits beside it.

**Rationale**: the existing guard gives **zero** coverage here, and this was verified rather than assumed — `.woff2` is a member of `UNSCANNABLE_SUFFIXES` in `tools/guard_no_raw_payloads.py`, so `make guard` and `make audit-fields` *skip* font files entirely. The 64 KB payload ceiling also does not apply, because `PAYLOAD_SUFFIXES` lists only data formats. A font could therefore carry anything and every existing check would stay green. Reading the `cmap` is the only honest check, and it needs a font library.

Principle I is unaffected: a dev-only dependency on a free PyPI package adds no running cost. Principle II is unaffected: the check runs in CI alongside the others.

**Alternatives considered:**

- **Scan the binary as text for Devanagari bytes.** Rejected: a `woff2` is brotli-compressed, so the scan would be meaningless in both directions — false negatives guaranteed, false positives likely. This is presumably why `.woff2` is in `UNSCANNABLE_SUFFIXES` already.
- **Assert the `unicode-range` in the stylesheet instead.** Rejected as the *only* check: it constrains what the browser will use the font for, not what entered the repository, and Principle IV is about the repository. It is worth keeping as a *second*, cheap assertion.
- **Hand-roll a woff2 `cmap` reader.** Rejected: requires brotli plus the woff2 table-transform rules; far more code and risk than a dev dependency.

---

## R5 — How does `app.js` split so FR-128 can hold?

**Decision**: split `web/app.js` (2,307 lines) at its existing seams into a shell plus three view modules, loaded by `import()` on first use. A fourth view module is new.

Measured at `gzip -6` by extracting each line range:

| Module | Lines today | raw | `gzip -6` | On first load? |
|---|---|---|---|---|
| `app.js` shell — helpers, coverage, sessions, licence, `boot`, router | 1–771 | 25,837 | 8,103 | yes |
| `views/ministries.js` — profile, compare, House series | 772–1188 | 14,859 | 4,560 | no |
| `views/search.js` — search, results, subject trend | 1189–1672 | 16,685 | 5,516 | no |
| `views/seat.js` — state, constituency, member | 1673–2307 | 22,724 | 6,412 | no |
| `views/composition.js` — new | — | — | ~1,500 est. | no |

**The seam is clean, and that was checked rather than assumed**: lines 89–580 — the shared DOM helpers, `renderCoverage`, `renderSessions`, `renderLicence`, `renderUnavailable` and `boot` — reference **none** of `stackedColumns`, `legend`, `seatById`, `seatsInState`, `stateSubjects`, `positionsFor`, `loadSearchIndex`, `profileSessions`, `selectSpan` or `subjectTally`. The landing view touches no view-only library.

Splitting costs about 3,200 B in total compressed size (one large file compresses better than four small ones) but moves **13,269 B off the first load**: 21,372 → 8,103.

Lines 581–771 — `views` state, `option`, `labelledSelect`, `basisBlock`, `changeText`, `statusStrip`, `mixTable` — are shared by more than one view and stay in the shell. `ministryNameFor` is shared by the search and ministry views, so **both** read `reference/ministries.jsonl` on their own first use; it is 1,856 B and is read once between them.

**Alternative considered**: leave `app.js` monolithic and defer only the `lib/` modules and the two aggregates. That still satisfies SC-003 (non-font first load ≈ 54,000 B, under the 60,000 B ceiling) but leaves FR-128 unmet on its own terms, since every view's render code would still ship on load. Rejected: FR-128 is a requirement, not an optimisation.

---

## R6 — Native `import()`, and the check that currently misses it

**Decision**: use native dynamic `import()` with relative specifiers. **And widen `test_no_page_file_imports_anything_but_a_relative_path` to cover the call form, because it does not today.**

**Rationale**: `import()` is native to every browser that supports `type="module"`, needs no bundler and no import map, and is the only way to defer code without a build step.

**VERIFIED gap** — the existing check's pattern is `(?:from|import)\s+["']([^"']+)["']`, which requires whitespace after `import` and so never matches a call:

```
'import { x } from "./lib/a.js";'          -> ['./lib/a.js']
'await import("./lib/a.js")'               -> []
'const m = await import("./views/search.js");' -> []
```

So every dynamic import this feature adds would escape the relative-specifier check entirely, and a bare or cross-origin specifier could land with the suite green. The pattern must also accept `import` followed by `(`.

---

## R7 — Hash routing without a router

**Decision**: a `hashchange` listener over a static map of `#hash → {render, loader}`; `aria-current="page"` on the active navigation item plus a non-colour cue (a `--house` rule beneath it, per FR-149); focus moved to the newly rendered view's heading on switch; an unknown or empty hash resolves to the coverage view (FR-153).

**Rationale**: `hashchange` gives back/forward for free (FR-147) and needs no server rewrite, which is what keeps Principle I intact on GitHub Pages — a path-routed view would 404 on direct load and would need redirect configuration the free tier does not offer.

**Accessibility specifics this must get right**, because switching views without a page load is silent by default: move focus to the view's `<h2>` with `tabIndex = -1` so a keyboard user lands in the new content, and keep the skip link pointing at the view container so it still works per view. The existing page already uses this `tabIndex = -1` focus-move pattern on `result-subject`, so it is consistent with what is there.

**Alternatives considered**: the History API with `pushState` (rejected — same deep-link problem on a static host, and no benefit over a hash); separate HTML files per view (rejected — duplicates the shell five times and reloads the fonts and stylesheet relationship on every move, and `index.html` is hand-written with no templating).

---

## R8 — The second chart series colour, which the palette does not name

**Decision**: `--series-2: #5F7D94`. Series 1 is `--house #1F5D3E`, which FR-106 permits on a mark.

**And a proof the spec needs**: *no* colour can be simultaneously ≥3:1 against the near-white grounds and ≥3:1 against `--house`. This is arithmetic, not taste:

```
--paper luminance        L_p = 0.8585
--house luminance        L_h = 0.0847
paper:house ratio            = 6.75:1
pure black on paper          = 18.17:1   (the darkest possible)

A DARKER second mark needs >=3:1 from house, so >=3 x 6.75 = 20.25:1 from paper.
  Unattainable: the maximum is 18.17:1.
A LIGHTER second mark needs 3(L_h+0.05) <= L_c+0.05 <= (L_p+0.05)/3,
  which requires paper:house >= 9:1. It is 6.75:1.
  Window: [0.4040, 0.3028] -> EMPTY
```

So **FR-122's stroke-separation clause applies by necessity**, not by preference: adjacent segments in a stacked column must be separated by a stroke in the surface colour, every series must be named in text, and the table beside the chart stays authoritative. The current chart already strokes each segment with `--surface` at 0.3 width, so the mechanism exists; only the colours change.

| Candidate | vs `--paper` | vs `--sheet` | vs `--house` |
|---|---|---|---|
| `#6F88BD` (today's `--bar-unstarred`) | 3.06:1 | 3.48:1 | 2.20:1 |
| `#6E8AA0` | 3.13:1 | 3.55:1 | 2.16:1 |
| **`#5F7D94` (chosen)** | **3.75:1** | **4.25:1** | **1.80:1** |
| `#66798F` | 3.87:1 | 4.39:1 | 1.74:1 |

`#5F7D94` is chosen over today's `#6F88BD` because 3.06:1 on `--paper` is 2% above the floor — a margin that any future tweak to the ground erases silently. 3.75:1 survives one. Charts additionally sit on `--sheet`, where it is 4.25:1.

---

## R9 — Narrowing the no-`url()` invariant

**Decision**: replace the assertion `"url(" not in body` in `tests/unit/test_page_fetch_layer.py::test_the_stylesheet_fetches_nothing` with: every `url()` in the stylesheet is a relative path, resolves inside `web/`, and names a file that exists; and no `@import` and no off-host reference anywhere in `web/`.

**Rationale**: FR-112 requires the invariant narrowed rather than deleted. The current assertion is a proxy for "makes no off-host request", which `url(fonts/x.woff2)` does not violate. Checking that the target *exists* is strictly stronger than today's check in one respect — it catches a typo'd font path, which today's stylesheet could not have.

`test_no_page_file_names_another_host` is unaffected: it matches hosts, and a relative path names none. UNVERIFIED by execution: that no *other* test asserts the no-font property. `grep` over `tests/` found the two assertions quoted in the spec; a third could exist under a name the grep missed.

---

## R10 — Where the two dead signals get wired

**Decision**: wire both at the existing `--previous` consumption site in `src/sansad/cli.py`. **The comparison infrastructure already exists** — this is a smaller change than the spec's framing implies.

**VERIFIED**: `.github/workflows/refresh.yml` already checks out the previous published snapshot *before* anything overwrites it, and passes it to the CLI:

```yaml
- name: Check out the previous published snapshot
  id: previous
  continue-on-error: true          # the first run has no `published` branch
  uses: actions/checkout@v4
  with: { ref: published, path: .previous-snapshot, fetch-depth: 1 }
...
    python -m sansad.cli --source upstream \
      --published-dir data/published --previous .previous-snapshot
```

and the step's own comment already names the purpose: *"FR-010's last-known-good and FR-011's signal for a question leaving `resolved` both need the prior record to compare against."* So the wiring was designed and then not done. `cli.py:304` consumes `previous_dir` via `retain_previous`; the two signal calls belong beside it.

What each reads from the previous snapshot:

- **FR-134 `resolved_transitions_out`** — `by-session/*.jsonl` → `resolution_status` per `question_id`, which is published per question (verified: `lok-sabha/17/1/starred/500` carries `"resolution_status": "resolved"`). Diff previous `resolved` against current not-`resolved`.
- **FR-135 `resolution_rate_below_target`** — `manifest.json` → `resolution_rate_automatic` and `resolution_rate_including_assertions`, both published (verified: `0.947831` and `0.963555`). Raise only on a **drop** against the previous value.

`continue-on-error: true` on the checkout means `.previous-snapshot` may be absent on the first run. FR-136 governs: record "no comparison made", not a pass.

The signal function already distinguishes the two rates with `is_automatic_rate`, raising NOTICE for automatic and DEGRADED for published. That distinction stays; the **trigger** changes from absolute to a drop.

---

## R11 — The field-scope check and `representations.member_name`

**Decision**: give `sansad.model.member` a declared synonym set for name forms, and have the field-scope diff resolve `representations.member_name` through it.

**Rationale**: `PUBLISHED_FIELDS` carries `canonical_name` and `name_variants` but not `member_name`, so the automated diff classifies a genuine FR-008 name form as unclassified. `gate-evidence.md` names two remedies — rename the published key, or declare a synonym. **Renaming is not available**: FR-140 forbids changing `data/published/`, and `representations.member_name` is a published key pinned by `tests/contract/test_constituency_reference.py`. So the synonym it is.

Note the ingest-side allowlist is *not* the defect: `src/sansad/ingest/field_allowlist.py` already carries `membername` in `_PERMITTED_KEYS`. The weakness is only in the published-record diff.

---

## R12 — Measuring the accessibility criteria

**Decision**: extend `tools/drive_page.mjs` rather than add a tool. Change `SCREENS` from `{390, 1280}` to `{390, 768, 1024, 1440}`, screenshot per view, and add three sweeps run at each width:

1. **Tap targets (SC-008)** — every `a, button, input, select, [tabindex]`, its `getBoundingClientRect()`, failing any under 44 px in either dimension.
2. **Result-list height (SC-006)** — the rendered height of the result list after a 25-result query at 390 px.
3. **Horizontal scroll (SC-007)** — `documentElement.scrollWidth <= clientWidth`.

Plus a contrast script that recomputes every palette pair from the stylesheet's own token values, so SC-005's recorded figures cannot drift from the tokens.

**Rationale**: the driver already has an `evaluate()` bridge and already calls `getBoundingClientRect()` for clipped screenshots, so these are additions to a working harness, not new infrastructure. No box-measurement *sweep* exists yet, which is why the four under-size links were found by hand.

Wire figures still come from the live deployment: `tools/measure_first_load.py` documents that `make serve-local` compresses nothing and asserts it from the recorded headers.

**RESOLVED 2026-10-13 (T110)**: `prefers-reduced-motion` (SC-010) **is** reachable through the existing CDP bridge. `Emulation.setEmulatedMedia` is accepted, the media query matches inside the driver, and the page already honours it at `web/style.css:676`. No fallback is needed and SC-010 is a genuine browser check.

One trap found while building it, recorded because trusting the check would have damaged correct code: a first version tested `transitionDuration > 0` and condemned every element on the page. The conventional reduced-motion reset is `transition-duration: 0.01ms !important`, not `0s` — a true zero can break code waiting on `transitionend` — and `0.01ms` parses to a positive number. The sweep compares against a 1 ms floor instead.

---

## R13 — Weight normalisation

**Decision**: the stylesheet ships `400` and `600` only.

It uses three weights today — `600` ×19, `700` ×17, `400` ×1 — against three faces offering 400 and 600. Every `700` must become `600` or the browser synthesises a bold, which on a serif heading looks like a mistake. Most of the `700` uses sit on the uppercase label rules FR-115 deletes, so this is largely absorbed by work already required.

---

## R14 — The first-load projection, re-derived

With R1, R5 and FR-151 together:

| Component | `gzip -6` wire estimate |
|---|---|
| `index.html` (+ nav markup) | 2,600 |
| `style.css` (new palette, `@font-face`, nav and view rules, minus deleted label rules) | 11,500 |
| `app.js` shell (+ router) | 9,100 |
| `lib/`: `fetch`, `coverage`, `format`, `licence` | 12,203 |
| landing data: `coverage`, `sessions`, `counting-basis`, `manifest` | 4,540 |
| response headers, ~11 requests | ~715 |
| **Non-font subtotal** | **~40,658** |
| 3 font files + headers | 60,879 |
| **Projected first load** | **~101,537 B, 14 requests** |

Against the spec's ceilings: SC-001 160,000 (**58,463 B headroom**), SC-002 95,000 (**34,316 B**), SC-003 60,000 (**19,342 B**), SC-004 16 requests (**2**).

**This is 1.14× the measured 88,961 B baseline, not the 2× the brief estimated and not the 1.80× the spec's ceiling allows for.** The three-face decision in R1 and the `app.js` split in R5 are what buy that. The ceilings are deliberately left where the spec set them — a ceiling with headroom is not a reason to re-target, and these are estimates until measured on the live deployment under FR-129.

---

## Carried forward as UNVERIFIED

| Claim | What would settle it |
|---|---|
| The 2026-10-10 live wire figures | Re-read `Content-Length` and `Content-Encoding` from the live deployment. The offline `gzip -6` sum agrees to within 1,180 B, which is corroboration only. |
| The three font files total 60,684 B *as served by GitHub Pages* | `woff2` is already compressed and Pages will not re-encode it, so the figure should carry across unchanged — but it is a `fonts.gstatic.com` `content-length`, not a measurement of this site. |
| ~~`prefers-reduced-motion` is reachable through the driver~~ | **RESOLVED 2026-10-13 (T110): it is.** `Emulation.setEmulatedMedia` works, the media query matches inside the driver, and `web/style.css:676` already honours it. SC-010 is a browser check, not the fallback stylesheet assertion. |
| No third test asserts the no-web-font property | A wider grep over `tests/` for `woff`, `font-face`, `@import`. |
| The 2,800 px result-list ceiling (SC-006) | Build one denser row and measure 25 of them at 390 px. |
