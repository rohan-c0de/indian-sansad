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
PAGE_FILES = (
    "index.html",
    "style.css",
    "app.js",
    "lib/fetch.js",
    "lib/format.js",
    "lib/coverage.js",
    "lib/profile.js",
    "lib/chart.js",
)


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


#: The ONE exempt string, exempt for a reason that can itself be checked: it
#: is an XML namespace IDENTIFIER required by `document.createElementNS`, not
#: a URL. Browsers never dereference it, so there is no request. Exempted as
#: an exact string rather than as a host, so anything else on w3.org is still
#: a finding.
SVG_NAMESPACE = "http://www.w3.org/2000/svg"


@pytest.mark.parametrize("name", PAGE_FILES)
def test_no_page_file_names_another_host(name: str) -> None:
    """No CDN, no web font, no analytics, no beacon — in code, not just intent."""
    offenders = []
    for number, line in _code_lines(WEB / name):
        for match in _OFF_HOST.finditer(line):
            if SVG_NAMESPACE in line and match.group(0) in SVG_NAMESPACE:
                continue
            offenders.append((number, line.strip()))
    assert offenders == [], f"{name} names an outside host: {offenders}"


def test_the_svg_namespace_is_used_only_as_a_namespace() -> None:
    """Keeps the exemption above honest: that string may appear only as the
    argument to createElementNS, never in a fetch, an href or a src."""
    chart = (WEB / "lib" / "chart.js").read_text(encoding="utf-8")
    assert chart.count(SVG_NAMESPACE) == 1
    assert f'const NS = "{SVG_NAMESPACE}"' in chart
    assert "createElementNS(NS" in chart
    for forbidden in ("fetch(NS", "src = NS", "href = NS"):
        assert forbidden not in chart


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


def test_the_only_unbuilt_region_is_the_one_a_gate_stopped() -> None:
    """T078 and T080 are built. T079 is NOT, and that is a measurement result
    rather than unfinished work: showing the first 25 results for a common word
    costs 4,348,529 B against T019's 4,183,979 B budget, and a two-word query
    costs 7,236,751 B. The region has to say so on screen, because a blank
    region reads as a bug and a missing one reads as a feature nobody wanted.
    """
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert 'data-task="T079"' in html, "T079's region is not marked"
    for built in ("T078", "T080"):
        assert f'data-task="{built}"' not in html, f"{built} is built; its region should be gone"
    assert html.count("Not built yet") == 1
    assert "measurement gate failed" in html
    # The real containers the built views render into.
    for node_id in ("profile-picker", "profile-result", "compare-picker", "compare-result"):
        assert f'id="{node_id}"' in html, f"{node_id} is missing"


#: Every field the page reads out of manifest.json or coverage.jsonl. A value
#: of one of these must never appear as a literal anywhere in web/.
_RUNTIME_FIELDS = (
    (
        "manifest.json",
        None,
        (
            "license",
            "attribution",
            "project_url",
            "license_file",
            "license_scope",
            "last_refreshed",
        ),
    ),
    (
        "coverage.jsonl",
        "lok-sabha",
        (
            "total_questions",
            "resolved_automatic",
            "resolved_including_assertions",
            "assertions_in_effect",
            "assertions_overriding_an_automatic_match",
            "ministry_ids",
            "ministry_names_observed",
            "ministry_names_without_confirmed_mapping",
            "sessions_covered_count",
            "period_start",
            "period_end",
            "houses_covered",
            "last_refreshed",
            "sc_002_target",
        ),
    ),
)


def _published_values() -> dict[str, object]:
    """The live values of every field the page reads at runtime."""
    import json

    root = REPO_ROOT / "data" / "published"
    out: dict[str, object] = {}
    for name, house, fields in _RUNTIME_FIELDS:
        path = root / name
        if not path.is_file():
            continue
        if name.endswith(".jsonl"):
            rows = [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]
            record = next((r for r in rows if r.get("house") == house), rows[0])
        else:
            record = json.loads(path.read_text())
        for field in fields:
            if field in record:
                out[f"{name}:{field}"] = record[field]
    return out


def test_the_page_hardcodes_nothing_the_record_supplies() -> None:
    """Fix (e). Checked against the LIVE values, not a fixed list of strings.

    An earlier version of this test listed six literals by hand. That catches
    the six and nothing else, and it goes stale the moment a figure changes —
    the same failure mode as the hand-typed test count in the README. This
    reads every field the page is known to render and asserts none of their
    values appears as a literal in any page file.

    Prose about the dataset's SHAPE is still allowed (the index is 2.37 MiB):
    that is a statement about a file, not a figure the record owns.
    """
    values = _published_values()
    if not values:
        pytest.skip("data/published/ not built -- NOT AUDITED, not a pass")
    assert len(values) > 15, f"only {len(values)} runtime fields found"

    offenders: list[str] = []
    for name in PAGE_FILES:
        text = (WEB / name).read_text(encoding="utf-8")
        body = re.sub(r"<!--.*?-->", "", text, flags=re.S)
        body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
        for key, value in values.items():
            if not isinstance(value, (str, int, float)) or isinstance(value, bool):
                continue
            literal = str(value)
            # Short values (a year, a small count) collide with ordinary code.
            if len(literal) < 6:
                continue
            if literal in body:
                offenders.append(f"{name} contains {key} = {literal[:60]!r}")
            grouped = f"{value:,}" if isinstance(value, int) else None
            if grouped and len(grouped) >= 6 and grouped in body:
                offenders.append(f"{name} contains {key} as {grouped!r}")
    assert offenders == [], "the page hardcodes what the record supplies:\n" + "\n".join(offenders)


def test_the_houses_claim_is_derived_not_typed() -> None:
    """Fix (a). The words must come out of a function over the coverage rows."""
    app = (WEB / "app.js").read_text(encoding="utf-8")
    body = re.sub(r"/\*.*?\*/", "", app, flags=re.S)
    assert "housesClaim(coverage)" in body
    assert '"Lok Sabha only"' not in body, "the claim is typed, not derived"
    assert "Lok Sabha only" not in (WEB / "index.html").read_text(encoding="utf-8")


def test_the_session_table_is_collapsed_and_the_key_figures_are_not() -> None:
    """Fix (b). The table is behind <details>; the figures above it are not."""
    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert 'el("details", "sessions")' in app
    assert 'el("summary")' in app
    assert "sessions`" in app, "the summary must state the session count"
    # The figures that stay visible are rendered into the fact grid, not the
    # details element: the grid is appended to the fragment before it.
    assert app.index('el("div", "fact-grid")') < app.index("renderSessions(lok, sessions)")


def test_zero_sitting_days_is_flagged_in_words() -> None:
    """Fix (c). Text, never colour alone, and n/a rather than a division."""
    coverage_js = (WEB / "lib" / "coverage.js").read_text(encoding="utf-8")
    assert "ZERO_SITTING_DAYS_FLAG" in coverage_js
    assert "0 sitting days as published" in coverage_js
    assert 'NOT_APPLICABLE = "n/a"' in coverage_js
    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert "ZERO_SITTING_DAYS_FLAG" in app


def test_the_project_link_opens_in_a_new_tab_safely() -> None:
    """Fix (d)."""
    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert 'a.target = "_blank"' in app
    assert 'a.rel = "noopener noreferrer"' in app


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
