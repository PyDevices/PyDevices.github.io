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
- `assets/img/logo.svg` — the PyDevices mark.

No build step: this is a static site, published directly from `main`.

See [`docs/github-presence.md`](docs/github-presence.md) for a reference on
how the PyDevices GitHub org is set up (Discussions, Issues, Pages sites,
licensing, and what's still a manual step).
