import math
from itertools import pairwise

from box2d import Color, Transform, Vec2

from .base_test import UI, BaseTest
from .human import Human
from .shared import Car, donut, random_polygon


class BallAndChain(BaseTest, category="Joints", name="Ball and Chain"):
    """Thirty capsule links pinned end to end, with a heavy ball on the last.

    The chain starts out straight and level, pinned to the ground at its left
    end, and is let go. The ball weighs several times as much as the whole
    chain, so it swings down and through like a pendulum bob and the chain
    trails after it.

    The links' pins turn freely, and only the ball's pin has friction. Box2D's
    own sample gives every pin the same friction, which makes a stiffer chain.
    """

    camera_center = (2.02, -1.99)
    camera_zoom = 21.76

    def setup(self):
        count = 30
        half_length = 0.5
        y = count * half_length

        ground = self.world.new_body().static().build()

        link = (
            self.world.new_body()
            .dynamic()
            .capsule((-half_length, 0), (half_length, 0), radius=0.125, density=20.0)
        )
        previous = ground
        for i in range(count):
            x = (1.0 + 2.0 * i) * half_length
            body = link.position(x, y).build()
            self.world.add_revolute_joint(previous, body, anchor=(x - half_length, y))
            previous = body

        radius = 4.0
        ball = (
            self.world.new_body()
            .dynamic()
            .position((1.0 + 2.0 * count) * half_length + radius - half_length, y)
            .circle(radius=radius, density=20.0)
            .build()
        )
        # A motor held at zero speed resists turning up to its torque: joint
        # friction.
        self.world.add_revolute_joint(
            previous,
            ball,
            anchor=(2.0 * count * half_length, y),
            enable_motor=True,
            max_motor_torque=100.0,
        )


class SoftBody(BaseTest, category="Joints", name="Soft Body"):
    """A ring of capsules welded into a donut, dropped onto the ground.

    The welds hold their length rigidly but are springs in angle, so the ring
    squashes flat when it lands and the springs pull it back round. Raise the
    hertz for a stiffer ring that barely dents; lower the damping and it
    wobbles for longer once it bounces.

    Segments rebuilds the ring; the spring sliders retune it as it is.
    """

    segments = UI.int(30, min=4, max=100)
    hertz = UI.float(12.0, min=1.0, max=200.0)
    damping = UI.float(2.0, min=0.0, max=10.0)

    def setup(self):
        self.world.new_body().static().position(0, -5).box(100, 1).build()
        _, self.joints = donut(
            self.world,
            position=(0, 50),
            radius=5,
            segments=self.segments,
            hertz=self.hertz,
            damping_ratio=self.damping,
        )

    @segments.callback
    def on_segments_change(self, key, value):
        self.rebuild()

    @hertz.callback
    @damping.callback
    def on_spring_change(self, key, value):
        for joint in self.joints:
            joint.angular_damping_ratio = self.damping
            joint.angular_hertz = self.hertz


class Arrow(BaseTest, category="Joints", name="Arrow"):
    """A volley of arrows fired at a stack of boxes.

    Each arrow is two bodies welded together: a heavy shaft with its head, and
    a light fletching at the tail. The fletching has linear damping, a crude
    air drag acting at the back of the arrow, and that is what turns each
    arrow to point along its flight as it arcs over, the way fletching does.
    The arrows leave at angles from 45 degrees down to 85 degrees up.
    """

    def setup(self):
        self.world.new_body().static().position(0, -5).box(100, 1).build()

        box = self.world.new_body().dynamic().box(0.5, 0.5)
        for i in range(30):
            box.position(20, -4.25 + 0.5 * i).build()

        speed = 20
        angles = range(-45, 90, 10)
        for i, degrees in enumerate(angles):
            position = (-10, 15 + i)
            rotation = math.radians(degrees)
            velocity = Vec2(speed, 0).rotate(rotation)
            shaft = (
                self.world.new_body()
                .dynamic()
                .position(*position)
                .rotation(rotation)
                .box(1, 0.1)
                .polygon(([0.7, 0], [0.5, 0.2], [0.5, -0.2]))
                .linear_velocity(*velocity)
                .angular_damping(1)
                .build()
            )
            fletching = (
                self.world.new_body()
                .dynamic()
                .position(*position)
                .rotation(rotation)
                .polygon(((-0.4, 0), (-0.5, 0.1), (-0.5, -0.1)), density=1)
                .linear_damping(1)
                .linear_velocity(*velocity)
                .build()
            )
            # Both bodies share a position, so their origins are the anchor.
            self.world.add_weld_joint(
                shaft, fletching, local_anchor_a=(0, 0), local_anchor_b=(0, 0)
            )


