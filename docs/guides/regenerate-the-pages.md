# Regenerate the pages

The head tags and hero of every landing page, and the portal's project cards,
are written by `scripts/generate_sites.py` in the `.github` repository from
`data/repos_db.json`. Run it after you change the database, the shared assets
or the PyScript template. It is a manual step on purpose: the database changes
rarely.

## Set up the folders

The generator finds its siblings by folder name, one level above itself. Put
the `.github` repository in a folder called `dotgithub`:

```bash
git clone https://github.com/PyDevices/.github dotgithub
git clone https://github.com/PyDevices/PyDevices.github.io
```

## Rewrite one page

To rewrite a single repository's page and leave everything else alone, name it
with `--only`. This needs only the two clones above:

```bash
python3 dotgithub/scripts/generate_sites.py --only pygraphics
```

```
=== Pure Harmonized PyDevices Site Generator (.github) ===
[OK] Database valid: 25 repos across 6 tiers
[OK] Generated & Updated pygraphics (PyDevices.github.io/pygraphics/index.html)
=== Complete! Processed pygraphics only ===
```

Run it twice and the second run changes no file. `--only` also skips the
shared assets and the ecosystem maps. A name that isn't in the database stops
the run with an error.

## Rewrite everything

Without `--only` the generator also copies the shared assets, refreshes the
PyScript template copy, and writes the ecosystem maps. Before it starts it
checks the database, and the check needs the repositories whose pages are
published from their own `.site` folder: clone `mip` and `gallery` beside the
others, with their `.site` folders present.

```bash
python3 dotgithub/scripts/generate_sites.py
```

A malformed database entry stops the run with a list of what is wrong, before
any file is written. A landing page must have exactly four buttons, a tier that
exists in the database, and, if it names a demo app, that app under the
`.github` repository's `assets/apps/`.

Only the regions between the `PYDEVICES-...: START` and `END` comments are
rewritten. Hand-written HTML outside them is untouched. See
[what is in the repository](../reference/contents.md) for which files this
touches.

## Refresh the pyscript-template copy

`pyscript-template/pwa/` is a copy of the app at the root of the
`pyscript-template` repository. It is copied whole, so a file the template
drops leaves the site too. The copy needs the template's vendored PyScript,
which is not committed there, so fetch it first:

```bash
git clone https://github.com/PyDevices/pyscript-template
(cd pyscript-template && scripts/vendor_pyscript.sh)
python3 dotgithub/scripts/generate_sites.py
```

If `pyscript-template/vendor/pyscript/core.js` is missing, the generator prints
that it is leaving the copy unchanged and goes on.
