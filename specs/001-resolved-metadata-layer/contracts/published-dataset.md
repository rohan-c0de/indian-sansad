# Contract: Published Dataset

**Feature**: `specs/001-resolved-metadata-layer` | **Date**: 2026-10-09

This feature's external interface is **a published dataset**, not a service. Its consumers are third-party builders and researchers (`spec.md` User Story 1). This contract states what a consumer may rely on. Field definitions are in [data-model.md](../data-model.md) and are not repeated here.

## What is exposed

| Published set | Contract |
|---|---|
| Members | One record per member identity, partitioned by House. Carries the state and constituency that a consumer filters on to reach a member subset (FR-007). |
| Questions — by session | One record per question, partitioned by House and session (FR-007). |
| Questions — by ministry | The same question records, one file per ministry (FR-007). |
| Questions — by member | The same question records, one file per `member_id`; a co-asked question appears in each asker's file (FR-007). |
| Resolution records | One record per name form encountered, with its outcome (FR-005). |
| Ministries, Sessions, Constituencies | Reference sets, whole. A ministry record carries its current display name and any former names from confirmed rename mappings. |
| Precomputed aggregates | Counts and trends, including User Story 4's composition and subject-trend files, with the counting basis stated (FR-012). |
| Subject-search index | Published so in-browser subject search needs no server. **One file**, `search/subject-index.json`, **measured at 2,484,758 bytes (2.37 MiB)** over all 95,268 published questions, subjects only — 16,979 distinct terms, 352,735 postings; see [spike/size-budget.md](../spike/size-budget.md) → T072. It carries **no similarity grade, score or weight**: nothing in it ranks one match above another, so a consumer presenting results as "closest first" is inventing an order the data does not contain. Consumers should expect the page to fetch it lazily, only on an actual search. *(Figure corrected 2026-10-10: this row read **3,002,356 bytes (2.86 MiB)** over "95,269 questions", which was the T018 **prototype's** measurement, not the published file's. The published file is smaller because its document list is prefix-encoded, and covers one question fewer because the declared duplicate is dropped — guarantee 5.)* |
| Coverage statement | One per House, always present (FR-013). |

There is **no per-state or per-constituency question partition**. Those subsets are reached by filtering the member reference set and then taking the matching members' files — a deliberate choice, since both are member attributes and a separate partition would republish the per-member files under a key the member set already supplies.

Each set is published in both newline-delimited JSON and CSV. The two are the same records; neither is authoritative over the other.

## Where it is published

The dataset lives on the rolling orphan branch **`published`**, which GitHub Pages serves, and which every successful refresh force-pushes as a **single commit** — so its history is one commit deep at all times and a consumer cannot fetch a previous snapshot from it. `main` carries the code; `data/published/` is git-ignored there as a build output.

**The layout on that branch is** (owner decision 2026-10-10):

```
/                        the page          (from web/)
/data/published/...      the dataset       (from data/published/)
/.nojekyll               so Pages serves files whose names begin with _
```

So a published set named `reference/members.jsonl` in this contract is fetched at `/data/published/reference/members.jsonl`, relative to wherever the branch is served. **The page and the dataset are on one origin by construction** — GitHub Pages serves one site per repository — which is load-bearing rather than convenient: the upstream sends no `Access-Control-Allow-Origin` (verified first-hand, `spike/route-capture.md` T005), so a browser is refused cross-origin reads, and a dataset on a different origin from the page would hit the identical wall against this project's own files.

**This changed on 2026-10-10 and the change is breaking for anyone who had already taken the branch.** The workflow previously copied the dataset to the **branch root** — `coverage.jsonl`, `by-session/`, `reference/` directly at `/` — and published no page at all. Under the breaking-change policy below this would require announcement in the coverage statement before taking effect; it does **not**, because **the branch has never existed**: the workflow has never run, nothing has ever been published, and so no consumer can have depended on the old layout. Recorded here rather than passed over, because that will not be true of the next layout change.

`make serve-local` serves the same two paths from one local static host so that a path which resolves locally resolves as served.

## Guarantees a consumer may rely on

