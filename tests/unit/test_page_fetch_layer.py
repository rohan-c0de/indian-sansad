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

import importlib.util
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WEB = REPO_ROOT / "web"
PAGE_TESTS = sorted((REPO_ROOT / "tests" / "page").glob("*.test.mjs"))
LIST_PAGE_URLS = REPO_ROOT / "tools" / "list_page_urls.py"

#: Suffixes these checks can read. A file under `web/` with any other suffix
#: fails `test_every_file_under_web_is_scanned` rather than being skipped.
PAGE_SUFFIXES = frozenset({".html", ".css", ".js"})

#: Every file that ships as part of the page. GLOBBED, never listed.
#:
#: This was a hand-kept tuple, and the hand-kept copy in
#: `tools/list_page_urls.py` proved the failure mode: it named five files while
#: `web/` held nine, so `lib/coverage.js`, `lib/profile.js`, `lib/chart.js` and
#: `lib/licence.js` went unscanned by that tool and nothing failed when each was
#: added. Collected at import time so `@pytest.mark.parametrize` can name each
#: file, and asserted complete below.
PAGE_FILES = tuple(sorted(str(p.relative_to(WEB)) for p in WEB.rglob("*") if p.is_file()))


def test_node_is_available_and_the_page_tests_exist() -> None:
    """Without this the suite could pass by silently skipping the only tests
    that exercise the refusal."""
    assert shutil.which("node"), "Node is required to run the page's tests"
    assert PAGE_TESTS, "no tests/page/*.test.mjs found"


def test_every_file_under_web_is_scanned() -> None:
    """Nothing ships in `web/` without these checks reading it.

    Three separate ways the scans could go blind, all closed here:

    1. **A file nobody added to a list.** `PAGE_FILES` is a glob now, so this
       asserts the glob matched something plausible rather than silently
       nothing -- a glob that stopped matching would turn every parametrised
       scan below into zero tests, which pytest reports as a pass.
    2. **A file these checks cannot read.** An image, a font or a wasm blob is
       a request the text scans cannot see. It fails here instead of being
       skipped.
    3. **`tools/list_page_urls.py` disagreeing.** The maintainer-facing tool
       does its own host scan, and it is the one that was stale: it named five
       files while `web/` held nine. Its list is a glob now too, and this pins
       the two together so they cannot drift apart again.
    """
    on_disk = sorted(str(p.relative_to(WEB)) for p in WEB.rglob("*") if p.is_file())
    assert on_disk, "web/ is empty, or the glob stopped matching"
    assert len(on_disk) >= 9, f"only {len(on_disk)} file(s) under web/; the glob looks wrong"
    assert sorted(PAGE_FILES) == on_disk

    unreadable = [name for name in on_disk if (WEB / name).suffix not in PAGE_SUFFIXES]
    assert unreadable == [], (
        f"these files ship in web/ but no check here can read them: {unreadable}. "
        "Add the suffix to PAGE_SUFFIXES deliberately, or do not ship the file."
    )

    spec = importlib.util.spec_from_file_location("sansad_list_page_urls", LIST_PAGE_URLS)
    assert spec and spec.loader
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    assert sorted(tool.page_files()) == on_disk, (
        "tools/list_page_urls.py scans a different set of files than these tests do"
    )
    assert tool.PAGE_SUFFIXES == PAGE_SUFFIXES


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


def test_no_region_of_the_page_is_unbuilt() -> None:
    """T078, T079 and T080 are all built now.

    This test previously asserted the OPPOSITE for T079 -- that the region said
    "Not built yet" on screen, because its measurement gate had failed. The
    gate was then re-measured against the published search digest
    (`spike/size-budget.md` -> T079: a common word at 3,999,739 B, -4.4% under
    T019's budget) and the view was built, so the assertion is inverted rather
    than deleted: a `data-task` marker or a "Not built yet" string reappearing
    in the shell is a region that silently stopped working.
    """
    html = (WEB / "index.html").read_text(encoding="utf-8")
    for built in ("T078", "T079", "T080"):
        assert f'data-task="{built}"' not in html, f"{built} is built; its region should be gone"
    assert "Not built yet" not in html
    assert "measurement gate failed" not in html
    # The real containers the three built views render into.
    for node_id in (
        "profile-picker",
        "profile-result",
        "search-form-host",
        "search-result",
        "compare-picker",
        "compare-result",
    ):
        assert f'id="{node_id}"' in html, f"{node_id} is missing"


