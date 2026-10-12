"""The hand-written pages, rendered from Markdown in content/.

  content/home.md            the thesis on the home page
  content/research/index.md  the research index's standfirst
  content/research/*.md      one file per paper: a card on the home page and
                             on research/index.html, and its own page
  content/about.md           about/index.html
  content/contact.md         contact/index.html

A research file's front matter:

  title     the paper's short title, as it appears on its card
  headline  optional: the title of the write-up page, if it differs
  order     position on the home page and the research index (1 is first)
  meta      one line under the title: status, method, platforms
  summary   one paragraph for the card
  authors   as listed on the paper
  eprint    the paper's IACR ePrint URL; leave empty until it is posted
  code      optional: where the code is published
"""

from __future__ import annotations

import re

from . import markdown
from .shell import A, E, page

EPRINT = re.compile(r"https://eprint\.iacr\.org/(\d{4}/\d+)$")
REQUIRED = ("title", "order", "meta", "summary")


def load_research(content, errors: list[str]) -> list[dict]:
    papers = []
    for path in sorted((content / "research").glob("*.md")):
        if path.stem == "index":
            continue
        meta, body = markdown.read(path)
        where = f"research/{path.name}"
        for key in REQUIRED:
            if not meta.get(key):
                errors.append(f"{where}: missing {key!r} in front matter")
        if meta.get("eprint") and not EPRINT.match(meta["eprint"]):
            errors.append(f"{where}: eprint must look like https://eprint.iacr.org/YYYY/NNNN")
        papers.append({**meta, "slug": path.stem, "body": body})
    papers.sort(key=lambda p: (int(p.get("order") or 99), p["slug"]))
    return papers


def paper_link(paper: dict) -> str:
    """The box under the title, and again at the end: the paper, then the code."""
    if paper.get("eprint"):
        ref = EPRINT.match(paper["eprint"]).group(1)
        text = (
            f'<a href="{E(paper["eprint"])}">Read the paper on IACR ePrint</a>'
            f' <span class="mono">{ref}</span>'
        )
    else:
        text = "The paper will be linked here when it is posted to IACR ePrint."
    if paper.get("code"):
        text += f'<br><a class="code-link" href="{E(paper["code"])}">Code on GitHub</a>'
    return f'      <p class="paper-link">{text}</p>\n'


def cards(papers: list[dict], prefix: str) -> str:
    items = []
    for paper in papers:
        href = f"{prefix}research/{paper['slug']}.html"
        links = [f'<li><a href="{href}">The work, in plain language</a></li>']
        if paper.get("eprint"):
            links.append(f'<li><a href="{E(paper["eprint"])}">Paper on IACR ePrint</a></li>')
        if paper.get("code"):
            links.append(f'<li><a href="{E(paper["code"])}">Code</a></li>')
        items.append(
            f'      <li class="card">\n'
            f'        <h3><a href="{href}">{paper["title"]}</a></h3>\n'
            f'        <p class="meta">{paper["meta"]}</p>\n'
            f'        <p>{markdown.inline(paper["summary"])}</p>\n'
            f'        <ul class="links">{"".join(links)}</ul>\n'
            f"      </li>\n"
        )
    return f'    <ol class="cards">\n{"".join(items)}    </ol>\n'


def render_home(content, papers: list[dict]) -> str:
    meta, body = markdown.read(content / "home.md")
    page_body = f"""    <h1 class="masthead">
      <picture>
        <source srcset="./assets/logo-dark.png" width="934" height="350" media="(prefers-color-scheme: dark)">
        <img src="./assets/logo-light.png" width="952" height="249" alt="Isogeny Labs">
      </picture>
    </h1>
    <section class="thesis" aria-labelledby="thesis-title">
      <h2 id="thesis-title">Thesis</h2>
{markdown.render(body, "      ")}    </section>
    <section aria-labelledby="research-title">
      <h2 id="research-title">Research</h2>
{cards(papers, "./")}    </section>
"""
    return page(
        prefix="./", here="home", title="Isogeny Labs", description=meta["description"],
        body=page_body, og_type="website",
    )


def render_research_index(content, papers: list[dict]) -> str:
    meta, _ = markdown.read(content / "research" / "index.md")
    page_body = f"""    <header>
      <h1>Research</h1>
      <p class="standfirst">{markdown.inline(meta["standfirst"])}</p>
    </header>
{cards(papers, "../")}"""
    return page(
        prefix="../", here="research", title="Research · Isogeny Labs",
        description=meta["description"], body=page_body,
    )


def render_paper(paper: dict) -> str:
    authors = f'      <p class="meta">{paper["authors"]}</p>\n' if paper.get("authors") else ""
    page_body = f"""    <article>
      <nav class="breadcrumb" aria-label="Breadcrumb">
        <a href="index.html">Research</a>
      </nav>
      <header>
        <h1>{paper.get("headline") or paper["title"]}</h1>
        <p class="meta">{paper["meta"]}</p>
{authors}      </header>
{paper_link(paper)}{markdown.render(paper["body"], "      ")}{paper_link(paper)}    </article>
"""
    return page(
        prefix="../", here="research", title=f"{A(paper.get('headline') or paper['title'])} · Isogeny Labs",
        description=paper["summary"], body=page_body,
    )


def render_plain(content, name: str) -> str:
    """About and contact: a heading, a standfirst, and a Markdown body."""
    meta, body = markdown.read(content / f"{name}.md")
    standfirst = f'      <p class="standfirst">{markdown.inline(meta["standfirst"])}</p>\n' if meta.get("standfirst") else ""
    page_body = f"""    <article>
      <header>
        <h1>{meta["heading"]}</h1>
{standfirst}      </header>
{markdown.render(body, "      ")}    </article>
"""
    return page(
        prefix="../", here=name, title=f"{meta['heading']} · Isogeny Labs",
        description=meta["description"], body=page_body,
    )


def build_pages(content) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    papers = load_research(content, errors)
    if errors:
        return {}, errors
    out = {
        "index.html": render_home(content, papers),
        "research/index.html": render_research_index(content, papers),
        "about/index.html": render_plain(content, "about"),
        "contact/index.html": render_plain(content, "contact"),
    }
    for paper in papers:
        out[f"research/{paper['slug']}.html"] = render_paper(paper)
    return out, errors
