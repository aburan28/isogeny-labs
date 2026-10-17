"""A small Markdown reader for the hand-written pages: home, research, about, contact.

Only what those pages need, so nothing has to be installed:

  front matter   `---` fenced `key: value` lines at the top of the file
  blocks         ## and ### headings, paragraphs, - and 1. lists, > quotes,
                 ``` fenced code, and raw HTML blocks (a line starting with `<`)
  inline         **bold**, *italic*, `code`, [text](url), and inline HTML

As with the JSON content, every file is authored in this repository, so inline
HTML is passed through rather than escaped.
"""

from __future__ import annotations

import html
import pathlib
import re

from .shell import slugify

INLINE = [
    (re.compile(r"`([^`]+)`"), lambda m: f"<code>{html.escape(m.group(1))}</code>"),
    (re.compile(r"\*\*(.+?)\*\*"), lambda m: f"<strong>{m.group(1)}</strong>"),
    (re.compile(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])"), lambda m: f"<em>{m.group(1)}</em>"),
    (re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)"), lambda m: f'<a href="{html.escape(m.group(2))}">{m.group(1)}</a>'),
]


def inline(text: str) -> str:
    for pattern, repl in INLINE:
        text = pattern.sub(repl, text)
    return text


def read(path: pathlib.Path) -> tuple[dict[str, str], str]:
    """Split a file into its front matter and its Markdown body."""
    text = path.read_text()
    meta: dict[str, str] = {}
    if text.startswith("---\n"):
        head, _, text = text[4:].partition("\n---\n")
        for line in head.splitlines():
            if line.strip() and not line.lstrip().startswith("#"):
                key, _, value = line.partition(":")
                meta[key.strip()] = value.strip()
    return meta, text


def render(text: str, indent: str = "    ") -> str:
    """Render a Markdown body to HTML, one block per line group."""
    out: list[str] = []
    lines = text.strip("\n").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif line.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            code = html.escape("\n".join(lines[i + 1 : j]))
            out.append(f'{indent}<pre class="listing">{code}</pre>')
            i = j + 1
        elif m := re.match(r"(#{2,3}) (.+)", line):
            level, title = len(m.group(1)), m.group(2).strip()
            out.append(f'{indent}<h{level} id="{slugify(title)}">{inline(title)}</h{level}>')
            i += 1
        elif line.startswith("<"):
            j = i
            while j < len(lines) and lines[j].strip():
                j += 1
            out.append("\n".join(indent + l for l in lines[i:j]))
            i = j
        elif re.match(r"(- |\d+\. )", line):
            tag = "ul" if line.startswith("- ") else "ol"
            items: list[str] = []
            while i < len(lines) and lines[i].strip():
                if m := re.match(r"(?:- |\d+\. )(.*)", lines[i]):
                    items.append(m.group(1))
                else:  # continuation of the previous item
                    items[-1] += " " + lines[i].strip()
                i += 1
            body = "".join(f"{indent}  <li>{inline(item)}</li>\n" for item in items)
            out.append(f"{indent}<{tag}>\n{body}{indent}</{tag}>")
        elif line.startswith(">"):
            quote = []
            while i < len(lines) and lines[i].startswith(">"):
                quote.append(lines[i].lstrip("> ").rstrip())
                i += 1
            out.append(f'{indent}<aside class="note"><p>{inline(" ".join(quote))}</p></aside>')
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not re.match(r"(#{2,3} |- |\d+\. |>|```|<)", lines[i]):
                para.append(lines[i].strip())
                i += 1
            out.append(f"{indent}<p>{inline(' '.join(para))}</p>")
    return "\n".join(out) + "\n"
