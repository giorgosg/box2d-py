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

import math
import time

from imgui_bundle import imgui

from box2d import AABB, Vec2
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


def expand_polygon(points, radius, segments_per_corner=None):
    """The Minkowski sum of a convex polygon and a disc, as one outline.

    Box2D's rounded polygons are the hull grown outwards by the radius, so
    the corners are arcs rather than points. Drawing that as a fill plus a
    thick stroke, which is the obvious approach, goes wrong twice over: the
    stroke overlaps the fill, and with translucent colours the overlap blends
    twice and draws a dark band inside every edge; and imgui's joins leave
    notches on the outside of each corner where the thick segments meet.

    Building the grown outline instead gives one convex polygon, filled once,
    with no overlap and no joins to go wrong.

    Args:
        points: The polygon, as screen-space (x, y) pairs.
        radius: How far to grow it, in pixels.
        segments_per_corner: Arc segments per corner. Derived from the radius
            when not given -- a 2px corner needs far fewer than a 40px one.

    Returns:
        list: The grown outline, in the same winding as the input.
    """
    count = len(points)
    if count < 3 or radius <= 0.0:
        return points

    # Which way the polygon winds decides which side is outside. Screen space
    # flips y, so this cannot be assumed from Box2D's winding.
    area = 0.0
    for index in range(count):
        x0, y0 = points[index]
        x1, y1 = points[(index + 1) % count]
        area += x0 * y1 - x1 * y0
    outward = 1.0 if area > 0.0 else -1.0

    if segments_per_corner is None:
        # Enough that the arc is smooth without being wasteful: a corner is
        # at most a quarter turn for a convex polygon with many sides.
        segments_per_corner = max(2, min(8, int(radius / 3.0) + 2))

    normals = []
    for index in range(count):
        x0, y0 = points[index]
        x1, y1 = points[(index + 1) % count]
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy)
        if length < 1e-9:
            normals.append((0.0, 0.0))
        else:
            normals.append((outward * dy / length, -outward * dx / length))

    grown = []
    for index in range(count):
        x, y = points[index]
        incoming = normals[index - 1]
        outgoing = normals[index]

        start = math.atan2(incoming[1], incoming[0])
        end = math.atan2(outgoing[1], outgoing[0])
        # Sweep the short way round, which for a convex corner is the
        # exterior angle.
        sweep = end - start
        while sweep > math.pi:
            sweep -= 2.0 * math.pi
        while sweep < -math.pi:
            sweep += 2.0 * math.pi

        for step in range(segments_per_corner + 1):
            angle = start + sweep * step / segments_per_corner
            grown.append((x + radius * math.cos(angle), y + radius * math.sin(angle)))
    return grown


class ImGuiDebugDraw(DebugDraw):
    """Draws the world with imgui primitives instead of OpenGL.

    A drop-in replacement for GLDebugDraw: same camera, same start_frame and
    end_frame, same primitive callbacks.
    """

    #: Filled shapes are drawn over each other constantly, so they are
    #: translucent to keep a pile readable, matching the GL renderer.
    FILL_ALPHA = 0x99

    #: Whether to let imgui anti-alias the world. Smoother, but it multiplies
    #: the geometry for every shape drawn.
    antialias = False

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
        if not self.antialias:
            # imgui anti-aliases fills and lines by default, which for a
            # scene of hundreds of shapes is a lot of extra geometry per
            # frame. The UI keeps its own draw list, so this only affects
            # the world.
            self._draw_list.flags &= ~(
                imgui.ImDrawListFlags_.anti_aliased_fill
                | imgui.ImDrawListFlags_.anti_aliased_lines
                | imgui.ImDrawListFlags_.anti_aliased_lines_use_tex
            )
        position = imgui.get_window_pos()
        self._origin_x, self._origin_y = position.x, position.y

        camera = self.camera
        ratio = float(camera.width) / float(camera.height)
        extents = Vec2(camera.zoom * ratio, camera.zoom)
        self._lower = camera.center - extents
        # Cull to what is on screen. Box2D queries its broad-phase tree with
        # this, so off-screen shapes cost nothing rather than being drawn and
        # clipped: on 7000 bodies that is 57ms against 6.7ms.
        self.drawing_bounds = AABB(lower=self._lower, upper=camera.center + extents)
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

    def transform_to_screen(self, transform, vertices):
        """Place local vertices by a transform and convert them, in one pass.

        The obvious spelling is [self.to_screen(transform(v)) for v in
        vertices], and it is the single most expensive thing this renderer
        did: profiling a scene of 291 shapes showed 734,664 Vec2 allocations
        per 120 frames, because every transform application builds several.
        The GL renderer never pays it -- it hands the transform to a shader
        and draws the local vertices untouched.

        So the rotation, the translation and the screen mapping are composed
        here and applied as plain floats, allocating nothing per vertex.
        """
        position = transform.p
        rotation = transform.q
        cos, sin = rotation.c, rotation.s
        px, py = position.x, position.y
        lower_x, lower_y = self._lower.x, self._lower.y
        scale_x, scale_y = self._scale_x, self._scale_y
        origin_x, origin_y = self._origin_x, self._origin_y
        height = self._height

        points = []
        for vertex in vertices:
            local_x, local_y = vertex.x, vertex.y
            world_x = px + cos * local_x - sin * local_y
            world_y = py + sin * local_x + cos * local_y
            points.append(
                (
                    (world_x - lower_x) * scale_x + origin_x,
                    height - (world_y - lower_y) * scale_y + origin_y,
                )
            )
        return points

    # --- primitives ----------------------------------------------------------

    def draw_polygon(self, transform, vertices, color):
        points = self.transform_to_screen(transform, vertices)
        self._draw_list.add_polyline(
            points, pack_color(color), 1.0, imgui.ImDrawFlags_.closed
        )

    def draw_solid_polygon(self, transform, vertices, radius, color):
        points = self.transform_to_screen(transform, vertices)
        if radius > 0.0:
            points = expand_polygon(points, self.to_pixels(radius))

        self._draw_list.add_convex_poly_filled(
            points, pack_color(color, self.FILL_ALPHA)
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