1. **Identity stability.** A `member_id` refers to the same person permanently. It is never reused and never changes because a name variant was added (FR-002).
2. **Nothing is silently dropped.** A question whose asker cannot be resolved is still published, carrying `resolution_status` (FR-004). A consumer filtering on `resolution_status == "resolved"` is making an explicit choice, not receiving a default.
3. **Every join is independently verifiable.** For any question-to-member join, the matching resolution record gives the name form as written and the source record reference (FR-005).
4. **Co-asked questions are not duplicated.** One question record carries all its askers (FR-003).
5. **Coverage is declared, not implied.** The coverage statement names the period, the sessions included, known gaps, the current resolution rate, and whether the data is current or last-known-good (FR-010, FR-013, SC-002). Known gaps include record-level ones: the upstream serves one record of the covered window twice, and the coverage statement declares the dropped copy rather than letting the published total differ from the upstream's own count without explanation.
6. **Subsets are addressable on every axis FR-007 names.** A consumer can take one House, one session, one ministry, one member, or the reference sets alone, without downloading everything. State and constituency subsets are reached in two fetches — the member reference set, then the matching members' files — not by taking the whole record (FR-007). Because the partitions republish the same question records under different keys, a `question_id` appearing in several files is **one** question: a consumer combining partitions must de-duplicate on `question_id` rather than sum across them. **A `question_id` is the composite `(House, session, type, quesNo)`** — `type` included, because `quesNo` is numbered per (session, type) and a starred and an unstarred question in one session share one. Corrected 2026-10-09: the earlier composite omitted `type` and collided on **7,431 of 95,269** records, so a consumer following this very instruction would have merged a starred question with an unstarred one. No dataset was published under the old composite.
7. **Freshness is stated.** Every published set carries the date it was last rebuilt (FR-016).
8. **Field scope is bounded.** No member attribute outside the published list appears, absent a recorded decision authorising it (FR-008, SC-010).
9. **No document-derived content.** Nothing in the dataset is extracted from a PDF or any other document file (FR-015). Consumers wanting debate or answer text will not find it here.

## What this contract explicitly does not promise

- **No server-side query interface.** There is no server and no search endpoint; interactive filtering happens in the visitor's browser over the published files. This follows from the zero-cost constraint (FR-014), not from oversight.
- **No completeness guarantee against the upstream.** The dataset claims only what its coverage statement claims. The upstream carries no contract, versioning or deprecation notice, so divergence is possible and is surfaced through the coverage statement rather than denied.
- **No stability of upstream-derived vocabularies.** Party, ministry and constituency names are reproduced as the source records them. Canonical forms are this feature's choice and may be revised; `member_id` and `ministry_id` will not be.

  **What `ministry_id` does and does not promise** (softened 2026-10-09, `spike/ministry-identity.md`): a `ministry_id` **never changes once assigned and is never reused**. It is **not** promised that one ministry always has exactly one id — a ministry the source renames acquires a second id until the rename is recorded as a maintainer-confirmed mapping, and mapping **keeps the older id** rather than minting a new one. Question records carry only the ministry *name*, and the upstream's own ministry code is per-term and is reused for unrelated ministries, so a rename cannot be detected automatically. The coverage statement reports how many ministry names are awaiting adjudication, so a consumer can see the size of the gap rather than infer it.
- **No Rajya Sabha coverage at first release.** Phase 0 found the candidate Rajya Sabha member route returning HTTP 403 where sibling paths return 404, cause UNVERIFIED. Until that is settled the coverage statement declares **Lok Sabha only**, which is what FR-001 requires of such a release — so this is not a shortfall against FR-001. It is a shortfall against the **owner's wider scope decision** that the Rajya Sabha be covered on the same calendar window, recorded here rather than concealed. A consumer should read the coverage statement as the authority on which Houses are present, not assume both.
- **No resolution-rate floor as a contract term.** SC-002's 95% is a target and an acknowledged invented default, not a promise to consumers. The actual rate is published so consumers can judge for themselves.

## Breaking-change policy

A change is breaking if it removes a published field, changes the meaning of `resolution_status`, or reassigns an existing `member_id`. Breaking changes are announced in the coverage statement before taking effect. Adding a field, adding a partition, or improving a canonical name is not breaking.

## Maintainer-facing signals (not part of the consumer contract)

Required by FR-011 and listed here so they are not mistaken for consumer-facing behaviour: ingestion failure, upstream shape change, resolution rate falling below target, and any transition of a question out of `resolved`. Visitors see a coherent dated record throughout (FR-010); only the maintainer is alerted.
