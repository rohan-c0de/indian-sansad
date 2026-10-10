"""The one definition of the dataset's licence, attribution and project URL.

**Owner decision 2026-10-10.** CC BY 4.0 obliges a consumer to attribute, and
until now nothing *inside* the dataset said what to attribute or where to link.
`DATA-LICENSE.md` reaches a consumer who takes the whole `published` branch; it
does not reach one who takes a single partition file. So the licence travels
with the data.

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

__all__ = [
    "ATTRIBUTION",
    "LICENCE_FIELDS",
    "LICENSE_FILE",
    "LICENSE_SCOPE",
    "LICENSE_SPDX",
    "PROJECT_URL",
]
