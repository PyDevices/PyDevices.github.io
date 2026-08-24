"""
PyDevices Bus Timing & Logic Scope (Hero Canvas App for displayif)
=================================================================
Digital logic analyzer visualizing high-speed SPI / 8080 / MIPI-DSI
hardware bus signals, clock pulses, frame throughput, and TE sync.
"""

import sys
import time
import math
from random import random

import board_config
import appdev
import pygraphics


def _color(value):
    value = value.lstrip("#")
    r, g, b = int(value[:2], 16), int(value[2:4], 16), int(value[4:], 16)
    return (r & 0xF8) << 8 | (g & 0xFC) << 3 | b >> 3


def _text(display, value, x, y, color, align="left"):
    value = str(value)
    if align == "right": x -= len(value) * 8
    pygraphics.text8(display, value, int(x), int(y) - 8, _color(color))


class BusScopeHero:
    def __init__(self, canvas_id="hero_canvas", size=240):
        self.canvas_id = canvas_id
        self.size = size
        self.w = size
        self.h = size

        import os
        os.environ.setdefault('PYDEVICES_WIDTH', str(size))
        os.environ.setdefault('PYDEVICES_HEIGHT', str(size))
        self.drv = board_config.display_drv
        self.app = appdev.App(board_config)

        self.offset = 0.0
        self.fps = 60.0
        self.mbps = 80.0
        self.frame_cnt = 0

        self.draw()
        self._tick_subscription = self.app.every(30, self._timer_tick)

    def _timer_tick(self, _timer):
        self.tick()

    def tick(self):
        self.offset += 2.5
        self.frame_cnt += 1
        self.draw()

    def draw(self):
        display = self.drv
        w, h = self.w, self.h

        # 1. Oscilloscope Dark Grid Background
        display.fill(_color("#070A0E"))

        # Oscilloscope Grid Lines
        for gx in range(20, w, 20):
            pygraphics.vline(display, gx, 0, h, _color("#172033"))
        for gy in range(20, h, 20):
            pygraphics.hline(display, 0, gy, w, _color("#172033"))

        # 2. Header Bar
        display.fill_rect(0, 0, w, 28, _color("#0F172A"))
        pygraphics.hline(display, 0, 28, w, _color("#1E293B"))
        _text(display, "BUS TIMING", 10, 18, "#F54E00")
        _text(display, f"{self.mbps:.0f}M | 60FPS", w - 10, 18, "#38BDF8", "right")

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
            _text(display, name, 10, base_y + amp / 2 + 3, color)

            plot_x_start = 42
            previous_y = base_y + amp
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
                if x > plot_x_start:
                    pygraphics.line(display, x - 1, previous_y, x, y, _color(color))
                previous_y = y

        # 4. Trigger Cursor
        trig_x = 130
        for y in range(28, 195, 6):
            pygraphics.vline(display, trig_x, y, 3, _color("#64748B"))

        # 5. Bottom Status Strip
        display.fill_rect(0, 198, w, 42, _color("#0F172A"))
        pygraphics.hline(display, 0, 198, w, _color("#1E293B"))
        _text(display, "BUS: QSPI / 8080 (DMA ACTIVE)", 10, 214, "#94A3B8")
        _text(display, f"FRAME_TX: #{self.frame_cnt:05d}  DROPPED: 0", 10, 228, "#94A3B8")

        if hasattr(self.drv, "show"):
            self.drv.show()


_bus_scope_app = None


def main(canvas_id="hero_canvas"):
    global _bus_scope_app
    print(f"Initializing PyDevices Bus Scope on canvas '{canvas_id}'...")
    _bus_scope_app = BusScopeHero(canvas_id, size=240)
    print("PyDevices Bus Scope running successfully!")
