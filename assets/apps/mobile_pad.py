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
import types

document = window = None
create_proxy = lambda fn: fn

from displaydev.auto import AutoDisplay


class MobilePadHero:
    def __init__(self, canvas_id="hero_canvas", size=240):
        self.canvas_id = canvas_id
        self.size = size
        self.w = size
        self.h = size

        bc = types.ModuleType("board_config")
        bc.display_drv = AutoDisplay(width=size, height=size, canvas_id=canvas_id)
        sys.modules["board_config"] = bc
        self.drv = bc.display_drv

        # Player avatar on virtual screen (x: 20..220, y: 32..112)
        self.avatar_x = 120.0
        self.avatar_y = 72.0
        self.avatar_color = "#38BDF8"
        self.active_btn = None
        self.score = 1280

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

        def handle_touch(event):
            rect = canvas.getBoundingClientRect()
            x = (event.clientX - rect.left) * (self.size / rect.width)
            y = (event.clientY - rect.top) * (self.size / rect.height)

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
            event.preventDefault()
            handle_touch(event)

        def on_pointer_up(event):
            self.active_btn = None
            self.draw()

        self._p_down = create_proxy(on_pointer_down)
        self._p_up = create_proxy(on_pointer_up)

        canvas.addEventListener("pointerdown", self._p_down)
        window.addEventListener("pointerup", self._p_up)

    def tick(self):
        # Subtle idle bob
        if not self.active_btn:
            self.avatar_y += math.sin(time.time() * 4.0) * 0.3
            self.draw()

    def draw(self):
        if not hasattr(self.drv, "_buf_ctx") or not self.drv._buf_ctx:
            return
        ctx = self.drv._buf_ctx
        w, h = self.w, self.h

        # 1. Dark Handheld Console Frame Background
        ctx.fillStyle = "#0F172A"
        ctx.fillRect(0, 0, w, h)

        # 2. Virtual LCD Viewport (x: 16, y: 14, w: 208, h: 104)
        vx, vy, vw, vh = 16, 14, 208, 104
        ctx.fillStyle = "#020617"
        ctx.beginPath()
        ctx.roundRect(vx, vy, vw, vh, 8)
        ctx.fill()
        ctx.strokeStyle = "#334155"
        ctx.lineWidth = 1.5
        ctx.stroke()

        # Viewport Header
        ctx.fillStyle = "#A855F7"
        ctx.font = "bold 9px system-ui, sans-serif"
        ctx.textAlign = "left"
        ctx.fillText("● ANDROID P4A", vx + 10, vy + 16)

        ctx.fillStyle = "#38BDF8"
        ctx.font = "bold 9px system-ui, monospace"
        ctx.textAlign = "right"
        ctx.fillText(f"PTS: {self.score}", vx + vw - 10, vy + 16)

        # Viewport Starfield / Grid
        ctx.strokeStyle = "rgba(51, 65, 85, 0.4)"
        ctx.lineWidth = 1
        for gy in range(vy + 26, vy + vh, 18):
            ctx.beginPath()
            ctx.moveTo(vx + 6, gy)
            ctx.lineTo(vx + vw - 6, gy)
            ctx.stroke()

        # Animated Player Avatar
        ax, ay = self.avatar_x, self.avatar_y
        ctx.beginPath()
        ctx.arc(ax, ay, 10, 0, math.pi * 2)
        ctx.fillStyle = self.avatar_color
        ctx.fill()
        ctx.strokeStyle = "#FFFFFF"
        ctx.lineWidth = 2
        ctx.stroke()

        # Avatar Glow
        ctx.beginPath()
        ctx.arc(ax, ay, 16, 0, math.pi * 2)
        ctx.fillStyle = "rgba(56, 189, 248, 0.2)"
        ctx.fill()

        # 3. 4-Way D-Pad on Left (Center: 64, 180)
        d_cx, d_cy = 64, 180
        pad_size = 72
        ctx.fillStyle = "#1E293B"
        # Cross Horizontal
        ctx.beginPath()
        ctx.roundRect(d_cx - pad_size / 2, d_cy - 12, pad_size, 24, 6)
        ctx.fill()
        # Cross Vertical
        ctx.beginPath()
        ctx.roundRect(d_cx - 12, d_cy - pad_size / 2, 24, pad_size, 6)
        ctx.fill()

        # D-Pad Arrows
        ctx.fillStyle = "#94A3B8"
        ctx.font = "bold 10px monospace"
        ctx.textAlign = "center"
        ctx.fillText("▲", d_cx, d_cy - 22)
        ctx.fillText("▼", d_cx, d_cy + 28)
        ctx.fillText("◀", d_cx - 24, d_cy + 4)
        ctx.fillText("▶", d_cx + 24, d_cy + 4)

        # 4. Action Buttons A & B on Right
        # B Button
        bx, by = 156, 192
        ctx.beginPath()
        ctx.arc(bx, by, 16, 0, math.pi * 2)
        ctx.fillStyle = "#9333EA" if self.active_btn == "B" else "#6B21A8"
        ctx.fill()
        ctx.strokeStyle = "#C084FC"
        ctx.lineWidth = 1.5
        ctx.stroke()
        ctx.fillStyle = "#FFFFFF"
        ctx.font = "bold 11px system-ui"
        ctx.textAlign = "center"
        ctx.fillText("B", bx, by + 4)

        # A Button
        ax_btn, ay_btn = 192, 162
        ctx.beginPath()
        ctx.arc(ax_btn, ay_btn, 16, 0, math.pi * 2)
        ctx.fillStyle = "#059669" if self.active_btn == "A" else "#065F46"
        ctx.fill()
        ctx.strokeStyle = "#34D399"
        ctx.lineWidth = 1.5
        ctx.stroke()
        ctx.fillStyle = "#FFFFFF"
        ctx.fillText("A", ax_btn, ay_btn + 4)

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
