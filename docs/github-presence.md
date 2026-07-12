# PyDevices on GitHub — feature reference

A map of how the [PyDevices](https://github.com/PyDevices) GitHub org is set
up: where discussions, issues, docs, and Pages sites live, and what's still
a manual step. Written to answer "how do I...?" / "where do I find...?"
questions later without re-deriving the answer from scratch.

## Quick answers

| I want to... | Go here |
|---|---|
| Ask a question / propose an idea / show something I built | [pydisplay Discussions](https://github.com/PyDevices/pydisplay/discussions) |
| Report a bug or request a feature | Issues on the **specific repo** it affects (see [repo map](#repos--pages-sites)); use the Bug report / Feature request templates |
| Find contribution guidelines shared across repos | [PyDevices/.github CONTRIBUTING.md](https://github.com/PyDevices/.github/blob/main/CONTRIBUTING.md) |
| Read the org's public-facing "about us" | [PyDevices/.github profile README](https://github.com/PyDevices/.github/blob/main/profile/README.md) (rendered on [github.com/PyDevices](https://github.com/PyDevices)) |
| Find the shared CSS/JS used by every Pages site | [`assets/css/site.css`](../assets/css/site.css) and [`assets/js/theme-toggle.js`](../assets/js/theme-toggle.js) in this repo, canonical at `https://pydevices.github.io/assets/...` |
| Read pydisplay's full documentation | [pydisplay.readthedocs.io](https://pydisplay.readthedocs.io) |
| Try the library without installing anything | [PyScript browser demos](https://pydevices.github.io/pydisplay/pyscript/) |

## Getting help: Discussions vs. Issues

- **Discussions** are enabled only on **pydisplay** and **lv_bindings** (the
  two repos most likely to get open-ended questions). Everything else routes
  through pydisplay Discussions — see the org's pinned "get help" pointer.
- **Issues** are enabled on every owned repo (bug reports / feature requests).
  Default issue *templates* (`bug.yml`, `feature.yml`) live in the org's
  [`.github`](https://github.com/PyDevices/.github/tree/main/.github/ISSUE_TEMPLATE)
  repo and apply automatically to any repo that doesn't define its own.
- If you're not sure which repo an issue belongs to, open it on
  [pydisplay](https://github.com/PyDevices/pydisplay/issues) — per
  CONTRIBUTING.md, that's the routing point.
- **Wikis** are present (GitHub's default) but intentionally unused — reference
  content lives in each repo's `README.md`/`AGENTS.md`, in
  [pydisplay's docs](https://pydisplay.readthedocs.io), or on a Pages site,
  not in a wiki page.

## Org profile

- **About / description / website**: set on the org (`https://pydevices.github.io/`).
- **Org avatar**: **not set yet** — GitHub has no public API for uploading an
  org avatar, so this is a manual step: Settings → Profile on
  [github.com/PyDevices](https://github.com/PyDevices) (there's a rendered
  copy of the logo at `assets/img/logo.svg` in this repo to use as source).
- **Pinned repositories**: **not set yet** — GitHub has no REST/GraphQL
  mutation for pinning an *organization's* repos (only user accounts), so
  this is also manual: "Customize pins" on
  [github.com/PyDevices](https://github.com/PyDevices). Suggested picks:
  `pydisplay`, `lv_bindings`, `cmods`, `displayif`, `graphics`,
  `lv_cpython_mod`.

## Repos & Pages sites

Every repo below ships a GitHub Pages site sharing the same chrome
(dark-default theme, light toggle in the header) from this repo's
`assets/css/site.css`.

| Repo | Role | Pages site |
|---|---|---|
| [pydisplay](https://github.com/PyDevices/pydisplay) | Core pure-Python display/input/graphics library | [pydevices.github.io/pydisplay](https://pydevices.github.io/pydisplay/) (+ [PyScript demos](https://pydevices.github.io/pydisplay/pyscript/)) |
| [lv_bindings](https://github.com/PyDevices/lv_bindings) | LVGL C→binding generator (source of truth for the native cmods) | [pydevices.github.io/lv_bindings](https://pydevices.github.io/lv_bindings/) |
| [cmods](https://github.com/PyDevices/cmods) | Workspace that builds/smoke-tests the native-module matrix together | [pydevices.github.io/cmods](https://pydevices.github.io/cmods/) |
| [displayif](https://github.com/PyDevices/displayif) | Native display bus/framebuffer modules | [pydevices.github.io/displayif](https://pydevices.github.io/displayif/) |
| [graphics](https://github.com/PyDevices/graphics) | Native FrameBuffer/Area module | [pydevices.github.io/graphics](https://pydevices.github.io/graphics/) |
| [usdl2](https://github.com/PyDevices/usdl2) | Native SDL2 subset for pydisplay's desktop backend | [pydevices.github.io/usdl2](https://pydevices.github.io/usdl2/) |
| [lv_micropython_cmod](https://github.com/PyDevices/lv_micropython_cmod) | MicroPython user C module glue for LVGL | [pydevices.github.io/lv_micropython_cmod](https://pydevices.github.io/lv_micropython_cmod/) |
| [lv_circuitpython_mod](https://github.com/PyDevices/lv_circuitpython_mod) | CircuitPython integration for LVGL | [pydevices.github.io/lv_circuitpython_mod](https://pydevices.github.io/lv_circuitpython_mod/) |
| [lv_cpython_mod](https://github.com/PyDevices/lv_cpython_mod) | Native CPython LVGL extension (`import lvgl`) | [pydevices.github.io/lv_cpython_mod](https://pydevices.github.io/lv_cpython_mod/) |
| [pydisplay_android](https://github.com/PyDevices/pydisplay_android) | Android APK path for pydisplay | [pydevices.github.io/pydisplay_android](https://pydevices.github.io/pydisplay_android/) |
| [PyDevices.github.io](https://github.com/PyDevices/PyDevices.github.io) | This repo — org landing + shared chrome | [pydevices.github.io](https://pydevices.github.io/) |
| [.github](https://github.com/PyDevices/.github) | Org profile README, issue templates, CONTRIBUTING.md | *(no Pages site — org metadata only)* |
| [micropython-lib](https://github.com/PyDevices/micropython-lib) | Fork carrying PyDevices' micropython-lib packages for `mip install` | *(no dedicated marketing site — it's a package index fork, not a product)* |

## Licensing

All owned repos are **MIT**, except **pydisplay**, which carries a LICENSE
file with mixed attribution (Russ Hughes' original work plus Brad Barnett's
additions) — GitHub shows this as `NOASSERTION` since it isn't a bare
single-author MIT template, but the file itself grants the same permissive
terms.

## Topics

Each repo has GitHub topics set for discoverability (e.g. `lvgl`,
`micropython`, `circuitpython`, `user-c-modules`) — check a repo's sidebar on
github.com rather than duplicating the list here, since topics change more
often than this doc will be updated.
