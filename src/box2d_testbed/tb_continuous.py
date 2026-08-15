# tb_continuous.py

import random

from box2d import Vec2

from .base_test import BaseTest, UI


class SkinnyBox(BaseTest, category="Continuous", name="Skinny Box"):
    """A thin box thrown down at a thin obstacle.

    Fast, thin geometry is where discrete collision fails: between two steps
    the box can pass clean through the post. Turning off continuous collision
    for the world shows exactly that, and the bullet flag asks Box2D to sweep
    the body against static geometry regardless.
    """

    # Framed by hand: the drop, the post and the floor together.
    camera_center = (0.0, 4.0)
    camera_zoom = 8.0

    continuous = UI.bool(True, label="World continuous")
    bullet = UI.bool(False)
    capsule = UI.bool(False)
    speed = UI.float(300.0, min=50.0, max=600.0)
    spin = UI.bool(True, label="Random spin")
    launch = UI.button("Launch")

    def setup(self):
        self.app_state.center = Vec2(1, 5)
        self.app_state.zoom = 25.0 * 0.25

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

    flipper_torque = UI.float(1000.0, min=100.0, max=5000.0)
    ball_speed = UI.float(20.0, min=5.0, max=60.0)
    serve = UI.button("Serve ball")

    def setup(self):
        self.app_state.center = Vec2(0, 9)
        self.app_state.zoom = 25.0 * 0.5

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
