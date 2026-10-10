# Indian Sansad -- maintainer-facing targets.
#
# Standing constraint, Constitution Principle V: NO RAW UPSTREAM PAYLOAD IS
# EVER WRITTEN INSIDE THE REPOSITORY TREE. Not as a cache, not as a fixture,
# not as a spike artefact, not in a test. Every fetched body is either
# transformed in memory behind the FR-008 field allowlist, or written under
# $(SANSAD_SCRATCH) -- which `make scratch` proves is outside this tree before
# any fetch target is allowed to run.

SHELL := /bin/bash
# .SHELLFLAGS is honoured only by GNU Make >= 3.82. macOS ships 3.81, which
# IGNORES IT SILENTLY -- verified: a recipe `@false; echo reached` printed
# `reached` and exited 0. So it is kept for newer make but is never relied
# on: every recipe below opens with its own `set -eu -o pipefail`. A fetch
# target that reports success after a failed step is worse than no target.
.SHELLFLAGS := -eu -o pipefail -c

PYTHON ?= python3.13
REPO_ROOT := $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))

# Scratch space for fetched bodies. TMPDIR already ends in a slash on macOS;
# fall back to /tmp/ where it is unset (most CI runners).
SANSAD_SCRATCH ?= $(or $(TMPDIR),/tmp/)sansad-scratch

.PHONY: scratch guard setup lint yamllint audit-fields \
        refresh verify-joins extract report lookup composition coverage \
        serve-local serve-local-mapping test-page validate

