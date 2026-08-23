"""
PyDevices Palette Orb & Gamut Visualizer (Hero Canvas App for palettes)
======================================================================
Real-time chromatic color harmonizer with dynamic harmonic nodes,
RGB565 / RGB888 precision math, and smooth gradient ramps.
"""

import sys
import time
import math

import appdev
import events
from displaydev.wasmdisplay import WasmDisplay
import pygraphics


def hsl_to_rgb(h, s, l):
    # h in [0, 360), s in [0, 1], l in [0, 1]
    c = (1.0 - abs(2.0 * l - 1.0)) * s
    x = c * (1.0 - abs((h / 60.0) % 2.0 - 1.0))
    m = l - c / 2.0
    if 0 <= h < 60:
        r1, g1, b1 = c, x, 0
    elif 60 <= h < 120:
        r1, g1, b1 = x, c, 0
    elif 120 <= h < 180:
        r1, g1, b1 = 0, c, x
    elif 180 <= h < 240:
        r1, g1, b1 = 0, x, c
    elif 240 <= h < 300:
        r1, g1, b1 = x, 0, c
    else:
        r1, g1, b1 = c, 0, x
    return int((r1 + m) * 255), int((g1 + m) * 255), int((b1 + m) * 255)


def rgb_to_rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def _color(value):
    value = value.lstrip("#")
    return rgb_to_rgb565(int(value[:2], 16), int(value[2:4], 16), int(value[4:], 16))


def _text(display, value, x, y, color):
    value = str(value)
    pygraphics.text8(display, value, int(x) - len(value) * 4, int(y) - 8, color)


class PaletteOrbHero:
    def __init__(self, canvas_id="hero_canvas", size=240):
        self.canvas_id = canvas_id
        self.size = size
        self.w = size
        self.h = size
        self.cx = size // 2
        self.cy = size // 2

        self.drv = WasmDisplay(width=size, height=size, canvas_id=canvas_id)
        self.app = appdev.App(displays=(self.drv,), host_read=self.drv.get_events)

        self.base_hue = 25.0  # Warm amber start
        self.is_dragging = False
        self.last_interaction_time = time.time()

        self._bind_events()
        self.draw()

        self._tick_subscription = self.app.every(30, self._timer_tick)

    def _timer_tick(self, _timer):
        self.tick()

    def _bind_events(self):
        def on_pointer_down(event):
            self.is_dragging = True
            px = event.pos[0] - self.cx
            py = event.pos[1] - self.cy
            self.base_hue = (math.degrees(math.atan2(py, px)) + 360.0) % 360.0
            self.last_interaction_time = time.time()
            self.draw()

        def on_pointer_move(event):
            if not self.is_dragging:
                return
            px = event.pos[0] - self.cx
            py = event.pos[1] - self.cy
            self.base_hue = (math.degrees(math.atan2(py, px)) + 360.0) % 360.0
            self.last_interaction_time = time.time()
            self.draw()

        def on_pointer_up(event):
            self.is_dragging = False

        self.app.on(events.MOUSEBUTTONDOWN, on_pointer_down)
        self.app.on(events.MOUSEMOTION, on_pointer_move)
        self.app.on(events.MOUSEBUTTONUP, on_pointer_up)

    def tick(self):
        now = time.time()
        if not self.is_dragging and (now - self.last_interaction_time > 2.0):
            self.base_hue = (self.base_hue + 0.4) % 360.0
            self.draw()

    def draw(self):
        display = self.drv
        w, h, cx, cy = self.w, self.h, self.cx, self.cy

        # 1. Dark Base
        display.fill(_color("#0B0E12"))

        # 2. Outer Chromatic Spectrum Ring
        ring_r_outer = 106
        ring_r_inner = 84
        segments = 72
        for i in range(segments):
            ang0 = i * (math.pi * 2 / segments)
            ang1 = (i + 1.05) * (math.pi * 2 / segments)
            hue = (i * (360.0 / segments)) % 360.0
            r, g, b = hsl_to_rgb(hue, 0.9, 0.52)

            for radius in range(ring_r_inner, ring_r_outer + 1):
                x0 = int(cx + math.cos(ang0) * radius)
                y0 = int(cy + math.sin(ang0) * radius)
                x1 = int(cx + math.cos(ang1) * radius)
                y1 = int(cy + math.sin(ang1) * radius)
                pygraphics.line(display, x0, y0, x1, y1, rgb_to_rgb565(r, g, b))

        # 3. Inner Dial Body
        inner_r = ring_r_inner - 2
        pygraphics.circle(display, cx, cy, inner_r, _color("#0A0D11"), True)
        for radius in range(inner_r, 5, -8):
            shade = min(40, 10 + (inner_r - radius) // 3)
            pygraphics.circle(display, cx - 2, cy - 2, radius, rgb_to_rgb565(shade, shade + 6, shade + 12))
        pygraphics.circle(display, cx, cy, inner_r, _color("#2A3644"))

        # 4. Triadic Harmonic Color Nodes (Base, Base+120, Base+240)
        hues = [
            (self.base_hue, 12, "BASE"),
            ((self.base_hue + 120.0) % 360.0, 8, "+120"),
            ((self.base_hue + 240.0) % 360.0, 8, "+240"),
        ]

        # Draw connecting triangle between nodes
        node_pts = []
        for hue, node_r, label in hues:
            rad = math.radians(hue)
            nx = cx + math.cos(rad) * ((ring_r_outer + ring_r_inner) / 2)
            ny = cy + math.sin(rad) * ((ring_r_outer + ring_r_inner) / 2)
            node_pts.append((nx, ny))

        for start, end in zip(node_pts, node_pts[1:] + node_pts[:1]):
            pygraphics.line(display, int(start[0]), int(start[1]), int(end[0]), int(end[1]), _color("#59616B"))

        # Draw Node Handles
        for idx, (hue, node_r, label) in enumerate(hues):
            nx, ny = node_pts[idx]
            r, g, b = hsl_to_rgb(hue, 1.0, 0.55)
            pygraphics.circle(display, int(nx), int(ny), node_r, rgb_to_rgb565(r, g, b), True)
            pygraphics.circle(display, int(nx), int(ny), node_r, _color("#FFFFFF"))

        # 5. Center Palette Swatches & RGB565 / Hex Telemetry
        r0, g0, b0 = hsl_to_rgb(self.base_hue, 1.0, 0.5)
        rgb565 = rgb_to_rgb565(r0, g0, b0)
        hex_str = f"#{r0:02X}{g0:02X}{b0:02X}"

        # Swatch Pill
        swatch_w, swatch_h = 70, 20
        pygraphics.round_rect(display, cx - swatch_w // 2, cy - 32, swatch_w, swatch_h, 6, rgb565, True)
        pygraphics.round_rect(display, cx - swatch_w // 2, cy - 32, swatch_w, swatch_h, 6, _color("#FFFFFF"))
        _text(display, hex_str, cx, cy + 2, _color("#F8FAFC"))
        _text(display, f"0x{rgb565:04X} (565)", cx, cy + 18, _color("#38BDF8"))
        _text(display, f"HSL({int(self.base_hue)}, 100%, 50%)", cx, cy + 32, _color("#94A3B8"))

        if hasattr(self.drv, "show"):
            self.drv.show()


_palette_app = None


def main(canvas_id="hero_canvas"):
    global _palette_app
    print(f"Initializing PyDevices Palette Orb on canvas '{canvas_id}'...")
    _palette_app = PaletteOrbHero(canvas_id, size=240)
    print("PyDevices Palette Orb running successfully!")
