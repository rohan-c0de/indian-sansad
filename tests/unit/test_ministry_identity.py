"""Ministry identity: the fold, the confirmed renames, and the published listing.

Owner decision 2026-10-09 (`spike/ministry-identity.md`). `ministry_id` is the
slug of the **first** name a ministry was seen under -- assigned once, never
changed, never reused -- and `minCode` is not used, because it is per-term and
reused for unrelated ministries while question records carry only the name.

**The owner's condition on approving the singular fold was that no merge can be
silent.** That is what `test_every_group_the_fold_merged_is_listed` and
`test_the_coverage_statement_lists_every_merged_group` exist for: the fold is
allowed precisely because its every effect is published.
"""

from __future__ import annotations

import pytest

from sansad.ingest.questions import ministry_fold_key, ministry_id_for
from sansad.publish.reference import (
    REFERENCE_ONLY_MINISTRY_NAMES,
    MinistryObservation,
    MinistryRegistry,
)
from sansad.resolve.assertions import MinistryRename, load_ministry_renames


def obs(name: str, first: str, last: str = "2026-08-12", n: int = 1) -> MinistryObservation:
    return MinistryObservation(name=name, questions=n, first_date=first, last_date=last)


# ---------------------------------------------------------------------------
# The fold
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("a", "b", "resolved_by"),
    [
        ("EDUCATION", "Education", "slug"),
        ("MICRO, SMALL AND MEDIUM ENTERPRISES", "MICRO,SMALL AND MEDIUM ENTERPRISES", "slug"),
        ("COMMUNICATIONS", "COMMUNICATION", "fold"),
        (
            "ENVIRONMENT,  FORESTS AND CLIMATE CHANGE",
            "ENVIRONMENT, FOREST AND CLIMATE CHANGE",
            "fold",
        ),
    ],
)
def test_the_four_trivial_variants_normalise_together(a, b, resolved_by):
    """The four groups measured over the window's 64 names.

    `resolved_by` records which mechanism does it, because the two are not
    interchangeable: the slug was already there, the fold is the new thing the
    owner approved, and claiming the fold for work the slug already did would
    overstate what was changed.
    """
    assert ministry_fold_key(a) == ministry_fold_key(b)
    if resolved_by == "slug":
        assert ministry_id_for(a) == ministry_id_for(b)
    else:
        assert ministry_id_for(a) != ministry_id_for(b), (
            "if the slug already merged these, the fold is not what resolves them"
        )


def test_the_fold_does_not_merge_distinct_ministries():
    """A trailing-`s` rule must not collapse two real ministries.

    Measured over the window: exactly four groups merged, no false merge. These
    are the near-miss pairs that would hurt most if it did.
    """
    distinct = [
        ("DEFENCE", "FINANCE"),
        ("COAL", "COOPERATION"),
        ("HOME AFFAIRS", "EXTERNAL AFFAIRS"),
        ("AGRICULTURE AND FARMERS WELFARE", "FISHERIES, ANIMAL HUSBANDRY AND DAIRYING"),
        ("HEAVY INDUSTRIES", "MICRO, SMALL AND MEDIUM ENTERPRISES"),
    ]
    for a, b in distinct:
        assert ministry_fold_key(a) != ministry_fold_key(b), (a, b)


def test_the_published_id_is_the_unfolded_slug_of_the_first_name():
    """The fold is a matching device; the id stays readable.

    `ports-shipping-and-waterways`, not `port-shipping-and-waterway`. Same
    discipline as member-name normalisation -- "normalisation is for matching
    only".
    """
    registry = MinistryRegistry.build([obs("PORTS, SHIPPING AND WATERWAYS", "2021-02-04")])
    assert set(registry.ministries) == {"ports-shipping-and-waterways"}


