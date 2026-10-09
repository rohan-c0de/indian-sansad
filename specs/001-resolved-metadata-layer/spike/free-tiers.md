# Spike item 4 — free tiers, named with their behaviour at the limit

**Tasks**: T007 (enumerate and choose a CI provider) · T008 (the chosen CI provider's figures)
· T015 (the static host's figures)
**Date retrieved for every figure below**: **2026-10-09**

**Why this file is shaped this way.** Constitution Principle I requires a plan to "name the free
tier each component lands on" and "state what happens when that tier's limit is reached", and the
Cost gate is passed by evidence rather than assertion. So every number here is quoted from the
provider's own current published page, with the URL and the retrieval date, and a figure that is
**not** published is recorded as not published rather than inferred.

---

# T007 — candidate free CI providers offering scheduled jobs, and the choice

## The bar a candidate has to clear

From Principle I and FR-014, three disqualifiers, all of which T007 names:

1. **No trial.** "A free trial, promotional credit, or anything that becomes chargeable later is
   a paid service."
2. **No free tier of a plan that becomes chargeable.** An automatic overage charge is a paid
   service even if the amount is small — "Every design that incurs recurring cost is
   non-compliant regardless of how small the amount is."
3. **Scheduled jobs must be supported**, because FR-009 requires detection and processing of new
   material without a manual step. A CI provider without a scheduler cannot deliver FR-009 at all.

And one that comes from T008 rather than from the constitution directly: **the behaviour at each
limit must be documented by the provider**. A gate "passed by evidence" cannot be passed against
a provider that does not publish what happens when you hit its ceiling — the honest verdict there
is "unknown", and unknown is not compliant.

## Candidates

| Provider | Scheduled jobs | Free allowance | Behaviour at the limit | Verdict |
|---|---|---|---|---|
| **GitHub Actions** (public repo, standard GitHub-hosted runners) | **Yes** — `schedule` with cron | **Free, unmetered** for public repositories | No metered usage exists to exceed; documented separately for private repos (see T008) | **CHOSEN** |
| GitLab CI/CD (GitLab.com Free) | Yes — pipeline schedules | "Free tier namespaces receive 400 compute minutes per month." | **Not documented on the compute-minutes page.** The page says only that "enforcement measures" apply, deferring detail to another section, and that "You can purchase additional compute minutes if you need more." | **Rejected** — the limit behaviour is not published where the limit is published, so Principle I's "state what happens when that tier's limit is reached" cannot be evidenced. Not rejected for being insufficient: 400 min/month would in fact be ample. |
| CircleCI (Free plan) | **Not documented on the pricing page** | "30,000 free credits/month" / "Up to 6,000 build minutes" on a small Docker resource class; "30x concurrency" | **Not documented on the pricing page.** It states only that "Credits on the Free plan expire after a month and do not roll over." | **Rejected** — neither scheduled-job inclusion nor the behaviour at exhaustion is published on the pricing page. Two unknowns on the two questions that decide the choice. |
| Azure Pipelines (public projects) | Yes | Free grant for public projects | Grant for public projects has required a manual request to Microsoft since 2021 | **Rejected** — a tier obtained by application is not a tier the project can rely on, and the dependency is on a human decision at the provider. |
| Self-hosted runner on a free compute tier | Yes | Depends entirely on the host | Deferred to that host | **Rejected** — it moves the Principle I question to a second provider instead of answering it, and adds a machine to maintain against the 2h/week ceiling. |

**Honesty about this table's depth**: GitHub Actions, GitLab and CircleCI were checked against
their own current published pages, quoted above and in T008. The Azure Pipelines and self-hosted
rows are **reasoned rejections, not page-verified ones** — they are rejected on grounds that do
not depend on a number, so no figure is quoted and none should be read into them.

## Choice: GitHub Actions, on a public repository, standard GitHub-hosted runners

Three reasons, in the order that actually decided it:

1. **There is no meter to exceed.** For public repositories GitHub Actions is free outright
   rather than free up to a quota. That is a materially stronger Principle I position than a
   generous quota, because no usage growth can ever cross a boundary into charging.
2. **Every figure T008 asks for is published**, including the two that bite (job duration, and
   schedule disabling on inactivity). GitLab and CircleCI each left a required figure unpublished.
3. **The static host question answers itself.** GitHub Pages serves the published dataset and
   `web/` from one origin on the same free footing — which T015 shows is not a convenience but
   the condition that makes the reader page possible, given the upstream sends no
   `Access-Control-Allow-Origin` (verified in `route-capture.md` T005).

**What this choice costs, recorded rather than buried**: it puts CI, hosting and source control
with one provider, so a single account action — suspension, policy change, a repository made
private — takes out the refresh and the published site together. The project accepts that
concentration because the alternative under Principle I is a second free tier with its own
unpublished limit behaviour, which trades a concentration risk for an unmeasurable one.

**Public repository is a requirement of this choice, not an incidental.** On a private
repository the free allowance is metered (T008), and the published dataset is meant to be
publicly consumable anyway (FR-006).

---

# T008 — GitHub Actions free tier, figure by figure

Every row is quoted from a GitHub-published page, with the URL and the retrieval date.

## Scheduled-job support

| | |
|---|---|
| **Supported** | Yes, via the `schedule` event with cron syntax. |
| **Shortest interval** | *"The shortest interval you can run scheduled workflows is once every 5 minutes."* |
| **Branch restriction** | *"Scheduled workflows will only run on the default branch."* |
| Source | `https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows` — retrieved **2026-10-09** |

## Minutes or runs per month

| | |
|---|---|
| **Public repository** | *"GitHub Actions usage is **free** for **self-hosted runners** and for **public repositories** that use standard GitHub-hosted runners."* — no monthly minute allowance applies, because usage is not metered. |
| **Private repository, Free plan** (not what this project uses; recorded for completeness) | 2,000 minutes per month. |
| Source | `https://docs.github.com/en/billing/concepts/product-billing/github-actions` — retrieved **2026-10-09** |

## Maximum single job duration

| | |
|---|---|
| **Per job, GitHub-hosted runner** | *"Each job in a workflow can run for up to 6 hours of execution time."* |
| **Behaviour at that limit** | *"the job is terminated and fails."* |
| **Per workflow run** | 35 days maximum; *"If a workflow run reaches this limit, the workflow run is cancelled."* |
| Source | `https://docs.github.com/en/actions/reference/limits` — retrieved **2026-10-09** |

**Sized against measured reality.** `route-capture.md` T005 measured the member roster at
**46.5 s** for one 5.0 MiB response, and the question route at **≈29 ms per record**. The covered
window is **95,269 questions**, so a full sequential ingest is on the order of
95,269 × 0.029 s ≈ **46 minutes**, plus the roster. That fits inside the 6-hour job ceiling with
room to spare, but it is **not** comfortable in the way "~10^5 records" made it sound: it is
roughly a seventh of the ceiling for one full refresh, on a provider whose own docs say schedules
may be delayed. The incremental refresh FR-009 actually relies on is far smaller. A *full*
re-ingest is a once-in-a-while operation, and if it ever stops fitting, Principle I's remedy
applies — reduce what is fetched, not buy a bigger runner.

## Concurrency

| | |
|---|---|
| **Free plan, standard GitHub-hosted runners** | 20 total concurrent jobs. |
| **Job matrix ceiling** | *"A job matrix can generate a maximum of 256 jobs per workflow run."* |
| **Workflow trigger rate** | 1,500 events / 10 seconds / repository. |
| **Queue ceiling** | 500 workflow runs / 10 seconds before blocking. |
| Source | `https://docs.github.com/en/actions/reference/limits` — retrieved **2026-10-09** |

This project needs **one** scheduled job. Concurrency is not a constraint and is recorded only
because T008 asks for it.

## Whether schedules are disabled on repository inactivity — **YES, and this is the finding**

| | |
|---|---|
| **Published wording** | *"In a public repository, scheduled workflows are automatically disabled when no repository activity has occurred in 60 days."* |
| Source | `https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows` — retrieved **2026-10-09** |

**This is a direct, specific threat to FR-009, and it is worse on this project than on most.**

FR-009 requires newly published material to be "detected and processed without a manual step",
and Principle II forbids any capability whose normal operation depends on the maintainer acting
on a schedule. A scheduler that switches itself off after 60 quiet days is exactly such a
dependency — it would need the maintainer to notice and re-enable it.

The trap is specific: **the refresh only counts as "repository activity" if it commits
something.** Indian parliamentary sessions have long recesses. `route-capture.md` measured the
18th Lok Sabha's eight sessions at 7, 15, 20, 27, 21, 15, 28 and 0 sitting days — a gap of more
than 60 days between sessions is entirely ordinary. A refresh that correctly finds no new
questions and commits nothing is **indistinguishable from inactivity** to this rule. So the
most likely way this project's refresh dies is: Parliament goes into recess, the pipeline
correctly does nothing for 60 days, GitHub disables the schedule, and the next session is missed
in silence.

**Mitigation, recorded here as a Phase 3 requirement rather than fixed now** (Phase 2 measures;
it does not build the pipeline): the refresh must produce a committed change on **every** run,
even a no-op one — a refresh timestamp in the coverage statement is the natural candidate, since
FR-016 already requires every published set to carry the date it was last rebuilt. That turns
"last_refreshed changed" into the activity heartbeat and costs nothing extra. It must be a
**commit**, not merely a workflow run, because the published wording is about repository
activity. Whether a workflow run alone counts is **UNVERIFIED** — the docs say "repository
activity" without enumerating it, and this project should not bet FR-009 on a reading of an
ambiguous phrase when a committed timestamp settles it outright.

## Behaviour at each limit — the Principle I column

| Limit | Documented behaviour | Overage charge? |
|---|---|---|
| Public-repo Actions usage | No meter exists | **No** |
| Job duration (6 h) | *"the job is terminated and fails."* | **No** — hard stop |
| Workflow run (35 days) | *"the workflow run is cancelled."* | **No** — hard stop |
| Concurrency (20) | Jobs queue | **No** |
| Queue rate (500 runs / 10 s) | Blocking | **No** |
| 60-day inactivity | Schedule silently disabled | **No** — but a **silent functional failure**, which Principle II treats as a breach in its own right: "Silence toward the maintainer and a wrong answer toward visitors are both breaches." |
| Private-repo minutes (2,000/mo, **not used here**) | *"If your account does not have a valid payment method on file, usage is blocked once you use up your quota."* With a payment method: *"You pay for any additional use above your quota."* | **Conditional** — hard block without a payment method on file, charged with one |

**No overage charge applies to the configuration this project uses**, so T008's disqualification
clause is not triggered and there is no need to return to T007.

**One qualification stated rather than glossed.** The private-repository row shows that
GitHub's billing model *does* charge above quota when a payment method is present. This project
is safe because public-repository usage is unmetered — not because the account is configured
safely. **If this repository were ever made private, the project would move onto a metered tier
whose overage behaviour depends on account billing state.** That is a Principle I exposure
controlled by a repository setting, so "keep the repository public" is a cost constraint here,
not just a publishing preference.

## What T008 does not establish

- **Nothing about the 60-day rule has been observed**, only read. It is quoted from GitHub's
  documentation, which is the evidence T008 asks for, but no 60-day silence has been tested.
  Verdict: **documented, not demonstrated.**
- **The ingest duration above is arithmetic from measured per-record cost**, not a timed full
  run. 46 minutes is a projection from 29 ms/record × 95,269 records. No full ingest has been
  executed. Verdict: **UNVERIFIED projection**, and T010 measures only reachability, not duration.
