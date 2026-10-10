"""T044 -- name-form normalisation. For matching only, never for publication.

Covers the forms T004 and T012 actually observed, which is a narrower and more
defensible claim than "covers Indian name forms". What was measured, over a
250-question sample of asker name instances (`spike/route-capture.md`):

| Measure | Value |
|---|---|
| Carrying a leading honorific (`Shri`, `Smt`, `Dr`, `Prof`, …) | **369 of 376 (98.1%)** |
| Containing a comma (inverted `Surname, Given` form) | **0** |
| Containing a single-letter initial | 46 |
| Containing a `.` anywhere | 95 |
| Containing parentheses | 0 |
| Entirely upper-case | 0 |
| Non-ASCII characters | **0** |

So the honorific is the dominant problem and punctuation is the second. Note
the **zero** comma-inverted forms: `quickstart.md` scenario 1 and this project's
required fixture pair both rest on `Singh, Sunil K.`, and that shape is **not
evidenced on the question route**. Which source carries it is UNVERIFIED and
open. The comma is still handled here -- it costs nothing and the roster is the
plausible origin -- but no claim is made that the question route serves it.

**Two rules this module obeys.**

1. **Source forms are preserved exactly as written.** Nothing here mutates a
   record. `canon` returns a *comparison key*; the written form travels on to
   `ResolutionRecord.name_as_written` untouched, because an audit record that
   stored the cleaned-up version of the thing that needed matching is useless
   (FR-005).

2. **This is not transliteration** (Principle IV). No script conversion, no
   romanisation, no "equivalent spelling" table. Case folding, punctuation
   stripping, honorific removal and token ordering only. `route-capture.md`
   measured **0 non-ASCII characters** across 376 instances, so there is no
   observed case to transliterate even if the principle allowed it.

**`md` and `mohd` are deliberately NOT stripped**, carried over unchanged from
`spike/resolve_rate.py`: "they are frequently part of a given name rather than
a title, and stripping them would corrupt real names to flatter the rate."
"""

from __future__ import annotations

import re

__all__ = [
    "DELIBERATELY_NOT_STRIPPED",
    "HONORIFICS",
    "canon",
    "canon_sorted",
    "token_set",
]

#: Honorific tokens removed before comparison. Verbatim from
#: `spike/resolve_rate.py`, whose configuration was fixed before the first run
#: and holdout-validated afterwards -- so this list is carried forward rather
#: than re-derived. An honorific is not part of anyone's identity.
HONORIFICS: frozenset[str] = frozenset(
    {
        "shri", "shrimati", "shrimathi", "smt", "smti", "sri", "srimati",
        "dr", "doctor", "prof", "professor", "adv", "advocate",
        "kumari", "kum", "kunwar", "kunwari", "sardar", "shrimatiji",
        "col", "colonel", "lt", "gen", "general", "capt", "captain", "maj", "major",
        "justice", "thiru", "thirumathi", "er", "mr", "mrs", "ms", "miss",
    }
)  # fmt: skip

#: Titles that are NOT stripped, and why. Kept as a named value rather than a
#: comment so a future edit to `HONORIFICS` has to confront the decision.
DELIBERATELY_NOT_STRIPPED: tuple[str, ...] = ("md", "mohd")

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def canon(text: str) -> str:
    """The comparison key for a written name form.

    Lowercased, punctuation to spaces, honorific tokens dropped, whitespace
    collapsed. **Token order is preserved** -- reordering is what the
    `normalised-reordered` tier is for, and folding it in here would hide which
    tier did the work, which is exactly what `ResolutionRecord.method` exists
    to record.
    """
    if not text:
        return ""
    lowered = _NON_ALNUM.sub(" ", text.lower())
    tokens = [t for t in lowered.split() if t and t not in HONORIFICS]
    return " ".join(tokens)


def canon_sorted(text: str) -> str:
    """`canon` with tokens sorted -- an order-insensitive comparison key.

    This is what matches the roster's `Tatkare Sunil Dattatrey` against the
    question route's `Sunil Dattatray Tatkare` ordering, independently of the
    spelling variance between them.
    """
    return " ".join(sorted(canon(text).split()))


def token_set(text: str) -> frozenset[str]:
    """The canonical token set, for the containment tier.

    A set, not a multiset: a repeated token carries no identity information and
    a set is what `spike/resolve_rate.py` compared.
    """
    return frozenset(canon(text).split())
