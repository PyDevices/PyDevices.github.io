"""
PyDevices Vector Radar & Sonar Scope (Hero Canvas App for pyscript-template)
===========================================================================
High-performance pure-Python 2D vector radar with 360-degree sweeping beam,
decaying phosphor persistence, anti-aliased range rings, and moving target blips.
"""

import time
import math
from random import random

from board_config import display_drv
import board_config
import appdev
import pygraphics

app = appdev.App(board_config)


def _color(value):
    value = value.lstrip("#")
    r, g, b = int(value[:2], 16), int(value[2:4], 16), int(value[4:], 16)
    return (r & 0xF8) << 8 | (g & 0xFC) << 3 | b >> 3


def _text(display, value, x, y, color, align="left"):
    value = str(value)
    if align == "center": x -= len(value) * 4
    pygraphics.text8(display, value, int(x), int(y) - 8, _color(color))


class RadarScopeHero:
    def __init__(self, size=240):
        self.size = size
        self.w = size
        self.h = size
        self.cx = size // 2
        self.cy = size // 2

        self.drv = display_drv

        self.sweep_ang = 0.0
        self.targets = [
            {"dist": 65, "ang": 45, "id": "TGT-01", "active": True},
            {"dist": 88, "ang": 190, "id": "TGT-02", "active": True},
            {"dist": 40, "ang": 310, "id": "TGT-03", "active": True},
        ]

        self.draw()
        self._tick_subscription = app.every(30, self._timer_tick)

    def _timer_tick(self, _timer):
        self.tick()

    def tick(self):
        self.sweep_ang = (self.sweep_ang + 2.5) % 360.0
        self.draw()

    def draw(self):
        display = self.drv
        w, h, cx, cy = self.w, self.h, self.cx, self.cy

        # 1. Dark Phosphor Background
        display.fill(_color("#060A08"))

        # 2. Radar Grid & Range Rings
        max_r = 108
        for r_step in (35, 70, 105):
            pygraphics.circle(display, cx, cy, r_step, _color("#0D4B3A"))

        # Crosshairs
        pygraphics.hline(display, cx - max_r, cy, max_r * 2, _color("#0D4B3A"))
        pygraphics.vline(display, cx, cy - max_r, max_r * 2, _color("#0D4B3A"))

        # 3. Rotating Phosphor Sweep Cone
        rad_sweep = math.radians(self.sweep_ang)
        for trailing in range(0, 46, 3):
            angle = rad_sweep - math.radians(trailing)
            color = _color("#0D5B42") if trailing < 15 else _color("#093326")
            pygraphics.line(display, cx, cy, int(cx + math.cos(angle) * max_r), int(cy + math.sin(angle) * max_r), color)

        # Leading Edge Line
        pygraphics.line(display, cx, cy, int(cx + math.cos(rad_sweep) * max_r), int(cy + math.sin(rad_sweep) * max_r), _color("#34D399"))

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
                pygraphics.circle(display, int(tx), int(ty), 4, _color("#34D399"), True)
                pygraphics.circle(display, int(tx), int(ty), 4, _color("#FFFFFF"))
                _text(display, tgt["id"], tx + 6, ty - 4, "#34D399")
            else:
                # Dim background ping
                pygraphics.circle(display, int(tx), int(ty), 2, _color("#0D5B42"), True)

        # 5. Outer Bezel & Cardinal Degree Markings
        pygraphics.circle(display, cx, cy, max_r + 4, _color("#059669"))
        _text(display, "000", cx, cy - max_r - 6, "#10B981", "center")
        _text(display, "090", cx + max_r + 14, cy + 3, "#10B981", "center")
        _text(display, "180", cx, cy + max_r + 12, "#10B981", "center")
        _text(display, "270", cx - max_r - 14, cy + 3, "#10B981", "center")

        # 6. Status Strip
        _text(display, f"HDG: {int(self.sweep_ang):03d} | SCAN 24 RPM", 12, 22, "#34D399")

        if hasattr(self.drv, "show"):
            self.drv.show()


_radar_app = RadarScopeHero(size=min(display_drv.width, display_drv.height))