class Bridge(BaseTest, category="Joints", name="Bridge"):
    """A hundred planks pinned edge to edge, with a load dropped onto them.

    Both ends are pinned to the ground and everything between hangs from
    them, so the bridge sags into a curve under its own weight and dips
    where the balls and polygons land. Each pin has a friction motor: without
    it the bridge would sway for a long time after every impact, and with it
    the planks settle. They feel half gravity, which keeps the sag shallow.
    """

    def setup(self):
        ground = self.world.new_body().static().build()

        count = 100
        plank_width = 1.0
        left_end = -0.5 * count * plank_width
        y = 10.0
        plank = (
            self.world.new_body()
            .dynamic()
            .gravity_scale(0.5)
            .box(plank_width, 0.2, density=20)
        )
        planks = [
            plank.position(left_end + (i + 0.5) * plank_width, y).build()
            for i in range(count)
        ]

        # A motor held at zero speed resists turning up to its torque: joint
        # friction.
        friction = {"enable_motor": True, "max_motor_torque": 200}
        for i, (left, right) in enumerate(pairwise(planks)):
            pin = (left_end + (i + 1) * plank_width, y)
            self.world.add_revolute_joint(left, right, anchor=pin, **friction)
        self.world.add_revolute_joint(
            ground, planks[0], anchor=(left_end, y), **friction
        )
        self.world.add_revolute_joint(
            ground, planks[-1], anchor=(-left_end, y), **friction
        )

        ball = self.world.new_body().dynamic().circle(0.5, density=10)
        for x in range(-10, 10, 2):
            ball.position(x, 20).build()
        for x in range(-11, 11, 2):
            polygon = random_polygon(0.5)
            (
                self.world.new_body()
                .dynamic()
                .position(x, 20)
                .polygon(polygon.vertices, polygon.radius, density=10)
                .build()
            )


class UserConstraint(BaseTest, category="Joints", name="User Constraint"):
    """A constraint written in Python rather than provided by Box2D.

    The box hangs by two ropes from the point (3, 0), one to each of its
    right-hand corners. No joint holds it: after every step, ``after_step``
    works out how fast each rope is being stretched and changes the box's
    velocities to resist it, which is how Box2D's own joints are solved. Each
    rope has a slack length of 1 and is drawn cyan while slack, magenta while
    taut; the status line shows the tension in each.

    The constraint is soft, a spring at 3 hertz, so the box bounces on its
    ropes before it settles.
    """

    ANCHOR = Vec2(3.0, 0.0)
    #: Where the ropes attach, in the box's own frame: its right-hand corners.
    LOCAL_ANCHORS = (Vec2(1.0, -0.5), Vec2(1.0, 0.5))
    SLACK_LENGTH = 1.0

    def setup(self):
        self.body = (
            self.world.new_body()
            .dynamic()
            .box(2.0, 1.0, density=20.0)
            .angular_damping(0.5)
            .linear_damping(0.2)
            .build()
        )
        self.tension = [0.0, 0.0]

    def after_step(self, dt):
        # The soft-constraint coefficients Box2D uses for its own joints: a
        # spring of this stiffness and damping, solved stably at this dt.
        hertz = 3.0
        damping = 0.7
        omega = 2.0 * math.pi * hertz
        sigma = 2.0 * damping + dt * omega
        s = dt * omega * sigma
        impulse_coefficient = 1.0 / (1.0 + s)
        mass_coefficient = s * impulse_coefficient
        bias_coefficient = omega / sigma
        max_force = 1000.0

        mass = self.body.mass
        inv_mass = 1.0 / mass if mass > 0.0001 else 0.0
        inertia = self.body.rotational_inertia
        inv_inertia = 1.0 / inertia if inertia > 0.0001 else 0.0

        center = self.body.transform((0, 0))
        velocity = self.body.linear_velocity
        angular_velocity = self.body.angular_velocity

        for i, local_anchor in enumerate(self.LOCAL_ANCHORS):
            anchor = self.body.transform(local_anchor)
            delta = anchor - self.ANCHOR
            length = delta.length
            if length < 0.001 or length < self.SLACK_LENGTH:
                self.tension[i] = 0.0
                continue

            axis = delta.normalize()
            r = anchor - center
            j_rot = r.cross(axis)
            k = inv_mass + j_rot * inv_inertia * j_rot
            inv_k = 1.0 / k if k > 0.0001 else 0.0

            c = length - self.SLACK_LENGTH
            c_dot = (
                velocity + Vec2(-angular_velocity * r.y, angular_velocity * r.x)
            ).dot(axis)
            impulse = -mass_coefficient * inv_k * (c_dot + bias_coefficient * c)
            impulse = max(impulse, -max_force * dt)

            p = axis * impulse
            velocity += p * inv_mass
            angular_velocity += inv_inertia * r.cross(p)
            # The impulse pulls the box towards the anchor, so it is negative.
            self.tension[i] = -impulse / dt

        self.body.linear_velocity = velocity
        self.body.angular_velocity = angular_velocity

    def debug_draw(self, debug_draw):
        # The world's axes, at the point the box starts from.
        debug_draw.draw_transform(Transform(Vec2(0, 0), 0.0))
        for local_anchor in self.LOCAL_ANCHORS:
            anchor = self.body.transform(local_anchor)
            taut = (anchor - self.ANCHOR).length >= self.SLACK_LENGTH
            color = 0xFF00FF if taut else 0x00FFFF
            debug_draw.draw_segment(self.ANCHOR, anchor, Color.from_b2HexColor(color))

    def status(self):
        return f"rope tension {self.tension[0]:.1f}, {self.tension[1]:.1f} N"


