"""
PyDevices 3D Rotary Encoder (Hero Canvas App for pydevices)
===========================================================
Interactive 3D knurled aluminum rotary encoder with 24 physical detents,
rotational drag physics, tactile momentary push-button switch, and live telemetry.
"""

import sys
import types
import time
import math

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


class EncoderHero:
    def __init__(self, canvas_id="hero_canvas", size=240):
        self.canvas_id = canvas_id
        self.size = size
        self.w = size
        self.h = size
        self.cx = size // 2
        self.cy = size // 2

        # Initialize PSDisplay
        if "board_config" not in sys.modules:
            bc = types.ModuleType("board_config")
            bc.display_drv = PSDisplay(canvas_id, width=size, height=size)
            sys.modules["board_config"] = bc
            self.drv = bc.display_drv
        else:
            self.drv = sys.modules["board_config"].display_drv

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

        self._tick_proxy = create_proxy(self._js_tick_cb) if window else None
        self._tick_interval = window.setInterval(self._tick_proxy, 25) if window else None

    def _js_tick_cb(self):
        self.tick()

    def _bind_events(self):
        if not document:
            return
        canvas = document.getElementById(self.canvas_id)
        if not canvas:
            return

        def get_angle_from_event(event):
            rect = canvas.getBoundingClientRect()
            px = event.clientX - rect.left - rect.width / 2
            py = event.clientY - rect.top - rect.height / 2
            ang = math.degrees(math.atan2(py, px))
            return (ang + 360.0) % 360.0, math.sqrt(px * px + py * py)

        def on_pointer_down(event):
            event.preventDefault()
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
            event.preventDefault()
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

        self._pointer_down_proxy = create_proxy(on_pointer_down)
        self._pointer_move_proxy = create_proxy(on_pointer_move)
        self._pointer_up_proxy = create_proxy(on_pointer_up)

        canvas.addEventListener("pointerdown", self._pointer_down_proxy)
        window.addEventListener("pointermove", self._pointer_move_proxy)
        window.addEventListener("pointerup", self._pointer_up_proxy)

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
        if not hasattr(self.drv, "_buf_ctx") or not self.drv._buf_ctx:
            return
        ctx = self.drv._buf_ctx
        w, h, cx, cy = self.w, self.h, self.cx, self.cy

        # 1. Base Panel Background
        ctx.fillStyle = "#0B0E12"
        ctx.fillRect(0, 0, w, h)

        # 2. Outer Bezel & Detent Ring
        outer_r = 108
        ctx.beginPath()
        ctx.arc(cx, cy, outer_r, 0, math.pi * 2)
        ctx.fillStyle = "#141920"
        ctx.fill()
        ctx.strokeStyle = "#2A3441"
        ctx.lineWidth = 2
        ctx.stroke()

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

            ctx.beginPath()
            ctx.moveTo(x0, y0)
            ctx.lineTo(x1, y1)
            ctx.strokeStyle = "#F54E00" if is_active else "#475569"
            ctx.lineWidth = 3 if is_active else 1.5
            ctx.stroke()

        # 3. 3D Knurled Aluminum Knob (Rotates with self.angle_deg)
        knob_r = 82
        rad_rot = math.radians(self.angle_deg)

        # Radial Metallic Gradient Shading
        grad = ctx.createLinearGradient(cx - knob_r, cy - knob_r, cx + knob_r, cy + knob_r)
        grad.addColorStop(0.0, "#334155")
        grad.addColorStop(0.3, "#1E293B")
        grad.addColorStop(0.7, "#475569")
        grad.addColorStop(1.0, "#0F172A")

        ctx.save()
        ctx.translate(cx, cy)
        ctx.rotate(rad_rot)

        # Draw Knurl Teeth around the perimeter
        teeth_count = 36
        for t in range(teeth_count):
            t_ang = t * (math.pi * 2 / teeth_count)
            tx = math.cos(t_ang) * (knob_r - 2)
            ty = math.sin(t_ang) * (knob_r - 2)
            ctx.beginPath()
            ctx.arc(tx, ty, 2.5, 0, math.pi * 2)
            ctx.fillStyle = "#64748B" if t % 2 == 0 else "#1E293B"
            ctx.fill()

        # Knob Main Body
        ctx.beginPath()
        ctx.arc(0, 0, knob_r - 4, 0, math.pi * 2)
        ctx.fillStyle = grad
        ctx.fill()
        ctx.strokeStyle = "#64748B"
        ctx.lineWidth = 1.5
        ctx.stroke()

        # Recessed Dial Dish
        dish_r = 58
        dish_grad = ctx.createRadialGradient(-10, -10, 5, 0, 0, dish_r)
        dish_grad.addColorStop(0.0, "#1E293B")
        dish_grad.addColorStop(1.0, "#090D11")
        ctx.beginPath()
        ctx.arc(0, 0, dish_r, 0, math.pi * 2)
        ctx.fillStyle = dish_grad
        ctx.fill()
        ctx.strokeStyle = "#0F172A"
        ctx.lineWidth = 2
        ctx.stroke()

        # Tactile Indicator Notch / Line (Pointing to current angle)
        ctx.beginPath()
        ctx.moveTo(dish_r - 18, 0)
        ctx.lineTo(dish_r - 2, 0)
        ctx.strokeStyle = "#F54E00"
        ctx.lineWidth = 4
        ctx.lineCap = "round"
        ctx.stroke()

        ctx.restore()

        # 4. Center Momentary Push-Button Hub
        hub_r = 34 if not self.is_pressed else 32
        hub_grad = ctx.createRadialGradient(cx - 5, cy - 5, 2, cx, cy, hub_r)
        if self.is_pressed:
            hub_grad.addColorStop(0.0, "#F54E00")
            hub_grad.addColorStop(1.0, "#9A3412")
        else:
            hub_grad.addColorStop(0.0, "#293544")
            hub_grad.addColorStop(1.0, "#111822")

        ctx.beginPath()
        ctx.arc(cx, cy, hub_r, 0, math.pi * 2)
        ctx.fillStyle = hub_grad
        ctx.fill()
        ctx.strokeStyle = "#FF8C42" if self.is_pressed else "#475569"
        ctx.lineWidth = 1.5
        ctx.stroke()

        # 5. Center Telemetry Readout
        ctx.textAlign = "center"
        ctx.textBaseline = "middle"

        if self.is_pressed:
            ctx.fillStyle = "#FFFFFF"
            ctx.font = "bold 10px system-ui, sans-serif"
            ctx.fillText("CLICK", cx, cy)
        else:
            pct = int((self.step_idx / self.detents) * 100)
            ctx.fillStyle = "#F8FAFC"
            ctx.font = "bold 13px system-ui, sans-serif"
            ctx.fillText(f"{self.step_idx:02d}", cx, cy - 6)

            ctx.fillStyle = "#94A3B8"
            ctx.font = "9px system-ui, sans-serif"
            ctx.fillText(f"{pct}%", cx, cy + 8)

        if hasattr(self.drv, "show"):
            self.drv.show()


_encoder_app = None


def main(canvas_id="hero_canvas"):
    global _encoder_app
    print(f"Initializing PyDevices 3D Rotary Encoder on canvas '{canvas_id}'...")
    _encoder_app = EncoderHero(canvas_id, size=240)
    print("PyDevices 3D Rotary Encoder running successfully!")
