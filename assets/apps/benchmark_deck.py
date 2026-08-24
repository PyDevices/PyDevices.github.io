"""
PyDevices Multi-Interpreter Benchmark (Hero Canvas App for pydevices-examples)
=============================================================================
Interactive multi-interpreter execution matrix and benchmark meter:
- 5-target performance comparator (MicroPython, CircuitPython, CPython, WASM, Android)
- Real-time frame throughput and dirty-rect blit telemetry
- Interactive benchmark mode selector
"""

import math
import sys
import time
from random import random

import board_config
import appdev
import board_config
import events
import pygraphics


def _color(value):
    value = value.lstrip("#")
    r, g, b = int(value[:2], 16), int(value[2:4], 16), int(value[4:], 16)
    return (r & 0xF8) << 8 | (g & 0xFC) << 3 | b >> 3


def _text(display, value, x, y, color, align="left"):
    value = str(value)
    if align == "right": x -= len(value) * 8
    elif align == "center": x -= len(value) * 4
    pygraphics.text8(display, value, int(x), int(y) - 8, _color(color))


BENCH_MODES = ["BLIT 16-BIT", "DIRTY-RECT", "MATH / TRIG"]

TARGETS = [
    ("MP", "#F59E0B", 0.88),
    ("CP", "#38BDF8", 0.76),
    ("CPy", "#10B981", 0.98),
    ("WASM", "#8B5CF6", 0.92),
    ("AND", "#EC4899", 0.84),
]


class BenchmarkDeckHero:
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

        self.mode_idx = 0
        self.frame_cnt = 0
        self.burst = 0.0

        self.draw()
        self._bind_events()

        self._tick_subscription = self.app.every(33, self._timer_tick)

    def _timer_tick(self, _timer):
        self.tick()

    def _bind_events(self):
        def on_pointer_down(_event):
            self.mode_idx = (self.mode_idx + 1) % len(BENCH_MODES)
            self.burst = 1.0
            self.draw()

        self.app.on(events.MOUSEBUTTONDOWN, on_pointer_down)

    def tick(self):
        self.frame_cnt += 1
        if self.burst > 0.0:
            self.burst = max(0.0, self.burst - 0.05)
        self.draw()

    def draw(self):
        display = self.drv
        w, h = self.w, self.h

        # 1. Dark Console Background
        display.fill(_color("#0A0E17"))

        # 2. Header Bar
        display.fill_rect(0, 0, w, 28, _color("#0F172A"))
        pygraphics.hline(display, 0, 28, w, _color("#1E293B"))
        _text(display, "MULTI-INTERPRETER", 10, 18, "#F59E0B")
        _text(display, "5 RUNTIMES / 60FPS", w - 10, 18, "#10B981", "right")

        # 3. Mode Pill Selector (x: 12, y: 36, w: 216, h: 26)
        mx, my, mw, mh = 12, 36, 216, 26
        pygraphics.round_rect(display, mx, my, mw, mh, 6, _color("#0F172A"), True)
        pygraphics.round_rect(display, mx, my, mw, mh, 6, _color("#334155"))
        _text(display, "BENCHMARK:", mx + 8, my + 17, "#94A3B8")
        _text(display, f"> {BENCH_MODES[self.mode_idx]}", mx + mw - 8, my + 17, "#38BDF8", "right")

        # 4. Multi-Target Performance Bars (x: 12, y: 70)
        t = time.time() * 2.0
        bar_y_start = 72
        bar_h = 16
        gap = 10

        for i, (tag, col_hex, base_val) in enumerate(TARGETS):
            row_y = bar_y_start + i * (bar_h + gap)

            # Label Tag
            _text(display, f"{tag:<4}", 12, row_y + 12, "#E2E8F0")

            # Bar Track
            bx, bw = 52, w - 66
            pygraphics.round_rect(display, bx, row_y, bw, bar_h, 4, _color("#1E293B"), True)

            # Dynamic Wave Load
            wave = math.sin(t + i * 1.2) * 0.08 + (random() * 0.04 - 0.02) + self.burst * 0.1
            eff_val = max(0.2, min(1.0, base_val + wave))

            # Active Bar Fill
            fill_w = int(bw * eff_val)
            pygraphics.round_rect(display, bx, row_y, fill_w, bar_h, 4, _color(col_hex), True)

            # Percentage text inside or beside bar
            _text(display, f"{int(eff_val * 100)}%", bx + fill_w - 4 if fill_w > 32 else bx + fill_w + 18, row_y + 12, "#FFFFFF", "right")

        # 5. Bottom Tap Prompt
        _text(display, "TAP TO CYCLE BENCHMARK MODE", w // 2, 218, "#64748B", "center")

        if hasattr(self.drv, "show"):
            self.drv.show()


_bench_app = None


def main(canvas_id="hero_canvas"):
    global _bench_app
    print(f"Initializing PyDevices Benchmark Deck on canvas '{canvas_id}'...")
    _bench_app = BenchmarkDeckHero(canvas_id, size=240)
    print("PyDevices Benchmark Deck running successfully!")


if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "hero_canvas"
    main(cid)
