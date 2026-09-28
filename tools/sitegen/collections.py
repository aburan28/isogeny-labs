"""Load, validate and render the site's three generated collections.

Each collection is a directory of JSON files under content/<name>/ with an
index.json describing its grouping, rendered into <name>/*.html:

  cryptanalysis  attacks, grouped into families; entries may be queued
  notes          longer explanations and computed worked examples
  schemes        a catalogue of schemes, plus full pages for some of them

An entry may name a `compute` module from sitegen.worked. That module runs at
build time and supplies values for {{placeholders}} in the entry's strings and
whole blocks for {"computed": "<name>"} markers. A placeholder or marker with
no value is a build error, so a number on a worked-example page can only ever
come from the code that computed it.
"""

from __future__ import annotations

import importlib
import json
import pathlib
import re

from .figures import size_dotplot
from .shell import A, E, T, page, render_blocks, slugify, validate_blocks

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
CONTENT = ROOT / "content"
COLLECTIONS = ("cryptanalysis", "notes", "schemes")
COLLECTION_LABELS = {
    "cryptanalysis": "Cryptanalysis reference",
    "notes": "Notes",
    "schemes": "Schemes",
}
PLACEHOLDER = re.compile(r"\{\{([A-Za-z0-9_.]+)\}\}")


# --------------------------------------------------------------------------
# Loading and computed values


def load(name: str) -> tuple[dict, list[dict]]:
    directory = CONTENT / name
    index = json.loads((directory / "index.json").read_text())
    entries = []
    for path in sorted(directory.glob("*.json")):
        if path.name == "index.json":
            continue
        entry = json.loads(path.read_text())
        entry["collection"] = name
        entries.append(entry)
    return index, entries


def apply_compute(entry: dict, errors: list[str]) -> dict:
    """Fill {{placeholders}} and {"computed": ...} blocks from the entry's module."""
    module_name = entry.get("compute")
    values: dict[str, str] = {}
    blocks: dict[str, list[dict]] = {}
    if module_name:
        module = importlib.import_module(f"sitegen.worked.{module_name}")
        result = module.compute()
        values, blocks = result["values"], result["blocks"]

    where = f'{entry["collection"]}/{entry["slug"]}'

    def fill(value):
        if isinstance(value, str):
            def sub(match):
                key = match.group(1)
                if key not in values:
                    errors.append(f"{where}: no computed value for {{{{{key}}}}}")
                    return match.group(0)
                return values[key]
            return PLACEHOLDER.sub(sub, value)
        if isinstance(value, list):
            out = []
            for item in value:
                if isinstance(item, dict) and set(item) == {"computed"}:
                    key = item["computed"]
                    if key not in blocks:
                        errors.append(f"{where}: no computed block {key!r}")
                        continue
                    out.extend(blocks[key])
                else:
                    out.append(fill(item))
            return out
        if isinstance(value, dict):
            return {fill(k): fill(v) for k, v in value.items()}
        return value

    return fill(entry)


# --------------------------------------------------------------------------
# Validation


def groups_of(index: dict) -> list[dict]:
    return index.get("families") or index.get("groups") or []


def group_key(entry: dict) -> str:
    return entry.get("family") or entry.get("group")


