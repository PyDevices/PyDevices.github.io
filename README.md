# PyDevices.github.io

Source for the organization landing portal at <https://pydevices.github.io/>.

**This repository holds no content of its own.** Everything on the page is
generated from the `.github` repository, and the ecosystem pitch lives in the
[org profile](https://github.com/PyDevices) and
[pydevices/docs/ecosystem.md](https://github.com/PyDevices/pydevices/blob/main/docs/ecosystem.md).
What follows is the mechanics.

## Contents

| Path | Role |
|---|---|
| `index.html` | The portal page. The regions between `<!-- PYDEVICES-…: START/END -->` markers are generated — edit the database, not the markup. |
| `img/logo.svg` | Brand mark, synced from `dotgithub/assets/img/`. |
| `vendor/pydevices-chrome/` | Shared chrome, synced from `dotgithub/assets/`: `site.css`, `site-chrome.js`, `theme-toggle.js`, `tree-nav.js`. |
| `.nojekyll` | Bypasses Jekyll on GitHub Pages. |

## Regenerating

Every landing page in the organization — this portal and the 15 per-repo
`.site/index.html` files — is rendered from
[`data/repos_db.json`](https://github.com/PyDevices/.github/blob/main/data/repos_db.json)
by
[`scripts/generate_sites.py`](https://github.com/PyDevices/.github/blob/main/scripts/generate_sites.py).
That database is the single source of truth for tiers, headlines, descriptions,
and CTA buttons.

The generator resolves sibling repositories relative to its own location, so run
it from a workspace where the repos are checked out side by side:

```bash
python3 dotgithub/scripts/generate_sites.py
```

It rewrites only the marked regions, syncs the chrome assets, and is idempotent —
running it twice produces no second diff. Repos it cannot find are skipped with a
`[SKIP]` line. It also writes the markdown ecosystem map into
`dotgithub/profile/README.md` and `pydevices/docs/ecosystem.md`.

A [workflow in `.github`](https://github.com/PyDevices/.github/blob/main/.github/workflows/ecosystem-map.yml)
validates the database and fails if `profile/README.md` has drifted from it.

## Deployment

Pushes to `main` publish the repository root to GitHub Pages at
<https://pydevices.github.io/>. There is no build step.