class PrismaticJoint(BaseTest, category="Joints", name="Prismatic Joint"):
    """A tall box that may only slide along a diagonal, with a limit, a motor
    and a spring to switch on.

    It starts with only the limit on, so the box slides down the diagonal
    under gravity and stops 10 m along it. The motor drives it at a set speed,
    but only as hard as its maximum force: below about 28 N, the part of the
    box's weight that acts along the diagonal, it cannot lift the box at all.
    The spring pulls the box back towards where it started. The status line
    shows where along the axis the box is and how hard the motor is pushing.
    """

    enable_limit = UI.bool(True)
    enable_motor = UI.bool(False)
    max_force = UI.float(50.0, min=0.0, max=200.0)
    motor_speed = UI.float(10.0, min=-40.0, max=40.0)
    enable_spring = UI.bool(False)
    spring_hertz = UI.float(2, min=0, max=10)
    spring_damping = UI.float(0.1, min=0, max=2)

    def setup(self):
        ground = self.world.new_body().static().build()
        body = self.world.new_body().dynamic().position(0, 10).box(1, 4).build()
        self.joint = self.world.add_prismatic_joint(
            ground,
            body,
            anchor=(0, 9),
            axis=Vec2(1, 1).normalize(),
            enable_limit=self.enable_limit,
            lower_limit=-10,
            upper_limit=10,
            enable_motor=self.enable_motor,
            max_motor_force=self.max_force,
            motor_speed=self.motor_speed,
            enable_spring=self.enable_spring,
            spring_damping_ratio=self.spring_damping,
            spring_hertz=self.spring_hertz,
        )

    @enable_limit.callback
    @enable_motor.callback
    @max_force.callback
    @motor_speed.callback
    @enable_spring.callback
    @spring_hertz.callback
    @spring_damping.callback
    def on_change(self, key, value):
        self.joint.enable_limit = self.enable_limit
        self.joint.enable_motor = self.enable_motor
        self.joint.max_motor_force = self.max_force
        self.joint.motor_speed = self.motor_speed
        self.joint.enable_spring = self.enable_spring
        self.joint.spring_damping_ratio = self.spring_damping
        self.joint.spring_hertz = self.spring_hertz
        # A box at rest is asleep, and would not notice the change.
        self.joint.wake_bodies()

    def status(self):
        return [
            f"translation {self.joint.joint_translation:.2f} m",
            f"motor force {self.joint.motor_force:.1f} N",
        ]


