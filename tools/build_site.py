#!/usr/bin/env python3
"""Render the generated parts of the site from content/.

The site itself stays build-free: this script writes plain static HTML into
cryptanalysis/, notes/ and schemes/, and that output is committed. CI re-runs
the script and fails if the committed pages differ, so the content and the
HTML cannot drift apart. Worked examples are recomputed on every run, so the
same check also proves that every number on those pages is still what the
code produces.

    python3 tools/build_site.py          # write the pages
    python3 tools/build_site.py --check  # fail if any page is stale
"""

from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from sitegen.collections import COLLECTIONS, ROOT, build  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="fail if committed pages are stale")
    args = parser.parse_args()

    pages, errors = build()
    if errors:
        for error in errors:
            print(f"content error: {error}", file=sys.stderr)
        return 1

    if args.check:
        stale = [
            name for name, text in pages.items()
            if not (ROOT / name).exists() or (ROOT / name).read_text() != text
        ]
        orphans = [
            str(path.relative_to(ROOT))
            for collection in COLLECTIONS
            for path in sorted((ROOT / collection).glob("*.html"))
            if str(path.relative_to(ROOT)) not in pages
        ]
        for name in sorted(stale):
            print(f"stale: {name}", file=sys.stderr)
        for name in orphans:
            print(f"orphan: {name} has no content file", file=sys.stderr)
        if stale or orphans:
            print("run: python3 tools/build_site.py", file=sys.stderr)
            return 1
        print(f"{len(pages)} generated pages up to date")
        return 0

    for name, text in pages.items():
        path = ROOT / name
        path.parent.mkdir(exist_ok=True)
        path.write_text(text)
    print(f"wrote {len(pages)} pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
