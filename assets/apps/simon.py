"""
PyDevices Simon Memory Game (Hero Canvas App for pygraphics)
============================================================
Classic 4-color memory game rendered in pure Python directly on PyDevices PSDisplay.
Features idle attract mode and full interactive touch/click gameplay.
"""

import sys
import time
import math
from random import getrandbits

import appdev
import events
from displaydev.wasmdisplay import WasmDisplay
import pygraphics

# Color definitions (RGB565)
BLACK = 0x0000
DARK_BG = 0x1014
WHITE = 0xFFFF
GREY_TEXT = 0x94A3

# (Green, Red, Yellow, Blue)
DIM_COLORS = (0x0320, 0x8000, 0x8400, 0x0010)
LIT_COLORS = (0x07E0, 0xF800, 0xFFE0, 0x001F)

IDLE, SHOW, INPUT, FAIL = 0, 1, 2, 3


class SimonHero:
    def __init__(self, canvas_id="hero_canvas", size=240):
        self.canvas_id = canvas_id
        self.size = size
        self.w = size
        self.h = size
        self.cx = size // 2
        self.cy = size // 2
        self.inner_r = max(28, size // 7)
        self.gap = 4
        self.half_gap = self.gap // 2
        self._strip = self.inner_r - self.half_gap

        # Geometry for 4 L-shaped quadrant pads
        self.pads = (
            # 0: Top-Left (Green)
            (
                (0, 0, self.cx - self.inner_r, self.cy - self.half_gap),
                (self.cx - self.inner_r, 0, self._strip, self.cy - self.inner_r),
            ),
            # 1: Top-Right (Red)
            (
                (self.cx + self.inner_r, 0, self.w - (self.cx + self.inner_r), self.cy - self.half_gap),
                (self.cx + self.half_gap, 0, self._strip, self.cy - self.inner_r),
            ),
            # 2: Bottom-Left (Yellow)
            (
                (0, self.cy + self.half_gap, self.cx - self.inner_r, self.h - (self.cy + self.half_gap)),
                (self.cx - self.inner_r, self.cy + self.inner_r, self._strip, self.h - (self.cy + self.inner_r)),
            ),
            # 3: Bottom-Right (Blue)
            (
                (self.cx + self.inner_r, self.cy + self.half_gap, self.w - (self.cx + self.inner_r), self.h - (self.cy + self.half_gap)),
                (self.cx + self.half_gap, self.cy + self.inner_r, self._strip, self.h - (self.cy + self.inner_r)),
            ),
        )

        # Initialize PSDisplay
        self.drv = WasmDisplay(width=size, height=size, canvas_id=canvas_id)
        self.app = appdev.App(displays=(self.drv,), host_read=self.drv.get_events)

        # Game state
        self.state = IDLE
        self.sequence = []
        self.step = 0
        self.score = 0
        self.best = 0
        self.lit_pad = -1
        self.anim_step = 0
        self.next_action_time = time.time() + 1.0
        self.attract_idx = 0

        # Draw initial board
        self.draw_board("SIMON", "TAP")

        # Bind touch/mouse events
        self._bind_events()

        # Start the animation through the direct WebAssembly timer backend.
        self._tick_subscription = self.app.every(33, self._timer_tick)

    def _timer_tick(self, _timer):
        self.tick()

    def _bind_events(self):
        def on_pointer_down(event):
            x, y = event.pos
            self.handle_touch(x, y)

        self.app.on(events.MOUSEBUTTONDOWN, on_pointer_down)

    def draw_pad(self, pad_idx, is_lit=False):
        color = LIT_COLORS[pad_idx] if is_lit else DIM_COLORS[pad_idx]
        for x, y, w, h in self.pads[pad_idx]:
            self.drv.fill_rect(x, y, w, h, color)

    def draw_board(self, hub_title="SIMON", hub_sub="TAP"):
        # Dark Background
        self.drv.fill_rect(0, 0, self.w, self.h, DARK_BG)
        # Draw 4 pads dim
        for i in range(4):
            self.draw_pad(i, is_lit=(self.lit_pad == i))

        # Center Hub Box (Round / Dark with border)
        hw = self.inner_r * 2 - self.gap
        hh = self.inner_r * 2 - self.gap
        hx = self.cx - hw // 2
        hy = self.cy - hh // 2
        self.drv.fill_rect(hx, hy, hw, hh, 0x080B)

        # Draw hub text directly into the display framebuffer.
        pygraphics.text8(
            self.drv,
            hub_title,
            self.cx - len(hub_title) * 4,
            self.cy - 11,
            WHITE,
        )
        pygraphics.text8(
            self.drv,
            hub_sub,
            self.cx - len(hub_sub) * 4,
            self.cy + 5,
            GREY_TEXT,
        )

        if hasattr(self.drv, "show"):
            self.drv.show()

    def handle_touch(self, x, y):
        now = time.time()
        # Find which pad was touched
        dx = x - self.cx
        dy = y - self.cy
        dist = math.sqrt(dx * dx + dy * dy)

        # Hub touched
        if dist < self.inner_r:
            if self.state in (IDLE, FAIL):
                self.start_game()
            return

        # Quadrant touched
        touched_pad = -1
        if dx < -self.half_gap and dy < -self.half_gap:
            touched_pad = 0  # Green (TL)
        elif dx > self.half_gap and dy < -self.half_gap:
            touched_pad = 1  # Red (TR)
        elif dx < -self.half_gap and dy > self.half_gap:
            touched_pad = 2  # Yellow (BL)
        elif dx > self.half_gap and dy > self.half_gap:
            touched_pad = 3  # Blue (BR)

        if touched_pad < 0:
            return

        if self.state == IDLE:
            self.start_game()
        elif self.state == INPUT:
            self.lit_pad = touched_pad
            self.draw_pad(touched_pad, True)
            self.drv.show()

            if touched_pad == self.sequence[self.step]:
                # Correct pad
                self.step += 1
                self.next_action_time = now + 0.25
                if self.step >= len(self.sequence):
                    # Finished sequence for this level!
                    self.score = len(self.sequence)
                    if self.score > self.best:
                        self.best = self.score
                    self.state = SHOW
                    self.sequence.append(getrandbits(2))
                    self.step = 0
                    self.anim_step = 0
                    self.next_action_time = now + 0.6
            else:
                # Wrong pad -> FAIL
                self.state = FAIL
                self.anim_step = 0
                self.next_action_time = now + 0.1

    def start_game(self):
        self.sequence = [getrandbits(2)]
        self.step = 0
        self.score = 0
        self.anim_step = 0
        self.state = SHOW
        self.next_action_time = time.time() + 0.5
        self.draw_board("WATCH", f"LEN {len(self.sequence):02d}")

    def tick(self):
        now = time.time()
        if self.state == IDLE:
            # Idle attract light sweep every 0.6s
            if now >= self.next_action_time:
                self.lit_pad = self.attract_idx
                self.draw_board("SIMON", f"BEST {self.best:02d}" if self.best > 0 else "TAP")
                self.attract_idx = (self.attract_idx + 1) % 4
                self.next_action_time = now + 0.45

        elif self.state == SHOW:
            if now >= self.next_action_time:
                # Flash each step in the sequence
                if self.anim_step % 2 == 0:
                    # Light pad
                    seq_idx = self.anim_step // 2
                    if seq_idx < len(self.sequence):
                        self.lit_pad = self.sequence[seq_idx]
                        self.draw_board("WATCH", f"LEN {len(self.sequence):02d}")
                        self.anim_step += 1
                        self.next_action_time = now + 0.35
                    else:
                        # End of sequence display -> switch to player input
                        self.lit_pad = -1
                        self.state = INPUT
                        self.step = 0
                        self.draw_board("PLAY", f"SCORE {self.score:02d}")
                        self.next_action_time = now + 5.0  # 5 sec timeout
                else:
                    # Unlight pad gap
                    self.lit_pad = -1
                    self.draw_board("WATCH", f"LEN {len(self.sequence):02d}")
                    self.anim_step += 1
                    self.next_action_time = now + 0.12

        elif self.state == INPUT:
            # Check timeout
            if now >= self.next_action_time and self.lit_pad >= 0:
                self.lit_pad = -1
                self.draw_board("PLAY", f"SCORE {self.score:02d}")

        elif self.state == FAIL:
            if now >= self.next_action_time:
                if self.anim_step < 4:
                    self.lit_pad = -1 if self.anim_step % 2 == 1 else 1  # flash red
                    self.draw_board("FAIL!", f"SCR {self.score:02d}")
                    self.anim_step += 1
                    self.next_action_time = now + 0.15
                else:
                    self.state = IDLE
                    self.lit_pad = -1
                    self.draw_board("SIMON", f"BEST {self.best:02d}")
                    self.next_action_time = now + 1.0


_simon_app = None


def main(canvas_id="hero_canvas"):
    global _simon_app
    print(f"Initializing PyDevices Simon on canvas '{canvas_id}'...")
    _simon_app = SimonHero(canvas_id, size=240)
    print("PyDevices Simon running successfully!")
