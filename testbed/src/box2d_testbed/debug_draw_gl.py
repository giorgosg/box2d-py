from box2d import AABB, DebugDraw, Vec2, Transform, Color
from .camera import Camera
from .testbed_state import state
from .draw import GLBackground, GLCircles, GLPoints, GLLines
from .draw import GLSolidPolygons, GLSolidCircles, GLSolidCapsules
from imgui_bundle import imgui
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
        # Add storage for debug strings
        self.debug_strings = []

    def update_settings(self):
        for key, value, _ in state.show_dd.get_current():
            name = "draw_" + key
            # Plain setattr would quietly create an instance attribute if the
            # property were renamed, leaving the toggle dead in the UI.
            if not hasattr(type(self), name):
                raise AttributeError(
                    f"DebugDraw has no {name!r}; "
                    f"the {key!r} toggle would have no effect."
                )
            setattr(self, name, value)

    def start_frame(self):
        self._draw_start_time = time.perf_counter()  # start timing
        self.update_settings()

        # Cull to the visible region: Box2D queries its broad-phase tree with
        # this, so shapes off screen never reach a callback at all.
        camera = self.camera
        ratio = float(camera.width) / float(camera.height)
        extents = Vec2(camera.zoom * ratio, camera.zoom)
        self.drawing_bounds = AABB(
            lower=camera.center - extents, upper=camera.center + extents
        )
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
            screen_pos = self.camera.convert_world_to_screen(pos)
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

    # Box2D's callbacks always hand these Vec2s, but scenario code calls the
    # same methods and naturally writes (x, y). Every point argument is
    # normalised here so both work, matching the rest of the API.

    def draw_polygon(self, transform, vertices: list, color):
        # 3.2 passes vertices in local space, so transform them before drawing.
        points = [transform(Vec2(v)) for v in vertices]
        n = len(points)
        for i in range(n):
            self.lines.add_line(points[i], points[(i + 1) % n], color.hex)

    def draw_solid_polygon(self, transform, vertices, radius: float, color):
        # Delegate to solid_polygons; pass the raw b2Transform from the Transform wrapper
        self.solid_polygons.add_polygon(
            transform, vertices, len(vertices), radius, color.hex
        )

    def draw_bounds(self, aabb, color):
        # Box2D 3.2 routes AABBs here rather than through draw_polygon.
        lower, upper = aabb.lower, aabb.upper
        corners = (
            Vec2(lower.x, lower.y),
            Vec2(upper.x, lower.y),
            Vec2(upper.x, upper.y),
            Vec2(lower.x, upper.y),
        )
        for i in range(4):
            self.lines.add_line(corners[i], corners[(i + 1) % 4], color.hex)

    def draw_circle(self, center, radius: float, color):
        # Queue border circle drawing
        self.circles.add_circle(Vec2(center), radius, color.hex)

    def draw_segment(self, p1, p2, color):
        # Draw a line segment between two points
        self.lines.add_line(Vec2(p1), Vec2(p2), color.hex)

    def draw_point(self, p, size: float, color):
        # Draw a point as a small circle
        self.points.add_point(Vec2(p), size, color.hex)

    def draw_string(self, p, s: str, color=Color(255, 255, 255, 255)):
        """Store debug string for rendering during end_frame"""
        self.debug_strings.append((Vec2(p), s, color))

    def draw_solid_capsule(self, p1, p2, radius: float, color):
        # Draw a filled capsule
        self.solid_capsules.add_capsule(Vec2(p1), Vec2(p2), radius, color.hex)

    def draw_solid_circle(self, transform, center, radius: float, color):
        # 3.2 passes the centre separately; fold it into the transform's origin.
        placed = Transform(position=transform(Vec2(center)), rotation=transform.q)
        self.solid_circles.add_circle(placed.b2Transform, radius, color.hex)

    def draw_transform(self, transform):
        # Draw coordinate axes. Use a fixed scale.
        scale = 0.5
        p = transform.p
        x_axis = transform((scale, 0))
        y_axis = transform((0, scale))
        self.lines.add_line(p, x_axis, 0xFF0000)  # red for x-axis
        self.lines.add_line(p, y_axis, 0x00FF00)  # green for y-axis
