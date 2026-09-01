# SPDX-FileCopyrightText: 2026 PyDevices / Brad Barnett
#
# SPDX-License-Identifier: MIT
"""
PyDevices Signal Generator (Hero Canvas App for pydevices)
============================================================
A rotary-knob audio signal generator. Drag the knob to dial in a frequency
on a logarithmic (equal-octave) scale, tap the center hub to toggle the
tone on/off, and pick a waveform along the top. The only hero app with
sound -- pydevices' own hero, showing off `board_config.audio_out`
(appdev's audio stack) alongside LVGL.
"""

import math
import time

# hero-runtime.js already sets these to 480x480 in production; set them here
# too so this square-canvas app also renders correctly under bin/wasm.py's
# generic (default 320x480) local test harness.
from displaydev import env_set

env_set("PYDEVICES_WIDTH", "480")
env_set("PYDEVICES_HEIGHT", "480")

import display_driver  # wires LVGL display/input into the app
import lvgl as lv
from board_config import display_drv
from display_driver import app
import board_config
import synthio
import ulab.numpy as np

FREQ_MIN = 55.0  # A1 -- low end most laptop speakers can still reproduce
FREQ_MAX = 7040.0  # A8 -- top of the comfortably audible band
FREQ_DEFAULT = 440.0  # A4, concert pitch
OCTAVE_DEG = 180.0  # knob degrees per octave -- equal angle per octave
_ENCODER_STEP_DEG = 6.0  # knob rotation per encoder tick (30 ticks/octave)
_MIN_ANGLE = OCTAVE_DEG * math.log2(FREQ_MIN / FREQ_DEFAULT)
_MAX_ANGLE = OCTAVE_DEG * math.log2(FREQ_MAX / FREQ_DEFAULT)

