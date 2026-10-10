"""The one definition of the dataset's licence, attribution, project URL, and
the source-terms disclosure that sits beside them.

**Owner decision 2026-10-10.** CC BY 4.0 obliges a consumer to attribute, and
until now nothing *inside* the dataset said what to attribute or where to link.
`DATA-LICENSE.md` reaches a consumer who takes the whole `published` branch; it
does not reach one who takes a single partition file. So the licence travels
with the data.

**Owner decision 2026-10-10** adds two fields to the same two files:
`source_terms`, which states that the terms under which the Lok Sabha publishes
these records have never been determined, and `corrections_url`, the channel
for a correction or a removal request. They are disclosure, not licence, so
they live in their own mapping -- but they travel exactly as far, and no
further.

**These fields go on `manifest.json` and the Coverage Statement and NOWHERE
else** -- not on question rows, not on aggregate rows, not in the search index.
Two reasons, the second load-bearing:

1. **Bytes.** `ATTRIBUTION` plus `LICENSE_SCOPE` is ~340 bytes. Carried on the
   92,942 subject-trend rows that is the 179 MiB mistake T064 made once already
   by inlining the counting basis on every row; the remedy there was a reference
   and the lesson is not to repeat the cause.
2. **Meaning.** A per-row licence field would assert that *that row* is CC BY
   4.0, and `DATA-LICENSE.md` says the opposite: a published row mixes this
   project's added work with source records this project cannot license. The
   claim is true of the dataset as a whole and false of any single row, so it
   belongs on the two files that describe the whole.

Everything here is a plain string constant rather than a computed value: the
dataset is force-pushed as one commit with no history to diff against, so two
refreshes over the same data must produce byte-identical files.

`tests/contract/test_attribution.py` asserts that `ATTRIBUTION` is character-
for-character the blockquoted line in `DATA-LICENSE.md`, so the human-readable
licence and the machine-readable field cannot drift apart. There is one more
place this string will have to change -- see `DATA-LICENSE.md` -> "Once a Pages
URL exists" -- and this module is that place.
"""

from __future__ import annotations

#: SPDX identifier for the licence granted over the ADDED work. Not MIT: that
#: is the code licence, in the repository root `LICENSE`.
LICENSE_SPDX: str = "CC-BY-4.0"

#: Canonical link. The repository, not a published site -- the `published`
#: branch does not exist until the first refresh runs and GitHub Pages can only
#: be pointed at it afterwards, so a site URL here would be a promise.
PROJECT_URL: str = "https://github.com/rohan-c0de/indian-sansad"

#: The licence document, at the root of both the repository and the `published`
#: branch (the refresh workflow copies it there).
LICENSE_FILE: str = "DATA-LICENSE.md"

#: The attribution to reproduce, verbatim. It names the source layer as well as
#: this project, because an attribution crediting only this project would imply
#: the parliamentary records themselves are ours.
ATTRIBUTION: str = (
    "Contains data from Indian Sansad "
    f"({PROJECT_URL}), licensed CC BY 4.0, "
    "built over records published by the Lok Sabha."
)

#: One line, so it survives a CSV cell unquoted and a terminal without wrapping.
#: It has to carry the limit, not just the grant: the grant alone would read as
#: a licence over the whole row.
LICENSE_SCOPE: str = (
    "CC BY 4.0 covers the added work only -- identity resolution, joins, "
    "ministry identity, aggregates and indexes. The underlying parliamentary "
    "records are not covered and remain subject to their source's terms; see "
    f"{LICENSE_FILE}."
)

#: **Owner decision 2026-10-10: publish without determining the source's terms,
#: with disclosure and a corrections path.** Terms of use, licensing and
#: copyright were scoped out of the assessment by owner instruction and have
#: never been researched -- so this says so, in the dataset, rather than
#: leaving a consumer to infer permission from silence. It makes NO legal claim
#: in either direction: not that reuse is permitted, not that it is barred.
#:
#: One line, for the same reason as `LICENSE_SCOPE`: it has to survive a CSV
#: cell and a terminal without wrapping.
SOURCE_TERMS: str = (
    "Not determined. The maintainer has not established the terms under which "
    "the Lok Sabha publishes these records and publishes this dataset without "
    f"that determination. See {LICENSE_FILE}."
)

#: Where a correction or a removal request goes. The issue tracker, because it
#: is the only channel this project actually has: there is no email address
#: published here (the work is published under a project name, not a
#: maintainer's, per the constitution) and no form, which would be a service.
#:
#: Published as an absolute `https://` URL. The page that renders it refuses to
#: link anything else -- see `web/lib/licence.js`.
CORRECTIONS_URL: str = f"{PROJECT_URL}/issues"

#: The published field names and their values, in the order they are written.
#: Both writers spread this mapping rather than listing fields themselves, and
#: the contract test iterates it -- so adding a sixth field here adds it to the
#: manifest, to the Coverage Statement and to every assertion at once.
LICENCE_FIELDS: dict[str, str] = {
    "license": LICENSE_SPDX,
    "attribution": ATTRIBUTION,
    "project_url": PROJECT_URL,
    "license_file": LICENSE_FILE,
    "license_scope": LICENSE_SCOPE,
}

#: The disclosure fields, kept in their own mapping rather than folded into
#: `LICENCE_FIELDS`, because they are not a licence: `source_terms` is the
#: ABSENCE of a determination and `corrections_url` is a channel. Calling
#: either one a licence field would be the overclaim this whole disclosure
#: exists to avoid.
DISCLOSURE_FIELDS: dict[str, str] = {
    "source_terms": SOURCE_TERMS,
    "corrections_url": CORRECTIONS_URL,
}

#: What the two whole-dataset files carry. Both writers spread THIS mapping, so
#: a field added to either half above reaches `manifest.json` and the Coverage
#: Statement at once -- and reaches nothing else, which is the point: these are
#: claims about the dataset, false of any single row.
WHOLE_DATASET_FIELDS: dict[str, str] = {**LICENCE_FIELDS, **DISCLOSURE_FIELDS}

__all__ = [
    "ATTRIBUTION",
    "CORRECTIONS_URL",
    "DISCLOSURE_FIELDS",
    "LICENCE_FIELDS",
    "LICENSE_FILE",
    "LICENSE_SCOPE",
    "LICENSE_SPDX",
    "PROJECT_URL",
    "SOURCE_TERMS",
    "WHOLE_DATASET_FIELDS",
]
