# Feature Specification: Resolved Metadata Layer for the Indian Parliamentary Record

**Feature Branch**: `001-resolved-metadata-layer`

**Created**: 2026-10-09

**Status**: Draft

**Input**: User description: "Use the handoff summary in .specify/assessments/indian-sansad/decision.md to specify the approved Option A (resolved metadata layer). Carry the handoff's open questions forward as open questions; do not guess answers."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A builder gets questions already joined to the right member (Priority: P1)

Someone building their own tool, analysis or dataset wants the parliamentary question record with each question already attached to the specific Member of Parliament who asked it — one identity per person, consistent across every spelling the record uses — so they can start from a joined record instead of spending their project's time reconciling names.

**Why this priority**: This is the only part of the feature with first-hand evidence of demand. The assessment records a developer who attempted exactly this task, documented name-spelling inconsistency and the difficulty of mapping an asking member to an actual MP, and covered under a month of questions before stopping. Every other story in this spec is built on top of the joined record this one produces, so it is also the technical foundation.

**Independent Test**: Take a set of questions whose asking members are written in several different name forms, request the joined record, and confirm each question resolves to exactly one member identity with party, state, constituency and term attached — or is visibly flagged as unresolved. Delivers value on its own even if no reader-facing view is ever built.

**Acceptance Scenarios**:

1. **Given** the same person appears in the source record as "Shri Sunil Kumar Singh" in one place and "Singh, Sunil K." in another, **When** a consumer retrieves the joined record, **Then** both questions are attached to one single member identity.
2. **Given** a question was co-asked by several members, **When** a consumer retrieves it, **Then** every asking member is attached and the question is not duplicated or silently reduced to one asker.
3. **Given** an asking member's name cannot be matched to any known member, **When** a consumer retrieves the joined record, **Then** the question is present and explicitly marked unresolved, and is never dropped.
4. **Given** a consumer wants only one session or one ministry, **When** they request that subset, **Then** they receive it without having to take the whole record.

---

### User Story 2 - A journalist or researcher sees which ministries carry the question load, and whether a subject has come up before (Priority: P2)

A journalist or researcher wants to see how questions distribute across ministries and sessions — how many, what mix of types, how that shifts over time — and, for any given subject, whether the same thing has been asked before and by whom.

**Delivery**: This story is delivered as an interactive page that runs entirely in the visitor's browser over the published dataset files — no server, no paid service, and no calls from the browser to the upstream source. The visitor picks a ministry and a span of sessions to see question counts and the mix of question types, and searches a subject to see its prior occurrences. Every figure shown states its counting basis, questions whose asking members are unresolved or ambiguous are visibly flagged rather than hidden, and the page shows the coverage statement, including which Houses are covered.

**Why this priority**: Researchers are the second evidenced audience in the assessment, and these two views are the cheapest useful things that sit directly on the joined record from Story 1. They require no new source material.

**Independent Test**: Pick a ministry and a period, request its question profile, and confirm the counts and type mix can be reproduced by hand from the underlying record. Separately, pick a question subject and confirm prior near-identical subjects are returned with their dates and ministries.

**Acceptance Scenarios**:

1. **Given** a ministry and a span of sessions, **When** a user views its question profile, **Then** they see question counts, the mix of question types, and how both changed across those sessions.
2. **Given** a question subject, **When** a user asks whether it has been raised before, **Then** earlier questions on the same subject are listed with their dates, ministries and asking members.
3. **Given** two ministries, **When** a user compares them over the same period, **Then** the comparison uses the same counting basis for both and states what that basis is.

---

### User Story 3 - A person looks up their state or constituency (Priority: P3)

Someone who knows where they live, but not their MP's name, wants to start from a state or constituency and see what the members representing it have raised in Parliament.

