# PyDevices.github.io — Organization Portal

Welcome to the **PyDevices Organization Portal** source repository. This site serves as the unified landing hub for the entire [PyDevices](https://pydevices.github.io/) ecosystem — bridging hardware abstraction drivers, 2D graphics engines, widget toolkits, native LVGL C extensions, and target application hosts across MicroPython, CircuitPython, CPython, PyScript, and Android.

---

## 🏛️ Ecosystem Overview & Architecture

All 16 repositories in the PyDevices organization follow a **100% uniform `.site/` filesystem layout**:

- **`.site/index.html`**: Clean landing page source file.
- **`.site/img/logo.svg`**: PyDevices brand mark.
- **`.site/vendor/pydevices-chrome/`**: Synced shared styling (`site.css`), theme toggle (`theme-toggle.js`), header/footer injector (`site-chrome.js`), and tree navigation (`tree-nav.js`).

---

## ⚡ Centralized Generator & Single Source of Truth

The entire PyDevices web presence is managed centrally from the **[`.github` (*dotgithub*)](https://github.com/PyDevices/.github)** repository:

1. **Database ([`repos_db.json`](file:///home/brad/gh/pydevices/dotgithub/data/repos_db.json))**: Single Source of Truth storing eyebrows, headlines, descriptions, tier colors, and 4-button CTA layouts for all repositories.
2. **Canonical Assets Vault ([`dotgithub/assets/`](file:///home/brad/gh/pydevices/dotgithub/assets/))**: Master source for shared CSS, JavaScript, and branding logos.
3. **Automated Site Generator ([`dotgithub/scripts/generate_sites.py`](file:///home/brad/gh/pydevices/dotgithub/scripts/generate_sites.py))**: Generates Above-the-Fold hero banners, head tags, and syncs chrome assets across all repositories in < 0.2 seconds.

---

## 🛠️ Local Development & Site Generation

To regenerate the portal page or sync canonical assets across the organization, run:

```bash
python3 ../dotgithub/scripts/generate_sites.py
```

---

## 🚀 Automated Deployment

Pushing changes to the `main` branch automatically triggers the GitHub Actions workflow ([`.github/workflows/deploy.yml`](.github/workflows/deploy.yml)):

1. Checks out `PyDevices.github.io` and `PyDevices/.github`.
2. Executes `python3 dotgithub/scripts/generate_sites.py`.
3. Packages and deploys `.site/` directly to **GitHub Pages** at [https://PyDevices.github.io/](https://PyDevices.github.io/).