class Driving(BaseTest, category="Joints", name="Driving"):
    """A car on sprung wheels, driven over hills, a seesaw and a bridge.

    The car is two wheel joints: each wheel slides on a spring along the
    chassis's up axis, which is the suspension, and turns on a motor, which
    is the drive. Hold A to drive left or D to drive right; hold S to brake.
    Letting go takes the motor off, and the car rolls freely.

    The sliders set the suspension's stiffness and damping, and the speed and
    torque the motors drive at. Too little torque and the car stalls on the
    first big hill. The camera follows the car.
    """

    camera_center = (0.0, 0.0)
    camera_zoom = 20.0

    hertz = UI.float(5.0, min=0.0, max=20.0)
    damping = UI.float(0.7, min=0.0, max=10.0)
    speed = UI.float(35.0, min=0.0, max=100.0)
    torque = UI.float(5.0, min=0.0, max=10.0)

    def setup(self):
        # The ground, from left to right: a wall, then the flat the car
        # starts on.
        points = [(-20, -20), (-20, 0), (20, 0)]
        # Two runs of hills and dips, a point every 5 m.
        heights = [0.25, 1.0, 4.0, 0.0, 0.0, -1.0, -2.0, -2.0, -1.25, 0.0]
        x = 20.0
        for _ in range(2):
            for h in heights:
                x += 5.0
                points.append((x, h))
        points += [
            (x + 40, 0),  # a flat run up to the bridge
            (x + 40, -20),  # down into the gap the bridge spans
            (x + 80, 0),  # a slope back up, under the bridge, to its far end
            (x + 120, 0),  # flat past the stack of boxes
            (x + 140, 0),
            (x + 150, 5),  # a ramp up and down again
            (x + 160, 0),
            (x + 200, 0),  # a last flat stretch
            (x + 200, 20),  # and a wall
        ]
        # Reversed so the solid side faces up. The first and last points are
        # passed as ghosts, which only tell the end segments what lies beyond
        # them, so neither wall is actually there.
        points = points[::-1]
        ground = (
            self.world.new_body()
            .static()
            .chain(points[1:-1], ghost1=points[0], ghost2=points[-1])
            .build()
        )

        # A seesaw on the flat before the bridge, started tipping.
        pivot = (140.0, 1.0)
        seesaw = (
            self.world.new_body()
            .dynamic()
            .position(*pivot)
            .angular_velocity(1.0)
            .box(20.0, 0.5)
            .build()
        )
        self.world.add_revolute_joint(
            ground,
            seesaw,
            anchor=pivot,
            enable_limit=True,
            lower_limit=math.radians(-18),
            upper_limit=math.radians(18),
        )

        # A rope bridge of twenty capsules over the gap.
        previous = ground
        for i in range(20):
            segment = (
                self.world.new_body()
                .dynamic()
                .position(161.0 + 2.0 * i, -0.125)
                .capsule((-1, 0), (1, 0), radius=0.125)
                .build()
            )
            self.world.add_revolute_joint(
                previous, segment, anchor=(160.0 + 2.0 * i, -0.125)
            )
            previous = segment
        # The last pin has a friction motor, which damps the bridge's sway.
        self.world.add_revolute_joint(
            previous,
            ground,
            anchor=(200.0, -0.125),
            enable_motor=True,
            max_motor_torque=50.0,
        )

        # Light, bouncy boxes to drive into.
        box = (
            self.world.new_body()
            .dynamic()
            .box(0.5, 0.5, density=0.25, friction=0.25, restitution=0.25)
        )
        for i in range(5):
            box.position(230.0, 0.5 + i).build()

        self.car = Car(
            self.world,
            position=(0, 0),
            scale=1.0,
            hertz=self.hertz,
            damping_ratio=self.damping,
            torque=self.torque,
        )

    @hertz.callback
    @damping.callback
    @torque.callback
    def on_car_change(self, key, value):
        # Speed is not here: it is read when a key is pressed.
        self.car.set_hertz(self.hertz)
        self.car.set_damping_ratio(self.damping)
        self.car.set_torque(self.torque)

    def on_key_down(self, key):
        # Positive motor speed turns the wheels anticlockwise, which rolls
        # the car left. Braking is a motor told to hold the wheels still.
        speeds = {"a": self.speed, "s": 0.0, "d": -self.speed}
        if key in speeds:
            self.car.set_torque(self.torque)
            self.car.set_speed(speeds[key])

    def on_key_up(self, key):
        if key in ("a", "s", "d"):
            self.car.set_torque(0.0)
            self.car.set_speed(0.0)

    def after_step(self, dt):
        position = self.car.chassis.position
        self.app_state.center = (position.x, position.y)

    def status(self):
        kph = self.car.chassis.linear_velocity.x * 3.6
        return ["left A, brake S, right D", f"{kph:.1f} km/h"]


class DistanceJoint(BaseTest, category="Joints", name="Distance Joint"):
    """A chain of balls, each held at a distance from the one before.

    With the spring off, a distance joint is a rigid rod of the set length,
    and the limit makes no difference. Switch the spring on and it becomes a
    spring of that rest length, stiffer the higher the hertz; at zero hertz
    there is no spring force at all and the length is free. The limit then
    bounds the length between the minimum and maximum, so zero hertz with the
    limit on is a rope that can only be pushed together so far. While the
    minimum and maximum are equal, as they start, the limit makes it rigid
    again.

    Count rebuilds the chain; everything else retunes the joints in place.
    """

    length = UI.float(1.0, min=0.1, max=4.0)
    count = UI.int(1, min=1, max=10)
    enable_spring = UI.bool(False)
    enable_limit = UI.bool(False)
    min_length = UI.float(1.0, min=0.1, max=4.0)
    max_length = UI.float(1.0, min=0.1, max=4.0)
    hertz = UI.float(2.0, min=0, max=15)
    damping_ratio = UI.float(0.5, min=0, max=4)

    def setup(self):
        ground = self.world.new_body().static().build()

        ball = self.world.new_body().dynamic().circle(radius=0.25, density=20.0)
        self.joints = []
        previous = ground
        for i in range(self.count):
            body = ball.position(self.length * (i + 1), 0.0).build()
            self.joints.append(
                self.world.add_distance_joint(
                    previous,
                    body,
                    local_anchor_a=(0, 0),
                    local_anchor_b=(0, 0),
                    spring_hertz=self.hertz,
                    spring_damping_ratio=self.damping_ratio,
                    length=self.length,
                    min_length=self.min_length,
                    max_length=self.max_length,
                    enable_spring=self.enable_spring,
                    enable_limit=self.enable_limit,
                )
            )
            previous = body

    @enable_spring.callback
    @enable_limit.callback
    @length.callback
    @min_length.callback
    @max_length.callback
    @hertz.callback
    @damping_ratio.callback
    def on_joint_change(self, key, value):
        for joint in self.joints:
            joint.enable_spring = self.enable_spring
            joint.enable_limit = self.enable_limit
            joint.length = self.length
            joint.min_length = self.min_length
            joint.max_length = self.max_length
            joint.spring_hertz = self.hertz
            joint.spring_damping_ratio = self.damping_ratio
            # A chain at rest is asleep, and would not notice the change.
            joint.wake_bodies()

    @count.callback
    def on_count_change(self, key, value):
        self.rebuild()


