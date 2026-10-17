#!/usr/bin/env python3
"""Check that every page parses and every local reference resolves.

Walks all .html files in the repository, and for each href/src that is not an
external URL, verifies that the target file exists and that any fragment names
an id that exists on the target page. Also reports duplicate ids, which break
in-page navigation silently.

    python3 tools/check_links.py
"""

from __future__ import annotations

import html.parser
import pathlib
import sys
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "_site", "node_modules"}


class Page(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.refs: list[str] = []
        self.ids: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if a.get("id"):
            self.ids.append(a["id"])
        for key in ("href", "src"):
            value = a.get(key)
            if value:
                self.refs.append(value)


def pages() -> dict[pathlib.Path, Page]:
    parsed = {}
    for path in sorted(ROOT.rglob("*.html")):
        if SKIP_DIRS & set(path.relative_to(ROOT).parts):
            continue
        page = Page()
        page.feed(path.read_text())
        parsed[path] = page
    return parsed


def main() -> int:
    parsed = pages()
    if not parsed:
        print("no HTML files found", file=sys.stderr)
        return 1

    errors: list[str] = []
    for path, page in parsed.items():
        where = path.relative_to(ROOT)

        duplicates = {i for i in page.ids if page.ids.count(i) > 1}
        for dup in sorted(duplicates):
            errors.append(f"{where}: duplicate id {dup!r}")

        for ref in page.refs:
            parts = urllib.parse.urlparse(ref)
            if parts.scheme or parts.netloc:
                continue  # external, or a data: URI

            if parts.path:
                target = (path.parent / urllib.parse.unquote(parts.path)).resolve()
                if not target.exists():
                    errors.append(f"{where}: missing local file: {ref}")
                    continue
            else:
                target = path

            if parts.fragment:
                page_for_target = parsed.get(target)
                if page_for_target is None:
                    continue  # not an HTML page we parsed; existence already checked
                if parts.fragment not in page_for_target.ids:
                    errors.append(f"{where}: dead anchor: {ref}")

    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print(f"checked {len(parsed)} pages, all local references resolve")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