_NOTE_NAMES = ("A", "A#", "B", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#")


def _note_name(freq):
    n = round(12.0 * math.log2(freq / FREQ_DEFAULT))
    octave = 4 + (n + 9) // 12
    return _NOTE_NAMES[n % 12], octave


# ---------------------------------------------------------------------------
# Signal synthesis -- a single live synthio.Note, played through the same
# audiodev.sample_out.AudioOut contract as pydevices-examples' piano.py
# (board_config.audio_out.play(synth) + attach(app)). Toggling the note
# on/off goes through synthio's own envelope (short attack/release) rather
# than a hand-rolled sample-ramp, so it stays click-free for free.
# ---------------------------------------------------------------------------

_TWO_PI = 2.0 * math.pi
_WAVE_TABLE_SIZE = 256
_WAVE_TABLE_AMPLITUDE = 28000  # headroom below int16 full scale


def _sine_table():
    return [
        int(_WAVE_TABLE_AMPLITUDE * math.sin(_TWO_PI * i / _WAVE_TABLE_SIZE))
        for i in range(_WAVE_TABLE_SIZE)
    ]


def _square_table():
    half = _WAVE_TABLE_SIZE // 2
    return [_WAVE_TABLE_AMPLITUDE] * half + [-_WAVE_TABLE_AMPLITUDE] * (_WAVE_TABLE_SIZE - half)


def _triangle_table():
    out = []
    for i in range(_WAVE_TABLE_SIZE):
        phase = i / _WAVE_TABLE_SIZE
        if phase < 0.25:
            v = phase * 4.0
        elif phase < 0.75:
            v = 2.0 - phase * 4.0
        else:
            v = phase * 4.0 - 4.0
        out.append(int(v * _WAVE_TABLE_AMPLITUDE))
    return out


def _saw_table():
    return [
        int((2.0 * i / _WAVE_TABLE_SIZE - 1.0) * _WAVE_TABLE_AMPLITUDE)
        for i in range(_WAVE_TABLE_SIZE)
    ]


_WAVES = (
    ("SIN", _sine_table),
    ("SQR", _square_table),
    ("TRI", _triangle_table),
    ("SAW", _saw_table),
)
_wave_table_cache = {}


def _wave_table(name):
    table = _wave_table_cache.get(name)
    if table is None:
        for label, make in _WAVES:
            if label == name:
                table = np.array(make(), dtype=np.int16)
                break
        _wave_table_cache[name] = table
    return table


class Oscillator:
    """One live synthio.Note. Envelope attack/release makes on/off click-free."""

    def __init__(self, out, amp=0.35):
        self.out = out
        self.amp = amp
        self._freq = FREQ_DEFAULT
        self._wave_name = "SIN"
        self.playing = False
        self._synth = None
        self._note = None
        self._ready = False

    @property
    def freq(self):
        return self._freq

    @freq.setter
    def freq(self, value):
        self._freq = value
        if self._note is not None:
            self._note.frequency = value

    @property
    def wave(self):
        return self._wave_name

    @wave.setter
    def wave(self, name):
        self._wave_name = name
        if self._note is not None:
            self._note.waveform = _wave_table(name)

    def _open(self):
        if self._ready:
            return True
        try:
            fmt = self.out.format
            self._synth = synthio.Synthesizer(
                sample_rate=fmt.rate,
                channel_count=fmt.channels,
                envelope=synthio.Envelope(
                    attack_time=0.03, decay_time=0.0, release_time=0.03, sustain_level=1.0
                ),
            )
            self.out.play(self._synth)
        except Exception:
            return False
        self._ready = True
        return True

    def start(self, app_):
        self.out.attach(app_)

    def set_playing(self, value):
        value = bool(value)
        if value == self.playing:
            return True
        if value:
            if not self._open():
                return False
            note = synthio.Note(
                frequency=self._freq,
                waveform=_wave_table(self._wave_name),
                amplitude=self.amp,
            )
            self._note = note
            self._synth.press(note)
        elif self._note is not None:
            self._synth.release(self._note)
            self._note = None
        self.playing = value
        return True


# ---------------------------------------------------------------------------
# LVGL styling helpers (same shape as the other LVGL hero apps)
# ---------------------------------------------------------------------------


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


def _zero_styles(obj):
    try:
        obj.remove_style_all()
    except AttributeError:
        pass
    try:
        obj.remove_flag(lv.obj.FLAG.SCROLLABLE)
    except AttributeError:
        pass
    return obj


def _clean_obj(parent):
    obj = lv.obj(parent)
    _zero_styles(obj)
    obj.set_style_pad_all(0, 0)
    obj.set_style_border_width(0, 0)
    obj.set_style_bg_opa(lv.OPA.TRANSP, 0)
    return obj


def _clean_label(parent, text, color, font_size):
    lbl = lv.label(parent)
    _zero_styles(lbl)
    font, _ = _font_for(font_size)
    if font is not None:
        lbl.set_style_text_font(font, 0)
    lbl.set_style_text_color(_color(color), 0)
    lbl.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
    lbl.set_text(text)
    return lbl


class SignalGenHero:
    def __init__(self, size=240):
        self.size = size
        self.cx = size // 2
        self.cy = int(size * 0.60)
        self.knob_r = int(size * 0.31)
        self.hub_r = int(size * 0.115)

        self.freq = FREQ_DEFAULT
        self.total_angle = 0.0
        self.wave_idx = 0
        self.playing = False
        self.last_interaction = time.time()

        self.osc = Oscillator(board_config.audio_out)

        scr = lv.screen_active() if hasattr(lv, "screen_active") else lv.scr_act()
        self.scr = scr
        self._build_background(scr)
        self._build_dial(scr)
        self._build_hub(scr)
        self._build_readout(scr)
        self._build_wave_buttons(scr)

        self._bind_events()
        self._update_readout()

        self.osc.start(app)
        app.every(60, self._idle_tick)

    # -- construction ------------------------------------------------

    def _build_background(self, scr):
        scr.set_style_bg_color(_color(0x0A0D10), 0)
        scr.set_style_bg_opa(lv.OPA.COVER, 0)
        scr.set_style_pad_all(0, 0)
        try:
            scr.set_style_margin_all(0, 0)
        except AttributeError:
            pass
        try:
            scr.remove_flag(lv.obj.FLAG.SCROLLABLE)
        except AttributeError:
            pass

    def _build_dial(self, scr):
        size, cx, cy, knob_r = self.size, self.cx, self.cy, self.knob_r

        # Static decorative bezel behind the knob -- depth, no interaction.
        bezel_d = knob_r * 2 + int(size * 0.05)
        bezel = _clean_obj(scr)
        bezel.set_size(bezel_d, bezel_d)
        bezel.set_pos(cx - bezel_d // 2, cy - bezel_d // 2)
        bezel.set_style_radius(lv.RADIUS_CIRCLE, 0)
        bezel.set_style_bg_color(_color(0x1B2129), 0)
        bezel.set_style_bg_grad_color(_color(0x07090B), 0)
        bezel.set_style_bg_grad_dir(lv.GRAD_DIR.VER, 0)
        bezel.set_style_bg_opa(lv.OPA.COVER, 0)
        bezel.set_style_border_color(_color(0x2A3441), 0)
        bezel.set_style_border_width(max(1, int(size * 0.006)), 0)

        # The rotating knob body -- a radial-gradient dome with a bright
        # brand-amber pointer bar and a knurled ring of grip dots, all as
        # children so they rotate together with the container.
        kd = knob_r * 2
        self.knob = _clean_obj(scr)
        self.knob.set_size(kd, kd)
        self.knob.set_pos(cx - knob_r, cy - knob_r)
        self.knob.set_style_radius(lv.RADIUS_CIRCLE, 0)
        self.knob.set_style_bg_color(_color(0x475467), 0)
        self.knob.set_style_bg_grad_color(_color(0x161B22), 0)
        self.knob.set_style_bg_grad_dir(lv.GRAD_DIR.RADIAL, 0)
        self.knob.set_style_bg_opa(lv.OPA.COVER, 0)
        self.knob.set_style_border_color(_color(0x64748B), 0)
        self.knob.set_style_border_width(max(1, int(size * 0.008)), 0)
        self.knob.set_style_transform_pivot_x(knob_r, 0)
        self.knob.set_style_transform_pivot_y(knob_r, 0)

        n_dots = 22
        dot_r = max(2, int(size * 0.011))
        ring_r = knob_r - dot_r - max(2, int(size * 0.012))
        for i in range(n_dots):
            ang = _TWO_PI * i / n_dots
            dx = int(math.cos(ang) * ring_r)
            dy = int(math.sin(ang) * ring_r)
            dot = _clean_obj(self.knob)
            dot.set_size(dot_r * 2, dot_r * 2)
            dot.set_style_radius(lv.RADIUS_CIRCLE, 0)
            dot.set_style_bg_color(_color(0x8291A3 if i % 2 == 0 else 0x222A34), 0)
            dot.set_style_bg_opa(lv.OPA.COVER, 0)
            dot.align(lv.ALIGN.CENTER, dx, dy)

        pw = max(3, int(size * 0.018))
        ph = int(knob_r * 0.46)
        self.pointer = _clean_obj(self.knob)
        self.pointer.set_size(pw, ph)
        self.pointer.set_style_radius(pw // 2, 0)
        self.pointer.set_style_bg_color(_color(0x22C7E2), 0)
        self.pointer.set_style_bg_opa(lv.OPA.COVER, 0)
        self.pointer.align(lv.ALIGN.TOP_MID, 0, int(knob_r * 0.14))

    def _build_hub(self, scr):
        hub_r = self.hub_r
        hd = hub_r * 2
        self.hub = _clean_obj(scr)
        self.hub.set_size(hd, hd)
        self.hub.set_pos(self.cx - hub_r, self.cy - hub_r)
        self.hub.set_style_radius(lv.RADIUS_CIRCLE, 0)
        self.hub.set_style_bg_color(_color(0x11161D), 0)
        self.hub.set_style_bg_opa(lv.OPA.COVER, 0)
        self.hub.set_style_border_color(_color(0x475569), 0)
        self.hub.set_style_border_width(max(1, int(self.size * 0.008)), 0)
        try:
            self.hub.add_flag(lv.obj.FLAG.CLICKABLE)
        except AttributeError:
            pass
        self.hub.add_event_cb(self._on_hub_click, lv.EVENT.CLICKED, None)

        self.hub_icon = _clean_label(self.hub, lv.SYMBOL.MUTE, 0x64748B, int(hub_r * 0.9))
        self.hub_icon.center()

    def _build_readout(self, scr):
        freq_font = int(self.size * 0.08)
        note_font = int(self.size * 0.045)
        bezel_top = self.cy - self.knob_r - int(self.size * 0.03)
        top = int(self.size * 0.14)  # just below the waveform button row
        self.freq_label = _clean_label(scr, "440 Hz", 0xF8FAFC, freq_font)
        self.freq_label.set_pos(0, top)
        self.freq_label.set_width(self.size)
        note_y = min(top + int(freq_font * 1.05), bezel_top - note_font)
        self.note_label = _clean_label(scr, "A4 - SIN", 0x94A3B8, note_font)
        self.note_label.set_pos(0, note_y)
        self.note_label.set_width(self.size)

    def _build_wave_buttons(self, scr):
        size = self.size
        n = len(_WAVES)
        bw, bh = int(size * 0.205), int(size * 0.105)
        gap = int(size * 0.017)
        total_w = bw * n + gap * (n - 1)
        x0 = self.cx - total_w // 2
        y0 = int(size * 0.025)
        self.wave_btns = []
        for i, (label, _fn) in enumerate(_WAVES):
            btn = _clean_obj(scr)
            btn.set_size(bw, bh)
            btn.set_pos(x0 + i * (bw + gap), y0)
            btn.set_style_radius(int(bh * 0.28), 0)
            btn.set_style_border_width(max(1, int(size * 0.004)), 0)
            try:
                btn.add_flag(lv.obj.FLAG.CLICKABLE)
            except AttributeError:
                pass
            lbl = _clean_label(btn, label, 0x94A3B8, int(bh * 0.55))
            lbl.center()
            btn.add_event_cb(lambda _e, idx=i: self._select_wave(idx), lv.EVENT.CLICKED, None)
            self.wave_btns.append((btn, lbl))
        self._select_wave(0, initial=True)

    # -- interaction ---------------------------------------------------

    def _bind_events(self):
        # A rotary encoder is a wheel gesture, not a drag: a real scroll
        # wheel and a two-finger trackpad swipe both arrive in the browser
        # as wheel events, and display_driver's VirtualDevices already fans
        # those into a real LVGL ENCODER indev (see EncoderInput / _encoder_cb
        # in display_driver.py) -- every indev it creates is attached to
        # lv.group_get_default() at creation time, so putting the knob in
        # that same default group and focusing it is all that's needed; no
        # custom pointer/drag math, no per-pixel redraw cost.
        default_group = lv.group_get_default()
        if default_group is not None:
            default_group.add_obj(self.knob)
            lv.group_focus_obj(self.knob)
            # In plain "navigate" mode, rotation moves focus between group
            # members instead of sending key events -- with the knob as the
            # only member, that has nowhere to go. "Editing" mode is the
            # standard way a lone encoder-driven control (arc, slider, ...)
            # gets rotation delivered as LV_KEY_LEFT/RIGHT instead.
            default_group.set_editing(True)

        def on_key(evt):
            key = evt.get_key()
            if key == lv.KEY.RIGHT:
                self.last_interaction = time.time()
                self._rotate(_ENCODER_STEP_DEG)
            elif key == lv.KEY.LEFT:
                self.last_interaction = time.time()
                self._rotate(-_ENCODER_STEP_DEG)

        self.knob.add_event_cb(on_key, lv.EVENT.KEY, None)

    def _on_hub_click(self, _evt):
        want = not self.playing
        self.osc.set_playing(want)
        self.playing = self.osc.playing
        self.last_interaction = time.time()
        self._refresh_hub()

    def _refresh_hub(self):
        if self.playing:
            self.hub_icon.set_text(lv.SYMBOL.VOLUME_MAX)
            self.hub_icon.set_style_text_color(_color(0x22C7E2), 0)
            self.hub.set_style_border_color(_color(0x22C7E2), 0)
        else:
            self.hub_icon.set_text(lv.SYMBOL.MUTE)
            self.hub_icon.set_style_text_color(_color(0x64748B), 0)
            self.hub.set_style_border_color(_color(0x475569), 0)

    def _select_wave(self, idx, initial=False):
        self.wave_idx = idx
        name, _make = _WAVES[idx]
        self.osc.wave = name
        for i, (btn, lbl) in enumerate(self.wave_btns):
            active = i == idx
            btn.set_style_bg_color(_color(0x22C7E2 if active else 0x151A20), 0)
            btn.set_style_bg_opa(lv.OPA.COVER, 0)
            btn.set_style_border_color(_color(0x22C7E2 if active else 0x2A3441), 0)
            lbl.set_style_text_color(_color(0x0A0D10 if active else 0x94A3B8), 0)
        if not initial:
            self.last_interaction = time.time()
            self._update_readout()

    def _rotate(self, delta_deg):
        new_angle = self.total_angle + delta_deg
        if new_angle < _MIN_ANGLE:
            new_angle = _MIN_ANGLE
        elif new_angle > _MAX_ANGLE:
            new_angle = _MAX_ANGLE
        if new_angle == self.total_angle:
            return
        self.total_angle = new_angle
        self._apply_angle()

    def _apply_angle(self):
        self.freq = FREQ_DEFAULT * (2.0 ** (self.total_angle / OCTAVE_DEG))
        self.osc.freq = self.freq
        visual = int(round(self.total_angle * 10)) % 3600
        self.knob.set_style_transform_rotation(visual, 0)
        self._update_readout()

    def _update_readout(self):
        name, octave = _note_name(self.freq)
        wave_name = _WAVES[self.wave_idx][0]
        if self.freq >= 1000:
            self.freq_label.set_text("{:.2f} kHz".format(self.freq / 1000.0))
        else:
            self.freq_label.set_text("{:.0f} Hz".format(self.freq))
        self.note_label.set_text("{}{} - {}".format(name, octave, wave_name))

    def _idle_tick(self, _timer):
        now = time.time()
        if self.playing:
            return
        idle_for = now - self.last_interaction
        if idle_for < 4.0:
            return
        sweep = math.sin((idle_for - 4.0) * 0.35) * (OCTAVE_DEG * 0.6)
        self.total_angle = sweep
        self._apply_angle()


_signal_gen = SignalGenHero(size=min(display_drv.width, display_drv.height))