def validate(index: dict, entries: list[dict], known: set[str]) -> list[str]:
    """`known` holds every page as "collection/slug", for cross-collection links."""
    errors = []
    groups = {g["id"]: g for g in groups_of(index)}
    slugs = {e["slug"] for e in entries}
    for entry in entries:
        where = f'{entry["collection"]}/{entry["slug"]}'
        if group_key(entry) not in groups:
            errors.append(f"{where}: unknown group {group_key(entry)!r}")
        else:
            entry["group_label"] = groups[group_key(entry)]["label"]
            entry["family_label"] = entry["group_label"]
        if not entry.get("references"):
            errors.append(f"{where}: no primary sources cited")
        for ref in entry.get("related", []):
            target = ref if "/" in ref else f'{entry["collection"]}/{ref}'
            if target not in known:
                errors.append(f"{where}: related to unknown page {ref!r}")
        headings = [slugify(s["heading"]) for s in entry["sections"]]
        if len(set(headings)) != len(headings):
            errors.append(f"{where}: duplicate section headings")
        for section in entry["sections"]:
            errors += validate_blocks(section["blocks"], where)
        leftover = PLACEHOLDER.findall(json.dumps(entry))
        for key in sorted(set(leftover)):
            errors.append(f"{where}: unresolved placeholder {{{{{key}}}}}")

    # A queued entry names the slug it will become, so writing it up is caught
    # here rather than silently counted twice: without this, adding
    # content/<collection>/<slug>.json while leaving the entry under `planned`
    # renders both a real item and a "Not written yet" item for the same page.
    seen: dict[str, str] = {}
    for group in groups_of(index):
        for planned in group.get("planned", []):
            where = f'{index.get("collection", "index.json")}: planned {planned["title"]!r}'
            slug = planned.get("slug")
            if not slug:
                errors.append(f"{where}: no slug declared")
                continue
            if slug in slugs:
                errors.append(f"{where}: already written up as {slug}.json — remove it from the planned list")
            if slug in seen:
                errors.append(f"{where}: slug {slug!r} also queued under {seen[slug]}")
            else:
                seen[slug] = group["id"]
    return errors


# --------------------------------------------------------------------------
# Rendering


def related_items(entry: dict, pages_by_key: dict[str, dict]) -> str:
    items = []
    for ref in entry.get("related", []):
        key = ref if "/" in ref else f'{entry["collection"]}/{ref}'
        target = pages_by_key[key]
        same = target["collection"] == entry["collection"]
        href = f'{target["slug"]}.html' if same else f'../{target["collection"]}/{target["slug"]}.html'
        tag = target.get("group_label", "") if same else COLLECTION_LABELS[target["collection"]]
        items.append(
            f'        <li><a href="{E(href)}">{T(target["title"])}</a>'
            f' <span class="family-tag">({T(tag)})</span></li>\n'
        )
    return "".join(items)


def render_article(entry: dict, pages_by_key: dict[str, dict]) -> str:
    collection = entry["collection"]
    facts = entry.get("facts") or {}
    meta_rows = "".join(f"        <div><dt>{T(k)}</dt><dd>{v}</dd></div>\n" for k, v in facts.items())
    facts_block = f'      <dl class="facts">\n{meta_rows}      </dl>\n' if facts else ""

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
        f'        <li><a href="{E(r["href"])}">{T(r["text"])}</a></li>\n' for r in entry.get("references", [])
    )
    references_block = (
        '      <section class="references" id="references" aria-labelledby="references-title">\n'
        '        <h2 id="references-title">Primary sources</h2>\n'
        f"        <ol>\n{references}        </ol>\n"
        "      </section>"
        if references
        else ""
    )

    related = related_items(entry, pages_by_key)
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
        <a href="index.html">{COLLECTION_LABELS[collection]}</a> /
        <a href="index.html#{E(group_key(entry))}">{T(entry["group_label"])}</a>
      </nav>
      <header>
        <h1>{T(entry["title"])}</h1>
        <p class="standfirst">{entry["standfirst"]}</p>
      </header>
{facts_block}      <nav class="toc" aria-label="On this page">
        <p>On this page</p>
        <ol>
{toc}        </ol>
      </nav>
{chr(10).join(sections)}
{references_block}
{related_block}
    </article>
