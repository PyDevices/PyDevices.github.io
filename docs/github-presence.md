# PyDevices on GitHub — feature reference

A map of how the [PyDevices](https://github.com/PyDevices) GitHub org is set
up: where discussions, issues, docs, and Pages sites live. Written to answer
"how do I...?" / "where do I find...?" questions later without re-deriving
the answer from scratch.

## Quick answers

| I want to... | Go here |
|---|---|
| Ask a question / propose an idea / show something I built | [pydisplay Discussions](https://github.com/PyDevices/pydisplay/discussions) |
| Find or share a one-off example that's too narrow for the official examples | [pydisplay Discussions → Recipes](https://github.com/PyDevices/pydisplay/discussions/categories/recipes) |
| Report a bug or request a feature | Issues on the **specific repo** it affects (see [repo map](#repos--pages-sites)); use the Bug report / Feature request templates |
| Find contribution guidelines shared across repos | [PyDevices/.github CONTRIBUTING.md](https://github.com/PyDevices/.github/blob/main/CONTRIBUTING.md) |
| Read the org's public-facing "about us" | [PyDevices/.github profile README](https://github.com/PyDevices/.github/blob/main/profile/README.md) (rendered on [github.com/PyDevices](https://github.com/PyDevices)) |
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
- **Recipes** ([pydisplay Discussions → Recipes](https://github.com/PyDevices/pydisplay/discussions/categories/recipes),
  open-ended format, not answerable) is for one-off examples/how-tos that
  answer a specific question well but are too narrow to promote into
  `src/examples/`. If one gets enough traction, promote it into a real
  example later — this category is meant to be a low-friction incubator,
  not a permanent home for everything filed into it.
- **Wikis** are disabled org-wide — reference content lives in each repo's
  `README.md`/`AGENTS.md`, in
  [pydisplay's docs](https://pydisplay.readthedocs.io), or on a Pages site,
  not in a wiki page.

## Org profile

- **About / description / website**: set on the org (`https://pydevices.github.io/`).

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

All owned repos are **MIT**, using GitHub's standard single-author template
(so it's correctly detected as MIT rather than `NOASSERTION`/`Other`). A
handful of files in **pydisplay** that still carry code from other authors
(`src/add_ons/tft_text.py`, `tft_write.py`, `tft_bitmap.py`, and the
`polygon()` function in `src/lib/graphics/_shapes.py`, tracing back through
Russ Hughes' st7789_mpy driver to Ivan Belokobylskiy's st7789py_mpy) keep
their own self-contained MIT header with that attribution — those in-file
notices govern those specific files/functions; the root `LICENSE` governs
everything else. Keep any such pointer *out* of the root `LICENSE` file
itself: GitHub's license detector does a similarity match against the exact
template, and extra text (even a short explanatory paragraph) can drop it
below the confidence threshold and flip the repo back to `NOASSERTION`.

## Topics

Each repo has GitHub topics set for discoverability (e.g. `lvgl`,
`micropython`, `circuitpython`, `user-c-modules`) — check a repo's sidebar on
github.com rather than duplicating the list here, since topics change more
often than this doc will be updated.
