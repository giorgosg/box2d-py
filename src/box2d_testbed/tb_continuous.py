# tb_continuous.py

import random


from .base_test import BaseTest, UI
from .human import Human
import math
from box2d import Vec2, Color


class SkinnyBox(BaseTest, category="Continuous", name="Skinny Box"):
    """A thin box thrown down at a thin obstacle.

    Fast, thin geometry is where discrete collision fails: between two steps
    the box can pass clean through the post. Turning off continuous collision
    for the world shows exactly that, and the bullet flag asks Box2D to sweep
    the body against static geometry regardless.
    """

    camera_center = (1, 5)
    camera_zoom = 25.0 * 0.25

    continuous = UI.bool(True, label="World continuous")
    bullet = UI.bool(False)
    capsule = UI.bool(False)
    speed = UI.float(300.0, min=50.0, max=600.0)
    spin = UI.bool(True, label="Random spin")
    launch = UI.button("Launch")

    def setup(self):

        # A thin floor is the case discrete collision misses: at 300 m/s a body
        # moves 5 units per step and can start above it and end below it.
        ground = self.world.new_body().static()
        ground.segment((-10, 0), (10, 0), friction=0.9)
        ground.box(0.2, 2.0, offset=(3, 1), friction=0.9)  # a post to clip
        self.ground = ground.build()

        self.world.enable_continuous = self.continuous
        self.projectile = None
        self.passed_through = 0
        self.launches = 0
        self.do_launch()

    def do_launch(self):
        # A control can be changed before setup has run, so this must not
        # assume the previous projectile exists yet.
        previous = getattr(self, "projectile", None)
        if previous is not None and previous.is_valid:
            previous.destroy()

        builder = (
            self.world.new_body()
            .dynamic()
            .position(0, 8)
            .angular_velocity(random.uniform(-50, 50) if self.spin else 0.0)
            .linear_velocity(0, -self.speed)
        )
        if self.capsule:
            builder.capsule((0, -1.0), (0, 1.0), radius=0.1)
        else:
            builder.box(0.2, 2.0)
        if self.bullet:
            builder.bullet()

        self.projectile = builder.build()
        self.launches += 1
        self.checked = False

    def after_step(self, dt):
        # Below the ground means it tunnelled rather than landed.
        if self.projectile and not self.checked and self.projectile.position.y < -1.0:
            self.passed_through += 1
            self.checked = True

    @launch.callback
    @bullet.callback
    @capsule.callback
    @speed.callback
    @spin.callback
    def on_relaunch(self, key, value):
        if hasattr(self, "ground"):
            self.do_launch()

    @continuous.callback
    def on_continuous_change(self, key, value):
        self.world.enable_continuous = value
        if hasattr(self, "ground"):
            self.do_launch()

    def debug_draw(self, debug_draw):
        debug_draw.draw_string(
            (-5, 11),
            f"launches: {self.launches}   tunnelled through: {self.passed_through}",
        )