class MotorJoint(BaseTest, category="Joints", name="Motor Joint"):
    """A box held up in mid-air and swept from side to side by a motor joint.

    Box2D 3.2 rewrote this joint: it drives a relative velocity, as hard as a
    maximum force and torque allow, rather than correcting toward a target
    offset. Here it joins the box to the ground and drives it along a sine
    from side to side, while holding its vertical speed and its spin at zero.
    Holding the vertical speed at zero is what keeps the box up.

    The force cap is the thing to play with. The box weighs 10 N, and the
    swing takes up to 8 N more, so below about 13 N the drive cannot hold it
    up: it sinks, faster the lower the cap, down to the platform. Drag the
    box with the mouse to feel it push back with up to the capped force and
    torque. The status line shows what the joint is applying.

    Untick Go to stop the clock: the drive goes to zero and the box holds
    where it is. Ticking it again carries on along the path.
    """

    camera_center = (0, 7)
    camera_zoom = 10.0

    enable_motion = UI.bool(True, label="Go")
    max_velocity_force = UI.float(500.0, min=0, max=1000)
    max_velocity_torque = UI.float(500.0, min=0, max=1000)
    speed = UI.float(4.0, min=0, max=20.0)

    def setup(self):
        ground = self.world.new_body().static().segment((-20, 0), (20, 0)).build()

        box = (
            self.world.new_body()
            .dynamic()
            .position(0, 8)
            .box(2.0, 0.5, density=1.0)
            .build()
        )

        # Starts at rest, where the path does. Collides with the ground it is
        # joined to, so a box the drive cannot hold up lands on the platform
        # rather than falling through it.
        self.motor = self.world.add_motor_joint(
            ground,
            box,
            max_velocity_force=self.max_velocity_force,
            max_velocity_torque=self.max_velocity_torque,
            collide_connected=True,
        )

        self.time = 0.0

    @enable_motion.callback
    def on_go_change(self, key, value):
        if value:
            # The box has been held still long enough to fall asleep, and a
            # sleeping body ignores its joints until something wakes it.
            self.motor.wake_bodies()
        else:
            # Time stops, so the box should stop too: drive it at zero.
            # Leaving the last velocity in place would carry it off at speed.
            self.motor.linear_velocity = (0.0, 0.0)

    @max_velocity_force.callback
    def on_max_force_change(self, key, value):
        self.motor.max_velocity_force = value

    @max_velocity_torque.callback
    def on_max_torque_change(self, key, value):
        self.motor.max_velocity_torque = value

    def after_step(self, dt):
        if self.enable_motion:
            self.time += dt
            # The velocity of x = (speed / 2) * (1 - cos 2t), a path that
            # swings between where the box started and speed metres right.
            self.motor.linear_velocity = (self.speed * math.sin(2.0 * self.time), 0.0)

    def status(self):
        force = self.motor.constraint_force
        return [
            f"drive {self.motor.linear_velocity.x:.1f} m/s",
            f"force ({force.x:.1f}, {force.y:.1f}) N, "
            f"torque {self.motor.constraint_torque:.1f} Nm",
        ]


