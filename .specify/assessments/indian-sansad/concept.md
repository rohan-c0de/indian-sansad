# Concept: Options for a self-sustaining use of the published parliamentary record

- **Slug**: indian-sansad
- **Created**: 2026-10-09 (supersedes the 2026-10-08 shaping; see the recommendation-stability note)
- **Recommended option**: Option A — Resolved metadata layer (builders first) — **reversing the previous recommendation of Option C**

## What the Second Research Pass Changed

Three findings from 2026-10-09 move the options. None of them is a scope decision; all three are evidence.

- **Demand now exists for exactly one audience, and it is the one the owner prioritised.** Two first-hand practitioner accounts: a developer who attempted this task documented "a staggering amount of data to scrape", name-spelling inconsistencies, and difficulty "Mapping the Asking Member to an actual Member of Parliament", and covered only **29 November – 23 December 2021** before stopping; a second project declined to scrape at all. Civic developers now rest on observed behaviour. Journalists and citizens still have no first-hand account after two passes. — [research.md: Second Research Pass, Blocker 3] (confidence: high for the accounts)
- **The volume blocker returned an unfavourable estimate.** ≈813 sitting-day debate documents across both Houses (274 cited sittings for the 17th LS + ~154 for the 18th, Rajya Sabha at ~0.9×), at the one sampled volume of 1,315 pages → **on the order of one million pages**, English alone. [ASSUMPTION — a cited sitting count times a single sampled page count; order of magnitude, not measurement] — [research.md: Second Research Pass, Blocker 1]
- **Option C's headline value shrank.** Only "24% of questions listed for oral response were answered by Ministers in the House in Lok Sabha" across the 17th LS, and starred questions are a minority of all questions. Oral answers are genuinely in the debate text — the owner saw one — but they cover a small slice of the answer record. — [research.md: Second Research Pass, incidental finding] (confidence: high, cited)

The net effect: **the case for serving builders got stronger on evidence, and the case for the debate-text option got weaker on both value and cost at once.**

## Owner Decisions In Force

Decisions, not proposals. [problem.md]

