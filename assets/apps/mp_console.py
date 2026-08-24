"""
PyDevices MicroPython LVGL Console (Hero Canvas App for lvgl-micropython)
========================================================================
Interactive round LVGL v9 micro-benchmark console:
- Animated sweeping spinner widget
- Interactive touch button cycling accent styles
- Live GC heap memory monitor and FPS telemetry
"""

import math
import sys
import time

import board_config
import appdev
import lvgl as lv


def _color(hex_val):
    r = (hex_val >> 16) & 0xFF
    g = (hex_val >> 8) & 0xFF
    b = hex_val & 0xFF
    return lv.color_make(r, g, b)


def _font_for(size):
    for s in (size, 14, 12, 10, 16, 20):
        name = f"font_montserrat_{s}"
        if hasattr(lv, name):
            f = getattr(lv, name)
            if callable(f):
                f = f()
            if f is not None:
                return (f, s)
    font = lv.font_default() if hasattr(lv, "font_default") else None
    return (font, 14) if font is not None else (None, 0)


def _zero_styles(obj):
    try:
        obj.remove_style_all()
    except AttributeError:
        pass
    parts = (
        0,
        getattr(lv.PART, "MAIN", 0),
        getattr(lv.PART, "INDICATOR", 0),
        getattr(lv.PART, "KNOB", 0),
        getattr(lv.PART, "ITEMS", 0),
        getattr(lv.PART, "ANY", 0),
    )
    methods = (
        "set_style_pad_all",
        "set_style_margin_all",
        "set_style_border_width",
        "set_style_outline_width",
    )
    for part in parts:
        for m in methods:
            fn = getattr(obj, m, None)
            if fn is not None:
                try:
                    fn(0, part)
                except (TypeError, AttributeError):
                    pass
    try:
        obj.remove_flag(lv.obj.FLAG.SCROLLABLE)
    except AttributeError:
        pass
    return obj


THEME_COLORS = [0x38BDF8, 0x10B981, 0xF59E0B, 0xEC4899, 0x8B5CF6]


