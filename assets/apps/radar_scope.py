"""
PyDevices Vector Radar & Sonar Scope (Hero Canvas App for pyscript-template)
===========================================================================
High-performance pure-Python 2D vector radar with 360-degree sweeping beam,
decaying phosphor persistence, anti-aliased range rings, and moving target blips.
"""

import sys
import types
import time
import math
from random import random

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


class RadarScopeHero:
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

        self.sweep_ang = 0.0
        self.targets = [
            {"dist": 65, "ang": 45, "id": "TGT-01", "active": True},
            {"dist": 88, "ang": 190, "id": "TGT-02", "active": True},
            {"dist": 40, "ang": 310, "id": "TGT-03", "active": True},
        ]

        self.draw()
        self._tick_proxy = create_proxy(self._js_tick_cb) if window else None
        self._tick_interval = window.setInterval(self._tick_proxy, 30) if window else None

    def _js_tick_cb(self):
        self.tick()

    def tick(self):
        self.sweep_ang = (self.sweep_ang + 2.5) % 360.0
        self.draw()

    def draw(self):
        if not hasattr(self.drv, "_buf_ctx") or not self.drv._buf_ctx:
            return
        ctx = self.drv._buf_ctx
        w, h, cx, cy = self.w, self.h, self.cx, self.cy

        # 1. Dark Phosphor Background
        ctx.fillStyle = "#060A08"
        ctx.fillRect(0, 0, w, h)

        # 2. Radar Grid & Range Rings
        max_r = 108
        ctx.strokeStyle = "rgba(16, 185, 129, 0.25)"
        ctx.lineWidth = 1

        for r_step in (35, 70, 105):
            ctx.beginPath()
            ctx.arc(cx, cy, r_step, 0, math.pi * 2)
            ctx.stroke()

        # Crosshairs
        ctx.beginPath()
        ctx.moveTo(cx - max_r, cy)
        ctx.lineTo(cx + max_r, cy)
        ctx.moveTo(cx, cy - max_r)
        ctx.lineTo(cx, cy + max_r)
        ctx.stroke()

        # 3. Rotating Phosphor Sweep Cone
        rad_sweep = math.radians(self.sweep_ang)
        cone_span = math.radians(45)

        sweep_grad = ctx.createRadialGradient(cx, cy, 5, cx, cy, max_r)
        sweep_grad.addColorStop(0.0, "rgba(16, 185, 129, 0.4)")
        sweep_grad.addColorStop(1.0, "rgba(5, 150, 105, 0.05)")

        ctx.save()
        ctx.beginPath()
        ctx.moveTo(cx, cy)
        ctx.arc(cx, cy, max_r, rad_sweep - cone_span, rad_sweep)
        ctx.closePath()
        ctx.fillStyle = sweep_grad
        ctx.fill()

        # Leading Edge Line
        ctx.beginPath()
        ctx.moveTo(cx, cy)
        ctx.lineTo(cx + math.cos(rad_sweep) * max_r, cy + math.sin(rad_sweep) * max_r)
        ctx.strokeStyle = "#34D399"
        ctx.lineWidth = 2
        ctx.stroke()
        ctx.restore()

        # 4. Target Blips
        for tgt in self.targets:
            tgt_rad = math.radians(tgt["ang"])
            tx = cx + math.cos(tgt_rad) * tgt["dist"]
            ty = cy + math.sin(tgt_rad) * tgt["dist"]

            # Calculate angular difference to sweep beam
            diff = (self.sweep_ang - tgt["ang"]) % 360.0
            if diff < 60:
                # Target is lit up by recent sweep
                alpha = 1.0 - (diff / 60.0)
                ctx.beginPath()
                ctx.arc(tx, ty, 4, 0, math.pi * 2)
                ctx.fillStyle = f"rgba(52, 211, 153, {alpha})"
                ctx.fill()
                ctx.strokeStyle = f"rgba(255, 255, 255, {alpha})"
                ctx.lineWidth = 1
                ctx.stroke()

                # Target ID Tag
                ctx.fillStyle = f"rgba(52, 211, 153, {alpha})"
                ctx.font = "8px system-ui, monospace"
                ctx.textAlign = "left"
                ctx.fillText(tgt["id"], tx + 6, ty - 4)
            else:
                # Dim background ping
                ctx.beginPath()
                ctx.arc(tx, ty, 2, 0, math.pi * 2)
                ctx.fillStyle = "rgba(16, 185, 129, 0.3)"
                ctx.fill()

        # 5. Outer Bezel & Cardinal Degree Markings
        ctx.beginPath()
        ctx.arc(cx, cy, max_r + 4, 0, math.pi * 2)
        ctx.strokeStyle = "#059669"
        ctx.lineWidth = 2
        ctx.stroke()

        ctx.fillStyle = "#10B981"
        ctx.font = "bold 8px system-ui, monospace"
        ctx.textAlign = "center"
        ctx.fillText("000°", cx, cy - max_r - 6)
        ctx.fillText("090°", cx + max_r + 14, cy + 3)
        ctx.fillText("180°", cx, cy + max_r + 12)
        ctx.fillText("270°", cx - max_r - 14, cy + 3)

        # 6. Status Strip
        ctx.fillStyle = "#34D399"
        ctx.font = "9px system-ui, monospace"
        ctx.textAlign = "left"
        ctx.fillText(f"HDG: {int(self.sweep_ang):03d}° | SCAN 24 RPM", 12, 22)

        if hasattr(self.drv, "show"):
            self.drv.show()


_radar_app = None


def main(canvas_id="hero_canvas"):
    global _radar_app
    print(f"Initializing PyDevices Vector Radar on canvas '{canvas_id}'...")
    _radar_app = RadarScopeHero(canvas_id, size=240)
    print("PyDevices Vector Radar running successfully!")
