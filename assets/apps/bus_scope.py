"""
PyDevices Bus Timing & Logic Scope (Hero Canvas App for displayif)
=================================================================
Digital logic analyzer visualizing high-speed SPI / 8080 / MIPI-DSI
hardware bus signals, clock pulses, frame throughput, and TE sync.
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


class BusScopeHero:
    def __init__(self, canvas_id="hero_canvas", size=240):
        self.canvas_id = canvas_id
        self.size = size
        self.w = size
        self.h = size

        bc = types.ModuleType("board_config")
        bc.display_drv = PSDisplay(canvas_id, width=size, height=size)
        sys.modules["board_config"] = bc
        self.drv = bc.display_drv

        self.offset = 0.0
        self.fps = 60.0
        self.mbps = 80.0
        self.frame_cnt = 0

        self.draw()
        self._tick_proxy = create_proxy(self._js_tick_cb) if window else None
        self._tick_interval = window.setInterval(self._tick_proxy, 30) if window else None

    def _js_tick_cb(self):
        self.tick()

    def tick(self):
        self.offset += 2.5
        self.frame_cnt += 1
        self.draw()

    def draw(self):
        if not hasattr(self.drv, "_buf_ctx") or not self.drv._buf_ctx:
            return
        ctx = self.drv._buf_ctx
        w, h = self.w, self.h

        # 1. Oscilloscope Dark Grid Background
        ctx.fillStyle = "#070A0E"
        ctx.fillRect(0, 0, w, h)

        # Oscilloscope Grid Lines
        ctx.strokeStyle = "rgba(30, 41, 59, 0.6)"
        ctx.lineWidth = 1
        for gx in range(20, w, 20):
            ctx.beginPath()
            ctx.moveTo(gx, 0)
            ctx.lineTo(gx, h)
            ctx.stroke()
        for gy in range(20, h, 20):
            ctx.beginPath()
            ctx.moveTo(0, gy)
            ctx.lineTo(w, gy)
            ctx.stroke()

        # 2. Header Bar
        ctx.fillStyle = "rgba(15, 23, 42, 0.9)"
        ctx.fillRect(0, 0, w, 28)
        ctx.strokeStyle = "#1E293B"
        ctx.lineWidth = 1
        ctx.beginPath()
        ctx.moveTo(0, 28)
        ctx.lineTo(w, 28)
        ctx.stroke()

        ctx.fillStyle = "#F54E00"
        ctx.font = "bold 9px system-ui, monospace"
        ctx.textAlign = "left"
        ctx.fillText("● BUS TIMING", 10, 18)

        ctx.fillStyle = "#38BDF8"
        ctx.font = "9px system-ui, monospace"
        ctx.textAlign = "right"
        ctx.fillText(f"{self.mbps:.0f}M | 60FPS", w - 10, 18)

        # 3. Waveform Channels (CS, SCK, MOSI, TE/VSYNC)
        channels = [
            ("CS", "#EF4444", 45, 14),      # Red
            ("SCK", "#38BDF8", 85, 14),     # Blue
            ("MOSI", "#10B981", 125, 14),   # Emerald
            ("TE", "#F59E0B", 165, 14),     # Amber
        ]

        t = self.offset

        for name, color, base_y, amp in channels:
            # Label
            ctx.fillStyle = color
            ctx.font = "bold 9px system-ui, monospace"
            ctx.textAlign = "left"
            ctx.fillText(name, 10, base_y + amp / 2 + 3)

            # Trace Signal
            ctx.beginPath()
            ctx.strokeStyle = color
            ctx.lineWidth = 1.5

            plot_x_start = 42
            for x in range(plot_x_start, w - 8):
                ph = (x + t)
                if name == "CS":
                    # Periodic active-low chip select burst
                    val = 0 if (ph % 160 < 120) else 1
                elif name == "SCK":
                    # High speed clock pulse
                    val = 1 if (int(ph / 4) % 2 == 0) else 0
                elif name == "MOSI":
                    # Data packet burst
                    val = 1 if (int(ph / 8 + math.sin(ph * 0.05) * 2) % 2 == 0) else 0
                else:  # TE / VSYNC
                    # VSync pulse once every 200px
                    val = 1 if (ph % 220 < 18) else 0

                y = base_y + (0 if val == 1 else amp)
                if x == plot_x_start:
                    ctx.moveTo(x, y)
                else:
                    ctx.lineTo(x, y)

            ctx.stroke()

        # 4. Trigger Cursor
        trig_x = 130
        ctx.beginPath()
        ctx.setLineDash([3, 3])
        ctx.moveTo(trig_x, 28)
        ctx.lineTo(trig_x, 195)
        ctx.strokeStyle = "rgba(255, 255, 255, 0.4)"
        ctx.stroke()
        ctx.setLineDash([])

        # 5. Bottom Status Strip
        ctx.fillStyle = "rgba(15, 23, 42, 0.9)"
        ctx.fillRect(0, 198, w, 42)
        ctx.strokeStyle = "#1E293B"
        ctx.lineWidth = 1
        ctx.beginPath()
        ctx.moveTo(0, 198)
        ctx.lineTo(w, 198)
        ctx.stroke()

        ctx.fillStyle = "#94A3B8"
        ctx.font = "9px system-ui, monospace"
        ctx.textAlign = "left"
        ctx.fillText("BUS: QSPI / 8080 (DMA ACTIVE)", 10, 214)
        ctx.fillText(f"FRAME_TX: #{self.frame_cnt:05d}  DROPPED: 0", 10, 228)

        if hasattr(self.drv, "show"):
            self.drv.show()


_bus_scope_app = None


def main(canvas_id="hero_canvas"):
    global _bus_scope_app
    print(f"Initializing PyDevices Bus Scope on canvas '{canvas_id}'...")
    _bus_scope_app = BusScopeHero(canvas_id, size=240)
    print("PyDevices Bus Scope running successfully!")
