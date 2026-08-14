# tb_character.py

import math

from box2d import Vec2, Color, clip_vector, solve_planes

from .base_test import BaseTest, UI


class Mover(BaseTest, category="Character", name="Mover"):
    """A kinematic character controller built from the mover queries.

    The character is not a body. Each step it asks the world what a capsule at
    its position would run into, works out the movement satisfying all of those
    at once, and trims the parts of its velocity that point into them. That is
    what lets it stop dead against a wall, walk up a slope, and stand on a
    ledge without ever being tipped over by a solver.

    Move with the arrow keys, jump with space.
    """

    speed = UI.float(8.0, min=1.0, max=20.0)
    jump_speed = UI.float(10.0, min=1.0, max=30.0)
    gravity = UI.float(30.0, min=0.0, max=60.0)

    def setup(self):
        self.app_state.center = Vec2(0, 5)
        self.app_state.zoom = 16.0

        terrain = self.world.new_body().static()
        terrain.segment((-20, 0), (8, 0))  # ground
        terrain.box(1, 6, offset=(9, 3))  # wall on the right
        terrain.box(6, 0.5, offset=(-8, 3))  # a ledge to land on
        terrain.box(5, 0.3, offset=(3, 0.9), angle=math.radians(20))  # a ramp up
        terrain.build()

        # The character's own state. Nothing here is a Box2D body.
        self.position = Vec2(-14, 2)
        self.velocity = Vec2(0, 0)
        self.radius = 0.4
        self.height = 0.8
        self.on_ground = False
        self.held = set()

    def capsule(self, at=None):
        """The character's capsule endpoints, about a position."""
        at = self.position if at is None else at
        return (at.x, at.y - self.height / 2), (at.x, at.y + self.height / 2)

    def after_step(self, dt):
        if dt <= 0:
            return

        wanted = 0.0
        if "left" in self.held:
            wanted -= self.speed
        if "right" in self.held:
            wanted += self.speed
        self.velocity = Vec2(wanted, self.velocity.y - self.gravity * dt)

        point1, point2 = self.capsule()
        planes = self.world.collide_mover(point1, point2, self.radius)

        # Standing on something means one of the planes faces mostly upward.
        self.on_ground = any(plane.plane.normal.y > 0.7 for plane in planes)

        result = solve_planes(self.velocity * dt, planes)
        self.position = self.position + result.translation
        self.velocity = clip_vector(self.velocity, planes)

    def on_key_down(self, key):
        if key in ("left", "right"):
            self.held.add(key)
        elif key == "space" and self.on_ground:
            self.velocity = Vec2(self.velocity.x, self.jump_speed)

    def on_key_up(self, key):
        self.held.discard(key)

    def debug_draw(self, debug_draw):
        colour = Color(80, 220, 120) if self.on_ground else Color(220, 180, 60)
        point1, point2 = self.capsule()
        debug_draw.draw_solid_capsule(Vec2(point1), Vec2(point2), self.radius, colour)
        debug_draw.draw_string(
            (-15, 10),
            f"arrows to move, space to jump   "
            f"{'grounded' if self.on_ground else 'airborne'}   "
            f"v=({self.velocity.x:.1f}, {self.velocity.y:.1f})",
        )
