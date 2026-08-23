"""
PyDevices MIP Package Resolver (Hero Canvas App for mip)
========================================================
Interactive package index & dependency graph visualizer:
- Orbital network nodes for ecosystem packages
- Animated dependency resolver beam and .mpy checksum verifier
- Interactive package selection and simulated mip.install() progress
"""

import math
import sys
import time

import appdev
import events
from displaydev.wasmdisplay import WasmDisplay
import pygraphics


def _rgb565(red, green, blue):
    return (int(red) & 0xF8) << 8 | (int(green) & 0xFC) << 3 | int(blue) >> 3


def _color(value):
    return _rgb565(value >> 16, value >> 8, value)


def _text(display, value, x, y, color):
    value = str(value)
    pygraphics.text8(display, value, int(x) - len(value) * 4, int(y) - 8, color)


PACKAGES = [
    ("pydevices", 0x38BDF8, ["appdev", "displaydev"]),
    ("pygraphics", 0x34D399, ["framebuf", "fonts"]),
    ("pdwidgets", 0xF59E0B, ["widgets", "theming"]),
    ("palettes", 0xEC4899, ["color_math", "swatches"]),
    ("displayif", 0x8B5CF6, ["spi", "i2c", "parallel"]),
    ("lvgl", 0x10B981, ["bindings", "widgets"]),
]


class PackageMatrixHero:
    def __init__(self, canvas_id="hero_canvas", size=240):
        self.canvas_id = canvas_id
        self.size = size
        self.w = size
        self.h = size
        self.cx = size // 2
        self.cy = size // 2

        self.drv = WasmDisplay(width=size, height=size, canvas_id=canvas_id)
        self.app = appdev.App(displays=(self.drv,), host_read=self.drv.get_events)

        self.angle = 0.0
        self.selected_idx = 0
        self.install_pct = 100
        self.is_installing = False

        self.draw()
        self._bind_events()

        self._tick_subscription = self.app.every(33, self._timer_tick)

    def _timer_tick(self, _timer):
        self.tick()

    def _bind_events(self):
        def on_pointer_down(_event):
            self.selected_idx = (self.selected_idx + 1) % len(PACKAGES)
            self.install_pct = 0
            self.is_installing = True
            self.draw()

        self.app.on(events.MOUSEBUTTONDOWN, on_pointer_down)

    def tick(self):
        self.angle = (self.angle + 0.02) % (math.pi * 2)
        if self.is_installing:
            self.install_pct += 4
            if self.install_pct >= 100:
                self.install_pct = 100
                self.is_installing = False
        self.draw()

    def draw(self):
        display = self.drv
        w, h, cx, cy = self.w, self.h, self.cx, self.cy

        # 1. Dark Circular Housing
        display.fill(_color(0x0A0E17))

        # 2. Outer Ring
        pygraphics.circle(display, cx, cy, 106, _color(0x111827), True)
        pygraphics.circle(display, cx, cy, 106, _color(0x1F2937))

        # Orbital Path
        orbit_r = 74
        pygraphics.circle(display, cx, cy, orbit_r, _color(0x164E63))

        # 3. Orbital Package Nodes
        num_pkgs = len(PACKAGES)
        for i, (name, col_int, deps) in enumerate(PACKAGES):
            node_ang = self.angle + i * (math.pi * 2 / num_pkgs)
            nx = cx + math.cos(node_ang) * orbit_r
            ny = cy + math.sin(node_ang) * orbit_r

            is_sel = (i == self.selected_idx)
            r = (col_int >> 16) & 0xFF
            g = (col_int >> 8) & 0xFF
            b = col_int & 0xFF

            # Dependency Connector Line to Center Hub
            line_color = _rgb565(r // 3, g // 3, b // 3) if is_sel else _color(0x202733)
            pygraphics.line(display, cx, cy, int(nx), int(ny), line_color)

            # Node Glow
            if is_sel:
                pygraphics.circle(display, int(nx), int(ny), 16, _rgb565(r // 3, g // 3, b // 3), True)

            # Node Bead
            radius = 10 if is_sel else 8
            pygraphics.circle(display, int(nx), int(ny), radius, _rgb565(r, g, b), True)
            pygraphics.circle(display, int(nx), int(ny), radius, _color(0xFFFFFF if is_sel else 0x7C8594))

        # 4. Center Package Info Hub
        hub_r = 46
        pygraphics.circle(display, cx, cy, hub_r, _color(0x0B1120), True)
        pygraphics.circle(display, cx, cy, hub_r, _color(0x38BDF8))

        cur_name, cur_col, cur_deps = PACKAGES[self.selected_idx]
        _text(display, "MIP INDEX SOT", cx, cy - 20, _color(0x38BDF8))
        _text(display, cur_name, cx, cy - 4, _color(0xF8FAFC))

        # Installation / Checksum Status
        if self.is_installing:
            _text(display, f"FETCH {self.install_pct}%", cx, cy + 12, _color(0xF59E0B))
        else:
            _text(display, ".mpy [VERIFIED]", cx, cy + 12, _color(0x10B981))
        _text(display, "TAP TO CYCLE", cx, cy + 24, _color(0x94A3B8))

        if hasattr(self.drv, "show"):
            self.drv.show()


_matrix_app = None


def main(canvas_id="hero_canvas"):
    global _matrix_app
    print(f"Initializing PyDevices MIP Matrix on canvas '{canvas_id}'...")
    _matrix_app = PackageMatrixHero(canvas_id, size=240)
    print("PyDevices MIP Matrix running successfully!")


if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "hero_canvas"
    main(cid)
