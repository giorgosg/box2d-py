from OpenGL.GL import *
from box2d import DebugDraw, Vec2, Transform, AABB, Color
from .testbed_state import state
from .draw import GLBackground, GLCircles, GLPoints, GLLines
from .draw import GLSolidPolygons, GLSolidCircles, GLSolidCapsules
from imgui_bundle import imgui
import numpy as np
import math
import time


class Camera:
    def __init__(self):
        self.width = 1280
        self.height = 800
        self.reset_view()
        self._matrix = None

    def reset_view(self):
        """Reset camera to initial position and zoom"""
        self.center = Vec2(0.0, 0.0)
        self.zoom = 1.0
        self._matrix = None

    def set_view(self, center, zoom, width, height):
        """Set camera view parameters"""
        if (
            self.center != Vec2(*center)
            or self.zoom != zoom
            or self.width != width
            or self.height != height
        ):
            self.center = Vec2(*center)
            self.zoom = zoom
            self.width = width
            self.height = height
            self._matrix = None

    def convert_screen_to_world(self, ps):
        """Convert from screen coordinates to world coordinates"""
        w = float(self.width)
        h = float(self.height)
        u = ps.x / w
        v = (h - ps.y) / h

        ratio = w / h
        extents = Vec2(self.zoom * ratio, self.zoom)

        lower = self.center - extents
        upper = self.center + extents

        pw = Vec2((1.0 - u) * lower.x + u * upper.x, (1.0 - v) * lower.y + v * upper.y)
        return pw

    def convert_world_to_screen(self, pw):
        """Convert from world coordinates to screen coordinates"""
        w = float(self.width)
        h = float(self.height)
        ratio = w / h

        extents = Vec2(self.zoom * ratio, self.zoom)

        # Vec2 operations
        lower = self.center - extents
        upper = self.center + extents

        u = (pw.x - lower.x) / (upper.x - lower.x)
        v = (pw.y - lower.y) / (upper.y - lower.y)

        ps = Vec2(u * w, (1.0 - v) * h)
        return ps

    def build_projection_matrix(self, z_bias=0.0):
        """Build projection matrix for rendering"""
        if self._matrix is not None:
            return self._matrix
        ratio = float(self.width) / float(self.height)
        extents = Vec2(self.zoom * ratio, self.zoom)

        # Vec2 operations
        lower = self.center - extents
        upper = self.center + extents

        w = upper.x - lower.x
        h = upper.y - lower.y

        matrix = np.zeros(16, dtype=np.float32)

        # Column-major order
        matrix[0] = 2.0 / w
        matrix[5] = 2.0 / h
        matrix[10] = -1.0
        matrix[12] = -2.0 * self.center.x / w
        matrix[13] = -2.0 * self.center.y / h
        matrix[14] = z_bias
        matrix[15] = 1.0
        self._matrix = matrix
        return matrix

    def get_view_bounds(self):
        """Get AABB in world coordinates of current view"""
        lower = self.convert_screen_to_world(Vec2(0.0, float(self.height)))
        upper = self.convert_screen_to_world(Vec2(float(self.width), 0.0))
        return AABB(lower, upper)


