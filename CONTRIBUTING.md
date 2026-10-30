# Contributing

Most of this repository is generated or copied from somewhere else, so the
first question is where a change belongs.

| You want to change | Edit it in |
|---|---|
| A landing page's title, description, headline or buttons, or the portal's cards | `data/repos_db.json` in the `.github` repository, then [regenerate the pages](docs/guides/regenerate-the-pages.md) |
| Below a landing page's hero: feature grids, code samples, prose | The page's `index.html` here, by hand |
| The shared stylesheet, scripts, logo or demo apps under `assets/` | The `.github` repository's `assets/`, then regenerate |
| The offline app under `pyscript-template/pwa/` | The `pyscript-template` repository, then [refresh the copy](docs/guides/regenerate-the-pages.md#refresh-the-pyscript-template-copy) |
| The MicroPython runtime under `vendor/micropython/` | `micropython-pydevices`, [rebuilt for the web](docs/guides/rebuild-the-webassembly-runtime.md) |
| `tools/serve_local.py`, `install.sh`, `404.html`, `com/` | Here |

Open an [issue](https://github.com/PyDevices/PyDevices.github.io/issues) for a
wrong or missing fact on the site. Pushes to `main` publish the site
([how](docs/how-it-works/index.md#publishing)), so check a page in the
[local preview](docs/get-started/install.md) before you push.
