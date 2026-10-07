import math
import random

from box2d import Color, Vec2

from .base_test import UI, BaseTest
from .human import Human


class SkinnyBox(BaseTest, category="Continuous", name="Skinny Box"):
    """A thin box thrown down at a thin obstacle.

    Fast, thin geometry is where discrete collision fails: between two steps
    the box can pass clean through the post. Turning off continuous collision
    for the world shows exactly that, and the bullet flag asks Box2D to sweep
    the body against static geometry regardless.
    """

    camera_center = (1, 5)
    camera_zoom = 6.25

    continuous = UI.bool(True, label="World continuous")
    bullet = UI.bool(False)
    capsule = UI.bool(False)
    speed = UI.float(300.0, min=50.0, max=600.0)
    spin = UI.bool(True, label="Random spin")
    launch = UI.button("Launch")

    def setup(self):
        # A thin floor is the case discrete collision misses: at 300 m/s a body
        # moves 5 units per step and can start above it and end below it.
        (
            self.world.new_body()
            .static()
            .segment((-10, 0), (10, 0), friction=0.9)
            .box(0.2, 2.0, offset=(3, 1), friction=0.9)
            .build()
        )

        self.world.enable_continuous = self.continuous
        self.projectile = None
        self.passed_through = 0
        self.launches = 0
        self.do_launch()

    def do_launch(self):
        if self.projectile is not None:
            self.projectile.destroy()

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
        if not self.checked and self.projectile.position.y < -1.0:
            self.passed_through += 1
            self.checked = True

    @launch.callback
    @bullet.callback
    @capsule.callback
    @speed.callback
    @spin.callback
    def on_relaunch(self, key, value):
        self.do_launch()

    @continuous.callback
    def on_continuous_change(self, key, value):
        self.world.enable_continuous = value
        self.do_launch()

    def status(self):
        return f"launches: {self.launches}   tunnelled through: {self.passed_through}"


class Pinball(BaseTest, category="Continuous", name="Pinball"):
    """A ball in a pinball table, with a flipper on each arrow key.

    The ball is a bullet. Box2D sweeps every fast body's path against static
    bodies, so nothing passes through the walls, but only a bullet's against
    other dynamic bodies too: without the flag a fast enough ball could pass
    through a flipper between two steps. The table is one chain loop, so the
    ball runs along its walls without catching on the corners between them.

    The left and right arrow keys work the flippers. Flipper Torque is the
    most torque each flipper's motor may use, in N m. Ball Speed is how fast
    a ball is served, in m/s; changing it serves a new one, as Serve Ball
    does.
    """

    camera_center = (0, 9)
    camera_zoom = 12.5

    #: How fast a flipper swings up while its key is held, and back down once
    #: it is let go, in rad/s. Box2D's values.
    FLIP_SPEED = 20.0
    RETURN_SPEED = 10.0

    flipper_torque = UI.float(1000.0, min=100.0, max=5000.0)
    ball_speed = UI.float(20.0, min=5.0, max=60.0)
    serve = UI.button("Serve ball")

    def setup(self):
        ground = (
            self.world.new_body()
            .static()
            .chain([(-8, 6), (-8, 20), (8, 20), (8, 6), (0, -2)], loop=True)
            .build()
        )

        # Each flipper turns about its middle, which is on the wall, between
        # limits that leave its inner end down at rest and up when flipped.
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
            lower_limit=-0.5,
            upper_limit=0.4,
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
            lower_limit=-0.4,
            upper_limit=0.5,
            motor_speed=0.0,
        )

        self.ball = None
        self.serve_ball()

    def serve_ball(self):
        if self.ball is not None:
            self.ball.destroy()
        self.ball = (
            self.world.new_body()
            .dynamic()
            .bullet()
            .position(1, 15)
            .linear_velocity(0, -self.ball_speed)
            .circle(radius=0.2, density=1.0, restitution=0.6)
            .build()
        )

    def on_key_down(self, key):
        # The left flipper swings up anticlockwise, the right one clockwise.
        if key == "left":
            self.left_joint.motor_speed = self.FLIP_SPEED
        elif key == "right":
            self.right_joint.motor_speed = -self.FLIP_SPEED

    def on_key_up(self, key):
        if key == "left":
            self.left_joint.motor_speed = -self.RETURN_SPEED
        elif key == "right":
            self.right_joint.motor_speed = self.RETURN_SPEED

    @serve.callback
    @ball_speed.callback
    def on_serve(self, key, value):
        self.serve_ball()

    @flipper_torque.callback
    def on_torque_change(self, key, value):
        self.left_joint.max_motor_torque = value
        self.right_joint.max_motor_torque = value

    def status(self):
        return "left and right arrows work the flippers"


class BounceHumans(BaseTest, category="Continuous", name="Bounce Humans"):
    """Ragdolls in a bouncy box, under gravity that swings around.

    The walls have a restitution of 1.3 and the post in the middle 2, so a
    figure comes off every bounce faster than it hit, and only what its own
    joints soak up holds it in check: the figures reach about 30 m/s.
    Continuous collision is what keeps them in the box at those speeds --
    turn off the testbed's Continuous Collision and a limb is through a wall
    within seconds.

    Gravity does not point down. It swings to and fro, in direction and in
    strength, along the tip of the white line from the centre, so the pile
    never settles. A figure drops in every two seconds, up to five.
    """

    camera_center = (0, 0)
    camera_zoom = 12.0

    #: A new figure every two seconds, up to five.
    SPAWN_INTERVAL = 2.0
    MAX_HUMANS = 5

    def setup(self):
        walls = self.world.new_body().static()
        corners = [(-10, -10), (10, -10), (10, 10), (-10, 10)]
        for start, end in zip(corners, corners[1:] + corners[:1]):
            walls.segment(start, end, restitution=1.3, friction=0.1)
        walls.circle(2.0, center=(0, 0), restitution=2.0, friction=0.1)
        walls.build()

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
                    # Each figure its own group, so that they collide with
                    # each other but not with themselves.
                    group_index=len(self.humans) + 1,
                )
            )
            self.countdown = self.SPAWN_INTERVAL

        self.time += dt
        self.countdown -= dt
        self.world.gravity = self.gravity_direction() * 10.0

    def gravity_direction(self):
        """The pull of gravity now, as a multiple of 10 m/s^2.

        x is sin(t/2) and y is cos(t), which is 1 - 2x^2, so the tip runs to
        and fro along a parabola: from straight up at full strength, round to
        down and to the right at 1.4 times it, back up, round to down and to
        the left, and up again, every 4 pi seconds.
        """
        return Vec2(math.sin(0.5 * self.time), math.cos(self.time))

    def debug_draw(self, debug_draw):
        debug_draw.draw_segment(
            (0, 0),
            self.gravity_direction() * 3.0,
            color=Color(255, 255, 255, 255),
        )
