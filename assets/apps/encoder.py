"""
PyDevices 3D Rotary Encoder (Hero Canvas App for pydevices)
===========================================================
Interactive 3D knurled aluminum rotary encoder with 24 physical detents,
rotational drag physics, tactile momentary push-button switch, and live telemetry.
"""

import sys
import time
import math

import appdev
import events
from displaydev.wasmdisplay import WasmDisplay
import pygraphics


def _color(value):
    value = value.lstrip("#")
    r, g, b = int(value[:2], 16), int(value[2:4], 16), int(value[4:], 16)
    return (r & 0xF8) << 8 | (g & 0xFC) << 3 | b >> 3


def _text(display, value, x, y, color):
    value = str(value)
    pygraphics.text8(display, value, int(x) - len(value) * 4, int(y) - 4, _color(color))


class EncoderHero:
    def __init__(self, canvas_id="hero_canvas", size=240):
        self.canvas_id = canvas_id
        self.size = size
        self.w = size
        self.h = size
        self.cx = size // 2
        self.cy = size // 2

        # Initialize PSDisplay
        self.drv = WasmDisplay(width=size, height=size, canvas_id=canvas_id)
        self.app = appdev.App(displays=(self.drv,), host_read=self.drv.get_events)

        # Encoder state
        self.angle_deg = 45.0
        self.target_angle = 45.0
        self.angular_velocity = 0.0
        self.detents = 24  # 15 deg per detent
        self.step_idx = 3
        self.is_dragging = False
        self.is_pressed = False
        self.last_pointer_angle = 0.0
        self.last_detent_sound_time = 0.0

        # Auto-spin in idle
        self.auto_spin_speed = 0.4
        self.last_interaction_time = time.time()

        self._bind_events()
        self.draw()

        self._tick_subscription = self.app.every(25, self._timer_tick)

    def _timer_tick(self, _timer):
        self.tick()

    def _bind_events(self):
        def get_angle_from_event(event):
            px = event.pos[0] - self.cx
            py = event.pos[1] - self.cy
            ang = math.degrees(math.atan2(py, px))
            return (ang + 360.0) % 360.0, math.sqrt(px * px + py * py)

        def on_pointer_down(event):
            ang, dist = get_angle_from_event(event)
            self.last_interaction_time = time.time()
            if dist <= 38:
                # Center button pressed
                self.is_pressed = True
            else:
                self.is_dragging = True
                self.last_pointer_angle = ang
            self.draw()

        def on_pointer_move(event):
            if not self.is_dragging:
                return
            ang, dist = get_angle_from_event(event)
            self.last_interaction_time = time.time()
            delta = ang - self.last_pointer_angle
            # Handle wrapping
            if delta > 180:
                delta -= 360
            elif delta < -180:
                delta += 360
            self.angle_deg = (self.angle_deg + delta) % 360.0
            self.target_angle = self.angle_deg
            self.last_pointer_angle = ang
            self.step_idx = int(round(self.angle_deg / (360.0 / self.detents))) % self.detents
            self.draw()

        def on_pointer_up(event):
            self.is_dragging = False
            self.is_pressed = False
            # Snap to nearest detent when released
            nearest_detent = round(self.angle_deg / (360.0 / self.detents))
            self.target_angle = (nearest_detent * (360.0 / self.detents)) % 360.0
            self.step_idx = int(nearest_detent) % self.detents
            self.draw()

        self.app.on(events.MOUSEBUTTONDOWN, on_pointer_down)
        self.app.on(events.MOUSEMOTION, on_pointer_move)
        self.app.on(events.MOUSEBUTTONUP, on_pointer_up)

    def tick(self):
        now = time.time()
        # Idle auto-rotation if untouched for 3 seconds
        if not self.is_dragging and (now - self.last_interaction_time > 3.0):
            self.angle_deg = (self.angle_deg + self.auto_spin_speed) % 360.0
            self.step_idx = int(round(self.angle_deg / (360.0 / self.detents))) % self.detents
            self.draw()
        elif not self.is_dragging:
            # Smoothly damp towards target angle
            diff = self.target_angle - self.angle_deg
            if diff > 180:
                diff -= 360
            elif diff < -180:
                diff += 360
            if abs(diff) > 0.1:
                self.angle_deg = (self.angle_deg + diff * 0.25) % 360.0
                self.draw()

    def draw(self):
        display = self.drv
        w, h, cx, cy = self.w, self.h, self.cx, self.cy

        # 1. Base Panel Background
        display.fill(_color("#0B0E12"))

        # 2. Outer Bezel & Detent Ring
        outer_r = 108
        pygraphics.circle(display, cx, cy, outer_r, _color("#141920"), True)
        pygraphics.circle(display, cx, cy, outer_r, _color("#2A3441"))

        # Detent Tick Marks (24 ticks around the perimeter)
        for i in range(self.detents):
            detent_deg = i * (360.0 / self.detents)
            rad = math.radians(detent_deg)
            is_active = (i == self.step_idx)
            t_len = 10 if is_active else 6
            r_inner = outer_r - t_len
            x0 = cx + math.cos(rad) * (outer_r - 2)
            y0 = cy + math.sin(rad) * (outer_r - 2)
            x1 = cx + math.cos(rad) * r_inner
            y1 = cy + math.sin(rad) * r_inner

            color = _color("#F54E00" if is_active else "#475569")
            pygraphics.line(display, int(x0), int(y0), int(x1), int(y1), color)
            if is_active:
                pygraphics.line(display, int(x0) + 1, int(y0), int(x1) + 1, int(y1), color)

        # 3. 3D Knurled Aluminum Knob (Rotates with self.angle_deg)
        knob_r = 82
        rad_rot = math.radians(self.angle_deg)

        # Draw Knurl Teeth around the perimeter
        teeth_count = 36
        for t in range(teeth_count):
            t_ang = rad_rot + t * (math.pi * 2 / teeth_count)
            tx = cx + math.cos(t_ang) * (knob_r - 2)
            ty = cy + math.sin(t_ang) * (knob_r - 2)
            pygraphics.circle(display, int(tx), int(ty), 2, _color("#64748B" if t % 2 == 0 else "#1E293B"), True)

        # Knob Main Body
        pygraphics.circle(display, cx, cy, knob_r - 4, _color("#334155"), True)
        for radius, color in ((70, "#293648"), (62, "#1E293B")):
            pygraphics.circle(display, cx, cy, radius, _color(color), True)
        pygraphics.circle(display, cx, cy, knob_r - 4, _color("#64748B"))

        # Recessed Dial Dish
        dish_r = 58
        pygraphics.circle(display, cx, cy, dish_r, _color("#090D11"), True)
        pygraphics.circle(display, cx - 6, cy - 6, dish_r - 8, _color("#111923"), True)
        pygraphics.circle(display, cx, cy, dish_r, _color("#0F172A"))

        # Tactile Indicator Notch / Line (Pointing to current angle)
        notch_start = dish_r - 18
        notch_end = dish_r - 2
        x0 = cx + math.cos(rad_rot) * notch_start
        y0 = cy + math.sin(rad_rot) * notch_start
        x1 = cx + math.cos(rad_rot) * notch_end
        y1 = cy + math.sin(rad_rot) * notch_end
        for offset in (-1, 0, 1):
            pygraphics.line(display, int(x0), int(y0) + offset, int(x1), int(y1) + offset, _color("#F54E00"))

        # 4. Center Momentary Push-Button Hub
        hub_r = 34 if not self.is_pressed else 32
        hub_color = "#9A3412" if self.is_pressed else "#111822"
        pygraphics.circle(display, cx, cy, hub_r, _color(hub_color), True)
        pygraphics.circle(display, cx - 4, cy - 4, hub_r - 6, _color("#F54E00" if self.is_pressed else "#293544"), True)
        pygraphics.circle(display, cx, cy, hub_r, _color("#FF8C42" if self.is_pressed else "#475569"))

        # 5. Center Telemetry Readout
        if self.is_pressed:
            _text(display, "CLICK", cx, cy, "#FFFFFF")
        else:
            pct = int((self.step_idx / self.detents) * 100)
            _text(display, f"{self.step_idx:02d}", cx, cy - 6, "#F8FAFC")
            _text(display, f"{pct}%", cx, cy + 8, "#94A3B8")

        if hasattr(self.drv, "show"):
            self.drv.show()


_encoder_app = None


def main(canvas_id="hero_canvas"):
    global _encoder_app
    print(f"Initializing PyDevices 3D Rotary Encoder on canvas '{canvas_id}'...")
    _encoder_app = EncoderHero(canvas_id, size=240)
    print("PyDevices 3D Rotary Encoder running successfully!")
