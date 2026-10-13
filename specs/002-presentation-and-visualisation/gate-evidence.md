# Gate Evidence — Feature 002, Presentation and Visualisation

**Executed**: 2026-10-13 · **Tasks**: T181, T182, T183, T186, T189

The constitution's five Compliance Gates, re-run against this feature. A gate
is passed by evidence — an executed check and its output — not by assertion.

| Gate | Principle | Verdict |
|---|---|---|
| **Cost** | I | **PASSED** |
| **Upkeep** | II | **PASSED** |
| **Sources** | III | **PASSED** |
| **Language** | IV | **PASSED** |
| **Member fields** | V | **PASSED** |

**Ordering**: the Language, Member-fields and untouched-dataset checks run
**before** the deploy, not after. The constitution says the Member-fields gate
must be re-run "against what will actually be published, not against what was
specified", *before publishing*, and Principle V's definition of "published"
covers "any interactive page". `/speckit-analyze` found this feature's task
list had them in the wrong order and it was corrected before any of them ran.

---

# Gate 1 — Cost (Principle I)

**What must be shown**: every component named, with the free tier it lands on
and the behaviour at that tier's limit. No paid service, trial, or promotional
credit anywhere.

## Verdict: PASSED

**No component was added.** The feature changes `web/`, three files under
`src/sansad/`, and the checks. It introduces no host, no service and no store.

| Component | Free tier | At the limit |
|---|---|---|
| Static hosting | GitHub Pages, already in use | 1 GiB per site. The last measured build sat at **26% of it**, and 60,684 B of fonts does not move that. |
| The three fonts | self-hosted from `web/fonts/`, **same origin** | No third-party font service is contacted, so there is no tier to exceed. |
| Routing | hash-based, **no server** | A path-routed view would 404 on a static host and need redirect configuration the free tier does not offer. The hash never reaches the server. |
| `fonttools[woff]` | PyPI, free, **dev extra only** | Never installed in the serving path. Runtime dependencies remain exactly two: `httpx` and `polars`. |

```
$ python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print(d['project']['dependencies'])"
['httpx>=0.28,<1.0', 'polars>=1.17,<2.0']
```

No trial, no promotional credit, nothing that becomes chargeable later.

---

# Gate 2 — Upkeep (Principle II)

**What must be shown**: the recurring manual work this change adds, in hours
per week, and the project total after it. Automated detection and processing of
new material. Quiet degradation for visitors plus a signal to the maintainer.

## Verdict: PASSED

## Recurring manual work added: 0 hours per week

| Change | Recurring cost |
|---|---|
| The page, the router, the five charts | **0** — static files; no scheduled step |
| The three fonts | **0** — acquired once, committed, byte-verified by `make check-fonts` |
| The two newly wired signals | **0** — raised by the existing refresh, no new job |
| The four new checks | **0** — run inside `make validate`, which already ran |

**Project total after this feature: unchanged.** The one-off work — acquiring
the fonts, splitting `app.js`, writing the checks — is build work, not upkeep.

## The rate signal is designed NOT to fire, and that is the Upkeep argument

This is the part of the gate this feature could most easily have failed. The
automatic resolution rate is **0.947831** against an `sc_002_target` of
**0.95**, both published, with `sc_002_met_on_automatic_rate: false`.

Wiring `resolution_rate_below_target` to its **threshold** would have raised a
signal on **every single run, forever**, for a state the owner has already
accepted and published. That is not a notification; it is a standing chore, and
chasing it daily is precisely the routine manual work this principle forbids.

So the trigger is a **drop against the previous publication**. Verified:

```
unchanged at 94.78%     -> None          (nothing raised)
risen                   -> None
no previous publication -> None          ("no comparison made" logged)
automatic dropped       -> NOTICE   94.78% -> 93.42%
published dropped       -> DEGRADED 96.36% -> 95.52%
```

## Quiet degradation for visitors, signal to the maintainer

Unchanged by this feature, and extended by it:

- A view whose module or data fails to load shows a **worded** message inside
  that view and leaves the shell and every other view working. The failure
  renderer was fixed during Phase 4 so it no longer destroys the view's own
  heading — measured: a failed module left `view-search` with no heading, and
  the router's focus move then landed on `<body>`.
- All four FR-011 signals now have a production caller, where two had none:

```
ingestion_failure             cli.py, ingest/questions.py
upstream_shape_change         ingest/shape.py
resolution_rate_below_target  cli.py            <- newly wired
resolved_transitions_out      cli.py            <- newly wired
```

