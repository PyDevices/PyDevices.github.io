# PyDevices.github.io — Organization Portal

Welcome to the **PyDevices Organization Portal** source repository. This site serves as the unified landing hub for the entire [PyDevices](https://pydevices.github.io/) ecosystem — bridging hardware abstraction drivers, 2D graphics engines, widget toolkits, native LVGL C extensions, and target application hosts across MicroPython, CircuitPython, CPython, PyScript, and Android.

---

## 🏛️ Ecosystem Overview & Architecture

All landing pages across the organization are centrally generated from the **[`.github` (*dotgithub*)](https://github.com/PyDevices/.github)** repository.

For the `PyDevices.github.io` portal repository:
- **`index.html`**: Organization portal landing page.
- **`img/logo.svg`**: PyDevices brand mark.
- **`vendor/pydevices-chrome/`**: Synced shared styling (`site.css`), theme toggle (`theme-toggle.js`), header/footer injector (`site-chrome.js`), and tree navigation (`tree-nav.js`).
- **`.nojekyll`**: Bypasses Jekyll processing on GitHub Pages.

---

## ⚡ Centralized Generator & Single Source of Truth

The entire PyDevices web presence is managed centrally from the **[`.github` (*dotgithub*)](https://github.com/PyDevices/.github)** repository:

1. **Database ([`repos_db.json`](https://github.com/PyDevices/.github/blob/main/data/repos_db.json))**: Single Source of Truth storing eyebrows, headlines, descriptions, tier colors, and 4-button CTA layouts for all repositories.
2. **Canonical Assets Vault ([`dotgithub/assets/`](https://github.com/PyDevices/.github/tree/main/assets/))**: Master source for shared CSS, JavaScript, and branding logos.
3. **Automated Site Generator ([`dotgithub/scripts/generate_sites.py`](https://github.com/PyDevices/.github/blob/main/scripts/generate_sites.py))**: Generates Above-the-Fold hero banners, head tags, grid cards, and syncs chrome assets across all repositories.

---

## 🛠️ Local Development & Site Generation

To regenerate the portal page or sync canonical assets across the organization, run:

```bash
python3 ../dotgithub/scripts/generate_sites.py
```

---

## 🚀 GitHub Pages Deployment

Pushing commits to the `main` branch automatically updates GitHub Pages at [https://PyDevices.github.io/](https://PyDevices.github.io/) directly from the repository root.