# ---------------------------------------------------------------------------
# No merge is silent -- the owner's condition
# ---------------------------------------------------------------------------
def test_every_group_the_fold_merged_is_listed():
    """The fold's every effect is reported, which is why it was approved."""
    registry = MinistryRegistry.build(
        [
            obs("COMMUNICATIONS", "2019-06-26"),
            obs("COMMUNICATION", "2024-07-24"),
            obs("ENVIRONMENT,  FORESTS AND CLIMATE CHANGE", "2019-06-21"),
            obs("ENVIRONMENT, FOREST AND CLIMATE CHANGE", "2024-07-22"),
            obs("DEFENCE", "2019-06-21"),
        ]
    )
    assert registry.fold_groups == (
        ("COMMUNICATION", "COMMUNICATIONS"),
        (
            "ENVIRONMENT,  FORESTS AND CLIMATE CHANGE",
            "ENVIRONMENT, FOREST AND CLIMATE CHANGE",
        ),
    )
    # A ministry seen under one name only is not a "merge" and is not listed --
    # otherwise the list would be noise and stop being read.
    assert not any("DEFENCE" in group for group in registry.fold_groups)


def test_a_group_merged_by_the_slug_alone_is_not_claimed_as_a_fold_merge():
    """Case and punctuation were already handled; the list is the fold's own."""
    registry = MinistryRegistry.build(
        [obs("EDUCATION", "2024-07-22"), obs("Education", "2020-09-14")]
    )
    assert registry.fold_groups == ()
    assert set(registry.ministries) == {"education"}


def test_the_coverage_statement_lists_every_merged_group(tmp_path):
    """The listing reaches the **published** statement, not just the registry."""
    from sansad.model._common import House
    from sansad.publish.coverage import CoverageInputs, write_coverage_statements
    from sansad.publish.formats import read_csv, read_ndjson

    groups = (("COMMUNICATION", "COMMUNICATIONS"),)
    write_coverage_statements(
        tmp_path,
        [
            CoverageInputs(
                house=House.LOK_SABHA,
                period_start="2019-06-21",
                period_end="2026-08-12",
                sessions_covered=("lok-sabha/17/1",),
                last_refreshed="2026-10-09",
                total_questions=10,
                resolved_automatic=9,
                resolved_assisted=10,
                ministry_name_groups_merged_by_normalisation=groups,
                ministry_names_in_reference_set_with_no_questions=4,
            )
        ],
    )
    row = read_ndjson(tmp_path / "coverage.jsonl")[0]
    assert row["ministry_name_groups_merged_by_normalisation"] == [
        ["COMMUNICATION", "COMMUNICATIONS"]
    ]
    assert row["ministry_names_in_reference_set_with_no_questions"] == 4
    # The CSV carries it too -- neither format is authoritative.
    assert (
        "COMMUNICATIONS"
        in read_csv(tmp_path / "coverage.csv")[0]["ministry_name_groups_merged_by_normalisation"]
    )


# ---------------------------------------------------------------------------
# The confirmed renames
# ---------------------------------------------------------------------------
def test_the_four_confirmed_renames_are_seeded():
    renames = load_ministry_renames()
    assert {r.ministry_id for r in renames} == {
        "shipping",
        "heavy-industries-and-public-enterprises",
        "human-resource-development",
        "ayurveda-yoga-naturopathy-unani-siddha-and-homeopathy-ayush",
    }
    for rename in renames:
        assert rename.former_names, rename.ministry_id
        assert rename.evidence, rename.ministry_id
        assert rename.confirmed_on == "2026-10-09"


