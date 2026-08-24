"""
PyDevices 3D Spinning Polyhedron (Hero Canvas App for cmods)
===========================================================
Real-time 3D projected faceted icosahedron with 3-axis matrix rotation,
depth sorting, light-source vector dot-product shading, and interactive touch tumbling.
"""

import sys
import time
import math

import board_config
import appdev
import board_config
import events
import pygraphics


def _rgb565(red, green, blue):
    return (int(red) & 0xF8) << 8 | (int(green) & 0xFC) << 3 | int(blue) >> 3


def _color(value):
    value = value.lstrip("#")
    return _rgb565(int(value[:2], 16), int(value[2:4], 16), int(value[4:], 16))


def _text(display, value, x, y, color, align="left"):
    value = str(value)
    if align == "right": x -= len(value) * 8
    pygraphics.text8(display, value, int(x), int(y) - 8, _color(color))


class PolyhedronHero:
    def __init__(self, canvas_id="hero_canvas", size=240):
        self.canvas_id = canvas_id
        self.size = size
        self.w = size
        self.h = size
        self.cx = size // 2
        self.cy = size // 2

        # Initialize PSDisplay
        import os
        os.environ.setdefault('PYDEVICES_WIDTH', str(size))
        os.environ.setdefault('PYDEVICES_HEIGHT', str(size))
        self.drv = board_config.display_drv
        self.app = appdev.App(board_config)

        # 3D Model: Icosahedron (12 vertices, 20 triangular faces)
        phi = (1.0 + math.sqrt(5.0)) / 2.0  # Golden ratio 1.618
        scale = 58.0

        raw_verts = [
            (-1, phi, 0), (1, phi, 0), (-1, -phi, 0), (1, -phi, 0),
            (0, -1, phi), (0, 1, phi), (0, -1, -phi), (0, 1, -phi),
            (phi, 0, -1), (phi, 0, 1), (-phi, 0, -1), (-phi, 0, 1),
        ]
        # Normalize vertices to unit sphere then scale
        self.vertices = []
        for x, y, z in raw_verts:
            length = math.sqrt(x * x + y * y + z * z)
            self.vertices.append([x / length * scale, y / length * scale, z / length * scale])

        self.faces = [
            (0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
            (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
            (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
            (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1),
        ]

        # Orientation & Momentum
        self.rot_x = 0.4
        self.rot_y = 0.8
        self.rot_z = 0.2
        self.vel_x = 0.012
        self.vel_y = 0.018
        self.is_dragging = False
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.last_interaction_time = time.time()

        # Light Vector (coming from top-left front: [-0.4, -0.6, 0.7])
        lx, ly, lz = -0.4, -0.6, 0.7
        l_len = math.sqrt(lx * lx + ly * ly + lz * lz)
        self.light_vec = (lx / l_len, ly / l_len, lz / l_len)

        self._bind_events()
        self.draw()

        self._tick_subscription = self.app.every(30, self._timer_tick)

    def _timer_tick(self, _timer):
        self.tick()

    def _bind_events(self):
        def on_pointer_down(event):
            self.is_dragging = True
            self.last_mouse_x, self.last_mouse_y = event.pos
            self.last_interaction_time = time.time()

        def on_pointer_move(event):
            if not self.is_dragging:
                return
            dx = event.pos[0] - self.last_mouse_x
            dy = event.pos[1] - self.last_mouse_y
            self.last_mouse_x, self.last_mouse_y = event.pos
            self.rot_y += dx * 0.015
            self.rot_x += dy * 0.015
            self.vel_y = dx * 0.008
            self.vel_x = dy * 0.008
            self.last_interaction_time = time.time()
            self.draw()

        def on_pointer_up(event):
            self.is_dragging = False

        self.app.on(events.MOUSEBUTTONDOWN, on_pointer_down)
        self.app.on(events.MOUSEMOTION, on_pointer_move)
        self.app.on(events.MOUSEBUTTONUP, on_pointer_up)

    def tick(self):
        if not self.is_dragging:
            self.rot_x += self.vel_x
            self.rot_y += self.vel_y
            self.rot_z += 0.004

            # Decay velocity to steady idle tumble
            idle_target_x = 0.012
            idle_target_y = 0.018
            self.vel_x += (idle_target_x - self.vel_x) * 0.05
            self.vel_y += (idle_target_y - self.vel_y) * 0.05
        self.draw()

    def rotate_point(self, p):
        x, y, z = p
        # Rotate around X
        rad_x = self.rot_x
        cos_x, sin_x = math.cos(rad_x), math.sin(rad_x)
        y1 = y * cos_x - z * sin_x
        z1 = y * sin_x + z * cos_x

        # Rotate around Y
        rad_y = self.rot_y
        cos_y, sin_y = math.cos(rad_y), math.sin(rad_y)
        x2 = x * cos_y + z1 * sin_y
        z2 = -x * sin_y + z1 * cos_y

        # Rotate around Z
        rad_z = self.rot_z
        cos_z, sin_z = math.cos(rad_z), math.sin(rad_z)
        x3 = x2 * cos_z - y1 * sin_z
        y3 = x2 * sin_z + y1 * cos_z

        return (x3, y3, z2)

    def draw(self):
        display = self.drv
        w, h, cx, cy = self.w, self.h, self.cx, self.cy

        # 1. High-Tech Background
        display.fill(_color("#0A0D11"))

        # Subtle Wire Grid
        for g in range(30, 240, 30):
            pygraphics.vline(display, g, 0, h, _color("#18212D"))
            pygraphics.hline(display, 0, g, w, _color("#18212D"))

        # 2. Transform all vertices
        t_verts = [self.rotate_point(v) for v in self.vertices]

        # 3. Project 3D to 2D
        fov = 220.0
        dist = 160.0
        p_verts = []
        for x, y, z in t_verts:
            z_cam = z + dist
            factor = fov / z_cam
            p_verts.append((cx + x * factor, cy + y * factor, z))

        # 4. Prepare Faces with Depth & Normal Lighting
        render_faces = []
        lx, ly, lz = self.light_vec

        for idx, (i0, i1, i2) in enumerate(self.faces):
            p0 = t_verts[i0]
            p1 = t_verts[i1]
            p2 = t_verts[i2]

            # Vector edge 1 & edge 2
            ax, ay, az = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
            bx, by, bz = p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]

            # Face Normal via Cross Product
            nx = ay * bz - az * by
            ny = az * bx - ax * bz
            nz = ax * by - ay * bx
            n_len = math.sqrt(nx * nx + ny * ny + nz * nz)
            if n_len > 0:
                nx /= n_len
                ny /= n_len
                nz /= n_len

            # Backface culling: if normal points away from viewer (nz < 0), skip or draw faint
            if nz <= 0.05:
                continue

            # Dot product with light source for intensity (0.0 to 1.0)
            dot = max(0.0, nx * lx + ny * ly + nz * lz)
            ambient = 0.2
            intensity = min(1.0, ambient + dot * 0.8)

            # Average face depth Z for sorting
            avg_z = (p0[2] + p1[2] + p2[2]) / 3.0
            render_faces.append((avg_z, i0, i1, i2, intensity, idx))

        # Sort back-to-front
        render_faces.sort(key=lambda item: item[0])

        # 5. Render Faces with Metallic / Palette Shading
        for avg_z, i0, i1, i2, intensity, f_idx in render_faces:
            x0, y0, _ = p_verts[i0]
            x1, y1, _ = p_verts[i1]
            x2, y2, _ = p_verts[i2]

            # Dynamic Palette Color Interpolation (Steel Blue -> Electric Cyan -> Brand Orange)
            if intensity < 0.5:
                # Interpolate #1E293B -> #0284C7
                t = intensity / 0.5
                r_c = int(30 + t * (2 - 30))
                g_c = int(41 + t * (132 - 41))
                b_c = int(59 + t * (199 - 59))
            else:
                # Interpolate #0284C7 -> #F54E00 / Gold
                t = (intensity - 0.5) / 0.5
                r_c = int(2 + t * (245 - 2))
                g_c = int(132 + t * (78 - 132))
                b_c = int(199 + t * (0 - 199))

            pygraphics.triangle(display, int(x0), int(y0), int(x1), int(y1), int(x2), int(y2), _rgb565(r_c, g_c, b_c), True)
            edge = _color("#64748B")
            pygraphics.line(display, int(x0), int(y0), int(x1), int(y1), edge)
            pygraphics.line(display, int(x1), int(y1), int(x2), int(y2), edge)
            pygraphics.line(display, int(x2), int(y2), int(x0), int(y0), edge)

        # 6. Tech HUD Overlay
        _text(display, "CMODS 3D ENGINE", 12, 20, "#94A3B8")
        _text(display, "60 FPS", w - 12, 20, "#94A3B8", "right")

        if hasattr(self.drv, "show"):
            self.drv.show()


_polyhedron_app = None


def main(canvas_id="hero_canvas"):
    global _polyhedron_app
    print(f"Initializing PyDevices 3D Polyhedron on canvas '{canvas_id}'...")
    _polyhedron_app = PolyhedronHero(canvas_id, size=240)
    print("PyDevices 3D Polyhedron running successfully!")