def test_the_search_view_is_keyboard_operable_and_labelled() -> None:
    """A search box reachable only by mouse is a search box most readers of a
    public record cannot use.

    Asserted on the code rather than the rendered page because no browser runs
    here -- T082 drives the real thing. What is asserted is the shape that
    makes it work: a real `<form>` (so Enter submits), a `<label>` bound to the
    input by `htmlFor`, a submit button, and a politely-announced result
    region.
    """
    app = (WEB / "app.js").read_text(encoding="utf-8")
    body = re.sub(r"/\*.*?\*/", "", app, flags=re.S)
    assert 'el("form", "search-form")' in body, "the search box is not a form"
    assert 'form.addEventListener("submit"' in body, "Enter in the field would not search"
    assert "event.preventDefault()" in body, "submitting would navigate; there is no server"
    assert 'label.htmlFor = "search-query"' in body, "the input has no bound label"
    assert 'input.id = "search-query"' in body
    assert 'submit.type = "submit"' in body
    # Announced politely: a reader who submits is told the outcome without
    # focus being yanked out from under them.
    assert 'result.setAttribute("role", "status")' in body
    assert 'result.setAttribute("aria-live", "polite")' in body
    assert 'input.setAttribute("aria-describedby", "search-help")' in body
    # Focus after "Show 25 more" lands on the first NEW result.
    assert "focusFrom" in body
    assert "subject.tabIndex = -1" in body


def test_the_result_order_is_rendered_from_the_code_not_retyped() -> None:
    """The order sentence on screen and the comparator that produces it must be
    one thing. `ORDER_STATEMENT` lives in `web/lib/search.js` beside the sort,
    and the page renders it -- so the page cannot describe an order it does not
    implement."""
    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert "ORDER_STATEMENT" in app, "the page never renders the order statement"
    assert 'el("p", "order-text", ORDER_STATEMENT)' in app
    # And the sentence itself is not duplicated into the page or the shell.
    for name in PAGE_FILES:
        if name == "lib/search.js":
            continue
        text = (WEB / name).read_text(encoding="utf-8")
        assert "Newest session first" not in text, f"{name} retypes the order statement"


def test_no_match_is_labelled_near_identical_or_similar() -> None:
    """Owner decision 2026-10-10. The published index carries no grade, so a
    page that graded a match would present an unmeasured judgement as a
    property of the data. Checked over every page file, code and prose alike --
    the prohibition is on what a reader can be shown, so a comment proposing
    the label is as much a problem as the label."""
    forbidden = ("near-identical", "near identical", "most relevant", "best match", "closest match")
    offenders = []
    for name in PAGE_FILES:
        text = (WEB / name).read_text(encoding="utf-8").lower()
        for word in forbidden:
            if word in text:
                offenders.append(f"{name} contains {word!r}")
    assert offenders == [], "a match grade reached the page: " + "; ".join(offenders)

    # "similar" is checked separately: it is an ordinary English word, so the
    # ban is on it being used ABOUT a result. Any occurrence at all in these
    # files would need reading, so none is allowed and the exemption list is
    # empty rather than unstated.
    for name in PAGE_FILES:
        text = (WEB / name).read_text(encoding="utf-8").lower()
        assert "similar" not in text, f"{name} contains 'similar'"


def test_the_search_view_renders_no_position_number() -> None:
    """The results are an `<ol>` so a screen reader announces "3 of 25", but
    the numbers are NOT shown: a visible 1, 2, 3 reads as a ranking, and
    nothing here is ranked."""
    css = (WEB / "style.css").read_text(encoding="utf-8")
    block = css[css.index(".result-list {") :]
    rule = block[: block.index("}")]
    assert "list-style: none" in rule, "the result list shows its numbers"
    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert 'el("ol", "result-list")' in app, "the list is not an ordered list"


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
            # Owner decision 2026-10-10: the source-terms disclosure. Listed
            # here so the hardcoding test below covers it -- if either value
            # were typed into the page there would be two definitions, and the
            # one a visitor reads would be the one nobody re-measures.
            "source_terms",
            "corrections_url",
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


