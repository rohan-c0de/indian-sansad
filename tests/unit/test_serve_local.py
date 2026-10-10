"""`make serve-local` serves the published-branch layout. T081.

The mapping must mirror what `.github/workflows/refresh.yml` writes to the
`published` branch, so a relative path that resolves locally resolves as
served. `tests/unit/test_published_branch_layout.py` executes the workflow's
own copy block; this file asserts the server agrees with it rather than
assuming the two were kept in step by hand.
"""

from __future__ import annotations

import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER = REPO_ROOT / "tools" / "serve_local.py"


def _resolve(path: str):
    from importlib import util

    spec = util.spec_from_file_location("sansad_serve_local", SERVER)
    assert spec and spec.loader
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def serve():
    return _resolve("")


# ---------------------------------------------------------------------------
# The mapping, without binding a port.
# ---------------------------------------------------------------------------


def test_the_page_is_at_the_root(serve) -> None:
    assert serve.resolve_request("/") == (REPO_ROOT / "web" / "index.html").resolve()
    assert serve.resolve_request("/index.html") == (REPO_ROOT / "web" / "index.html").resolve()
    assert serve.resolve_request("/style.css") == (REPO_ROOT / "web" / "style.css").resolve()
    assert serve.resolve_request("/app.js") == (REPO_ROOT / "web" / "app.js").resolve()
    assert (
        serve.resolve_request("/lib/fetch.js") == (REPO_ROOT / "web" / "lib" / "fetch.js").resolve()
    )


def test_the_dataset_is_under_data_published(serve) -> None:
    got = serve.resolve_request("/data/published/manifest.json")
    assert got == (REPO_ROOT / "data" / "published" / "manifest.json").resolve()
    got = serve.resolve_request("/data/published/aggregates/counting-basis.jsonl")
    assert (
        got == (REPO_ROOT / "data" / "published" / "aggregates" / "counting-basis.jsonl").resolve()
    )


def test_the_licences_are_at_the_root(serve) -> None:
    assert serve.resolve_request("/LICENSE") == (REPO_ROOT / "LICENSE").resolve()
    assert serve.resolve_request("/DATA-LICENSE.md") == (REPO_ROOT / "DATA-LICENSE.md").resolve()


def test_nothing_outside_the_two_roots_is_served(serve) -> None:
    """A static server that can be talked out of its root is a file-disclosure
    bug, and this one runs on a maintainer's laptop beside a scratch directory
    full of raw upstream payloads."""
    for path in (
        "/../pyproject.toml",
        "/data/published/../../pyproject.toml",
        "/..%2fpyproject.toml",
        "/src/sansad/cli.py",
        "/data/assertions/lok-sabha.json",
        "/.git/config",
    ):
        target = serve.resolve_request(path)
        assert target is None or not target.is_file(), f"{path} resolved to {target}"


def test_the_query_string_is_not_part_of_the_path(serve) -> None:
    assert serve.resolve_request("/app.js?v=2") == (REPO_ROOT / "web" / "app.js").resolve()
    assert serve.resolve_request("/app.js#x") == (REPO_ROOT / "web" / "app.js").resolve()


def test_a_module_script_is_served_as_javascript(serve) -> None:
    """A module served as anything but a JavaScript type is REFUSED by the
    browser, and the page would load with no behaviour and no obvious cause."""
    assert serve.EXTRA_TYPES[".js"] == "text/javascript"
    assert serve.EXTRA_TYPES[".css"] == "text/css"


def test_the_mapping_matches_the_workflow_layout(serve) -> None:
    """One layout, two implementations: they must agree.

    The workflow copies `web/.` to the branch root, `data/published/.` to
    `data/published/`, and LICENSE + DATA-LICENSE.md to the root. The server's
    declared roots must be exactly those.
    """
    workflow = (REPO_ROOT / ".github" / "workflows" / "refresh.yml").read_text(encoding="utf-8")
    block = workflow.split("# BEGIN LAYOUT", 1)[1].split("# END LAYOUT", 1)[0]

    assert f'cp -R "${{GITHUB_WORKSPACE}}/{serve.PAGE_ROOT}/." .' in block
    for prefix, target in serve.PREFIX_ROOTS:
        assert f'cp -R "${{GITHUB_WORKSPACE}}/{target}/." {target}/' in block
        assert prefix == f"/{target}/"
    for name in serve.ROOT_FILES:
        assert f'cp "${{GITHUB_WORKSPACE}}/{name}" {name}' in block


# ---------------------------------------------------------------------------
# It actually starts and answers.
# ---------------------------------------------------------------------------


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def running_server():
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, str(SERVER), "--host", "127.0.0.1", "--port", str(port)],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            out, err = proc.communicate()
            pytest.fail(f"server exited: {out}\n{err}")
        try:
            with urllib.request.urlopen(base + "/", timeout=1):
                break
        except Exception:
            time.sleep(0.05)
    else:  # pragma: no cover
        proc.kill()
        pytest.fail("server did not start")
    try:
        yield base
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:  # pragma: no cover
            proc.kill()


def test_the_page_and_the_dataset_answer_from_one_origin(running_server) -> None:
    """The point of T081: both come from the SAME scheme, host and port."""
    from urllib.parse import urlsplit

    origins = set()
    for path, expected_type in (
        ("/", "text/html"),
        ("/style.css", "text/css"),
        ("/app.js", "text/javascript"),
        ("/lib/fetch.js", "text/javascript"),
        ("/data/published/manifest.json", "application/json"),
        ("/data/published/coverage.jsonl", "text/plain"),
        ("/LICENSE", None),
    ):
        url = running_server + path
        with urllib.request.urlopen(url, timeout=10) as response:
            assert response.status == 200, path
            assert response.read(), f"{path} served an empty body"
            if expected_type:
                assert response.headers.get_content_type() == expected_type, path
        parts = urlsplit(url)
        origins.add((parts.scheme, parts.hostname, parts.port))
    assert len(origins) == 1, f"more than one origin: {origins}"


def test_an_unserved_path_is_404_not_a_file(running_server) -> None:
    for path in ("/src/sansad/cli.py", "/pyproject.toml", "/data/assertions/lok-sabha.json"):
        with pytest.raises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(running_server + path, timeout=10)
        assert caught.value.code == 404, path
