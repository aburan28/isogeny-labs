#!/usr/bin/env python3
"""Render the cryptanalysis library from content/cryptanalysis/*.json.

The site itself stays build-free: this script writes plain static HTML into
cryptanalysis/, and that output is committed. CI re-runs the script and fails
if the committed pages differ, so the JSON and the HTML cannot drift apart.

    python3 tools/build_cryptanalysis.py          # write the pages
    python3 tools/build_cryptanalysis.py --check  # fail if they are stale
"""

from __future__ import annotations

import argparse
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content" / "cryptanalysis"
OUT = ROOT / "cryptanalysis"

# Content strings may carry inline HTML and character entities, because every
# one of them is authored in this repository rather than supplied by a user.
# Two renderings are therefore needed:
#
#   T(s) -- inside element content: emit as authored, entities intact.
#   A(s) -- inside an attribute, a <title>, or a slug: strip markup, resolve
#           entities to characters, then escape for the attribute context.
#
# Anything not from a content file (hrefs, generated ids) goes through E.
E = html.escape


def T(value: str) -> str:
    """Authored markup, rendered as-is into element content."""
    return value


def A(value: str) -> str:
    """Authored markup, flattened to escaped plain text for an attribute."""
    return E(html.unescape(re.sub(r"<[^>]+>", "", value)))


def nav(prefix: str, here: str) -> str:
    """Site header. `prefix` reaches the site root; `here` marks the current page."""
    def current(name: str) -> str:
        return ' aria-current="page"' if name == here else ""

    return f"""  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header">
    <div class="wrap">
      <a class="wordmark" href="{prefix}index.html">Isogeny Labs</a>
      <nav class="site-nav" aria-label="Main">
        <a href="{prefix}index.html#work">Work</a>
        <a href="{prefix}index.html#services">Services</a>
        <a href="{prefix}cryptanalysis/index.html"{current('library')}>Cryptanalysis reference</a>
        <a href="{prefix}index.html#contact">Contact</a>
      </nav>
    </div>
  </header>
"""


def footer(prefix: str) -> str:
    return """  <footer class="site-footer">
    <div class="wrap">
      <span>© <span id="year">2026</span> Isogeny Labs</span>
      <a href="https://github.com/aburan28/cryptanalysis">GitHub</a>
    </div>
  </footer>
"""


