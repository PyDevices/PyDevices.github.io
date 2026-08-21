/**
 * templates.js — Starter code snippets for the PyDevices Simulator.
 *
 * Provides ready-to-run interactive examples for LVGL v9, pdwidgets,
 * pygraphics, and raw displaydev across both Pyodide and MicroPython WASM.
 */

const SIMULATOR_TEMPLATES = {
  // --- LVGL v9 Templates ---
  "lvgl-counter": {
    name: "LVGL v9: Interactive Counter",
    category: "LVGL v9",
    runtime: "pyodide",
    width: 320,
    height: 240,
    shape: "rectangle",
    deps: ["pydevices", "pydevices-lvgl"],
    code: `# LVGL v9: Interactive Counter & Buttons
import types, sys
from displaydev.psdisplay import PSDisplay

# Synthesize board_config for hero / simulator canvas
bc = types.ModuleType("board_config")
bc.display_drv = PSDisplay("display_canvas", width=320, height=240)
bc.get_events = bc.display_drv.get_events
sys.modules["board_config"] = bc

import display_driver
import lvgl as lv

print("Initializing LVGL v9 Counter Demo...")

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

scr = lv.screen_active()
scr.set_style_bg_color(lv.color_hex(0x0F172A), 0)

# Card Container
card = lv.obj(scr)
card.set_size(280, 200)
card.center()
card.set_style_bg_color(lv.color_hex(0x1E293B), 0)
card.set_style_border_color(lv.color_hex(0x334155), 0)
card.set_style_border_width(2, 0)
card.set_style_radius(16, 0)
card.set_style_pad_all(16, 0)

# Title Label
title = lv.label(card)
title.set_text("PyDevices · LVGL v9")
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
    name: "LVGL v9: Smart Thermostat Arc",
    category: "LVGL v9",
    runtime: "pyodide",
    width: 240,
    height: 240,
    shape: "round",
    deps: ["pydevices", "pydevices-lvgl"],
    code: `# LVGL v9: Smart Thermostat Dial (Round Watch UI)
import types, sys
from displaydev.psdisplay import PSDisplay

# Synthesize board_config
bc = types.ModuleType("board_config")
bc.display_drv = PSDisplay("display_canvas", width=240, height=240)
bc.get_events = bc.display_drv.get_events
sys.modules["board_config"] = bc

import display_driver
import lvgl as lv

print("Initializing Smart Thermostat Dial...")

def _font(size):
    for s in (size, 28, 20, 16, 14, 12):
        name = f"font_montserrat_{s}"
        if hasattr(lv, name):
            f = getattr(lv, name)
            return f() if callable(f) else f
    return lv.font_default() if hasattr(lv, "font_default") else None

scr = lv.screen_active()
scr.set_style_bg_color(lv.color_hex(0x0B0F19), 0)

# Temperature Arc (Interactive drag)
arc = lv.arc(scr)
arc.set_size(210, 210)
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
lbl_temp.set_text("22°C")
lbl_temp.set_style_text_color(lv.color_hex(0xF9FAFB), 0)
f_temp = _font(28)
if f_temp:
    lbl_temp.set_style_text_font(f_temp, 0)
lbl_temp.align(lv.ALIGN.CENTER, 0, -10)

lbl_status = lv.label(scr)
lbl_status.set_text("COMFORT · HEATING")
lbl_status.set_style_text_color(lv.color_hex(0xF472B6), 0)
lbl_status.align(lv.ALIGN.CENTER, 0, 24)

def arc_event_cb(e):
    val = arc.get_value()
    lbl_temp.set_text(f"{val}°C")
    if val >= 25:
        lbl_status.set_text("HIGH · WARMING")
        arc.set_style_arc_color(lv.color_hex(0xEF4444), lv.PART.INDICATOR)
    elif val <= 18:
        lbl_status.set_text("ECO · COOLING")
        arc.set_style_arc_color(lv.color_hex(0x3B82F6), lv.PART.INDICATOR)
    else:
        lbl_status.set_text("COMFORT · BALANCED")
        arc.set_style_arc_color(lv.color_hex(0xEC4899), lv.PART.INDICATOR)
    print(f"Target Temperature: {val}°C")

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
    deps: ["pydevices", "pydevices-pdwidgets"],
    code: `# pdwidgets: Interactive Sensor Deck Dashboard
import appdev
from displaydev.psdisplay import PSDisplay
import pdwidgets as pd

print("Initializing pdwidgets Sensor Deck...")

display_drv = PSDisplay("display_canvas", width=240, height=240)
app = appdev.App(display_drv)
display = pd.Display(display_drv, app)

# Screen background
screen = pd.Screen(display, bg=0x0842)

# Title Label
lbl_title = pd.Label(screen, text="PYDEVICES SENSOR DECK", x=12, y=10, color=0x38BDF8)

# Telemetry Readouts
lbl_temp = pd.Label(screen, text="TEMP: 24.5 °C", x=12, y=34, color=0x4ADE80)
lbl_pres = pd.Label(screen, text="PRES: 1013 hPa", x=12, y=54, color=0xFCD34D)
lbl_hum  = pd.Label(screen, text="HUM : 48.0 %", x=12, y=74, color=0x60A5FA)

# Interactive Slider
lbl_slider = pd.Label(screen, text="OUTPUT GAIN: 65%", x=12, y=106, color=0xE2E8F0)
slider = pd.Slider(screen, x=12, y=130, w=216, h=24, min_val=0, max_val=100, val=65)

def on_slider_change(val):
    lbl_slider.text = f"OUTPUT GAIN: {int(val)}%"
    print(f"Output Gain set to: {int(val)}%")

slider.on_change = on_slider_change

# Status Badge Button
btn_status = pd.Button(screen, text="SYS: ACTIVE [OK]", x=12, y=175, w=216, h=36, bg=0x064E3B, fg=0x34D399)

def on_btn_click():
    print("System health check requested - All sensors operational.")
    btn_status.text = "SYS: HEALTHY 100%"

btn_status.on_click = on_btn_click

screen.show()
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
    deps: ["pydevices", "pydevices-pygraphics", "pydevices-palettes"],
    code: `# pygraphics: High-Performance Vector & FrameBuffer Graphics
import math, time
import pygraphics as pg
from displaydev.psdisplay import PSDisplay
from displaybuf import DisplayBuffer

print("Initializing pygraphics vector canvas...")

display_drv = PSDisplay("display_canvas", width=320, height=240)
ssd = DisplayBuffer(display_drv, DisplayBuffer.RGB565)

# Clear background to deep navy
ssd.fill(pg.color565(10, 15, 30))

cx, cy = 160, 120

# Draw animated geometric rings and starburst
for r in range(20, 110, 15):
    color = pg.color565(56, 189, int(200 + r / 2))
    ssd.ellipse(cx, cy, r, int(r * 0.7), color, False)

# Draw radiating lines
for i in range(16):
    angle = i * (2 * math.pi / 16)
    x2 = int(cx + 100 * math.cos(angle))
    y2 = int(cy + 70 * math.sin(angle))
    ssd.line(cx, cy, x2, y2, pg.color565(245, 158, 11))

# Central Orb
ssd.fill_circle(cx, cy, 18, pg.color565(239, 68, 68))
ssd.fill_circle(cx, cy, 8, pg.color565(255, 255, 255))

# Corner Badges
ssd.fill_rect(10, 10, 130, 26, pg.color565(30, 41, 59))
ssd.rect(10, 10, 130, 26, pg.color565(71, 85, 105))
ssd.text("PyGraphics v1.0", 16, 18, pg.color565(56, 189, 248))

ssd.fill_rect(10, 204, 150, 26, pg.color565(30, 41, 59))
ssd.rect(10, 204, 150, 26, pg.color565(71, 85, 105))
ssd.text("FPS: 60 | RGB565", 16, 212, pg.color565(74, 222, 128))

ssd.show()
print("Drawn vector frame to display successfully!")
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
    deps: ["pydevices"],
    code: `# displaydev: Low-Level Direct Display Driver
from displaydev.psdisplay import PSDisplay

print("Initializing bare PSDisplay driver...")

drv = PSDisplay("display_canvas", width=320, height=240)

# Fill solid dark background
drv.fill(0x050510)

# Draw color bars
colors = [
    0xFF0000, 0x00FF00, 0x0000FF, 
    0xFFFF00, 0x00FFFF, 0xFF00FF, 
    0xFFFFFF, 0x38BDF8
]
bar_w = 320 // len(colors)

for i, color in enumerate(colors):
    drv.fill_rect(i * bar_w, 20, bar_w, 140, color)

print("Rendered 8-bar test pattern directly to display hardware!")
`
  }
};