class MotionLocks(BaseTest, category="Joints", name="Motion Locks"):
    """Six boxes, each held by a different kind of joint, sharing one set of
    motion locks.

    Box2D 3.2 replaced the single fixed-rotation flag with three independent
    locks: no movement along x, none along y, and no rotation. A lock is part
    of the body, not of any joint, so each joint has to work around it.
    From the left the boxes hang from a distance, motor, prismatic, revolute,
    weld and wheel joint; tick the locks to watch how each one reacts, and
    shove the first box to see a lock hold against an impulse.
    """

    camera_center = (0, 8)
    camera_zoom = 17.5

    lock_x = UI.bool(False, label="Lock Linear X")
    lock_y = UI.bool(False, label="Lock Linear Y")
    lock_rotation = UI.bool(True, label="Lock Angular Z")
    shove = UI.button("Shove first box")

    def setup(self):
        ground = self.world.new_body().static().build()

        box = (
            self.world.new_body()
            .dynamic()
            .lock_x(self.lock_x)
            .lock_y(self.lock_y)
            .lock_rotation(self.lock_rotation)
            .box(2, 2)
        )
        attach = (
            self.attach_distance,
            self.attach_motor,
            self.attach_prismatic,
            self.attach_revolute,
            self.attach_weld,
            self.attach_wheel,
        )
        self.bodies = []
        for index, attach_joint in enumerate(attach):
            position = Vec2(-12.5 + 5.0 * index, 10.0)
            body = box.position(position).build()
            attach_joint(ground, body, position)
            self.bodies.append(body)

    def attach_distance(self, ground, body, position):
        # Hung from a point above the box by a rod 2 m long.
        length = 2.0
        self.world.add_distance_joint(
            ground,
            body,
            local_anchor_a=position + (0, 1.0 + length),
            local_anchor_b=(0, 1.0),
            length=length,
        )

    def attach_motor(self, ground, body, position):
        # No velocity to drive towards, only a capped force resisting any
        # motion, which acts like friction.
        self.world.add_motor_joint(
            ground, body, max_velocity_force=200.0, max_velocity_torque=200.0
        )

    def attach_prismatic(self, ground, body, position):
        self.world.add_prismatic_joint(ground, body, anchor=position - (1.0, 0))

    def attach_revolute(self, ground, body, position):
        self.world.add_revolute_joint(ground, body, anchor=position - (1.0, 0))

    def attach_weld(self, ground, body, position):
        self.world.add_weld_joint(
            ground,
            body,
            anchor=position - (1.0, 0),
            linear_hertz=1.0,
            linear_damping_ratio=0.5,
            angular_hertz=1.0,
            angular_damping_ratio=0.5,
        )

    def attach_wheel(self, ground, body, position):
        self.world.add_wheel_joint(
            ground,
            body,
            anchor=position - (1.0, 0),
            axis=(0, 1),
            enable_spring=True,
            spring_hertz=1.0,
            spring_damping_ratio=0.7,
            lower_limit=-1.0,
            upper_limit=1.0,
            enable_limit=True,
            enable_motor=True,
            max_motor_torque=10.0,
            motor_speed=1.0,
        )

    @lock_x.callback
    @lock_y.callback
    @lock_rotation.callback
    def on_lock_change(self, key, value):
        for body in self.bodies:
            body.lock_x = self.lock_x
            body.lock_y = self.lock_y
            body.lock_rotation = self.lock_rotation
            # A body at rest is asleep, and would not notice the new lock.
            body.awake = True

    @shove.callback
    def on_shove(self, key, value):
        self.bodies[0].apply_linear_impulse((100, 0))


class FilterJoint(BaseTest, category="Joints", name="Filter Joint"):
    """Two stacks where one pair of boxes ignores each other.

    A filter joint names an exact pair, which collision categories cannot do
    without also affecting everything sharing a category. The left stack has
    one, so its middle boxes sink through each other; the right stack does not,
    so it stacks normally. The status line compares the two heights.
    """

    camera_center = (0, 4)
    camera_zoom = 10.0

    def setup(self):
        self.world.new_body().static().position(0, -1).box(40, 2).build()

        box = self.world.new_body().dynamic().box(1, 1, density=1.0)

        self.left = [box.position(-3, 0.5 + 1.2 * i).build() for i in range(4)]
        self.world.add_filter_joint(self.left[1], self.left[2])

        self.right = [box.position(3, 0.5 + 1.2 * i).build() for i in range(4)]

    def status(self):
        left_height = max(body.position.y for body in self.left)
        right_height = max(body.position.y for body in self.right)
        return (
            f"filtered stack top {left_height:.2f}, normal stack top {right_height:.2f}"
        )


