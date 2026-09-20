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
    <a class="brand" href="{prefix}index.html" aria-label="Isogeny Labs home"><svg class="brand-mark" viewBox="0 0 34 34" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="2"><path d="M17 5 5 12v14l12 7 12-7V12z"/><path d="M17 5v28M5 12l24 14M29 12 5 26"/></g><circle cx="17" cy="5" r="3.2" fill="currentColor"/><circle cx="5" cy="26" r="3.2" fill="currentColor"/><circle cx="29" cy="26" r="3.2" fill="currentColor"/></svg><span class="brand-name">isogeny<span class="brand-security">LABS</span></span></a>
    <button class="menu-toggle" type="button" aria-expanded="false" aria-controls="navigation"><span>Menu</span><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M3 7h18M3 17h18"/></svg></button>
    <nav class="navigation" id="navigation" aria-label="Main navigation">
      <a href="{prefix}index.html#work">What we do</a><a href="{prefix}index.html#approach">How we work</a><a href="{prefix}index.html#foundations">Foundations</a><a href="{prefix}cryptanalysis/index.html"{current('library')}>Cryptanalysis</a>
      <a class="nav-cta" href="{prefix}index.html#engagement">Start a conversation <span aria-hidden="true">↗</span></a>
    </nav>
  </header>
"""


def footer(prefix: str) -> str:
    return f"""  <footer class="site-footer">
    <div class="footer-top">
      <a class="brand" href="{prefix}index.html" aria-label="Isogeny Labs home"><svg class="brand-mark" viewBox="0 0 34 34" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="2"><path d="M17 5 5 12v14l12 7 12-7V12z"/><path d="M17 5v28M5 12l24 14M29 12 5 26"/></g><circle cx="17" cy="5" r="3.2" fill="currentColor"/><circle cx="5" cy="26" r="3.2" fill="currentColor"/><circle cx="29" cy="26" r="3.2" fill="currentColor"/></svg><span class="brand-name">isogeny<span class="brand-security">LABS</span></span></a>
      <p>Cryptographic analysis.<br>Systems that hold up.</p>
      <a class="text-link light" href="#main">Back to top <span aria-hidden="true">↑</span></a>
    </div>
    <div class="footer-bottom">
      <span>© <span id="year">2026</span> Isogeny Labs</span>
      <span>Hardness analysis · Isogeny systems · Post-quantum migration</span>
    </div>
  </footer>
"""


def page(*, prefix: str, here: str, title: str, description: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#0d0f18">
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
{nav(prefix, here)}  <main id="main">
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
            out.append(f'{indent}<ol class="doc-steps">\n{items}{indent}</ol>')
        elif "math" in block:
            label = block.get("label")
            caption = f'\n{indent}  <span class="math-label">{label}</span>' if label else ""
            out.append(f'{indent}<div class="math">{block["math"]}{caption}</div>')
        elif "note" in block:
            out.append(
                f'{indent}<aside class="doc-note"><span class="doc-note-label">'
                f'{T(block.get("note_label", "Where this bites"))}</span>'
                f'<p>{block["note"]}</p></aside>'
            )
        else:  # pragma: no cover - guarded by validate()
            raise ValueError(f"unknown block: {sorted(block)}")
    return "\n".join(out) + "\n"


def render_technique(entry: dict, by_slug: dict[str, dict]) -> str:
    meta_rows = "".join(
        f'        <div class="fact"><dt>{T(k)}</dt><dd>{v}</dd></div>\n'
        for k, v in entry["facts"].items()
    )

    toc = "".join(
        f'        <li><a href="#{E(slugify(s["heading"]))}">{T(s["heading"])}</a></li>\n'
        for s in entry["sections"]
    )

    sections = []
    for number, section in enumerate(entry["sections"], start=1):
        anchor = slugify(section["heading"])
        sections.append(
            f'      <section class="doc-section" id="{E(anchor)}" aria-labelledby="{E(anchor)}-title">\n'
            f'        <h2 id="{E(anchor)}-title"><span class="doc-section-number">{number:02d}</span>'
            f'{T(section["heading"])}</h2>\n'
            + render_blocks(section["blocks"], "        ")
            + "      </section>"
        )

    references = "".join(
        f'        <li><a href="{E(r["href"])}" rel="noopener noreferrer" target="_blank">{T(r["text"])}'
        f' <span aria-hidden="true">↗</span></a></li>\n'
        for r in entry.get("references", [])
    )
    references_block = (
        '      <section class="doc-section doc-references" id="references" aria-labelledby="references-title">\n'
        '        <h2 id="references-title"><span class="doc-section-number">'
        f'{len(entry["sections"]) + 1:02d}</span>Primary sources</h2>\n'
        '        <p>Read these rather than this page. Links open in a new tab.</p>\n'
        f"        <ul class=\"reference-list\">\n{references}        </ul>\n"
        "      </section>"
        if references
        else ""
    )

    related = "".join(
        f'        <li><a href="{E(slug)}.html"><span>{T(by_slug[slug]["family_label"])}</span>'
        f'{T(by_slug[slug]["title"])}</a></li>\n'
        for slug in entry.get("related", [])
        if slug in by_slug
    )
    related_block = (
        '      <section class="doc-related" aria-labelledby="related-title">\n'
        '        <h2 id="related-title" class="eyebrow">Related techniques</h2>\n'
        f"        <ul>\n{related}        </ul>\n"
        "      </section>"
        if related
        else ""
    )

    body = f"""    <article class="doc">
      <nav class="breadcrumb" aria-label="Breadcrumb">
        <a href="../index.html">Isogeny Labs</a> <span aria-hidden="true">/</span>
        <a href="index.html">Cryptanalysis</a> <span aria-hidden="true">/</span>
        <span aria-current="page">{T(entry["short_title"])}</span>
      </nav>
      <header class="doc-header">
        <p class="eyebrow"><span class="small-cross">+</span> {T(entry["family_label"].upper())}</p>
        <h1>{T(entry["title"])}</h1>
        <p class="doc-standfirst">{entry["standfirst"]}</p>
      </header>
      <dl class="doc-facts">
{meta_rows}      </dl>
      <nav class="doc-toc" aria-label="On this page">
        <p class="eyebrow">On this page</p>
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
        title=f"{entry['title']} — Isogeny Labs",
        description=entry["description"],
        body=body,
    )


