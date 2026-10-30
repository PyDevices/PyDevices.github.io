# How the site is made and published

The site has three kinds of content, and the rule for each is different.

**Generated.** `data/repos_db.json` in the `.github` repository lists every
project with its tier, headline, description and four buttons. The generator
turns each entry into the head tags and hero of that project's landing page,
and all of them into the portal's cards. Keeping this in one file is what makes
the pages agree: a button label or a tier name is edited once. A full run also
writes the organization's ecosystem map into the `.github` profile README and,
when it is checked out, the `pydevices` repository's `docs/ecosystem.md`, so a
database change has effects outside this repository.

**Copied.** The shared stylesheet, scripts, logo and demo apps live in the
`.github` repository so that every page, here and in the `mip` and `gallery`
sites, loads one copy. The offline PyScript app lives in `pyscript-template`
and is mirrored here so it publishes from the same root. These copies have no
other source of truth, so editing them in place is lost at the next run.

**By hand.** Everything on a landing page below the hero, the `com/` page, the
404 page, `install.sh` and the preview server.

The generator is run by hand rather than by CI. The database changes rarely,
the generator checks it on every run, and a human looking at the diff is the
review. Run twice with nothing changed, it changes no file.

## The live demos

A hero can run a small MicroPython app in a canvas. The page loads
`assets/chrome/hero-runtime.js`, which starts the runtime in
`vendor/micropython/` and runs the app named in the database entry. The
runtime is one shared copy so that every page downloads it once. Its
provenance file says which patches and sources it was built from. The runtime has the
PyDevices stack frozen in, so a demo imports it with nothing to install.

## Publishing

Pushes to `main` publish the repository root at <https://pydevices.github.io/>.
There is no build step, so what is in the repository is what is served.
`.nojekyll` keeps GitHub Pages from running Jekyll over it.

The `mip` and `gallery` sites are published by their own repositories. The
[roadmap](../../ROADMAP.md) has the planned move to the PyDevices domain.
