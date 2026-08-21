"""
PyDevices LVGL Smart Thermostat (Hero Canvas App for lvgl-python)
=================================================================
Modern LVGL v9 circular climate dial featuring an interactive target temperature arc,
touch-draggable knob, ambient status readout, and multi-state ECO leaf badge.
"""

import math
import sys
import time
import types

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

# Provide synthetic board_config for display_driver in browser / standalone canvas
if "board_config" not in sys.modules:
    bc = types.ModuleType("board_config")
    bc.display_drv = PSDisplay("hero_canvas", width=240, height=240)
    bc.get_events = bc.display_drv.get_events
    sys.modules["board_config"] = bc

import display_driver
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


class LVGLThermostat:
    def __init__(self, parent=None, size=240, canvas_id="hero_canvas"):
        self.canvas_id = canvas_id
        self.size = size
        self.r = size // 2
        self.target_temp = 72
        self.current_temp = 71.4
        self.humidity = 45
        self.is_dragging = False

        if parent is None:
            parent = lv.screen_active() if hasattr(lv, "screen_active") else lv.scr_act()
        self.parent = parent
        _zero_styles(self.parent)

        self._build_ui()
        self._bind_canvas_events()

    def _build_ui(self):
        size = self.size
        # 1. Outer Dark Bezel
        self.bezel = lv.obj(self.parent)
        _zero_styles(self.bezel)
        self.bezel.set_size(size, size)
        self.bezel.center()
        self.bezel.set_style_radius(lv.RADIUS_CIRCLE, 0)
        self.bezel.set_style_bg_color(_color(0x0A0D11), 0)
        self.bezel.set_style_bg_opa(lv.OPA.COVER, 0)
        self.bezel.remove_flag(lv.obj.FLAG.CLICKABLE)

        # 2. Main Dial Body
        dial_size = size - 16
        self.dial = lv.obj(self.bezel)
        _zero_styles(self.dial)
        self.dial.set_size(dial_size, dial_size)
        self.dial.center()
        self.dial.set_style_radius(lv.RADIUS_CIRCLE, 0)
        self.dial.set_style_bg_color(_color(0x131A22), 0)
        self.dial.set_style_bg_opa(lv.OPA.COVER, 0)
        self.dial.set_style_border_color(_color(0x232D3A), 0)
        self.dial.set_style_border_width(1, 0)
        self.dial.remove_flag(lv.obj.FLAG.CLICKABLE)

        # 3. Interactive Temperature Arc (range: 50 to 90 F)
        arc_size = dial_size - 18
        self.arc = lv.arc(self.dial)
        _zero_styles(self.arc)
        self.arc.set_size(arc_size, arc_size)
        self.arc.center()
        self.arc.set_range(50, 90)
        self.arc.set_value(self.target_temp)
        self.arc.set_bg_angles(135, 45)
        self.arc.set_mode(lv.arc.MODE.NORMAL)
        self.arc.add_flag(lv.obj.FLAG.CLICKABLE)

        # Arc Background Track
        self.arc.set_style_arc_width(8, lv.PART.MAIN)
        self.arc.set_style_arc_color(_color(0x1E293B), lv.PART.MAIN)
        self.arc.set_style_arc_rounded(True, lv.PART.MAIN)

        # Arc Active Indicator (Warm Amber/Orange)
        self.arc.set_style_arc_width(8, lv.PART.INDICATOR)
        self.arc.set_style_arc_color(_color(0xF54E00), lv.PART.INDICATOR)
        self.arc.set_style_arc_rounded(True, lv.PART.INDICATOR)

        # Arc Knob
        self.arc.set_style_bg_color(_color(0xFFF7ED), lv.PART.KNOB)
        self.arc.set_style_bg_opa(lv.OPA.COVER, lv.PART.KNOB)
        self.arc.set_style_radius(lv.RADIUS_CIRCLE, lv.PART.KNOB)
        self.arc.set_style_pad_all(4, lv.PART.KNOB)

        # Value Changed Event Callback
        def on_arc_change(event):
            val = self.arc.get_value()
            self.set_target_temp(val)

        self.arc.add_event_cb(on_arc_change, lv.EVENT.VALUE_CHANGED, None)

        # 4. Status Title Label
        self.lbl_status = lv.label(self.dial)
        _zero_styles(self.lbl_status)
        font_sm, _ = _font_for(10)
        if font_sm:
            self.lbl_status.set_style_text_font(font_sm, 0)
        self.lbl_status.set_style_text_color(_color(0xF54E00), 0)
        self.lbl_status.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
        self.lbl_status.set_text("HEATING TO")
        self.lbl_status.align(lv.ALIGN.TOP_MID, 0, 38)
        self.lbl_status.remove_flag(lv.obj.FLAG.CLICKABLE)

        # 5. Large Target Temperature Display
        self.lbl_target = lv.label(self.dial)
        _zero_styles(self.lbl_target)
        font_lg, _ = _font_for(20)
        if font_lg:
            self.lbl_target.set_style_text_font(font_lg, 0)
        self.lbl_target.set_style_text_color(_color(0xF8FAFC), 0)
        self.lbl_target.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
        self.lbl_target.set_text(f"{self.target_temp}°")
        self.lbl_target.align(lv.ALIGN.CENTER, 0, -6)
        self.lbl_target.remove_flag(lv.obj.FLAG.CLICKABLE)

        # 6. Current Ambient Temperature Subtext
        self.lbl_current = lv.label(self.dial)
        _zero_styles(self.lbl_current)
        if font_sm:
            self.lbl_current.set_style_text_font(font_sm, 0)
        self.lbl_current.set_style_text_color(_color(0x94A3B8), 0)
        self.lbl_current.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
        self.lbl_current.set_text(f"INSIDE {self.current_temp:.1f}°")
        self.lbl_current.align(lv.ALIGN.BOTTOM_MID, 0, -42)
        self.lbl_current.remove_flag(lv.obj.FLAG.CLICKABLE)

        # 7. ECO Badge Pill
        self.pill = lv.obj(self.dial)
        _zero_styles(self.pill)
        self.pill.set_size(68, 18)
        self.pill.align(lv.ALIGN.BOTTOM_MID, 0, -18)
        self.pill.set_style_radius(9, 0)
        self.pill.set_style_bg_color(_color(0x064E3B), 0)
        self.pill.set_style_bg_opa(lv.OPA.COVER, 0)
        self.pill.set_style_border_color(_color(0x10B981), 0)
        self.pill.set_style_border_width(1, 0)
        self.pill.remove_flag(lv.obj.FLAG.CLICKABLE)

        self.lbl_eco = lv.label(self.pill)
        _zero_styles(self.lbl_eco)
        font_xs, _ = _font_for(8)
        if font_xs:
            self.lbl_eco.set_style_text_font(font_xs, 0)
        self.lbl_eco.set_style_text_color(_color(0x34D399), 0)
        self.lbl_eco.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
        self.lbl_eco.set_text("ECO LEAF")
        self.lbl_eco.center()
        self.lbl_eco.remove_flag(lv.obj.FLAG.CLICKABLE)

    def set_target_temp(self, val):
        val = int(max(50, min(90, val)))
        self.target_temp = val
        self.arc.set_value(val)
        self.lbl_target.set_text(f"{val}°")

    def _bind_canvas_events(self):
        if not document:
            return
        canvas = document.getElementById(self.canvas_id)
        if not canvas:
            return

        def get_temp_from_event(event):
            rect = canvas.getBoundingClientRect()
            px = event.clientX - rect.left - rect.width / 2
            py = event.clientY - rect.top - rect.height / 2
            dist = math.sqrt(px * px + py * py)
            if dist < 30 or dist > 115:
                return None
            ang = (math.degrees(math.atan2(py, px)) + 360.0) % 360.0
            # Arc spans from 135 deg to 405 deg (45 deg) = 270 deg range
            rel_ang = (ang - 135.0) % 360.0
            if rel_ang > 270.0:
                rel_ang = 0.0 if rel_ang > 315.0 else 270.0
            temp = 50 + int((rel_ang / 270.0) * 40)
            return temp

        def on_pointer_down(event):
            t = get_temp_from_event(event)
            if t is not None:
                self.is_dragging = True
                self.set_target_temp(t)

        def on_pointer_move(event):
            if not self.is_dragging:
                return
            t = get_temp_from_event(event)
            if t is not None:
                self.set_target_temp(t)

        def on_pointer_up(event):
            self.is_dragging = False

        self._p_down = create_proxy(on_pointer_down)
        self._p_move = create_proxy(on_pointer_move)
        self._p_up = create_proxy(on_pointer_up)

        canvas.addEventListener("pointerdown", self._p_down)
        window.addEventListener("pointermove", self._p_move)
        window.addEventListener("pointerup", self._p_up)


_thermostat_app = None


def main(canvas_id="hero_canvas"):
    global _thermostat_app
    print(f"Initializing PyDevices LVGL Thermostat on canvas '{canvas_id}'...")

    scr = lv.screen_active() if hasattr(lv, "screen_active") else lv.scr_act()
    _thermostat_app = LVGLThermostat(scr, size=240, canvas_id=canvas_id)
    print("PyDevices LVGL Thermostat running successfully!")


if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "hero_canvas"
    main(cid)
