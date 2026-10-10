# Phase 1 Data Model: Resolved Metadata Layer

**Feature**: `specs/001-resolved-metadata-layer` | **Date**: 2026-10-09

Entities derive from `spec.md` **Key Entities**; validation rules derive from its functional requirements, cited per rule.

## Member

One person who has served during the covered period.

| Field | Notes |
|---|---|
| `member_id` | Stable internal identity. Assigned once, never reused, never derived from a name. |
| `canonical_name` | One display form chosen per member. |
| `name_variants` | Every form the source record uses for this person. |
| `house` | Lok Sabha or Rajya Sabha. |
| `party` | As recorded by the source. |
| `state` | As recorded by the source. |
| `constituency` | Lok Sabha members only; absent for Rajya Sabha. |
| `terms` | Terms served, each with its own period. |
| `sitting_status` | Sitting or former, as of the last refresh. |
| `source_record_ref` | Identifier of the upstream record this was built from. |
| `last_refreshed` | Date this member record was last rebuilt. |

**Validation rules**

- `member_id` MUST be stable across refreshes and MUST NOT change when a name variant is added (FR-002).
- Two members with identical or near-identical names MUST NOT be merged; distinctness is decided on attributes beyond the name (FR-002, Edge Cases).
- A member whose party or House changes within the covered period MUST retain one `member_id` with the change represented in `terms`, not split into two identities (Edge Cases).
- Published fields MUST be limited to those above. Any further personal attribute available upstream MUST NOT appear unless a recorded decision authorises it (FR-008, SC-010).
- Missing attributes MUST be represented as an explicit "not stated" value, never silently dropped (User Story 4 acceptance scenario 1).

## Question

One question put to a ministry.

| Field | Notes |
|---|---|
| `question_id` | Stable identity: the composite `(House, session, type, quesNo)`. **`type` is part of the identity** — `quesNo` is numbered per (session, type), so a starred and an unstarred question in one session share a `quesNo` (corrected 2026-10-09; see the validation rules). |
| `house` | Which House it was asked in. |
| `session` | Session it belongs to. |
| `date` | Date recorded by the source. |
| `type` | Question type as recorded (e.g. starred, unstarred). |
| `subject` | Subject line as recorded. |
| `ministry_id` | Ministry addressed. |
| `asking_members` | One or more `member_id` values, or empty with `resolution_status` set. |
| `resolution_status` | `resolved`, `ambiguous`, or `unresolved`. |
| `source_record_ref` | Identifier of the upstream record. |
| `last_refreshed` | Date this question record was last rebuilt. |

**Validation rules**

- A co-asked question MUST carry every asking member and MUST NOT be duplicated per asker (FR-003, US1 scenario 2).
- A question whose asker cannot be resolved MUST be retained with `resolution_status` set to `ambiguous` or `unresolved`, and MUST NOT be dropped or assigned a guessed member (FR-004, US1 scenario 3).
- A question dated outside the covered window MUST be excluded, and its exclusion reflected in the Coverage Statement rather than passing silently (FR-013).
- A question attributed to a member not sitting on its date MUST be flagged rather than silently re-attributed (Edge Cases).
- Answer text is explicitly **not** part of this entity. No document file is opened (FR-015).
- A `question_id` MUST identify exactly one question. **Corrected 2026-10-09**: the composite was `(lokNo, sessionNo, quesNo)`, on a 250-record observation that `quesNo` is unique within a session. Measured over the full 95,269-record window that is false — **7,431 records collided onto an already-used id**, because `quesNo` is numbered per (session, **type**) and `STARRED`/`UNSTARRED` are separate series. The composite now includes `type`, which leaves zero collisions apart from one byte-identical duplicate record.
- An upstream record served more than once MUST be reduced to one published question, and the drop MUST be declared in the Coverage Statement rather than passing silently (FR-013). Copies that are **not** identical MUST be refused rather than resolved by choosing one: keeping either drops a real question (FR-004) and keeping both breaks the de-duplication guarantee consumers are told to rely on (`contracts/published-dataset.md` guarantee 6).

## Resolution Record

The audit link between a written name form and the identity it resolved to. This entity exists so FR-005 is satisfiable.

| Field | Notes |
|---|---|
| `name_as_written` | The exact form found in the source. |
| `member_id` | Identity resolved to, or empty. |
| `status` | `resolved`, `ambiguous`, `unresolved`. |
| `method` | How it was resolved. One of **six** values, matching the tiers T046 implements so any join shows which tier produced it (FR-005): `exact` | `normalised` | `normalised-reordered` | `approximate` | `token-containment` | `manual-assertion`. |
| `candidates` | For `ambiguous`, the member identities that matched equally well. |
| `source_record_ref` | Where the name form was encountered. |
| `asserted_by` | `automatic` or `maintainer`, for manual corrections. |

**Validation rules**

