"""The layout `.github/workflows/refresh.yml` publishes to the `published` branch.

**Owner decision 2026-10-10**: the page (`web/`) at the **branch root** and the
dataset under **`data/published/`**, so the page's same-origin paths (T076) and
`make serve-local` (T081) resolve exactly as GitHub Pages serves them.

The workflow previously copied `data/published/.` to the **root** and **nothing
from `web/`**. Under that layout the coverage statement sat at
`/coverage.jsonl`, every `/data/...` path T076 fetches would have 404'd, and
there would have been no page at `/` to fetch them. It was found by review
(`specs/001-resolved-metadata-layer/mockup/README.md`) and never observed,
because the workflow has never run -- T058 is ticked "written, statically
checked, NOT yet run on GitHub".

**These tests execute the workflow's own shell.** The copy block between
`# BEGIN LAYOUT` and `# END LAYOUT` is extracted from the YAML and run against
a temporary directory, so the layout has ONE definition. A test that
reimplemented the copy would assert the reimplementation, pass forever, and
tell us nothing about the file that actually runs on the runner.

**What these tests do not establish.** Nothing here runs on a GitHub runner, so
every step around the block -- the orphan worktree, the force-push, Pages
serving the branch -- is still UNVERIFIED. They also run under the local
`/bin/bash` and BSD `cp`; the runner is `ubuntu-latest` with GNU coreutils. The
block is written to avoid the one construct where the two are known to differ
(`cp -R` into or out of an empty or missing directory) by testing for the
directory and its contents first, rather than relying on `cp`'s behaviour.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "refresh.yml"

BEGIN = "# BEGIN LAYOUT"
END = "# END LAYOUT"

#: Set by the workflow's `env:` block, and the only variable the extracted
#: block is permitted to depend on besides the working directory.
WORKSPACE_VAR = "GITHUB_WORKSPACE"


def _publish_step() -> dict:
    """The one step that writes the published tree."""
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["refresh"]["steps"]
    matching = [s for s in steps if s.get("name", "").startswith("Publish to")]
    assert len(matching) == 1, f"expected one publish step, found {len(matching)}"
    return matching[0]


def _layout_block() -> str:
    """The shell between the markers, dedented and ready to execute."""
    run = _publish_step()["run"]
    assert run.count(BEGIN) == 1, f"expected exactly one {BEGIN!r}"
    assert run.count(END) == 1, f"expected exactly one {END!r}"
    body = run.split(BEGIN, 1)[1].split(END, 1)[0]
    return textwrap.dedent(body)


def _run_layout(workspace: Path, target: Path) -> subprocess.CompletedProcess:
    """Execute the extracted block with the workflow's own shell options."""
    script = "set -eu -o pipefail\n" + _layout_block()
    return subprocess.run(
        ["bash", "-c", script],
        cwd=target,
        env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", WORKSPACE_VAR: str(workspace)},
        capture_output=True,
        text=True,
        check=False,
    )


def _workspace(tmp_path: Path, *, web: str) -> Path:
    """A fake checkout. `web` is "populated", "empty" or "absent".

    The dataset is always present: the publish step runs only after
    `test -d data/published/by-session` and `test -f .../manifest.json`, so a
    missing dataset is a state the block is never reached in.
    """
    workspace = tmp_path / "workspace"
    published = workspace / "data" / "published"
    (published / "by-session").mkdir(parents=True)
    (published / "manifest.json").write_text('{"source": "scratch"}\n')
    (published / "by-session" / "lok-sabha-18-7.jsonl").write_text('{"question_id": "x"}\n')
    (published / "coverage.jsonl").write_text('{"house": "lok-sabha"}\n')

    if web == "populated":
        page = workspace / "web"
        (page / "assets").mkdir(parents=True)
        (page / "index.html").write_text("<p>page</p>\n")
        (page / "app.js").write_text("// fetch layer\n")
        (page / "assets" / "style.css").write_text("body{}\n")
    elif web == "empty":
        (workspace / "web").mkdir()
    elif web == "absent":
        pass
    else:  # pragma: no cover - guards the test's own parameterisation
        raise AssertionError(f"unknown web state {web!r}")
    return workspace


@pytest.fixture
def target(tmp_path: Path) -> Path:
    """Stand-in for the emptied orphan worktree the block copies into."""
    branch = tmp_path / "worktree"
    branch.mkdir()
    return branch


def test_the_markers_exist_and_delimit_the_copy() -> None:
    """If the markers are deleted, every other test here silently stops testing."""
    block = _layout_block()
    assert 'cp -R "${GITHUB_WORKSPACE}/web/." .' in block
    assert 'cp -R "${GITHUB_WORKSPACE}/data/published/." data/published/' in block
    assert "touch .nojekyll" in block


def test_the_block_depends_on_nothing_but_the_workspace_and_cwd() -> None:
    """A block that read other workflow variables could not be tested in isolation."""
    block = _layout_block()
    referenced = set(re.findall(r"\$\{(\w+)\}", block))
    assert referenced == {WORKSPACE_VAR}, f"unexpected variables: {referenced}"


