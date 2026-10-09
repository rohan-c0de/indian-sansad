"""Identity reconciliation: name variants, ambiguity handling, assertions.

The production `approximate` tier MUST use `difflib.SequenceMatcher.ratio` on
normalised forms at APPROX_THRESHOLD = 0.90 and APPROX_MARGIN = 0.02. Those
constants were holdout-validated on 15,082 previously unseen questions and
every figure behind the owner's SC-002 decision rests on that metric. Swapping
the similarity metric re-opens SC-002 and requires a fresh holdout. See
`pyproject.toml` for the full rationale.
"""