def page(*, prefix: str, here: str, title: str, description: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#fbfaf6" media="(prefers-color-scheme: light)">
  <meta name="theme-color" content="#161513" media="(prefers-color-scheme: dark)">
  <meta name="description" content="{A(description)}">
  <meta property="og:title" content="{A(title)}">
  <meta property="og:description" content="{E(description)}">
  <meta property="og:type" content="article">
  <title>{A(title)}</title>
  <link rel="icon" type="image/svg+xml" href="{prefix}favicon.svg">
  <link rel="stylesheet" href="{prefix}styles.css">
  <script defer src="{prefix}script.js"></script>
</head>
<body>
{nav(prefix, here)}  <main id="main" class="wrap">
{body}  </main>
{footer(prefix)}</body>
</html>
"""


def render_blocks(blocks: list[dict], indent: str) -> str:
    out = []
    for block in blocks:
        if "p" in block:
            out.append(f"{indent}<p>{block['p']}</p>")
        elif "ul" in block:
            items = "".join(f"{indent}  <li>{item}</li>\n" for item in block["ul"])
            out.append(f"{indent}<ul>\n{items}{indent}</ul>")
        elif "steps" in block:
            items = "".join(f"{indent}  <li>{item}</li>\n" for item in block["steps"])
            out.append(f'{indent}<ol>\n{items}{indent}</ol>')
        elif "math" in block:
            label = block.get("label")
            caption = f'\n{indent}  <span class="math-label">{label}</span>' if label else ""
            out.append(f'{indent}<div class="math">{block["math"]}{caption}</div>')
        elif "note" in block:
            out.append(
                f'{indent}<aside class="note"><p><span class="note-label">'
                f'{T(block.get("note_label", "Where this bites"))}.</span> '
                f'{block["note"]}</p></aside>'
            )
        else:  # pragma: no cover - guarded by validate()
            raise ValueError(f"unknown block: {sorted(block)}")
    return "\n".join(out) + "\n"


def render_technique(entry: dict, by_slug: dict[str, dict]) -> str:
    meta_rows = "".join(
        f'        <div><dt>{T(k)}</dt><dd>{v}</dd></div>\n'
        for k, v in entry["facts"].items()
    )

    toc = "".join(
        f'        <li><a href="#{E(slugify(s["heading"]))}">{T(s["heading"])}</a></li>\n'
        for s in entry["sections"]
    )

    sections = []
    for section in entry["sections"]:
        anchor = slugify(section["heading"])
        sections.append(
            f'      <section id="{E(anchor)}" aria-labelledby="{E(anchor)}-title">\n'
            f'        <h2 id="{E(anchor)}-title">{T(section["heading"])}</h2>\n'
            + render_blocks(section["blocks"], "        ")
            + "      </section>"
        )

    references = "".join(
        f'        <li><a href="{E(r["href"])}">{T(r["text"])}</a></li>\n'
        for r in entry.get("references", [])
    )
    references_block = (
        '      <section class="references" id="references" aria-labelledby="references-title">\n'
        '        <h2 id="references-title">Primary sources</h2>\n'
        f"        <ol>\n{references}        </ol>\n"
        "      </section>"
        if references
        else ""
    )

    related = "".join(
        f'        <li><a href="{E(slug)}.html">{T(by_slug[slug]["title"])}</a>'
        f' <span class="family-tag">({T(by_slug[slug]["family_label"])})</span></li>\n'
        for slug in entry.get("related", [])
        if slug in by_slug
    )
    related_block = (
        '      <section class="related" aria-labelledby="related-title">\n'
        '        <h2 id="related-title">Related</h2>\n'
        f"        <ul>\n{related}        </ul>\n"
        "      </section>"
        if related
        else ""
    )

    body = f"""    <article>
      <nav class="breadcrumb" aria-label="Breadcrumb">
        <a href="index.html">Cryptanalysis reference</a> /
        <a href="index.html#{E(entry["family"])}">{T(entry["family_label"])}</a>
      </nav>
      <header>
        <h1>{T(entry["title"])}</h1>
        <p class="standfirst">{entry["standfirst"]}</p>
      </header>
      <dl class="facts">
{meta_rows}      </dl>
      <nav class="toc" aria-label="On this page">
        <p>On this page</p>
        <ol>
{toc}        </ol>
      </nav>
{chr(10).join(s for s in sections)}
{references_block}
{related_block}
    </article>
"""
    return page(
        prefix="../",
        here="library",
        title=f"{entry['title']} · Isogeny Labs",
        description=entry["description"],
        body=body,
    )


def render_index(index: dict, entries: list[dict]) -> str:
    by_family: dict[str, list[dict]] = {}
    for entry in entries:
        by_family.setdefault(entry["family"], []).append(entry)

    families = []
    for family in index["families"]:
        items = []
        for entry in by_family.get(family["id"], []):
            items.append(
                f'          <li>\n'
                f'            <h3><a href="{E(entry["slug"])}.html">{T(entry["short_title"])}</a></h3>\n'
                f'            <p>{entry["one_liner"]}</p>\n'
                f'            <p class="meta">{entry["cost_label"]}</p>\n'
                f"          </li>\n"
            )
        for planned in family.get("planned", []):
            items.append(
                f'          <li class="queued">\n'
                f'            <h3>{T(planned["title"])}</h3>\n'
                f'            <p>{planned["one_liner"]}</p>\n'
                f'            <p class="meta">Not written yet</p>\n'
                f"          </li>\n"
            )
        families.append(
            f'      <section id="{E(family["id"])}" aria-labelledby="{E(family["id"])}-title">\n'
            f'        <h2 id="{E(family["id"])}-title">{T(family["label"])}</h2>\n'
            f'        <p class="family-intro">{family["intro"]}</p>\n'
            f'        <ul class="technique-list">\n{"".join(items)}        </ul>\n'
            f"      </section>"
        )

    jump = "".join(
        f'        <li><a href="#{E(f["id"])}">{T(f["label"])}</a></li>\n' for f in index["families"]
    )

    body = f"""    <header aria-labelledby="library-title">
      <h1 id="library-title">{index["heading"]}</h1>
      <p class="standfirst">{index["standfirst"]}</p>
    </header>
    <nav class="toc" aria-label="Families">
      <ol>
{jump}      </ol>
    </nav>
    <section aria-labelledby="guide-title">
      <h2 id="guide-title">{index["guide_heading"]}</h2>
{render_blocks(index["guide_blocks"], "      ")}    </section>
{chr(10).join(families)}
"""
    return page(
        prefix="../",
        here="library",
        title=index["title"],
        description=index["description"],
        body=body,
    )


def slugify(heading: str) -> str:
    plain = html.unescape(re.sub(r"<[^>]+>", "", heading))
    keep = [c.lower() if c.isalnum() else "-" for c in plain]
    out = "".join(keep)
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")


def validate(entries: list[dict], index: dict) -> list[str]:
    errors = []
    family_ids = {f["id"] for f in index["families"]}
    labels = {f["id"]: f["label"] for f in index["families"]}
    slugs = {e["slug"] for e in entries}
    for entry in entries:
        where = entry["slug"]
        if entry["family"] not in family_ids:
            errors.append(f"{where}: unknown family {entry['family']!r}")
        else:
            entry["family_label"] = labels[entry["family"]]
        if not entry.get("references"):
            errors.append(f"{where}: no primary sources cited")
        for slug in entry.get("related", []):
            if slug not in slugs:
                errors.append(f"{where}: related to unknown technique {slug!r}")
        headings = [slugify(s["heading"]) for s in entry["sections"]]
        if len(set(headings)) != len(headings):
            errors.append(f"{where}: duplicate section headings")
        for section in entry["sections"]:
            for block in section["blocks"]:
                if not {"p", "ul", "ol", "steps", "math", "note"} & set(block):
                    errors.append(f"{where}: unknown block {sorted(block)}")

    # A queued technique names the slug it will become, so writing it up is
    # caught here rather than silently counted twice. Without this, adding
    # content/cryptanalysis/<slug>.json while leaving the entry under
    # `planned` renders both a real card and a "Not written yet" card for the
    # same technique, and inflates the "Queued" count on the library index.
    seen: dict[str, str] = {}
    for family in index["families"]:
        for planned in family.get("planned", []):
            where = f'index.json: planned {planned["title"]!r}'
            slug = planned.get("slug")
            if not slug:
                errors.append(f"{where}: no slug declared")
                continue
            if slug in slugs:
                errors.append(
                    f"{where}: already written up as {slug}.json "
                    f"— remove it from the planned list"
                )
            if slug in seen:
                errors.append(f"{where}: slug {slug!r} also queued under {seen[slug]}")
            else:
                seen[slug] = family["id"]

    return errors


def build() -> dict[str, str]:
    index = json.loads((CONTENT / "index.json").read_text())
    entries = [
        json.loads(path.read_text())
        for path in sorted(CONTENT.glob("*.json"))
        if path.name != "index.json"
    ]
    order = {f["id"]: n for n, f in enumerate(index["families"])}
    entries.sort(key=lambda e: (order.get(e["family"], 99), e.get("position", 0), e["slug"]))

    errors = validate(entries, index)
    if errors:
        for error in errors:
            print(f"content error: {error}", file=sys.stderr)
        raise SystemExit(1)

    by_slug = {e["slug"]: e for e in entries}
    pages = {"index.html": render_index(index, entries)}
    for entry in entries:
        pages[f"{entry['slug']}.html"] = render_technique(entry, by_slug)
    return pages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if committed pages are stale")
    args = parser.parse_args()

    pages = build()
    OUT.mkdir(exist_ok=True)

    if args.check:
        stale = [
            name
            for name, text in pages.items()
            if not (OUT / name).exists() or (OUT / name).read_text() != text
        ]
        extra = [p.name for p in OUT.glob("*.html") if p.name not in pages]
        for name in sorted(stale):
            print(f"stale: cryptanalysis/{name}", file=sys.stderr)
        for name in sorted(extra):
            print(f"orphan: cryptanalysis/{name} has no content file", file=sys.stderr)
        if stale or extra:
            print("run: python3 tools/build_cryptanalysis.py", file=sys.stderr)
            return 1
        print(f"cryptanalysis/: {len(pages)} pages up to date")
        return 0

    for name, text in pages.items():
        (OUT / name).write_text(text)
    print(f"wrote {len(pages)} pages to cryptanalysis/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