def test_the_page_reads_the_source_terms_disclosure_from_the_manifest() -> None:
    """Owner decision 2026-10-10. Both statements are rendered, and both are
    read from `manifest.json` rather than typed into the page.

    The negative half is `test_the_page_hardcodes_nothing_the_record_supplies`
    above, which now carries `source_terms` and `corrections_url` and so fails
    if either published value appears as a literal in any page file.
    """
    licence = (WEB / "lib" / "licence.js").read_text(encoding="utf-8")
    for field in ("source_terms", "corrections_url"):
        assert f"manifest.{field}" in licence, f"licence.js never reads manifest.{field}"
    # The footer has to call it, or the module renders for nobody.
    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert 'from "./lib/licence.js"' in app
    assert "renderDisclosure(" in app


def test_the_corrections_link_is_https_only_and_opened_safely() -> None:
    """The one link on this page a reader is directed to ACT on, and the one
    place a published string reaches `href`. `javascript:` in an href executes
    on click, so the scheme is checked rather than trusted.

    `tests/page/licence-footer.test.mjs` proves the refusal by executing it --
    including that NO node acquires an href when the value is not https. This
    asserts the rule is still written down where that test can reach it.
    """
    licence = (WEB / "lib" / "licence.js").read_text(encoding="utf-8")
    body = re.sub(r"/\*.*?\*/", "", licence, flags=re.S)
    assert 'startsWith("https://")' in body, "the scheme check is gone"
    assert 'link.rel = "noopener noreferrer"' in body
    assert 'link.target = "_blank"' in body
    # The href is set from the CHECKED value and from nothing else. The raw
    # field may be read (and displayed), but it may not reach an href.
    assert "link.href = href;" in body
    assert ".href = manifest." not in body, "a raw manifest field reaches an href"
    assert ".href = url" not in body, "the unchecked value reaches an href"


def _function_body(source: str, name: str) -> str:
    """One top-level function's body, by name.

    Sliced from its signature to the next `}` in column 0 -- every top-level
    function in `web/app.js` closes that way, and brace-counting through
    template literals would need a lexer to be correct. Raises rather than
    returning "" if the function is not found: a silently empty body would make
    the assertions below pass by finding nothing.
    """
    match = re.search(rf"^(?:export )?(?:async )?function {re.escape(name)}\(", source, re.M)
    assert match, f"{name}() is not defined in app.js"
    rest = source[match.start() :]
    end = re.search(r"^\}", rest[1:], re.M)
    assert end, f"{name}() has no closing brace in column 0"
    return rest[: end.end() + 1]


def test_the_function_body_helper_actually_slices_a_function() -> None:
    """The helper above is load-bearing for the laziness test: if it returned
    the whole file, or nothing, that test would pass for the wrong reason."""
    app = (WEB / "app.js").read_text(encoding="utf-8")
    body = re.sub(r"/\*.*?\*/", "", app, flags=re.S)
    boot = _function_body(body, "boot")
    assert boot.startswith("export async function boot(")
    assert "await bootViews(doc)" in boot, "the slice stopped short of the end of boot()"
    assert "function bootViews" not in boot, "the slice ran past the end of boot()"
    assert len(boot) < len(body) / 2, "the slice is most of the file; it is not slicing"
    views = _function_body(body, "bootViews")
    assert "buildCompareView(doc)" in views
    assert "buildSearchView(doc)" in views
    assert "function resultItem" not in views, "the slice ran past the end of bootViews()"


def test_no_search_file_is_fetched_on_load() -> None:
    """The laziness is asserted by the page itself at boot, not just intended.

    This test used to assert `loadSearchIndex` appeared nowhere in `app.js`,
    which was right while T079 was unbuilt and is now the wrong shape: the
    search handler has to call it. What survives is the part that matters --
    the index is loaded from the SEARCH PATH and from nowhere else, and boot
    asserts that no search file has been touched before it renders.

    `searchAssetsRequested`, not `searchIndexRequested`: the narrower check
    would pass while a digest was already in flight, and a digest is up to
    1,573,939 B.
    """
    app = (WEB / "app.js").read_text(encoding="utf-8")
    body = re.sub(r"/\*.*?\*/", "", app, flags=re.S)

    assert "searchAssetsRequested()" in body, "boot must assert NO search file is requested"
    assert "a search file was requested during boot" in body, (
        "the boot assertion has lost its message"
    )

    # The three lazy loaders are called from the search path only. `boot` and
    # `bootViews` run on page load; neither may name one.
    for loader in ("loadSearchIndex", "loadAskerNames", "loadSearchDigest"):
        assert loader in body, f"{loader} is never called; the view cannot work"
    for loader in ("loadSearchIndex", "loadAskerNames", "loadSearchDigest"):
        for runs_on_load in ("boot", "bootViews"):
            called = _function_body(body, runs_on_load)
            assert loader not in called, f"{runs_on_load}() calls {loader}; it must be lazy"

    # And the index is loaded in exactly one place, so there is one thing to
    # reason about when asking what a first search costs.
    assert body.count("loadSearchIndex(") == 1, "loadSearchIndex is called more than once"
    assert body.count("loadAskerNames(") == 1


