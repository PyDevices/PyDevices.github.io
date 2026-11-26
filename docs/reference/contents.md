# What is in the repository

Who writes each path, and whether the generator may overwrite it. "Generated"
means [regenerate the pages](../guides/regenerate-the-pages.md) rewrites it
from the `.github` repository.

| Path | What it is | Written by |
|---|---|---|
| `index.html` | The portal's front page. Regions between `PYDEVICES-...: START` and `END` comments (head tags, hero, project cards) are generated. | Generated regions; the rest by hand |
| `<project>/index.html` | A landing page per project, one for each repository in the database that has a portal page. The head tags and hero are generated. Feature grids and code samples below the hero are not. | Generated regions; the rest by hand |
| `com/`, `mcuctl/`, `mpvst/` | "Moved" notices that send a browser to the same page on [pydevices.com](https://pydevices.com/), where the tools' pages live. | By hand |
| `micropython-vst3/index.html` | A "moved" notice for a renamed project. | By hand |
| `404.html` | The Pages error page. | By hand |
| `install.sh` | The script behind `curl -fsSL https://omnipython.org/install.sh \| sh`. It clones `omnipython-builds` and checks the build tools. | By hand |
| `assets/img/` | `logo.svg`, `logo-512.png`, `logo-avatar.png`, `favicon.ico`. | Copied from `.github` |
| `assets/chrome/` | The shared stylesheet and scripts: `site.css`, `site-chrome.js`, `theme-toggle.js`, `hero-runtime.js`, `docs-runtime.js`. | Copied from `.github` |
| `assets/apps/` | The pure-Python demo apps the other heroes run. | Copied from `.github` |
| `pyscript-template/pwa/` | The offline PyScript app, mirrored from the `pyscript-template` repository. | Copied from `pyscript-template` |
| `vendor/micropython/` | The WebAssembly MicroPython runtime and its provenance file. | [Rebuilt by hand](../guides/rebuild-the-webassembly-runtime.md) |
| `vendor/allapps/` | The all-apps runtime, with every app frozen in, which the front page's watch boots; its provenance file and `allapps.json`. | [Rebuilt by hand](../guides/rebuild-the-webassembly-runtime.md#the-all-apps-runtime) |
| `tools/serve_local.py` | The [preview server](../get-started/install.md). | By hand |
| `.nojekyll` | Tells GitHub Pages to serve the files as they are. | By hand |

Anything marked "Copied" is replaced when the generator runs, so edit its
source, not the copy.
