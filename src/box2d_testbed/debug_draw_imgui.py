"""
A debug draw that renders through Dear ImGui's draw list.

The OpenGL renderer needs a real GL context, which ties the testbed to a
window: it cannot run under hello_imgui's null backend, and it cannot follow
the bindings into a browser, where there is no PyOpenGL. ImDrawList runs
wherever imgui does, which is all three.

Everything is submitted to the window's own draw list, so it clips to the
simulation window and needs no viewport handling. World coordinates are
converted here rather than by the camera's convert_world_to_screen, which
allocates two vectors and does four divisions per point; the mapping is
constant for a frame, so it is worked out once in start_frame and applied
as two multiplies per vertex.
"""

import time

from imgui_bundle import imgui

from box2d import Vec2
from box2d.debug_draw import Color, DebugDraw

from .debug_draw_gl import Camera
from .testbed_state import state


def pack_color(color, alpha=None):
    """A Color as the ABGR word ImDrawList wants.

    imgui packs alpha high and red low, which is the reverse of the RGB
    ordering Box2D's colours arrive in.
    """
    a = color.a if alpha is None else alpha
    return (a << 24) | (color.b << 16) | (color.g << 8) | color.r


class ImGuiDebugDraw(DebugDraw):
    """Draws the world with imgui primitives instead of OpenGL.

    A drop-in replacement for GLDebugDraw: same camera, same start_frame and
    end_frame, same primitive callbacks.
    """

    #: Filled shapes are drawn over each other constantly, so they are
    #: translucent to keep a pile readable, matching the GL renderer.
    FILL_ALPHA = 0x99

    def __init__(self):
        super().__init__()
        self.camera = Camera()
        self.debug_strings = []
        self._draw_list = None
        self._draw_start_time = 0.0
        # World-to-screen, recomputed each frame: screen = (world - _lower) * _scale
        self._lower = Vec2(0.0, 0.0)
        self._scale_x = 1.0
        self._scale_y = 1.0
        self._origin_x = 0.0
        self._origin_y = 0.0
        self._height = 0.0

    # --- frame ---------------------------------------------------------------

    def start_frame(self):
        self._draw_start_time = time.perf_counter()
        self.update_settings()

        # Called from inside the simulation window's gui function, so this is
        # that window: the draw list clips to it, and its position is the
        # origin the camera's screen coordinates are relative to.
        self._draw_list = imgui.get_window_draw_list()
        position = imgui.get_window_pos()
        self._origin_x, self._origin_y = position.x, position.y

        camera = self.camera
        ratio = float(camera.width) / float(camera.height)
        extents = Vec2(camera.zoom * ratio, camera.zoom)
        self._lower = camera.center - extents
        self._scale_x = float(camera.width) / (2.0 * extents.x)
        self._scale_y = float(camera.height) / (2.0 * extents.y)
        self._height = float(camera.height)

    def end_frame(self):
        for position, text, color in self.debug_strings:
            self._draw_list.add_text(self.to_screen(position), pack_color(color), text)
        self.debug_strings.clear()

        elapsed = (time.perf_counter() - self._draw_start_time) * 1000.0
        smoothing = state.perf.smoothing_avg
        state.perf.draw_ms = elapsed
        state.perf.draw_ms_avg *= smoothing
        state.perf.draw_ms_avg += elapsed * (1 - smoothing)
        state.perf.draw_ms_max = max(state.perf.draw_ms_max, elapsed)

    def update_settings(self):
        for key, value, _ in state.show_dd.get_current():
            name = "draw_" + key
            if not hasattr(type(self), name):
                raise AttributeError(
                    f"DebugDraw has no {name!r}; the settings and the renderer "
                    f"have drifted apart"
                )
            setattr(self, name, value)

    # --- coordinates ---------------------------------------------------------

    def to_screen(self, point):
        """One world point as an imgui screen position."""
        x = (point.x - self._lower.x) * self._scale_x + self._origin_x
        y = self._height - (point.y - self._lower.y) * self._scale_y + self._origin_y
        return (x, y)

    def to_screen_list(self, points):
        """Several world points at once, which is the hot path."""
        lower_x, lower_y = self._lower.x, self._lower.y
        scale_x, scale_y = self._scale_x, self._scale_y
        origin_x, origin_y = self._origin_x, self._origin_y
        height = self._height
        return [
            (
                (point.x - lower_x) * scale_x + origin_x,
                height - (point.y - lower_y) * scale_y + origin_y,
            )
            for point in points
        ]

    def to_pixels(self, length):
        """A world length as a pixel length."""
        return length * self._scale_x

    # --- primitives ----------------------------------------------------------

    def draw_polygon(self, transform, vertices, color):
        points = self.to_screen_list([transform(vertex) for vertex in vertices])
        self._draw_list.add_polyline(
            points, pack_color(color), 1.0, imgui.ImDrawFlags_.closed
        )

    def draw_solid_polygon(self, transform, vertices, radius, color):
        points = self.to_screen_list([transform(vertex) for vertex in vertices])
        fill = pack_color(color, self.FILL_ALPHA)
        self._draw_list.add_convex_poly_filled(points, fill)

        # Box2D's radius is a Minkowski sum: the shape is the hull grown
        # outwards by the radius, not inset. A polyline is centred on its
        # path, so a stroke of twice the radius reproduces that growth, with
        # the joins standing in for the true rounded corners.
        if radius > 0.0:
            self._draw_list.add_polyline(
                points, fill, 2.0 * self.to_pixels(radius), imgui.ImDrawFlags_.closed
            )
        self._draw_list.add_polyline(
            points, pack_color(color), 1.0, imgui.ImDrawFlags_.closed
        )

    def draw_circle(self, center, radius, color):
        self._draw_list.add_circle(
            self.to_screen(Vec2(center)), self.to_pixels(radius), pack_color(color)
        )

    def draw_solid_circle(self, transform, center, radius, color):
        placed = transform(Vec2(center))
        screen = self.to_screen(placed)
        pixels = self.to_pixels(radius)
        self._draw_list.add_circle_filled(
            screen, pixels, pack_color(color, self.FILL_ALPHA)
        )
        self._draw_list.add_circle(screen, pixels, pack_color(color))
        # A line to the rim, so a rolling circle visibly rolls.
        rim = self.to_screen(transform(Vec2(center) + Vec2(radius, 0.0)))
        self._draw_list.add_line(screen, rim, pack_color(color))

    def draw_solid_capsule(self, p1, p2, radius, color):
        # A capsule is a segment grown by the radius, so a stroke of twice the
        # radius is the shape itself rather than an outline of it.
        start, end = self.to_screen(Vec2(p1)), self.to_screen(Vec2(p2))
        pixels = self.to_pixels(radius)
        fill = pack_color(color, self.FILL_ALPHA)
        self._draw_list.add_line(start, end, fill, 2.0 * pixels)
        # add_line has flat ends; the caps are what make it a capsule.
        self._draw_list.add_circle_filled(start, pixels, fill)
        self._draw_list.add_circle_filled(end, pixels, fill)
        outline = pack_color(color)
        self._draw_list.add_circle(start, pixels, outline)
        self._draw_list.add_circle(end, pixels, outline)

    def draw_segment(self, p1, p2, color):
        self._draw_list.add_line(
            self.to_screen(Vec2(p1)), self.to_screen(Vec2(p2)), pack_color(color)
        )

    def draw_point(self, p, size, color):
        self._draw_list.add_circle_filled(
            self.to_screen(Vec2(p)), max(1.0, size * 0.5), pack_color(color)
        )

    def draw_string(self, p, s, color=Color(255, 255, 255, 255)):
        # Held until end_frame so text lands on top of the shapes.
        self.debug_strings.append((Vec2(p), s, color))

    def draw_bounds(self, aabb, color):
        lower = self.to_screen(aabb.lower)
        upper = self.to_screen(aabb.upper)
        self._draw_list.add_rect(
            (lower[0], upper[1]), (upper[0], lower[1]), pack_color(color)
        )

    def draw_transform(self, transform):
        origin = self.to_screen(transform.p)
        scale = 0.5
        self._draw_list.add_line(
            origin, self.to_screen(transform((scale, 0))), pack_color(Color(255, 0, 0))
        )
        self._draw_list.add_line(
            origin, self.to_screen(transform((0, scale))), pack_color(Color(0, 255, 0))
        )