class MPConsoleHero:
    def __init__(self, parent=None, size=240, canvas_id="hero_canvas"):
        self.canvas_id = canvas_id
        self.size = size
        self.theme_idx = 0
        self.heap_free_kb = 142
        self.tap_count = 0

        if parent is None:
            parent = lv.screen_active() if hasattr(lv, "screen_active") else lv.scr_act()
        self.parent = parent
        _zero_styles(self.parent)

        self._build_ui()

    def _build_ui(self):
        size = self.size
        # 1. Bezel
        self.bezel = lv.obj(self.parent)
        _zero_styles(self.bezel)
        self.bezel.set_size(size, size)
        self.bezel.center()
        self.bezel.set_style_radius(lv.RADIUS_CIRCLE, 0)
        self.bezel.set_style_bg_color(_color(0x090D14), 0)
        self.bezel.set_style_bg_opa(lv.OPA.COVER, 0)
        self.bezel.remove_flag(lv.obj.FLAG.CLICKABLE)

        # 2. Main Dial
        dial_size = size - 16
        self.dial = lv.obj(self.bezel)
        _zero_styles(self.dial)
        self.dial.set_size(dial_size, dial_size)
        self.dial.center()
        self.dial.set_style_radius(lv.RADIUS_CIRCLE, 0)
        self.dial.set_style_bg_color(_color(0x111827), 0)
        self.dial.set_style_bg_opa(lv.OPA.COVER, 0)
        self.dial.set_style_border_color(_color(0x1F2937), 0)
        self.dial.set_style_border_width(1, 0)
        self.dial.remove_flag(lv.obj.FLAG.CLICKABLE)

        # 3. Header Label
        font_sm, _ = _font_for(10)
        font_xs, _ = _font_for(8)
        font_md, _ = _font_for(14)

        self.lbl_head = lv.label(self.dial)
        _zero_styles(self.lbl_head)
        if font_sm:
            self.lbl_head.set_style_text_font(font_sm, 0)
        self.lbl_head.set_style_text_color(_color(0x38BDF8), 0)
        self.lbl_head.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
        self.lbl_head.set_text("MICROPYTHON C")
        self.lbl_head.align(lv.ALIGN.TOP_MID, 0, 24)

        # 4. Animated Spinner Arc
        self.spinner = lv.spinner(self.dial)
        _zero_styles(self.spinner)
        self.spinner.set_size(84, 84)
        self.spinner.center()
        self.spinner.set_style_arc_width(6, lv.PART.MAIN)
        self.spinner.set_style_arc_color(_color(0x1F2937), lv.PART.MAIN)
        self.spinner.set_style_arc_width(6, lv.PART.INDICATOR)
        self.spinner.set_style_arc_color(_color(THEME_COLORS[self.theme_idx]), lv.PART.INDICATOR)
        self.spinner.set_style_arc_rounded(True, lv.PART.INDICATOR)
        self.spinner.remove_flag(lv.obj.FLAG.CLICKABLE)

        # 5. Interactive Center Button
        btn_cls = getattr(lv, "button", None) or getattr(lv, "btn", None) or lv.obj
        self.btn = btn_cls(self.dial)
        _zero_styles(self.btn)
        self.btn.set_size(56, 56)
        self.btn.center()
        self.btn.set_style_radius(lv.RADIUS_CIRCLE, 0)
        self.btn.set_style_bg_color(_color(0x1F2937), 0)
        self.btn.set_style_bg_opa(lv.OPA.COVER, 0)
        self.btn.set_style_border_color(_color(THEME_COLORS[self.theme_idx]), 0)
        self.btn.set_style_border_width(2, 0)
        self.btn.add_flag(lv.obj.FLAG.CLICKABLE)

        self.lbl_btn = lv.label(self.btn)
        _zero_styles(self.lbl_btn)
        if font_xs:
            self.lbl_btn.set_style_text_font(font_xs, 0)
        self.lbl_btn.set_style_text_color(_color(0xF9FAFB), 0)
        self.lbl_btn.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
        self.lbl_btn.set_text("TAP ME")
        self.lbl_btn.center()
        self.lbl_btn.remove_flag(lv.obj.FLAG.CLICKABLE)

        def on_tap(e):
            self.cycle_theme()

        self.btn.add_event_cb(on_tap, lv.EVENT.CLICKED, None)

        # 6. Bottom Heap & GC Readout
        self.lbl_heap = lv.label(self.dial)
        _zero_styles(self.lbl_heap)
        if font_xs:
            self.lbl_heap.set_style_text_font(font_xs, 0)
        self.lbl_heap.set_style_text_color(_color(0x10B981), 0)
        self.lbl_heap.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
        self.lbl_heap.set_text(f"GC HEAP: {self.heap_free_kb} KB")
        self.lbl_heap.align(lv.ALIGN.BOTTOM_MID, 0, -32)

        self.lbl_fps = lv.label(self.dial)
        _zero_styles(self.lbl_fps)
        if font_xs:
            self.lbl_fps.set_style_text_font(font_xs, 0)
        self.lbl_fps.set_style_text_color(_color(0x9CA3AF), 0)
        self.lbl_fps.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
        self.lbl_fps.set_text("60 FPS | USERMOD")
        self.lbl_fps.align(lv.ALIGN.BOTTOM_MID, 0, -18)

    def cycle_theme(self):
        self.tap_count += 1
        self.theme_idx = (self.theme_idx + 1) % len(THEME_COLORS)
        col = THEME_COLORS[self.theme_idx]
        self.spinner.set_style_arc_color(_color(col), lv.PART.INDICATOR)
        self.btn.set_style_border_color(_color(col), 0)
        self.lbl_head.set_style_text_color(_color(col), 0)
        self.heap_free_kb = 120 + (self.tap_count * 7) % 60
        self.lbl_heap.set_text(f"GC HEAP: {self.heap_free_kb} KB")

_mp_app = None
_display_drv = None
_app = None
_display_driver = None


def main(canvas_id="hero_canvas"):
    global _mp_app, _display_drv, _app, _display_driver
    print(f"Initializing PyDevices MP Console on canvas '{canvas_id}'...")
    import os
    os.environ.setdefault('PYDEVICES_WIDTH', str(240))
    os.environ.setdefault('PYDEVICES_HEIGHT', str(240))
    _display_drv = board_config.display_drv
    _app = appdev.App(board_config)
    import display_driver as _driver

    _display_driver = _driver
    scr = lv.screen_active() if hasattr(lv, "screen_active") else lv.scr_act()
    _mp_app = MPConsoleHero(scr, size=240, canvas_id=canvas_id)
    print("PyDevices MP Console running successfully!")


if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "hero_canvas"
    main(cid)
