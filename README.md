# Isogeny Labs website

Static website for Isogeny Labs, a cryptography research and engineering lab:
hardness analysis, isogeny and elliptic-curve systems, post-quantum migration,
and protocol review.

## Preview locally

```sh
python3 -m http.server 8000 --bind 127.0.0.1 --directory .
```

Open <http://localhost:8000>. There is no build step and no package installation.
All asset paths are relative, so the site also serves correctly from a subdirectory.

## Files

- `index.html`: page copy, services, primitives panel, navigation, and favicon.
- `styles.css`: typography, responsive layouts, and the indigo/violet theme.
- `script.js`: mobile navigation and copyright year.

The hero artwork is an inline SVG isogeny graph generated directly in the page —
nodes are curves and edges are isogenies between them. There are no binary image
assets, so nothing needs to be fetched or optimized.

The stylesheet requests DM Sans and Space Grotesk from Google Fonts; system fonts
are used if that service is unavailable. Everything else is local.

## Before launch

The contact section deliberately reads "Contact details coming soon." Replace that
text in `#contact-slot` with the approved business email or booking link before
accepting enquiries. There is no enquiry form and no backend.

## Deployment

`.github/workflows/pages.yml` publishes the site to GitHub Pages on every push to
`main`, and can also be run manually from the Actions tab. It copies the three site
files into `_site/`, adds `.nojekyll` so Pages serves them verbatim, and deploys via
the official Pages actions. No build tooling is involved.

This requires Pages to be enabled once in **Settings → Pages → Source → GitHub
Actions**. Until that is set, the deploy job fails with a Pages-not-enabled error;
the site itself is unaffected.

`.github/workflows/ci.yml` runs on pull requests and on pushes to `main`: it checks
the script syntax and verifies that every local file reference and in-page anchor in
`index.html` actually resolves.

## Checks

```sh
node --check script.js
```

For content changes, verify local asset references and section anchors. Review the
page at desktop and mobile widths and exercise the menu, the service disclosures,
and keyboard navigation (including Escape to close the mobile menu).
