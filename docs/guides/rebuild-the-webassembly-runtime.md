# Rebuild the WebAssembly runtime

The live demos on the landing pages run MicroPython compiled to WebAssembly.
The three files are in `vendor/micropython/`: `micropython.mjs`,
`micropython.wasm` and `micropython.wasm.provenance`.

The runtime is built from the `micropython-pydevices` repository, not here.
Build its `webassembly` port:

```bash
git clone https://github.com/PyDevices/micropython-pydevices
cd micropython-pydevices
python3 build_mp.py --port webassembly
```

The prerequisites, the other ports and where the build writes its files are in
the [build command reference](https://github.com/PyDevices/micropython-pydevices/blob/main/docs/reference/build-command.md).

Copy the resulting `micropython.mjs` and `micropython.wasm` over the ones in
`vendor/micropython/`. Then update `micropython.wasm.provenance` beside them: a
JSON file that records the binary's size and SHA-256, the patches applied and
the commit of every source that went in, so a reader can tell what a published
runtime was built from. The build's `pydevices-build.json` has the commits.
Check that `binary.sha256` in the provenance file equals
`sha256sum vendor/micropython/micropython.wasm`, then
[preview the site](../get-started/install.md) and open a page with a live demo
before you push.