- An absent previous publication records **"NO COMPARISON MADE"**, naming which
  comparisons were skipped and why. Not a pass, not a signal — a valid first run
  and a broken comparison stay distinguishable (FR-136).

---

# Gate 3 — Sources (Principle III)

**What must be shown**: every input identified as an already-structured source.
No document file opened, parsed, or depended on.

## Verdict: PASSED

**No ingest was added and no document was opened.** This feature reads only
files `data/published/` already carries, and adds one request to the page:
`aggregates/composition.jsonl`, published by feature 001 and fetched by nothing
until now.

The three `woff2` files are **font binaries, not document files**, and nothing
is extracted *from* them: `tools/check_font_scope.py` reads a `cmap` to prove a
negative — that no Devanagari codepoint is present. That is the opposite of
depending on a document's contents.

---

# Gate 4 — Language (Principle IV)

**What must be shown**: all ingested and published material is English. No
translation or transliteration path introduced.

## Verdict: PASSED

## Executed: the codepoint scan, over the whole repository

```
text files scanned                : 2,020
binary files (not text-scannable) :    75
lines with a Devanagari codepoint :     0
lines with any non-ASCII codepoint:  8,325
distinct non-ASCII codepoints     :    48
DEVANAGARI FOUND                  :     0
```

## Executed: inside the three font binaries, which no text scan can read

**Feature 001's Language evidence cannot be inherited here**, because these
files did not exist then — and no pre-existing check can see into one.
`.woff2` is a member of `UNSCANNABLE_SUFFIXES` in
`tools/guard_no_raw_payloads.py`, so `make guard` and `make audit-fields` skip
font files; the 64 KB payload ceiling does not apply because `PAYLOAD_SUFFIXES`
holds only data formats; and the text scans in
`tests/unit/test_page_fetch_layer.py` raise `UnicodeDecodeError` on a
compressed binary.

```
$ make check-fonts
  ibm-plex-sans-400.woff2   Devanagari U+0900-U+097F: none
  ibm-plex-sans-600.woff2   Devanagari U+0900-U+097F: none
  newsreader-600.woff2      Devanagari U+0900-U+097F: none
  total: 60,684 B across 3 file(s)
check-fonts: PASS
```

Read from each font's `cmap`, not inferred from the subset's name.

## Executed: no translation or transliteration path

```
$ grep -riEl "translat|transliterat|indic-nlp|bhashini|googletrans|deep-translator|unidecode" \
    src/ tools/ web/ tests/ pyproject.toml
src/sansad/resolve/normalise.py
src/sansad/publish/formats.py
tools/cdp.mjs
web/style.css
```

**Four hits, none of them a translation path**, read rather than counted:

| File | What it is |
|---|---|
| `resolve/normalise.py` | prose: *"This is not transliteration (Principle IV). No script conversion…"* |
| `publish/formats.py` | prose: *"Principle IV: no transliteration"* |
| `tools/cdp.mjs` | a Chrome flag `--disable-features=…,Translate,…` — it **turns translation off** |
| `web/style.css` | `transform: translateY(0.12em)` — the starred asterisk's baseline nudge |

The last two are new since feature 001's scan and are named here so nobody
re-derives them. Two are prose forbidding the thing; one disables it in the
browser; one is a CSS transform that merely matches the substring.

## The Latin subset is sufficient, and three codepoints are not

All 13 distinct non-ASCII codepoints in the published dataset fall inside the
`latin` subset's declared `unicode-range`. But the declared range is **wider
than the fonts' actual `cmap`**, and three of the 13 are in none of them:

| Codepoint | Occurrences | What a reader sees |
|---|---|---|
| U+2011 NON-BREAKING HYPHEN | 51 | a hyphen, from the fallback stack |
| U+202F NARROW NO-BREAK SPACE | 14 | a space; invisible either way |
| U+2060 WORD JOINER | 5 | zero-width; invisible by definition |

70 occurrences in 95,268 questions. Accepted rather than fixed — rewriting them
at render time would change what the page shows relative to what the record
says. `tools/check_font_scope.py` asserts this exact list, so a **new** dataset
codepoint missing from the fonts is a finding while these three are a recorded
exception.

---

# Gate 5 — Member fields (Principle V)

**What must be shown**: the published field list diffed against the FR-008 set.
Dataset files, pages, derived statistics and repository fixtures all checked.

## Verdict: PASSED

## Executed: the field diff, now a TOOL rather than an afternoon

