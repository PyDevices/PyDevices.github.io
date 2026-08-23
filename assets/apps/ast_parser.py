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
from random import random, choice

import appdev
import events
from displaydev.wasmdisplay import WasmDisplay
import pygraphics


def _color(value):
    value = value.lstrip("#")
    red, green, blue = int(value[:2], 16), int(value[2:4], 16), int(value[4:], 16)
    return (red & 0xF8) << 8 | (green & 0xFC) << 3 | blue >> 3


def _text(display, value, x, y, color, align="left"):
    value = str(value)
    if align == "right":
        x -= len(value) * 8
    elif align == "center":
        x -= len(value) * 4
    pygraphics.text8(display, value, int(x), int(y) - 8, _color(color))


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

        self.drv = WasmDisplay(width=size, height=size, canvas_id=canvas_id)
        self.app = appdev.App(displays=(self.drv,), host_read=self.drv.get_events)

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

        self._tick_subscription = self.app.every(33, self._timer_tick)

    def _timer_tick(self, _timer):
        self.tick()

    def _bind_events(self):
        def on_pointer_down(_event):
            self.tokens_parsed += 42
            self.schemas_gen += 1
            tok, col = choice(C_TOKENS)
            self.log_lines.pop(0)
            self.log_lines.append((f"EMIT {tok}", col))
            self.draw()

        self.app.on(events.MOUSEBUTTONDOWN, on_pointer_down)

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
        display = self.drv
        w, h = self.w, self.h

        # 1. Dark Blueprint Bezel Background
        display.fill(_color("#070B12"))

        # Subtle Matrix Grid
        for gx in range(16, w, 20):
            pygraphics.vline(display, gx, 0, h, _color("#111827"))
        for gy in range(16, h, 20):
            pygraphics.hline(display, 0, gy, w, _color("#111827"))

        # 2. Header Bar
        display.fill_rect(0, 0, w, 26, _color("#0F172A"))
        pygraphics.hline(display, 0, 26, w, _color("#1E293B"))
        _text(display, "LVGL BINDINGS GEN", 10, 17, "#38BDF8")
        _text(display, f"AST: {self.schemas_gen}", w - 10, 17, "#10B981", "right")

        # 3. Token Matrix Window
        matrix_y = 32
        for i, (text, color) in enumerate(self.log_lines):
            row_y = matrix_y + i * 22
            # Terminal prompt pill
            pygraphics.round_rect(display, 10, row_y, w - 20, 18, 4, _color("#0F172A"), True)
            pygraphics.round_rect(display, 10, row_y, w - 20, 18, 4, _color("#164E63"))
            _text(display, ">", 16, row_y + 12, "#64748B")
            _text(display, text, 28, row_y + 12, color)

        # 4. Scanning Parse Beam
        pygraphics.hline(display, 12, int(self.scan_line_y), w - 24, _color("#38BDF8"))

        # 5. Bottom Generation Telemetry Box
        bot_y = 135
        pygraphics.round_rect(display, 10, bot_y, w - 20, 94, 8, _color("#0F172A"), True)
        pygraphics.round_rect(display, 10, bot_y, w - 20, 94, 8, _color("#1E293B"))

        # Telemetry Labels
        _text(display, "TOKENS PARSED", 18, bot_y + 16, "#94A3B8")
        _text(display, "TARGETS", 18, bot_y + 40, "#94A3B8")
        _text(display, "HEADER SOT", 18, bot_y + 64, "#94A3B8")
        _text(display, f"{self.tokens_parsed:,}", w - 18, bot_y + 16, "#F8FAFC", "right")
        _text(display, "CPython / MP / CP", w - 18, bot_y + 40, "#818CF8", "right")
        _text(display, "LVGL v9.2.2 C", w - 18, bot_y + 64, "#34D399", "right")

        # Progress bar
        pygraphics.round_rect(display, 18, bot_y + 76, w - 36, 6, 3, _color("#1E293B"), True)
        prog_w = int((w - 36) * ((self.tokens_parsed % 500) / 500.0))
        pygraphics.round_rect(display, 18, bot_y + 76, max(6, prog_w), 6, 3, _color("#38BDF8"), True)

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
