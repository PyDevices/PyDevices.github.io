"""Application entry point for the PyDevices PyScript template.

Interactive touch/paint demo built on the PyDevices Board Contract
(``board_config`` and ``appdev.App``). Edit this file to make the app yours.
"""

import board_config
import appdev
from pyscript import document

display_drv = board_config.display_drv
app = appdev.App(board_config)

colors = [0xFFFF, 0xF800, 0x07E0, 0x001F, 0x07FF, 0xF81F, 0xFFE0, 0x0000]
block_size = display_drv.width // len(colors)
selected = 0


def draw_palette():
    for i, color in enumerate(colors):
        x = i * block_size
        display_drv.fill_rect(x, 0, block_size, 30, color)
    display_drv.show()


draw_palette()
document.querySelector("#status").textContent = (
    "Running displaydev in Pyodide. Click the canvas to paint."
)


def on_touch(event):
    global selected
    x, y = event.pos
    if y < 30:
        selected = min(len(colors) - 1, x // block_size)
    else:
        display_drv.fill_rect(x - 3, y - 3, 6, 6, colors[selected])
        display_drv.show()


app.on(app.events.MOUSEBUTTONDOWN, on_touch)
app.on(app.events.MOUSEMOTION, on_touch)
app.run()
