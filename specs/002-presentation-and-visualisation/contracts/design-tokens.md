# Contract: Design Tokens

**Feature**: `002-presentation-and-visualisation` | **Date**: 2026-10-10

The single definition of every colour, face and weight. The stylesheet records these figures beside the tokens (FR-107); `tools/check_contrast.py` recomputes them from the token values so the record cannot drift from what is served.

All ratios computed with the WCAG relative-luminance formula. Text floor **4.5:1**; meaning-carrying marks **3:1**.

## Palette

```css
:root {
  --paper:    #EEEFEA;  /* page ground                                   */
  --sheet:    #FDFDFB;  /* surfaces                                      */
  --ink:      #15253A;  /* body text                                     */
  --ink-soft: #4A5663;  /* notes and meta                                */
  --house:    #1F5D3E;  /* institutional marker — rules and marks ONLY   */
  --mark:     #8C3325;  /* links and focus ring                          */
  --series-2: #5F7D94;  /* second chart series — see the proof below     */
}
```

`--house` is the Lok Sabha chamber colour, which also reserves red for the Rajya Sabha if a second House is ever covered. `--mark` is unchanged from the current stylesheet.

### Computed ratios — text

| Foreground | on `--paper` | on `--sheet` | Verdict |
|---|---|---|---|
| `--ink` `#15253A` | **13.38:1** | **15.19:1** | PASS |
| `--ink-soft` `#4A5663` | **6.48:1** | **7.36:1** | PASS |
| `--house` `#1F5D3E` | **6.75:1** | **7.66:1** | PASS |
| `--mark` `#8C3325` | **6.95:1** | **7.88:1** | PASS |

All eight clear 4.5:1 with margin. The narrowest is `--ink-soft` on `--paper` at 6.48:1, 44% above the floor.

### Computed ratios — marks

| Mark | on `--paper` | on `--sheet` | Verdict |
|---|---|---|---|
| `--house` (rules, series 1, the asterisk) | 6.75:1 | 7.66:1 | PASS |
| `--mark` (focus ring) | 6.95:1 | 7.88:1 | PASS |
| `--series-2` `#5F7D94` | **3.75:1** | **4.25:1** | PASS |

### Pairs that do NOT clear a floor, and what carries the meaning instead

Recorded here because an unrecorded near-miss is the one that gets broken later.

| Pair | Ratio | Consequence |
|---|---|---|
| `--paper` vs `--sheet` | **1.13:1** | A surface is effectively invisible against the page ground by fill alone. **FR-108**: any surface distinction a reader needs is carried by a rule, a boundary or space — never by the fill difference. This is also why FR-115's uniform card can go without losing information: the card's *border* was doing the work, not its fill. |
| `--house` vs `--mark` | **1.03:1** | Nearly identical in luminance, separable only by hue — so unavailable to a reader with a red-green deficiency. **FR-109**: these two are never the only difference between two meanings. `--house` marks the institution; `--mark` marks interaction; nothing is distinguished by *which of the two* it is. |
| `--series-2` vs `--house` | **1.80:1** | Below the 3:1 adjacent-mark floor. **Unavoidable — see the proof below.** Adjacent segments are stroked in the surface colour, every series is named in text, and the table beside the chart is authoritative. |

### Proof: no second series colour can clear 3:1 from both the ground and `--house`

Not a design compromise; an arithmetic impossibility.

```
--paper luminance        L_p = 0.8585
--house luminance        L_h = 0.0847
paper:house ratio            = 6.75:1
pure black on paper          = 18.17:1   (the darkest attainable)

A DARKER second mark needs >=3:1 from --house, hence >=3 x 6.75 = 20.25:1 from --paper.
  Unattainable: the maximum is 18.17:1.

A LIGHTER second mark needs  3(L_h+0.05) <= L_c+0.05 <= (L_p+0.05)/3,
  which requires paper:house >= 9:1.  It is 6.75:1.
  Window: [0.4040, 0.3028]  ->  EMPTY
```

So FR-122's stroke-separation clause is **required**, not preferred. `#5F7D94` is chosen over today's `--bar-unstarred #6F88BD` (3.06:1 on `--paper`) because 3.06:1 sits 2% above the floor, a margin any later tweak to the ground erases silently; 3.75:1 survives one.

A third series, if one ever appears, uses the existing hatch pattern — never a lighter colour, which is where the 3:1 floor gets broken quietly.

## Type

Self-hosted, same-origin, `latin` subset only (FR-110, FR-111). **Three faces, 60,684 B** — against SC-002's 95,000 B ceiling across at most 4 files.

