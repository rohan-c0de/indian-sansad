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

.PHONY: scratch guard

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
