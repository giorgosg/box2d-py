# tb_bodies.py


from .base_test import BaseTest, UI


class BodyTypes(BaseTest, category="Bodies", name="Body Type"):
    """Switch a platform between the three body types while it runs.

    A static platform never moves. A kinematic one moves under its own velocity
    and is unaffected by what lands on it. A dynamic one is pushed around by
    everything, including the boxes riding it.
    """

    camera_center = (0, 8)
    camera_zoom = 14.0

    body_type = UI.select("kinematic", ["static", "kinematic", "dynamic"])
    enable_sleep = UI.bool(True)

    def setup(self):

        ground = self.world.new_body().static()
        ground.segment((-20, 0), (20, 0))
        ground.build()

        # An attached platform that slides back and forth.
        self.platform = (
            self.world.new_body()
            .kinematic()
            .position(-4, 5)
            .linear_velocity(2, 0)
            .box(8, 1, friction=0.6)
            .build()
        )
        self.platform.type = self.body_type

        # Cargo riding on it, so the difference between the types is visible.
        cargo = self.world.new_body().dynamic().box(1, 1, friction=0.6)
        self.cargo = [cargo.position(-5 + 2 * i, 8).build() for i in range(4)]

    def after_step(self, dt):
        # Only a kinematic platform patrols; the others are left to physics.
        if self.platform.type == "kinematic":
            if self.platform.position.x > 6:
                self.platform.linear_velocity = (-2, 0)
            elif self.platform.position.x < -6:
                self.platform.linear_velocity = (2, 0)

    @body_type.callback
    def on_type_change(self, key, value):
        self.platform.type = value
        self.platform.awake = True
        if value == "kinematic":
            self.platform.linear_velocity = (2, 0)

    @enable_sleep.callback
    def on_sleep_change(self, key, value):
        for body in self.world.bodies:
            body.enable_sleep = value
            if value is False:
                body.awake = True

    def debug_draw(self, debug_draw):
        asleep = sum(1 for b in self.cargo if not b.awake)
        debug_draw.draw_string(
            (-12, 12),
            f"platform is {self.platform.type}   cargo asleep: {asleep}/{len(self.cargo)}",
        )


class SetVelocity(BaseTest, category="Bodies", name="Set Velocity"):
    """Bodies launched by setting velocity directly rather than by forces.

    Assigning velocity overrides whatever the solver had planned, which is how
    a projectile or a dash is usually implemented. The bodies are re-launched
    whenever they fall out of view.
    """

    camera_center = (0, 8)
    camera_zoom = 20.0

    speed = UI.float(12.0, min=1.0, max=40.0)
    spin = UI.float(8.0, min=-30.0, max=30.0)

    def setup(self):

        self.world.new_body().static().segment((-40, 0), (40, 0)).build()

        launcher = self.world.new_body().dynamic().box(1, 0.4, density=1.0)
        self.bodies = [launcher.position(-15 + 3 * i, 2).build() for i in range(8)]
        self.launch()
        self.launches = 1

    def launch(self):
        import math

        for i, body in enumerate(self.bodies):
            angle = math.radians(30 + 5 * i)
            body.linear_velocity = (
                self.speed * math.cos(angle),
                self.speed * math.sin(angle),
            )
            body.angular_velocity = self.spin
            body.awake = True

    def after_step(self, dt):
        if all(
            b.position.y < 1.0 and abs(b.linear_velocity.y) < 0.5 for b in self.bodies
        ):
            self.launch()
            self.launches += 1

    def debug_draw(self, debug_draw):
        debug_draw.draw_string((-18, 16), f"launches: {self.launches}")
