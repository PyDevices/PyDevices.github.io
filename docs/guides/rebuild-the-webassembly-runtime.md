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

The watch on the front page is a second runtime, in `vendor/allapps/`: every
app of the [apps repository](https://github.com/PyDevices/apps) frozen in, so
the page fetches nothing once it has loaded. It boots Watch as its home
screen; the same build boots Home anywhere else.

Build it with omnipython-builds'
[all-apps page script](https://github.com/PyDevices/omnipython-builds/blob/main/docs/guides/build-the-all-apps-page.md),
or take the `allapps-page` artifact of its "All-apps browser page" workflow,
and copy four of its files into `vendor/allapps/`: `micropython.mjs`,
`micropython.wasm`, `micropython.wasm.provenance` and `allapps.json`, which
says which apps commit went in. The page's own `index.html` stays out.

