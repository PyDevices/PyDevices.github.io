# PyDevices.github.io

Source for the [PyDevices](https://pydevices.github.io/) org landing page,
served from the `main` branch root via GitHub Pages.

This repo also hosts the shared site chrome used across PyDevices project
Pages:

- `assets/css/site.css` — shared design tokens + layout primitives (header,
  hero, buttons, cards, footer). Linked by absolute URL
  (`https://pydevices.github.io/assets/css/site.css`) from other repos'
  Pages, which also vendor a local copy under
  `web/vendor/pydevices-chrome/site.css` for offline/CI use.
- `assets/img/logo.svg` — the PyDevices mark (header / org hero).
- `assets/img/products/*.svg` — per-product hero marks used by sibling
  Pages sites (same icons as the org landing cards). Product heroes should
  use `logo-badge product-mark` with these SVGs; keep the header brand on
  the org mark.

No build step: this is a static site, published directly from `main`.

See [PyDevices/.github `github-presence.md`](https://github.com/PyDevices/.github/blob/main/github-presence.md)
for a reference on how the org is set up (Discussions, Issues, Pages sites,
licensing).
