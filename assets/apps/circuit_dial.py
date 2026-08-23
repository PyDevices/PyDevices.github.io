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
import types

document = window = None
create_proxy = lambda fn: fn

from displaydev.auto import AutoDisplay


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

        bc = types.ModuleType("board_config")
        bc.display_drv = AutoDisplay(width=size, height=size, canvas_id=canvas_id)
        sys.modules["board_config"] = bc
        self.drv = bc.display_drv

        self.num_leds = 16
        self.base_hue = 0.0
        self.selected_led = 0
        self.is_dragging = False
        self.brightness = 0.85
        self.last_interaction_time = time.time()

        self.draw()
        self._bind_events()

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

        def update_from_pointer(event):
            rect = canvas.getBoundingClientRect()
            px = event.clientX - rect.left - rect.width / 2
            py = event.clientY - rect.top - rect.height / 2
            dist = math.sqrt(px * px + py * py)
            if dist >= 25:
                ang = (math.degrees(math.atan2(py, px)) + 360.0) % 360.0
                self.base_hue = ang
                self.selected_led = int((ang / 360.0) * self.num_leds) % self.num_leds
                self.last_interaction_time = time.time()
                self.draw()

        def on_pointer_down(event):
            event.preventDefault()
            self.is_dragging = True
            update_from_pointer(event)

        def on_pointer_move(event):
            if not self.is_dragging:
                return
            event.preventDefault()
            update_from_pointer(event)

        def on_pointer_up(event):
            self.is_dragging = False

        self._p_down = create_proxy(on_pointer_down)
        self._p_move = create_proxy(on_pointer_move)
        self._p_up = create_proxy(on_pointer_up)

        canvas.addEventListener("pointerdown", self._p_down)
        window.addEventListener("pointermove", self._p_move)
        window.addEventListener("pointerup", self._p_up)

    def tick(self):
        now = time.time()
        if not self.is_dragging and (now - self.last_interaction_time) > 2.0:
            self.base_hue = (self.base_hue + 1.2) % 360.0
            self.selected_led = int((self.base_hue / 360.0) * self.num_leds) % self.num_leds
            self.draw()

    def draw(self):
        if not hasattr(self.drv, "_buf_ctx") or not self.drv._buf_ctx:
            return
        ctx = self.drv._buf_ctx
        w, h, cx, cy = self.w, self.h, self.cx, self.cy

        # 1. Dark Circular Housing
        ctx.fillStyle = "#0A0D14"
        ctx.fillRect(0, 0, w, h)

        # 2. Outer Bezel Track
        ctx.beginPath()
        ctx.arc(cx, cy, 106, 0, math.pi * 2)
        ctx.fillStyle = "#111827"
        ctx.fill()
        ctx.strokeStyle = "#1F2937"
        ctx.lineWidth = 2
        ctx.stroke()

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
                ctx.beginPath()
                ctx.arc(lx, ly, 16, 0, math.pi * 2)
                ctx.fillStyle = f"rgba({r}, {g}, {b}, 0.35)"
                ctx.fill()

            # LED Bead
            ctx.beginPath()
            ctx.arc(lx, ly, 8 if not is_active else 10, 0, math.pi * 2)
            ctx.fillStyle = f"rgb({r}, {g}, {b})"
            ctx.fill()
            ctx.strokeStyle = "#FFFFFF" if is_active else "rgba(255, 255, 255, 0.4)"
            ctx.lineWidth = 1.5
            ctx.stroke()

        # 4. Center Display Hub
        hub_r = 54
        ctx.beginPath()
        ctx.arc(cx, cy, hub_r, 0, math.pi * 2)
        ctx.fillStyle = "#0D131F"
        ctx.fill()
        ctx.strokeStyle = "#2563EB"
        ctx.lineWidth = 1.5
        ctx.stroke()

        # Hub Readouts
        ctx.fillStyle = "#38BDF8"
        ctx.font = "bold 9px system-ui, sans-serif"
        ctx.textAlign = "center"
        ctx.fillText("CIRCUITPYTHON", cx, cy - 22)

        cur_r, cur_g, cur_b = hsl_to_rgb(self.base_hue, 1.0, 0.55)
        ctx.fillStyle = "#F8FAFC"
        ctx.font = "bold 15px monospace"
        ctx.fillText(f"LED #{self.selected_led:02d}", cx, cy - 2)

        # Color Hex Badge
        hex_str = f"#{cur_r:02X}{cur_g:02X}{cur_b:02X}"
        ctx.fillStyle = f"rgb({cur_r}, {cur_g}, {cur_b})"
        ctx.font = "bold 9px monospace"
        ctx.fillText(hex_str, cx, cy + 18)

        ctx.fillStyle = "#94A3B8"
        ctx.font = "8px system-ui, sans-serif"
        ctx.fillText("TOUCH TO POSITION", cx, cy + 32)

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