class Pinball(BaseTest, category="Continuous", name="Pinball"):
    """A ball in a pinball table, with flippers on the arrow keys.

    The ball is a bullet and the table walls are a chain loop, which together
    are what stop something small and fast escaping the table between steps.
    """

    camera_center = (0, 9)
    camera_zoom = 25.0 * 0.5

    flipper_torque = UI.float(1000.0, min=100.0, max=5000.0)
    ball_speed = UI.float(20.0, min=5.0, max=60.0)
    serve = UI.button("Serve ball")

    def setup(self):

        ground = self.world.new_body().static()
        ground.chain(
            [(-8, 6), (-8, 20), (8, 20), (8, 6), (0, -2)],
            loop=True,
        )
        ground = ground.build()

        flippers = self.world.new_body().dynamic().enable_sleep(False).box(3.5, 0.4)
        self.left = flippers.position(-2, 0).build()
        self.right = flippers.position(2, 0).build()

        self.left_joint = self.world.add_revolute_joint(
            ground,
            self.left,
            local_anchor_a=(-2, 0),
            local_anchor_b=(0, 0),
            enable_motor=True,
            max_motor_torque=self.flipper_torque,
            enable_limit=True,
            lower_angle=-0.5,
            upper_angle=0.4,
            motor_speed=0.0,
        )
        self.right_joint = self.world.add_revolute_joint(
            ground,
            self.right,
            local_anchor_a=(2, 0),
            local_anchor_b=(0, 0),
            enable_motor=True,
            max_motor_torque=self.flipper_torque,
            enable_limit=True,
            lower_angle=-0.4,
            upper_angle=0.5,
            motor_speed=0.0,
        )

        self.ball = None
        self.serve_ball()

    def serve_ball(self):
        previous = getattr(self, "ball", None)
        if previous is not None and previous.is_valid:
            previous.destroy()
        self.ball = (
            self.world.new_body()
            .dynamic()
            .bullet()
            .position(1, 15)
            .linear_velocity(0, -self.ball_speed)
            .circle(radius=0.2, density=1.0, restitution=0.6)
            .build()
        )

    def after_step(self, dt):
        # A ball that escaped the table means continuous collision let it slip.
        if self.ball and self.ball.is_valid and self.ball.position.y < -10:
            self.serve_ball()

    def on_key_down(self, key):
        if key == "left":
            self.left_joint.motor_speed = 20.0
        elif key == "right":
            self.right_joint.motor_speed = -20.0

    def on_key_up(self, key):
        if key == "left":
            self.left_joint.motor_speed = -10.0
        elif key == "right":
            self.right_joint.motor_speed = 10.0

    @serve.callback
    @ball_speed.callback
    def on_serve(self, key, value):
        if hasattr(self, "left_joint"):
            self.serve_ball()

    @flipper_torque.callback
    def on_torque_change(self, key, value):
        for joint in (
            getattr(self, "left_joint", None),
            getattr(self, "right_joint", None),
        ):
            if joint is not None:
                joint.max_motor_torque = value

    def debug_draw(self, debug_draw):
        debug_draw.draw_string((-7, 19), "left and right arrows work the flippers")


class BounceHumans(BaseTest, category="Continuous", name="Bounce Humans"):
    """Ragdolls in a bouncy box, under gravity that swings around.

    Every wall has a restitution above one and the middle post has two, so
    nothing loses energy -- figures gain it on each bounce until the box is
    chaos. Continuous collision is what keeps them inside it at those speeds.

    Gravity rotates rather than pointing down, tracing the white line from the
    centre, so the pile never settles.
    """

    camera_center = (0, 0)
    camera_zoom = 12.0

    SPAWN_INTERVAL = 2.0
    MAX_HUMANS = 5

    def setup(self):
        walls = self.world.new_body().static()
        corners = [(-10, -10), (10, -10), (10, 10), (-10, 10)]
        for start, end in zip(corners, corners[1:] + corners[:1]):
            walls.segment(start, end, restitution=1.3, friction=0.1)
        # The post is livelier than the walls, so a figure that finds it is
        # thrown back harder than it arrived.
        walls.circle(2.0, center=(0, 0), restitution=2.0, friction=0.1)
        self.walls = walls.build()

        self.humans = []
        self.time = 0.0
        self.countdown = 0.0

    def after_step(self, dt):
        if len(self.humans) < self.MAX_HUMANS and self.countdown <= 0.0:
            self.humans.append(
                Human(
                    self.world,
                    (0, 5),
                    scale=1.0,
                    # Limp, with a weak spring: they should flail rather than
                    # hold a shape as they are thrown about.
                    friction_torque=0.0,
                    hertz=1.0,
                    damping_ratio=0.1,
                    group_index=len(self.humans) + 1,
                )
            )
            self.countdown = self.SPAWN_INTERVAL

        self.time += dt
        self.countdown -= dt
        self.world.gravity = self.gravity_direction() * 10.0

    def gravity_direction(self):
        """A slow Lissajous figure, so the pull never repeats for a while."""
        return Vec2(math.sin(0.5 * self.time), math.cos(self.time))

    def debug_draw(self, debug_draw):
        debug_draw.draw_segment(
            (0, 0),
            self.gravity_direction() * 3.0,
            color=Color(255, 255, 255, 255),
        )
