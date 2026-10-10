"""T041 -- the FR-008 field allowlist, over Principle V's whole excluded list.

> an upstream record carrying every excluded attribute from Principle V passes
> through T029 with all of them absent from the output, and an unrecognised new
> field is excluded by default

**This test names no excluded spelling in its own source, and that is
deliberate.** The spellings are read at run time from
`tools/guard_no_raw_payloads.py`, which is where Principle V's list is already
maintained. Three reasons, in order of weight:

1. `tools/guard_no_raw_payloads.py` scans this file. A test that spelled the
   prohibited field names out would trip the guard, and the fix would be an
   exemption -- "a guard you have to exempt your own code from is a guard with
   a hole in it" (`spike/fetch_slice.py`).
2. The list cannot be complete. The upstream carries no contract, versioning or
   deprecation notice, so a future spelling is unknowable and the guard's list
   widens "whenever a new spelling is observed". Reading it means this test
   widens with it instead of drifting behind it.
3. Two copies of a prohibition disagree eventually, and the copy that is wrong
   is the one nobody is looking at.

The cost, stated rather than hidden: this test is only as complete as the
guard's list. Neither is a proof that the tree is clean -- the guard says so
itself ("A pass by this guard is evidence that these spellings are absent --
not that the tree is clean").
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from sansad.ingest.field_allowlist import (
    EXCLUDED_EXAMPLES,
    PERMITTED_ATTRIBUTES,
    excluded_keys_in,
    filter_record,
    is_permitted,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_guard():
    """Import the guard by path -- `tools/` is not a package, by design."""
    path = REPO_ROOT / "tools" / "guard_no_raw_payloads.py"
    spec = importlib.util.spec_from_file_location("sansad_guard_under_test", path)
    assert spec and spec.loader, path
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def prohibited_spellings() -> dict[str, tuple[str, ...]]:
    """Principle V's attributes, each with the spellings the guard knows."""
    guard = _load_guard()
    return dict(guard.PROHIBITED_ATTRIBUTES)


def test_the_guards_attribute_list_is_principle_vs_list(prohibited_spellings):
    """The two modules must be talking about the same eight attributes.

    `EXCLUDED_EXAMPLES` in the allowlist and `PROHIBITED_ATTRIBUTES` in the
    guard are independently maintained. If they diverge, one of them is quietly
    no longer about Principle V.
    """
    assert set(prohibited_spellings) == set(EXCLUDED_EXAMPLES), (
        "the guard and the allowlist disagree about Principle V's excluded set: "
        f"guard-only={sorted(set(prohibited_spellings) - set(EXCLUDED_EXAMPLES))}, "
        f"allowlist-only={sorted(set(EXCLUDED_EXAMPLES) - set(prohibited_spellings))}"
    )


def test_every_excluded_spelling_is_refused_by_the_allowlist(prohibited_spellings):
    """Each spelling, one at a time, so a failure names the offender."""
    admitted: list[tuple[str, str]] = []
    for attribute, spellings in prohibited_spellings.items():
        for spelling in spellings:
            if is_permitted(spelling):
                admitted.append((attribute, spelling))
    assert not admitted, f"the allowlist admits prohibited spelling(s): {admitted}"


def test_a_record_carrying_every_excluded_attribute_loses_all_of_them(prohibited_spellings):
    """The whole excluded list on one record, as the ingest boundary sees it.

    Values are placeholders generated here. No value from any real person
    appears in this file or in this suite.
    """
    record: dict[str, object] = {
        "memberId": "fx-9001",
        "memberName": "Placeholder Name",
        "party": "Party Z",
        "state": "State Nine",
        "constituency": "Constituency Omega",
        "house": "Lok Sabha",
        "term": 18,
        "sittingStatus": "sitting",
    }
    for spellings in prohibited_spellings.values():
        for spelling in spellings:
            record[spelling] = "PLACEHOLDER"

    filtered = filter_record(record)

    survivors = [k for k in filtered if not is_permitted(k)]
    assert not survivors, f"excluded attribute(s) survived the allowlist: {survivors}"

    for spellings in prohibited_spellings.values():
        for spelling in spellings:
            assert spelling not in filtered, spelling

    # The permitted attributes are all still there -- a filter that dropped
    # everything would pass the assertions above and publish nothing.
    assert set(filtered) == {
        "memberId",
        "memberName",
        "party",
        "state",
        "constituency",
        "house",
        "term",
        "sittingStatus",
    }


