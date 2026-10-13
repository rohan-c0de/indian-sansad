# Contract: The Four FR-011 Maintainer Signals

**Feature**: `002-presentation-and-visualisation` | **Date**: 2026-10-10

Feature 001's FR-011 promises the maintainer four signals. Two have production callers; two do not. This contract fixes all four: trigger, severity, payload, caller.

## Status today — VERIFIED

`grep` over `src/` and `tools/`, excluding the definition module `src/sansad/signals/alerts.py`:

| Signal | Caller today | Verdict |
|---|---|---|
| `ingestion_failure` | `cli.py:302`, `ingest/questions.py:723,769` | wired |
| `upstream_shape_change` | `ingest/shape.py:149` | wired |
| `resolution_rate_below_target` | **none** | **VERIFIED BROKEN** |
| `resolved_transitions_out` | **none** | **VERIFIED BROKEN** |

Both unwired signals are fully defined, documented, and pinned by tests in `tests/unit/test_state_transitions.py` — one of which asserts that `resolved_transitions_out` **has no caller**, so that test inverts as part of this work rather than being deleted.

## The comparison source already exists

This is a smaller change than it looks. `.github/workflows/refresh.yml` already checks out the previous published snapshot before anything overwrites it, and its own comment names this exact purpose:

```yaml
# (a) Read the PREVIOUS snapshot before overwriting anything. FR-010's
# last-known-good and FR-011's signal for a question leaving `resolved`
# both need the prior record to compare against, and after the publish
# step it is gone -- the branch is one commit deep.
- name: Check out the previous published snapshot
  id: previous
  continue-on-error: true
  uses: actions/checkout@v4
  with: { ref: published, path: .previous-snapshot, fetch-depth: 1 }
```

and passes it through:

```
python -m sansad.cli --source upstream \
  --published-dir data/published --previous .previous-snapshot
```

`cli.py` consumes `previous_dir` at line ~304 via `retain_previous`. **The wiring was designed and then not done.** Both signal calls belong beside that call site, where the previous snapshot is already in hand.

`continue-on-error: true` means the snapshot may be absent — on the first run, or if the `published` branch is missing. FR-136 governs that case.

---

## 1. `ingestion_failure` — wired, unchanged

| | |
|---|---|
| Trigger | A stage of the ingest fails |
| Severity | `FAILED` |
| Payload | stage, reason (exception type), house |
| Caller | `cli.py:302`, `ingest/questions.py:723,769` |
| Change | **none** |

## 2. `upstream_shape_change` — wired, unchanged

| | |
|---|---|
| Trigger | The upstream's field-name set diverges from the recorded baseline |
| Severity | `DEGRADED` when a field went missing, `NOTICE` when one was added |
| Payload | missing names, added names, route |
| Caller | `ingest/shape.py:149` |
| Change | **none** |

The severity split is deliberate and stays: a disappeared field means a published field is now derived from nothing, while an added field is already dropped by the allowlist's excluded-by-default rule and needs a human only to decide whether it should be.

## 3. `resolution_rate_below_target` — to be wired, with a changed trigger

| | |
|---|---|
| **Trigger — NEW** | The rate **dropped against the previous publication's recorded rate**. Never an absolute threshold. |
| Severity | `NOTICE` for the automatic rate, `DEGRADED` for the published rate — the existing `is_automatic_rate` split, unchanged |
| Payload | both rates, the previous value, the target, which rate |
| Caller | `cli.py`, at the `--previous` site |
| Reads | previous `manifest.json` → `resolution_rate_automatic`, `resolution_rate_including_assertions` |

**Why the trigger changes.** The automatic rate is **0.947831** against an `sc_002_target` of **0.95** — both published on `manifest.json` and `coverage.jsonl`, with `sc_002_met_on_automatic_rate: false` and `sc_002_met_on_published_rate: true`. An absolute trigger would therefore fire on **every single run**, for a state the owner has already accepted and published. A signal that always fires carries no information and manufactures exactly the routine upkeep Principle II forbids.

So:

```
fire when   current_automatic  < previous_automatic    -> NOTICE
fire when   current_published  < previous_published    -> DEGRADED
do not fire when a rate is below target but unchanged
do not fire when a rate rose
```

The severity split survives because the two rates mean different things: the automatic rate being below target is the known and accepted state, while the published rate slipping is a regression against a criterion that is currently met.

**Acceptance (SC-021)**: a run whose automatic rate is unchanged at 94.78% raises nothing; a run whose rate has fallen against the previously published figure raises one, naming both rates.

## 4. `resolved_transitions_out` — to be wired

| | |
|---|---|
| Trigger | A question whose `resolution_status` was `resolved` in the previous publication is not `resolved` now |
| Severity | `DEGRADED` |
| Payload | **question ids only** — count, new status, ids. No name, no value. |
| Caller | `cli.py`, at the `--previous` site |
| Reads | previous `by-session/*.jsonl` → `resolution_status` per `question_id` |

The field is published per question, verified:

```json
{"question_id": "lok-sabha/17/1/starred/500", ...,
 "asking_members": ["ls-5191"], "resolution_status": "resolved", ...}
```

This is the signal most likely to be the only sign of a real problem, and its own docstring says why: it fires on a **successful** refresh — nothing failed, nothing is stale, the overall rate may even have risen — while a join a consumer already took has silently become uncertain.

The payload is question ids only, because `excluded_keys_in`'s interface rule holds across the signal surface too: report the offending path, never the value.

## No previous publication available

| | |
|---|---|
| Condition | `.previous-snapshot` absent, or carrying no `manifest.json` / `by-session/` |
| Requirement | Record **"no comparison made"**, naming which comparison was skipped and why (FR-136) |
| Forbidden | Reporting a pass. Raising a signal. Silently continuing. |

A valid first run and a broken comparison must be distinguishable in the log. `--require-present`-style strictness is *not* applied here: the first run genuinely has no previous publication, and the workflow's checkout is already `continue-on-error: true` for that reason.

## Visitors see nothing

FR-139, and FR-010 is unchanged: every one of these degrades quietly for visitors while signalling the maintainer. A signal changing what a visitor sees would be a breach of both.

## Acceptance

| Criterion | Check |
|---|---|
| SC-020 | All four signals have a production caller outside `signals/alerts.py` and outside `tests/` |
| SC-021 | Unchanged 94.78% raises nothing; a drop raises one |
| FR-134 | A seeded `resolved` → `ambiguous` transition between two snapshots raises the signal with the right ids |
| FR-136 | An absent `.previous-snapshot` records "no comparison made", not a pass |
| FR-139 | The visitor-facing record is unchanged across a run that raised a signal |

The existing assertion in `tests/unit/test_state_transitions.py` that `resolved_transitions_out` has **no** caller must be **inverted, not deleted** — the same treatment feature 001 gave the "not built yet" assertion when the search view was finally built. An inverted assertion keeps the fact under test; a deleted one lets it silently revert.
