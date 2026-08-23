"""
PyDevices Palette Orb & Gamut Visualizer (Hero Canvas App for palettes)
======================================================================
Real-time chromatic color harmonizer with dynamic harmonic nodes,
RGB565 / RGB888 precision math, and smooth gradient ramps.
"""

import sys
import types
import time
import math

document = window = None
create_proxy = lambda fn: fn

from displaydev.auto import AutoDisplay


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


class PaletteOrbHero:
    def __init__(self, canvas_id="hero_canvas", size=240):
        self.canvas_id = canvas_id
        self.size = size
        self.w = size
        self.h = size
        self.cx = size // 2
        self.cy = size // 2

        bc = types.ModuleType("board_config")
        bc.display_drv = AutoDisplay(width=size, height=size, canvas_id=canvas_id)
        sys.modules["board_config"] = bc
        self.drv = bc.display_drv

        self.base_hue = 25.0  # Warm amber start
        self.is_dragging = False
        self.last_interaction_time = time.time()

        self._bind_events()
        self.draw()

        self._tick_proxy = create_proxy(self._js_tick_cb) if window else None
        self._tick_interval = window.setInterval(self._tick_proxy, 30) if window else None

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
            self.is_dragging = True
            rect = canvas.getBoundingClientRect()
            px = event.clientX - rect.left - rect.width / 2
            py = event.clientY - rect.top - rect.height / 2
            self.base_hue = (math.degrees(math.atan2(py, px)) + 360.0) % 360.0
            self.last_interaction_time = time.time()
            self.draw()

        def on_pointer_move(event):
            if not self.is_dragging:
                return
            event.preventDefault()
            rect = canvas.getBoundingClientRect()
            px = event.clientX - rect.left - rect.width / 2
            py = event.clientY - rect.top - rect.height / 2
            self.base_hue = (math.degrees(math.atan2(py, px)) + 360.0) % 360.0
            self.last_interaction_time = time.time()
            self.draw()

        def on_pointer_up(event):
            self.is_dragging = False

        self._pointer_down_proxy = create_proxy(on_pointer_down)
        self._pointer_move_proxy = create_proxy(on_pointer_move)
        self._pointer_up_proxy = create_proxy(on_pointer_up)

        canvas.addEventListener("pointerdown", self._pointer_down_proxy)
        window.addEventListener("pointermove", self._pointer_move_proxy)
        window.addEventListener("pointerup", self._pointer_up_proxy)

    def tick(self):
        now = time.time()
        if not self.is_dragging and (now - self.last_interaction_time > 2.0):
            self.base_hue = (self.base_hue + 0.4) % 360.0
            self.draw()

    def draw(self):
        if not hasattr(self.drv, "_buf_ctx") or not self.drv._buf_ctx:
            return
        ctx = self.drv._buf_ctx
        w, h, cx, cy = self.w, self.h, self.cx, self.cy

        # 1. Dark Base
        ctx.fillStyle = "#0B0E12"
        ctx.fillRect(0, 0, w, h)

        # 2. Outer Chromatic Spectrum Ring
        ring_r_outer = 106
        ring_r_inner = 84
        segments = 72
        for i in range(segments):
            ang0 = i * (math.pi * 2 / segments)
            ang1 = (i + 1.05) * (math.pi * 2 / segments)
            hue = (i * (360.0 / segments)) % 360.0
            r, g, b = hsl_to_rgb(hue, 0.9, 0.52)

            ctx.beginPath()
            ctx.arc(cx, cy, ring_r_outer, ang0, ang1)
            ctx.arc(cx, cy, ring_r_inner, ang1, ang0, True)
            ctx.closePath()
            ctx.fillStyle = f"rgb({r},{g},{b})"
            ctx.fill()

        # 3. Inner Dial Body
        inner_r = ring_r_inner - 2
        dial_grad = ctx.createRadialGradient(cx - 10, cy - 10, 5, cx, cy, inner_r)
        dial_grad.addColorStop(0.0, "#1A222C")
        dial_grad.addColorStop(1.0, "#0A0D11")
        ctx.beginPath()
        ctx.arc(cx, cy, inner_r, 0, math.pi * 2)
        ctx.fillStyle = dial_grad
        ctx.fill()
        ctx.strokeStyle = "#2A3644"
        ctx.lineWidth = 1.5
        ctx.stroke()

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

        ctx.beginPath()
        ctx.moveTo(node_pts[0][0], node_pts[0][1])
        ctx.lineTo(node_pts[1][0], node_pts[1][1])
        ctx.lineTo(node_pts[2][0], node_pts[2][1])
        ctx.closePath()
        ctx.strokeStyle = "rgba(255, 255, 255, 0.3)"
        ctx.lineWidth = 1
        ctx.stroke()

        # Draw Node Handles
        for idx, (hue, node_r, label) in enumerate(hues):
            nx, ny = node_pts[idx]
            r, g, b = hsl_to_rgb(hue, 1.0, 0.55)
            ctx.beginPath()
            ctx.arc(nx, ny, node_r, 0, math.pi * 2)
            ctx.fillStyle = f"rgb({r},{g},{b})"
            ctx.fill()
            ctx.strokeStyle = "#FFFFFF"
            ctx.lineWidth = 2 if idx == 0 else 1
            ctx.stroke()

        # 5. Center Palette Swatches & RGB565 / Hex Telemetry
        r0, g0, b0 = hsl_to_rgb(self.base_hue, 1.0, 0.5)
        rgb565 = rgb_to_rgb565(r0, g0, b0)
        hex_str = f"#{r0:02X}{g0:02X}{b0:02X}"

        # Swatch Pill
        swatch_w, swatch_h = 70, 20
        ctx.beginPath()
        ctx.roundRect(cx - swatch_w // 2, cy - 32, swatch_w, swatch_h, 6)
        ctx.fillStyle = hex_str
        ctx.fill()
        ctx.strokeStyle = "#FFFFFF"
        ctx.lineWidth = 1
        ctx.stroke()

        ctx.textAlign = "center"
        ctx.textBaseline = "middle"

        ctx.fillStyle = "#F8FAFC"
        ctx.font = "bold 12px system-ui, monospace"
        ctx.fillText(hex_str, cx, cy + 2)

        ctx.fillStyle = "#38BDF8"
        ctx.font = "10px system-ui, monospace"
        ctx.fillText(f"0x{rgb565:04X} (565)", cx, cy + 18)

        ctx.fillStyle = "#94A3B8"
        ctx.font = "9px system-ui, sans-serif"
        ctx.fillText(f"HSL({int(self.base_hue)}°, 100%, 50%)", cx, cy + 32)

        if hasattr(self.drv, "show"):
            self.drv.show()


_palette_app = None


def main(canvas_id="hero_canvas"):
    global _palette_app
    print(f"Initializing PyDevices Palette Orb on canvas '{canvas_id}'...")
    _palette_app = PaletteOrbHero(canvas_id, size=240)
    print("PyDevices Palette Orb running successfully!")
