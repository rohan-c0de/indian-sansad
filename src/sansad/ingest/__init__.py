"""Read already-structured upstream sources.

This package is the only place in the codebase permitted to touch the
upstream. Two mechanisms make that safe, and both run before any write:

- `field_allowlist` -- the FR-008 allowlist. Drops every attribute outside the
  permitted set in memory, at the ingest boundary, so an excluded attribute
  never reaches a cache, a log line, an error message or a test artefact.
- `transport` -- the non-persisting transport. Persists no raw body inside the
  repository tree; any on-disk cache is rooted at `$SANSAD_SCRATCH` with an
  assertion that the resolved path lies outside the repo root.
"""