def test_a_rename_keeps_the_older_id_and_moves_the_old_name_to_former_names():
    """The decision's core: "the older id is kept; the new name becomes the
    display name and the old one goes into `former_names`"."""
    rename = MinistryRename(
        ministry_id="shipping",
        canonical_name="PORTS, SHIPPING AND WATERWAYS",
        former_names=("SHIPPING",),
        evidence="date handoff",
    )
    registry = MinistryRegistry.build(
        [
            obs("SHIPPING", "2019-06-27", "2020-09-22"),
            obs("PORTS, SHIPPING AND WATERWAYS", "2021-02-04"),
        ],
        [rename],
    )
    assert set(registry.ministries) == {"shipping"}, "a rename must not mint a second id"
    ministry = registry.ministries["shipping"]
    assert ministry.ministry_id == "shipping"
    assert ministry.canonical_name == "PORTS, SHIPPING AND WATERWAYS"
    assert ministry.former_names == ("SHIPPING",)
    assert set(ministry.name_variants) == {"SHIPPING", "PORTS, SHIPPING AND WATERWAYS"}
    # Both written forms route to the kept id.
    assert registry.id_for_minted(ministry_id_for("SHIPPING")) == "shipping"
    assert registry.id_for_minted(ministry_id_for("PORTS, SHIPPING AND WATERWAYS")) == "shipping"


def test_a_rename_absorbs_the_variants_of_the_name_it_absorbs():
    """Row 3's shape: the successor covers **both** written forms of Education.

    `EDUCATION` and `Education` already pool under one id by the slug; the
    mapping must re-point that whole pool at `human-resource-development`, not
    just the one spelling it happens to name.
    """
    rename = MinistryRename(
        ministry_id="human-resource-development",
        canonical_name="EDUCATION",
        former_names=("HUMAN RESOURCE DEVELOPMENT",),
        evidence="date handoff",
    )
    registry = MinistryRegistry.build(
        [
            obs("HUMAN RESOURCE DEVELOPMENT", "2019-06-24", "2020-03-23"),
            obs("Education", "2020-09-14", "2024-02-05"),
            obs("EDUCATION", "2024-07-22"),
        ],
        [rename],
    )
    assert set(registry.ministries) == {"human-resource-development"}
    for name in ("HUMAN RESOURCE DEVELOPMENT", "Education", "EDUCATION"):
        assert registry.id_for_minted(ministry_id_for(name)) == "human-resource-development", name


def test_an_unmapped_name_mints_its_own_id_and_is_counted():
    """ "A name with no mapping mints its own id" -- never guessed into one."""
    registry = MinistryRegistry.build(
        [obs("COOPERATION", "2021-08-03"), obs("DEFENCE", "2019-06-21")]
    )
    assert set(registry.ministries) == {"cooperation", "defence"}
    assert registry.names_without_confirmed_mapping == ("COOPERATION", "DEFENCE")


def test_reference_only_names_get_no_id_and_are_only_counted():
    """Table 4: zero questions in the window, so no id and not published."""
    registry = MinistryRegistry.build([obs("DEFENCE", "2019-06-21")])
    assert len(registry.reference_only) == 4
    assert set(registry.reference_only) == set(REFERENCE_ONLY_MINISTRY_NAMES)
    for name in registry.reference_only:
        assert ministry_id_for(name) not in registry.ministries, name


def test_a_rename_with_no_former_names_or_no_evidence_is_refused():
    """Same discipline as the member assertions: a mapping nobody can review is
    not reviewable evidence, and a "rename" with nothing to rename is not one."""
    with pytest.raises(ValueError, match="not a rename"):
        MinistryRename(ministry_id="x", canonical_name="X", former_names=(), evidence="e")
    with pytest.raises(ValueError, match="recorded evidence"):
        MinistryRename(ministry_id="x", canonical_name="X", former_names=("Y",), evidence="  ")


def test_two_mappings_claiming_one_name_are_refused(tmp_path):
    """Two confirmed mappings disagreeing is a correction to make by hand."""
    import json

    (tmp_path / "ministries.json").write_text(
        json.dumps(
            {
                "confirmed_on": "2026-10-09",
                "renames": [
                    {
                        "ministry_id": "a",
                        "canonical_name": "SHARED",
                        "former_names": ["OLD A"],
                        "evidence": "e",
                    },
                    {
                        "ministry_id": "b",
                        "canonical_name": "SHARED",
                        "former_names": ["OLD B"],
                        "evidence": "e",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="mapped to both"):
        load_ministry_renames(tmp_path)