class GLDebugDraw(DebugDraw):
    def __init__(self):
        super().__init__()
        self.update_settings()

        self.camera = Camera()
        self.background = GLBackground(self.camera)
        self.circles = GLCircles(self.camera)
        self.solid_circles = GLSolidCircles(self.camera)
        self.solid_capsules = GLSolidCapsules(self.camera)
        self.solid_polygons = GLSolidPolygons(self.camera)
        self.points = GLPoints(self.camera)
        self.lines = GLLines(self.camera)
        # Add storage for debug strings
        self.debug_strings = []

    def update_settings(self):
        for key, value, _ in state.show_dd.get_current():
            self.__setattr__("draw_" + key, value)

    def start_frame(self):
        self._draw_start_time = time.perf_counter()  # start timing
        self.update_settings()
        self.background.draw()

    def end_frame(self):
        self.solid_circles.draw()
        self.solid_capsules.draw()
        self.solid_polygons.draw()
        self.circles.draw()
        self.lines.draw()
        self.points.draw()

        # Draw debug strings
        for pos, text, color in self.debug_strings:
            screen_pos = self.camera.convert_world_to_screen(Vec2(*pos))
            # Convert hex color to RGB float values
            r = ((color.hex >> 16) & 0xFF) / 255.0
            g = ((color.hex >> 8) & 0xFF) / 255.0
            b = (color.hex & 0xFF) / 255.0
            imgui.set_cursor_screen_pos((screen_pos.x, screen_pos.y))
            imgui.push_style_color(imgui.Col_.text, (r, g, b, 1.0))
            imgui.text(text)
            imgui.pop_style_color()
        self.debug_strings.clear()

        # Calculate and update draw performance metrics
        elapsed = (time.perf_counter() - self._draw_start_time) * 1000.0  # elapsed ms
        smoothing = state.perf.smoothing_avg
        state.perf.draw_ms = elapsed
        state.perf.draw_ms_avg *= smoothing
        state.perf.draw_ms_avg += elapsed * (1 - smoothing)
        state.perf.draw_ms_max = max(state.perf.draw_ms_max, elapsed)

    def draw_polygon(self, vertices: list, color):
        # Draw polygon outlines by connecting vertices in order
        n = len(vertices)
        for i in range(n):
            self.lines.add_line(vertices[i], vertices[(i + 1) % n], color.hex)

    def draw_solid_polygon(self, transform, vertices, count, radius: float, color):
        # Delegate to solid_polygons; pass the raw b2Transform from the Transform wrapper
        self.solid_polygons.add_polygon(transform, vertices, count, radius, color)

    def draw_circle(self, center, radius: float, color):
        # Queue border circle drawing
        self.circles.add_circle(center, radius, color.hex)

    def draw_segment(self, p1, p2, color):
        # Draw a line segment between two points
        self.lines.add_line(p1, p2, color.hex)

    def draw_point(self, p, size: float, color):
        # Draw a point as a small circle
        self.points.add_point(p, size, color.hex)

    def draw_string(self, p, s: str, color=Color(0xFFFFFF)):
        """Store debug string for rendering during end_frame"""
        self.debug_strings.append((p, s, color))

    def draw_capsule(self, p1, p2, radius: float, color):
        # Draw capsule outline by adding a capsule (the same as solid capsule here)
        self.solid_capsules.add_capsule(p1, p2, radius, color.hex)

    def draw_solid_capsule(self, p1, p2, radius: float, color):
        # Draw a filled capsule
        self.solid_capsules.add_capsule(p1, p2, radius, color.hex)

    def draw_solid_circle(self, transform, radius: float, color):
        # Queue solid circle drawing; pass the underlying b2Transform
        self.solid_circles.add_circle(transform, radius, color)

    def draw_transform(self, transform):
        # Draw coordinate axes. Use a fixed scale.
        scale = 0.5
        p = transform.p
        x_axis = transform((scale, 0))
        y_axis = transform((0, scale))
        self.lines.add_line(p, x_axis, 0xFF0000)  # red for x-axis
        self.lines.add_line(p, y_axis, 0x00FF00)  # green for y-axis

    def draw_debug_shapes(self):
        self.circles.add_circle(Vec2(0, 0), 0.5, 0x0000FF)
        self.circles.add_circle(Vec2(-0.5, 0), 0.1, 0x00FF00)
        self.circles.add_circle(Vec2(0.5, 0), 0.2, 0xFF0000)
        self.solid_circles.add_circle(
            Transform((0, 1), math.radians(45)).b2Transform[0], 0.4, 0x0000FF
        )
        self.solid_capsules.add_capsule(Vec2(-2, -2), Vec2(-1, -1), 0.2, 0x00FF00)

        # Test with CCW square (vertices ordered counter-clockwise)
        points = [
            Vec2(-0.5, -0.5),  # Bottom left
            Vec2(0.5, -0.5),  # Bottom right
            Vec2(0.5, 0.5),  # Top right
            Vec2(-0.5, 0.5),  # Top left
        ]
        transform = Transform((0, 2), math.radians(30))  # At origin, no rotation
        self.solid_polygons.add_polygon(transform.b2Transform[0], points, 0.1, 0xFF0000)
        self.points.add_point(Vec2(0, 0), 5, 0x0000FF)
        self.lines.add_line(Vec2(0.2, 0.3), Vec2(1, 1), 0x00FF00)