Feature 001 produced this census **once, by hand**. The constitution requires it
re-run before each publication, and a census nobody can re-run is a census that
was true on one afternoon. `tools/check_field_scope.py` is that census as a
command.

```
$ make check-field-scope
  FR-008 (11): canonical_name, constituency, house, last_refreshed, member_id,
               name_variants, party, sitting_status, source_record_ref, state, terms
  declared spellings (1): member_name -> canonical_name
  ...
  Resolved through a DECLARED SPELLING, which is the defect this closes:
    reference: representations.member_name -> canonical_name

check-field-scope: PASS -- 9 published set(s), 205 distinct field name(s);
no published key names an attribute Principle V excludes
```

## The feature 001 defect, closed

`representations.member_name` **is** a member name form and
`contracts/published-dataset.md` declares it as one — but the spelling is not
what `PUBLISHED_FIELDS` carries, so the original diff reported a genuine FR-008
field as "not a member attribute" and its membership rested on a human reading
the contract.

`gate-evidence.md` named two remedies. **Renaming the published key is not
available**: FR-140 forbids changing `data/published/`, and the key is pinned
by `tests/contract/test_constituency_reference.py`. So the synonym is the one
that remains, and it is now resolved mechanically.

**It widens no field set.** Every entry in `PUBLISHED_FIELD_SYNONYMS` must map
onto a field already in `PUBLISHED_FIELDS`, which
`tests/unit/test_field_scope_synonyms.py` asserts, so it cannot become a back
door. Adding a genuinely new attribute still means editing the tuple, which is
a decision about what this project publishes about 5,426 named people.

## The one newly reachable set

`aggregates/composition.jsonl` is the only file this feature adds to the page's
request surface.

```
fields: basis_version, category, counting_basis_unit, dimension, members,
        term, total_members
carries a member id?  False
carries a name form?  False
```

`party` and `state` appear as **category values**, not as attributes of a named
person. No member id and no name form.

## The page's surface NARROWED

FR-151 takes `ministry-profile.jsonl` and `ministries.jsonl` off the first load
and defers every view's data to first use. A visitor who reads only the coverage
statement now reaches **four files**, where before they reached six.

```
$ make audit-fields
audit-fields: PASS -- all 3 scope(s) audited, no prohibited attribute, no oversized payload

$ make guard
guard: PASS -- 2,019 file(s) scanned; no prohibited attribute, no payload over 65536 bytes
```

## `data/published/` is byte-identical

```
$ git status --porcelain data/published/
(empty)

$ git diff --stat 27399b3 -- data/published/
(no change)
```

Not a file, not a field, not a figure, not a counting basis (FR-140, SC-024).

---

# What a green run does NOT establish (T189)

Recorded because the moment this claim is most likely to be made is immediately
after a green run.

| Claim | Status | What would settle it |
|---|---|---|
| **SC-001/003/004 — the live wire figures** | See the T184 section below | Response headers from the live deployment |
| **The three fonts total 60,684 B as served by this site** | **UNVERIFIED** | `woff2` is pre-compressed and GitHub Pages will not re-encode it, so the figure should carry across — but 60,684 B is a `fonts.gstatic.com` `content-length`, not a measurement of this site |
| **SC-025 — zero running cost** | **UNVERIFIED, and unverifiable here** | Observable only in operation. A billing period with no charge |
| **SC-012 — no off-host request** | **VERIFIED locally only** | A local run proves the page made none *in that run*; a reference reachable only on an unexercised path would not appear. The static off-host assertions over all of `web/` cover the rest |
| **SC-011's screenshots** | **captured, not judged** | 68 images prove a layout rendered. Whether it reads well is a person's call |
| **FR-009 / SC-003 (feature 001) — the unattended refresh** | **UNVERIFIED**, carried from feature 001 | A scheduled run firing without a human. Still never observed |
| **The 2026-10-10 baseline wire figures** | **UNVERIFIED** — the owner's measurements, taken as given | They were not re-measured here. The offline `gzip -6` sum agreeing to within 1,180 B is corroboration, not confirmation |

## Resolved since the spec was written

| Was UNVERIFIED | Now |
|---|---|
| Whether two variable Latin romans fit 95,000 B | **They do not** — 98,392 B. Three static instances at 60,684 B replaced them |
| Whether `prefers-reduced-motion` is reachable through the driver | **It is.** SC-010 is a genuine browser check, not the fallback stylesheet assertion |
| The 2,800 px result-list ceiling | **Met at every width** — 2,672 px at 390 px, from a measured 9,720 px |