def render_index(index: dict, entries: list[dict]) -> str:
    by_family: dict[str, list[dict]] = {}
    for entry in entries:
        by_family.setdefault(entry["family"], []).append(entry)

    families = []
    for number, family in enumerate(index["families"], start=1):
        cards = []
        for entry in by_family.get(family["id"], []):
            cards.append(
                f'          <li class="technique">\n'
                f'            <a href="{E(entry["slug"])}.html">\n'
                f'              <h3>{T(entry["short_title"])}</h3>\n'
                f'              <p>{entry["one_liner"]}</p>\n'
                f'              <span class="technique-cost">{entry["cost_label"]}</span>\n'
                f'            </a>\n'
                f"          </li>\n"
            )
        for planned in family.get("planned", []):
            cards.append(
                f'          <li class="technique technique-planned">\n'
                f'            <h3>{T(planned["title"])}</h3>\n'
                f'            <p>{planned["one_liner"]}</p>\n'
                f'            <span class="technique-cost">Not written yet</span>\n'
                f"          </li>\n"
            )
        families.append(
            f'      <section class="family" id="{E(family["id"])}" aria-labelledby="{E(family["id"])}-title">\n'
            f'        <div class="family-head">\n'
            f'          <p class="eyebrow"><span class="section-index">{number:02d} /</span> {T(family["label"].upper())}</p>\n'
            f'          <h2 id="{E(family["id"])}-title">{T(family["heading"])}</h2>\n'
            f'          <p class="family-intro">{family["intro"]}</p>\n'
            f"        </div>\n"
            f'        <ul class="technique-grid">\n{"".join(cards)}        </ul>\n'
            f"      </section>"
        )

    jump = "".join(
        f'        <li><a href="#{E(f["id"])}">{T(f["label"])}</a></li>\n' for f in index["families"]
    )

    written = len(entries)
    planned = sum(len(f.get("planned", [])) for f in index["families"])

    body = f"""    <section class="library-hero" aria-labelledby="library-title">
      <nav class="breadcrumb" aria-label="Breadcrumb">
        <a href="../index.html">Isogeny Labs</a> <span aria-hidden="true">/</span>
        <span aria-current="page">Cryptanalysis</span>
      </nav>
      <p class="eyebrow"><span class="small-cross">+</span> {T(index["eyebrow"].upper())}</p>
      <h1 id="library-title">{index["heading"]}</h1>
      <p class="library-standfirst">{index["standfirst"]}</p>
      <dl class="doc-facts library-facts">
        <div class="fact"><dt>Techniques written up</dt><dd>{written}</dd></div>
        <div class="fact"><dt>Queued</dt><dd>{planned}</dd></div>
        <div class="fact"><dt>Scope</dt><dd>{T(index["scope"])}</dd></div>
      </dl>
    </section>
    <section class="library-guide section-pad" aria-labelledby="guide-title">
      <div class="guide-copy">
        <h2 id="guide-title">{index["guide_heading"]}</h2>
{render_blocks(index["guide_blocks"], "        ")}      </div>
      <nav class="library-jump" aria-label="Technique families">
        <p class="eyebrow">Families</p>
        <ol>
{jump}        </ol>
      </nav>
    </section>
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
