"""
PyDevices Serial FTP Scope (Hero Canvas App for mpftp)
======================================================
Interactive dual-pane serial FTP and hex data transfer monitor:
- Real-time animated serial packet progress bar
- Live scrolling MicroPython .mpy bytecode hex dump
- Interactive file selection and UART CDC transfer trigger
"""

import math
import sys
import time
from random import randint, choice

import board_config
import appdev
import board_config
import events
import pygraphics


def _color(value):
    value = value.lstrip("#")
    r, g, b = int(value[:2], 16), int(value[2:4], 16), int(value[4:], 16)
    return (r & 0xF8) << 8 | (g & 0xFC) << 3 | b >> 3


def _text(display, value, x, y, color, align="left"):
    value = str(value)
    if align == "right": x -= len(value) * 8
    pygraphics.text8(display, value, int(x), int(y) - 8, _color(color))


SAMPLE_FILES = [
    ("main.py", 1420),
    ("boot.py", 340),
    ("driver.mpy", 4890),
    ("config.json", 680),
]


class FtpScopeHero:
    def __init__(self, canvas_id="hero_canvas", size=240):
        self.canvas_id = canvas_id
        self.size = size
        self.w = size
        self.h = size

        import os
        os.environ.setdefault('PYDEVICES_WIDTH', str(size))
        os.environ.setdefault('PYDEVICES_HEIGHT', str(size))
        self.drv = board_config.display_drv
        self.app = appdev.App(board_config)

        self.file_idx = 0
        self.cur_file, self.cur_size = SAMPLE_FILES[self.file_idx]
        self.bytes_transferred = 620
        self.baud = "115,200"
        self.hex_offset = 0x0000

        self.draw()
        self._bind_events()

        self._tick_subscription = self.app.every(33, self._timer_tick)

    def _timer_tick(self, _timer):
        self.tick()

    def _bind_events(self):
        def on_pointer_down(_event):
            self.file_idx = (self.file_idx + 1) % len(SAMPLE_FILES)
            self.cur_file, self.cur_size = SAMPLE_FILES[self.file_idx]
            self.bytes_transferred = 0
            self.hex_offset += 0x0040
            self.draw()

        self.app.on(events.MOUSEBUTTONDOWN, on_pointer_down)

    def tick(self):
        if self.bytes_transferred < self.cur_size:
            self.bytes_transferred = min(self.cur_size, self.bytes_transferred + 48)
        else:
            if randint(0, 100) > 96:
                self.file_idx = (self.file_idx + 1) % len(SAMPLE_FILES)
                self.cur_file, self.cur_size = SAMPLE_FILES[self.file_idx]
                self.bytes_transferred = 0
                self.hex_offset += 0x0040
        self.draw()

    def draw(self):
        display = self.drv
        w, h = self.w, self.h

        # 1. Dark Terminal Background
        display.fill(_color("#0A0D14"))

        # 2. Header Bar
        display.fill_rect(0, 0, w, 28, _color("#0F172A"))
        pygraphics.hline(display, 0, 28, w, _color("#1E293B"))
        _text(display, "MPFTP SERIAL REPL", 10, 18, "#94A3B8")
        _text(display, "USB CDC / 115k", w - 10, 18, "#10B981", "right")

        # 3. Virtual Remote File Bar (x: 12, y: 36, w: 216, h: 48)
        fx, fy, fw, fh = 12, 36, 216, 50
        pygraphics.round_rect(display, fx, fy, fw, fh, 6, _color("#0F172A"), True)
        pygraphics.round_rect(display, fx, fy, fw, fh, 6, _color("#334155"))
        _text(display, self.cur_file, fx + 10, fy + 17, "#38BDF8")

        pct = int((self.bytes_transferred / self.cur_size) * 100)
        _text(display, f"{pct}% ({self.cur_size}B)", fx + fw - 10, fy + 17, "#94A3B8", "right")

        # Progress Track
        pygraphics.round_rect(display, fx + 10, fy + 28, fw - 20, 8, 4, _color("#1E293B"), True)

        # Progress Active Bar
        prog_w = int((fw - 20) * (self.bytes_transferred / self.cur_size))
        progress_color = "#38BDF8" if pct < 100 else "#10B981"
        pygraphics.round_rect(display, fx + 10, fy + 28, max(6, prog_w), 8, 4, _color(progress_color), True)

        # 4. Hex Dump Stream Pane (x: 12, y: 94, w: 216, h: 134)
        hx, hy, hw, hh = 12, 94, 216, 134
        pygraphics.round_rect(display, hx, hy, hw, hh, 6, _color("#020617"), True)
        pygraphics.round_rect(display, hx, hy, hw, hh, 6, _color("#1E293B"))
        _text(display, "OFFSET   HEX STREAM     ASCII", hx + 8, hy + 14, "#64748B")

        # Generate 5 lines of realistic MicroPython bytecode hex
        hex_data = [
            ("0000", "4D 50 59 06 00 20", "MPY.. "),
            ("0008", "02 04 08 12 1F 0A", "......"),
            ("0010", "28 32 4F 50 54 33", "(2OPT3"),
            ("0018", "64 69 73 70 6C 61", "displa"),
            ("0020", "79 69 66 2E 64 72", "yif.dr"),
        ]

        for i, (off, bytes_str, asc_str) in enumerate(hex_data):
            row_y = hy + 32 + i * 19
            # Row highlight
            if i == 2:
                display.fill_rect(hx + 4, row_y - 10, hw - 8, 16, _color("#0C3548"))
            _text(display, f"{int(off, 16) + self.hex_offset:04X}", hx + 8, row_y, "#F59E0B")
            _text(display, bytes_str, hx + 48, row_y, "#E2E8F0")
            _text(display, asc_str, hx + 168, row_y, "#34D399")

        if hasattr(self.drv, "show"):
            self.drv.show()


_ftp_app = None


def main(canvas_id="hero_canvas"):
    global _ftp_app
    print(f"Initializing PyDevices FTP Scope on canvas '{canvas_id}'...")
    _ftp_app = FtpScopeHero(canvas_id, size=240)
    print("PyDevices FTP Scope running successfully!")


if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "hero_canvas"
    main(cid)