class ScissorLift(BaseTest, category="Joints", name="Scissor Lift"):
    """A scissor lift raised by a single motor, with a car parked on top.

    Every crossing pair is pinned at its middle and at both ends, so the whole
    stack is one loop of constraints. That makes it a stiff thing to solve:
    the joints are given a high constraint stiffness, and it wants at least
    eight sub-steps to stay steady under the car's weight. The testbed
    default is comfortably above that.

    The lift itself is one distance joint with a motor, pulling the bottom
    scissor closed. Tick Motor to raise it; a negative speed lowers it, and
    too little force lets the car's weight win.
    """

    camera_center = (0, 9)
    camera_zoom = 10.0

    motor = UI.bool(False)
    motor_force = UI.float(2000.0, min=0.0, max=3000.0, label="Max force")
    motor_speed = UI.float(0.25, min=-0.3, max=0.3, label="Speed")

    # Stiff enough that the linkage does not visibly sag under the car.
    CONSTRAINT_HERTZ = 240.0
    CONSTRAINT_DAMPING = 20.0
    LEVELS = 3

    def setup(self):
        ground = self.world.new_body().static().segment((-20, 0), (20, 0)).build()

        arm = (
            self.world.new_body()
            .dynamic()
            .sleep_threshold(0.01)
            .capsule((-2.5, 0), (2.5, 0), radius=0.15)
        )
        joints = []
        base_a, base_b = ground, ground
        anchor_a, anchor_b = (-2.5, 0.2), (2.5, 0.2)
        y = 0.5
        for level in range(self.LEVELS):
            # The two arms of one scissor, crossed and pinned in the middle.
            left_arm = arm.position(0, y).rotation(0.15).build()
            right_arm = arm.position(0, y).rotation(-0.15).build()
            if level == 1:
                lift_link = right_arm

            joints.append(
                self.world.add_revolute_joint(
                    base_a,
                    left_arm,
                    local_anchor_a=anchor_a,
                    local_anchor_b=(-2.5, 0),
                    # Only the bottom pair may touch the ground.
                    collide_connected=(level == 0),
                )
            )
            if level == 0:
                # The bottom right corner rolls along the ground instead of
                # being pinned, which is what lets the scissor open at all.
                joints.append(
                    self.world.add_wheel_joint(
                        base_b,
                        right_arm,
                        local_anchor_a=anchor_b,
                        local_anchor_b=(2.5, 0),
                        enable_spring=False,
                        collide_connected=True,
                    )
                )
            else:
                joints.append(
                    self.world.add_revolute_joint(
                        base_b,
                        right_arm,
                        local_anchor_a=anchor_b,
                        local_anchor_b=(2.5, 0),
                    )
                )
            joints.append(
                self.world.add_revolute_joint(
                    left_arm, right_arm, local_anchor_a=(0, 0), local_anchor_b=(0, 0)
                )
            )

            # The next scissor stands on this one, crossed over.
            base_a, base_b = right_arm, left_arm
            anchor_a, anchor_b = (-2.5, 0), (2.5, 0)
            y += 1.0

        platform = (
            self.world.new_body()
            .dynamic()
            .position(0, y)
            .sleep_threshold(0.01)
            .box(6, 0.4)
            .build()
        )
        # Pinned on the left and rolling on the right, like the bottom.
        joints.append(
            self.world.add_revolute_joint(
                platform,
                base_a,
                local_anchor_a=(-2.5, -0.4),
                local_anchor_b=anchor_a,
                collide_connected=True,
            )
        )
        joints.append(
            self.world.add_wheel_joint(
                platform,
                base_b,
                local_anchor_a=(2.5, -0.4),
                local_anchor_b=anchor_b,
                enable_spring=False,
                collide_connected=True,
            )
        )
        for joint in joints:
            joint.constraint_tuning = (self.CONSTRAINT_HERTZ, self.CONSTRAINT_DAMPING)

        # One motor raises the whole lift by closing the bottom scissor.
        self.lift_joint = self.world.add_distance_joint(
            ground,
            lift_link,
            local_anchor_a=(-2.5, 0.2),
            local_anchor_b=(0.5, 0),
            enable_spring=True,
            min_length=0.2,
            max_length=5.5,
            enable_limit=True,
            enable_motor=self.motor,
            motor_speed=self.motor_speed,
            max_motor_force=self.motor_force,
        )

        Car(self.world, (0, y + 2.0), scale=1.0, hertz=3.0, damping_ratio=0.7)

    @motor.callback
    def on_motor_change(self, key, value):
        self.lift_joint.enable_motor = value
        self.lift_joint.wake_bodies()

    @motor_force.callback
    def on_force_change(self, key, value):
        self.lift_joint.max_motor_force = value
        self.lift_joint.wake_bodies()

    @motor_speed.callback
    def on_speed_change(self, key, value):
        self.lift_joint.motor_speed = value
        self.lift_joint.wake_bodies()


