/**
 * templates.js — Starter code snippets for the PyDevices Simulator.
 *
 * Provides ready-to-run interactive examples for LVGL, pdwidgets,
 * pygraphics, and displaydev using standard pydevices-examples imports
 * and board_config.py from pydevices-desktop.
 */

const SIMULATOR_TEMPLATES = {
  // --- LVGL Templates ---
  "lvgl-counter": {
    name: "LVGL: Interactive Counter",
    category: "LVGL",
    runtime: "pyodide",
    width: 320,
    height: 240,
    shape: "rectangle",
    deps: ["pydevices-desktop", "pydevices-lvgl"],
    code: `# LVGL: Interactive Counter & Buttons
import display_driver
import lvgl as lv
from board_config import display_drv

# Query LVGL major.minor version dynamically from the bindings
ver_str = f"v{lv.version_major()}.{lv.version_minor()}" if hasattr(lv, "version_major") else ""
print(f"Initializing LVGL {ver_str} Counter Demo...".strip())

def _font(size):
    for s in (size, 14, 16, 12, 20):
        name = f"font_montserrat_{s}"
        if hasattr(lv, name):
            f = getattr(lv, name)
            return f() if callable(f) else f
    return lv.font_default() if hasattr(lv, "font_default") else None

def _create_btn(parent):
    btn_cls = getattr(lv, "button", getattr(lv, "btn", None))
    return btn_cls(parent)

# Clean active screen from previous runs
scr = lv.screen_active()
scr.clean()
scr.set_style_bg_color(lv.color_hex(0x0F172A), 0)

# Card Container
card = lv.obj(scr)
card.set_size(min(display_drv.width - 40, 280), min(display_drv.height - 40, 200))
card.center()
card.set_style_bg_color(lv.color_hex(0x1E293B), 0)
card.set_style_border_color(lv.color_hex(0x334155), 0)
card.set_style_border_width(2, 0)
card.set_style_radius(16, 0)
card.set_style_pad_all(16, 0)

# Title Label with dynamic LVGL version
title = lv.label(card)
title.set_text(f"PyDevices - LVGL {ver_str}".strip())
title.set_style_text_color(lv.color_hex(0xF8FAFC), 0)
title.align(lv.ALIGN.TOP_MID, 0, 0)

# Counter Value
count = 0
lbl_count = lv.label(card)
lbl_count.set_text("Count: 0")
lbl_count.set_style_text_color(lv.color_hex(0x38BDF8), 0)
f_large = _font(20)
if f_large:
    lbl_count.set_style_text_font(f_large, 0)
lbl_count.align(lv.ALIGN.CENTER, 0, -10)

def btn_inc_cb(e):
    global count
    count += 1
    lbl_count.set_text(f"Count: {count}")
    print(f"Incremented: {count}")

def btn_dec_cb(e):
    global count
    count -= 1
    lbl_count.set_text(f"Count: {count}")
    print(f"Decremented: {count}")

def btn_reset_cb(e):
    global count
    count = 0
    lbl_count.set_text("Count: 0")
    print("Reset count to 0")

# Plus Button
btn_plus = _create_btn(card)
btn_plus.set_size(65, 38)
btn_plus.align(lv.ALIGN.BOTTOM_RIGHT, 0, 0)
btn_plus.set_style_bg_color(lv.color_hex(0x0284C7), 0)
btn_plus.add_event_cb(btn_inc_cb, lv.EVENT.CLICKED, None)
lbl_plus = lv.label(btn_plus)
lbl_plus.set_text("+1")
lbl_plus.center()

# Minus Button
btn_minus = _create_btn(card)
btn_minus.set_size(65, 38)
btn_minus.align(lv.ALIGN.BOTTOM_LEFT, 0, 0)
btn_minus.set_style_bg_color(lv.color_hex(0x475569), 0)
btn_minus.add_event_cb(btn_dec_cb, lv.EVENT.CLICKED, None)
lbl_minus = lv.label(btn_minus)
lbl_minus.set_text("-1")
lbl_minus.center()

# Reset Button
btn_rst = _create_btn(card)
btn_rst.set_size(80, 38)
btn_rst.align(lv.ALIGN.BOTTOM_MID, 0, 0)
btn_rst.set_style_bg_color(lv.color_hex(0xDC2626), 0)
btn_rst.add_event_cb(btn_reset_cb, lv.EVENT.CLICKED, None)
lbl_rst = lv.label(btn_rst)
lbl_rst.set_text("Reset")
lbl_rst.center()

print("LVGL Counter initialized and active. Click buttons to interact!")
`
  },

  "lvgl-thermostat": {
    name: "LVGL: Smart Thermostat Arc",
    category: "LVGL",
    runtime: "pyodide",
    width: 240,
    height: 240,
    shape: "round",
    deps: ["pydevices-desktop", "pydevices-lvgl"],
    code: `# LVGL: Smart Thermostat Dial (Round Watch UI)
import display_driver
import lvgl as lv
from board_config import display_drv

ver_str = f"v{lv.version_major()}.{lv.version_minor()}" if hasattr(lv, "version_major") else ""
print(f"Initializing Smart Thermostat Dial ({ver_str})...".strip())

def _font(size):
    for s in (size, 28, 20, 16, 14, 12):
        name = f"font_montserrat_{s}"
        if hasattr(lv, name):
            f = getattr(lv, name)
            return f() if callable(f) else f
    return lv.font_default() if hasattr(lv, "font_default") else None

# Clean active screen from previous runs
scr = lv.screen_active()
scr.clean()
scr.set_style_bg_color(lv.color_hex(0x0B0F19), 0)

# Temperature Arc (Interactive drag)
dim = min(display_drv.width, display_drv.height) - 30
arc = lv.arc(scr)
arc.set_size(dim, dim)
arc.set_rotation(135)
arc.set_bg_angles(0, 270)
arc.set_range(16, 32)
arc.set_value(22)
arc.center()

arc.set_style_arc_width(12, lv.PART.MAIN)
arc.set_style_arc_color(lv.color_hex(0x1F2937), lv.PART.MAIN)
arc.set_style_arc_width(12, lv.PART.INDICATOR)
arc.set_style_arc_color(lv.color_hex(0xEC4899), lv.PART.INDICATOR)

# Labels
lbl_temp = lv.label(scr)
lbl_temp.set_text("22 C")
lbl_temp.set_style_text_color(lv.color_hex(0xF9FAFB), 0)
f_temp = _font(28)
if f_temp:
    lbl_temp.set_style_text_font(f_temp, 0)
lbl_temp.align(lv.ALIGN.CENTER, 0, -10)

lbl_status = lv.label(scr)
lbl_status.set_text("COMFORT - HEATING")
lbl_status.set_style_text_color(lv.color_hex(0xF472B6), 0)
lbl_status.align(lv.ALIGN.CENTER, 0, 24)

def arc_event_cb(e):
    val = arc.get_value()
    lbl_temp.set_text(f"{val} C")
    if val >= 25:
        lbl_status.set_text("HIGH - WARMING")
        arc.set_style_arc_color(lv.color_hex(0xEF4444), lv.PART.INDICATOR)
    elif val <= 18:
        lbl_status.set_text("ECO - COOLING")
        arc.set_style_arc_color(lv.color_hex(0x3B82F6), lv.PART.INDICATOR)
    else:
        lbl_status.set_text("COMFORT - BALANCED")
        arc.set_style_arc_color(lv.color_hex(0xEC4899), lv.PART.INDICATOR)
    print(f"Target Temperature: {val} C")

arc.add_event_cb(arc_event_cb, lv.EVENT.VALUE_CHANGED, None)
print("Drag the outer ring to adjust temperature!")
`
  },

  // --- pdwidgets Templates ---
  "pdwidgets-dashboard": {
    name: "pdwidgets: Sensor Deck Dashboard",
    category: "pdwidgets",
    runtime: "pyodide",
    width: 240,
    height: 240,
    shape: "square",
    deps: ["pydevices-desktop", "pydevices-pdwidgets"],
    code: `# pdwidgets: Interactive Sensor Deck Dashboard
import appdev
import board_config
import pdwidgets as pd

print("Initializing pdwidgets Sensor Deck...")

app = appdev.App(board_config)
display = pd.Display(board_config.display_drv, app)

# Screen background
screen = pd.Screen(display, bg=0x0842)

# Header Title
lbl_title = pd.Label(
    screen,
    value="PDWIDGETS INSTRUMENT",
    x=16,
    y=12,
    align=pd.ALIGN.TOP_LEFT,
    text_height=pd.TEXT_SIZE.SMALL,
    fg=0x8C71,
    bg=screen.bg,
)

# Gauge Widget
gauge = pd.Gauge(
    screen,
    x=16,
    y=30,
    w=78,
    h=78,
    align=pd.ALIGN.TOP_LEFT,
    value=0.68,
    fg=0x156A,
    track_color=0x18E3,
    label="68%",
)

# Switch Widget
switch_label = pd.Label(
    screen,
    value="ONLINE",
    x=124,
    y=36,
    align=pd.ALIGN.TOP_LEFT,
    text_height=pd.TEXT_SIZE.SMALL,
    fg=0xFFFF,
    bg=screen.bg,
)
switch = pd.Switch(
    screen,
    x=124,
    y=54,
    w=68,
    h=28,
    align=pd.ALIGN.TOP_LEFT,
    value=True,
    on_color=0x04C6,
    off_color=0x31A6,
    knob_color=0xFFFF,
)

def on_switch_change(s):
    switch_label.value = "ONLINE" if s.value else "MUTED"
    switch_label.fg = 0xFFFF if s.value else 0x8C71
    print(f"Switch toggled: {'ONLINE' if s.value else 'MUTED'}")

switch.set_change_cb(on_switch_change)

# Telemetry Readouts
lbl_telemetry = pd.Label(
    screen,
    value="BUS TELEMETRY: 48 kHz",
    x=16,
    y=116,
    align=pd.ALIGN.TOP_LEFT,
    text_height=pd.TEXT_SIZE.SMALL,
    fg=0x35FA,
    bg=screen.bg,
)

prog = pd.ProgressBar(
    screen,
    x=16,
    y=134,
    w=display.width - 32,
    h=12,
    align=pd.ALIGN.TOP_LEFT,
    value=0.55,
    fg=0x35FA,
    bg=0x1082,
)

# Interactive Slider
lbl_slider = pd.Label(
    screen,
    value="GAIN DAMPING: 72%",
    x=16,
    y=158,
    align=pd.ALIGN.TOP_LEFT,
    text_height=pd.TEXT_SIZE.SMALL,
    fg=0xFD20,
    bg=screen.bg,
)

slider = pd.Slider(
    screen,
    x=16,
    y=176,
    w=display.width - 32,
    h=20,
    align=pd.ALIGN.TOP_LEFT,
    value=0.72,
    fg=0xF440,
    bg=0x2124,
    knob_color=0xFFFF,
)

def on_slider_change(s):
    pct = int(s.value * 100)
    lbl_slider.value = f"GAIN DAMPING: {pct}%"
    gauge.value = s.value
    gauge.label = f"{pct}%"
    print(f"Gain adjusted to: {pct}%")

slider.set_change_cb(on_slider_change)

print("pdwidgets Sensor Deck is live! Move the slider or click buttons.")
`
  },

  // --- pygraphics Templates ---
  "pygraphics-shapes": {
    name: "pygraphics: Vector & FrameBuffer Art",
    category: "pygraphics",
    runtime: "pyodide",
    width: 320,
    height: 240,
    shape: "rectangle",
    deps: ["pydevices-desktop", "pydevices-pygraphics", "pydevices-palettes"],
    code: `# pygraphics: High-Performance Vector & FrameBuffer Graphics
import math
from board_config import display_drv
from palettes import get_palette
import pygraphics as pg

print("Initializing pygraphics vector canvas...")

width = display_drv.width
height = display_drv.height

# Define palette
pal = get_palette()

# Create 16-bit RGB565 frame buffer
buf = bytearray(width * height * 2)
fb = pg.FrameBuffer(buf, width, height, pg.RGB565)

# Fill background
fb.fill(pal.NAVY if hasattr(pal, "NAVY") else 0x0842)

cx, cy = width // 2, height // 2

# Draw concentric geometric circles & ellipses
for r in range(20, min(cx, cy) - 10, 15):
    pg.ellipse(fb, cx, cy, r, int(r * 0.7), pal.CYAN if hasattr(pal, "CYAN") else 0x07FF)

# Radiating vector lines
for i in range(16):
    angle = i * (2 * math.pi / 16)
    x2 = int(cx + (cx - 20) * math.cos(angle))
    y2 = int(cy + (cy - 20) * math.sin(angle))
    pg.line(fb, cx, cy, x2, y2, pal.ORANGE if hasattr(pal, "ORANGE") else 0xFD20)

# Central Orbs
pg.circle(fb, cx, cy, 18, pal.RED if hasattr(pal, "RED") else 0xF800)
pg.circle(fb, cx, cy, 8, pal.WHITE if hasattr(pal, "WHITE") else 0xFFFF)

# Header Badge and Text
pg.fill_rect(fb, 10, 10, 150, 24, pal.DARKGREY if hasattr(pal, "DARKGREY") else 0x39E7)
pg.rect(fb, 10, 10, 150, 24, pal.GREY if hasattr(pal, "GREY") else 0x7BEF)
pg.text8(fb, "PyGraphics", 18, 18, pal.CYAN if hasattr(pal, "CYAN") else 0x07FF)

# Footer Badge
pg.fill_rect(fb, 10, height - 34, 180, 24, pal.DARKGREY if hasattr(pal, "DARKGREY") else 0x39E7)
pg.rect(fb, 10, height - 34, 180, 24, pal.GREY if hasattr(pal, "GREY") else 0x7BEF)
pg.text8(fb, "RGB565 FrameBuffer", 18, height - 26, pal.GREEN if hasattr(pal, "GREEN") else 0x07E0)

# Blit frame to canvas display
display_drv.blit_rect(buf, 0, 0, width, height)
print("Rendered pygraphics vector FrameBuffer successfully to display!")
`
  },

  // --- Bare displaydev ---
  "displaydev-raw": {
    name: "displaydev: Direct Pixel Painter",
    category: "displaydev",
    runtime: "pyodide",
    width: 320,
    height: 240,
    shape: "rectangle",
    deps: ["pydevices-desktop", "pydevices-palettes"],
    code: `# displaydev: Low-Level Direct Display Driver
from board_config import display_drv
from palettes import get_palette

print("Initializing bare display driver...")

pal = get_palette()

# Fill solid dark background
display_drv.fill(pal.BLACK if hasattr(pal, "BLACK") else 0x0000)

# Draw color bars
colors = [
    pal.RED if hasattr(pal, "RED") else 0xF800,
    pal.GREEN if hasattr(pal, "GREEN") else 0x07E0,
    pal.BLUE if hasattr(pal, "BLUE") else 0x001F,
    pal.YELLOW if hasattr(pal, "YELLOW") else 0xFFE0,
    pal.CYAN if hasattr(pal, "CYAN") else 0x07FF,
    pal.MAGENTA if hasattr(pal, "MAGENTA") else 0xF81F,
    pal.WHITE if hasattr(pal, "WHITE") else 0xFFFF,
    pal.ORANGE if hasattr(pal, "ORANGE") else 0xFD20,
]
bar_w = display_drv.width // len(colors)

for i, color in enumerate(colors):
    display_drv.fill_rect(i * bar_w, 20, bar_w, display_drv.height - 40, color)

print("Rendered 8-bar test pattern directly to display hardware!")
`
  }
};
