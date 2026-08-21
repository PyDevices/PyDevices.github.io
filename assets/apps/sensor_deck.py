"""
PyDevices Sensor Deck & Widget Dashboard (Hero Canvas App for pdwidgets)
========================================================================
Interactive pure-Python widget dashboard featuring a rotary arc gauge,
scrolling sparkline telemetry graph, interactive toggle button, and slider.
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


class SensorDeckHero:
    def __init__(self, canvas_id="hero_canvas", size=240):
        self.canvas_id = canvas_id
        self.size = size
        self.w = size
        self.h = size

        if "board_config" not in sys.modules:
            bc = types.ModuleType("board_config")
            bc.display_drv = PSDisplay(canvas_id, width=size, height=size)
            sys.modules["board_config"] = bc
            self.drv = bc.display_drv
        else:
            self.drv = sys.modules["board_config"].display_drv

        # Widget States
        self.gauge_val = 68.0  # 0..100
        self.slider_val = 0.72  # 0.0..1.0
        self.toggle_active = True
        self.sparkline_history = [math.sin(i * 0.3) * 12 + 18 for i in range(40)]

        # Interaction
        self.is_dragging_slider = False

        self._bind_events()
        self.draw()

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
            rect = canvas.getBoundingClientRect()
            x = (event.clientX - rect.left) * (self.size / rect.width)
            y = (event.clientY - rect.top) * (self.size / rect.height)

            # Check Toggle Button Hit (x: 135..225, y: 16..54)
            if 135 <= x <= 225 and 16 <= y <= 54:
                self.toggle_active = not self.toggle_active
                self.draw()
                return

            # Check Slider Hit (x: 20..220, y: 190..230)
            if 20 <= x <= 220 and 190 <= y <= 230:
                self.is_dragging_slider = True
                self.slider_val = max(0.0, min(1.0, (x - 25) / 190.0))
                self.draw()

        def on_pointer_move(event):
            if not self.is_dragging_slider:
                return
            event.preventDefault()
            rect = canvas.getBoundingClientRect()
            x = (event.clientX - rect.left) * (self.size / rect.width)
            self.slider_val = max(0.0, min(1.0, (x - 25) / 190.0))
            self.draw()

        def on_pointer_up(event):
            self.is_dragging_slider = False

        self._pointer_down_proxy = create_proxy(on_pointer_down)
        self._pointer_move_proxy = create_proxy(on_pointer_move)
        self._pointer_up_proxy = create_proxy(on_pointer_up)

        canvas.addEventListener("pointerdown", self._pointer_down_proxy)
        window.addEventListener("pointermove", self._pointer_move_proxy)
        window.addEventListener("pointerup", self._pointer_up_proxy)

    def tick(self):
        # Update live sparkline
        t = time.time() * 3.0
        val = math.sin(t) * 10 + math.cos(t * 1.7) * 5 + (random() * 4 - 2) + 20
        self.sparkline_history.pop(0)
        self.sparkline_history.append(val)

        # Oscillate gauge smoothly
        self.gauge_val = 50.0 + math.sin(time.time() * 1.5) * 32.0 * self.slider_val
        self.draw()

    def draw(self):
        if not hasattr(self.drv, "_buf_ctx") or not self.drv._buf_ctx:
            return
        ctx = self.drv._buf_ctx
        w, h = self.w, self.h

        # 1. Dark Bezel Panel Background
        ctx.fillStyle = "#0A0D12"
        ctx.fillRect(0, 0, w, h)

        # Header Title
        ctx.fillStyle = "#64748B"
        ctx.font = "bold 9px system-ui, sans-serif"
        ctx.textAlign = "left"
        ctx.fillText("PDWIDGETS INSTRUMENT", 16, 18)

        # 2. Top-Left Arc Gauge Widget
        gx, gy, gr = 65, 68, 38
        # Background arc
        ctx.beginPath()
        ctx.arc(gx, gy, gr, math.pi * 0.75, math.pi * 2.25)
        ctx.strokeStyle = "#1E293B"
        ctx.lineWidth = 6
        ctx.lineCap = "round"
        ctx.stroke()

        # Active Value Arc
        arc_span = (self.gauge_val / 100.0) * (math.pi * 1.5)
        ctx.beginPath()
        ctx.arc(gx, gy, gr, math.pi * 0.75, math.pi * 0.75 + arc_span)
        ctx.strokeStyle = "#10B981"  # Emerald
        ctx.lineWidth = 6
        ctx.stroke()

        # Gauge Center Digits
        ctx.textAlign = "center"
        ctx.textBaseline = "middle"
        ctx.fillStyle = "#F8FAFC"
        ctx.font = "bold 15px system-ui, monospace"
        ctx.fillText(f"{int(self.gauge_val)}%", gx, gy - 2)
        ctx.fillStyle = "#94A3B8"
        ctx.font = "8px system-ui, sans-serif"
        ctx.fillText("TEMP_LOAD", gx, gy + 14)

        # 3. Top-Right Toggle Switch Widget
        tx, ty, tw, th = 145, 46, 75, 28
        ctx.beginPath()
        ctx.roundRect(tx, ty, tw, th, 14)
        ctx.fillStyle = "#059669" if self.toggle_active else "#334155"
        ctx.fill()
        ctx.strokeStyle = "#10B981" if self.toggle_active else "#64748B"
        ctx.lineWidth = 1.5
        ctx.stroke()

        # Toggle Knob
        kx = (tx + tw - 16) if self.toggle_active else (tx + 16)
        ctx.beginPath()
        ctx.arc(kx, ty + th / 2, 10, 0, math.pi * 2)
        ctx.fillStyle = "#FFFFFF"
        ctx.fill()

        ctx.fillStyle = "#FFFFFF" if self.toggle_active else "#94A3B8"
        ctx.font = "bold 8px system-ui, sans-serif"
        ctx.textAlign = "left" if not self.toggle_active else "right"
        ctx.fillText("ONLINE" if self.toggle_active else "MUTE", (tx + tw - 8) if not self.toggle_active else (tx + 8), ty + th / 2 + 1)

        # 4. Center Sparkline Graph Widget
        sx, sy, sw, sh = 16, 118, 208, 48
        ctx.fillStyle = "#0F172A"
        ctx.beginPath()
        ctx.roundRect(sx, sy, sw, sh, 8)
        ctx.fill()
        ctx.strokeStyle = "#1E293B"
        ctx.lineWidth = 1
        ctx.stroke()

        # Draw Sparkline Path
        ctx.beginPath()
        pts_cnt = len(self.sparkline_history)
        step_x = sw / (pts_cnt - 1)
        for i, val in enumerate(self.sparkline_history):
            px = sx + i * step_x
            py = sy + sh - (val / 40.0 * (sh - 12)) - 6
            if i == 0:
                ctx.moveTo(px, py)
            else:
                ctx.lineTo(px, py)

        ctx.strokeStyle = "#38BDF8"
        ctx.lineWidth = 2
        ctx.stroke()

        ctx.fillStyle = "#94A3B8"
        ctx.font = "8px system-ui, sans-serif"
        ctx.textAlign = "left"
        ctx.fillText("BUS TELEMETRY (kHz)", sx + 8, sy + 12)

        # 5. Bottom Interactive Slider Widget
        sl_x, sl_y, sl_w, sl_h = 16, 185, 208, 38
        ctx.fillStyle = "#0F172A"
        ctx.beginPath()
        ctx.roundRect(sl_x, sl_y, sl_w, sl_h, 8)
        ctx.fill()

        # Slider Track
        track_y = sl_y + 20
        ctx.beginPath()
        ctx.moveTo(sl_x + 12, track_y)
        ctx.lineTo(sl_x + sl_w - 12, track_y)
        ctx.strokeStyle = "#334155"
        ctx.lineWidth = 4
        ctx.lineCap = "round"
        ctx.stroke()

        # Active Track Fill
        knob_pos_x = sl_x + 12 + self.slider_val * (sl_w - 24)
        ctx.beginPath()
        ctx.moveTo(sl_x + 12, track_y)
        ctx.lineTo(knob_pos_x, track_y)
        ctx.strokeStyle = "#F54E00"
        ctx.lineWidth = 4
        ctx.stroke()

        # Slider Knob
        ctx.beginPath()
        ctx.arc(knob_pos_x, track_y, 8, 0, math.pi * 2)
        ctx.fillStyle = "#FFFFFF"
        ctx.fill()
        ctx.strokeStyle = "#F54E00"
        ctx.lineWidth = 2
        ctx.stroke()

        ctx.fillStyle = "#94A3B8"
        ctx.font = "8px system-ui, sans-serif"
        ctx.textAlign = "left"
        ctx.fillText("GAIN DAMPING", sl_x + 8, sl_y + 10)
        ctx.textAlign = "right"
        ctx.fillText(f"{int(self.slider_val * 100)}%", sl_x + sl_w - 8, sl_y + 10)

        if hasattr(self.drv, "show"):
            self.drv.show()


_sensor_deck_app = None


def main(canvas_id="hero_canvas"):
    global _sensor_deck_app
    print(f"Initializing PyDevices Sensor Deck on canvas '{canvas_id}'...")
    _sensor_deck_app = SensorDeckHero(canvas_id, size=240)
    print("PyDevices Sensor Deck running successfully!")
