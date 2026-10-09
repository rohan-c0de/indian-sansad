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
| `question_id` | Stable identity for the question. |
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
| `ministry_id` | Stable identity. |
| `canonical_name` | One display form. |
| `name_variants` | Forms used by the source. |

**Validation rules**: ministries are reconciled by the same stability rule as members — renaming upstream MUST NOT create a second ministry identity.

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
| `known_gaps` | Sessions or dates known to be missing or incomplete. |
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