- **English only** (supersedes intake's "English and Hindi"); Hindi is a non-goal.
- **Audience follows the evidence** — civic developers and researchers first; citizens remain intent, not basis.
- **Criteria: novelty, personal interest, reach.** Durability and low upkeep explicitly *not* criteria; ~2h/week remains a limit.
- **Published under a project name.**
- **No personal-data guardrail adopted** — `research.md`'s risk notes stand, the risk is accepted rather than mitigated, and A8.6 carries it.
- **Agent-originated goals and metrics accepted in full**; the use threshold remains unstated.
- **Rajya Sabha in scope**, bounded by the Lok Sabha calendar window.

## Framing Notes

- **The owner has chosen no use.** None of these options is a selection.
- **Appetite**: the owner set an *upkeep* ceiling (~2h/week) and no build budget; build appetites below are **agent proposals**.
- **"One PDF per sitting day" is UNVERIFIED** and now doubtful — the owner reported rows at roughly 1,000+ pages each.
- **No OCR assumption.** One English volume has a text layer; other volumes, written answers and anything scanned are untested.
- **The A9 ideas carry no demand evidence**, and their speaker/section parsing dependency is **UNVERIFIED**.
- **No architecture, data model, API design or code appears here.**

## Candidates: Carried, Dropped, Excluded

Twenty-one recorded uses; every carried candidate is placed in an option.

| Disposition | Count | Candidates |
|---|---|---|
| Excluded by the owner | 1 | Capability Gaps #2 |
| Carried and placed | 12 | Option A: A8.1, A8.2, A8.5, A8.6, A8.8 · Option B: #3, A8.7 · Option C: #1 (partially), A9.5, A9.6 · Option D: A9.1, A9.3 |
| Dropped | 8 | #4, #5, #6, #7, A8.3, A8.4, A9.2, A9.4 |
| **Total** | **21** | |

Drop reasons are unchanged from the 2026-10-08 shaping. One is worth re-stating because the new evidence touches it: **A8.3** (bilingual digest) stays dropped — English-only removes its language problem but not its two live objections, unevidenced citizen demand and per-sitting-day LLM cost.

## Options

### Option A — Resolved metadata layer (builders first, readers second)

- **Sketch**: Take what is already structured — question metadata, the member roster, Rajya Sabha question text — and resolve the specific things that stopped other people: consistent member identity across spelling variants, questions reliably joined to the MP who asked them, and extracts that someone else can consume without re-deriving any of it. A builder gets the joined record; a reader gets what sits on top of it — ministry question-load and mix (A8.1), prior occurrences of a subject (A8.2), what a state's or constituency's MPs raised (A8.5), how the House's composition has changed (A8.6), and how subjects rise and fall (A8.8). **No document is opened.**
- **Audience served**: civic developers and researchers — the only audience with first-hand evidence of being blocked, and the owner's stated first priority. Readers second.
- **Evidence from `research.md`**: the pains this addresses are *quoted* by someone who hit them — "a staggering amount of data to scrape", "an even more daunting number of typing inconsistencies" (e.g. "Shri Sunil Kumar Singh" vs "Singh, Sunil K."), "Mapping the Asking Member to an actual Member of Parliament was also a difficult task", built "rather than accessing a structured API or database", stopping after under a month [cited, first-hand]. Inputs verified: metadata for 34,720 LS questions [cited]; the roster at `"totalElements":5426` in one unauthenticated response [verified]; RS "returns full question text" [cited].
- **Owner-stated appetite (≈2h/week)**: the **only option demonstrably inside it.** The ~1M-page estimate is irrelevant here — nothing is extracted from a document.
- **Build appetite — *agent proposal***: **small** (days), with A8.8 the one component that could push to medium if topic labelling moves from counting to models.
- **Trade-offs**: wins the ceiling, dodges the volume estimate entirely, and is the only option aimed at demonstrated demand. **Its novelty rating is better than the previous shaping credited**: the member-identity and question-to-MP joining problem is a *documented, named, unsolved* obstacle, not generic metadata work. Sacrifices all debate and answer content. Carries the accepted personal-data risk through A8.6 and A8.5.
- **Rabbit holes**: member identity resolution becoming an open-ended fuzzy-matching project with no ground truth — the same wall the cited practitioner hit; the RS member route being unidentified (`api_rs/member` → 404); A8.8 drifting into model-based labelling; A8.6 drifting from cohort analysis into republishing contact fields, which nothing now forbids.

### Option B — Upstream observability and durable citation

- **Sketch**: Watch and preserve the record *of* the record — what appeared, what vanished, which URLs stopped resolving — plus a citation that survives a document being moved (A8.7 + #3).
- **Audience served**: researchers and anyone citing these documents; barely serves citizens.
- **Evidence from `research.md`**: the strongest first-hand base of any option — three hosts failed DNS during the assessment [verified]; `sitemap.xml` → 404 [verified]; "no contract, no versioning and no deprecation notice" [cited]; a prior archival project returned 404 [verified].
- **Owner-stated appetite (≈2h/week)**: fits well; uniquely turns breakage into the product.
- **Build appetite — *agent proposal***: **small** (days).
- **Trade-offs**: best-evidenced premise of the five. **Demoted by the owner's criteria**, whose central virtue — durability — was explicitly not selected, and it has the narrowest reach. Risk: a change feed nobody reads.
- **Rabbit holes**: what counts as "the same document" across a host move; mirroring runs into the licensing question the owner scoped out.

### Option C — Debate-text slice, parsing-free core

- **Sketch**: Work from the text layer in the tested English debates volume, stopping short of interpreting structure: a search returns passages and the page they sit on (A9.6), and a term can be watched for in new sittings (A9.5). Oral answers are present in that text, so they become findable — the weak sense in which this carries #1.
- **Audience served**: researchers and journalists, plus citizens via A9.5. Broad, but aimed at audiences without first-hand demand evidence.
- **Evidence from `research.md`**: the text layer, 1,315 pages, "national" on 272 pages, page 54's starred question with the Minister's answer as text [owner test, first-hand]; the official results view showed **no snippets**, which is the gap [owner observation]; A9.5 needs no section parsing and A9.6 needs page mapping rather than speaker parsing [cited].
- **Owner-stated appetite (≈2h/week)**: **now estimated unfavourable, where it was previously only unmeasured.** The sole pre-check returned ≈813 documents and on the order of a million pages. At a nominal 2–4 KB of text per page that implies roughly 2–4 GB, which is at or beyond the free static-hosting limits recorded in `research.md` [ASSUMPTION — no bytes measured]. This is an estimate, not a measurement; one counting pass over ten volumes would confirm or overturn it.
- **Build appetite — *agent proposal***: **medium to large** (weeks, plausibly longer) — raised from `medium` purely on the volume estimate.
- **Trade-offs**: still the largest value reachable without OCR, and English-only removed its half-serves defect. **But both of its premises moved against it on the same day**: the answer payoff narrowed to roughly a quarter of starred questions, and the cost estimate grew by an order of magnitude. Risk: backfill breaches the ceiling or the free tier.
- **Rabbit holes**: the pull toward Option D the moment someone asks "who said it"; finding where one debate ends and the next begins inside a volume spanning "Nos. 1 to 10", which is section parsing by the back door; text quality across 1,315 pages with no ground truth; backfill.
- **Still viable under one condition**: if a counting pass shows volumes far below the estimate — or if the owner narrows the window, which would be a new `define` decision and not something this shaping assumes.

### Option D — Who-said-what layer (parsing-dependent)

- **Sketch**: Attribute debate text to the speaker, so passages can be retrieved by member, minister or party (A9.1) and a minister's statements on a subject assembled with page-level provenance (A9.3).
- **Audience served**: journalists, researchers and citizens checking their MP — broadest reach of any option.
- **Evidence from `research.md`**: the same single owner test plus page 54. **Against it**: the speaker/section parsing dependency is **UNVERIFIED**, there is **no demand evidence** for any A9 idea, and the 24% finding narrows A9.3's oral-answer coverage the same way it narrows Option C's.
- **Owner-stated appetite (≈2h/week)**: **cannot be assessed**, and a drifting parser produces silently wrong attributions rather than visible breakage — the opposite of the owner's stated preference.
- **Build appetite — *agent proposal***: **medium to large** (weeks to months), deliberately wide.
- **Trade-offs**: ranks highest on novelty and reach, and is the only option whose core premise is UNVERIFIED rather than merely unmeasured. Misattributing a passage to a named MP is a correctness failure with reputational consequences.
- **Rabbit holes**: speaker-label conventions across volumes and years; interruptions, points of order, chair interventions; no ground truth for attribution accuracy.

### Option E — Do not build; use or contribute to what exists

- **Sketch**: Treat the problem as substantially addressed and spend the appetite on using or improving existing work.
- **Evidence from `research.md`**: the SansadSaar/IndiaVotes cluster already runs continuous ingestion at "approximately the owner's stated end-state"; demand signals small (549 and 35 downloads). **Qualified by the second pass**: the practitioner accounts show the *member-mapping* problem specifically was not solved by those mirrors, so "already addressed" is less complete than it looked.
- **Owner-stated appetite**: trivially satisfied. **Build appetite**: none.
- **Trade-offs**: costs nothing; scores zero on novelty and personal interest, and forfeits the owner's actual goal.

## Recommendation

**Option A — the resolved metadata layer — reversing the previous recommendation of Option C.**

Two reasons, both from evidence rather than preference. **First, A is now the only option aimed at demonstrated demand.** The owner decided the audience follows the evidence; the evidence names civic developers; and the pains A addresses are quoted verbatim by a developer who hit them and stopped after a month. No other option can cite a blocked user. **Second, C's case weakened from both ends at once** — its oral-answer payoff narrowed to roughly a quarter of starred questions, and its cost estimate moved from "unmeasured" to "on the order of a million pages". A, by contrast, opens no document, so the volume estimate does not touch it.

On the owner's criteria, A also scores better than the previous shaping credited it. Its novelty is not "metadata analytics" — it is resolving a **named, documented, unsolved** obstacle that stopped a real project.

### Recommendation-stability note — read this before trusting the above

**This recommendation has now changed four times across four shapings**: A → C → C (reshaped parsing-free) → A. That oscillation is itself information, and it is not a sign of converging judgement. It means **the options are close, and each new test has moved the deciding factor rather than settling it**: the text-layer discovery favoured C, the Hindi failure and the 24% finding and the volume estimate moved back toward A, and the practitioner accounts pushed further that way.

Per the working agreement, a conclusion revised this many times warrants outside review rather than a fifth confident restatement. The honest summary for `/speckit-assess-decide` is: **A and C are within noise of each other on everything except demand evidence, where A is now clearly ahead, and cost, where A is clearly cheaper.** If a counting pass shows volumes far below the estimate, C returns to contention immediately.

**Stated against the recommendation**: Option D is what the owner's criteria actually point at — highest novelty, broadest reach — and is excluded only because its enabling capability is UNVERIFIED. Option B has the best-evidenced premise of the five and loses only on a criterion the owner declined to use.

**This is not a decision.**

## Out of Scope (for the recommended option)

Inherited from `problem.md` Non-Goals: anything before the 17th Lok Sabha; **Hindi** and all other languages; uncorrected-vs-final debate comparison (owner-excluded); `eparlib.sansad.in` and `eparlib.nic.in`; terms-of-use, licensing and copyright analysis; revenue or commercialisation; a team.
- **Owner decision 2026-10-10**: still not researched, and the dataset is published without that determination — with the gap disclosed as `source_terms` on `manifest.json` and every Coverage Statement, in the page footer, and in `DATA-LICENSE.md` → *Source terms: not determined*, and with corrections and removal requests taken through the issue tracker (`corrections_url`). No legal conclusion either way.

Newly excluded by choosing Option A:

- **All PDF handling, text extraction and page-level work** — Options C and D. This is what keeps the ~1M-page estimate out of the critical path; it is **not** a claim that the volume problem has been solved.
- **All debate text and all answer text**, including the oral answers the owner found. The 24% finding reduces what is forfeited but does not eliminate it.
- **Speaker attribution** (A9.1, A9.3) and the structured form of #1.
- **The eight dropped candidates**, and Options B and E.
- **Any claim about what the official Debate Search matches**, or use of its "KEYWORD COUNT" as a quantity.

## Assumptions to Validate

- **That solving member identity and question-to-MP joining is useful to other builders** — inferred from one practitioner's documented failure plus one project's refusal to scrape. Two accounts, not a user study. **This is the assumption the recommendation is least able to defend.**
- **That member identity can be resolved without ground truth.** The cited practitioner needed fuzzy matching and still found it "a difficult task"; nothing establishes that it is tractable to a solo maintainer at 2h/week.
- **That a Rajya Sabha member route exists.** `api_rs/member` → 404 and the correct route was never found; without it, Option A is Lok Sabha-only and the owner's Rajya Sabha scope decision cannot be honoured.
- **That the question-metadata route is reachable and stable** — cited from a third party as found "in the Next.js client bundle", never fetched directly in either pass.
- **That builders would use it rather than build their own again** — eight projects have already each built their own, which is evidence of need *and* of a preference for self-building.
- **That the official Digital Sansad / Sansad Bhashini programme does not supersede this** — UNVERIFIED after two passes; bears less on Option A than on C, since metadata joining is not what that programme is reported to build.
- **That the ~1M-page estimate is roughly right.** It does not affect Option A, but it is the figure that demoted Option C, so if it is badly wrong the recommendation should be revisited.
