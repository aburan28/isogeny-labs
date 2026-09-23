# Isogeny Labs website

Static website for Isogeny Labs, a cryptography research and engineering lab:
hardness analysis, isogeny and elliptic-curve systems, post-quantum migration,
and protocol review. It also hosts the **cryptanalysis library** at
`/cryptanalysis/` — an open reference on how the underlying hardness assumptions
are actually attacked.

## Preview locally

```sh
python3 -m http.server 8000 --bind 127.0.0.1 --directory .
```

Open <http://localhost:8000>. There is no package installation, and the pages that
ship are plain HTML — nothing is compiled at request time. All asset paths are
relative, so the site also serves correctly from a subdirectory.

## Files

- `index.html`: the home page: current work, services, and contact.
- `styles.css`: one stylesheet for every page. A single text column, Source Serif 4
  for text and IBM Plex Mono for figures, with a dark scheme that follows the
  reader's system setting.
- `script.js`: fills in the copyright year, shared by every page.
- `favicon.svg`: the site icon, referenced by every page.
- `content/cryptanalysis/*.json`: the source of truth for the library.
- `cryptanalysis/*.html`: the rendered library. **Generated — do not hand-edit.**
- `tools/build_cryptanalysis.py`, `tools/check_links.py`: the generator and the
  link checker, both stdlib-only.

The stylesheet requests Source Serif 4 and IBM Plex Mono from Google Fonts; system
fonts are used if that service is unavailable. Everything else is local, and there
are no binary image assets.

### Writing for the site

The site should read like it was written by the people doing the work. Prefer a
measured figure, a named result, or a link to code over an adjective. Write plain
sentences: no slogans, no taglines split across lines, and no section eyebrows or
decorative numbering. If a number on the home page changes in the source
repository, change it here too, and link to where it was measured.

## The cryptanalysis library

Each technique is one JSON file in `content/cryptanalysis/`, rendered into a page
by `tools/build_cryptanalysis.py`. The generated HTML is committed, so the served
site stays build-free; CI re-runs the generator and fails if the two have drifted.

To add or edit a technique:

```sh
cp content/cryptanalysis/pollard-rho.json content/cryptanalysis/my-technique.json
$EDITOR content/cryptanalysis/my-technique.json
python3 tools/build_cryptanalysis.py     # rewrites cryptanalysis/
python3 tools/check_links.py
```

Commit both the JSON and the regenerated HTML. A technique's `family` must be one
declared in `content/cryptanalysis/index.json`; entries listed under a family's
`planned` array appear on the index as queued, with no page behind them.

Each entry carries `facts` (the summary table), `sections` of `blocks`, and
`references`. The generator refuses to build an entry with no `references`: the
library's premise is that every page points at primary sources rather than
restating folklore, and that is enforced rather than merely intended.

Block types are `p`, `ul`, `steps`, `math` (with an optional `label`), and `note`
(with an optional `note_label`). Text may contain inline HTML — every string is
authored in this repository, so nothing untrusted is interpolated.

### House rules for content

- State the cost *and* the boundary. A page that does not say where the attack
  stops applying is not finished.
- Prefer a measured record computation over an asymptotic bound; give both when
  both exist.
- Never cite a result you have not read, and never state a complexity more
  precisely than the source does. Where a bound rests on a heuristic, say so on
  the page.

## Before launch

The contact section deliberately reads "Contact details coming soon." Replace that
text in `#contact-slot` with the approved business email or booking link before
accepting enquiries. There is no enquiry form and no backend.

## Deployment

`.github/workflows/pages.yml` publishes the site to GitHub Pages on every push to
`main`, and can also be run manually from the Actions tab. It runs the same checks
as CI, copies the site files and the `cryptanalysis/` directory into `_site/`, adds
`.nojekyll` so Pages serves them verbatim, and deploys via the official Pages
actions. No build tooling is installed.

This requires Pages to be enabled once in **Settings → Pages → Source → GitHub
Actions**. Until that is set, the deploy job fails with a Pages-not-enabled error;
the site itself is unaffected.

`.github/workflows/ci.yml` runs on pull requests and on pushes to `main`.

## Checks

```sh
node --check script.js
python3 tools/build_cryptanalysis.py --check   # generated pages are current
python3 tools/check_links.py                   # references, anchors, duplicate ids
```

For content changes, review the pages at desktop and phone widths, in both light
and dark mode.
