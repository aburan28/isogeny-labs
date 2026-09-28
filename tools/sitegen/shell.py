"""The parts every generated page shares: escaping, the page shell, and blocks.

Content strings may carry inline HTML and character entities, because every
one of them is authored in this repository rather than supplied by a user.
Two renderings are therefore needed:

  T(s) -- inside element content: emit as authored, entities intact.
  A(s) -- inside an attribute, a <title>, or a slug: strip markup, resolve
          entities to characters, then escape for the attribute context.

Anything not from a content file (hrefs, generated ids) goes through E.
"""

from __future__ import annotations

import html
import re

E = html.escape

# Sections of the site that have their own generated directory. The key is
# what a page passes as `here` to mark its nav entry as current.
NAV = [
    ("work", "index.html#work", "Work"),
    ("services", "index.html#services", "Services"),
    ("notes", "notes/index.html", "Notes"),
    ("schemes", "schemes/index.html", "Schemes"),
    ("cryptanalysis", "cryptanalysis/index.html", "Cryptanalysis reference"),
    ("contact", "index.html#contact", "Contact"),
]

BLOCK_TYPES = {"p", "ul", "steps", "math", "note", "h3", "table", "pre", "svg", "dl", "computed", "traits"}


def T(value: str) -> str:
    """Authored markup, rendered as-is into element content."""
    return value


def A(value: str) -> str:
    """Authored markup, flattened to escaped plain text for an attribute."""
    return E(html.unescape(re.sub(r"<[^>]+>", "", value)))


def slugify(heading: str) -> str:
    plain = html.unescape(re.sub(r"<[^>]+>", "", heading))
    keep = [c.lower() if c.isalnum() else "-" for c in plain]
    out = "".join(keep)
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")


def nav(prefix: str, here: str) -> str:
    """Site header. `prefix` reaches the site root; `here` marks the current section."""
    links = "\n".join(
        f'        <a href="{prefix}{href}"'
        f'{" aria-current=" + chr(34) + "page" + chr(34) if key == here else ""}>{label}</a>'
        for key, href, label in NAV
    )
    return f"""  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header">
    <div class="wrap">
      <a class="wordmark" href="{prefix}index.html">Isogeny Labs</a>
      <nav class="site-nav" aria-label="Main">
{links}
      </nav>
    </div>
  </header>
"""


def footer() -> str:
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
  <meta property="og:description" content="{A(description)}">
  <meta property="og:type" content="article">
  <title>{A(title)}</title>
  <link rel="icon" type="image/svg+xml" href="{prefix}favicon.svg">
  <link rel="stylesheet" href="{prefix}styles.css">
  <script defer src="{prefix}script.js"></script>
