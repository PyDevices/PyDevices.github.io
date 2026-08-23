"""
PyDevices CircuitPython Dial (Hero Canvas App for lvgl-circuitpython)
====================================================================
Interactive NeoPixel-style RGB LED ring and capacitive touch dial:
- 16 individually illuminated virtual NeoPixel LED segments
- 360° rainbow chase and interactive touch hue positioning
- Real-time CircuitPython Feather / RP2040 telemetry readouts
"""

import math
import sys
import time

import appdev
import events
from displaydev.wasmdisplay import WasmDisplay
import pygraphics


def _rgb565(red, green, blue):
    return (int(red) & 0xF8) << 8 | (int(green) & 0xFC) << 3 | int(blue) >> 3


def _color(value):
    value = value.lstrip("#")
    return _rgb565(int(value[:2], 16), int(value[2:4], 16), int(value[4:], 16))


def _text(display, value, x, y, color, align="center"):
    value = str(value)
    if align == "center": x -= len(value) * 4
    elif align == "right": x -= len(value) * 8
    pygraphics.text8(display, value, int(x), int(y) - 8, color)


def hsl_to_rgb(h, s, l):
    c = (1.0 - abs(2.0 * l - 1.0)) * s
    x = c * (1.0 - abs((h / 60.0) % 2.0 - 1.0))
    m = l - c / 2.0
    if 0 <= h < 60:
        r, g, b = c, x, 0
    elif 60 <= h < 120:
        r, g, b = x, c, 0
    elif 120 <= h < 180:
        r, g, b = 0, c, x
    elif 180 <= h < 240:
        r, g, b = 0, x, c
    elif 240 <= h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    return int((r + m) * 255), int((g + m) * 255), int((b + m) * 255)


class CircuitDialHero:
    def __init__(self, canvas_id="hero_canvas", size=240):
        self.canvas_id = canvas_id
        self.size = size
        self.w = size
        self.h = size
        self.cx = size // 2
        self.cy = size // 2

        self.drv = WasmDisplay(width=size, height=size, canvas_id=canvas_id)
        self.app = appdev.App(displays=(self.drv,), host_read=self.drv.get_events)

        self.num_leds = 16
        self.base_hue = 0.0
        self.selected_led = 0
        self.is_dragging = False
        self.brightness = 0.85
        self.last_interaction_time = time.time()

        self.draw()
        self._bind_events()

        self._tick_subscription = self.app.every(33, self._timer_tick)

    def _timer_tick(self, _timer):
        self.tick()

    def _bind_events(self):
        def update_from_pointer(event):
            px = event.pos[0] - self.cx
            py = event.pos[1] - self.cy
            dist = math.sqrt(px * px + py * py)
            if dist >= 25:
                ang = (math.degrees(math.atan2(py, px)) + 360.0) % 360.0
                self.base_hue = ang
                self.selected_led = int((ang / 360.0) * self.num_leds) % self.num_leds
                self.last_interaction_time = time.time()
                self.draw()

        def on_pointer_down(event):
            self.is_dragging = True
            update_from_pointer(event)

        def on_pointer_move(event):
            if not self.is_dragging:
                return
            update_from_pointer(event)

        def on_pointer_up(event):
            self.is_dragging = False

        self.app.on(events.MOUSEBUTTONDOWN, on_pointer_down)
        self.app.on(events.MOUSEMOTION, on_pointer_move)
        self.app.on(events.MOUSEBUTTONUP, on_pointer_up)

    def tick(self):
        now = time.time()
        if not self.is_dragging and (now - self.last_interaction_time) > 2.0:
            self.base_hue = (self.base_hue + 1.2) % 360.0
            self.selected_led = int((self.base_hue / 360.0) * self.num_leds) % self.num_leds
            self.draw()

    def draw(self):
        display = self.drv
        w, h, cx, cy = self.w, self.h, self.cx, self.cy

        # 1. Dark Circular Housing
        display.fill(_color("#0A0D14"))

        # 2. Outer Bezel Track
        pygraphics.circle(display, cx, cy, 106, _color("#111827"), True)
        pygraphics.circle(display, cx, cy, 106, _color("#1F2937"))

        # 3. 16 NeoPixel LEDs
        ring_r = 82
        for i in range(self.num_leds):
            angle_rad = (i * (360.0 / self.num_leds) - 90.0) * (math.pi / 180.0)
            lx = cx + math.cos(angle_rad) * ring_r
            ly = cy + math.sin(angle_rad) * ring_r

            # LED Hue calculation
            led_hue = (self.base_hue + i * (360.0 / self.num_leds)) % 360.0
            r, g, b = hsl_to_rgb(led_hue, 1.0, 0.55 * self.brightness)

            # Glow aura
            is_active = (i == self.selected_led)
            if is_active:
                pygraphics.circle(display, int(lx), int(ly), 16, _rgb565(r // 3, g // 3, b // 3), True)

            # LED Bead
            radius = 10 if is_active else 8
            pygraphics.circle(display, int(lx), int(ly), radius, _rgb565(r, g, b), True)
            pygraphics.circle(display, int(lx), int(ly), radius, _color("#FFFFFF" if is_active else "#64748B"))

        # 4. Center Display Hub
        hub_r = 54
        pygraphics.circle(display, cx, cy, hub_r, _color("#0D131F"), True)
        pygraphics.circle(display, cx, cy, hub_r, _color("#2563EB"))

        # Hub Readouts
        _text(display, "CIRCUITPYTHON", cx, cy - 22, _color("#38BDF8"))

        cur_r, cur_g, cur_b = hsl_to_rgb(self.base_hue, 1.0, 0.55)
        _text(display, f"LED #{self.selected_led:02d}", cx, cy - 2, _color("#F8FAFC"))

        # Color Hex Badge
        hex_str = f"#{cur_r:02X}{cur_g:02X}{cur_b:02X}"
        _text(display, hex_str, cx, cy + 18, _rgb565(cur_r, cur_g, cur_b))
        _text(display, "TOUCH TO POSITION", cx, cy + 32, _color("#94A3B8"))

        if hasattr(self.drv, "show"):
            self.drv.show()


_circuit_app = None


def main(canvas_id="hero_canvas"):
    global _circuit_app
    print(f"Initializing PyDevices CircuitPython Dial on canvas '{canvas_id}'...")
    _circuit_app = CircuitDialHero(canvas_id, size=240)
    print("PyDevices CircuitPython Dial running successfully!")


if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "hero_canvas"
    main(cid)
