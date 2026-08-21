"""
PyDevices C Header Parser & Binding Generator (Hero Canvas App for lvgl-bindings)
================================================================================
Interactive AST token parser stream and binding generator matrix.
- Real-time token scan and syntax highlighting
- C header struct typedef decomposition and schema graph
- Interactive touch token trigger
"""

import math
import sys
import time
import types
from random import random, choice

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


C_TOKENS = [
    ("typedef struct", "#38BDF8"),
    ("lv_obj_t*", "#818CF8"),
    ("lv_color_t", "#34D399"),
    ("lv_area_t", "#FBBF24"),
    ("lv_event_cb_t", "#F472B6"),
    ("lv_screen_active()", "#60A5FA"),
    ("lv_display_create()", "#A78BFA"),
    ("lv_arc_set_value()", "#F87171"),
    ("lv_anim_t*", "#38BDF8"),
    ("lv_image_dsc_t", "#4ADE80"),
    ("mp_obj_t", "#F59E0B"),
    ("mp_bind_method()", "#10B981"),
]


class AstParserHero:
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

        self.tokens_parsed = 4820
        self.schemas_gen = 142
        self.scan_line_y = 36.0
        self.log_lines = [
            ("PARSE lv_obj_tree.h ...", "#94A3B8"),
            ("EMIT mp_lvgl_obj_type", "#10B981"),
            ("AST lv_style_prop_t [OK]", "#38BDF8"),
            ("GEN bindings_py.c", "#F59E0B"),
        ]

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

        def on_pointer_down(event):
            event.preventDefault()
            self.tokens_parsed += 42
            self.schemas_gen += 1
            tok, col = choice(C_TOKENS)
            self.log_lines.pop(0)
            self.log_lines.append((f"EMIT {tok}", col))
            self.draw()

        self._p_down = create_proxy(on_pointer_down)
        canvas.addEventListener("pointerdown", self._p_down)

    def tick(self):
        self.scan_line_y += 1.8
        if self.scan_line_y > 175:
            self.scan_line_y = 36.0
            self.tokens_parsed += 8
            if random() > 0.6:
                tok, col = choice(C_TOKENS)
                self.log_lines.pop(0)
                self.log_lines.append((f"MATCH {tok}", col))
        self.draw()

    def draw(self):
        if not hasattr(self.drv, "_buf_ctx") or not self.drv._buf_ctx:
            return
        ctx = self.drv._buf_ctx
        w, h = self.w, self.h

        # 1. Dark Blueprint Bezel Background
        ctx.fillStyle = "#070B12"
        ctx.fillRect(0, 0, w, h)

        # Subtle Matrix Grid
        ctx.strokeStyle = "rgba(30, 41, 59, 0.4)"
        ctx.lineWidth = 1
        for gx in range(16, w, 20):
            ctx.beginPath()
            ctx.moveTo(gx, 0)
            ctx.lineTo(gx, h)
            ctx.stroke()
        for gy in range(16, h, 20):
            ctx.beginPath()
            ctx.moveTo(0, gy)
            ctx.lineTo(w, gy)
            ctx.stroke()

        # 2. Header Bar
        ctx.fillStyle = "rgba(15, 23, 42, 0.92)"
        ctx.fillRect(0, 0, w, 26)
        ctx.strokeStyle = "#1E293B"
        ctx.lineWidth = 1
        ctx.beginPath()
        ctx.moveTo(0, 26)
        ctx.lineTo(w, 26)
        ctx.stroke()

        ctx.fillStyle = "#38BDF8"
        ctx.font = "bold 9px system-ui, monospace"
        ctx.textAlign = "left"
        ctx.fillText("⚡ LVGL BINDINGS GEN", 10, 17)

        ctx.fillStyle = "#10B981"
        ctx.textAlign = "right"
        ctx.fillText(f"AST: {self.schemas_gen}", w - 10, 17)

        # 3. Token Matrix Window
        matrix_y = 32
        for i, (text, color) in enumerate(self.log_lines):
            row_y = matrix_y + i * 22
            # Terminal prompt pill
            ctx.fillStyle = "rgba(15, 23, 42, 0.75)"
            ctx.beginPath()
            ctx.roundRect(10, row_y, w - 20, 18, 4)
            ctx.fill()
            ctx.strokeStyle = "rgba(56, 189, 248, 0.2)"
            ctx.stroke()

            ctx.fillStyle = "#64748B"
            ctx.font = "8px monospace"
            ctx.textAlign = "left"
            ctx.fillText("›", 16, row_y + 12)

            ctx.fillStyle = color
            ctx.font = "bold 9px monospace"
            ctx.fillText(text, 28, row_y + 12)

        # 4. Scanning Parse Beam
        ctx.strokeStyle = "rgba(56, 189, 248, 0.85)"
        ctx.lineWidth = 1.5
        ctx.beginPath()
        ctx.moveTo(12, self.scan_line_y)
        ctx.lineTo(w - 12, self.scan_line_y)
        ctx.stroke()

        # 5. Bottom Generation Telemetry Box
        bot_y = 135
        ctx.fillStyle = "#0F172A"
        ctx.beginPath()
        ctx.roundRect(10, bot_y, w - 20, 94, 8)
        ctx.fill()
        ctx.strokeStyle = "#1E293B"
        ctx.lineWidth = 1
        ctx.stroke()

        # Telemetry Labels
        ctx.fillStyle = "#94A3B8"
        ctx.font = "8px system-ui, sans-serif"
        ctx.textAlign = "left"
        ctx.fillText("TOKENS PARSED", 18, bot_y + 16)
        ctx.fillText("TARGETS", 18, bot_y + 40)
        ctx.fillText("HEADER SOT", 18, bot_y + 64)

        ctx.fillStyle = "#F8FAFC"
        ctx.font = "bold 11px system-ui, monospace"
        ctx.textAlign = "right"
        ctx.fillText(f"{self.tokens_parsed:,}", w - 18, bot_y + 16)
        ctx.fillStyle = "#818CF8"
        ctx.font = "bold 9px system-ui, monospace"
        ctx.fillText("CPython · MP · CP", w - 18, bot_y + 40)
        ctx.fillStyle = "#34D399"
        ctx.fillText("LVGL v9.2.2 C", w - 18, bot_y + 64)

        # Progress bar
        ctx.fillStyle = "#1E293B"
        ctx.beginPath()
        ctx.roundRect(18, bot_y + 76, w - 36, 6, 3)
        ctx.fill()
        ctx.fillStyle = "#38BDF8"
        prog_w = int((w - 36) * ((self.tokens_parsed % 500) / 500.0))
        ctx.beginPath()
        ctx.roundRect(18, bot_y + 76, max(6, prog_w), 6, 3)
        ctx.fill()

        if hasattr(self.drv, "show"):
            self.drv.show()


_ast_app = None


def main(canvas_id="hero_canvas"):
    global _ast_app
    print(f"Initializing PyDevices AST Parser on canvas '{canvas_id}'...")
    _ast_app = AstParserHero(canvas_id, size=240)
    print("PyDevices AST Parser running successfully!")


if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "hero_canvas"
    main(cid)
