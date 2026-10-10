"""The non-persisting transport. The only code permitted to fetch.

Standing constraint, Constitution Principle V: **no raw upstream payload is
ever written inside the repository tree.** Not as a cache, not as a fixture,
not as a spike artefact, not in a test.

This module enforces that with two mechanisms, both of which refuse rather
than degrade:

1. **Fetched bodies go straight to the FR-008 allowlist.** `fetch_records`
   decodes, filters in memory via `sansad.ingest.field_allowlist.filter_record`,
   and returns filtered records. The raw decoded body is never returned to a
   caller and never written by this module.

2. **Any on-disk cache is rooted outside the repository, proven, not assumed.**
   `resolve_scratch_root` resolves `$SANSAD_SCRATCH` with symlinks and `..`
   segments collapsed, compares it against the resolved repository root, and
   **raises** if it lies inside. There is no fallback to a repo path: the
   process exits non-zero instead. A fallback is how a guard becomes a
   formality -- the one time the environment is misconfigured is exactly the
   time the payload would land in the tree.

`realpath` rather than string comparison is deliberate: on macOS `$TMPDIR` is
under `/var`, which is a symlink to `/private/var`, and a `..` segment can
walk an innocent-looking path back into the tree. Neither can smuggle an
in-tree path past a resolved comparison. `make scratch` applies the same
assertion at the shell level, so the check holds whether the caller came
through make or imported this module directly.
"""

from __future__ import annotations

import os
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import httpx

from sansad.ingest.field_allowlist import filter_record

__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "ScratchPathInsideRepoError",
    "assert_outside_repo",
    "fetch_json",
    "fetch_records",
    "repo_root",
    "resolve_scratch_root",
    "scratch_path",
]

#: Explicit, and not generous. The upstream carries no contract, versioning or
#: deprecation notice, so a hung request is an expected failure mode rather
#: than a surprise. httpx's default is 5s; the window is ~95k records across
#: paginated requests, and a request that has not answered in 30s is a failure
#: to signal (FR-011), not a request to keep waiting on.
DEFAULT_TIMEOUT_SECONDS = 30.0


class ScratchPathInsideRepoError(RuntimeError):
    """Raised when `$SANSAD_SCRATCH` resolves inside the repository tree.

    A distinct type, so no caller can catch this by accident while handling
    ordinary I/O errors and carry on writing into the tree.
    """


def repo_root() -> Path:
    """The repository root, resolved.

    Derived from this file's location -- `src/sansad/ingest/transport.py` is
    three parents below `src/`, four below the root -- rather than from the
    current working directory, which a caller can change.
    """
    return Path(__file__).resolve().parents[3]


def resolve_scratch_root(scratch: str | os.PathLike[str] | None = None) -> Path:
    """Resolve the out-of-tree scratch root, or raise.

    Raises:
        ScratchPathInsideRepoError: if the resolved path is the repository root
            or lies inside it. There is no fallback -- see the module
            docstring.
        RuntimeError: if `$SANSAD_SCRATCH` is unset and no path is given.
    """
    raw = scratch if scratch is not None else os.environ.get("SANSAD_SCRATCH")
    if not raw:
        raise RuntimeError(
            "SANSAD_SCRATCH is not set. Fetched bodies have nowhere outside the "
            "repository tree to go, and this module will not fall back to a path "
            "inside it (Constitution Principle V). Run `make scratch` or set "
            "SANSAD_SCRATCH to a directory outside the repository."
        )

    resolved = Path(raw).expanduser().resolve()
    root = repo_root()
    if resolved == root or root in resolved.parents:
        raise ScratchPathInsideRepoError(
            f"SANSAD_SCRATCH resolves INSIDE the repository tree.\n"
            f"  requested : {raw}\n"
            f"  resolved  : {resolved}\n"
            f"  repo root : {root}\n"
            f"Constitution Principle V: no raw upstream payload is ever written "
            f"inside this tree. Set SANSAD_SCRATCH outside it. This is not "
            f"recoverable in-process and there is deliberately no fallback."
        )
    return resolved


def assert_outside_repo(path: str | os.PathLike[str], *, what: str = "path") -> Path:
    """Resolve `path` and raise if it lies inside the repository tree.

    Public because more than one writer needs it now. `scratch_path` applies it
    to paths it builds; this applies it to a path a **caller** supplies, which
    is the case `fetch_question_records`'s `checkpoint` argument introduced --
    an argument that takes any Path is an argument that can take an in-tree one.
    """
    resolved = Path(path).expanduser().resolve()
    root = repo_root()
    if resolved == root or root in resolved.parents:
        raise ScratchPathInsideRepoError(
            f"{what} resolves INSIDE the repository tree.\n"
            f"  requested : {path}\n"
            f"  resolved  : {resolved}\n"
            f"  repo root : {root}\n"
            f"Constitution Principle V: no raw upstream payload is ever written "
            f"inside this tree. There is deliberately no fallback."
        )
    return resolved


def scratch_path(*parts: str, scratch: str | os.PathLike[str] | None = None) -> Path:
    """A path under the verified out-of-tree scratch root, created on demand.

    Every on-disk write of anything upstream-derived goes through here, so the
    assertion cannot be bypassed by composing a path by hand.
    """
    root = resolve_scratch_root(scratch)
    target = (root / Path(*parts)).resolve()
    if root not in target.parents and target != root:
        raise ScratchPathInsideRepoError(
            f"path {target} escapes the scratch root {root} -- refusing to write."
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def fetch_json(
    url: str,
    *,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    client: httpx.Client | None = None,
) -> Any:
    """Fetch and decode one JSON body. Returns the decoded body; writes nothing.

    The return value is the **unfiltered** decoded body and is for callers that
    must read envelope metadata -- a total-record count, a pagination cursor --
    which are not member attributes. It is in memory only. A caller that holds
    records from it MUST pass them through `filter_record`; `fetch_records`
    does that itself and is what ingest code should normally use.
    """
    owns_client = client is None
    active = client or httpx.Client(timeout=timeout, follow_redirects=True)
    try:
        response = active.get(url, params=dict(params or {}), headers=dict(headers or {}))
        response.raise_for_status()
        return response.json()
    finally:
        if owns_client:
            active.close()


def fetch_records(
    url: str,
    *,
    records_key: str | None = None,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    client: httpx.Client | None = None,
) -> Iterator[dict[str, Any]]:
    """Fetch, decode, and yield records **already through the FR-008 allowlist**.

    This is the ingest path. The raw body is not returned, not logged and not
    written -- it is filtered in memory and only the permitted attributes leave
    this function.
    """
    body = fetch_json(url, params=params, headers=headers, timeout=timeout, client=client)

    if records_key is not None:
        if not isinstance(body, Mapping):
            raise TypeError(
                f"expected a mapping to read records_key {records_key!r} from, "
                f"got {type(body).__name__}"
            )
        raw_records = body.get(records_key, [])
    else:
        raw_records = body

    if isinstance(raw_records, Mapping):
        raw_records = [raw_records]
    if not isinstance(raw_records, list):
        raise TypeError(
            f"expected a list of records, got {type(raw_records).__name__}. "
            f"An unexpected envelope shape is a maintainer signal (FR-011), not "
            f"something to coerce."
        )

    for record in raw_records:
        if isinstance(record, Mapping):
            yield filter_record(dict(record))
