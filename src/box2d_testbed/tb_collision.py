from box2d import Vec2, Color, ShapeProxy
from .base_test import BaseTest, UI
import random
import math


class RayCast(BaseTest, category="Collision", name="Ray Cast"):
    collisions = UI.int(1, min=1, max=5)

    def setup(self):
        self.ray_start = Vec2(-8, -2)
        self.ray_end = Vec2(6, 2)

        self.world.gravity = (0, 0)
        ground = self.world.new_body().static()
        for x, y in ((x, y) for x in range(-6, 6, 2) for y in range(-6, 6, 2)):
            shape = random.choice(["circle", "box", "segment", "capsule"])
            if shape == "circle":
                ground.circle(0.5, center=(x, y))
            elif shape == "box":
                ground.box(
                    0.7, 0.5, offset=(x, y), angle=random.uniform(0, 2 * math.pi)
                )
            elif shape == "segment":
                ground.segment((-0.5 + x, -0.5 + y), (0.5 + x, 0.5 + y))
            elif shape == "capsule":
                ground.capsule((-0.5 + x, -0.5 + y), (0.5 + x, 0.5 + y), radius=0.2)
        ground = ground.build()

    def on_mouse_down(self, pos):
        self.ray_start = pos

    def on_mouse_release(self, pos):
        self.ray_end = pos

    def on_mouse_drag(self, pos, rel):
        self.ray_end = pos

    def debug_draw(self, debug_draw):
        debug_draw.draw_segment(
            self.ray_start, self.ray_end, color=Color.from_b2HexColor(0x00FFFF)
        )
        translation = self.ray_end - self.ray_start
        first_only = True if self.collisions == 1 else False
        collisions = self.world.ray_cast(
            self.ray_start, translation, first_hit_only=first_only
        )
        for collision in collisions[: self.collisions]:
            debug_draw.draw_point(
                collision.point, 5, color=Color.from_b2HexColor(0xFF0000)
            )


class ShapeCast(BaseTest, category="Collision", name="Shape Cast"):
    """Sweeping a shape instead of a point.

    A ray finds what a point would hit, so it slips through any gap. Sweeping
    a shape of real size answers the question a character controller actually
    asks: will this fit, and where does it stop? Drag to aim, and widen the
    mover until it no longer clears the gap.
    """

    mover = UI.select("circle", ["circle", "box", "capsule"])
    size = UI.float(0.5, min=0.1, max=2.0)
    all_hits = UI.bool(False, label="Show all hits")

    def setup(self):
        self.cast_start = Vec2(-9, 5)
        self.cast_end = Vec2(9, -3)

        self.world.gravity = (0, 0)
        ground = self.world.new_body().static()
        # A wall with a gap, so the mover's width decides whether it passes.
        ground.box(0.6, 6, offset=(0, 5))
        ground.box(0.6, 6, offset=(0, -5))
        for x, y in ((-6, -4), (5, 3), (6, -5), (-5, 2)):
            ground.circle(0.8, center=(x, y))
        ground.segment((-10, -8), (10, -8))
        self.ground = ground.build()

    def build_proxy(self, at):
        if self.mover == "circle":
            return ShapeProxy.circle(self.size, center=at)
        if self.mover == "box":
            return ShapeProxy.box(self.size * 2, self.size * 2, center=at)
        return ShapeProxy.capsule(
            at - Vec2(0, self.size), at + Vec2(0, self.size), self.size
        )

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
            corners = self.build_proxy(at).points
            for a, b in zip(corners, corners[1:] + corners[:1]):
                debug_draw.draw_segment(a, b, color=color)
        else:
            debug_draw.draw_solid_capsule(
                at - Vec2(0, self.size), at + Vec2(0, self.size), self.size, color=color
            )

    def debug_draw(self, debug_draw):
        grey = Color.from_b2HexColor(0x808080)
        white = Color.from_b2HexColor(0xFFFFFF)
        red = Color.from_b2HexColor(0xFF0000)

        translation = self.cast_end - self.cast_start
        debug_draw.draw_segment(self.cast_start, self.cast_end, color=grey)
        self.draw_mover(debug_draw, self.cast_start, grey)

        hits = self.world.cast_shape(
            self.build_proxy(self.cast_start),
            translation,
            first_hit_only=not self.all_hits,
        )
        if not hits:
            # Nothing in the way: show the mover where it ends up.
            self.draw_mover(debug_draw, self.cast_end, white)
            debug_draw.draw_string(self.cast_end, "clear", color=white)
            return

        for hit in hits:
            debug_draw.draw_point(hit.point, 6, color=red)
            debug_draw.draw_segment(hit.point, hit.point + hit.normal, color=red)

        stopped_at = self.cast_start + translation * hits[0].fraction
        self.draw_mover(debug_draw, stopped_at, white)
