"""The page's own tests, plus static assertions about `web/`. T074-T077.

**The cross-origin refusal is proven in `tests/page/*.test.mjs`**, run here by
Node's built-in test runner so there is one suite to run. Node 22.22.3 was
already installed; nothing was installed for this — no test framework, no
browser driver, no `package.json`, no `node_modules/`.

**What these tests do not establish.** No browser runs here. Whether the real
page in a real browser issues only same-origin requests is T082's to prove from
an actual network log; what is proven here is that the one function every
request goes through refuses an off-origin URL **before calling fetch**, and
that nothing in `web/` names another host at all.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WEB = REPO_ROOT / "web"
PAGE_TESTS = sorted((REPO_ROOT / "tests" / "page").glob("*.test.mjs"))

#: Every text file that ships as part of the page.
PAGE_FILES = ("index.html", "style.css", "app.js", "lib/fetch.js", "lib/format.js")


def test_node_is_available_and_the_page_tests_exist() -> None:
    """Without this the suite could pass by silently skipping the only tests
    that exercise the refusal."""
    assert shutil.which("node"), "Node is required to run the page's tests"
    assert PAGE_TESTS, "no tests/page/*.test.mjs found"


def test_the_page_test_suite_passes() -> None:
    """Runs `node --test tests/page/*.test.mjs` and fails with its output."""
    result = subprocess.run(
        ["node", "--test", "--test-reporter=tap", *[str(p) for p in PAGE_TESTS]],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"node --test failed:\n{result.stdout}\n{result.stderr}"
    assert re.search(r"^# fail 0$", result.stdout, re.M), result.stdout
    passed = re.search(r"^# pass (\d+)$", result.stdout, re.M)
    assert passed and int(passed.group(1)) > 10, result.stdout


# ---------------------------------------------------------------------------
# Static: nothing in web/ reaches another host.
# ---------------------------------------------------------------------------

#: Matches a scheme-qualified or protocol-relative URL in code or markup.
_OFF_HOST = re.compile(r"""(?:https?:)?//[A-Za-z0-9.-]+\.[A-Za-z]{2,}""")


def _code_lines(path: Path) -> list[tuple[int, str]]:
    """Lines with block comments, line comments and HTML comments removed.

    A URL in prose is documentation; a URL in code is a request. The two have
    to be told apart or the check is unusable in a codebase that explains
    itself.
    """
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    out = []
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith(("//", "*", "#")):
            continue
        out.append((number, line))
    return out


@pytest.mark.parametrize("name", PAGE_FILES)
def test_no_page_file_names_another_host(name: str) -> None:
    """No CDN, no web font, no analytics, no beacon — in code, not just intent."""
    offenders = [
        (number, line.strip()) for number, line in _code_lines(WEB / name) if _OFF_HOST.search(line)
    ]
    assert offenders == [], f"{name} names an outside host: {offenders}"


@pytest.mark.parametrize("name", PAGE_FILES)
def test_no_page_file_imports_anything_but_a_relative_path(name: str) -> None:
    """A bare module specifier would need a bundler or an import map; either
    way it is a build step, and there is not one."""
    for number, line in _code_lines(WEB / name):
        for match in re.finditer(r"""(?:from|import)\s+["']([^"']+)["']""", line):
            spec = match.group(1)
            assert spec.startswith("./") or spec.startswith("../"), (
                f"{name}:{number} imports a non-relative specifier {spec!r}"
            )


def test_the_stylesheet_fetches_nothing() -> None:
    css = (WEB / "style.css").read_text(encoding="utf-8")
    body = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    assert "@import" not in body
    assert "url(" not in body, "url() would be a request for a font or an image"


def test_the_shell_loads_the_module_and_the_stylesheet_relatively() -> None:
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert '<script type="module" src="app.js"></script>' in html
    assert '<link rel="stylesheet" href="style.css">' in html
    assert 'name="viewport"' in html, "390 px first needs a viewport meta"
    assert '<html lang="en">' in html


def test_the_unbuilt_regions_are_marked_on_screen_not_just_absent() -> None:
    """T078, T079 and T080 are out of scope here. A blank region reads as a
    bug; a region that says what it is does not."""
    html = (WEB / "index.html").read_text(encoding="utf-8")
    for task in ("T078", "T079", "T080"):
        assert f'data-task="{task}"' in html, f"{task}'s region is not marked"
    assert html.count("Not built yet") == 3


def test_the_shell_does_not_hardcode_a_figure_or_the_licence() -> None:
    """Everything numeric and every licence string is read at runtime.

    The shell may name a measured SIZE in prose (the index is 2.37 MiB) because
    that is a statement about the dataset's shape, not a published figure. What
    it must not do is state a count, a rate or a licence that the record owns.
    """
    html = (WEB / "index.html").read_text(encoding="utf-8")
    body = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    for forbidden in ("95,268", "94.78", "96.36", "CC-BY-4.0", "CC BY 4.0", "Contains data from"):
        assert forbidden not in body, f"index.html hardcodes {forbidden!r}"


def test_the_counting_basis_text_is_not_retyped_in_the_page() -> None:
    """Owner decision: the basis is read from the published file and rendered,
    never copied into the page. Checked against the real published sentence."""
    basis = REPO_ROOT / "data" / "published" / "aggregates" / "counting-basis.jsonl"
    if not basis.is_file():
        pytest.skip("counting-basis not built -- NOT AUDITED, not a pass")
    import json

    sentences = [
        json.loads(line)["counting_basis"]
        for line in basis.read_text().splitlines()
        if line.strip()
    ]
    for name in PAGE_FILES:
        text = (WEB / name).read_text(encoding="utf-8")
        for sentence in sentences:
            # Any run of the published prose long enough to be a copy.
            probe = sentence[:80]
            assert probe not in text, f"{name} contains published basis prose"


def test_the_page_reads_the_basis_and_the_licence_from_the_published_files() -> None:
    """The positive half of the two tests above: it must actually read them."""
    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert "fetchCountingBasis" in app
    assert "counting_basis" in app
    for field in ("license", "license_scope", "attribution", "project_url", "license_file"):
        assert field in app, f"app.js never reads manifest.{field}"


def test_the_search_index_is_not_fetched_on_load() -> None:
    """The laziness is asserted by the page itself at boot, not just intended."""
    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert "loadSearchIndex" not in app, "app.js must not load the index in this part"
    assert "searchIndexRequested()" in app, "boot must assert the index is unrequested"
