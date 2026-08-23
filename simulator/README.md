# PyDevices Simulator

Interactive browser-based Python device playground for LVGL, pdwidgets, pygraphics, and displaydev.

Live at <https://pydevices.github.io/simulator/>.

## Architecture

- **Editor**: Monaco Editor with Python syntax highlighting and LZ-String compressed URL hash sharing.
- **Runtimes**:
  - **MicroPython WebAssembly**: Pre-compiled binary (`/vendor/micropython/micropython.mjs`) containing built-in `displaydev`, `multimer`, `appdev`, `board_config`, `lvgl`, `pydevices-lvgl`, `display_driver`, `palettes`, `pdwidgets`, `pygraphics`, and `usdl2`.
  - **Pyodide (CPython WASM)**: Python 3.12+ in the browser with dynamic wheel loading for companion packages.
- **Display Emulation**: Direct HTML5 Canvas binding with configurable resolution and shape presets (round watches, rectangular displays, landscape panels).
- **Progressive Web App (PWA)**: Includes `manifest.json` and `sw.js` with Cross-Origin-Isolation (`COOP`/`COEP`/`CORP`) headers, enabling offline installation and execution on desktop and mobile browsers.
