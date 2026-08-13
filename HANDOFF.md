# Hand-Off Notes — PyDevices Organization Web Redesign

## Current Status (Completed Phase 2 Above-the-Fold Redesign)
We have completed Phase 2 **Above-the-Fold** redesign across all **PyDevices** organization repository landing pages (`https://PyDevices.github.io/*`).

### Summary of Completed Above-the-Fold Features
1. **Org Chrome Global Nav Links (`[1b]`)**:
   - `Tree View` modal button
   - `Core Stack` -> `pydevices`
   - `Toolkits` -> `pygraphics`
   - `Native C` -> `displayif`
   - `Gallery` -> `pydevices-examples/pyscript/`
   - `GitHub` -> org profile
2. **Eyebrow Tag (`[2a1]`)**: Set to just the clean repository name (`palettes`, `pygraphics`, `pdwidgets`, etc.).
3. **Headline (`[2b]`)**: Formatted as `repo-name — Short Headline` at font size `~1.85rem`.
4. **Hero Lead Paragraph (`[2c]`)**: Unconstrained horizontally to span full container width (`1080px`).
5. **4-Button CTA Action Bar (`[2d]`)**:
   - Standardized to **exactly 4 buttons** across all 16 repos (no maintainer/publishing links).
   - Target-specific tier button border/text colors (Amber for Core, Emerald for Toolkits, Blue for Native C, Purple for Hosts, Steel Cyan for Tools/cmods/MIP).
6. **Org Asset Sync**: Synced `site.css`, `site-chrome.js`, `tree-nav.js`, and `theme-toggle.js` to `web/vendor/pydevices-chrome/` across all subrepositories.

---

## Deferred Items for Next Session (Pick-Up Points)

1. **Below-the-Fold Content Review**:
   - User will inspect the redesigned landing pages live on GitHub Pages / local site.
   - Review lower section components (feature grids, specs, code blocks, tables).

2. **PyScript Gallery Revamp (Phase 3)**:
   - Overhaul the PyScript gallery generator in `pydevices-examples`.
   - Re-architect gallery card layouts, live runner sandboxes, and MIP package imports.

---

## Workspace Repositories Modified & Pushed to `main`
- `PyDevices.github.io`
- `pydevices`
- `palettes`
- `pygraphics`
- `pdwidgets`
- `displayif`
- `lvgl-bindings`
- `lvgl-micropython`
- `lvgl-python`
- `lvgl-circuitpython`
- `pydevices-android-template`
- `mpftp`
