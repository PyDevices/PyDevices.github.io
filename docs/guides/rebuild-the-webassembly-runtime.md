# Rebuild the WebAssembly runtime

The live demos on the landing pages run MicroPython compiled to WebAssembly.
The three files are in `vendor/micropython/`: `micropython.mjs`,
`micropython.wasm` and `micropython.wasm.provenance`.

The runtime is built from the `omnipython-builds` repository, not here.
Build its `webassembly` port:

```bash
git clone https://github.com/PyDevices/omnipython-builds
cd omnipython-builds
python3 build.py --port webassembly
```

The prerequisites, the other ports and where the build writes its files are in
the [build command reference](https://github.com/PyDevices/omnipython-builds/blob/main/docs/reference/build-command.md).

Copy the resulting `micropython.mjs` and `micropython.wasm` over the ones in
`vendor/micropython/`. Then update `micropython.wasm.provenance` beside them: a
JSON file that records the binary's size and SHA-256, the patches applied and
the commit of every source that went in, so a reader can tell what a published
runtime was built from. The build's `pydevices-build.json` has the commits.
Check that `binary.sha256` in the provenance file equals
`sha256sum vendor/micropython/micropython.wasm`, then
[preview the site](../get-started/install.md) and open a page with a live demo
before you push.

## The all-apps runtime

The watch on the front page, and the hero on the apps page, boot a second
runtime: every app of the [apps repository](https://github.com/PyDevices/apps)
frozen in, the same build that boots Home and Watch everywhere else. It
isn't kept here. The pages load it from
<https://apps.omnipython.org/>, where omnipython-builds publishes it with
each apps release, so there is nothing to rebuild in this repository. How
that build is made and published is in its
[guide](https://github.com/PyDevices/omnipython-builds/blob/main/docs/guides/build-the-all-apps-page.md).
