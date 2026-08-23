"""
PyDevices Mobile Pad (Hero Canvas App for android-template)
===========================================================
Interactive Android handheld touchscreen gamepad controller:
- Interactive 4-way D-Pad (Up, Down, Left, Right)
- Responsive A/B action buttons
- Virtual mobile display viewport with responsive player avatar
"""

import math
import sys
import time

import appdev
import events
from displaydev.wasmdisplay import WasmDisplay
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


class MobilePadHero:
    def __init__(self, canvas_id="hero_canvas", size=240):
        self.canvas_id = canvas_id
        self.size = size
        self.w = size
        self.h = size

        self.drv = WasmDisplay(width=size, height=size, canvas_id=canvas_id)
        self.app = appdev.App(displays=(self.drv,), host_read=self.drv.get_events)

        # Player avatar on virtual screen (x: 20..220, y: 32..112)
        self.avatar_x = 120.0
        self.avatar_y = 72.0
        self.avatar_color = "#38BDF8"
        self.active_btn = None
        self.score = 1280

        self.draw()
        self._bind_events()

        self._tick_subscription = self.app.every(33, self._timer_tick)

    def _timer_tick(self, _timer):
        self.tick()

    def _bind_events(self):
        def handle_touch(event):
            x, y = event.pos

            # D-Pad (Center: 64, 180; radius 40)
            d_cx, d_cy = 64, 180
            dx = x - d_cx
            dy = y - d_cy
            dist_d = math.sqrt(dx * dx + dy * dy)
            if dist_d <= 42:
                if abs(dx) > abs(dy):
                    if dx > 10:
                        self.avatar_x = min(205, self.avatar_x + 6)
                        self.active_btn = "RIGHT"
                    elif dx < -10:
                        self.avatar_x = max(35, self.avatar_x - 6)
                        self.active_btn = "LEFT"
                else:
                    if dy > 10:
                        self.avatar_y = min(100, self.avatar_y + 6)
                        self.active_btn = "DOWN"
                    elif dy < -10:
                        self.avatar_y = max(44, self.avatar_y - 6)
                        self.active_btn = "UP"
                self.score += 5
                self.draw()
                return

            # A Button (190, 165, r=16)
            if math.sqrt((x - 190) ** 2 + (y - 165) ** 2) <= 20:
                self.avatar_color = "#10B981" if self.avatar_color != "#10B981" else "#F59E0B"
                self.active_btn = "A"
                self.score += 20
                self.draw()
                return

            # B Button (160, 195, r=16)
            if math.sqrt((x - 160) ** 2 + (y - 195) ** 2) <= 20:
                self.avatar_color = "#EC4899" if self.avatar_color != "#EC4899" else "#38BDF8"
                self.active_btn = "B"
                self.score += 20
                self.draw()
                return

        def on_pointer_down(event):
            handle_touch(event)

        def on_pointer_up(event):
            self.active_btn = None
            self.draw()

        self.app.on(events.MOUSEBUTTONDOWN, on_pointer_down)
        self.app.on(events.MOUSEBUTTONUP, on_pointer_up)

    def tick(self):
        # Subtle idle bob
        if not self.active_btn:
            self.avatar_y += math.sin(time.time() * 4.0) * 0.3
            self.draw()

    def draw(self):
        display = self.drv
        w, h = self.w, self.h

        # 1. Dark Handheld Console Frame Background
        display.fill(_color("#0F172A"))

        # 2. Virtual LCD Viewport (x: 16, y: 14, w: 208, h: 104)
        vx, vy, vw, vh = 16, 14, 208, 104
        pygraphics.round_rect(display, vx, vy, vw, vh, 8, _color("#020617"), True)
        pygraphics.round_rect(display, vx, vy, vw, vh, 8, _color("#334155"))

        # Viewport Header
        _text(display, "ANDROID P4A", vx + 10, vy + 16, "#A855F7")
        _text(display, f"PTS: {self.score}", vx + vw - 10, vy + 16, "#38BDF8", "right")

        # Viewport Starfield / Grid
        for gy in range(vy + 26, vy + vh, 18):
            pygraphics.hline(display, vx + 6, gy, vw - 12, _color("#1E293B"))

        # Animated Player Avatar
        ax, ay = self.avatar_x, self.avatar_y
        pygraphics.circle(display, int(ax), int(ay), 16, _color("#123247"), True)
        pygraphics.circle(display, int(ax), int(ay), 10, _color(self.avatar_color), True)
        pygraphics.circle(display, int(ax), int(ay), 10, _color("#FFFFFF"))

        # 3. 4-Way D-Pad on Left (Center: 64, 180)
        d_cx, d_cy = 64, 180
        pad_size = 72
        pygraphics.round_rect(display, int(d_cx - pad_size / 2), d_cy - 12, pad_size, 24, 6, _color("#1E293B"), True)
        pygraphics.round_rect(display, d_cx - 12, int(d_cy - pad_size / 2), 24, pad_size, 6, _color("#1E293B"), True)

        # D-Pad Arrows
        _text(display, "^", d_cx, d_cy - 22, "#94A3B8", "center")
        _text(display, "v", d_cx, d_cy + 28, "#94A3B8", "center")
        _text(display, "<", d_cx - 24, d_cy + 4, "#94A3B8", "center")
        _text(display, ">", d_cx + 24, d_cy + 4, "#94A3B8", "center")

        # 4. Action Buttons A & B on Right
        # B Button
        bx, by = 156, 192
        pygraphics.circle(display, bx, by, 16, _color("#9333EA" if self.active_btn == "B" else "#6B21A8"), True)
        pygraphics.circle(display, bx, by, 16, _color("#C084FC"))
        _text(display, "B", bx, by + 4, "#FFFFFF", "center")

        # A Button
        ax_btn, ay_btn = 192, 162
        pygraphics.circle(display, ax_btn, ay_btn, 16, _color("#059669" if self.active_btn == "A" else "#065F46"), True)
        pygraphics.circle(display, ax_btn, ay_btn, 16, _color("#34D399"))
        _text(display, "A", ax_btn, ay_btn + 4, "#FFFFFF", "center")

        if hasattr(self.drv, "show"):
            self.drv.show()


_pad_app = None


def main(canvas_id="hero_canvas"):
    global _pad_app
    print(f"Initializing PyDevices Mobile Pad on canvas '{canvas_id}'...")
    _pad_app = MobilePadHero(canvas_id, size=240)
    print("PyDevices Mobile Pad running successfully!")


if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "hero_canvas"
    main(cid)
