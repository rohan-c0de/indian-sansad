# Fonts: where these files came from

**Acquired**: 2026-10-13 · **Feature**: `002-presentation-and-visualisation`, T102–T104

Three self-hosted faces, **60,684 bytes total**, served same-origin from this
directory. Nothing on this page requests a font — or anything else — from
another host.

## The files

| File | Bytes | Family (internal `name` table) | `usWeightClass` | Glyphs | cmap |
|---|---|---|---|---|---|
| `newsreader-600.woff2` | 23,888 | `Newsreader 16pt 16pt SemiBold` | 600 | 262 | 224 codepoints, U+0020–U+2215 |
| `ibm-plex-sans-400.woff2` | 17,604 | `IBM Plex Sans` | 400 | 270 | 232 codepoints, U+0020–U+FFFD |
| `ibm-plex-sans-600.woff2` | 19,192 | `IBM Plex Sans SemiBold` | 600 | 270 | 232 codepoints, U+0020–U+FFFD |

All three are **static instances**, not variable fonts (`fvar` absent). That is
deliberate — see *Why static* below.

The internal family names are not the names the stylesheet declares. A
`@font-face` `font-family` is an author-chosen label, and the stylesheet calls
these `"Newsreader"` and `"IBM Plex Sans"` at weights 400 and 600.
`tools/check_font_scope.py` therefore asserts the internal name *contains* the
expected family and that `usWeightClass` matches the declared weight, rather
than demanding a literal match it would never get.

`Newsreader 16pt 16pt SemiBold` is Google's name for the **16pt optical size**
instance. The doubled "16pt" is theirs, not a transcription error here.

## Source

Downloaded from `fonts.gstatic.com` via the Google Fonts `css2` API, taking the
`/* latin */` block of each response. **Redistributed exactly as Google
publishes them** — not re-subset, not re-compressed, not renamed internally.

| File | `css2` query | URL |
|---|---|---|
| `newsreader-600.woff2` | `family=Newsreader:wght@600&display=swap` | `https://fonts.gstatic.com/s/newsreader/v26/cY9qfjOCX1hbuyalUrK49dLac06G1ZGsZBtoBCzBDXXD9JVF438wpojwC-ZFHDWwgUii.woff2` |
| `ibm-plex-sans-400.woff2` | `family=IBM+Plex+Sans:wght@400&display=swap` | `https://fonts.gstatic.com/s/ibmplexsans/v23/zYXGKVElMYYaJe8bpLHnCwDKr932-G7dytD-Dmu1swZSAXcomDVmadSD6llDB6g4tIOm6_De.woff2` |
| `ibm-plex-sans-600.woff2` | `family=IBM+Plex+Sans:wght@600&display=swap` | `https://fonts.gstatic.com/s/ibmplexsans/v23/zYXGKVElMYYaJe8bpLHnCwDKr932-G7dytD-Dmu1swZSAXcomDVmadSDNF5DB6g4tIOm6_De.woff2` |

These URLs are versioned (`v26`, `v23`) and content-addressed; Google may stop
serving them. The committed files are the artefact, not the URLs.

## Licence

Both families are **SIL Open Font License 1.1**, and the licence text ships
beside the fonts:

- `OFL-Newsreader.txt` — *Copyright 2020 The Newsreader Project Authors*
- `OFL-IBMPlexSans.txt` — *Copyright © 2017 IBM Corp. with Reserved Font Name "Plex"*

OFL 1.1 permits bundling and redistribution provided the licence travels with
the font, which is why both files are committed rather than linked.

IBM Plex carries the Reserved Font Name "Plex". That clause constrains naming a
**Modified Version** — it is not engaged here, because these files are
redistributed as Google publishes them, with their internal names untouched.

## Why static instances, not variable fonts

The obvious choice — one variable font per family — **does not fit the byte
budget**. Measured on `fonts.gstatic.com`:

```
Newsreader:wght@400..700  (variable, latin)   58,152 B
IBM+Plex+Sans:wght@400..600 (variable, latin) 40,240 B
                                      total   98,392 B   <-- over the 95,000 B ceiling
```

Narrowing the axis does not help: `wght@400..600` and `wght@400..500` both
return the **identical** 58,152-byte file, because the whole axis ships
regardless of the range requested. Pinning a single weight makes Google serve a
static instance instead, and three of those total 60,684 B — 36% under the
ceiling, with room for a fourth face if one is ever needed.

## Weights, and no italic

The stylesheet uses **400 and 600 only**, which is exactly what ships. Any other
weight would be synthesised by the browser, which on a serif heading reads as a
defect.

**No italic face ships.** The page's only italic uses marked absence — "not
stated", a missing subject, an unidentified asker — each of which is already
carried by a word, so the italic was a third redundant cue. Absence is now
carried by the word plus `--ink-soft`. Synthetic oblique is not used. If italic
is ever genuinely needed, IBM Plex Sans italic 400 is about 18,000 B and fits
inside the budget as a fourth file.

## Script scope: zero Devanagari

**Verified by reading each font's `cmap`**, not inferred from the subset's name:

```
ibm-plex-sans-400.woff2   Devanagari U+0900-U+097F: 0 codepoints
ibm-plex-sans-600.woff2   Devanagari U+0900-U+097F: 0 codepoints
newsreader-600.woff2      Devanagari U+0900-U+097F: 0 codepoints
```

This matters because **no pre-existing check in this repository can see inside a
font**: `.woff2` is a member of `UNSCANNABLE_SUFFIXES` in
`tools/guard_no_raw_payloads.py`, so `make guard` and `make audit-fields` skip
these files entirely, and the 64 KB payload ceiling does not apply to them
either. `tools/check_font_scope.py` is the only thing that reads them, and
Constitution Principle IV is why it exists.

## Three dataset codepoints fall back to a system face

Recorded because it was found by measurement and contradicts a claim made
earlier in planning. `research.md` R3 verified that all 13 distinct non-ASCII
codepoints in the published dataset fall inside the `latin` subset's declared
`unicode-range`. They do — but the **declared range is wider than the actual
`cmap`**, and three of the 13 are in no font here:

| Codepoint | Occurrences in the dataset | In any shipped font? | What a reader sees |
|---|---|---|---|
| U+2011 NON-BREAKING HYPHEN | 51 | no | a hyphen, from the fallback stack |
| U+202F NARROW NO-BREAK SPACE | 14 | no | a space; invisible either way |
| U+2060 WORD JOINER | 5 | no | zero-width; invisible by definition |

70 occurrences in 95,268 questions. When a codepoint is inside `unicode-range`
but absent from the font, the browser selects the face, finds no glyph, and
continues down the stack for that one character — so these render from a system
font. Two of the three are invisible. The third is 51 hyphens in a subject line
set at a slightly different face.

This is accepted rather than fixed. The alternatives were rejected:
rewriting those codepoints at render time would change what the page shows
relative to what the record says, against this project's rule that a source
form is preserved exactly as written; and a wider subset would cost bytes for
two invisible characters and one hyphen.

**The earlier claim that "no character in the record falls back to a system face
mid-word" is wrong, and is corrected here and in `research.md` R3.**
`tools/check_font_scope.py` asserts this list rather than leaving it to be
re-discovered: a *new* dataset codepoint missing from the fonts is a finding,
while these three are a recorded exception.