| File | Family | Weight | Role | Bytes |
|---|---|---|---|---|
| `fonts/newsreader-600.woff2` | Newsreader | 600 | all headings | 23,888 |
| `fonts/ibm-plex-sans-400.woff2` | IBM Plex Sans | 400 | body, data, tables | 17,604 |
| `fonts/ibm-plex-sans-600.woff2` | IBM Plex Sans | 600 | figures, denominators, table heads, emphasis | 19,192 |
| | | | **Total** | **60,684** |

```css
@font-face {
  font-family: "Newsreader";
  font-style: normal;
  font-weight: 600;
  font-display: swap;
  src: url(fonts/newsreader-600.woff2) format("woff2");
  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6,
                 U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F,
                 U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215,
                 U+FEFF, U+FFFD;
}
/* IBM Plex Sans 400 and 600: same unicode-range. */

:root {
  --font-head: "Newsreader", Charter, "Iowan Old Style", "Palatino Linotype", Georgia, serif;
  --font-body: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
```

The fallback stacks are the current system stacks, unchanged (FR-110), so a blocked or failed font leaves the page readable in exactly what it uses today. `--font-mono` ships no file and stays on system faces.

### Weights

**400 and 600 only.** The stylesheet uses three today — `600` ×19, `700` ×17, `400` ×1 — and every `700` must become `600`, or the browser synthesises a bold, which on a serif heading reads as a defect. Most of the `700` uses sit on the uppercase label rules FR-115 deletes, so this is largely absorbed by work already required.

### No italic

No italic face ships. The stylesheet has exactly three italic rules today — `.not-stated`, `.result-subject-missing`, `.result-no-asker` — and **all three mark absence, which is already carried by a word** ("not stated", the missing-subject text, "no asking member is identified"). Italic is a third, redundant cue. Absence is carried by the word plus `--ink-soft`.

If the build finds it needs italic, IBM Plex Sans italic 400 is ~18,000 B and fits inside SC-002 (60,684 + 18,000 = 78,684 of 95,000) as a fourth file. Synthetic oblique MUST NOT be used instead.

### Why `latin` is sufficient, not merely chosen

All 13 distinct non-ASCII codepoints in the published dataset fall inside that `unicode-range`, and the range does not intersect Devanagari U+0900–U+097F. Verified codepoint by codepoint in [research.md](../research.md) R3. **FR-111 holds, verified from each font's `cmap` rather than from the subset's name: zero Devanagari in all three files.**

**Corrected 2026-10-13**: the declared `unicode-range` is wider than the fonts' actual `cmap`, and **three of the 13 are in none of the three faces** — U+2011 non-breaking hyphen (×51), U+202F narrow no-break space (×14), U+2060 word joiner (×5), 70 occurrences in 95,268 questions. Those three render from the fallback stack; two are invisible and the third is 51 hyphens at a slightly different face. Accepted, not fixed, with the rejected alternatives recorded in `web/fonts/PROVENANCE.md`. An earlier draft of this line claimed no character falls back mid-word, which was true of the declared range and false of the fonts.

Note the en dash U+2013 appears 724 times in the record: FR-115 deletes the em-dash **heading construction**, not the dashes the source itself wrote.

## Provenance

`web/fonts/PROVENANCE.md` records, per file: the `fonts.gstatic.com` URL, the `css2` query that produced it, the subset, the byte count, and the acquisition date. Both licences ship beside the fonts:

- `fonts/OFL-Newsreader.txt` — SIL OFL 1.1, "Copyright 2020 The Newsreader Project Authors"
- `fonts/OFL-IBMPlexSans.txt` — SIL OFL 1.1, "Copyright © 2017 IBM Corp. with Reserved Font Name 'Plex'"

## Enforcement

| Token property | Checked by |
|---|---|
| Every ratio above | `tools/check_contrast.py`, recomputing from the stylesheet's own token values |
| No Devanagari codepoint in any font | `tools/check_font_scope.py`, reading each `woff2` `cmap` (the existing guard **skips** `.woff2`) |
| Family and weight match the declaration | `tools/check_font_scope.py` |
| A licence sits beside each font | `tools/check_font_scope.py` |
| Every `url()` is relative and its target exists | `test_the_stylesheet_fetches_nothing`, narrowed per FR-112 |
| No off-host reference anywhere in `web/` | `test_no_page_file_names_another_host`, unchanged |
| Only weights 400 and 600 are used | a stylesheet assertion |
| `--house` never a background field | a stylesheet assertion (FR-106) |
