# PyDevices Simulator

Interactive browser-based Python device playground for LVGL, pdwidgets, pygraphics, and displaydev.

Live at <https://pydevices.github.io/simulator/>.

## Architecture

- **Editor**: Monaco Editor with Python syntax highlighting and LZ-String compressed URL hash sharing.
- **Runtime**: Direct MicroPython WebAssembly (`/vendor/micropython/micropython.mjs`) containing built-in `displaydev`, `multimer`, `appdev`, `board_config`, `lvgl`, `pydevices-lvgl`, `display_driver`, `palettes`, `pdwidgets`, `pygraphics`, and `usdl2`.
- **REPL**: Starts before editor execution. **Run** compiles `/main.py` into the persistent `__main__` globals, so imports, objects, and assignments are immediately available for interactive introspection afterward. **Reset VM** creates a clean interpreter while retaining the editor draft and display resolution.
- **Display Emulation**: Direct HTML5 Canvas binding with configurable resolution and shape presets (round watches, rectangular displays, landscape panels).
- **Progressive Web App (PWA)**: Includes `manifest.json` and `sw.js` with Cross-Origin-Isolation (`COOP`/`COEP`/`CORP`) headers, enabling offline installation and execution on desktop and mobile browsers.
