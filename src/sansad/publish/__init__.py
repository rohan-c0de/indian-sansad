"""Partitioned dataset output and the Coverage Statement.

Writes `data/published/`, which is git-ignored on `main` and lives only on the
rolling orphan branch `published` (owner decision 2026-10-09). The refresh
workflow force-pushes a single commit there on success and pushes nothing at
all on a failed or partial refresh, so the previous snapshot keeps being
served.
"""
