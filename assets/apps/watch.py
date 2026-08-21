# SPDX-FileCopyrightText: 2026 PyDevices / Brad Barnett
#
# SPDX-License-Identifier: MIT
"""
PyDevices Hybrid Smartwatch — 240x240 LVGL v9 watch face for hero canvas.

Features:
- Self-rendered circular metallic bezel and casing
- Dark sunray/carbon watch dial with Roman hour numerals and 60-minute tick ring
- High-precision dauphine analog hour & minute hands
- Continuous sweeping brand amber/orange seconds hand (~30 FPS)
- Central/lower digital time readout (HH:MM:SS) and date badge (Day, Mon DD)
- Zero board_config dependency (uses PSDisplay + display_driver directly)
"""

import math
import sys
import time
import types

try:
    from js import Date as _JSDate
except ImportError:
    _JSDate = None

from displaydev.psdisplay import PSDisplay

# Provide synthetic board_config for display_driver in browser / standalone canvas
if "board_config" not in sys.modules:
    bc = types.ModuleType("board_config")
    bc.display_drv = PSDisplay("hero_canvas", width=240, height=240)
    sys.modules["board_config"] = bc

import display_driver
import lvgl as lv


def _color(rgb):
    return lv.color_hex(rgb)


def _font_for(size):
    for points in (48, 40, 36, 32, 28, 24, 22, 20, 18, 16, 14, 12, 10):
        if points <= size:
            font = getattr(lv, "font_montserrat_%d" % points, None)
            if font is not None:
                return font, points
    font = getattr(lv, "font_montserrat_14", None)
    return (font, 14) if font is not None else (None, 0)


def _set_scaled_font(label, target_size):
    font, points = _font_for(max(1, int(target_size)))
    if font is not None:
        label.set_style_text_font(font, 0)
    scale = max(128, min(640, round(256 * target_size / max(1, points))))
    if scale != 256 and points > 0:
        try:
            label.set_style_transform_scale(scale, 0)
        except AttributeError:
            pass


def _plain(obj):
    obj.set_style_border_width(0, 0)
    obj.set_style_pad_all(0, 0)
    obj.set_style_bg_opa(lv.OPA.TRANSP, 0)
    try:
        obj.remove_flag(lv.obj.FLAG.SCROLLABLE)
    except AttributeError:
        pass


def _local_time():
    """Return (hour, minute, second, millis, day_name, month_name, day_num)."""
    if _JSDate is not None:
        now = _JSDate.new()
        hour = int(now.getHours())
        minute = int(now.getMinutes())
        second = int(now.getSeconds())
        millis = int(now.getMilliseconds())
        days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
        months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
        day_name = days[int(now.getDay())]
        month_name = months[int(now.getMonth())]
        day_num = int(now.getDate())
        return hour, minute, second, millis, day_name, month_name, day_num
    else:
        t = time.localtime()
        millis = int((time.time() % 1.0) * 1000)
        days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
        day_name = days[t[6]]
        month_name = months[t[1] - 1]
        return t[3], t[4], t[5], millis, day_name, month_name, t[2]