# ---------------------------------------------------------------------------
# Every custom property and every class the page names must actually exist.
# ---------------------------------------------------------------------------

_VAR_REF = re.compile(r"var\(\s*(--[A-Za-z0-9-]+)")
_VAR_DEF = re.compile(r"^\s*(--[A-Za-z0-9-]+)\s*:", re.M)
#: `var(--x, <anything>)` -- a reference carrying a fallback value.
_VAR_FALLBACK = re.compile(r"var\(\s*(--[A-Za-z0-9-]+)\s*,")


def test_every_custom_property_the_page_uses_is_defined() -> None:
    """An undefined `var(--x)` fails SILENTLY — a CSS property with an invalid
    value falls back to its initial value, so a fill becomes black and a swatch
    becomes transparent with no error anywhere. That is how `--bar-unstarred`
    shipped: `chart.js` named it, `style.css` never defined it, every unstarred
    bar rendered black and the legend swatch rendered blank.

    A fallback (`var(--x, #fff)`) is not a definition either: it is a second,
    undocumented palette hiding behind the first.
    """
    css = (WEB / "style.css").read_text(encoding="utf-8")
    defined = set(_VAR_DEF.findall(css))

    referenced: dict[str, list[str]] = {}
    for path in sorted(WEB.rglob("*")):
        if not path.is_file() or path.suffix not in {".css", ".js", ".html"}:
            continue
        for name in _VAR_REF.findall(path.read_text(encoding="utf-8")):
            referenced.setdefault(name, []).append(str(path.relative_to(WEB)))

    missing = {name: files for name, files in sorted(referenced.items()) if name not in defined}
    assert missing == {}, f"used but never defined in style.css: {missing}"


def test_no_var_reference_carries_a_fallback() -> None:
    """Owner decision 2026-10-10: every custom property is defined, so no
    `var(--x, …)` may carry a fallback.

    A fallback is a SECOND palette. It is invisible in `:root`, it never shows
    up when the defined palette is audited, and it is reached in exactly the
    case nobody is watching — when the real definition is missing or
    misspelled. One of the three removed here, `#8A93A3`, was below the 3:1
    non-text floor on `--ground`, so the fallback was not merely a duplicate:
    it was a worse value waiting for a typo.
    """
    offenders: list[str] = []
    for path in sorted(WEB.rglob("*")):
        if not path.is_file() or path.suffix not in {".css", ".js", ".html"}:
            continue
        text = path.read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), start=1):
            for match in _VAR_FALLBACK.finditer(line):
                offenders.append(f"{path.relative_to(WEB)}:{number} var({match.group(1)}, …)")
    assert offenders == [], "var() references carrying a fallback: " + "; ".join(offenders)


def test_every_class_the_page_sets_has_a_rule_or_is_a_known_hook() -> None:
    """`.visually-hidden` was named by app.js and defined nowhere, so a caption
    meant to be off-screen rendered visibly and clipped. Classes used purely as
    state hooks are listed, so adding one is a decision rather than an
    accident."""
    css = (WEB / "style.css").read_text(encoding="utf-8")
    styled = set(re.findall(r"\.([A-Za-z][A-Za-z0-9_-]*)", css))
    hooks = {"card", "container"}  # structural, always paired with another class

    used: set[str] = set()
    for path in (WEB / "app.js", WEB / "lib" / "chart.js", WEB / "lib" / "licence.js"):
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        # `licence.js` names its local helper `node` rather than `el`; the
        # argument shape is the same, so one pattern covers both.
        for match in re.finditer(r'(?:el|node)\(\s*"[a-z]+"\s*,\s*"([^"]+)"', text):
            used.update(match.group(1).split())
        for match in re.finditer(r'\.className\s*=\s*"([^"]+)"', text):
            used.update(match.group(1).split())
        for match in re.finditer(r'classList\.add\(\s*"([^"]+)"', text):
            used.update(match.group(1).split())

    missing = sorted(name for name in used - styled - hooks)
    assert missing == [], f"classes the page sets but style.css never styles: {missing}"