def test_page_at_the_root_and_dataset_under_data_published(tmp_path: Path, target: Path) -> None:
    """Decision 5, the whole of it."""
    workspace = _workspace(tmp_path, web="populated")
    result = _run_layout(workspace, target)
    assert result.returncode == 0, result.stderr

    # The page is at the ROOT -- not under web/, not under data/.
    assert (target / "index.html").read_text() == "<p>page</p>\n"
    assert (target / "app.js").exists()
    assert (target / "assets" / "style.css").exists(), "nested page dirs must survive"
    assert not (target / "web").exists(), "web/ must not be reproduced as a directory"

    # The dataset is under data/published/ -- not at the root.
    assert (target / "data" / "published" / "manifest.json").exists()
    assert (target / "data" / "published" / "by-session" / "lok-sabha-18-7.jsonl").exists()
    assert (target / "data" / "published" / "coverage.jsonl").exists()
    assert not (target / "manifest.json").exists(), "the dataset must NOT be at the root"
    assert not (target / "coverage.jsonl").exists(), "this is the layout that 404'd T076"
    assert not (target / "by-session").exists()

    # And no doubled path from copying a directory into itself.
    assert not (target / "data" / "published" / "data").exists()

    # Pages must not run the dataset through Jekyll.
    assert (target / ".nojekyll").is_file()


def test_an_empty_web_publishes_the_dataset_alone(tmp_path: Path, target: Path) -> None:
    """`web/` exists but holds nothing. Must not fail under `set -e`."""
    workspace = _workspace(tmp_path, web="empty")
    result = _run_layout(workspace, target)
    assert result.returncode == 0, result.stderr
    assert "dataset only" in result.stdout

    assert (target / "data" / "published" / "manifest.json").exists()
    assert (target / ".nojekyll").is_file()
    assert not (target / "index.html").exists()


def test_an_absent_web_publishes_the_dataset_alone(tmp_path: Path, target: Path) -> None:
    """The REAL case today: `web/` is untracked and empty, so a CI checkout has
    no `web/` at all -- git cannot track an empty directory. This is what the
    first run will actually do."""
    workspace = _workspace(tmp_path, web="absent")
    assert not (workspace / "web").exists()

    result = _run_layout(workspace, target)
    assert result.returncode == 0, result.stderr
    assert "dataset only" in result.stdout

    assert (target / "data" / "published" / "manifest.json").exists()
    assert (target / ".nojekyll").is_file()
    assert not (target / "index.html").exists()


def test_web_today_is_in_fact_empty_or_absent() -> None:
    """Pins the premise the two tests above rest on. When `web/` acquires
    T074's files this test fails, which is the signal to re-read them."""
    page = REPO_ROOT / "web"
    tracked = subprocess.run(
        ["git", "ls-files", "web/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert tracked == "", f"web/ now tracks files: {tracked!r} -- T074 has landed"
    assert not page.exists() or not any(page.iterdir())


def test_the_dataset_wins_a_path_collision(tmp_path: Path, target: Path) -> None:
    """A page file and a dataset file cannot both own one path. The dataset is
    copied second so the dataset wins -- a page that shadowed a published file
    would serve the page's bytes to a consumer fetching the dataset."""
    workspace = _workspace(tmp_path, web="populated")
    colliding = workspace / "web" / "data" / "published"
    colliding.mkdir(parents=True)
    (colliding / "manifest.json").write_text('{"source": "THE PAGE, WRONGLY"}\n')

    result = _run_layout(workspace, target)
    assert result.returncode == 0, result.stderr
    assert (
        target / "data" / "published" / "manifest.json"
    ).read_text() == '{"source": "scratch"}\n'


def test_the_workflow_holds_the_permission_the_push_needs() -> None:
    """`contents: write` covers both the force-push to `published` and the
    keep-alive commit to `main`. Pages serving a branch needs no workflow
    permission at all -- `pages: write` and `id-token: write` belong to the
    artifact-based deployment this project does not use."""
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert workflow["permissions"] == {"contents": "write"}

    text = WORKFLOW.read_text(encoding="utf-8")
    assert "deploy-pages" not in text, "branch-served Pages needs no deploy action"
    assert "upload-pages-artifact" not in text


def test_the_publish_step_asserts_the_dataset_was_actually_staged() -> None:
    """`data/published/` is git-ignored on `main`, so `git add -A` stages it
    only because the step's `find ... -exec rm -rf` deletes `.gitignore` first.
    VERIFIED in an isolated repository on 2026-10-10: with `.gitignore` left in
    place, `git add -A` staged the page and `.gitignore` and DROPPED the whole
    dataset. The step must therefore assert on the INDEX, or a regression would
    force-push an empty dataset over a good one."""
    run = _publish_step()["run"]
    assert "git diff --cached --name-only -- data/published/manifest.json" in run
    assert "refusing to publish" in run
    # The assertion has to come after the staging it checks.
    assert run.index("git add -A") < run.index("refusing to publish")


def test_bash_and_cp_are_available() -> None:
    """The extracted block is shell; without these the suite would pass by
    skipping the only tests that touch the real workflow."""
    assert shutil.which("bash"), "these tests execute the workflow's shell"
    assert shutil.which("cp") or Path("/bin/cp").exists()
