# Publish rehearsal — the three steps that had never run

**Date**: 2026-10-10. **Machine**: this laptop (arm64 macOS, git 2.50.1, GNU
bash 3.2.57). **Not a GitHub runner.**

## Why

GitHub Actions run #1 on `main` (44m 25s) reached the end of a 42-minute live
refresh and then failed in 0s on `make verify-joins`:

```
/home/runner/work/indian-sansad/indian-sansad/.venv/bin/python: No such file or directory
make: *** [verify-joins] Error 127
```

Because that step failed, **`Publish to the rolling orphan branch` was skipped**
— as were the parts of `Keep-alive commit to main` and `Report the refresh
outcome` that matter. So the publish mechanism, the keep-alive push and the
report had **never executed**, on a runner or anywhere else, and each attempt to
find out on the real workflow costs about 45 minutes of upstream fetching.
This rehearsal buys those three steps a verdict without a 45-minute run.

## Method

The step scripts are **extracted from `.github/workflows/refresh.yml`**, never
retyped — the same rule `tests/unit/test_published_branch_layout.py` already
follows for the layout block. A rehearsal of a reimplementation would prove
something about the reimplementation.

| Thing CI provides | Stand-in here |
| --- | --- |
| `origin` on github.com | a local `--bare` repository, seeded with `main` from this checkout |
| a fresh `actions/checkout` per run | a fresh `git clone` of that bare repository per run |
| `data/published/` built by the Refresh step | the real T059 output hard-linked in: **278,684,386 bytes, 1,790 files** |
| `GITHUB_WORKSPACE`, `RUNNER_TEMP` | set to the clone and a scratch dir |
| no user git config | `HOME` pointed at an empty directory |
| `${{ steps.*.outcome }}`, `${{ github.run_id }}` | **substituted by hand** before the shell sees them |

Harness: `rehearse.sh` / `rehearse2.sh` / `rehearse3.sh`, written to the session
scratchpad, not committed — they are a measurement instrument, not project code.

## What this does NOT establish

- **Nothing here ran on a GitHub-hosted runner.** Local `/bin/bash` 3.2 and BSD
  `cp`; the runner is `ubuntu-24.04` with GNU coreutils.
- **GitHub Pages serving the `published` branch is still UNVERIFIED.** This
  proves the branch is produced with the right shape, not that Pages serves it.
- The `${{ }}` expressions were substituted, so the runner's own expansion of
  them is still UNVERIFIED.
- The push went to a local bare repository, so nothing here tests GitHub's
  refusal rules, size limits, or `contents: write` actually being sufficient.

## Publish — VERIFIED WORKING, twice

### Run 1 — no `published` branch on origin yet (the real first-run case)

```
origin refs before: [refs/heads/main ]
Preparing worktree (detached HEAD 2d34e79)
HEAD is now at 2d34e79 Prove the page in a browser and measure the real first load (T082-T085)
Switched to a new branch 'published'
layout: copied web/ to the branch root
staged     1804 file(s)
 * [new branch]      published -> published
published: force-pushed a single commit to `published`

real	0m11.678s
```

Read back out of the bare repository:

```
commit  e67e008f02fb9e265d86aa635c3eaa8f5ad96fa0
parents []
author  Indian Sansad Maintainer <noreply@users.noreply.github.com>
subject Published dataset 2026-10-10T18:06:22Z
--- commit count on published ---
1
--- expected paths ---
  PRESENT  data/published/manifest.json   (manifest)
  PRESENT  data/published/coverage.jsonl   (coverage)
  PRESENT  data/published/resolution-records.jsonl   (resolution)
  PRESENT  index.html   (page)
  PRESENT  style.css   (page-css)
  PRESENT  app.js   (page-js)
  PRESENT  lib/fetch.js   (page-lib)
  PRESENT  LICENSE   (licence)
  PRESENT  DATA-LICENSE.md   (data-licence)
  PRESENT  .nojekyll   (nojekyll)
--- must NOT be at the root (the layout that 404'd T076) ---
  absent   manifest.json
  absent   coverage.jsonl
  absent   by-session
--- totals ---
  tracked files:     1804
  top-level entries: .nojekyll DATA-LICENSE.md LICENSE app.js data index.html lib style.css
  data/published/ files: 1790
```

`parents []` is the orphan assertion: one commit, no history. 1,804 tracked
files = 1,790 dataset + 11 page files + `LICENSE` + `DATA-LICENSE.md` +
`.nojekyll`. The three "absent" lines are the layout defect that review caught
and this now pins at the branch, not just at the copy block.

### Run 2 — force-push over an existing `published`

A second fresh clone, as a second CI run would be:

```
origin published before: e67e008f02fb9e265d86aa635c3eaa8f5ad96fa0
Switched to a new branch 'published'
layout: copied web/ to the branch root
staged     1804 file(s)
 + e67e008...f5203b5 published -> published (forced update)
published: force-pushed a single commit to `published`

real	0m3.439s
```

```
run1 published = e67e008f02fb9e265d86aa635c3eaa8f5ad96fa0
run2 published = f5203b5068047b549920aef5997704c719dcb556
VERDICT: the branch was replaced, not appended to
reachable from run2's published: 1 commit(s)
is run1's commit still reachable? no
```

**This is the size bound working.** The branch is one commit deep after the
second publish, not two — which is the whole reason the dataset lives here
rather than on `main`.

`origin.git` after both: **62M** (`du -sh`) for a 278 MB working tree, twice
pushed.

