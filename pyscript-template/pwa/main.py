"""Application entry point for the PyDevices PyScript template."""

from board_config import display_drv
from pyscript import document


COLORS = (0xF800, 0x07E0, 0x001F, 0xFFE0)


def draw_demo():
    """Draw a small portability demo with the real ``displaydev`` API."""
    display_drv.fill(0x1082)
    margin = 24
    band_height = 72
    for index, color in enumerate(COLORS):
        display_drv.fill_rect(
            margin,
            margin + index * (band_height + 12),
            display_drv.width - margin * 2,
            band_height,
            color,
        )
    display_drv.show()
    document.querySelector("#status").textContent = (
        "Running displaydev in Pyodide. Click the canvas to focus input."
    )


draw_demo()