"""
    return page(
        prefix="../",
        here=collection,
        title=f"{entry['title']} · Isogeny Labs",
        description=entry["description"],
        body=body,
    )


def render_grouped_index(index: dict, entries: list[dict], collection: str) -> str:
    """Index for cryptanalysis and notes: groups of entries, each with a one-liner."""
    by_group: dict[str, list[dict]] = {}
    for entry in entries:
        by_group.setdefault(group_key(entry), []).append(entry)

    sections = []
    for group in groups_of(index):
        items = []
        for entry in by_group.get(group["id"], []):
            meta = entry.get("cost_label") or entry.get("index_meta", "")
            items.append(
                f"          <li>\n"
                f'            <h3><a href="{E(entry["slug"])}.html">{T(entry["short_title"])}</a></h3>\n'
                f'            <p>{entry["one_liner"]}</p>\n'
                f'            <p class="meta">{meta}</p>\n'
                f"          </li>\n"
            )
        for planned in group.get("planned", []):
            items.append(
                f'          <li class="queued">\n'
                f'            <h3>{T(planned["title"])}</h3>\n'
                f'            <p>{planned["one_liner"]}</p>\n'
                f'            <p class="meta">Not written yet</p>\n'
                f"          </li>\n"
            )
        sections.append(
            f'      <section id="{E(group["id"])}" aria-labelledby="{E(group["id"])}-title">\n'
            f'        <h2 id="{E(group["id"])}-title">{T(group["label"])}</h2>\n'
            f'        <p class="family-intro">{group["intro"]}</p>\n'
            f'        <ul class="technique-list">\n{"".join(items)}        </ul>\n'
            f"      </section>"
        )

    jump = "".join(f'        <li><a href="#{E(g["id"])}">{T(g["label"])}</a></li>\n' for g in groups_of(index))
    guide = (
        f'    <section aria-labelledby="guide-title">\n'
        f'      <h2 id="guide-title">{index["guide_heading"]}</h2>\n'
        f'{render_blocks(index["guide_blocks"], "      ")}    </section>\n'
        if index.get("guide_heading")
        else ""
    )

    body = f"""    <header aria-labelledby="library-title">
      <h1 id="library-title">{index["heading"]}</h1>
      <p class="standfirst">{index["standfirst"]}</p>
    </header>
    <nav class="toc" aria-label="{"Families" if collection == "cryptanalysis" else "Parts"}">
      <ol>
{jump}      </ol>
    </nav>
{guide}{chr(10).join(sections)}
"""
    return page(prefix="../", here=collection, title=index["title"], description=index["description"], body=body)


def render_catalogue(index: dict, entries: list[dict], pages_by_key: dict[str, dict]) -> str:
    """schemes/index.html: the catalogue. Entries with a full page link to it."""
    full_pages = {e["slug"] for e in entries}

    def link(ref: str) -> str:
        collection, slug = ref.split("/")
        target = pages_by_key[ref]
        href = f"{slug}.html" if collection == "schemes" else f"../{collection}/{slug}.html"
        return f'<a href="{E(href)}">{T(target["short_title"])}</a>'

    glance_rows = []
    groups_html = []
    for group in index["groups"]:
        items = []
        for item in group["entries"]:
            anchor = item["id"]
            glance_rows.append(
                f'          <tr><th scope="row"><a href="#{E(anchor)}">{T(item["name"])}</a></th>'
                f'<td>{T(item.get("kind", group["short"]))}</td><td>{item["rests_on_short"]}</td>'
                f'<td>{item["quantum_short"]}</td></tr>\n'
            )
            facts = "".join(
                f"              <div><dt>{T(k)}</dt><dd>{v}</dd></div>\n" for k, v in item["facts"].items()
            )
            see = []
            if item.get("page"):
                if item["page"] not in full_pages:
                    raise ValueError(f"catalogue entry {anchor}: no page {item['page']!r}")
                see.append(f'<a href="{E(item["page"])}.html">Full page</a>')
            see += [link(ref) for ref in item.get("see", [])]
            see_html = (
                f'            <p class="see">See also: {" · ".join(see)}</p>\n' if see else ""
            )
            items.append(
                f'          <li id="{E(anchor)}">\n'
                f'            <h3>{T(item["name"])}</h3>\n'
                f'            <p>{item["summary"]}</p>\n'
                f'            <dl class="facts compact">\n{facts}            </dl>\n'
                f"{see_html}"
                f"          </li>\n"
            )
        chart = ""
        if group.get("chart"):
            spec = group["chart"]
            # The figure and its table twin: every value in the chart is also
            # readable here without hovering, and without seeing colour.
            chart = render_blocks([
                {"svg": size_dotplot(spec["rows"]), "caption": spec["caption"]},
                {"table": {
                    "caption": spec["table_caption"],
                    "head": ["Scheme", "Public key (bytes)", "Signature (bytes)", "Standard or status"],
                    "rows": [[r["name"], f'{r["public_key"]:,}', f'{r["signature"]:,}', r["status"]] for r in spec["rows"]],
                    "numeric": [1, 2],
                }},
            ], "        ")
        groups_html.append(
            f'      <section id="{E(group["id"])}" aria-labelledby="{E(group["id"])}-title">\n'
            f'        <h2 id="{E(group["id"])}-title">{T(group["label"])}</h2>\n'
            f'        <p class="family-intro">{group["intro"]}</p>\n'
            f"{chart}"
            f'        <ul class="catalogue">\n{"".join(items)}        </ul>\n'
            f"      </section>"
        )

    extra = render_blocks(index["glance_after"], "      ") if index.get("glance_after") else ""
    jump = "".join(f'        <li><a href="#{E(g["id"])}">{T(g["label"])}</a></li>\n' for g in index["groups"])
    body = f"""    <header aria-labelledby="catalogue-title">
      <h1 id="catalogue-title">{index["heading"]}</h1>
      <p class="standfirst">{index["standfirst"]}</p>
    </header>
    <nav class="toc" aria-label="Groups">
      <ol>
{jump}      </ol>
    </nav>
    <section aria-labelledby="glance-title">
      <h2 id="glance-title">{index["glance_heading"]}</h2>
{render_blocks(index["glance_blocks"], "      ")}      <div class="table-wrap">
      <table class="data glance">
        <thead><tr><th scope="col">Scheme</th><th scope="col">Kind</th><th scope="col">Rests on</th><th scope="col">Against a quantum computer</th></tr></thead>
        <tbody>
{"".join(glance_rows)}        </tbody>
      </table>
      </div>
{extra}    </section>
{chr(10).join(groups_html)}
"""
    return page(prefix="../", here="schemes", title=index["title"], description=index["description"], body=body)


# --------------------------------------------------------------------------
# Whole-site build


def build() -> tuple[dict[str, str], list[str]]:
    """Return ({"<collection>/<file>.html": text}, errors)."""
    errors: list[str] = []
    loaded = {}
    for name in COLLECTIONS:
        index, entries = load(name)
        index["collection"] = name
        entries = [apply_compute(e, errors) for e in entries]
        order = {g["id"]: n for n, g in enumerate(groups_of(index))}
        entries.sort(key=lambda e: (order.get(group_key(e), 99), e.get("position", 0), e["slug"]))
        loaded[name] = (index, entries)

    known = {f'{e["collection"]}/{e["slug"]}' for _, es in loaded.values() for e in es}
    for name, (index, entries) in loaded.items():
        errors += validate(index, entries, known)
    if errors:
        return {}, errors

    pages_by_key = {f'{e["collection"]}/{e["slug"]}': e for _, es in loaded.values() for e in es}
    for name in ("schemes",):
        index, _ = loaded[name]
        for group in index["groups"]:
            for item in group["entries"]:
                for ref in item.get("see", []):
                    if ref not in pages_by_key:
                        errors.append(f"schemes/index.json: {item['id']} links to unknown page {ref!r}")
    if errors:
        return {}, errors

    out: dict[str, str] = {}
    for name, (index, entries) in loaded.items():
        if name == "schemes":
            out[f"{name}/index.html"] = render_catalogue(index, entries, pages_by_key)
        else:
            out[f"{name}/index.html"] = render_grouped_index(index, entries, name)
        for entry in entries:
            out[f'{name}/{entry["slug"]}.html'] = render_article(entry, pages_by_key)

    # Last line of defence: whatever went wrong upstream, no page ships with
    # template syntax in it.
    for name, text in out.items():
        if "{{" in text or "}}" in text:
            line = next(l for l in text.splitlines() if "{{" in l or "}}" in l)
            errors.append(f"{name}: unrendered template syntax: {line.strip()[:120]}")
    return (out if not errors else {}), errors
