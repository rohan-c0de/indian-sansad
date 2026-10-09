# Problem Definition: The published parliamentary record is available as documents, not as data

- **Slug**: indian-sansad
- **Created**: 2026-10-08
- **Inputs used**: intake.md ✓ | research.md ✓

**Sourcing rule applied throughout**: every claim below carries `[research.md: <section>]` or `[intake.md: <answer>]`. Anything the agent originated is labelled **Proposed** and is not presented as a finding.

## Problem Statement

Parliament publishes the record for the 17th–18th Lok Sabha period and it can be located, but what a person holds at the end of a search is a document rather than data: answers to parliamentary questions are PDF-only in both Houses, the record-listing pages render no content outside a browser, and bulk access was refused when officially requested. [research.md: Capability Gaps #1; Verified first-hand; Users & Demand]

Twenty-one uses are recorded (seven in Capability Gaps, one of which the owner excluded; eight in the ideation pass; and six debate-text ideas, A9.1 to A9.6, added on 2026-10-08); the owner has chosen none. [research.md: Capability Gaps & Candidate Uses; intake.md: "A shortlist of the most promising uses … not a single winner"] The agent reads the uses as sharing a document-not-data blocker; this is a proposed reading, not a research.md finding, and not every use depends on it.

**Deliberately *not* claimed**: that the record cannot be *found*. The owner's browser observation shows a Debate Search whose free-text box returned 10,595 hits for "national", with a per-volume PDF download on each row. What it did not show was any snippet in the results view. Whether the open-link view page exposes text is **UNVERIFIED**, as is the meaning of the per-row "KEYWORD COUNT: 1". [research.md: Data & Constraints — Debate Search page, owner browser observation]

**Narrowed by the second research pass (2026-10-09)**: oral answers *are* present as text inside debates PDFs, as the owner's page-54 observation showed — but only "24% of questions listed for oral response were answered by Ministers in the House in Lok Sabha" across the 17th Lok Sabha, and starred questions are themselves a minority of all questions. The share of the answer record reachable that way is therefore small, and the bulk of answers remain PDF-only written replies. [research.md: Second Research Pass — incidental finding]

## Affected Users & Stakeholders

Ordered by strength of evidence in `research.md`, **not** by owner priority — intake leaves priority unset and asks the assessment to show which audience has the biggest unmet need. [intake.md: audience answer]

- **Civic developers and data re-publishers** — *not* among the three audiences named in intake, and the most strongly evidenced group. At least 8 independent projects rebuild this data; one cluster runs 2-hourly ingestion holding ~243K–280K question records, and one repository within it has 1,624 commits. They each absorb the same extraction cost. [research.md: Users & Demand; Prior Art] **Confirmed first-hand by the second research pass (2026-10-09)**: one developer who attempted exactly this task documented "a staggering amount of data to scrape", name-spelling inconsistencies and difficulty "Mapping the Asking Member to an actual Member of Parliament", and covered only 29 November – 23 December 2021 before stopping; a second project declined to scrape at all after being refused permission. This group now rests on observed behaviour rather than inference. [research.md: Second Research Pass — Blocker 3]
- **Researchers** — convert corpora by hand before analysing them. A committee-report corpus (1954–2023) exists only because the originals were "scanned pdfs" needing conversion (35 downloads); a current-MP activity dump has 549 downloads and 873 views; a published topic-modelling study rests on a hand-built corpus whose authors note "it is difficult to analyze such a huge collection manually". Candidate uses aimed at this group: A8.1, A8.2, A8.6, A8.7, A8.8, and A9.1, A9.2, A9.3, A9.4, A9.6. [research.md: Users & Demand; Additional candidate uses]
- **People who cite these documents** — a distinct affected group surfaced by the ideation pass. Three hosts failed during the assessment (`eparlib.nic.in`, `loksabha.nic.in`, `pprloksabha.sansad.in`), there is no sitemap, and third parties still link to dead hosts. Candidate uses: existing #3, A8.7. [research.md: Market & Context; Verified first-hand; Additional candidate uses A8.7]
- **Journalists** — named in intake; direct evidence in `research.md` is **absent**. The authoritative critique names "researchers and citizens", not journalists, and the one journalistic-adjacent signal is a sitting MP's commentary, recorded there as "an interested party's claim, not an audited finding". Candidate uses aimed at this group: A8.1, A8.2, A8.4, A8.8, and A9.1, A9.2, A9.3, A9.4, A9.5, A9.6. [research.md: Users & Demand] The second pass located the nearest thing to direct journalist evidence — a newsroom analysis of 35 parliamentary questions (2015–2023) reporting "no such data is maintained" in 17 of them — but the URL returned a cross-host 301 and was **not fetched** under the URL Trust Policy, so it stays **UNVERIFIED**. Two passes have now looked and found no first-hand journalist account. [research.md: Second Research Pass — Blocker 3]
- **Citizens** — the owner intends a student or civics learner, a curious general reader, and a voter checking their MP. `research.md` records that **no evidence of citizen demand was found**; every located signal traces to a researcher, developer, think tank or politician. Carried as owner intent, not as evidenced demand. Candidate uses aimed at this group: A8.3, A8.4, A8.5, and A9.1, A9.5. [research.md: Users & Demand, including the owner's intent note; intake.md: citizen-users answer] The second pass looked again and found none. [research.md: Second Research Pass — Blocker 3]

**Stakeholders**

- **The owner** — solo; no one else involved or expected. Sole decider and sole maintainer. [intake.md: "Solo. No one else is involved or expected to be."]
- **Lok Sabha and Rajya Sabha Secretariats** — the publishers. Custodians for both Houses "explained that whatever was on the website was all that was accessible"; hosts under their control have already stopped resolving. [research.md: Users & Demand; Verified first-hand]
- **Individual MPs** — data subjects rather than users. The member endpoint returns, unauthenticated, personal phone, personal email, present and permanent address, `dob`, `maritalStatus` and family composition for 5,426 named people. [research.md: Data & Constraints]
- **Incumbents** — PRS (bill tracking, briefs, MP track records, vital statistics), ADR/MyNeta (affidavits only, explicitly not parliamentary activity), the SansadSaar/IndiaVotes cluster, TCPD. [research.md: Prior Art]
- **MeitY and the Sansad Bhashini programme** — could narrow the problem from above; scope **UNVERIFIED**. [research.md: Prior Art; Evidence Against #5]

## Goals

**Owner-stated only** — each traceable to `intake.md` or the captured idea:

- A public website that keeps track of newly published data on a continuing basis and makes use of it. [intake.md: idea as captured]
- Once built, it detects and processes newly published material by itself, with no routine manual work from the owner. [intake.md: self-sustaining answer]
- New and useful ways to use what Parliament has published, for citizens, journalists and researchers — expressly including uses the owner has not thought of. [intake.md: idea as captured]
- A shortlist of the most promising uses, with the evidence for each, rather than a single winner; the owner chooses later. [intake.md: shortlist answer]
- English only. Owner decision 2026-10-08, superseding intake.md's "English and Hindi". [owner decision; intake.md: language answer, superseded]
- The current term and the one before it. [intake.md: depth answer]
- Show which of citizens, journalists or researchers has the biggest unmet need the published data could address. [intake.md: audience answer]
- When upstream pages change, it degrades quietly for visitors but flags the problem to the owner. [intake.md: appetite answer]
- It earns no revenue. [intake.md: self-sustaining answer]

**Goals originated by the agent, accepted by owner 2026-10-08:**

- **Accepted by owner 2026-10-08**: that the record become usable as data and not only as documents, so that use of it stops requiring each person to extract it first. Rationale is the shared blocker in the Problem Statement; the owner has not stated this as a goal.
- **Accepted by owner 2026-10-08**: that whichever use is chosen remain operable by one person inside the stated ceilings. This restates the owner's constraints as an objective, which the owner did not do.

## Non-Goals

- **Choosing the use.** Intake asks for options, not a winner. [intake.md: shortlist answer]
- **Any depth before the 17th Lok Sabha.** [intake.md: depth answer] **No OCR claim is made here.** `research.md` establishes that pre-1952 historical debates and older committee reports are scanned PDFs; it does **not** establish whether current-term question-answer or debate PDFs carry a text layer, so excluding older material cannot be said to avoid OCR. [research.md: Data & Constraints; Additional candidate uses preamble]
- **Languages beyond English and Hindi**, including the wider Bhashini language surface. [intake.md: language answer; research.md: Prior Art]
- **Hindi** (owner decision 2026-10-08; a Hindi test gave garbled or partial text, cause **UNVERIFIED**).
- **Comparing uncorrected against final-edited debates** — not of interest to the owner; recorded as not to be pursued rather than prohibited. [research.md: Capability Gaps #2, owner note]
- **Any reliance on `eparlib.sansad.in` or `eparlib.nic.in`** — treated as unavailable by owner decision. [research.md: Gaps, two CLOSED items]
- **Terms of use, licensing and copyright analysis** — scoped out by the owner. This defers a risk; it does not establish that none exists. [intake.md: licensing answer]
- **Revenue or commercialisation.** [intake.md: self-sustaining answer]
- **A team.** [intake.md: solo answer]

**Guardrail — owner decision made, not a proposal:**

- Owner decision 2026-10-08: the owner does NOT adopt a guardrail against republishing MPs' personal contact data. The risk notes stay on record: the member endpoint returns `personalPhone`, `delhiPhone`, `email`, present and permanent addresses, `dob`, `maritalStatus`, `numberOfSons` and `numberOfDaughters` for 5,426 named people without authentication; the DPDP framing is an untested ASSUMPTION; licensing was scoped out by the owner, which defers that risk and does not clear it. [research.md: Data & Constraints; intake.md: out-of-bounds answer, licensing answer]

## Success Metrics

**Owner-stated ceilings — the only metrics the owner has set:**

- Owner maintenance: **about 2 hours per week**. (baseline: 0, nothing built) [intake.md: self-sustaining and appetite answers]
- Money: **none per month**; first deployment as cheap as possible, free tiers wherever possible. (baseline: ₹0) [intake.md: appetite answer] — note that the owner lifted this limit **for the ideation pass only**. [research.md: Additional candidate uses preamble]
- Revenue: **none**. (baseline: none) [intake.md: self-sustaining answer]
- Manual steps: **occasional** is tolerated; routine manual work is not. [intake.md: appetite and self-sustaining answers]

**Metrics originated by the agent, accepted by owner 2026-10-08:**

- **Accepted by owner 2026-10-08**: share of newly published in-scope documents picked up without manual intervention. (baseline: 0, nothing built)
- **Accepted by owner 2026-10-08**: lag from upstream publication to availability. (baseline: none built. Upstream reference points: uncorrected debates next-day, final edited typically 10–15 days [research.md: Verified first-hand])
- **Accepted by owner 2026-10-08**: breakage flagged to the owner rather than served silently wrong. **Qualitative** until a detection signal is defined.
- **Accepted by owner 2026-10-08**: use by someone other than the owner. (baseline: 0. External comparators from `research.md` are **weak proxies** for a service and small in absolute terms: 549 downloads for a static current-MP dump, 35 for a historical committee corpus [research.md: Users & Demand; Market & Context]) → the threshold that would satisfy the owner is unstated.

## Cost of Inaction

The record stays usable only by those who can extract it themselves — the status quo `research.md` describes as records that are "both hard to find, and hard to make use of by researchers and citizens", with custodians stating that the website is all there is. Answers to parliamentary questions remain unavailable as text in either House: Rajya Sabha answer text is `null` for every record, and Lok Sabha answers sit in randomly-suffixed PDFs. The one-off-dump pattern continues, so each researcher pays the conversion cost again and the result decays from its cutoff date. [research.md: Users & Demand; Capability Gaps #1; Market & Context]

Access degrades while nothing is done: two formerly canonical hosts no longer resolve and a third failed DNS during this assessment, while third parties still link to the dead ones; one prior archival project returned 404 when checked. [research.md: Market & Context; Prior Art; Verified first-hand]

**The barrier is now quantified.** The in-scope record is approximately **813 sitting-day debate documents** across both Houses — 274 cited sittings for the 17th Lok Sabha plus roughly 154 for the 18th, with Rajya Sabha estimated at about 0.9× the Lok Sabha count — and, at the one sampled volume of 1,315 pages, on the order of **one million pages** in English alone. [ASSUMPTION — a cited sitting count multiplied by a single sampled page count; an order of magnitude, not a measurement] That is the extraction cost each individual currently absorbs alone, and it is the most likely explanation for why the one documented attempt covered under a month of questions before stopping. [research.md: Second Research Pass — Blockers 1 and 3]

**Bound on this section**: inaction does not mean nothing exists. The SansadSaar/IndiaVotes cluster already runs continuous ingestion at approximately the owner's stated end-state, and PRS continues to publish curated analysis — so the cost is that fragmentation persists and the answer-text gap stays open, not that provision is absent. [research.md: Evidence Against #2; Prior Art]

## Open Questions

**Carried from `research.md`, still open:**

- [NEEDS CLARIFICATION: the complete `api_ls/*` / `api_rs/*` inventory and the parameters the committee routes require — build-stage; does not block shaping]
- [NEEDS CLARIFICATION: what data.gov.in holds, in what formats, how current — blocked by HTTP 403 to automated fetches]
- [NEEDS CLARIFICATION: measured volumes — documents per sitting day, MB per session — which gate the free-tier expectation, currently ASSUMPTION at low confidence]
- [NEEDS CLARIFICATION: the scope of Digital Sansad / Sansad Bhashini — the one finding that could remove this problem from above, still UNVERIFIED]
  - Answer: The owner could not tell what the Digital Sansad app offers for debates (owner, 2026-10-08). **Remains open.**
- [NEEDS CLARIFICATION: whether current-term question-answer and debate PDFs carry a text layer. English: one volume has a text layer; other volumes and written answers untested. Hindi: out of scope by owner decision. The OCR cost of the in-scope period therefore remains unknown and no use may assume it is avoided]

**Carried from the second research pass (2026-10-09):**

- [NEEDS CLARIFICATION: pages per sitting-day document, measured across several volumes rather than one — the single missing factor in the volume estimate]
- [NEEDS CLARIFICATION: the Rajya Sabha sitting-day series for 2019–2026, currently an ASSUMPTION derived from two sampled sessions]
- [NEEDS CLARIFICATION: the unit of the 16124 "Full Text" facet count, which does not reconcile with ~428 in-scope Lok Sabha sitting days]
- [NEEDS CLARIFICATION: the debates data route beneath `api_ls/debate`, whose service index is reachable but whose data sub-path was not identified]
- [NEEDS CLARIFICATION: whether to approve `isignal.in` so the one newsroom analysis of parliamentary answers can be verified]
- [NEEDS CLARIFICATION: any first-hand journalist or citizen account — two passes have found none]
- [NEEDS CLARIFICATION: what the Digital Sansad app offers for debates — unresolved after two passes and not resolvable by fetching; needs the app on a device]

**At definition stage:**
- [NEEDS CLARIFICATION: is there any observed case of someone actually blocked by this data — a story not written, a dataset requested, an analysis abandoned? `research.md` records demand evidence as absent for journalists and none at all for citizens]
  - Answer: The owner knows of no specific case of someone blocked by this data (owner, 2026-10-08). **Remains open** — `decision.md` identifies this as the blocker that decides whether to build at all, and the owner's answer narrows it to "none known" rather than closing it.

- [NEEDS CLARIFICATION: "the current term and the one before it" maps cleanly onto the Lok Sabha (18th and 17th) but not onto the Rajya Sabha, which is a continuing house with no terms. What is the Rajya Sabha scope boundary — a date range, a session range, or is the Rajya Sabha out of scope?]
  - Answer: Owner decision, confirmed 2026-10-08: The Rajya Sabha is **in scope**, bounded by the same calendar period the Lok Sabha scope covers — from the start of the 17th Lok Sabha to the present end of the 18th. The boundary is defined relationally, by the Lok Sabha window, not by Rajya Sabha terms or session numbering. Approximately mid-2019 onward **[ASSUMPTION — the date was not verified in this session]**; the exact start and end dates, and the Rajya Sabha session numbers falling inside that window, are **UNVERIFIED** in this session and must be confirmed against an authoritative source before use.
- [NEEDS CLARIFICATION: Does the owner adopt the proposed guardrail against re-publishing MPs' personal contact data? It is the agent's proposal, not an owner decision, and intake set no out-of-bounds areas]
  - Answer: Not adopted (owner decision, 2026-10-08).
- [NEEDS CLARIFICATION: does the owner accept any of the proposed goals and proposed metrics above? Only the 2h/week, ₹0/month, no-revenue and occasional-manual-steps ceilings are owner-stated]
  - Answer: Accepted in full (owner decision, 2026-10-08).
- [NEEDS CLARIFICATION: the most strongly evidenced affected group — civic developers — is not among the three audiences named in intake, while the audience described most concretely (citizens) has no evidence in `research.md`. Does the definition follow the evidence or the owner's intent? Owner's call; left unresolved]
  - Answer: Follow the evidence (owner decision, 2026-10-08). Civic developers and researchers come first. Citizens remain the owner's intent but not the basis of the definition.
- [NEEDS CLARIFICATION: is the work published under the owner's name? Half-answered at intake; bears on the personal-data and publication-risk posture]
  - Answer: No. It will be published under a project name, not the owner's name (owner decision, 2026-10-08).
- [NEEDS CLARIFICATION: by what criteria will the owner choose among the twenty-one recorded candidate uses at the decide stage — reach, novelty, durability, personal interest, or lowest upkeep?]
  - Answer: Novelty, personal interest and reach (owner decision, 2026-10-08). Durability and low upkeep were not selected as criteria; the 2h/week ceiling still applies as a limit.
- [NEEDS CLARIFICATION: does sansad.in's Debate Search free-text box match inside debate text, and does the open-link view expose text? Both UNVERIFIED; neither changes this problem statement]
