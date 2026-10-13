"""`representations.member_name` is an FR-008 name form, mechanically. T179.

The defect this closes, in feature 001's own words (`gate-evidence.md`):

    The finding: `representations.member_name` **is** a member name form --
    inside FR-008's "name forms" and declared in the contract -- but the
    spelling `member_name` is not in `PUBLISHED_FIELDS`, which carries
    `canonical_name` and `name_variants`. So **the automated diff classifies a
    genuine FR-008 field as "not a member attribute"**, and its membership of
    the set rests on a human reading the contract. The data is correct; the
    check is weaker than it looks.

Two remedies were named there. **Renaming the published key is not available**
-- FR-140 forbids changing `data/published/`, and the key is pinned by
`tests/contract/test_constituency_reference.py` -- so the synonym is the one
that remains.

What must not happen is the synonym becoming a back door. These tests assert
both halves: that the genuine name form resolves, and that the permitted SET is
unchanged, so nothing outside FR-008 can be admitted by adding a spelling.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sansad.model.member import (
    PUBLISHED_FIELD_SYNONYMS,
    PUBLISHED_FIELDS,
    published_field_for,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CONSTITUENCIES = REPO_ROOT / "data" / "published" / "reference" / "constituencies.jsonl"

#: Principle V's excluded attributes, DERIVED FROM THE GUARD rather than typed.
#:
#: Two reasons, and the first is not subtle: a tuple of those spellings written
#: out here is a tuple of prohibited keys in a tracked file, and `make guard`
#: failed this module for exactly that -- ten violations, every one of them a
#: string literal in a test about not publishing them. The guard was right
#: about the shape and the file was wrong.
#:
#: The precedent is already in this codebase. `tools/drive_page.mjs` hit the
#: same thing with the CDP parameter named `mobile` and recorded the rule: move
#: the token out of key position rather than exempt the file.
#:
#: The second reason is better anyway. A copy of the list here could drift from
#: the guard's, and the copy that drifts is always the one nobody re-reads.
#: Reading the guard's own table means this test checks what the guard actually
#: prohibits, not what someone once believed it did.
_GUARD = REPO_ROOT / "tools" / "guard_no_raw_payloads.py"


def excluded_spellings() -> tuple[str, ...]:
    namespace: dict[str, object] = {"__file__": str(_GUARD), "__name__": "_guard_for_test"}
    exec(compile(_GUARD.read_text(encoding="utf-8"), str(_GUARD), "exec"), namespace)
    table: dict[str, tuple[str, ...]] = namespace["PROHIBITED_ATTRIBUTES"]  # type: ignore[assignment]
    return tuple(spelling for spellings in table.values() for spelling in spellings)


def test_member_name_resolves_to_the_field_it_is_a_spelling_of() -> None:
    """The defect, closed. No human reading a contract required."""
    assert published_field_for("member_name") == "canonical_name"


def test_every_field_in_the_permitted_set_resolves_to_itself() -> None:
    for field in PUBLISHED_FIELDS:
        assert published_field_for(field) == field


def test_the_synonyms_widen_no_field_set() -> None:
    """The guard against this becoming a back door.

    Every synonym must map ONTO a field already in `PUBLISHED_FIELDS`. A
    synonym pointing at something not in that tuple would be a new published
    attribute admitted by the spelling table rather than by the decision
    Principle V requires.
    """
    for spelling, field in PUBLISHED_FIELD_SYNONYMS.items():
        assert field in PUBLISHED_FIELDS, (
            f"synonym {spelling!r} maps to {field!r}, which is not in PUBLISHED_FIELDS -- "
            f"that would widen the FR-008 set without a recorded decision"
        )
        assert spelling not in PUBLISHED_FIELDS, (
            f"{spelling!r} is in both the set and the synonym table; one of them is wrong"
        )


def test_nothing_principle_v_excludes_resolves_to_anything() -> None:
    """The set is still bounded, and the synonym table did not loosen it."""
    spellings = excluded_spellings()
    assert len(spellings) > 20, "the guard's prohibited table looks empty or unreadable"
    for key in spellings:
        assert published_field_for(key) is None, (
            f"{key!r} resolves to an FR-008 field -- Principle V names it as excluded"
        )


def test_an_unknown_key_resolves_to_nothing() -> None:
    """Unknown means excluded. "The absence of a prohibition is NOT permission."""
    for key in ("", "favouriteColour", "memberName", "MEMBER_NAME", "nickname"):
        assert published_field_for(key) is None


def test_the_published_key_this_is_about_really_is_published() -> None:
    """The premise, checked rather than assumed.

    If `representations.member_name` ever stops being published, this synonym
    is dead weight and should go rather than sit there looking load-bearing.
    """
    if not CONSTITUENCIES.is_file():
        pytest.skip("data/published/ is not built")
    first = json.loads(CONSTITUENCIES.read_text(encoding="utf-8").splitlines()[0])
    representations = first.get("representations") or []
    assert representations, "the constituency set carries no representations"
    assert "member_name" in representations[0], (
        "representations no longer carry `member_name`; the synonym is now unused"
    )


def test_every_member_attribute_in_the_constituency_set_classifies(tmp_path: Path) -> None:
    """The whole point, end to end.

    Every key on a published representation either resolves to an FR-008 field
    or is a fact about the REPRESENTATION rather than about a person. Both are
    permitted; what would not be is a third category — a key that is neither,
    which is what `member_name` looked like before the synonym existed.
    """
    if not CONSTITUENCIES.is_file():
        pytest.skip("data/published/ is not built")

    #: Facts about a representation, not attributes of a person. `start_date`
    #: and `end_date` are both "not stated" in every published row.
    ABOUT_THE_REPRESENTATION = {"term_number", "start_date", "end_date"}

    unclassified: set[str] = set()
    for line in CONSTITUENCIES.read_text(encoding="utf-8").splitlines():
        for representation in json.loads(line).get("representations") or []:
            for key in representation:
                if key in ABOUT_THE_REPRESENTATION or published_field_for(key):
                    continue
                unclassified.add(key)

    assert unclassified == set(), (
        f"these published representation keys are neither an FR-008 field nor a fact "
        f"about the representation: {sorted(unclassified)}. Each is either a member "
        f"attribute outside the permitted set -- a Principle V breach -- or a spelling "
        f"the synonym table should carry."
    )
