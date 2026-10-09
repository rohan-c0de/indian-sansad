"""A resolved metadata layer over the Indian parliamentary record.

Standing constraint across every module here (Constitution Principle V):
**no raw upstream payload is ever written inside the repository tree.** Not as
a cache, not as a fixture, not as a spike artefact, not in a test. Every
fetched body is transformed in memory behind the FR-008 field allowlist
(`sansad.ingest.field_allowlist`) or written under `$SANSAD_SCRATCH`, which
`sansad.ingest.transport` asserts lies outside the repository root.
"""