**Delivery**: This story is delivered as an interactive page that runs entirely in the visitor's browser over the published dataset files — no server, no paid service, and no calls from the browser to the upstream source. The visitor picks a state or a constituency to see its members and their questions. Every figure shown states its counting basis, questions whose asking members are unresolved or ambiguous are visibly flagged rather than hidden, and the page shows the coverage statement, including which Houses are covered.

**Why this priority**: This is the owner's intended citizen use — "a voter checking their MP" — expressed in the form the record can actually support. It is P3 because the assessment found no evidence of citizen demand after two research passes; it is included because it is nearly free once Story 1 exists, not because demand is established.

**Independent Test**: Enter a constituency name, confirm the members who have represented it in the covered period are listed, and confirm their questions are reachable from there.

**Acceptance Scenarios**:

1. **Given** a constituency name, **When** a user looks it up, **Then** the members representing it within the covered period are listed with their party and term.
2. **Given** a state, **When** a user looks it up, **Then** the subjects its members have raised are summarised and individual questions are reachable.
3. **Given** a constituency that was represented by different members across the two covered terms, **When** a user looks it up, **Then** both members appear with their respective periods, not merged into one.

---

### User Story 4 - Composition and subject trends over the covered period (Priority: P3)

A researcher wants to see how the House's composition has changed across the covered terms — by party, state and number of terms served, which are the fields FR-008 allows — and how question subjects have risen and fallen across sessions.

**Delivery**: For the first release this story is delivered as precomputed files in the published dataset, not on the interactive page that delivers Stories 2 and 3. The page may add it later; nothing here requires it to.

**Note**: Composition is limited to party, state and number of terms served. Gender, age band, profession and qualification are out of scope here; publishing any of them requires an explicitly recorded decision under FR-008.

**Why this priority**: Both sit on material already in hand once Story 1 exists, and the assessment notes that comparable academic topic work stops at 2019 with nothing kept current. P3 because neither is load-bearing for the feature's evidenced purpose.

**Independent Test**: Request a composition breakdown for one term and confirm the totals reconcile with the member count for that term. Separately, request a subject's frequency across sessions and confirm the series can be reproduced by counting the underlying questions.

**Acceptance Scenarios**:

1. **Given** a covered term, **When** a user requests a composition breakdown, **Then** the categories sum to the total membership for that term and any member with missing attributes is counted in an explicit "not stated" category rather than omitted.
2. **Given** a subject, **When** a user requests its trend, **Then** a per-session series is returned with the counting basis stated.

---

### Edge Cases