</head>
<body>
{nav(prefix, here)}  <main id="main" class="wrap">
{body}  </main>
{footer()}</body>
</html>
"""


def render_table(table: dict, indent: str) -> str:
    numeric = set(table.get("numeric", []))
    caption = f"{indent}  <caption>{table['caption']}</caption>\n" if table.get("caption") else ""

    def cell(value: str, col: int, row_header: bool) -> str:
        cls = ' class="num"' if col in numeric else ""
        if row_header and col == 0:
            return f'<th scope="row"{cls}>{value}</th>'
        return f"<td{cls}>{value}</td>"

    head = ""
    if table.get("head"):
        cells = "".join(
            f'<th scope="col"{" class=" + chr(34) + "num" + chr(34) if i in numeric else ""}>{h}</th>'
            for i, h in enumerate(table["head"])
        )
        head = f"{indent}  <thead><tr>{cells}</tr></thead>\n"
    row_header = table.get("row_headers", True)
    rows = "".join(
        f"{indent}    <tr>{''.join(cell(v, i, row_header) for i, v in enumerate(row))}</tr>\n"
        for row in table["rows"]
    )
    return (
        f'{indent}<div class="table-wrap" role="region" aria-label="Scrollable data table" tabindex="0">\n'
        f'{indent}<table class="data">\n{caption}{head}'
        f"{indent}  <tbody>\n{rows}{indent}  </tbody>\n"
        f"{indent}</table>\n{indent}</div>"
    )


def render_blocks(blocks: list[dict], indent: str) -> str:
    out = []
    for block in blocks:
        if "p" in block:
            out.append(f"{indent}<p>{block['p']}</p>")
        elif "traits" in block:
            out.append('<div id="filters" class="trait-filters" hidden><div><label for="trait-search">Search traits</label><input id="trait-search" type="search" placeholder="Trace, conductor, factorization…"></div><div><label for="trait-origin">Source</label><select id="trait-origin"><option value="all">All topics</option><option value="dissect">DiSSECT</option><option value="foundation">Foundations</option></select></div><button type="button" id="reset-traits">Clear filters</button></div><p id="trait-count" role="status" aria-live="polite">30 of 30 topics</p>')
            for trait in block["traits"]:
                number = trait["id"]
                label = "Foundation" if trait["origin"] == "foundation" else "DiSSECT"
                out.append(f'<details class="trait" id="trait-{number}" data-origin="{E(trait["origin"])}"><summary>{number}. {trait["title"]} <span class="trait-origin">{label}</span></summary><div class="trait-body"><p><strong>What it measures.</strong> {trait["meaning"]}</p><p><strong>Security connection and study task.</strong> {trait["task"]}</p><a href="#trait-{number}">Link to topic {number}</a></div></details>')
            out.append('<p id="no-results" hidden>No matching topics. Try another term or clear the filters.</p>')
        elif "ul" in block:
            items = "".join(f"{indent}  <li>{item}</li>\n" for item in block["ul"])
            out.append(f"{indent}<ul>\n{items}{indent}</ul>")
        elif "steps" in block:
            items = "".join(f"{indent}  <li>{item}</li>\n" for item in block["steps"])
            out.append(f"{indent}<ol>\n{items}{indent}</ol>")
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
        elif "h3" in block:
            out.append(f'{indent}<h3 id="{E(slugify(block["h3"]))}">{block["h3"]}</h3>')
        elif "table" in block:
            out.append(render_table(block["table"], indent))
        elif "pre" in block:
            label = block.get("label")
            caption = f'\n{indent}<p class="listing-label">{label}</p>' if label else ""
            out.append(f'{indent}<pre class="listing" tabindex="0">{E(block["pre"])}</pre>{caption}')
        elif "svg" in block:
            # Generated by tools/sitegen/figures.py from computed data, never
            # hand-authored, so it is inserted verbatim.
            caption = f"\n{indent}  <figcaption>{block['caption']}</figcaption>" if block.get("caption") else ""
            out.append(f'{indent}<figure class="diagram">\n{indent}  {block["svg"]}{caption}\n{indent}</figure>')
        elif "dl" in block:
            items = "".join(
                f"{indent}  <div><dt>{term}</dt><dd>{definition}</dd></div>\n"
                for term, definition in block["dl"]
            )
            out.append(f'{indent}<dl class="terms">\n{items}{indent}</dl>')
        else:  # pragma: no cover - guarded by validate_blocks()
            raise ValueError(f"unknown block: {sorted(block)}")
    return "\n".join(out) + "\n"


def validate_blocks(blocks: list[dict], where: str) -> list[str]:
    errors = []
    for block in blocks:
        if "traits" in block:
            traits = block["traits"]
            if [t.get("id") for t in traits] != list(range(1, 31)):
                errors.append(f"{where}: expected each trait ID 1–30 exactly once")
            if sum(t.get("origin") == "dissect" for t in traits) != 22 or sum(t.get("origin") == "foundation" for t in traits) != 8:
                errors.append(f"{where}: expected 22 DiSSECT entries and eight foundations")
        kinds = BLOCK_TYPES & set(block)
        if len(kinds) != 1:
            errors.append(f"{where}: block must have exactly one type, got {sorted(block)}")
    return errors
