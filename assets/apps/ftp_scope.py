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
import types
from random import randint, choice

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

        if "board_config" not in sys.modules:
            bc = types.ModuleType("board_config")
            bc.display_drv = PSDisplay(canvas_id, width=size, height=size)
            sys.modules["board_config"] = bc
            self.drv = bc.display_drv
        else:
            self.drv = sys.modules["board_config"].display_drv

        self.file_idx = 0
        self.cur_file, self.cur_size = SAMPLE_FILES[self.file_idx]
        self.bytes_transferred = 620
        self.baud = "115,200"
        self.hex_offset = 0x0000

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
            self.file_idx = (self.file_idx + 1) % len(SAMPLE_FILES)
            self.cur_file, self.cur_size = SAMPLE_FILES[self.file_idx]
            self.bytes_transferred = 0
            self.hex_offset += 0x0040
            self.draw()

        self._p_down = create_proxy(on_pointer_down)
        canvas.addEventListener("pointerdown", self._p_down)

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
        if not hasattr(self.drv, "_buf_ctx") or not self.drv._buf_ctx:
            return
        ctx = self.drv._buf_ctx
        w, h = self.w, self.h

        # 1. Dark Terminal Background
        ctx.fillStyle = "#0A0D14"
        ctx.fillRect(0, 0, w, h)

        # 2. Header Bar
        ctx.fillStyle = "rgba(15, 23, 42, 0.95)"
        ctx.fillRect(0, 0, w, 28)
        ctx.strokeStyle = "#1E293B"
        ctx.lineWidth = 1
        ctx.beginPath()
        ctx.moveTo(0, 28)
        ctx.lineTo(w, 28)
        ctx.stroke()

        ctx.fillStyle = "#94A3B8"
        ctx.font = "bold 9px system-ui, monospace"
        ctx.textAlign = "left"
        ctx.fillText("⚡ MPFTP SERIAL REPL", 10, 18)

        ctx.fillStyle = "#10B981"
        ctx.textAlign = "right"
        ctx.fillText("USB CDC · 115k", w - 10, 18)

        # 3. Virtual Remote File Bar (x: 12, y: 36, w: 216, h: 48)
        fx, fy, fw, fh = 12, 36, 216, 50
        ctx.fillStyle = "#0F172A"
        ctx.beginPath()
        ctx.roundRect(fx, fy, fw, fh, 6)
        ctx.fill()
        ctx.strokeStyle = "#334155"
        ctx.lineWidth = 1
        ctx.stroke()

        ctx.fillStyle = "#38BDF8"
        ctx.font = "bold 9px monospace"
        ctx.textAlign = "left"
        ctx.fillText(f"📁 {self.cur_file}", fx + 10, fy + 17)

        pct = int((self.bytes_transferred / self.cur_size) * 100)
        ctx.fillStyle = "#94A3B8"
        ctx.font = "9px monospace"
        ctx.textAlign = "right"
        ctx.fillText(f"{pct}% ({self.cur_size}B)", fx + fw - 10, fy + 17)

        # Progress Track
        ctx.fillStyle = "#1E293B"
        ctx.beginPath()
        ctx.roundRect(fx + 10, fy + 28, fw - 20, 8, 4)
        ctx.fill()

        # Progress Active Bar
        prog_w = int((fw - 20) * (self.bytes_transferred / self.cur_size))
        ctx.fillStyle = "#38BDF8" if pct < 100 else "#10B981"
        ctx.beginPath()
        ctx.roundRect(fx + 10, fy + 28, max(6, prog_w), 8, 4)
        ctx.fill()

        # 4. Hex Dump Stream Pane (x: 12, y: 94, w: 216, h: 134)
        hx, hy, hw, hh = 12, 94, 216, 134
        ctx.fillStyle = "#020617"
        ctx.beginPath()
        ctx.roundRect(hx, hy, hw, hh, 6)
        ctx.fill()
        ctx.strokeStyle = "#1E293B"
        ctx.lineWidth = 1
        ctx.stroke()

        ctx.fillStyle = "#64748B"
        ctx.font = "8px monospace"
        ctx.textAlign = "left"
        ctx.fillText("OFFSET   HEX STREAM          ASCII", hx + 8, hy + 14)

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
                ctx.fillStyle = "rgba(56, 189, 248, 0.12)"
                ctx.fillRect(hx + 4, row_y - 10, hw - 8, 16)

            ctx.fillStyle = "#F59E0B"
            ctx.font = "9px monospace"
            ctx.fillText(f"{int(off, 16) + self.hex_offset:04X}", hx + 8, row_y)

            ctx.fillStyle = "#E2E8F0"
            ctx.fillText(bytes_str, hx + 48, row_y)

            ctx.fillStyle = "#34D399"
            ctx.fillText(asc_str, hx + 168, row_y)

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