def test_excluded_keys_in_reports_names_and_never_values(prohibited_spellings):
    """ "it prints the offending path and key, never the value"."""
    one_spelling = next(iter(next(iter(prohibited_spellings.values()))))
    record = {"memberName": "Placeholder Name", one_spelling: "SECRET-PLACEHOLDER-VALUE"}

    reported = excluded_keys_in(record)

    assert reported == (one_spelling,)
    assert "SECRET-PLACEHOLDER-VALUE" not in repr(reported)


def test_an_unrecognised_new_field_is_excluded_by_default():
    """ "The absence of a prohibition is NOT permission."

    The field invented here resembles nothing in the permitted set and nothing
    in the guard's list. It must be dropped on the strength of being unknown
    alone, because the opposite default would let the upstream add an attribute
    and have this project start publishing it with no code change and no
    decision.
    """
    record = {
        "memberName": "Placeholder Name",
        "somethingTheUpstreamAddedOnTuesday": "PLACEHOLDER",
        "nameOfSomethingUnforeseen": "PLACEHOLDER",
    }

    filtered = filter_record(record)

    assert set(filtered) == {"memberName"}
    assert is_permitted("somethingTheUpstreamAddedOnTuesday") is False
    # ...including a field whose name merely *contains* a permitted word. A
    # pattern match on `*name*` would admit this one.
    assert is_permitted("nameOfSomethingUnforeseen") is False


def test_nested_structures_are_filtered_too(prohibited_spellings):
    """ "an excluded attribute one level down is still published if its parent is"."""
    one_spelling = next(iter(next(iter(prohibited_spellings.values()))))
    record = {
        "memberName": "Placeholder Name",
        "terms": [
            {"term": 17, "party": "Party Y", one_spelling: "PLACEHOLDER"},
            {"term": 18, "party": "Party Z"},
        ],
    }

    filtered = filter_record(record)

    assert [set(entry) for entry in filtered["terms"]] == [{"term", "party"}, {"term", "party"}]


def test_the_permitted_set_is_the_seven_principle_v_classes():
    """A change to this tuple is a change to what this project publishes about
    5,426 named people, and it should fail a test rather than pass review."""
    assert PERMITTED_ATTRIBUTES == (
        "name forms",
        "party",
        "state",
        "constituency",
        "House",
        "term",
        "sitting status",
    )


def test_the_two_captured_routes_fields_survive_the_allowlist():
    """The allowlist must admit the fields the pipeline actually needs.

    An allowlist that drops `member` from the question route, or the roster's
    name-form fields, is not conservative -- it silently empties User Story 1.
    These spellings come from `spike/route-capture.md` (the question route's 17
    observed field names) and `spike/fetch_slice.py` (the roster's recorded
    allowlist), and every one of them sits inside a Principle V class.
    """
    question_route_needed = (
        "quesNo",
        "lokNo",
        "sessionNo",
        "date",
        "type",
        "subjects",
        "ministry",
        "member",
    )
    roster_needed = (
        "mpsno",
        "initial",
        "firstName",
        "lastName",
        "mpFirstLastName",
        "mpLastFirstName",
        "partyFname",
        "partySname",
        "stateName",
        "constName",
        "noOfTerms",
        "lastLoksabha",
        "lsExpr",
        "status",
    )

    missing = [k for k in question_route_needed + roster_needed if not is_permitted(k)]
    assert not missing, f"the allowlist drops field(s) the pipeline needs: {missing}"


def test_the_document_pointer_and_hindi_fields_are_dropped():
    """Principles III and IV, enforced by the same gate.

    `route-capture.md`: the four `*FilePath` / `*DocPath` fields are "ingestible
    as nothing at all: not followed, not fetched, not published", and the Hindi
    fields must not be ingested. `supplementaryType` is populated and carries no
    personal data, but is not in `data-model.md` and is therefore not published
    without a decision.
    """
    record = {
        "quesNo": 1,
        "questionsFilePath": "PLACEHOLDER",
        "questionsDocPath": "PLACEHOLDER",
        "questionsFilePathHindi": "PLACEHOLDER",
        "questionsDocPathHindi": "PLACEHOLDER",
        "answerTextHindi": "PLACEHOLDER",
        "questionText": "PLACEHOLDER",
        "answerText": "PLACEHOLDER",
        "supplementaryQuestionResDtoList": None,
        "supplementaryType": False,
    }

    assert set(filter_record(record)) == {"quesNo"}
