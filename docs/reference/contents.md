# What is in the repository

Who writes each path, and whether the generator may overwrite it. "Generated"
means [regenerate the pages](../guides/regenerate-the-pages.md) rewrites it
from the `.github` repository.

| Path | What it is | Written by |
|---|---|---|
| `index.html` | The portal's front page. Regions between `PYDEVICES-...: START` and `END` comments (head tags, hero, project cards) are generated. | Generated regions; the rest by hand |
| `<project>/index.html` | A landing page per project, one for each of the 19 repositories in the database that has a portal page. The head tags and hero are generated. Feature grids and code samples below the hero are not. | Generated regions; the rest by hand |
| `com/index.html` | The page for pydevices.com. It has no generated regions. | By hand |
| `micropython-vst3/index.html` | A "moved" notice for a renamed project. | By hand |
| `404.html` | The Pages error page. | By hand |
| `install.sh` | The script behind `curl -fsSL https://pydevices.github.io/install.sh \| sh`. It clones `micropython-pydevices` and checks the build tools. | By hand |
| `assets/img/` | `logo.svg`, `logo-512.png`, `logo-avatar.png`, `favicon.ico`. | Copied from `.github` |
| `assets/chrome/` | The shared stylesheet and scripts: `site.css`, `site-chrome.js`, `theme-toggle.js`, `hero-runtime.js`, `docs-runtime.js`. | Copied from `.github` |
| `assets/apps/` | The pure-Python demo apps the heroes run. | Copied from `.github` |
| `pyscript-template/pwa/` | The offline PyScript app, mirrored from the `pyscript-template` repository. | Copied from `pyscript-template` |
| `vendor/micropython/` | The WebAssembly MicroPython runtime and its provenance file. | [Rebuilt by hand](../guides/rebuild-the-webassembly-runtime.md) |
| `tools/serve_local.py` | The [preview server](../get-started/install.md). | By hand |
| `.nojekyll` | Tells GitHub Pages to serve the files as they are. | By hand |

Anything marked "Copied" is replaced when the generator runs, so edit its
source, not the copy.
