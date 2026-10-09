# Phase 0 Research: Resolved Metadata Layer

**Feature**: `specs/001-resolved-metadata-layer` | **Date**: 2026-10-09

**Scope note**: this file resolves the **Technical Context** unknowns for the implementation plan. It is distinct from `.specify/assessments/indian-sansad/research.md`, which is the assessment-stage evidence file (306 lines, two passes) and remains the source for every domain claim cited below. The spec's nine **Open Questions Carried Forward** are *not* all resolved here; which ones moved is stated at the end.

## Upstream Access Findings (new, 2026-10-09)

Probing was limited to the already-approved `sansad.in` host and stopped after the pattern was clear.

### Decision: route discovery from the API itself is not possible

- **Finding**: service base paths return a HAL-style index that exposes **only operational endpoints**, not data routes. `GET /api_ls/question` returned verbatim `{"_links":{"self":{"href":"http://sansad.in/api_ls/question","templated":false},"health":{...},"health-path":{...},"metrics-requiredMetricName":{...},"metrics":{...}}}` — self, health, health-path, metrics. The same shape was seen at `/api_ls/debate` in the assessment's second pass.
- **Finding**: there is no umbrella index. `GET /api_ls` → **404**; `GET /api_rs` → **404**.
- **Decision**: data sub-paths must be learned by capturing the requests the site's own pages make in a browser, not by querying the API. This is the method the assessment records a third party as having used ("found in the Next.js client bundle").
- **Alternatives considered**: path guessing — attempted and abandoned; it produced 404s with no signal. Reading the site's client bundle — viable, and the same browser-capture work, so not a separate option.

### Decision: the Rajya Sabha member route is narrowed, not resolved

- **Finding**: `GET /api_rs/member` → **404** (confirming the assessment). `GET /api_rs/question` → **404**. But `GET /api_rs/members` (plural) → **HTTP 403 Forbidden**.
- **Reading**: a 403 where every sibling path returns 404 is consistent with the route existing and being access-controlled or request-filtered, rather than being absent. **The cause is UNVERIFIED** — a bot/WAF rule, a path-specific block, or genuine authorisation are all consistent with what was observed, and no further probing was done.
- **Decision**: treat Rajya Sabha member data as **not yet obtainable**, and plan for Lok Sabha-first delivery with Rajya Sabha as a documented follow-on. This does **not** mean it is unobtainable — it means the plan must not depend on it.
- **Consequence for the spec**: FR-001's Rajya Sabha half remains at risk, and the owner's Rajya Sabha scope decision cannot be honoured until this is settled. Settling it needs browser network capture against the Rajya Sabha member pages.

### Confirmed, unchanged from the assessment

- `GET /api_ls/member` returns the full Lok Sabha roster unauthenticated, `"totalElements":5426`, with `createdAt`/`updatedAt` timestamps — the only data route verified end-to-end anywhere in this project.
- Record-listing HTML pages render no content outside a browser, so nothing can be scraped from markup.
- Cross-origin browser requests to the upstream are not permitted. This rules out a browser reading the **upstream** directly; it does not rule out a browser reading **this feature's own published files from its own host** — see the client-side decision below.
- There is no sitemap (`/sitemap.xml` → 404), and the API carries no contract, versioning or deprecation notice.

## Technical Context Decisions

### Language: Python 3.13

- **Rationale**: the work is record reconciliation and tabular aggregation; Python has the strongest standard and third-party support for approximate string matching and tabular output, and the maintainer-facing cost of a correction is low. It is also the default runtime on every free CI provider, which matters under the zero-cost constraint.
- **Alternatives considered**: TypeScript/Node — equally viable for fetching and JSON shaping, weaker for the fuzzy-matching core that `spec.md` FR-002 makes load-bearing. Go — good single-binary ergonomics, least convenient for exploratory reconciliation work by one maintainer at ~2h/week.

### Project type: scheduled pipeline producing a static published dataset

