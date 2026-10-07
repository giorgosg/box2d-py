import math

from .base_test import UI, BaseTest


class BodyTypes(BaseTest, category="Bodies", name="Body Type"):
    """A platform switched between the three body types, with boxes riding it.

    A static body never moves, whatever lands on it. A kinematic body moves
    at the velocity it is given, and nothing that touches it pushes it back:
    here it patrols left and right at 2 m/s, and the boxes on it are carried
    along by friction alone. A dynamic body is moved by forces and contacts
    like the boxes are, so with nothing holding it up the platform falls to
    the ground, boxes and all.

    Body Type switches the platform in place: the scene is not rebuilt, so
    what happens next starts from wherever things are. Enable Sleep turns
    sleeping on or off for every body. The status line counts the boxes
    asleep, which they never are on a moving platform.
    """

    camera_center = (0, 8)
    camera_zoom = 14.0

    #: How fast the kinematic platform patrols, in m/s, and how far either
    #: side of x = 0 its middle goes before it turns back, in m.
    PATROL_SPEED = 2.0
    PATROL_LIMIT = 6.0
    #: Friction is what carries the boxes on a moving platform. Box2D's
    #: default.
    FRICTION = 0.6

    body_type = UI.select("kinematic", ["static", "kinematic", "dynamic"])
    enable_sleep = UI.bool(True)

    def setup(self):
        self.world.new_body().static().segment((-20, 0), (20, 0)).build()

        self.platform = (
            self.world.new_body()
            .kinematic()
            .position(0, 5)
            .enable_sleep(self.enable_sleep)
            .box(8, 1, friction=self.FRICTION)
            .build()
        )
        self.make_platform(self.body_type)

        # Four boxes dropped on it, half a metre apart. Any wider and the
        # outer ones come off: the platform moves on 1.3 m while they fall,
        # and at either end it turns round so sharply that a box skids about
        # as far along it before friction catches it up.
        cargo = (
            self.world.new_body()
            .dynamic()
            .enable_sleep(self.enable_sleep)
            .box(1, 1, friction=self.FRICTION)
        )
        self.cargo = [cargo.position(-2.25 + 1.5 * i, 8).build() for i in range(4)]

    def after_step(self, dt):
        # Only a kinematic platform is driven. Its velocity is all there is to
        # it, so turning it round at either end is a matter of reversing that.
        if self.platform.type == "kinematic":
            if self.platform.position.x > self.PATROL_LIMIT:
                self.platform.linear_velocity = (-self.PATROL_SPEED, 0)
            elif self.platform.position.x < -self.PATROL_LIMIT:
                self.platform.linear_velocity = (self.PATROL_SPEED, 0)

    def make_platform(self, body_type):
        """Make the platform ``body_type``, setting off on patrol if kinematic."""
        self.platform.type = body_type
        if body_type == "kinematic":
            # A kinematic body keeps the velocity it had, and nothing slows it
            # down: a platform switched while tumbling would turn forever.
            self.platform.linear_velocity = (self.PATROL_SPEED, 0)
            self.platform.angular_velocity = 0.0

    @body_type.callback
    def on_type_change(self, key, value):
        self.make_platform(value)

    @enable_sleep.callback
    def on_sleep_change(self, key, value):
        # Turning sleep off wakes a body that is asleep.
        for body in [self.platform, *self.cargo]:
            body.enable_sleep = value

    def status(self):
        asleep = sum(1 for box in self.cargo if not box.awake)
        return (
            f"platform: {self.platform.type}   cargo asleep: {asleep}/{len(self.cargo)}"
        )


class SetVelocity(BaseTest, category="Bodies", name="Set Velocity"):
    """Boxes launched by setting their velocity, rather than by a force.

    Setting a body's velocity gives it that motion at once, and gravity and
    contacts carry on from there. There is no force or impulse to work out
    from its mass first, which is why a jump, a dash or a projectile is
    usually done this way.

    Eight boxes are launched to the right together, each 5 degrees steeper
    than the one before, from 30 to 65 degrees, and spinning. Once every box
    has landed they are put back where they started and launched again.

    Speed, in m/s, and Spin, in rad/s, take effect at the next launch. The
    status line counts the launches.
    """

    camera_center = (0, 8)
    camera_zoom = 20.0

    #: The first box's launch angle, and how much steeper each next one is, in
    #: degrees.
    FIRST_ANGLE = 30
    ANGLE_STEP = 5

    speed = UI.float(12.0, min=1.0, max=40.0)
    spin = UI.float(8.0, min=-30.0, max=30.0)

    def setup(self):
        self.world.new_body().static().segment((-40, 0), (40, 0)).build()

        self.starts = [(-15 + 3 * i, 2) for i in range(8)]
        boxes = self.world.new_body().dynamic().box(1, 0.4)
        self.boxes = [boxes.position(*start).build() for start in self.starts]
        self.launches = 0
        self.launch()

    def launch(self):
        # From where they started, or each launch would carry them further
        # right, until they went off the end of the ground. A body given a
        # velocity is woken, so a box that has fallen asleep goes too.
        for i, (box, start) in enumerate(zip(self.boxes, self.starts)):
            box.position = start
            box.rotation = 0.0
            angle = math.radians(self.FIRST_ANGLE + self.ANGLE_STEP * i)
            box.linear_velocity = (
                self.speed * math.cos(angle),
                self.speed * math.sin(angle),
            )
            box.angular_velocity = self.spin
        self.launches += 1

    def after_step(self, dt):
        # Landed: low, and no longer rising or falling. Low as well, because
        # a box at the top of its arc is not rising or falling either.
        if all(
            box.position.y < 1.0 and abs(box.linear_velocity.y) < 0.5
            for box in self.boxes
        ):
            self.launch()

    def status(self):
        return f"launches: {self.launches}"
