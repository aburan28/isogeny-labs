# Isogeny Labs website

Static website for Isogeny Labs, a cryptography research and engineering lab:
hardness analysis, isogeny and elliptic-curve systems, post-quantum migration,
and protocol review. Besides the home page it hosts three generated sections:

- `/cryptanalysis/` — the **cryptanalysis reference**: how hardness assumptions are
  actually attacked, with costs, records, and where each attack stops applying.
- `/notes/` — **notes**: elliptic curves and the ECDLP, and worked examples of the
  attacks, computed by the build on groups small enough to follow by hand.
- `/schemes/` — the **catalogue of schemes**, with full pages on ML-KEM, ML-DSA and
  SQIsign.

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
- `content/{cryptanalysis,notes,schemes}/*.json`: the source of truth for the
  generated sections, one file per page plus an `index.json` per section.
- `cryptanalysis/`, `notes/`, `schemes/`: the rendered pages. **Generated — do not
  hand-edit.**
- `tools/build_site.py`: builds all three sections. The code lives in
  `tools/sitegen/`: `shell.py` (page shell and content blocks), `collections.py`
  (loading, validation, rendering), `figures.py` (SVG figures), and `worked/` (the
  worked examples, see below).
- `tools/check_links.py`: the link checker.

Everything is stdlib-only Python; nothing is installed.

The stylesheet requests Source Serif 4 and IBM Plex Mono from Google Fonts; system
fonts are used if that service is unavailable. Everything else is local, and there
are no binary image assets.

### Writing for the site

The site should read like it was written by the people doing the work. Prefer a
measured figure, a named result, or a link to code over an adjective. Write plain
sentences: no slogans, no taglines split across lines, and no section eyebrows or
decorative numbering. If a number on the home page changes in the source
repository, change it here too, and link to where it was measured.

## Generated sections

Each page is one JSON file in `content/<section>/`, rendered by
`tools/build_site.py`. The generated HTML is committed, so the served site stays
build-free; CI re-runs the generator and fails if the two have drifted.

```sh
$EDITOR content/notes/ecdlp.json
python3 tools/build_site.py      # rewrites cryptanalysis/, notes/ and schemes/
python3 tools/check_links.py
```

Commit both the JSON and the regenerated HTML. Each entry names its `family`
(cryptanalysis) or `group` (notes, schemes), which must be declared in that
section's `index.json`, and carries `facts`, `sections` of `blocks`, `references`,
and optional `related` pages (a bare slug for the same section, or `notes/ecdlp`
across sections). The generator refuses an entry with no `references`: every page
points at primary sources rather than restating folklore, and that is enforced
rather than merely intended.

Block types are `p`, `ul`, `steps`, `math` (optional `label`), `note` (optional
`note_label`), `h3`, `table` (`head`, `rows`, optional `caption` and `numeric`
column indices), `pre` (optional `label`), `dl`, and `svg` (generated figures
only). Text may contain inline HTML — every string is authored in this
repository, so nothing untrusted is interpolated.

In the cryptanalysis reference, entries under a family's `planned` array appear on
the index as queued. Each declares the `slug` it will become, and the build fails
if a queued slug has been written up, so a technique is never counted twice.

The schemes index is a catalogue rather than a list of pages: its entries live in
`content/schemes/index.json`, and those with a full page name it in `page`.

### Worked examples

An entry with `"compute": "<module>"` is filled in by `tools/sitegen/worked/<module>.py`
at build time. The module returns values for `{{placeholders}}` in the entry's
strings and whole blocks for `{"computed": "<name>"}` markers. A placeholder with no
value is a build error, and so is any `{{` left in a rendered page, so a number on
a worked-example page can only come from the code that computed it.

The modules draw randomness from a SHA-256 counter-mode generator in
`worked/arith.py` rather than `random`, so the pages are byte-identical on every
Python version, and they check their own answers: every discrete logarithm is
verified by exponentiation or scalar multiplication before it is printed, and the
published group orders in the standard-curves table are checked to be prime and to
lie in their field's Hasse interval. `--check` therefore re-derives every worked
example on every CI run. The whole build takes about a second.

Figures are inline SVG from `tools/sitegen/figures.py`, drawn from the same computed
data and styled through the stylesheet's colour tokens, so dark mode needs no second
copy. The two chart series colours, `--series-1` and `--series-2`, were checked for
lightness, chroma, colour-blind separation and contrast against both page surfaces;
re-check them if either surface colour changes.

### House rules for content

- State the cost *and* the boundary. A page that does not say where the attack
  stops applying is not finished.
- Prefer a measured record computation over an asymptotic bound; give both when
  both exist.
- Never cite a result you have not read, and never state a complexity more
  precisely than the source does. Where a bound rests on a heuristic, say so on
  the page.
- Sizes, parameters and timings on scheme pages come from the standard or the
  designers' specification, and the page says which version.
- Numbers on worked-example pages are placeholders filled by code, never typed.

## Before launch

The contact section deliberately reads "Contact details coming soon." Replace that
text in `#contact-slot` with the approved business email or booking link before
accepting enquiries. There is no enquiry form and no backend.

## Deployment

`.github/workflows/pages.yml` publishes the site to GitHub Pages on every push to
`main`, and can also be run manually from the Actions tab. It runs the same checks
as CI, copies the site files and the `cryptanalysis/`, `notes/` and `schemes/`
directories into `_site/`, adds
`.nojekyll` so Pages serves them verbatim, and deploys via the official Pages
actions. No build tooling is installed.

This requires Pages to be enabled once in **Settings → Pages → Source → GitHub
Actions**. Until that is set, the deploy job fails with a Pages-not-enabled error;
the site itself is unaffected.

`.github/workflows/ci.yml` runs on pull requests and on pushes to `main`.

## Checks

```sh
node --check script.js
python3 tools/build_site.py --check   # generated pages are current; worked examples recomputed
python3 tools/check_links.py                   # references, anchors, duplicate ids
```

For content changes, review the pages at desktop and phone widths, in both light
and dark mode.