- **Rationale**: this satisfies three spec constraints at once — no running server to pay for (FR-014), autonomous refresh on a schedule (FR-009), and a published artefact a third party can take directly (FR-006). The assessment cites existing projects in this exact space running on free CI plus free static hosting, which is corroboration that the shape works rather than a design borrowed on faith.
- **Alternatives considered**: a live API over a hosted database — better for arbitrary queries, but introduces a paid or sleep-prone service and a server to maintain, breaching FR-014 and the upkeep ceiling. A browser-only app reading upstream directly — ruled out: the upstream does not permit cross-origin requests.

### Storage: version-controlled files, no database

- **Rationale**: scale makes this safe. Members are ~5,426 records; question metadata across the covered period is on the order of 10^5 records (the assessment cites 34,720 for one term and ~243K–280K held by other projects). **This is three to four orders of magnitude smaller in bytes than the ~1,000,000-page document corpus that demoted the other options** — which is precisely why the zero-cost constraint is plausible for this feature and was not for them. ~~Files also give FR-005 provenance and FR-016 refresh dating for free, since history is inherent.~~ **Corrected 2026-10-09 — this no longer holds.** The owner decided the dataset is published to a rolling orphan branch as a single force-pushed commit (see `spike/size-budget.md`), because at the measured 216.5 MiB per snapshot full history breaches GitHub's repository-size guidance on about the fifth refresh. That destroys the history this rationale relied on, so **FR-005 is met by the Resolution Records (T049) and FR-016 by an explicit rebuilt-date field on every published set (T093)** — explicit mechanisms rather than a free side-effect of version control. The file-based storage decision itself stands; only this one claimed benefit of it is withdrawn.
- **Alternatives considered**: a managed database — unnecessary at this scale and a recurring-cost risk. An embedded database file — defensible, but a database file is less directly consumable by a third party than plain tabular files, working against FR-006.

### Published formats and partitions: newline-delimited JSON plus CSV, partitioned to cover every axis FR-007 names

- **Rationale**: FR-006 wants third-party re-use without re-derivation and FR-007 wants subsets without taking the whole record. Partitioned files satisfy the subset requirement without any query service. Two formats because the two evidenced audiences differ — the practitioner account in the assessment describes CSV-shaped work, while a programmatic consumer is better served by JSON.
- **Correction to an earlier gap in this plan**: FR-007 names **five** subset axes — session, ministry, member, state and constituency — and partitioning by House and session alone covers one of them. Partitioning by House and session was therefore not sufficient, and the published partitions are:
  - **House** — every published set is House-scoped.
  - **House + session** — the primary question partition.
  - **Per-ministry** — one question file per ministry across the covered window.
  - **Per-member** — one question file per `member_id`. A co-asked question appears in each asker's file.
  - **State and constituency** — **not** separate question partitions. They are resolved through the member reference set: read the member set, filter to the state or constituency, then take those members' per-member files. Two fetches, no whole-record download.
- **Why state and constituency are a join rather than a partition**: both are attributes of a member, not of a question, so a per-state or per-constituency question partition would republish the per-member files under a key the member set already supplies. At ~543 constituencies across two terms that is a large duplication for no information a consumer cannot get in one extra fetch.
- **Alternatives considered**: a single bulk file — fails FR-007 on every axis. A columnar format only — efficient, but adds a dependency for the CSV-shaped consumer the demand evidence actually describes. Per-state and per-constituency question partitions — rejected as duplication, per the point above. Leaving ministry and member to consumer-side filtering of the session partitions — rejected: it makes every consumer take the whole record to answer a per-ministry or per-member question, which is the re-derivation cost FR-007 exists to remove.

### Added storage from the new partitions is MEASURED — 216.5 MiB, duplication 3.725×

