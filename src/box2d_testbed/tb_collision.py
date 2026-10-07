import math
import random

from box2d import Color, ShapeProxy, Vec2

from .base_test import UI, BaseTest

RAY = Color.from_b2HexColor(0x00FFFF)
HIT = Color.from_b2HexColor(0xFF0000)
PATH = Color.from_b2HexColor(0x808080)
MOVER = Color.from_b2HexColor(0xFFFFFF)


class RayCast(BaseTest, category="Collision", name="Ray Cast"):
    """A ray cast through a grid of shapes, and the hits it reports.

    A ray cast asks which shapes a line from one point to another crosses.
    Each hit is a shape, the point where the ray enters it, the surface
    normal there, and how far along the ray that is, as a fraction. Asked
    for the first hit only, Box2D looks for the closest and nothing else;
    otherwise it reports every shape the ray crosses, nearest first.

    The red dots mark the hits: the closest at Max Hits 1, and at most that
    many otherwise. Press and drag to cast a ray from where you press to
    where you let go. The shapes are circles, boxes, segments and capsules,
    chosen at random but the same every time, on a static body, so there is
    nothing to drag.
    """

    camera_center = (-1, -1)
    camera_zoom = 7.5

    #: The shapes are laid out at random, but always from this seed, so the
    #: scene is the same every time it is built: opened again, or Reset.
    SEED = 1

    max_hits = UI.int(1, min=1, max=5)

    def setup(self):
        self.ray_start = Vec2(-8, -2)
        self.ray_end = Vec2(6, 2)

        # One of the four kinds of shape at each place on a grid, chosen at
        # random, and a box at a random angle. From a generator of its own,
        # rather than the random module's, which is shared: seeding that
        # would reseed it for everything else too.
        rng = random.Random(self.SEED)
        ground = self.world.new_body().static()
        for x in range(-6, 6, 2):
            for y in range(-6, 6, 2):
                kind = rng.choice(["circle", "box", "segment", "capsule"])
                if kind == "circle":
                    ground.circle(0.5, center=(x, y))
                elif kind == "box":
                    ground.box(
                        0.7, 0.5, offset=(x, y), angle=rng.uniform(0, 2 * math.pi)
                    )
                elif kind == "segment":
                    ground.segment((x - 0.5, y - 0.5), (x + 0.5, y + 0.5))
                else:
                    ground.capsule((x - 0.5, y - 0.5), (x + 0.5, y + 0.5), radius=0.2)
        ground.build()

    def cast(self):
        """The hits shown: the closest, or up to Max Hits, nearest first."""
        hits = self.world.ray_cast(
            self.ray_start,
            self.ray_end - self.ray_start,
            first_hit_only=self.max_hits == 1,
        )
        return hits[: self.max_hits]

    def on_mouse_down(self, pos):
        self.ray_start = pos

    def on_mouse_drag(self, pos, rel):
        self.ray_end = pos

    def on_mouse_release(self, pos):
        self.ray_end = pos

    def debug_draw(self, debug_draw):
        debug_draw.draw_segment(self.ray_start, self.ray_end, color=RAY)
        for hit in self.cast():
            debug_draw.draw_point(hit.point, 5, color=HIT)

    def status(self):
        hits = self.cast()
        if not hits:
            return "no hits"
        return f"hits: {len(hits)}   nearest {hits[0].fraction:.0%} of the way along"


class ShapeCast(BaseTest, category="Collision", name="Shape Cast"):
    """Sweeping a shape instead of a point.

    A ray finds what a point would hit, so it slips through any gap. Sweeping
    a shape of real size answers the question a character controller asks:
    will this fit, and where does it stop? Drag to aim, and widen the mover
    until it no longer clears the gap in the wall.

    The grey outline is the mover where the cast starts, the white one where
    it stops, and the red dots and lines are the hits and their normals. A
    hit is the shape run into, the point of contact, the normal, and the
    fraction of the way along the cast that the mover got.

    Mover picks the shape swept, and Size is its radius, or half its width
    for the box. A capsule stands upright, twice as tall as it is wide. Show
    all hits draws every shape the sweep would touch over its whole length,
    as if nothing stopped it; the mover still stops at the first. Press and
    drag to cast from where you press to where you let go.
    """

    camera_center = (0, 0)
    camera_zoom = 10.5

    mover = UI.select("circle", ["circle", "box", "capsule"])
    size = UI.float(0.5, min=0.1, max=2.0)
    all_hits = UI.bool(False, label="Show all hits")

    def setup(self):
        self.cast_start = Vec2(-9, 5)
        self.cast_end = Vec2(9, -3)

        ground = self.world.new_body().static()
        # A wall with a gap, so the mover's width decides whether it passes.
        ground.box(0.6, 6, offset=(0, 5))
        ground.box(0.6, 6, offset=(0, -5))
        for x, y in ((-6, -4), (5, 3), (6, -5), (-5, 2)):
            ground.circle(0.8, center=(x, y))
        ground.segment((-10, -8), (10, -8))
        ground.build()

    def proxy(self, at):
        """The mover as a shape proxy, centred on ``at``."""
        if self.mover == "circle":
            return ShapeProxy.circle(self.size, center=at)
        if self.mover == "box":
            return ShapeProxy.box(self.size * 2, self.size * 2, center=at)
        return ShapeProxy.capsule(
            at - Vec2(0, self.size), at + Vec2(0, self.size), self.size
        )

    def cast(self):
        """The hits, nearest first: only the first unless Show all hits."""
        return self.world.cast_shape(
            self.proxy(self.cast_start),
            self.cast_end - self.cast_start,
            first_hit_only=not self.all_hits,
        )

    def stopped_at(self, hits):
        """Where the mover's centre gets to: the first hit, or the end."""
        if not hits:
            return self.cast_end
        return self.cast_start + (self.cast_end - self.cast_start) * hits[0].fraction

    def on_mouse_down(self, pos):
        self.cast_start = pos

    def on_mouse_drag(self, pos, rel):
        self.cast_end = pos

    def on_mouse_release(self, pos):
        self.cast_end = pos

    def draw_mover(self, debug_draw, at, color):
        if self.mover == "circle":
            debug_draw.draw_circle(at, self.size, color=color)
        elif self.mover == "box":
            corners = self.proxy(at).points
            for a, b in zip(corners, corners[1:] + corners[:1]):
                debug_draw.draw_segment(a, b, color=color)
        else:
            debug_draw.draw_solid_capsule(
                at - Vec2(0, self.size), at + Vec2(0, self.size), self.size, color=color
            )

    def debug_draw(self, debug_draw):
        debug_draw.draw_segment(self.cast_start, self.cast_end, color=PATH)
        self.draw_mover(debug_draw, self.cast_start, PATH)

        hits = self.cast()
        for hit in hits:
            debug_draw.draw_point(hit.point, 6, color=HIT)
            debug_draw.draw_segment(hit.point, hit.point + hit.normal, color=HIT)
        self.draw_mover(debug_draw, self.stopped_at(hits), MOVER)

    def status(self):
        hits = self.cast()
        if not hits:
            return "clear"
        stopped = f"stopped {hits[0].fraction:.0%} of the way"
        if self.all_hits:
            return f"{stopped}   shapes in the way: {len(hits)}"
        return stopped
