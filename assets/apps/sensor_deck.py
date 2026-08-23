"""
PyDevices Sensor Deck (Hero Canvas App for pdwidgets)
=====================================================
Interactive instrument deck built with pdwidgets:
- Dynamic circular Gauge with needle load indicator
- Interactive Switch toggle (Online / Muted)
- Real-time live scrolling telemetry meter
- Sleek 20px draggable Slider with touch & mouse tracking
"""

import math
import sys
import time

import appdev
from displaydev.wasmdisplay import WasmDisplay
import pdwidgets as pd


class SensorDeckHero:
    def __init__(self, canvas_id="hero_canvas", size=240):
        self.canvas_id = canvas_id
        self.size = size

        # 1. Initialize PSDisplay, App, and pdwidgets Display
        self.display_drv = WasmDisplay(width=size, height=size, canvas_id=canvas_id)
        self.app = appdev.App(
            displays=(self.display_drv,), host_read=self.display_drv.get_events
        )
        self.display = pd.Display(self.display_drv, self.app)

        # 2. Dark Slate Blue Screen Background
        self.screen = pd.Screen(self.display, bg=0x0842)

        # 3. Header Title (8px font, top-left aligned)
        self.lbl_title = pd.Label(
            self.screen,
            value="PDWIDGETS INSTRUMENT",
            x=16,
            y=12,
            align=pd.ALIGN.TOP_LEFT,
            text_height=pd.TEXT_SIZE.SMALL,
            fg=0x8C71,  # Slate
            bg=self.screen.bg,
        )

        # 4. Top-Left Gauge Widget
        self.gauge = pd.Gauge(
            self.screen,
            x=16,
            y=30,
            w=78,
            h=78,
            align=pd.ALIGN.TOP_LEFT,
            value=0.68,
            fg=0x156A,  # Emerald
            track_color=0x18E3,
            label="68%",
        )

        # 5. Top-Right Switch Widget
        self.switch_label = pd.Label(
            self.screen,
            value="ONLINE",
            x=124,
            y=36,
            align=pd.ALIGN.TOP_LEFT,
            text_height=pd.TEXT_SIZE.SMALL,
            fg=0xFFFF,
            bg=self.screen.bg,
        )
        self.switch = pd.Switch(
            self.screen,
            x=124,
            y=54,
            w=68,
            h=28,
            align=pd.ALIGN.TOP_LEFT,
            value=True,
            on_color=0x04C6,  # Emerald
            off_color=0x31A6,
            knob_color=0xFFFF,
        )

        def on_switch_change(s):
            self.switch_label.value = "ONLINE" if s.value else "MUTED"
            self.switch_label.fg = 0xFFFF if s.value else 0x8C71

        self.switch.set_change_cb(on_switch_change)

        # 6. Telemetry Meter
        self.lbl_telemetry = pd.Label(
            self.screen,
            value="BUS TELEMETRY: 48 kHz",
            x=16,
            y=116,
            align=pd.ALIGN.TOP_LEFT,
            text_height=pd.TEXT_SIZE.SMALL,
            fg=0x35FA,  # Sky blue
            bg=self.screen.bg,
        )

        # Progress / Level Bar for Telemetry
        self.prog = pd.ProgressBar(
            self.screen,
            x=16,
            y=134,
            w=208,
            h=12,
            align=pd.ALIGN.TOP_LEFT,
            value=0.55,
            fg=0x35FA,
            bg=0x1082,
        )

        # 7. Sleek 20px Interactive Slider Widget
        self.lbl_slider = pd.Label(
            self.screen,
            value="GAIN DAMPING: 72%",
            x=16,
            y=158,
            align=pd.ALIGN.TOP_LEFT,
            text_height=pd.TEXT_SIZE.SMALL,
            fg=0xFD20,  # Amber
            bg=self.screen.bg,
        )

        self.slider = pd.Slider(
            self.screen,
            x=16,
            y=176,
            w=208,
            h=20,
            align=pd.ALIGN.TOP_LEFT,
            value=0.72,
            fg=0xF440,
            bg=0x2124,
            knob_color=0xFFFF,
        )

        def on_slider_change(s):
            pct = int(s.value * 100)
            self.lbl_slider.value = f"GAIN DAMPING: {pct}%"

        self.slider.set_change_cb(on_slider_change)

        # Paint the initial widget tree into the WasmDisplay framebuffer.
        self.display.tick()

        # 8. Start Background Tick Animation
        self._tick_subscription = self.app.every(33, self._timer_tick)

    def _timer_tick(self, _timer):
        t = time.time()
        # Modulate telemetry and gauge smoothly
        load = (math.sin(t * 1.8) * 0.25 + 0.65) * self.slider.value
        self.gauge.value = max(0.0, min(1.0, load))
        self.gauge.label = f"{int(self.gauge.value * 100)}%"

        khz = int(32 + math.sin(t * 3.0) * 16 * (1.0 if self.switch.value else 0.1))
        self.lbl_telemetry.value = f"BUS TELEMETRY: {khz} kHz"
        self.prog.value = max(0.0, min(1.0, khz / 64.0))
        self.display.tick()


_hero_app = None


def main(canvas_id="hero_canvas"):
    global _hero_app
    print(f"Initializing PyDevices Sensor Deck on canvas '{canvas_id}'...")
    _hero_app = SensorDeckHero(canvas_id, size=240)
    print("PyDevices Sensor Deck running successfully!")


if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "hero_canvas"
    main(cid)
