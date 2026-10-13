"""The view map, pinned. T127.

These are STATIC assertions about the router's declaration -- the ids, the
module specifiers, the landing view, and the correspondence between the map,
the navigation and the containers in `index.html`.

**What they do not establish.** No browser runs here, so nothing in this file
proves a hash actually renders a view, that the others are hidden, that focus
moves, or that returning refetches nothing. That is `tools/drive_page.mjs`'s
job (T190), and it is a genuinely different claim: this module can only show
that the three places the view set is written down agree with each other.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WEB = REPO_ROOT / "web"
APP = WEB / "app.js"
INDEX = WEB / "index.html"

#: The seven views, in the order the router declares them.
#:
#: These ids are a PUBLIC INTERFACE -- a reader may link to `#composition` --
#: so this list is the thing that makes renaming one a deliberate, visible act
#: rather than a refactor nobody noticed.
#:
#: SEVEN, not the eight `contracts/view-routes.md` first listed. `licence` was
#: planned as the eighth and was wrong: the licence, the attribution and the
#: source-terms disclosure live in the page footer, outside <main>, so they
#: render on every view. Feature 001 put them there deliberately, and turning
#: the disclosure into a page a reader opts into would have been a regression.
EXPECTED_VIEWS: tuple[tuple[str, str | None], ...] = (
    ("coverage", None),
    ("search", "./views/search.js"),
    ("seat", "./views/seat.js"),
    ("ministry", "./views/ministries.js"),
    ("compare", "./views/ministries.js"),
    ("load", "./views/ministries.js"),
    ("composition", "./views/composition.js"),
)

LANDING = "coverage"

_ENTRY = re.compile(
    r'\{\s*id:\s*"([a-z-]+)"\s*,\s*heading:\s*"[^"]+"\s*,\s*module:\s*(null|"[^"]+")\s*\}'
)


def declared_views() -> list[tuple[str, str | None]]:
    """The view map as `app.js` declares it."""
    source = APP.read_text(encoding="utf-8")
    out: list[tuple[str, str | None]] = []
    for view_id, module in _ENTRY.findall(source):
        out.append((view_id, None if module == "null" else module.strip('"')))
    return out


def test_the_view_map_is_exactly_the_expected_set() -> None:
    assert declared_views() == list(EXPECTED_VIEWS)


def test_every_view_id_is_unique() -> None:
    ids = [v for v, _ in declared_views()]
    assert len(ids) == len(set(ids)), f"a duplicate view id would shadow a route: {ids}"


def test_every_module_specifier_is_relative() -> None:
    """A bare specifier would need a bundler or an import map; either way a
    build step, and there is not one."""
    for view_id, module in declared_views():
        if module is None:
            continue
        assert module.startswith("./"), f"{view_id} names a non-relative module {module!r}"


def test_every_named_module_exists() -> None:
    """A specifier pointing at nothing fails at runtime in the one place a
    reader notices -- when they open that view -- and passes every static
    check. So it is checked here."""
    for view_id, module in declared_views():
        if module is None:
            continue
        target = WEB / module.removeprefix("./")
        assert target.is_file(), f"{view_id} names {module!r}, which does not exist"


def test_every_view_module_exports_a_mount_function() -> None:
    """The router calls `mod.mount(doc, id)`. A module without it throws on
    first open, and the router would report "this view could not be loaded"
    for what is really a missing export."""
    for view_id, module in declared_views():
        if module is None:
            continue
        source = (WEB / module.removeprefix("./")).read_text(encoding="utf-8")
        assert re.search(r"^export async function mount\(", source, re.M), (
            f"{module} has no exported `mount` function, so view {view_id!r} cannot mount"
        )


def test_the_landing_view_is_the_coverage_statement() -> None:
    """FR-153. What the record claims to cover is read before anything drawn
    from it, and an unknown hash lands here rather than on an error."""
    source = APP.read_text(encoding="utf-8")
    assert re.search(rf'const LANDING = "{LANDING}";', source), (
        "the landing view is not the coverage statement"
    )
    assert declared_views()[0][0] == LANDING, "the landing view is not declared first"


def test_the_landing_view_needs_no_module() -> None:
    """It is rendered by the shell, from data already on the first load. A
    module here would put a deferred import on the critical path."""
    first_id, first_module = declared_views()[0]
    assert first_module is None, f"the landing view {first_id!r} defers to {first_module!r}"


def test_every_view_has_a_container_in_the_page() -> None:
    html = INDEX.read_text(encoding="utf-8")
    for view_id, _ in declared_views():
        assert f'id="view-{view_id}"' in html, f"no container for view {view_id!r} in index.html"


def test_every_view_but_the_landing_one_starts_hidden() -> None:
    """The router manages `hidden` after the first render, but the markup must
    arrive correct: a page whose seven views are all visible before the module
    runs flashes the whole document at every visitor on every load."""
    html = INDEX.read_text(encoding="utf-8")
    for view_id, _ in declared_views():
        tag = re.search(rf'<section class="view[^"]*" id="view-{view_id}"[^>]*>', html)
        assert tag, f"no <section> for view {view_id!r}"
        if view_id == LANDING:
            assert "hidden" not in tag.group(0), "the landing view must not start hidden"
        else:
            assert "hidden" in tag.group(0), f"view {view_id!r} does not start hidden"


def test_every_view_has_a_navigation_link() -> None:
    html = INDEX.read_text(encoding="utf-8")
    for view_id, _ in declared_views():
        assert f'href="#{view_id}" data-view="{view_id}"' in html, (
            f"view {view_id!r} has no navigation link, so it is reachable only by typing a hash"
        )


def test_the_navigation_has_no_link_to_a_view_that_does_not_exist() -> None:
    """The other direction. A stale link is worse than a missing one: it looks
    like a view and resolves to the landing page, which reads as a bug."""
    html = INDEX.read_text(encoding="utf-8")
    linked = set(re.findall(r'data-view="([a-z-]+)"', html))
    declared = {v for v, _ in declared_views()}
    assert linked == declared, f"navigation links {linked} against views {declared}"


def test_every_view_container_has_a_heading_for_focus_to_land_on() -> None:
    """The router moves focus to the view's heading on switch. Without one, a
    keyboard reader is left where the old -- now hidden -- view was.

    This was a real failure and not a hypothetical: a view whose module threw
    had its heading destroyed by the error renderer, and the measured result
    was `document.activeElement === body`.
    """
    html = INDEX.read_text(encoding="utf-8")
    for view_id, _ in declared_views():
        block = re.search(
            rf'<section class="view[^"]*" id="view-{view_id}".*?</section>', html, re.S
        )
        assert block, f"no <section> for view {view_id!r}"
        assert re.search(r"<h[12][ >]", block.group(0)), (
            f"view {view_id!r} has no <h1> or <h2>, so focus has nothing to land on"
        )


def test_the_licence_is_outside_the_views_so_it_shows_on_every_one() -> None:
    """The source-terms disclosure is a standing obligation, not a view.

    Feature 001 put the licence, the attribution and the "source terms: not
    determined" disclosure in the footer so they are visible wherever a reader
    is. This asserts the router cannot have quietly swallowed them: the footer
    must still be outside <main>, where no view's `hidden` can reach it.
    """
    html = INDEX.read_text(encoding="utf-8")
    main_end = html.index("</main>")
    footer_start = html.index("<footer")
    assert footer_start > main_end, "the footer moved inside <main>, where a view can hide it"
    assert 'id="licence-body"' in html[footer_start:], "the licence block is not in the footer"