- The per-ministry and per-member partitions **republish the same question records under additional keys**. One question appears in its House/session partition, in one per-ministry file, and in one per-member file per asker — so total published bytes are a multiple of the single-copy size.
- The multiplier depends on the **mean asker count per question**, which this project has never measured, and both publication formats apply it again.
- ~~**No measurement exists.** That the duplicated partitions stay inside a free static tier's storage is an **ASSUMPTION** at low confidence.~~ **MEASURED 2026-10-09** over the full 95,269-question window: **227,007,149 bytes (216.5 MiB)** across **1,750 files**, a duplication multiple of **3.725×** a single copy, at **2,382.8 bytes per question**. That is **21.1% of the 1 GiB GitHub Pages ceiling** — it fits with 4.7× headroom, so **no published axis needs dropping** and Principle I's reduce-or-drop remedy is not triggered. The mean asker count the multiplier depends on is also measured, at **1.645–1.711** across both terms. See [spike/size-budget.md](./spike/size-budget.md).
- **All three figures were measured with the containment tier OFF and no maintainer assertion applied**, so 8,917 of 95,269 questions carry an empty `asking_members` array. They are therefore a **FLOOR**: adopting the tier and seeding the four confirmed assertions resolves further questions, each of which then lands in a per-member file in both formats, and the by-member axis is 46% of all published bytes. Re-measure once Phase 3's matcher exists.
- **What binds instead is repository growth, not site size** — 216.5 MiB per snapshot breaches GitHub's 1 GB repository guidance on about the fifth refresh, which is why the owner decided on a rolling `published` branch (same file).

### Subject-search index size is MEASURED — 2.86 MiB

- Story 2's "has this subject been asked before" search runs in the visitor's browser (see the client-side decision below), so the index it searches has to be **a published file the page fetches** — there is no server to query.
- Its size depends on two things not yet settled: the tokenisation, and whether the index covers question subjects only or subjects plus ministry and member names.
- ~~**No measurement exists.** This is an **ASSUMPTION** at low confidence on the same footing as the two above.~~ **MEASURED 2026-10-09** over all 95,269 real subjects: **3,002,356 bytes (2.86 MiB)**, 16,979 distinct terms, 352,738 postings, **31.51 bytes per question**. The open choice this section names is settled by measurement too — **subjects only is chosen**; subjects plus ministry and member names was also measured at 4,860,719 bytes (4.64 MiB), **+58.6%**, and is recorded as measured-but-not-adopted. Tokenisation is deliberately unaggressive (lowercase, split on non-alphanumeric, minimum 3 characters, 36 stopwords, **no stemming**, delta-encoded postings). See [spike/size-budget.md](./spike/size-budget.md).
- **Fetch it lazily.** At 2.86 MiB the index is 83% of its view's total page weight; loading it eagerly cuts sustainable reach from ~166,000 to ~27,750 visitors a month.

### Decision: the reader views (User Stories 2 and 3) are client-side only

- **Decision**: Stories 2 and 3 are delivered as a static page in `web/` that runs entirely in the visitor's browser over the published dataset files, served from the same static host as those files.
- **Rationale** — three reasons, each independently sufficient to exclude a server:
  - **No server.** The views need filtering, counting and subject search. Done in the browser, none of that needs an always-on process, which is the only thing a server would have contributed.
  - **Zero running cost.** The page is static files on the free static host that already serves the dataset (FR-014). It adds no component, so there is no second free tier to stay inside and no second thing that can start charging.
  - **Same-origin files, so the upstream's cross-origin block does not apply.** The page fetches only this feature's own published files from its own host and never calls the upstream. The restriction that rules out a browser-only app reading the upstream directly is a fact about the upstream's responses; it is simply not engaged here.
- **Consequence, accepted deliberately**: the page is a second consumer of the published dataset on precisely the terms a third party gets (FR-006, FR-007) — no private route, no view the published files cannot reproduce. If the page needs something the files do not carry, the files are wrong.
- **Alternatives considered**:
  - **A server-side search service** — better for arbitrary free-text search over question subjects, and the obvious way to avoid shipping any index to the browser. **Rejected**: it reintroduces an always-on process, which is either a paid tier or a sleep-prone free one, breaching FR-014; and it becomes a second system to keep running against the ~2h/week ceiling.
  - **A hosted database with a query API** — best for ad-hoc queries the partitions do not anticipate. **Rejected** on the same recurring-cost ground, and separately against FR-006: a consumer would have to query a service instead of taking files, which is the re-derivation cost this feature exists to remove.

### Page load size is MEASURED — 587 KiB median, 2.50 MiB worst case