class Cantilever(BaseTest, category="Joints", name="Cantilever"):
    """Eight capsules welded end to end, held at the left end and free at the tip.

    Zero hertz is the stiff end of each slider, not the soft one. A weld at
    zero hertz is not a spring at all: it is held as firmly as the solver
    holds any joint, here tuned up to 120 hertz. Any value above zero makes it
    a spring of that frequency instead, very soft just above zero and stiffer
    as it rises. So at the defaults the beam flops down and swings, and with
    both hertz at zero it holds out nearly level -- though even then the tip
    sags a little, since an iterative solver cannot hold a long chain of
    bodies perfectly rigid. Linear softness lets the segments pull apart
    along the beam; angular softness lets them hinge, which is what droops
    the tip.

    The status line shows the tip's height, since the interesting thing is
    how far it settles rather than what it looks like mid-swing.
    """

    camera_center = (0, 0)
    camera_zoom = 8.75

    linear_hertz = UI.float(15.0, min=0.0, max=20.0, label="Linear hertz")
    linear_damping = UI.float(0.5, min=0.0, max=10.0, label="Linear damping")
    angular_hertz = UI.float(5.0, min=0.0, max=20.0, label="Angular hertz")
    angular_damping = UI.float(0.5, min=0.0, max=4.0, label="Angular damping")
    collide_connected = UI.bool(False, label="Collide connected")

    COUNT = 8

    def setup(self):
        ground = self.world.new_body().static().build()

        half_length = 0.5
        segment = (
            self.world.new_body()
            .dynamic()
            .capsule((-half_length, 0), (half_length, 0), radius=0.125, density=20.0)
        )
        self.joints = []
        previous = ground
        for i in range(self.COUNT):
            body = segment.position((1.0 + 2.0 * i) * half_length, 0.0).build()
            joint = self.world.add_weld_joint(
                previous,
                body,
                # Where the two capsules meet.
                anchor=((2.0 * i) * half_length, 0.0),
                linear_hertz=self.linear_hertz,
                linear_damping_ratio=self.linear_damping,
                angular_hertz=self.angular_hertz,
                angular_damping_ratio=self.angular_damping,
                collide_connected=self.collide_connected,
            )
            # Stiffer than the default 60 hertz, which is what a weld at zero
            # hertz is held with. Box2D's sample calls it experimental tuning.
            joint.constraint_tuning = (120.0, 10.0)
            self.joints.append(joint)
            previous = body

        self.tip = previous

    @linear_hertz.callback
    @linear_damping.callback
    @angular_hertz.callback
    @angular_damping.callback
    def on_softness_change(self, key, value):
        for joint in self.joints:
            joint.linear_hertz = self.linear_hertz
            joint.linear_damping_ratio = self.linear_damping
            joint.angular_hertz = self.angular_hertz
            joint.angular_damping_ratio = self.angular_damping
            joint.wake_bodies()

    @collide_connected.callback
    def on_collide_change(self, key, value):
        self.rebuild()

    def status(self):
        return f"tip y = {self.tip.position.y:.2f}"


class Ragdoll(BaseTest, category="Joints", name="Ragdoll"):
    """A jointed figure dropped from a height, to be poked and dragged.

    Every joint has an angle limit, a friction motor and a spring. The limits
    are what keep it looking like a body rather than a bag of sticks; the
    friction decides whether it flops or holds a pose; the spring pulls it
    back towards standing.

    Turn the friction to zero for a rag, or up for something that resists
    being folded. Drag a limb to feel the difference, and Respawn to drop a
    fresh one.
    """

    camera_center = (0, 12)
    camera_zoom = 16.0

    friction = UI.float(0.03, min=0.0, max=1.0, label="Joint friction")
    hertz = UI.float(5.0, min=0.0, max=10.0, label="Spring hertz")
    damping = UI.float(0.5, min=0.0, max=4.0, label="Spring damping")
    respawn = UI.button("Respawn")

    SPAWN = (0.0, 25.0)

    def setup(self):
        self.world.new_body().static().segment((-20, 0), (20, 0)).build()

        # A stiff, barely-damped contact response, so a body landing on the
        # ground does not sink into it before being pushed back out.
        self.world.contact_hertz = 240.0
        self.world.contact_damping_ratio = 0.0
        self.world.contact_push_velocity = 2.0

        self.human = None
        self.spawn()

    def spawn(self):
        if self.human is not None:
            self.human.destroy()
        self.human = Human(
            self.world,
            self.SPAWN,
            scale=1.0,
            friction_torque=self.friction,
            hertz=self.hertz,
            damping_ratio=self.damping,
        )

    @respawn.callback
    def on_respawn(self, key, value):
        self.spawn()

    @friction.callback
    def on_friction_change(self, key, value):
        self.human.set_joint_friction_torque(value)

    @hertz.callback
    def on_hertz_change(self, key, value):
        self.human.set_joint_spring_hertz(value)

    @damping.callback
    def on_damping_change(self, key, value):
        self.human.set_joint_damping_ratio(value)


class ScaleRagdoll(BaseTest, category="Joints", name="Scale Ragdoll"):
    """One ragdoll, resized live.

    Dragging the slider rewrites every bone's shape and every joint frame in
    place, keeping the pose. It is a test of whether a jointed thing survives
    being rebuilt underneath itself. The figure drops a few metres with a
    little random spin and comes to rest lying on the ground, which is where
    to resize it: you want to watch the joints hold, not the figure fall.

    Joint friction grows with the cube of the size, not in step with it, so a
    larger figure is proportionally as floppy rather than turning rigid.
    """

    camera_center = (0, 4.5)
    camera_zoom = 6.0

    # The lower bound is not the C++ sample's 0.1: below about half size the
    # feet fall under Box2D's minimum polygon feature size and cannot be built.
    scale = UI.float(1.0, min=0.5, max=10.0)

    def setup(self):
        self.world.new_body().static().box(40, 2, offset=(0, -1)).build()

        self.human = Human(
            self.world,
            (0, 5),
            scale=self.scale,
            friction_torque=0.03,
            hertz=1.0,
            damping_ratio=0.5,
            colorize=False,
        )
        self.human.apply_random_angular_impulse(0.1)

    @scale.callback
    def on_scale_change(self, key, value):
        self.human.set_scale(value)
