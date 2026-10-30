# Preview the site

The site is static files, so a preview is a web server pointed at the
repository root. `tools/serve_local.py` is one, and it needs only Python 3.

```bash
git clone https://github.com/PyDevices/PyDevices.github.io
cd PyDevices.github.io
python3 tools/serve_local.py --port 8000
```

Open <http://127.0.0.1:8000/>. Pages load their scripts and the runtime by
absolute paths such as `/vendor/micropython/micropython.mjs`, so serve the
repository root, not a subfolder. A plain `python3 -m http.server` also shows
the pages and runs the live demos; `serve_local.py` adds the `mip` and
`gallery` mounts below. It binds to `127.0.0.1`; pass `--bind 0.0.0.0` to reach
it from a phone on your network.

## See the mip index and the gallery too

The `mip` package index and the gallery are published from their own
repositories. Clone them beside this one and the server mounts them at their
real addresses:

```
parent-folder/
  PyDevices.github.io/
  mip/
  gallery/
```

`/mip/` and `/gallery/` then serve each repository's `.site` folder, and fall
back to its `origin/gh-pages` branch for files that aren't there. A request for
something neither has returns a 404.

Next: [regenerate the pages](../guides/regenerate-the-pages.md) after you
change the database.