- Every join in the published record MUST have a corresponding Resolution Record enabling independent verification (FR-005).
- A manual assertion MUST survive subsequent refreshes and MUST NOT be overwritten by automatic matching (implied by FR-009 + FR-011: unattended refresh must not undo maintainer corrections).
- `ambiguous` MUST list its candidates; an ambiguous match MUST NOT be silently collapsed to the first candidate (Edge Cases).

## Ministry

| Field | Notes |
|---|---|
| `ministry_id` | Stable identity: the slug of the **first** name under which this ministry was seen. Assigned once, never changed, never reused (owner decision 2026-10-09). |
| `canonical_name` | One display form — the current name once a rename has been mapped. |
| `name_variants` | Forms used by the source. |
| `former_names` | Names this ministry was previously seen under, from confirmed rename mappings. |

**Validation rules** — **softened 2026-10-09, and the softening is deliberate** (`spike/ministry-identity.md`):

- A `ministry_id` MUST NOT change once assigned, and MUST NOT be reused.
- **One ministry MAY carry two ids until a rename is mapped.** This is weaker than the earlier rule ("renaming upstream MUST NOT create a second ministry identity") and it replaces it, because that rule cannot be kept unaided: question records carry only the ministry **name**, and the reference set's `minCode` is per-term — 10 of 52 shared names change code between terms and 14 of 56 shared codes name a different ministry in each. Claiming the stronger rule would have meant either splitting renamed ministries while promising not to, or merging unrelated ones.
- A rename MUST be recorded by a **maintainer-confirmed** mapping in `data/assertions/ministries.json`, which **keeps the older id**, makes the new name the `canonical_name`, and moves the previous name into `former_names`. Only owner-confirmed pairs; never generated.
- A name with no mapping MUST mint its own id rather than be guessed into an existing one.
- Trivial spelling variants — case, punctuation, and a trailing plural — are resolved by **name normalisation**, not by assertion.
- The Coverage Statement MUST report how many ministry names are awaiting adjudication (FR-013). This is **not** a maintainer signal; the four signals stay four.
- `minCode` is NOT published and is NOT used for identity.

## Session

| Field | Notes |
|---|---|
| `session_id` | House plus session number. |
| `house` | Which House. |
| `number` | Session number as the House numbers it. |
| `start_date`, `end_date` | Period covered. |
| `sitting_days` | Count, where known. |

**Note**: Lok Sabha and Rajya Sabha number sessions independently; `session_id` MUST be scoped by House so the two series are never conflated (Key Entities, House).

## Constituency

| Field | Notes |
|---|---|
| `constituency_id` | Stable identity. |
| `name` | As recorded. |
| `state` | Parent state. |
| `representations` | Member and period pairs within the covered window. |

**Validation rule**: a constituency represented by different members across the two covered terms MUST list both with their periods, not merged (US3 scenario 3).

## Coverage Statement

A first-class published entity, because FR-013 makes coverage a user-visible requirement rather than metadata.

| Field | Notes |
|---|---|
| `house` | Which House this statement describes. |
| `period_start`, `period_end` | Claimed coverage window. |
| `sessions_covered` | Session identifiers included. |
| `known_gaps` | Known gaps in coverage: sessions or dates missing or incomplete, **field-level gaps** that apply to every record (question and answer text, which Principle III puts out of scope), and **record-level gaps** such as an upstream record served twice and reduced to one. Widened 2026-10-09 — the earlier wording named only sessions and dates, which `spike/route-capture.md` had already recorded as too narrow for the text gap. |
| `resolution_rate` | Share of questions resolved to exactly one member. |
| `last_refreshed` | Date of last successful refresh. |
| `last_known_good` | Whether the published record is current or being served from the last good state (FR-010). |

**Validation rules**

- `resolution_rate` MUST be published, not merely computed, so SC-002 is externally checkable.
- When a refresh fails, `last_known_good` MUST indicate it and the record MUST remain coherent and dated rather than empty or partial (FR-010).
- If Rajya Sabha material proves unobtainable, the Coverage Statement MUST say so explicitly rather than implying both Houses are covered (Edge Cases; Phase 0 route finding).

## Relationships

- `Question.asking_members` → `Member.member_id` (many-to-many; empty permitted with `resolution_status`).
- `Question.ministry_id` → `Ministry.ministry_id` (many-to-one).
- `Question.session` → `Session.session_id` (many-to-one, House-scoped).
- `Member.constituency` → `Constituency.constituency_id` (Lok Sabha only).
- `ResolutionRecord.member_id` → `Member.member_id` (many-to-one, nullable).
- `CoverageStatement.house` → `House` (one statement per House).

## State Transitions

`Question.resolution_status` is the only stateful field:

```
unresolved ──automatic match──▶ resolved
unresolved ──several equal matches──▶ ambiguous
ambiguous  ──maintainer assertion──▶ resolved
resolved   ──upstream name change──▶ ambiguous   (re-resolution needed; MUST notify, FR-011)
```

A transition out of `resolved` MUST raise a maintainer signal, because it means a previously published join has become uncertain.