# --------------------------------------------------------------------------
# scratch -- create the out-of-tree scratch directory, and REFUSE to if the
#            resolved path lies inside the repository.
#
# The assertion is the point of this target, not the mkdir, and it runs BEFORE
# the mkdir -- otherwise a refusal would itself leave a directory inside the
# tree. realpath resolves symlinks (/var -> /private/var on macOS) and `..`
# segments, so neither can smuggle an in-tree path past a string comparison. The
# "/*" arm stops /tmp/scratch-elsewhere matching a repo at /tmp/scratch.
# --------------------------------------------------------------------------
scratch:
	@set -eu -o pipefail; \
	 resolved="$$($(PYTHON) -c 'import os,sys;print(os.path.realpath(sys.argv[1]))' "$(SANSAD_SCRATCH)")"; \
	 repo="$$($(PYTHON) -c 'import os,sys;print(os.path.realpath(sys.argv[1]))' "$(REPO_ROOT)")"; \
	 if [[ "$$resolved" == "$$repo" || "$$resolved" == "$$repo"/* ]]; then \
	   echo "make scratch: REFUSED."; \
	   echo "  SANSAD_SCRATCH resolves inside the repository tree:"; \
	   echo "    requested : $(SANSAD_SCRATCH)"; \
	   echo "    resolved  : $$resolved"; \
	   echo "    repo root : $$repo"; \
	   echo "  Constitution Principle V: no raw upstream payload is ever"; \
	   echo "  written inside this tree. Set SANSAD_SCRATCH outside it."; \
	   exit 1; \
	 fi; \
	 mkdir -p "$$resolved"; \
	 echo "scratch: OK -- $$resolved (outside $$repo)"

# --------------------------------------------------------------------------
# guard -- the only automated thing standing between the upstream's
#          personal-data payload and publication (quickstart.md scenario 10).
# --------------------------------------------------------------------------
guard:
	@set -eu -o pipefail; \
	 $(PYTHON) tools/guard_no_raw_payloads.py "$(REPO_ROOT)"

# --------------------------------------------------------------------------
# setup -- create the virtual environment and install the project.
#
# The venv lives at .venv/ (git-ignored). It is created with the SAME
# interpreter the measurements were taken on, and setup FAILS rather than
# falling back to another python if $(PYTHON) is missing -- a pipeline that
# silently runs on a different interpreter than the one its figures came
# from is worse than one that refuses to start.
# --------------------------------------------------------------------------
VENV := $(REPO_ROOT)/.venv
VENV_PY := $(VENV)/bin/python

setup:
	@set -eu -o pipefail; \
	 if ! command -v $(PYTHON) >/dev/null 2>&1; then \
	   echo "make setup: REFUSED -- $(PYTHON) not found on PATH."; \
	   echo "  plan.md pins Python 3.13 and every spike figure was measured"; \
	   echo "  on it. Install it rather than overriding PYTHON."; \
	   exit 1; \
	 fi; \
	 $(PYTHON) -m venv "$(VENV)"; \
	 "$(VENV_PY)" -m pip install --quiet --upgrade pip; \
	 "$(VENV_PY)" -m pip install --quiet -e '.[dev]'; \
	 echo "setup: OK -- $$("$(VENV_PY)" --version) at $(VENV)"; \
	 "$(VENV_PY)" -m pip list --format=freeze | grep -iE '^(httpx|polars|pytest|ruff)=' || true

# --------------------------------------------------------------------------
# lint -- ruff check, format verification, AND yamllint. Read-only: it
#         reports, it does not rewrite, so a lint run can never be the thing
#         that changed a file under a measurement.
#
# yamllint is part of `lint` rather than only standing alone because this is
# the aggregating check, and a lint target that passes while the workflow YAML
# is unchecked is how T058 came to record "yamllint reports 0 findings" for
# two days when the real figure was 9 (2026-10-10).
# --------------------------------------------------------------------------
lint: yamllint
	@set -eu -o pipefail; \
	 if [[ ! -x "$(VENV_PY)" ]]; then \
	   echo "make lint: no environment at $(VENV). Run 'make setup' first."; \
	   exit 1; \
	 fi; \
	 "$(VENV_PY)" -m ruff check .; \
	 "$(VENV_PY)" -m ruff format --check .

# --------------------------------------------------------------------------
# yamllint -- the YAML half of lint, against the committed .yamllint config.
#
# --strict is NOT decoration. yamllint's default exit code for a run whose
# only findings are WARNINGS is 0 -- verified 2026-10-10: a file reported
# `warning  missing document start "---"` and exited 0, and exited 2 under
# --strict. A target that reported findings and exited 0 would be the same
# hole the config was added to close, so every finding fails here.
#
# Scope is `.` and the ignore list lives in .yamllint, not in this recipe:
# the config is what the CI and a human both read, and a path list here would
# be a second definition that drifts.
# --------------------------------------------------------------------------
yamllint:
	@set -eu -o pipefail; \
	 if [[ ! -x "$(VENV_PY)" ]]; then \
	   echo "make yamllint: no environment at $(VENV). Run 'make setup' first."; \
	   exit 1; \
	 fi; \
	 "$(VENV_PY)" -m yamllint --strict .; \
	 echo "yamllint: 0 findings (--strict, config .yamllint)"

# --------------------------------------------------------------------------
# audit-fields -- T031 / quickstart.md scenario 10.
#
# Wider than `make guard`, and deliberately so: `guard` scans the committed
# tree, which is NOT the set a third party can reach. data/published/ is
# git-ignored on `main` and reaches consumers via the `published` branch, so a
# tree-only scan never looks at the actual published dataset. Principle V's
# gate names pages and derived statistics explicitly.
#
# An absent scope is reported as NOT PRESENT, never as a pass -- SC-010 cannot
# be asserted about a dataset that was never built. `make validate` passes
# --require-present, where an empty data/published/ after a refresh is itself
# a failure.
# --------------------------------------------------------------------------
audit-fields:
	@set -eu -o pipefail; \
	 $(PYTHON) tools/guard_no_raw_payloads.py "$(REPO_ROOT)" --audit-fields

# ========================================================================
# T035 -- an address for every quickstart.md entry point, from the start.
#
# Each target below is STUBBED TO FAIL LOUDLY. The point is that all twelve
# validation scenarios have a name you can type today, so a scenario cannot be
# quietly forgotten by never acquiring an entry point -- and so that nothing
# can mistake "the target does not exist" for "the scenario passes".
#
# Every stub exits NON-ZERO. A stub that exited 0 would make `make validate`
# green on a project that does nothing, which is the single most expensive
# wrong signal this Makefile could send.
#
# Written as explicit recipes rather than a $(call ...) macro: make splits
# $(call) arguments on commas, which silently truncated the scenario and task
# fields of every target whose text contained one. VERIFIED -- `make coverage`
# printed "quickstart.md:  sessions" where the scenario belonged.
# ========================================================================

# --------------------------------------------------------------------------
# refresh -- T055. One full ingestion and publish, prompting for NOTHING.
#
# "make refresh must complete without prompting for anything. A prompt is a
# failure against FR-009." So this passes --source explicitly rather than
# letting anything be inferred, and the default source is `scratch`: a command
# that reaches the upstream unless told otherwise is one that reaches it by
# accident. SOURCE=upstream is the fetching path the workflow calls.
#
# Writes data/published/ LOCALLY only -- it is git-ignored on main. Publishing
# is the scheduled workflow's job (T058).
# --------------------------------------------------------------------------
SOURCE ?= scratch
PREVIOUS ?=
# RESUME=1 reuses a COMPLETE checkpoint instead of refetching that term.
# OFF by default and never set in CI: a resumed term is older than the refresh
# date, and reusing one silently publishes stale data labelled live.
RESUME ?=

refresh: scratch
	@set -eu -o pipefail; \
	 if [[ ! -x "$(VENV_PY)" ]]; then \
	   echo "make refresh: no environment at $(VENV). Run 'make setup' first."; \
	   exit 1; \
	 fi; \
	 SANSAD_SCRATCH="$(SANSAD_SCRATCH)" "$(VENV_PY)" -m sansad.cli \
	   --source "$(SOURCE)" \
	   --published-dir "$(REPO_ROOT)/data/published" \
	   $(if $(PREVIOUS),--previous "$(PREVIOUS)",) \
	   $(if $(RESUME),--resume,)

# --------------------------------------------------------------------------
# verify-joins -- T056 / quickstart.md scenario 4 (FR-005).
#
# Recomputes nothing: it reads the published files and confirms a consumer
# could audit any join without re-deriving it.
# --------------------------------------------------------------------------
verify-joins:
	@set -eu -o pipefail; \
	 "$(VENV_PY)" tools/verify_joins.py "$(REPO_ROOT)/data/published"

# --------------------------------------------------------------------------
# extract -- T057 / quickstart.md scenario 5 (FR-007), all five axes.
#
#   make extract HOUSE=lok-sabha/17 SESSION=1
#   make extract MINISTRY=defence
#   make extract MEMBER=ls-5199
#   make extract STATE=Maharashtra
#   make extract CONSTITUENCY=Raigad
#
# Session, ministry and member each come from their own partition in ONE fetch.
# State and constituency resolve through the member reference set plus only the
# matching members' files -- the tool asserts that budget and names every file
# it opened, because a fetch count is the only way to tell "reached the subset"
# from "filtered the whole record in memory".
# --------------------------------------------------------------------------
extract:
	@set -eu -o pipefail; \
	 "$(VENV_PY)" tools/extract.py --published "$(REPO_ROOT)/data/published" \
	   $(if $(HOUSE),--house "$(HOUSE)",) \
	   $(if $(SESSION),--session "$(SESSION)",) \
	   $(if $(MINISTRY),--ministry "$(MINISTRY)",) \
	   $(if $(MEMBER),--member "$(MEMBER)",) \
	   $(if $(STATE),--state "$(STATE)",) \
	   $(if $(CONSTITUENCY),--constituency "$(CONSTITUENCY)",) \
	   $(if $(OUT),--out "$(OUT)",)

# --------------------------------------------------------------------------
# report -- T085 / quickstart.md scenario 6 (US2, FR-012, SC-007).
#
#   make report MINISTRY="JAL SHAKTI" SESSIONS=5-8 [LS_TERM=18]
#
# Prints the published aggregate's figures, an INDEPENDENT recount straight off
# `by-session/` that never touches the aggregation code, and the counting basis
# read from the published file. Exits non-zero if the two counts disagree: a
# report that printed a figure without re-deriving it would be testing nothing,
# and SC-007 is about reproducibility rather than about having a number to show.
#
# SESSIONS is session NUMBERS and covers both terms unless LS_TERM= narrows it
# -- the tool says so on its own output rather than picking a term silently.
#
# LS_TERM, not TERM: every interactive shell EXPORTS `TERM`, so a `TERM ?=`
# picks up `xterm-256color` from the environment whenever the caller does not
# pass one. MEASURED on this machine, before the rename below:
#
#   $ TERM=xterm-256color make composition
#   show_composition.py: error: argument --term: invalid int value: 'xterm-256color'
#   make: *** [composition] Error 2
#
# `make composition` carried the same collision and was left alone when this
# target was written, on the reasoning that `TERM=18` on the command line
# overrides the environment so only the no-argument case was affected.
# OWNER DECISION 2026-10-10: rename it too. One variable name for the same
# thing in both targets, and the no-argument case says what is missing instead
# of reporting the caller's terminal type as a bad integer.
# --------------------------------------------------------------------------
# Used by BOTH `report` (optional -- narrows a session range to one term) and
# `composition` (required).
LS_TERM ?=

report:
	@set -eu -o pipefail; \
	 if [[ -z "$(MINISTRY)" || -z "$(SESSIONS)" ]]; then \
	   echo "make report: MINISTRY and SESSIONS are both required."; \
	   echo "  e.g. make report MINISTRY=\"JAL SHAKTI\" SESSIONS=5-8"; \
	   exit 1; \
	 fi; \
	 "$(VENV_PY)" tools/show_report.py \
	   --ministry "$(MINISTRY)" \
	   --sessions "$(SESSIONS)" \
	   $(if $(LS_TERM),--term "$(LS_TERM)",) \
	   --published "$(REPO_ROOT)/data/published"

# --------------------------------------------------------------------------
# lookup -- T089 / quickstart.md scenario 7 (US3, SC-008).
#
#   make lookup CONSTITUENCY=Aurangabad
#   make lookup CONSTITUENCY=Aurangabad STATE=Bihar
#
# Walks the same two files the page does -- the constituency reference set,
# then the chosen members' own question files -- and never
# reference/members.jsonl. A tool that reached the answer another way would
# not be checking the route a consumer has.
#
# A NAME IS NOT AN IDENTITY. Three names in the covered window name a
# different seat in each of two states, so a bare name prints BOTH seats under
# their own states and says so; STATE= narrows it. Picking one would be wrong
# half the time and silently.
# --------------------------------------------------------------------------
STATE ?=

lookup:
	@set -eu -o pipefail; \
	 if [[ -z "$(CONSTITUENCY)" ]]; then \
	   echo "make lookup: CONSTITUENCY is required."; \
	   echo "  e.g. make lookup CONSTITUENCY=Aurangabad [STATE=Bihar]"; \
	   exit 1; \
	 fi; \
	 "$(VENV_PY)" tools/show_lookup.py \
	   --constituency "$(CONSTITUENCY)" \
	   $(if $(STATE),--state "$(STATE)",) \
	   --published "$(REPO_ROOT)/data/published"

# --------------------------------------------------------------------------
# composition -- T068 / quickstart.md scenario 8 (US4).
#
#   make composition LS_TERM=18
#
# LS_TERM, not TERM -- see the note above `report`.
#
# Reads the PUBLISHED aggregate rather than recomputing, and prints the
# reconciliation category by category -- the scenario's assertion is that the
# categories sum to the term's total membership, so the sum is written out and
# compared. A tool that printed the breakdown and left the reader to add it up
# would be testing nothing.
# --------------------------------------------------------------------------
composition:
	@set -eu -o pipefail; \
	 if [[ -z "$(LS_TERM)" ]]; then \
	   echo "make composition: LS_TERM is required."; \
	   echo "  e.g. make composition LS_TERM=18"; \
	   exit 1; \
	 fi; \
	 "$(VENV_PY)" tools/show_composition.py --term "$(LS_TERM)" \
	   --published "$(REPO_ROOT)/data/published"

# --------------------------------------------------------------------------
# coverage -- T053 / quickstart.md scenario 11 (FR-013).
#
# Prints the published Coverage Statement for every House, including the one
# with no route: "If Rajya Sabha data is absent, the statement says Lok Sabha
# only -- it must not imply coverage it does not have."
# --------------------------------------------------------------------------
coverage:
	@set -eu -o pipefail; \
	 "$(VENV_PY)" tools/show_coverage.py "$(REPO_ROOT)/data/published"

serve-local:
	@set -eu -o pipefail; \
	 $(PYTHON) tools/serve_local.py --host "$${SANSAD_HOST:-127.0.0.1}" --port "$${SANSAD_PORT:-8013}"

# --------------------------------------------------------------------------
# serve-local-mapping -- print the URL-to-file mapping and exit. Binds no
#                        port, so it is safe in a check that must not block.
# --------------------------------------------------------------------------
serve-local-mapping:
	@set -eu -o pipefail; \
	 $(PYTHON) tools/serve_local.py --print-mapping

# --------------------------------------------------------------------------
# test-page -- T082 / quickstart.md scenario 12, and the T083 measurement.
#
# Starts the static host on an EPHEMERAL port (so two runs cannot collide and
# a stale server cannot be mistaken for this one), drives the real page in
# headless Chrome with the upstream blocked at the network level, prints the
# network log summary, and measures the first-load and first-search bytes.
#
# The block is `--host-resolver-rules=MAP * ~NOTFOUND , EXCLUDE 127.0.0.1`:
# every hostname but the loopback static host is unresolvable inside that
# browser. That is stronger than blocking the upstream by name, deliberately --
# a named block would still let a request to some other host succeed and go
# unnoticed, and scenario 12's claim is that the page needs nothing but this
# project's own files.
#
# NOTHING IS INSTALLED. The driver is `tools/cdp.mjs` plus
# `tools/drive_page.mjs` over Node 22's built-in WebSocket and fetch: no
# Puppeteer, no Playwright, no package.json, no node_modules. A browser-driver
# dependency tree breaks on its own schedule, and Principle II caps upkeep at
# about 2 hours a week.
#
# SCREENS=<dir> also writes the review screenshots at 390 and 1280 CSS px,
# using CDP device-metric emulation rather than a resized window.
# --------------------------------------------------------------------------
SCREENS ?=

test-page:
	@set -eu -o pipefail; \
	 if [[ ! -d "$(REPO_ROOT)/data/published" ]]; then \
	   echo "make test-page: data/published/ is not built. Run 'make refresh' first."; \
	   exit 1; \
	 fi; \
	 command -v node >/dev/null || { echo "make test-page: Node is required."; exit 1; }; \
	 work="$$(mktemp -d)"; \
	 log="$$work/serve.log"; \
	 report="$$work/drive.json"; \
	 trap 'if [[ -n "$${pid:-}" ]]; then kill "$$pid" 2>/dev/null || true; fi; rm -rf "$$work"' EXIT; \
	 $(PYTHON) tools/serve_local.py --host 127.0.0.1 --port 0 >"$$log" 2>&1 & \
	 pid=$$!; \
	 origin=""; \
	 for _ in $$(seq 1 100); do \
	   origin="$$(sed -n 's|^serve-local: \(http://127\.0\.0\.1:[0-9]*\)/.*|\1|p' "$$log" | head -1)"; \
	   if [[ -n "$$origin" ]]; then break; fi; \
	   if ! kill -0 "$$pid" 2>/dev/null; then echo "make test-page: the static host exited:"; cat "$$log"; exit 1; fi; \
	   sleep 0.1; \
	 done; \
	 if [[ -z "$$origin" ]]; then echo "make test-page: the static host never reported a port:"; cat "$$log"; exit 1; fi; \
	 echo "make test-page: static host at $$origin (pid $$pid)"; \
	 echo ""; \
	 node tools/drive_page.mjs --origin "$$origin" --report "$$report" \
	   $(if $(SCREENS),--screens "$(SCREENS)",); \
	 echo ""; \
	 "$(VENV_PY)" tools/measure_first_load.py "$$report"

# --------------------------------------------------------------------------
# validate -- T091. quickstart.md scenarios 1-12 plus the full test suite.
#
# THIS IS THE GATE. "Passing `make validate` means every functional
# requirement with an automatable criterion is met."
#
# Four design points, each of which is the difference between a gate and a
# green light:
#
# 1. **It refuses on an unbuilt dataset.** Scenarios 4-8 and 10-12 are checks
#    on the PUBLISHED record. Run against an absent `data/published/`, the
#    tools that skip would report NOT PRESENT and the suite would report a
#    pass -- which is the one wrong signal this target must never send. So the
#    manifest is required up front, and `audit-fields` is called with
#    `--require-present` rather than bare.
#
# 2. **It runs every check even after one fails**, and prints the captured
#    output of each failure at the end. Stopping at the first failure hides
#    the rest until the next run, and a failure whose output was not captured
#    is a data point destroyed.
#
# 3. **It calls the same entry points quickstart.md tells a reader to type**
#    -- `$(MAKE) verify-joins`, not the tool behind it. A gate that reached
#    the answer by another route would not be checking the route a maintainer
#    has.
#
# 4. **It says what it does not cover, on success.** SC-003, SC-004, SC-005
#    and SC-009 are observable only in operation. A green run is not evidence
#    for any of them, and the place that claim is most likely to be made is
#    immediately after a green run.
#
# Scenario 12 runs `serve-local-mapping` (the URL-to-file mapping, which binds
# no port) and `test-page` (which starts its own host on an ephemeral port).
# `make serve-local` itself is NOT called: it blocks by design, and a target
# that waits forever is not a check.
#
# The scenario arguments are variables rather than literals so that a value
# which stops existing in the dataset is changed in ONE place. They are not
# arbitrary: each is present in the dataset built on 2026-10-10, and
# `Aurangabad` is specifically the name that denotes a different seat in two
# states, so scenario 7's two-state case is the one exercised.
# --------------------------------------------------------------------------
VALIDATE_HOUSE ?= lok-sabha/18
VALIDATE_SESSION ?= 5
VALIDATE_MINISTRY ?= JAL SHAKTI
VALIDATE_SESSIONS ?= 5-8
VALIDATE_MEMBER ?= ls-129
VALIDATE_STATE ?= Maharashtra
VALIDATE_CONSTITUENCY ?= Aurangabad
VALIDATE_LS_TERM ?= 18

validate:
	@set -u -o pipefail; \
	 if [[ ! -x "$(VENV_PY)" ]]; then \
	   echo "make validate: no environment at $(VENV). Run 'make setup' first."; \
	   exit 1; \
	 fi; \
	 if [[ ! -f "$(REPO_ROOT)/data/published/manifest.json" ]]; then \
	   echo "make validate: REFUSED -- data/published/ is not built."; \
	   echo "  Scenarios 4-8 and 10-12 are checks on the published record. Against"; \
	   echo "  an absent dataset they would report NOT PRESENT, and this target"; \
	   echo "  would report a pass on work that has not been done."; \
	   echo "  Run 'make refresh' first."; \
	   exit 1; \
	 fi; \
	 work="$$(mktemp -d)"; \
	 trap 'rm -rf "$$work"' EXIT; \
	 : >"$$work/failures"; \
	 n=0; \
	 step() { \
	   local label="$$1"; shift; \
	   n=$$((n+1)); \
	   local out="$$work/$$n.log"; \
	   if "$$@" >"$$out" 2>&1; then \
	     printf '  [PASS] %s\n' "$$label"; \
	   else \
	     printf '  [FAIL] %s\n' "$$label"; \
	     printf '%s\t%s\n' "$$label" "$$out" >>"$$work/failures"; \
	   fi; \
	 }; \
	 echo "make validate: quickstart.md scenarios 1-12, then the full test suite."; \
	 echo ""; \
	 echo "Scenarios 1-3 -- identity resolution (US1; FR-002, FR-003, FR-004)"; \
	 step "1  one member_id across both recorded name forms" \
	   "$(VENV_PY)" -m pytest tests/resolution -k variants -q; \
	 step "2  nothing silently dropped; the count is identical either side" \
	   "$(VENV_PY)" -m pytest tests/resolution -k unresolved -q; \
	 step "3  a co-asked question is ONE record carrying every asker" \
	   "$(VENV_PY)" -m pytest tests/resolution -k co_asked -q; \
	 echo ""; \
	 echo "Scenario 4 -- joins are independently verifiable (FR-005)"; \
	 step "4  every published join has a resolution record" \
	   $(MAKE) --no-print-directory verify-joins; \
	 echo ""; \
	 echo "Scenario 5 -- subsets on every axis FR-007 names (FR-007, guarantee 6)"; \
	 step "5a session -- one partition file" \
	   $(MAKE) --no-print-directory extract HOUSE="$(VALIDATE_HOUSE)" SESSION="$(VALIDATE_SESSION)"; \
	 step "5b ministry -- one partition file" \
	   $(MAKE) --no-print-directory extract MINISTRY="$(VALIDATE_MINISTRY)"; \
	 step "5c member -- one partition file" \
	   $(MAKE) --no-print-directory extract MEMBER="$(VALIDATE_MEMBER)"; \
	 step "5d state -- reference set plus the matching members' files only" \
	   $(MAKE) --no-print-directory extract STATE="$(VALIDATE_STATE)"; \
	 step "5e constituency -- reference set plus the matching members' files only" \
	   $(MAKE) --no-print-directory extract CONSTITUENCY="$(VALIDATE_CONSTITUENCY)"; \
	 echo ""; \
	 echo "Scenario 6 -- counts reproducible, basis stated (US2; FR-012, SC-007)"; \
	 step "6  the published aggregate recounted off by-session/" \
	   $(MAKE) --no-print-directory report MINISTRY="$(VALIDATE_MINISTRY)" SESSIONS="$(VALIDATE_SESSIONS)"; \
	 echo ""; \
	 echo "Scenario 7 -- the constituency entry point (US3, SC-008)"; \
	 step "7  a seat name in two states lists both, holders not merged" \
	   $(MAKE) --no-print-directory lookup CONSTITUENCY="$(VALIDATE_CONSTITUENCY)"; \
	 echo ""; \
	 echo "Scenario 8 -- composition totals reconcile (US4)"; \
	 step "8  every dimension sums to the term's total membership" \
	   $(MAKE) --no-print-directory composition LS_TERM="$(VALIDATE_LS_TERM)"; \
	 echo ""; \
	 echo "Scenario 9 -- degrade quietly, alert the maintainer (FR-010, FR-011, SC-006)"; \
	 step "9  unavailable, shape-changed and truncated upstream in turn" \
	   "$(VENV_PY)" -m pytest tests/resilience -q; \
	 echo ""; \
	 echo "Scenario 10 -- field scope is bounded (FR-008, SC-010, Principle V)"; \
	 step "10 all three scopes present and clean" \
	   "$(VENV_PY)" tools/guard_no_raw_payloads.py "$(REPO_ROOT)" --audit-fields --require-present; \
	 echo ""; \
	 echo "Scenario 11 -- coverage honesty (FR-013)"; \
	 step "11 a statement per House, Lok Sabha only while RS is absent" \
	   $(MAKE) --no-print-directory coverage; \
	 echo ""; \
	 echo "Scenario 12 -- the page runs over the published files, upstream blocked"; \
	 step "12a the URL-to-file mapping is the published-branch layout" \
	   $(MAKE) --no-print-directory serve-local-mapping; \
	 step "12b the real page in a real browser, every hostname but loopback unresolvable" \
	   $(MAKE) --no-print-directory test-page; \
	 echo ""; \
	 echo "The full test suite"; \
	 step "every test in tests/" "$(VENV_PY)" -m pytest -q; \
	 echo ""; \
	 if [[ -s "$$work/failures" ]]; then \
	   count="$$(wc -l <"$$work/failures" | tr -d ' ')"; \
	   echo "make validate: FAIL -- $$count of $$n check(s) failed."; \
	   while IFS="$$(printf '\t')" read -r label out; do \
	     echo ""; \
	     echo "=== $$label ==="; \
	     tail -40 "$$out"; \
	   done <"$$work/failures"; \
	   exit 1; \
	 fi; \
	 echo "make validate: PASS -- $$n check(s): quickstart.md scenarios 1-12 and the full test suite."; \
	 echo ""; \
	 echo "What a green run here does NOT cover (quickstart.md -> Full gate):"; \
	 echo "  SC-003  newly published material picked up with no manual step"; \
	 echo "          -- needs a SCHEDULED run nobody started"; \
	 echo "  SC-004  upkeep within about 2 hours a week"; \
	 echo "          -- needs weeks of operation to measure"; \
	 echo "  SC-005  running cost stays at zero per month"; \
	 echo "          -- needs a billing period to elapse"; \
	 echo "  SC-009  the published record is used by someone other than the maintainer"; \
	 echo "          -- needs another person"; \
	 echo "  All four are observable only in operation. This run is not evidence"; \
	 echo "  for any of them, and it does not become evidence by being green."
