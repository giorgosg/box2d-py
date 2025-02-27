from OpenGL.GL import *
from box2d import DebugDraw, Vec2, Transform
from .testbed_state import state
from .draw import GLBackground, Camera, GLCircles, GLPoints, GLLines
from .draw import GLSolidPolygons, GLSolidCircles, GLSolidCapsules
import math
import time


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

    def draw_solid_polygon(self, transform, vertices: list, radius: float, color):
        # Delegate to solid_polygons; pass the raw b2Transform from the Transform wrapper
        self.solid_polygons.add_polygon(
            transform.b2Transform[0], vertices, radius, color.hex
        )

    def draw_circle(self, center, radius: float, color):
        # Queue border circle drawing
        self.circles.add_circle(center, radius, color.hex)

    def draw_segment(self, p1, p2, color):
        # Draw a line segment between two points
        self.lines.add_line(p1, p2, color.hex)

    def draw_point(self, p, size: float, color):
        # Draw a point as a small circle (or use point API)
        self.points.add_point(p, size, color.hex)

    def draw_string(self, p, s: str, color):
        # Render debug string.
        # For simplicity, here we print, but a real implementation would use proper text rendering.
        print(f"Debug string at {p}: {s} (color: {hex(color.hex)})")

    def draw_capsule(self, p1, p2, radius: float, color):
        # Draw capsule outline by adding a capsule (the same as solid capsule here)
        self.solid_capsules.add_capsule(p1, p2, radius, color.hex)

    def draw_solid_capsule(self, p1, p2, radius: float, color):
        # Draw a filled capsule
        self.solid_capsules.add_capsule(p1, p2, radius, color.hex)

    def draw_solid_circle(self, transform, radius: float, color):
        # Queue solid circle drawing; pass the underlying b2Transform
        self.solid_circles.add_circle(transform.b2Transform[0], radius, color.hex)

    def draw_transform(self, transform):
        # Draw coordinate axes. Use a fixed scale.
        scale = 0.5
        p = transform.position
        # Assume rotation components provided by transform.rotation.x_axis and .y_axis:
        # If not available, you can compute them via math.cos and math.sin
        x_axis = transform.rotation.x_axis
        y_axis = transform.rotation.y_axis
        self.lines.add_line(p, p + x_axis * scale, 0xFF0000)  # red for x-axis
        self.lines.add_line(p, p + y_axis * scale, 0x00FF00)  # green for y-axis

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
