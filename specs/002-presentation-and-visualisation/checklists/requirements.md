# Specification Quality Checklist: Presentation and Visualisation for the Published Lok Sabha Question Record

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-10
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Constitution Compliance Gates

Checked at specification, per the constitution's "At specification" rule: a requirement that cannot pass a gate must be changed or removed before the spec is accepted.

- [x] **Cost (Principle I)** — FR-143 and SC-025. No component added. The fonts are self-hosted on the same GitHub Pages free tier already in use; the build sat at 26% of the 1 GiB Pages ceiling on 2026-10-10 and ~95 KB of fonts does not move that materially. Hash routing is chosen over path routing specifically so no redirect configuration or server is needed.
- [x] **Upkeep (Principle II)** — FR-139 keeps visitor-facing degradation quiet while FR-134 to FR-137 close the maintainer half of FR-011. Adds no recurring manual work; FR-135's trigger is designed so the signal does **not** fire on every run, which would itself have created upkeep.
- [x] **Sources (Principle III)** — no document is opened. This feature adds no ingest and reads only files already published.
- [x] **Language (Principle IV)** — FR-111, FR-144 and SC-013. The Latin-only font subset is required by this gate, and SC-013 re-runs the codepoint scan over the font binaries.
- [x] **Member fields (Principle V)** — FR-125 and SC-023 bound every new visualisation to the FR-008 set. FR-138 and SC-022 strengthen the automated check that enforces it.

## Structural checks (executed)

```
NEEDS CLARIFICATION markers : 0
FR definitions              : 53, FR-101..FR-153, no duplicates, no gaps
SC definitions              : 25, SC-001..SC-025, no duplicates
FR cited but undefined      : FR-008, FR-010, FR-011 (feature 001's, declared in Scope and Numbering)
SC cited but undefined      : none
User stories                : 8, priorities P1 x3, P2 x3, P3 x2
Story-to-FR subsection map  : 1->1, 2->2, 3->3, 4/5/6->4,5,6, 7->7, 8->8  (consistent)
```

## Notes

### Validation iteration 1 — 2026-10-10

Two [NEEDS CLARIFICATION] markers, both scope questions, both put to the owner and both answered:

1. **Page structure** → *switchable in-page views*. One HTML page, sections switched by hash links, exactly one view rendered at a time. Encoded as FR-146 to FR-153 and User Story 3 (P1).
2. **"Question load over twenty-one sessions"** → *both series*. The whole-House per-session total and the matched-subject trend from the search index. Encoded as FR-116 and FR-145.

### Validation iteration 2 — 2026-10-10

All items pass. Four things were resolved by measurement during drafting rather than deferred to implementation:

- **The palette's contrast was computed, not assumed.** All eight text pairs clear 4.5:1. Two findings the spec now states as requirements rather than leaving to be discovered: `--paper` vs `--sheet` is **1.13:1** (FR-108) and `--house` vs `--mark` is **1.03:1** (FR-109).
- **The byte budget was re-derived after the structure answer, and it is better than the brief assumed.** The brief estimated fonts would roughly double the 88,961 B first load. Measured, FR-151 defers **38,819 B** — 44% of the first load — off the landing view without splitting `app.js` at all, so the fonts land on ~52,000 B rather than on 88,961 B. SC-001 is therefore 160,000 B and **1.80×**, not ~190,000 B and 2.14×, and SC-003 requires the non-font first load to *fall* rather than hold. This supersedes the arithmetic in the first draft of this spec.
- **A 13 MB trap was closed.** `aggregates/subject-trends.jsonl` is 13,178,975 B. The spec forbids fetching it and records the confirmed zero-byte alternative: the search index's `prefixes[doc_prefix[position]]` yields session and starred/unstarred for every matched document.
- **The landing view's real data cost was read from the code**, not estimated: `boot()` fetches four files totalling 4,540 B at `gzip -6`, and `bootViews()` separately fetches the two ministry files that FR-151 now defers.

### Verification status of the claims this spec rests on

Per the working agreement's evidence discipline:

- **VERIFIED** — 21 sessions, 95,268 questions, period 2019-06-21 to 2026-08-12, automatic rate 0.947831 against `sc_002_target` 0.95, composition dimensions `party`/`state`/`terms_served` for terms 17 and 18, 545 seats, 36 states × 25 subject lines, and every term and session `start_date` reading "not stated" — all read from `data/published/`.
- **VERIFIED** — the per-module and per-file `gzip -6` figures in the spec's two budget tables, measured locally. Their sum over the 18 first-load files is 87,781 B against the 88,961 B observed on the wire, the difference being response headers.
- **VERIFIED** — the subject trend is derivable at zero cost. The term `under` resolves to 6,254 documents spread across all 21 sessions and 41 session/type buckets, decoded from the published index's gap-encoded postings by the same cumulative sum `web/lib/search.js::positionsFor` already performs.
- **VERIFIED BROKEN** — `resolved_transitions_out` and `resolution_rate_below_target` have no caller in `src/` or `tools/`; `grep` returns the definition module only. The other two signals do have callers (`cli.py`, `ingest/questions.py`, `ingest/shape.py`).
- **VERIFIED** — `representations.member_name` is published in `reference/constituencies.jsonl` and is absent from `sansad.model.member.PUBLISHED_FIELDS`, which carries `canonical_name` and `name_variants`.
- **VERIFIED** — `tests/unit/test_page_fetch_layer.py::test_the_stylesheet_fetches_nothing` asserts `"url(" not in body`, which self-hosted `@font-face` must break. FR-112 governs; the check is to be narrowed, not removed.
- **VERIFIED** — the skip link's `min-height: var(--tap)` at `web/style.css:185` cannot apply: the `<a>` is a non-replaced inline element with no `display` change, which is why it measures 25 px. The three footer links have no height rule at all.
- **VERIFIED** — exactly one view draws a chart today. `stackedColumns` has a single call site, `web/app.js:872`, inside `renderProfileResult`; the two-ministry comparison is text and a table only, and `composition.jsonl` is fetched by nothing in `web/`.
- **UNVERIFIED** — the 2026-10-10 live-deployment wire figures are the owner's measurements, taken as given. They were not re-measured here, and the repository's `README.md` still records Pages as unobserved. The offline `gzip -6` sum agreeing to within 1,180 B is corroboration, not independent confirmation.
- **UNVERIFIED** — that two variable Latin-subset romans fit inside 95,000 B. No font file was fetched. SC-002 is the constraint; measuring it is a planning task.
- **UNVERIFIED** — the 2,800 px result-list ceiling in SC-006. Derived from 25 rows at ~90 px plus ~400 px of summary, not measured against a built row.
