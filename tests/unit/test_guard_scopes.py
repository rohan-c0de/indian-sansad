"""The guard's size-ceiling exemptions, both halves of each.

`tools/guard_no_raw_payloads.py` applies a **64 KB fixture ceiling** to
payload-shaped files, because "a committed fixture of a raw upstream response is
the likeliest route by which the full personal-data payload enters the
repository". Two directories are exempt from that ceiling and **neither is
exempt from the attribute scan**:

- `data/published/` -- the build output. Large by design; 216.5 MiB measured.
- `.previous-snapshot/` -- the refresh workflow's checkout of the previous
  published snapshot, which FR-010's last-known-good needs.

Each exemption is a hole in a NON-NEGOTIABLE guard, so each gets two tests: one
that the ceiling really is lifted, and one that a prohibited attribute planted
there is **still caught**. A test for only the first half would let the second
regress silently, which is the failure mode that makes a guard worse than none.

**Why `.previous-snapshot/` needed this at all** -- review, 2026-10-09: on the
first CI run there is no `published` branch, so the directory is absent and the
guard passes. From the second run on it holds ~1,759 files, 759 of them over
64 KB, so the workflow's first `make guard` step would have failed, the refresh
would never have started, nothing would have been published, and only the
keep-alive commit would still have run.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GUARD = REPO_ROOT / "tools" / "guard_no_raw_payloads.py"

#: Comfortably over the 64 KB ceiling.
OVERSIZED_BYTES = 200 * 1024


def _load_guard():
    spec = importlib.util.spec_from_file_location("sansad_guard_scopes", GUARD)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_guard(root: Path) -> subprocess.CompletedProcess[str]:
    """Run the guard as the Makefile does -- the exit code is the interface."""
    return subprocess.run(
        [sys.executable, str(GUARD), str(root)],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """A minimal repo-shaped tree the guard can be pointed at."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "ok.py").write_text("x = 1\n", encoding="utf-8")
    return tmp_path


def test_the_exempt_prefixes_are_exactly_the_two_build_outputs():
    """A third entry here is a third hole, and should fail a test first."""
    guard = _load_guard()
    assert guard.SIZE_CEILING_EXEMPT_PREFIXES == (
        "data/published/",
        ".previous-snapshot/",
    )


def test_previous_snapshot_is_not_skipped_wholesale():
    """It must be ceiling-exempt, NOT in SKIP_DIRS.

    A skip would stop the attribute scan reaching it, which is the opposite of
    what is wanted: a prohibited attribute in a previously published file is
    still one reaching this tree.
    """
    guard = _load_guard()
    assert ".previous-snapshot" not in guard.SKIP_DIRS
    assert "data/published" not in guard.SKIP_DIRS


@pytest.mark.parametrize("scope", [".previous-snapshot", "data/published"])
def test_an_oversized_payload_in_an_exempt_scope_passes(tree: Path, scope: str):
    """Half one: the ceiling is lifted."""
    directory = tree / scope
    directory.mkdir(parents=True)
    # Valid JSON, well over the ceiling, carrying only permitted field names.
    body = '{"question_id":"q","asking_members":["ls-1"],"subject":"' + "x" * OVERSIZED_BYTES + '"}'
    (directory / "by-session.jsonl").write_text(body + "\n", encoding="utf-8")
    assert (directory / "by-session.jsonl").stat().st_size > 64 * 1024

    result = _run_guard(tree)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "size violation" not in result.stdout or "0 size violation" in result.stdout


@pytest.mark.parametrize("scope", [".previous-snapshot", "data/published"])
def test_a_prohibited_attribute_in_an_exempt_scope_still_fails(tree: Path, scope: str):
    """Half two, and the one that matters: the attribute scan still covers it.

    The planted key is read from the guard's own list rather than spelled out,
    so this file does not itself carry a prohibited spelling -- the same reason
    `tests/unit/test_field_allowlist.py` reads it.
    """
    guard = _load_guard()
    # Chosen by a computed property, never spelled out. This file is itself
    # scanned by the guard, and an earlier draft that wrote the spelling as a
    # literal tripped it -- correctly. `min(..., key=len)` is stable in meaning
    # regardless of how the guard's list is ordered. The attribute LABEL below
    # is safe to write: its words tokenise separately and none is prohibited.
    planted = min(guard.PROHIBITED_ATTRIBUTES["date of birth"], key=len)

    directory = tree / scope
    directory.mkdir(parents=True)
    (directory / "member.jsonl").write_text(
        f'{{"memberName":"Placeholder","{planted}":"PLACEHOLDER"}}\n',
        encoding="utf-8",
    )

    result = _run_guard(tree)
    assert result.returncode == 1, result.stdout + result.stderr
    assert planted in result.stdout
    assert "date of birth" in result.stdout
    assert f"{scope}/member.jsonl" in result.stdout
    # The guard prints the key, never the value.
    assert "PLACEHOLDER" not in result.stdout


def test_an_oversized_payload_outside_the_exempt_scopes_still_fails(tree: Path):
    """The control. If this passed, the exemption would have become general and
    the ceiling would protect nothing.
    """
    (tree / "tests").mkdir()
    (tree / "tests" / "fixtures.json").write_text(
        '{"subject":"' + "x" * OVERSIZED_BYTES + '"}\n', encoding="utf-8"
    )

    result = _run_guard(tree)
    assert result.returncode == 1, result.stdout
    assert "exceeds the" in result.stdout
    assert "tests/fixtures.json" in result.stdout
