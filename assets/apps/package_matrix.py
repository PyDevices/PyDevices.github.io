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
import types

try:
    import js
    from js import document, window
    from pyodide.ffi import create_proxy
except ImportError:
    js = None
    document = None
    window = None
    create_proxy = lambda fn: fn

from displaydev.psdisplay import PSDisplay


PACKAGES = [
    ("pydevices", 0x38BDF8, ["board_config", "displaydev"]),
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

        if "board_config" not in sys.modules:
            bc = types.ModuleType("board_config")
            bc.display_drv = PSDisplay(canvas_id, width=size, height=size)
            sys.modules["board_config"] = bc
            self.drv = bc.display_drv
        else:
            self.drv = sys.modules["board_config"].display_drv

        self.angle = 0.0
        self.selected_idx = 0
        self.install_pct = 100
        self.is_installing = False

        self.draw()
        self._bind_events()

        self._tick_proxy = create_proxy(self._js_tick_cb) if window else None
        self._tick_interval = window.setInterval(self._tick_proxy, 33) if window else None

    def _js_tick_cb(self):
        self.tick()

    def _bind_events(self):
        if not document:
            return
        canvas = document.getElementById(self.canvas_id)
        if not canvas:
            return

        def on_pointer_down(event):
            event.preventDefault()
            self.selected_idx = (self.selected_idx + 1) % len(PACKAGES)
            self.install_pct = 0
            self.is_installing = True
            self.draw()

        self._p_down = create_proxy(on_pointer_down)
        canvas.addEventListener("pointerdown", self._p_down)

    def tick(self):
        self.angle = (self.angle + 0.02) % (math.pi * 2)
        if self.is_installing:
            self.install_pct += 4
            if self.install_pct >= 100:
                self.install_pct = 100
                self.is_installing = False
        self.draw()

    def draw(self):
        if not hasattr(self.drv, "_buf_ctx") or not self.drv._buf_ctx:
            return
        ctx = self.drv._buf_ctx
        w, h, cx, cy = self.w, self.h, self.cx, self.cy

        # 1. Dark Circular Housing
        ctx.fillStyle = "#0A0E17"
        ctx.fillRect(0, 0, w, h)

        # 2. Outer Ring
        ctx.beginPath()
        ctx.arc(cx, cy, 106, 0, math.pi * 2)
        ctx.fillStyle = "#111827"
        ctx.fill()
        ctx.strokeStyle = "#1F2937"
        ctx.lineWidth = 2
        ctx.stroke()

        # Orbital Path
        orbit_r = 74
        ctx.beginPath()
        ctx.arc(cx, cy, orbit_r, 0, math.pi * 2)
        ctx.strokeStyle = "rgba(56, 189, 248, 0.2)"
        ctx.lineWidth = 1
        ctx.setLineDash([4, 4])
        ctx.stroke()
        ctx.setLineDash([])

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
            ctx.beginPath()
            ctx.moveTo(cx, cy)
            ctx.lineTo(nx, ny)
            ctx.strokeStyle = f"rgba({r}, {g}, {b}, 0.3)" if is_sel else "rgba(255, 255, 255, 0.08)"
            ctx.lineWidth = 1.5 if is_sel else 1
            ctx.stroke()

            # Node Glow
            if is_sel:
                ctx.beginPath()
                ctx.arc(nx, ny, 16, 0, math.pi * 2)
                ctx.fillStyle = f"rgba({r}, {g}, {b}, 0.35)"
                ctx.fill()

            # Node Bead
            ctx.beginPath()
            ctx.arc(nx, ny, 8 if not is_sel else 10, 0, math.pi * 2)
            ctx.fillStyle = f"rgb({r}, {g}, {b})"
            ctx.fill()
            ctx.strokeStyle = "#FFFFFF" if is_sel else "rgba(255, 255, 255, 0.5)"
            ctx.lineWidth = 1.5
            ctx.stroke()

        # 4. Center Package Info Hub
        hub_r = 46
        ctx.beginPath()
        ctx.arc(cx, cy, hub_r, 0, math.pi * 2)
        ctx.fillStyle = "#0B1120"
        ctx.fill()
        ctx.strokeStyle = "#38BDF8"
        ctx.lineWidth = 1.5
        ctx.stroke()

        cur_name, cur_col, cur_deps = PACKAGES[self.selected_idx]
        ctx.fillStyle = "#38BDF8"
        ctx.font = "bold 8px system-ui, sans-serif"
        ctx.textAlign = "center"
        ctx.fillText("MIP INDEX SOT", cx, cy - 20)

        ctx.fillStyle = "#F8FAFC"
        ctx.font = "bold 11px system-ui, monospace"
        ctx.fillText(cur_name, cx, cy - 4)

        # Installation / Checksum Status
        if self.is_installing:
            ctx.fillStyle = "#F59E0B"
            ctx.font = "bold 8px monospace"
            ctx.fillText(f"FETCH {self.install_pct}%", cx, cy + 12)
        else:
            ctx.fillStyle = "#10B981"
            ctx.font = "bold 8px monospace"
            ctx.fillText(".mpy [VERIFIED]", cx, cy + 12)

        ctx.fillStyle = "#94A3B8"
        ctx.font = "7px system-ui, sans-serif"
        ctx.fillText("TAP TO CYCLE", cx, cy + 24)

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
