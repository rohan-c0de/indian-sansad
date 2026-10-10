#!/usr/bin/env python3
"""List every URL the page can request, without running a browser.

Two halves, because either alone would be misleading:

1. **The declared surface.** `web/lib/fetch.js` names every published file in
   one frozen object, `PUBLISHED_FILES`, and builds each URL with
   `PUBLISHED_BASE`. Those are read out of the source here.
2. **Anything else that looks like a URL.** A declared list proves what the
   page *means* to request; a scan proves nothing else crept in. Comments are
   stripped first -- a URL in prose is documentation, a URL in code is a
   request, and a check that cannot tell them apart is unusable in a codebase
   that explains itself.

Exits non-zero if any requestable URL is not relative, or if any page file
names another host in code.

This is a static check. It does not establish what a real browser does; T082
does that from an actual network log.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB = REPO_ROOT / "web"

PAGE_FILES = ("index.html", "style.css", "app.js", "lib/fetch.js", "lib/format.js")

PUBLISHED_BASE_PREFIX = "./data/published/"

_OFF_HOST = re.compile(r"(?:https?:)?//[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_BASE = re.compile(r"""PUBLISHED_BASE\s*=\s*["']([^"']+)["']""")
_ENTRY = re.compile(r"""^\s*([A-Za-z][A-Za-z0-9]*)\s*:\s*["']([^"']+)["'],?\s*$""", re.M)


def strip_comments(text: str, *, html: bool = False) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    if html:
        text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    kept = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("//", "*")):
            continue
        kept.append(line)
    return "\n".join(kept)


def declared_urls() -> list[tuple[str, str]]:
    source = (WEB / "lib" / "fetch.js").read_text(encoding="utf-8")
    base_match = _BASE.search(source)
    if not base_match:
        raise SystemExit("could not find PUBLISHED_BASE in web/lib/fetch.js")
    base = base_match.group(1)

    block = source.split("PUBLISHED_FILES = Object.freeze({", 1)
    if len(block) != 2:
        raise SystemExit("could not find PUBLISHED_FILES in web/lib/fetch.js")
    body = block[1].split("});", 1)[0]
    return [(name, base + path) for name, path in _ENTRY.findall(body)]


#: Requested as soon as the page loads, versus on demand. Read off app.js.
def eager_names(declared: list[tuple[str, str]]) -> set[str]:
    app = strip_comments((WEB / "app.js").read_text(encoding="utf-8"))
    fetched = set()
    for name, _ in declared:
        # app.js calls the named helper, e.g. fetchCoverage for `coverage`.
        helper = "fetch" + name[0].upper() + name[1:]
        if helper in app:
            fetched.add(name)
    return fetched


def main() -> int:
    declared = declared_urls()
    eager = eager_names(declared)

    print("Every URL this page can request")
    print("=" * 92)
    print(f"{'when':<11}{'name':<17}{'bytes':>12}  url")
    print("-" * 92)
    problems: list[str] = []
    published = REPO_ROOT / "data" / "published"
    eager_bytes = lazy_bytes = 0
    missing = False
    for name, url in declared:
        when = "on load" if name in eager else "on demand"
        path = published / url[len(PUBLISHED_BASE_PREFIX) :]
        if path.is_file():
            size = path.stat().st_size
            if name in eager:
                eager_bytes += size
            else:
                lazy_bytes += size
            shown = f"{size:,}"
        else:
            shown = "NOT BUILT"
            missing = True
        print(f"{when:<11}{name:<17}{shown:>12}  {url}")
        if not url.startswith("./"):
            problems.append(f"{name}: {url} is not a relative path")
        if url.startswith("//") or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", url):
            problems.append(f"{name}: {url} is absolute or protocol-relative")
    print("-" * 92)
    print(f"{len(declared)} URL(s): {len(eager)} on load, {len(declared) - len(eager)} on demand")
    if missing:
        print("  (sizes are from the locally built dataset; some files are NOT BUILT)")
    else:
        print(f"  on load  : {eager_bytes:>12,} B   = {eager_bytes / 1048576:.2f} MiB")
        print(f"  on demand: {lazy_bytes:>12,} B   = {lazy_bytes / 1048576:.2f} MiB")
        print(f"  all      : {eager_bytes + lazy_bytes:>12,} B")
        print()
        print("  Against T019's budgets (spike/size-budget.md):")
        print(
            f"    ministry-profile view, 904,231 B   -> on load is "
            f"{100 * eager_bytes / 904231 - 100:+.1f}%"
        )
        print(
            f"    with subject search, 4,183,979 B   -> on load + index is "
            f"{100 * (eager_bytes + lazy_bytes) / 4183979 - 100:+.1f}%"
        )
    print()
    print("Outbound LINKS (not requests -- nothing is fetched unless clicked):")
    print("  manifest.project_url, rendered in the footer from the published manifest")
    print()

    print("Scan for any other host named in page code")
    print("=" * 64)
    found = False
    for name in PAGE_FILES:
        path = WEB / name
        text = strip_comments(path.read_text(encoding="utf-8"), html=name.endswith(".html"))
        for number, line in enumerate(text.splitlines(), start=1):
            for match in _OFF_HOST.finditer(line):
                found = True
                problems.append(f"{name}: names host {match.group(0)}")
                print(f"  {name}:{number}  {match.group(0)}")
    if not found:
        print("  none -- no page file names another host in code")
    print()

    css = strip_comments((WEB / "style.css").read_text(encoding="utf-8"))
    for token in ("@import", "url("):
        if token in css:
            problems.append(f"style.css contains {token}")
            print(f"  style.css contains {token}")

    if problems:
        print("FAIL:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("PASS -- every requestable URL is relative, and no other host is named.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