**A second publish in the SAME checkout would fail**, at
`git checkout --orphan published`, because that local branch already exists. It
is not a CI case — every run is a fresh checkout, and the previous snapshot is
read into `.previous-snapshot/` as its own separate repository — but it is why
the rehearsal clones again rather than re-running in place.

## Keep-alive — VERIFIED WORKING, both paths

### Case A — clean push, run in the clone the publish step had just used

Deliberately not a fresh clone: this is the state CI is in when the keep-alive
runs, with the publish step's linked worktree still registered.

```
HEAD in clone2: main (worktrees: 2)
   2d34e79..00baa5a  HEAD -> main
```

The file, read back out of origin, and parsed:

```
{
  "last_attempted": "2026-10-10T18:06:33Z",
  "refresh_outcome": "success",
  "previous_snapshot_checkout": "failure",
  "run_id": "19999999999",
  "note": "Keep-alive against the 60-day scheduled-workflow disable rule.",
  "why_main": "Whether a push to a non-default branch counts as",
  "why_main_cont": "repository activity is UNVERIFIED; FR-009 does not rest on it."
}
valid JSON, 7 keys: last_attempted, refresh_outcome, previous_snapshot_checkout, run_id, note, why_main, why_main_cont
```

### Case B — `main` moved during the run, so the push is rejected

A 45-minute run means `main` may well have moved. A third party pushed to the
bare repository after the clone was taken:

```
origin/main moved to 3af52d9 while clone4 sat at 52d1ab6
 ! [rejected]        HEAD -> main (fetch first)
error: failed to push some refs to '.../origin.git'
keep-alive push rejected -- main moved during the run; rebasing once
   52d1ab6..3af52d9  main       -> origin/main
Rebasing (1/1)Successfully rebased and updated refs/heads/main.
   3af52d9..cc130ac  HEAD -> main
```

```
  cc130ac Indian Sansad Maintainer: Refresh keep-alive 2026-10-10T18:07:14Z [skip ci]
  3af52d9 Someone: Second unrelated commit, pushed mid-refresh
  52d1ab6 Someone: Unrelated commit pushed while the refresh was running
  the mid-refresh commit SURVIVED -- rebased onto, not force-pushed away
  is it still an ancestor of main? YES
```

**The thing that mattered**: the mid-refresh commit is still an ancestor of
`main`. The step's comment says "NEVER --force ... discarding someone's commit
costs something that cannot be recovered"; that is now observed, not just
intended.

### A finding about the "no change to commit" arm

Case B was run twice. **The first attempt never reached the push at all**:

```
nothing to commit, working tree clean
no change to commit
```

Cause: the harness substituted the **same** `run_id` into both cases, and the
two runs landed in the same second, so `refresh.json` came out byte-identical
to the one already on `main` and the step's
`|| { echo "no change to commit"; exit 0; }` arm fired. A keep-alive that
commits nothing records no repository activity — which is exactly the failure
the step exists to prevent.

**It cannot happen in CI**: `github.run_id` is unique per run, so the file
always differs. The arm is unreachable there. Recorded because it looked like a
defect for several minutes and the next person should not have to re-derive
that it is not one. Case B was then re-run with a distinct `run_id`, which is
the output above.

## Report — VERIFIED WORKING, both paths

```
############ REPORT -- success path ############
refresh outcome: success
exit 0 (as a green run should)

############ REPORT -- failure path ############
refresh outcome: failure
::error::Refresh failed. Nothing was pushed to `published`;
::error::the previous snapshot keeps being served (FR-010).
exit 1 (non-zero is the delivery mechanism)
```

## One hazard flagged and NOT changed

The publish step's staging assertion is a pipeline under `pipefail`:

```sh
git diff --cached --name-only -- data/published/manifest.json \
  | grep -qx 'data/published/manifest.json' \
  || { echo "::error::data/published/ was not staged -- refusing to publish"; exit 1; }
```

`grep -q` exits on its first match and closes the pipe. If the left-hand command
is still writing, it takes SIGPIPE, and `pipefail` then reports the whole
pipeline as failed **even though grep matched**. MEASURED, in this rehearsal's
own harness, on the analogous `git log --format='%s' main | grep -qxF ...`:

```
pipestatus=141 0
```

— grep succeeded (0), git was killed by SIGPIPE (141), and the pipeline
reported failure. In the harness that produced a false `NO -- DATA LOSS` line
against a `main` that had in fact kept the commit.

**The workflow's instance is safe as written, and was left alone.** Its pathspec
limits the output to a single line: `grep` cannot match before that line has
been written, and there is no subsequent write to take the signal. Both publish
runs above passed the assertion. Recorded, not fixed — changing working code on
a theory is how a cargo-cult fix gets in. The hazard is real for any future
`… | grep -q …` in this file whose left side emits more than it needs to.

## Verdicts

| Step | Before | Now |
| --- | --- | --- |
| Publish, first run (no branch) | NOT RUN | VERIFIED WORKING locally |
| Publish, force-push over existing | NOT RUN | VERIFIED WORKING locally |
| Publish leaves one orphan commit | NOT RUN | VERIFIED WORKING locally |
| Keep-alive, clean push | NOT RUN | VERIFIED WORKING locally |
| Keep-alive, rejected → rebase once | NOT RUN | VERIFIED WORKING locally |
| Report, success and failure | NOT RUN | VERIFIED WORKING locally |
| Pages serves the `published` branch | UNVERIFIED | UNVERIFIED |
| Any of it on a GitHub runner | UNVERIFIED | UNVERIFIED |
