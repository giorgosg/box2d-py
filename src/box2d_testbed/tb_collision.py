from box2d import World, Vec2, Color
from .base_test import BaseTest, UI
import random
import math
import itertools


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
        debug_draw.draw_segment(self.ray_start, self.ray_end, color=Color(0x00FFFF))
        translation = self.ray_end - self.ray_start
        first_only = True if self.collisions == 1 else False
        collisions = self.world.ray_cast(
            self.ray_start, translation, first_hit_only=first_only
        )
        for collision in collisions[: self.collisions]:
            debug_draw.draw_point(collision.point, 5, color=Color(0xFF0000))
