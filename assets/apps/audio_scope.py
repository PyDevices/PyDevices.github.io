"""
PyDevices Audio Rack (Hero Canvas App for audioif)
==================================================
Studio mixer + oscilloscope: four CircuitPython-compatible module strips
(synthio, mixer, effects, mp3) feeding a stereo PCM trace. Visual-only —
the wasm hero host does not load native audioif usermods.
"""

import math

from board_config import display_drv
import board_config
import appdev
import events
import pygraphics

app = appdev.App(board_config)


def _color(value):
    value = value.lstrip("#")
    r, g, b = int(value[:2], 16), int(value[2:4], 16), int(value[4:], 16)
    return (r & 0xF8) << 8 | (g & 0xFC) << 3 | b >> 3


def _text(display, value, x, y, color, align="left"):
    value = str(value)
    if align == "right":
        x -= len(value) * 8
    elif align == "center":
        x -= len(value) * 4
    pygraphics.text8(display, value, int(x), int(y) - 8, _color(color))


_CHANNELS = (
    ("OSC", "#38BDF8", 1.00, 220.0),
    ("MIX", "#10B981", 0.72, 440.0),
    ("FX", "#A78BFA", 0.48, 660.0),
    ("MP3", "#F59E0B", 0.36, 110.0),
)


class AudioScopeHero:
    def __init__(self, size=240):
        self.size = size
        self.w = size
        self.h = size
        self.drv = display_drv
        self.t = 0.0
        self.patch = 0
        self.peak_l = 0.2
        self.peak_r = 0.2
        self.draw()
        app.on(events.MOUSEBUTTONDOWN, self._on_pointer)
        self._tick_subscription = app.every(33, self._timer_tick)

    def _timer_tick(self, _timer):
        self.tick()

    def _on_pointer(self, _event):
        self.patch = (self.patch + 1) % 3

    def _wave(self, x, freq, harm):
        phase = (x / self.w) * freq * 2.0 * math.pi + self.t
        if self.patch == 0:
            return math.sin(phase) + 0.35 * math.sin(phase * 2) * harm
        if self.patch == 1:
            return (1.0 if math.sin(phase) >= 0 else -1.0) * 0.85
        tri = 2.0 * abs((phase / math.pi) % 2.0 - 1.0) - 1.0
        return tri

    def tick(self):
        self.t += 0.22
        mix = 0.55 + 0.35 * math.sin(self.t * 0.7)
        self.peak_l = 0.25 + 0.7 * abs(math.sin(self.t * 1.3)) * mix
        self.peak_r = 0.25 + 0.7 * abs(math.cos(self.t * 1.1)) * mix
        self.draw()

    def draw(self):
        display = self.drv
        w, h = self.w, self.h
        display.fill(_color("#07090D"))

        for gx in range(16, w, 16):
            pygraphics.vline(display, gx, 28, 92, _color("#121826"))
        for gy in range(32, 120, 16):
            pygraphics.hline(display, 0, gy, w, _color("#121826"))

        display.fill_rect(0, 0, w, 28, _color("#0B1220"))
        pygraphics.hline(display, 0, 28, w, _color("#1E293B"))
        _text(display, "AUDIO RACK", 8, 18, "#F54E00")
        mode = ("SINE", "SQUARE", "TRI")[self.patch]
        _text(display, f"48k  {mode}", w - 8, 18, "#94A3B8", "right")

        mid_y = 74
        prev = mid_y
        for x in range(0, w):
            acc = 0.0
            for _name, _col, gain, freq in _CHANNELS:
                acc += self._wave(x, freq / 220.0, gain) * gain * 0.28
            y = int(mid_y - acc * 28)
            y = 32 if y < 32 else (118 if y > 118 else y)
            pygraphics.vline(display, x, min(y, mid_y), abs(y - mid_y) + 1, _color("#0E3A4A"))
            if x:
                pygraphics.line(display, x - 1, prev, x, y, _color("#22D3EE"))
            prev = y
        pygraphics.hline(display, 0, mid_y, w, _color("#1E3A4A"))

        display.fill_rect(0, 122, w, 82, _color("#0B1220"))
        pygraphics.hline(display, 0, 122, w, _color("#1E293B"))

        strip_w = w // 4
        meter_h = 46
        meter_top = 130
        for i, (name, color, gain, _freq) in enumerate(_CHANNELS):
            cx = i * strip_w + strip_w // 2
            level = gain * (0.45 + 0.55 * abs(math.sin(self.t * (1.1 + i * 0.35))))
            bar_h = int(meter_h * level)
            bx = cx - 7
            display.fill_rect(bx, meter_top, 14, meter_h, _color("#111827"))
            fill_y = meter_top + meter_h - bar_h
            display.fill_rect(bx, fill_y, 14, bar_h, _color(color))
            cap = meter_top + int(meter_h * (1.0 - min(1.0, level + 0.08)))
            pygraphics.hline(display, bx, cap, 14, _color("#F8FAFC"))
            _text(display, name, cx, 196, color, "center")
            if i:
                pygraphics.vline(display, i * strip_w, 122, 82, _color("#1E293B"))

        display.fill_rect(0, 204, w, 36, _color("#0B1220"))
        pygraphics.hline(display, 0, 204, w, _color("#1E293B"))
        l_w = int((w // 2 - 16) * self.peak_l)
        r_w = int((w // 2 - 16) * self.peak_r)
        _text(display, "L", 8, 226, "#64748B")
        display.fill_rect(20, 216, w // 2 - 28, 8, _color("#111827"))
        display.fill_rect(20, 216, max(2, l_w), 8, _color("#34D399"))
        _text(display, "R", w // 2 + 4, 226, "#64748B")
        rx = w // 2 + 16
        display.fill_rect(rx, 216, w // 2 - 28, 8, _color("#111827"))
        display.fill_rect(rx, 216, max(2, r_w), 8, _color("#FBBF24"))

        if hasattr(self.drv, "show"):
            self.drv.show()


_audio_scope_app = AudioScopeHero(size=min(display_drv.width, display_drv.height))
