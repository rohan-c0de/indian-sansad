#!/usr/bin/env python3
"""Serve the page and the dataset from ONE origin and port. T081.

The published-branch layout, mirrored exactly (owner decision 2026-10-10):

    /                       ->  web/index.html
    /style.css              ->  web/style.css
    /app.js                 ->  web/app.js
    /lib/fetch.js           ->  web/lib/fetch.js
    /data/published/...     ->  data/published/...
    /LICENSE                ->  LICENSE
    /DATA-LICENSE.md        ->  DATA-LICENSE.md

One scheme, one host, one port -- so **same origin by definition**, which is
what the page needs rather than what is convenient. `spike/route-capture.md`
T005 verified that the upstream sends no `Access-Control-Allow-Origin`, so a
browser is refused cross-origin reads of it; the page's whole design is to read
this project's own files from its own host, and if those files were on a
different origin from the page it would hit the identical wall against its own
data.

The mapping above is the same one `.github/workflows/refresh.yml` writes to the
`published` branch, so a relative path that resolves here resolves as served.
`tests/unit/test_serve_local.py` asserts the two agree rather than trusting
that they do.

Reads only. Writes nothing, serves nothing outside the two mapped roots, and
refuses a path that escapes them.
"""

from __future__ import annotations

import argparse
import http.server
import mimetypes
import os
import socketserver
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Served at `/` -- the page, exactly as the workflow copies `web/.` to root.
PAGE_ROOT = "web"

#: Served under a prefix -- the dataset, under the same path the page fetches.
#: A tuple so the order is explicit: longest prefix first if more are added.
PREFIX_ROOTS: tuple[tuple[str, str], ...] = (("/data/published/", "data/published"),)

#: Single files the workflow also copies to the branch root.
ROOT_FILES: tuple[str, ...] = ("LICENSE", "DATA-LICENSE.md")

#: Correct types matter for one of these: a module script served as anything
#: but a JavaScript type is REFUSED by the browser, and the page would load
#: with no behaviour and no obvious cause.
EXTRA_TYPES: dict[str, str] = {
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".css": "text/css",
    ".json": "application/json",
    ".jsonl": "text/plain",
    ".csv": "text/csv",
    ".md": "text/plain",
}

DEFAULT_PORT = 8013
DEFAULT_HOST = "127.0.0.1"


def resolve_request(path: str, root: Path = REPO_ROOT) -> Path | None:
    """Map a URL path to a file on disk, or None if it is not served.

    Pure, so the mapping can be tested without a socket.
    """
    clean = path.split("?", 1)[0].split("#", 1)[0]
    if not clean.startswith("/"):
        clean = "/" + clean

    # Refuse traversal before resolving anything.
    if ".." in clean.split("/"):
        return None

    for prefix, target in PREFIX_ROOTS:
        if clean.startswith(prefix):
            relative = clean[len(prefix) :]
            if not relative:
                return None
            candidate = (root / target / relative).resolve()
            base = (root / target).resolve()
            if candidate == base or base in candidate.parents:
                return candidate
            return None

    name = clean.lstrip("/")
    if name in ROOT_FILES:
        return (root / name).resolve()

    if clean.endswith("/"):
        name = name + "index.html"
    if not name:
        name = "index.html"

    candidate = (root / PAGE_ROOT / name).resolve()
    base = (root / PAGE_ROOT).resolve()
    if candidate == base or base in candidate.parents:
        return candidate
    return None


class OneOriginHandler(http.server.BaseHTTPRequestHandler):
    """Serves the mapping above and nothing else."""

    server_version = "sansad-serve-local"
    sys_version = ""

    # Names chosen by BaseHTTPRequestHandler, not by this module.
    def do_GET(self) -> None:
        self._respond(include_body=True)

    def do_HEAD(self) -> None:
        self._respond(include_body=False)

    def _respond(self, *, include_body: bool) -> None:
        target = resolve_request(self.path)
        if target is None or not target.is_file():
            self.send_error(404, "Not served")
            return
        try:
            body = target.read_bytes()
        except OSError:
            self.send_error(404, "Not readable")
            return

        ctype = EXTRA_TYPES.get(target.suffix.lower())
        if ctype is None and target.name in ROOT_FILES:
            # LICENSE has no extension. It is text; say so, or a browser
            # offers to download the licence instead of showing it.
            ctype = "text/plain"
        if ctype is None:
            ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if ctype.startswith(("text/", "application/json")):
            ctype = f"{ctype}; charset=utf-8"

        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        # The published branch is static and immutable per refresh; locally,
        # never cache, so an edit shows up on reload.
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if include_body:
            self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write(f"  {self.address_string()} {fmt % args}\n")


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default=os.environ.get("SANSAD_HOST", DEFAULT_HOST))
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("SANSAD_PORT", DEFAULT_PORT))
    )
    parser.add_argument(
        "--print-mapping",
        action="store_true",
        help="print the URL-to-file mapping and exit, without binding a port",
    )
    args = parser.parse_args(argv)

    page = REPO_ROOT / PAGE_ROOT
    dataset = REPO_ROOT / "data" / "published"

    lines = [
        "serve-local: one origin, one port. The published-branch layout.",
        "",
        f"  /                     -> {PAGE_ROOT}/index.html",
        f"  /<file>               -> {PAGE_ROOT}/<file>        "
        f"({'present' if page.is_dir() else 'MISSING'})",
    ]
    for prefix, target in PREFIX_ROOTS:
        lines.append(
            f"  {prefix}...   -> {target}/...   "
            f"({'present' if (REPO_ROOT / target).is_dir() else 'NOT BUILT'})"
        )
    for name in ROOT_FILES:
        lines.append(
            f"  /{name:<20} -> {name}   "
            f"({'present' if (REPO_ROOT / name).is_file() else 'MISSING'})"
        )
    print("\n".join(lines))

    if args.print_mapping:
        return 0

    if not page.is_dir():
        print(f"\nserve-local: REFUSED -- {PAGE_ROOT}/ does not exist.", file=sys.stderr)
        return 1
    if not dataset.is_dir():
        print(
            "\nserve-local: data/published/ is not built. The page will load and "
            "report that it could not read the published files, which is the "
            "correct behaviour -- but it is not a useful check. Run `make refresh` "
            "first.",
            file=sys.stderr,
        )

    with Server((args.host, args.port), OneOriginHandler) as httpd:
        host, port = httpd.server_address[0], httpd.server_address[1]
        print(f"\nserve-local: http://{host}:{port}/   (ctrl-c to stop)")
        print(f"serve-local: dataset at http://{host}:{port}/data/published/manifest.json")
        sys.stdout.flush()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nserve-local: stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