- What a visitor actually downloads depends on two things not yet built: **how finely the dataset is partitioned per session**, and **which aggregates are precomputed at publish time** rather than computed in the browser.
- At ~10^5 question records, fetching the whole dataset into a page is not viable. Per-session partitions plus precomputed aggregates are what keep that from happening — so the design depends on both, not on one as a nicety.
- ~~**No size has been measured.** The claim that the reader views fit inside a free static tier's bandwidth, and load acceptably for a visitor, is an **ASSUMPTION** at low confidence.~~ **MEASURED 2026-10-09** from the real window publish: **587 KiB** for a median ministry profile, **401 KiB** for a median constituency view, **2.50 MiB** for the largest ministry, **3.44 MiB** with the subject index loaded — allowing roughly **166,000 median visitors a month** inside the 100 GB soft bandwidth, and 441 whole-dataset downloads. The views fit. See [spike/size-budget.md](./spike/size-budget.md).
- **Budget against the largest partition, not the median.** Ministry files span **350 B to 2,564,507 B** — a 4.4× spread between median and largest — so a visitor's first load depends on which ministry they open.
- **Two inputs remain unobserved rather than unmeasured**: the page shell is a 60 KiB estimate because `web/` does not exist, and every figure is **uncompressed** because the gzip/brotli ratio was not measured. **All three figures were measured with the containment tier OFF and no maintainer assertion applied**, so 8,917 of 95,269 questions carry an empty `asking_members` array. They are therefore a **FLOOR**: adopting the tier and seeding the four confirmed assertions resolves further questions, each of which then lands in a per-member file in both formats, and the by-member axis is 46% of all published bytes. Re-measure once Phase 3's matcher exists.

### Testing: pytest, with reconciliation fixtures drawn from real recorded name variants

- **Rationale**: FR-002 and FR-004 are the requirements most likely to fail silently, and silent misattribution to a named MP is the risk the assessment flags as reputational. Fixtures must include the real variant pair the assessment records ("Shri Sunil Kumar Singh" / "Singh, Sunil K."), co-asked questions, and a deliberately unresolvable name.
- **Alternatives considered**: unittest — equivalent; pytest chosen for fixture ergonomics.

### Target platform: free-tier CI runner on a schedule; static hosting for output

- **Rationale**: no always-on compute, which is what keeps cost at zero.
- **Constraint accepted**: a scheduled runner is the single point of failure for FR-009, and runner time limits bound the refresh. Both are sized comfortably at 10^5 records.

### Performance and scale targets

- **Not latency-driven.** The meaningful target is that a full refresh completes inside one scheduled run, and an incremental refresh completes well inside it.
- **Scale**: ~5,426 member records; ~10^5 question records; ~428 Lok Sabha sitting days in the covered window (274 cited for the 17th, ~154 estimated for the 18th).
- **Constraints**: zero running cost; ~2h/week maintainer attention; no document files opened at any point (FR-015).

## Resolution of Spec Open Questions

**Moved by this phase (1 of 9):**

- Carried question 1 (Rajya Sabha member route) — **narrowed, not closed.** `api_rs/members` returns 403 where siblings return 404. The plan now treats Lok Sabha as the deliverable scope and Rajya Sabha as a follow-on, so the question no longer blocks planning, but it still limits delivered scope.

**Answered method, not substance (1 of 9):**

- Carried question 2 (the question-metadata route was never fetched directly) — **still unfetched**, but this phase establishes *how* to get it: browser network capture against the site's own question pages, because the API's own index exposes no data routes. That is now a concrete task rather than an open search.

**Unchanged (7 of 9):**

- 3 (whether identity resolution is tractable at ~2h/week without ground truth) — the plan's highest-risk assumption; `/speckit-tasks` should sequence a resolution-quality measurement early rather than late.
- 4 (which member attributes are published) — remains a required explicit decision under FR-008 and SC-010.
- 5 (whether other builders would consume this) — only answerable by publishing.
- 6 (what the official Digital Sansad application offers) — unresolved after two assessment passes; not resolvable by fetching.
- 7 (national open-data portal holdings) — still refuses automated access.
- 8 (the target level for SC-009) — owner decision, unstated.
- 9 (verifying the one newsroom analysis) — needs a host outside the approved set.