- Two different members share the same or near-identical name in the same House — the system must not merge them into one identity.
- A member changes party, or moves between Houses, within the covered period.
- A question is attributed to a member who was not sitting on the date of the question.
- An asking member's name is present but matches several known members equally well.
- The upstream record changes shape — a field disappears, is renamed, or stops being served — mid-period.
- Rajya Sabha material proves unobtainable, leaving the record covering one House.
- A session is published incompletely and later amended upstream.
- A consumer requests a period that is partly outside the covered window.
- The upstream serves an unexpectedly large or truncated response during a scheduled refresh.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST cover questions from the 17th and 18th Lok Sabha. System MUST cover Rajya Sabha material only once a Rajya Sabha member route has been established; until then the coverage statement MUST state that the published record covers the Lok Sabha only.
- **FR-002**: System MUST assign each Member of Parliament a single stable identity that persists across every name form the source record uses for that person.
- **FR-003**: System MUST attach to each question every member recorded as asking it, without duplicating the question and without reducing a co-asked question to a single asker.
- **FR-004**: System MUST retain and explicitly mark any question whose asking member cannot be resolved to a single identity, and MUST NOT silently drop or silently guess it.
- **FR-005**: System MUST record, for every resolved join, the source name form as written and an identifier for the source record it came from, so that a consumer can verify the join independently without re-deriving it.
- **FR-006**: System MUST publish the joined record in a form a third party can consume and re-use without re-deriving the identity resolution.
- **FR-007**: System MUST allow a consumer to retrieve a subset by session, ministry, member, state or constituency without taking the whole record.
- **FR-008**: System MUST limit published member attributes to those required by the user stories in this spec — name forms, party, state, constituency, House, term, and sitting status. Any additional personal attribute available from the source MUST NOT be published unless its publication is an explicitly recorded decision. (This implements the assessment's position that no guardrail was adopted: publication is permitted but must be deliberate, not incidental.)
- **FR-009**: System MUST detect newly published in-scope material and process it without routine manual intervention.
- **FR-010**: System MUST continue to serve the last known-good record when the upstream changes shape or becomes unavailable, rather than serving an empty or partial record as if it were complete.
- **FR-011**: System MUST signal to the maintainer when ingestion fails, when the upstream shape changes, or when resolution quality falls below its stated threshold — while degrading quietly for visitors.
- **FR-012**: System MUST state, wherever a count or comparison is shown, the basis on which it was counted.
- **FR-013**: System MUST make the covered period and the known gaps in coverage visible to a consumer, including which House a given part of the record covers.
- **FR-014**: System MUST operate without any paid service.
- **FR-015**: System MUST NOT open, extract from, or depend on any document file from the source record; all material comes from already-structured sources.
- **FR-016**: System MUST record the date each part of the published record was last refreshed.

### Key Entities *(include if feature involves data)*

- **Member**: one person who has served in Parliament during the covered period. Carries a stable identity, the set of name forms by which the source record refers to them, party, state, constituency, House, terms served, and sitting status.
- **Question**: one question put to a ministry. Carries its subject, type, date, session, the ministry addressed, and one or more asking members — or an explicit unresolved marker.
- **Ministry**: the government department a question is addressed to, as named in the source record.
- **Session**: a numbered sitting period of a House, used as the primary time unit for counts and trends.
- **House**: Lok Sabha or Rajya Sabha, with its own session numbering and coverage window.
- **Constituency**: the territorial seat a Lok Sabha member represents; the entry point for User Story 3.
- **Resolution record**: the link between a name form as written in the source and the member identity it was resolved to, with its provenance and confidence.
- **Coverage statement**: what period, House and session range the published record claims to cover, and where it is known to be incomplete.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A consumer can obtain the joined question record for the covered period without writing any extraction or name-reconciliation code of their own.
- **SC-002**: At least 95% of in-scope questions resolve to exactly one member identity, and 100% of the remainder are visibly marked unresolved rather than absent. *(Threshold is an assumption — see Assumptions.)*
- **SC-003**: Newly published in-scope material appears in the published record without any manual step by the maintainer.
- **SC-004**: Routine upkeep by the maintainer stays within about 2 hours per week.
- **SC-005**: Running cost stays at zero per month.
- **SC-006**: When the upstream changes shape or fails, visitors see a coherent, dated record rather than an error or an empty result, and the maintainer is notified within one refresh cycle.
- **SC-007**: Any count or comparison shown can be reproduced by hand from the published record using the stated counting basis.
- **SC-008**: A person who knows only their constituency or state can reach their members' questions without knowing a member's name.
- **SC-009**: The published record is used by at least one person other than the maintainer. *(No target level is set — see Open Questions Carried Forward.)*
- **SC-010**: No member attribute beyond those named in FR-008 appears anywhere in the published record unless a recorded decision authorising it exists, verifiable by inspecting the published record against that list.

## Assumptions

- **Audience priority follows the evidence**, per the recorded owner decision: civic developers and researchers first, with citizen use included as owner intent rather than evidenced demand.
- **English only.** A recorded owner decision supersedes the earlier "English and Hindi" scope; Hindi is a non-goal for this feature.
- **The joined record is derived only from already-structured sources** — published question metadata, the published member roster, and Rajya Sabha question text. No document file is opened. This is what keeps the assessment's ~1,000,000-page estimate off this feature's critical path; it does not resolve that estimate.
- **The 95% resolution threshold in SC-002 is a reasonable-default assumption**, not an owner-stated or evidence-derived figure. It exists so the requirement is testable; it should be revisited once real resolution rates are known. **It was tested against the full 95,269-question window on 2026-10-09 and retained unchanged at 95%: the matcher alone reached 90.64%, the owner adopted a token-containment tier taking it to 94.78%, and four owner-confirmed maintainer assertions carry it to 96.26%, a 1.26-point margin — so the threshold was met by improving resolution rather than by lowering the target (see `spike/spike-report.md`).**
- **The owner's scope decision covers both Houses; Rajya Sabha obtainability is unverified.** The assessment could not identify the route to Rajya Sabha member data. FR-001 is met either way: while no Rajya Sabha route exists, FR-001 requires the coverage statement to say Lok Sabha only, and a Lok Sabha-only release that declares itself as such satisfies it. What goes unmet is the **owner's wider scope decision** that the Rajya Sabha be covered on the same calendar window — see Open Questions Carried Forward.
- **Personal-attribute publication is permitted but must be deliberate.** The owner declined to adopt a guardrail against republishing members' personal contact data; FR-008 therefore restricts publication to what the user stories need and requires any wider publication to be an explicit decision. The assessment's risk notes — that the source serves phone numbers, personal emails, home addresses, dates of birth, marital status and family composition for 5,426 named people without authentication, and that the data-protection framing was never researched — stand unresolved.
- **Terms of use, licensing and copyright were excluded from the assessment by owner decision.** This feature is specified without any determination of what may lawfully be re-published. That is a deferred question, not a cleared one.
- **The feature is maintained by one person with no budget**, publishing under a project name rather than the owner's name.
- **Zero candidate uses beyond this option are authorised.** The assessment recorded twenty-one candidate uses; the decision authorised one option comprising five of them. Nothing in this spec covers debate text, answer text, speaker attribution, or the document-level work in the other options.

## Open Questions Carried Forward

Carried from the handoff in `.specify/assessments/indian-sansad/decision.md` as recorded open questions, per the feature description's instruction not to guess answers. None of these blocks the requirements above; each affects feasibility, validation, or external risk rather than what the feature is required to do.

1. **The Rajya Sabha member route is unknown.** This is the only carried question that limits the delivered scope. It does **not** leave FR-001 unmet: FR-001 requires the coverage statement to say Lok Sabha only until a Rajya Sabha member route is established, which a Lok Sabha-only release satisfies by declaring itself as such. What remains unfulfilled is the **owner's scope decision** that the Rajya Sabha be covered on the same calendar window as the Lok Sabha.
2. **The question-metadata route has never been retrieved directly.** The assessment cites it from a third party as having been found inside the source site's own client bundle; neither research pass fetched it first-hand.
3. **Whether member identity can be resolved within the upkeep ceiling, without ground truth.** The practitioner whose account motivates User Story 1 needed fuzzy matching and still called it "a difficult task". The assessment names this the recommendation's least defensible assumption.
4. **Which member attributes are published**, given no guardrail was adopted and the data-protection framing is untested. FR-008 makes this a required explicit decision rather than resolving it.
5. **Whether other builders would consume this rather than build their own again.** Eight independent projects have each already built their own, which is evidence of need and also of a preference for self-building.
6. **What the official Digital Sansad application offers for debates and search.** Unresolved after two research passes and not resolvable by fetching; it bears less on this feature than on the options not chosen, but it is the assessment's standing obsolescence risk.
7. **What the national open-data portal holds, in what formats, and how current.** It refused automated access during both passes.
8. **The target level for SC-009.** The owner has set no threshold for use by anyone other than the maintainer, and the assessment notes this is the demand question in another form.
9. **Whether to verify the one located newsroom analysis of parliamentary answers**, whose URL redirected to a host outside the approved set and was therefore not retrieved.
