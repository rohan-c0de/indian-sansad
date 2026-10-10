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

.PHONY: scratch guard setup lint audit-fields \
        refresh verify-joins extract report lookup composition coverage \
        serve-local test-page validate

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
# lint -- ruff check and format verification. Read-only: it reports, it does
#         not rewrite, so a lint run can never be the thing that changed a
#         file under a measurement.
# --------------------------------------------------------------------------
lint:
	@set -eu -o pipefail; \
	 if [[ ! -x "$(VENV_PY)" ]]; then \
	   echo "make lint: no environment at $(VENV). Run 'make setup' first."; \
	   exit 1; \
	 fi; \
	 "$(VENV_PY)" -m ruff check .; \
	 "$(VENV_PY)" -m ruff format --check .

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

refresh: scratch
	@set -eu -o pipefail; \
	 if [[ ! -x "$(VENV_PY)" ]]; then \
	   echo "make refresh: no environment at $(VENV). Run 'make setup' first."; \
	   exit 1; \
	 fi; \
	 SANSAD_SCRATCH="$(SANSAD_SCRATCH)" "$(VENV_PY)" -m sansad.cli \
	   --source "$(SOURCE)" \
	   --published-dir "$(REPO_ROOT)/data/published" \
	   $(if $(PREVIOUS),--previous "$(PREVIOUS)",)

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

report:
	@set -eu -o pipefail; \
	 echo "make report: NOT IMPLEMENTED YET."; \
	 echo "  will: produce reproducible counts carrying the FR-012 counting-basis stamp, e.g. MINISTRY=<name> SESSIONS=5-8"; \
	 echo "  quickstart.md: scenario 6 (US2, FR-012, SC-007)"; \
	 echo "  implemented by: T085; the basis stamp itself is T064"; \
	 echo "  Failing deliberately (T035): a stub that exited 0 would let"; \
	 echo "  'make validate' report success on work that has not been done."; \
	 exit 1

lookup:
	@set -eu -o pipefail; \
	 echo "make lookup: NOT IMPLEMENTED YET."; \
	 echo "  will: resolve a constituency to its members and their periods, e.g. CONSTITUENCY=<name>"; \
	 echo "  quickstart.md: scenario 7 (US3, SC-008)"; \
	 echo "  implemented by: T089"; \
	 echo "  Failing deliberately (T035): a stub that exited 0 would let"; \
	 echo "  'make validate' report success on work that has not been done."; \
	 exit 1

composition:
	@set -eu -o pipefail; \
	 echo "make composition: NOT IMPLEMENTED YET."; \
	 echo "  will: produce the composition breakdown whose totals reconcile, e.g. TERM=18"; \
	 echo "  quickstart.md: scenario 8 (US4)"; \
	 echo "  implemented by: T068"; \
	 echo "  Failing deliberately (T035): a stub that exited 0 would let"; \
	 echo "  'make validate' report success on work that has not been done."; \
	 exit 1

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
	 echo "make serve-local: NOT IMPLEMENTED YET."; \
	 echo "  will: serve web/ and data/published/ from ONE local static host, on one origin"; \
	 echo "  quickstart.md: scenario 12 (US2, US3)"; \
	 echo "  implemented by: T081"; \
	 echo "  Failing deliberately (T035): a stub that exited 0 would let"; \
	 echo "  'make validate' report success on work that has not been done."; \
	 exit 1

test-page:
	@set -eu -o pipefail; \
	 echo "make test-page: NOT IMPLEMENTED YET."; \
	 echo "  will: drive the page in a browser with the upstream blocked at the network level"; \
	 echo "  quickstart.md: scenario 12 (US2, US3)"; \
	 echo "  implemented by: T082"; \
	 echo "  Failing deliberately (T035): a stub that exited 0 would let"; \
	 echo "  'make validate' report success on work that has not been done."; \
	 exit 1

validate:
	@set -eu -o pipefail; \
	 echo "make validate: NOT IMPLEMENTED YET."; \
	 echo "  will: run scenarios 1-12 plus the full test suite. It does NOT cover SC-003, SC-004, SC-005 or SC-009 -- those are only observable in operation"; \
	 echo "  quickstart.md: all scenarios"; \
	 echo "  implemented by: T091"; \
	 echo "  Failing deliberately (T035): a stub that exited 0 would let"; \
	 echo "  'make validate' report success on work that has not been done."; \
	 exit 1
