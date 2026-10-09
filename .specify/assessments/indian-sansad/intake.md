# Idea Intake: New uses for India's published parliamentary data (Sansad Issues)

- **Slug**: indian-sansad
- **Created**: 2026-10-08
- **Source**: pasted text (no URL supplied; no fetch performed)
- **Type**: exploration

## Idea (as captured)

> "India publishes a ton of parliamentary data but I believe it is underused and hard to access. Sansad Issues is a solo, non-commercial civic project. I want new and useful ways to use what Parliament has published on sansad.in and its eLibrary, for citizens, journalists and researchers. I especially want uses I haven't thought of. I have not chosen any. Eventual goal is to create a public website that can be self sustaining in the sense that it will keep track of new data published on continuing basis and make use of it."

No credentials, tokens, or credential-bearing URLs appeared in the input; nothing was redacted. `sansad.in` and "its eLibrary" are named as subject matter, not as inputs to fetch — no URL Trust Policy branch was exercised because no URL was provided.

## Restated

The owner wants to identify candidate uses — not yet chosen — for the parliamentary material India already publishes on sansad.in and its eLibrary, serving citizens, journalists, and researchers, with an explicit preference for uses the owner has not already considered. The eventual target is a public, non-commercial website run by one person that continuously tracks newly published material and does something useful with it.

## Origin & Context

- **Raised by**: the project owner — sole maintainer of "Sansad Issues", described as a solo, non-commercial civic project. [NEEDS CLARIFICATION: whether anyone else is involved or expected to be, and whether the work is to be published under the owner's name]
  - Answer: Solo. No one else is involved or expected to be. (The second half of the question — whether the work is published under the owner's name — is still unanswered.)
- **Trigger**: not stated as an event. The stated motivation is a belief that published parliamentary data is "underused and hard to access". [NEEDS CLARIFICATION: what prompted raising this now — a specific frustration, a failed search, prior attempt, external ask, or deadline]
  - Answer: The owner was looking for a solo side project built on an under-exploited public dataset, and Indian parliamentary data came up as a candidate. No use has been picked.
- **Observed repository state**: the project directory contains only `.claude/` and `.specify/` — no application source code, data, or prior implementation is present at intake time. Whether "Sansad Issues" already exists elsewhere (site, dataset, scrapers, audience) is unknown. [NEEDS CLARIFICATION]
  - Answer: This is a fully fresh project, starting from zero. No earlier work, repository, notes, or material related to it is to be referred to or consulted, and no folder outside this project directory is to be read or searched.
- **Explicit framing constraint**: the request is for option generation, not for picking or designing. No candidate use has been selected.

## First-Glance Unknowns

- [NEEDS CLARIFICATION: what sansad.in and the eLibrary actually publish, and in what form — questions and answers, debates/verbatim proceedings, bills, bulletins, committee reports, member profiles, attendance, voting, budget documents, historical holdings — and which of these are in scope]
- [NEEDS CLARIFICATION: how that material is technically accessible — any API, bulk download, or sitemap, versus HTML/PDF/scanned images only; URL stability; rate limits; whether scanned material needs OCR]
- [NEEDS CLARIFICATION: terms of use, licensing, and copyright status for sansad.in and eLibrary content — what may be re-hosted, redistributed, or derived from, and whether automated collection is permitted]
  - Answer: Out of scope for this assessment. Do not research terms of use, licensing or copyright.
- [NEEDS CLARIFICATION: historical depth required — current Lok Sabha/Rajya Sabha session only, a few terms, or the full archive since 1952]
  - Answer: The current term and the one before it.
- [NEEDS CLARIFICATION: language coverage expectations — English and Hindi content, other languages, transliteration, and whether cross-language search or translation is in or out of scope]
  - Answer: English and Hindi.
- [NEEDS CLARIFICATION: which of the three named audiences is primary when their needs conflict — citizens, journalists, or researchers — and what each is currently unable to do]
  - Answer: No audience ranks first yet. The assessment should show which of citizens, journalists, or researchers has the biggest unmet need that the published data could address.
- [NEEDS CLARIFICATION: the evidence behind "underused and hard to access" — who is blocked, at what step, and how that would be observed]
- [NEEDS CLARIFICATION: what already exists in this space (e.g. PRS Legislative Research, data.gov.in, academic/NGO datasets, earlier scraping projects) and what gap would remain after accounting for them]
- [NEEDS CLARIFICATION: what "self-sustaining" means concretely — unattended continuous ingestion, a monetary cost ceiling, a maintenance-hours ceiling, or longevity without the owner's attention]
  - Answer: Once built, it detects and processes newly published material by itself, with no routine manual work from the owner, and it earns no revenue. Cost ceiling: no budget — the first deployment should be as cheap as possible, using free tiers wherever possible, just to validate that it works. Maintenance ceiling: about 2 hours per week.
- [NEEDS CLARIFICATION: appetite and constraints of a solo non-commercial maintainer — time per week, money per month, tolerance for manual steps, and acceptable failure modes when upstream pages change]
  - Answer: Time per week: 2 hours. Money per month: none (no budget; free tiers where possible). Tolerance for manual steps: occasional. If upstream pages change, the preference is that it degrades quietly for visitors but flags the problem to the owner.
- [NEEDS CLARIFICATION: how many candidate uses the owner wants carried forward, and by what criteria they intend to choose among them]
  - Answer: A shortlist of the most promising uses, with the evidence for each, not a single winner. The owner will choose among them later.
- [NEEDS CLARIFICATION: any out-of-bounds areas — e.g. editorial commentary, scoring or ranking individual members, political interpretation, or anything with legal/reputational exposure in publishing about Parliament]
  - Answer: No preference at this stage. No areas have been ruled in or out yet.
