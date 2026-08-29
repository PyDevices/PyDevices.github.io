# PyDevices.github.io

Source for the organization landing portal at <https://pydevices.github.io/>.

This repository is not a blank shell — it holds the portal's own `index.html`,
a per-repo landing page for every tier-1..5 project (`displayif/`, `pygraphics/`,
`mpftp/`, `workbench/`, …), the `404.html` error page, a vendored copy of the
`pyscript-template` PWA demo, and a `vendor/` tree of prebuilt WebAssembly
runtimes. What it does **not** hold is the source of truth for that content:
the head tags and hero section of every generated page (title, description,
headline, CTA buttons, theme color) are rendered from the `.github` repository's
database and should be edited there, not by hand here. The ecosystem pitch
itself lives in the [org profile](https://github.com/PyDevices) and
[pydevices/docs/ecosystem.md](https://github.com/PyDevices/pydevices/blob/main/docs/ecosystem.md).

## Contents

| Path | Role |
|---|---|
| `index.html` | The portal page. The regions between `<!-- PYDEVICES-…: START/END -->` markers are generated — edit the database, not the markup. |
| `<repo>/index.html` | One landing page per repo (e.g. `displayif/`, `pygraphics/`, `mpftp/`, `workbench/`). The head-tags and above-the-fold hero regions are generated the same way as the portal page; everything below the hero (feature grids, code samples) is hand-authored directly in this repo and is untouched by regeneration. |
| `assets/img/` | Brand marks, synced from `dotgithub/assets/img/`: `logo.svg`, `logo-512.png`, `logo-avatar.png`. |
| `assets/chrome/` | Shared first-party chrome, synced from `dotgithub/assets/`: `site.css`, `site-chrome.js`, `theme-toggle.js`, `hero-runtime.js`. |
| `assets/apps/` | Interactive pure-Python apps, synced from `dotgithub/assets/apps/`. |
| `pyscript-template/pwa/` | The `pyscript-template` repo's offline PWA demo, mirrored in whole by the generator's `sync_assets()` step so it publishes from this Pages root. Re-vendor it by re-running the generator after `pyscript-template` bumps its PyScript pin — don't hand-edit the copy here. |
| `vendor/micropython/` | Centralized third-party WebAssembly MicroPython runtime, rebuilt separately from this generator (see `cmods`). |
| `404.html` | Custom GitHub Pages 404. |
| `.nojekyll` | Bypasses Jekyll on GitHub Pages. |

## Regenerating

The head-tags and hero section of every generated landing page in the
organization — this portal, its per-repo subpages in this repo, and a few
repos' own `.site/index.html` pages — are rendered from
[`data/repos_db.json`](https://github.com/PyDevices/.github/blob/main/data/repos_db.json)
by
[`scripts/generate_sites.py`](https://github.com/PyDevices/.github/blob/main/scripts/generate_sites.py).
That database is the single source of truth for tiers, headlines, descriptions,
and CTA buttons. Everything else on a per-repo page (feature grids, code
snippets, deep-dive prose) is static HTML maintained by hand in this repo and
is not touched by regeneration — edit it directly here.

The generator resolves sibling repositories relative to its own location, so run
it from a workspace where the repos are checked out side by side:

```bash
python3 dotgithub/scripts/generate_sites.py
```

It rewrites only the marked regions, syncs the chrome assets, and is idempotent —
running it twice produces no second diff. Repos it cannot find are skipped with a
`[SKIP]` line. It also writes the markdown ecosystem map into
`dotgithub/profile/README.md` and `pydevices/docs/ecosystem.md`.

Regeneration is **deliberately manual** — the database changes rarely, and
running the generator is a one-line step when it does. It validates the database
on every run and exits non-zero on a malformed entry, so the check happens at the
moment you would notice it.

## Deployment

Pushes to `main` publish the repository root to GitHub Pages at
<https://pydevices.github.io/>. There is no build step.