class PyDevicesWatch:
    def __init__(self, parent, size=240):
        self.parent = parent
        self.size = size
        self._styles = []
        self._build_watch()

    def _line(self, parent, color, width):
        line = lv.line(parent)
        style = lv.style_t()
        style.init()
        style.set_line_color(_color(color))
        style.set_line_width(width)
        style.set_line_rounded(True)
        line.add_style(style, 0)
        self._styles.append(style)
        return line

    def _build_watch(self):
        size = self.size
        dial_size = int(size * 0.916)
        r = dial_size // 2

        # 1. Base Screen Layer
        self.parent.set_style_bg_color(_color(0x0A0D10), 0)
        self.parent.set_style_bg_opa(lv.OPA.COVER, 0)
        self.parent.set_style_pad_all(0, 0)
        try:
            self.parent.remove_flag(lv.obj.FLAG.SCROLLABLE)
        except AttributeError:
            pass

        # 2. Outer Watch Bezel / Casing
        self.bezel = lv.obj(self.parent)
        self.bezel.set_size(size, size)
        self.bezel.center()
        self.bezel.set_style_radius(lv.RADIUS_CIRCLE, 0)
        self.bezel.set_style_bg_color(_color(0x1E242B), 0)
        self.bezel.set_style_bg_grad_color(_color(0x101418), 0)
        self.bezel.set_style_bg_grad_dir(lv.GRAD_DIR.VER, 0)
        self.bezel.set_style_border_color(_color(0x3B444E), 0)
        self.bezel.set_style_border_width(max(2, int(size * 0.017)), 0)
        self.bezel.set_style_pad_all(0, 0)
        _plain(self.bezel)

        # 3. Inner Metallic Bezel Ring with Subtle Amber Accent
        inner_bezel_size = int(size * 0.95)
        self.bezel_ring = lv.obj(self.bezel)
        self.bezel_ring.set_size(inner_bezel_size, inner_bezel_size)
        self.bezel_ring.center()
        self.bezel_ring.set_style_radius(lv.RADIUS_CIRCLE, 0)
        self.bezel_ring.set_style_bg_color(_color(0x151A20), 0)
        self.bezel_ring.set_style_border_color(_color(0xF54E00), 0)
        self.bezel_ring.set_style_border_width(1, 0)
        self.bezel_ring.set_style_border_opa(lv.OPA._60, 0)
        _plain(self.bezel_ring)

        # 4. Dial Face (Underlay for background elements)
        self.face = lv.obj(self.bezel_ring)
        self.face.set_size(dial_size, dial_size)
        self.face.center()
        self.face.set_style_radius(lv.RADIUS_CIRCLE, 0)
        self.face.set_style_bg_color(_color(0x0E1115), 0)
        self.face.set_style_bg_grad_color(_color(0x181F26), 0)
        self.face.set_style_bg_grad_dir(lv.GRAD_DIR.VER, 0)
        self.face.set_style_border_color(_color(0x28323D), 0)
        self.face.set_style_border_width(1, 0)
        _plain(self.face)

        # 5. Roman Hour Numerals (XII, III, VI, IX) - Created on dial face
        numerals = {0: "XII", 3: "III", 6: "VI", 9: "IX"}
        num_radius = int(r * 0.76)
        num_font_size = int(dial_size * 0.065)
        for hour, label_text in numerals.items():
            lbl = lv.label(self.face)
            lbl.set_text(label_text)
            lbl.set_style_text_color(_color(0xE2E8F0), 0)
            _set_scaled_font(lbl, num_font_size)
            angle = math.radians(hour * 30 - 90)
            nx = int(math.cos(angle) * num_radius)
            ny = int(math.sin(angle) * num_radius)
            lbl.align(lv.ALIGN.CENTER, nx, ny)

        # 6. Brand Label (Top Half) - Calculated anchor point
        brand_y = -int(r * 0.38)
        self.brand_lbl = lv.label(self.face)
        self.brand_lbl.set_text("PYDEVICES")
        self.brand_lbl.set_style_text_color(_color(0xF54E00), 0)
        _set_scaled_font(self.brand_lbl, int(dial_size * 0.05))
        self.brand_lbl.align(lv.ALIGN.CENTER, 0, brand_y)

        # 7. Digital Readout Sub-Dial (Lower Half) - Created on dial face behind hands
        pill_w = int(dial_size * 0.46)
        pill_h = int(dial_size * 0.16)
        pill_y = int(r * 0.42)

        self.pill = lv.obj(self.face)
        self.pill.set_size(pill_w, pill_h)
        self.pill.align(lv.ALIGN.CENTER, 0, pill_y)
        self.pill.set_style_radius(max(4, int(pill_h * 0.18)), 0)
        self.pill.set_style_bg_color(_color(0x080B0E), 0)
        self.pill.set_style_bg_opa(lv.OPA._90, 0)
        self.pill.set_style_border_color(_color(0x28333E), 0)
        self.pill.set_style_border_width(1, 0)
        self.pill.set_style_pad_all(0, 0)
        try:
            self.pill.remove_flag(lv.obj.FLAG.SCROLLABLE)
        except AttributeError:
            pass

        time_y = -int(pill_h * 0.18)
        self.digital_time = lv.label(self.pill)
        self.digital_time.set_text("00:00:00")
        self.digital_time.set_style_text_color(_color(0xF8FAFC), 0)
        _set_scaled_font(self.digital_time, int(pill_h * 0.38))
        self.digital_time.align(lv.ALIGN.CENTER, 0, time_y)

        date_y = int(pill_h * 0.24)
        self.digital_date = lv.label(self.pill)
        self.digital_date.set_text("FRI  OCT 24")
        self.digital_date.set_style_text_color(_color(0x94A3B8), 0)
        _set_scaled_font(self.digital_date, int(pill_h * 0.28))
        self.digital_date.align(lv.ALIGN.CENTER, 0, date_y)

        # 8. Scale for Ticks & Analog Needles - Created AFTER dial & digital sub-dial
        # This guarantees that the tick ring and all rotating hands draw in FRONT of the digital display!
        self.scale = lv.scale(self.face)
        self.scale.set_size(dial_size, dial_size)
        self.scale.center()
        _plain(self.scale)
        self.scale.set_mode(lv.scale.MODE.ROUND_INNER)
        self.scale.set_range(0, 3600)
        self.scale.set_angle_range(360)
        self.scale.set_rotation(270)
        self.scale.set_total_tick_count(60)
        self.scale.set_major_tick_every(5)
        self.scale.set_label_show(False)

        # Minor ticks (minutes)
        minor_style = lv.style_t()
        minor_style.init()
        minor_style.set_line_color(_color(0x64748B))
        minor_style.set_line_width(1)
        minor_style.set_length(max(3, int(r * 0.05)))
        self.scale.add_style(minor_style, lv.PART.ITEMS)

        # Major ticks (hours)
        major_style = lv.style_t()
        major_style.init()
        major_style.set_line_color(_color(0xF54E00))
        major_style.set_line_width(max(2, int(dial_size * 0.009)))
        major_style.set_length(max(6, int(r * 0.09)))
        major_style.set_line_rounded(True)
        self.scale.add_style(major_style, lv.PART.INDICATOR)
        self._styles.extend([minor_style, major_style])

        # 9. Analog Hands (attached to self.scale)
        self.hands = {"hour": [], "minute": [], "second": []}

        # Hour hand layers (dark border + bright silver core + gold ridge)
        hour_len = int(r * 0.58)
        self.hands["hour"].append((self._line(self.scale, 0x050709, max(4, int(dial_size * 0.025))), hour_len + 1))
        self.hands["hour"].append((self._line(self.scale, 0xE2E8F0, max(3, int(dial_size * 0.018))), int(hour_len * 0.85)))
        self.hands["hour"].append((self._line(self.scale, 0xF54E00, 1), hour_len))

        # Minute hand layers
        min_len = int(r * 0.82)
        self.hands["minute"].append((self._line(self.scale, 0x050709, max(3, int(dial_size * 0.018))), min_len + 1))
        self.hands["minute"].append((self._line(self.scale, 0xF8FAFC, max(2, int(dial_size * 0.010))), int(min_len * 0.88)))
        self.hands["minute"].append((self._line(self.scale, 0xF54E00, 1), min_len))

        # Second hand (sweeping brand orange/amber needle + dark outline)
        sec_len = int(r * 0.90)
        self.hands["second"].append((self._line(self.scale, 0x1A0802, max(2, int(dial_size * 0.012))), sec_len + 1))
        self.hands["second"].append((self._line(self.scale, 0xF54E00, 1), sec_len))

        # 10. Center Hub Cap - Created on top of the hands
        hub_size = max(10, int(dial_size * 0.065))
        self.hub = lv.obj(self.face)
        self.hub.set_size(hub_size, hub_size)
        self.hub.center()
        self.hub.set_style_radius(lv.RADIUS_CIRCLE, 0)
        self.hub.set_style_bg_color(_color(0xF54E00), 0)
        self.hub.set_style_bg_grad_color(_color(0x9A3412), 0)
        self.hub.set_style_bg_grad_dir(lv.GRAD_DIR.VER, 0)
        self.hub.set_style_border_color(_color(0xFFF7ED), 0)
        self.hub.set_style_border_width(1, 0)
        _plain(self.hub)

        # First update and timer (~30 FPS: 33ms)
        self.update_time()
        self._timer = lv.timer_create(lambda _t: self.update_time(), 33, None)

    def update_time(self):
        hour, minute, second, millis, day_name, month_name, day_num = _local_time()

        # Update analog needles (range: 0..3600)
        sec_val = int((second + millis / 1000.0) * 60) % 3600
        min_val = int((minute + second / 60.0) * 60) % 3600
        hour_val = int(((hour % 12) + minute / 60.0 + second / 3600.0) * 300) % 3600

        for hand, length in self.hands["hour"]:
            self.scale.set_line_needle_value(hand, length, hour_val)
        for hand, length in self.hands["minute"]:
            self.scale.set_line_needle_value(hand, length, min_val)
        for hand, length in self.hands["second"]:
            self.scale.set_line_needle_value(hand, length, sec_val)

        # Update digital readout
        time_str = f"{hour:02d}:{minute:02d}:{second:02d}"
        date_str = f"{day_name}  {month_name} {day_num:02d}"
        self.digital_time.set_text(time_str)
        self.digital_date.set_text(date_str)


_watch_app = None


def main(canvas_id="hero_canvas"):
    global _watch_app
    print(f"Initializing PyDevices LVGL Smartwatch on canvas '{canvas_id}'...")

    scr = lv.screen_active() if hasattr(lv, "screen_active") else lv.scr_act()
    _watch_app = PyDevicesWatch(scr, size=240)
    print("PyDevices LVGL Smartwatch running successfully!")


if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "hero_canvas"
    main(cid)
