# tb_joints.py

from .base_test import BaseTest, UI
from .shared import donut, create_random_polygon, Car
import math
from box2d import Vec2, World, Body, Transform, Color


class BallAndChain(BaseTest, category="Joints", name="Ball and Chain"):
    def setup(self):
        joint_friction = 100.0  # Maximum motor torque for the joints
        count = 30  # Number of chain links
        hx = 0.5  # Half-length used for defining the capsule endpoints
        circle_radius = 4.0  # Radius for the final circle body

        ground = self.world.new_body().static().build()
        self.joints = []

        # Build the chain: For each link, create a dynamic body with a capsule shape
        # and attach it to the previous body using a revolute joint.
        prev_body = ground
        cl_builder = (
            self.world.new_body()
            .dynamic()
            .capsule(point1=(-hx, 0), point2=(hx, 0), radius=0.125, density=20.0)
        )
        for i in range(count):
            pos_x = (1.0 + 2.0 * i) * hx
            pos_y = count * hx
            body = cl_builder.position(pos_x, pos_y).build()
            pivot = (pos_x - hx, pos_y)
            joint = self.world.add_revolute_joint(
                prev_body,
                body,
                anchor=pivot,
                max_motor_torque=joint_friction,
                enable_motor=False,
            )

            self.joints.append(joint)
            prev_body = body

        # Create the final body to serve as the weight at the end of the chain.
        final_x = (1.0 + 2.0 * count) * hx + circle_radius - hx
        final_y = count * hx
        circle_body = (
            self.world.new_body()
            .dynamic()
            .position(final_x, final_y)
            .circle(radius=circle_radius, center=(0, 0), density=20.0)
            .build()
        )
        pivot = (2.0 * count * hx, count * hx)
        final_joint = self.world.add_revolute_joint(
            prev_body,
            circle_body,
            anchor=pivot,
            max_motor_torque=joint_friction,
            enable_motor=True,
        )
        self.joints.append(final_joint)


class SoftBody(BaseTest, category="Joints", name="Soft Body"):
    segments = UI.int(30, min=4, max=100)
    hertz = UI.int(12, min=1, max=200)
    damping = UI.int(2, min=0, max=10)

    @segments.callback
    def on_change_segments(self, key, value):
        for body in self.world.bodies:
            body.destroy()
        self.setup()

    @hertz.callback
    @damping.callback
    def on_change_joint(self, key, value):
        for joint in self.joints:
            joint.angular_damping_ratio = self.damping
            joint.angular_hertz = self.hertz

    def setup(self):
        ground = self.world.new_body().position(0, -5).box(100, 1).build()
        self.bodies, self.joints = donut(
            self.world, (0, 50), 5, self.segments, self.hertz, self.damping
        )


class Arrow(BaseTest, category="Joints", name="Arrow"):
    def setup(self):
        ground = self.world.new_body().position(0, -5).box(100, 1).build()
        boxbuilder = self.world.new_body().dynamic().box(0.5, 0.5)
        boxstack = [boxbuilder.position(20, -4.25 + 0.5 * i).build() for i in range(30)]

        def create_arrow(position, rotation, velocity):
            vel_v = Vec2(velocity, 0).rotate(rotation)
            arrow_body = (
                self.world.new_body()
                .dynamic()
                .position(*position)
                .rotation(rotation)
                .box(1, 0.1)
                .polygon(([0.7, 0], [0.5, 0.2], [0.5, -0.2]))
                .linear_velocity(*vel_v)
                .angular_damping(1)
                .build()
            )
            arrow_fletch = (
                self.world.new_body()
                .dynamic()
                .position(*position)
                .rotation(rotation)
                .polygon(((-0.4, 0), (-0.5, 0.1), (-0.5, -0.1)), density=1)
                .linear_damping(1)
                .linear_velocity(*vel_v)
                .build()
            )
            joint = self.world.add_weld_joint(
                arrow_body,
                arrow_fletch,
                local_anchor_a=(0, 0),
                local_anchor_b=(0, 0),
            )

            return arrow_body, arrow_fletch, joint

        self.arrows = [
            create_arrow((-10, 20 + y), rotation, 20)
            for y, rotation in zip(
                range(-5, 50), (math.radians(a) for a in range(-45, 90, 10))
            )
        ]


class Bridge(BaseTest, category="Joints", name="Bridge"):
    def setup(self):
        ground = self.world.new_body().build()

        def create_bridge(
            world: World,
            anchor: Body,
            psize: Vec2,
            count: int,
            center: Vec2 = Vec2(0, 0),
        ):
            length = psize.x * count
            start = center - Vec2(length / 2, 0) + Vec2(psize.x / 2, 0)
            piece_builder = (
                world.new_body().dynamic().gravity_scale(0.5).box(*psize, density=20)
            )
            pieces = [
                piece_builder.position(*(start + (i * psize.x, 0))).build()
                for i in range(count)
            ]
            joint_params = {"enable_motor": True, "max_motor_torque": 200}
            joints = [
                world.add_revolute_joint(
                    pieces[i],
                    pieces[i + 1],
                    anchor=pieces[i].transform(Vec2(psize.x / 2, 0)),
                    **joint_params,
                )
                for i in range(count - 1)
            ]
            world.add_revolute_joint(
                anchor,
                pieces[0],
                anchor=pieces[0].transform(Vec2(-psize.x / 2, 0)),
                **joint_params,
            )
            world.add_revolute_joint(
                anchor,
                pieces[-1],
                anchor=pieces[-1].transform(Vec2(psize.x / 2, 0)),
                **joint_params,
            )
            return pieces, joints

        bridge = create_bridge(self.world, ground, Vec2(1, 0.2), 100, Vec2(0, 10))
        self.bridge_bodies, self.bridge_joints = bridge
        circle_builder = self.world.new_body().dynamic().circle(0.5, density=10)
        self.circles = [
            circle_builder.position(i, 20).build() for i in range(-10, 10, 2)
        ]
        self.polygons = [
            self.world.new_body()
            .dynamic()
            .position(i, 20)
            .create_random_polygon(0.5, density=10)
            .build()
            for i in range(-11, 11, 2)
        ]


class UserConstraint(BaseTest, category="Joints", name="User Constraint"):
    """
    This shows how to implement a constraint outside of Box2D.
    The constraint keeps a body at a fixed position relative to anchors using velocity-based control.
    """

    def setup(self):
        # Create dynamic body with box shape
        self.body = (
            self.world.new_body()
            .dynamic()
            .position(0, 0)
            .box(2.0, 1.0, density=20.0)
            .angular_damping(0.5)
            .linear_damping(0.2)
            .gravity_scale(1.0)
            .build()
        )

        self.impulses = [0.0, 0.0]  # Store impulses for visualization
        self.inv_dt = 0.0

    def after_step(self, dt):
        if dt == 0.0:
            return
        self.inv_dt = 1.0 / dt

        # Parameters
        hertz = 3.0
        damping = 0.7
        omega = 2.0 * math.pi * hertz
        sigma = 2.0 * damping + dt * omega
        s = dt * omega * sigma
        impulse_coefficient = 1.0 / (1.0 + s)
        mass_coefficient = s * impulse_coefficient
        bias_coefficient = omega / sigma
        max_force = 1000.0

        # Get body state
        mass = self.body.mass
        inv_mass = 1.0 / mass if mass > 0.0001 else 0.0
        inertia = self.body.rotational_inertia
        inv_inertia = 1.0 / inertia if inertia > 0.0001 else 0.0

        pos = self.body.transform((0, 0))  # convert from local to world
        vel = self.body.linear_velocity
        ang_vel = self.body.angular_velocity

        # Define two anchor points for the constraint
        anchors_a = [Vec2(3.0, 0.0), Vec2(3.0, 0.0)]
        local_anchors = [Vec2(1.0, -0.5), Vec2(1.0, 0.5)]

        # Transform local anchors to world space
        anchors_b = [
            self.body.transform(local_anchor) for local_anchor in local_anchors
        ]

        # Apply constraint for each anchor point
        new_vel = vel
        new_ang_vel = ang_vel

        for i in range(2):
            # Calculate position error
            delta = anchors_b[i] - anchors_a[i]
            length = delta.length
            slack_length = 1.0

            if length < 0.001 or length < slack_length:
                self.impulses[i] = 0.0
                continue

            # Calculate constraint axis
            axis = delta.normalize()

            # Calculate geometric Jacobian
            r = anchors_b[i] - pos
            Jrot = r.cross(axis)

            # Calculate effective mass
            K = inv_mass + Jrot * inv_inertia * Jrot
            inv_K = 1.0 / K if K > 0.0001 else 0.0

            # Calculate velocity bias
            C = length - slack_length
            bias = bias_coefficient * C

            Cdot = (new_vel + Vec2(-new_ang_vel * r.y, new_ang_vel * r.x)).dot(axis)
            impulse = -mass_coefficient * inv_K * (Cdot + bias)
            max_impulse = max_force * dt
            impulse = max(impulse, -max_impulse)

            # Apply impulse
            P = axis * impulse
            new_vel += P * inv_mass
            new_ang_vel += inv_inertia * r.cross(P)

            self.impulses[i] = impulse

        # Update velocities
        self.body.linear_velocity = new_vel
        self.body.angular_velocity = new_ang_vel

    def debug_draw(self, debug_draw):
        """Draw debug visualization of the constraint"""
        # Draw coordinate system
        axes = Vec2(0, 0)
        debug_draw.draw_transform(Transform(axes, 0.0))

        # Get world anchor points
        local_anchors = [Vec2(1.0, -0.5), Vec2(1.0, 0.5)]
        anchors_a = [Vec2(3.0, 0.0), Vec2(3.0, 0.0)]
        anchors_b = [
            self.body.transform(local_anchor) for local_anchor in local_anchors
        ]

        # Draw constraint lines
        for i in range(2):
            length = (anchors_b[i] - anchors_a[i]).length
            if length < 1.0:
                debug_draw.draw_segment(anchors_a[i], anchors_b[i], Color(0x00FFFF))
            else:
                debug_draw.draw_segment(anchors_a[i], anchors_b[i], Color(0xFF00FF))

        # Draw forces
        debug_draw.draw_string(
            self.body.transform(Vec2(0, 0)),
            f"forces = {self.impulses[0] * self.inv_dt:.1f}, {self.impulses[1] * self.inv_dt:.1f}",
        )


class PrismaticJointTest(BaseTest, category="Joints", name="Prismatic Joint"):
    enable_limit = UI.bool(True)
    enable_motor = UI.bool(False)
    max_force = UI.int(50, min=0, max=200)
    motor_speed = UI.int(10, min=-40, max=40)
    enable_spring = UI.bool(False)
    spring_hertz = UI.float(2, min=0, max=10)
    spring_damping = UI.float(0.1, min=0, max=2)

    @enable_limit.callback
    @enable_motor.callback
    @max_force.callback
    @motor_speed.callback
    @enable_spring.callback
    @spring_hertz.callback
    @spring_damping.callback
    def on_change(self, key, value):
        self.joint.limit_enabled = self.enable_limit
        self.joint.motor_enabled = self.enable_motor
        self.joint.max_motor_force = self.max_force
        self.joint.motor_speed = self.motor_speed
        self.joint.spring_enabled = self.enable_spring
        self.joint.spring_damping_ratio = self.spring_damping
        self.joint.spring_frequency_hertz = self.spring_hertz
        self.body.awake = True

    def setup(self):
        ground = self.world.new_body().position(0, 0).build()
        body = self.world.new_body().dynamic().position(0, 10).box(1, 4).build()
        pivot = Vec2(0, 9)
        axis = Vec2(1, 1).normalize()
        self.joint = self.world.add_prismatic_joint(
            ground,
            body,
            anchor=pivot,
            axis=ground.transform.q(axis),
            enable_limit=self.enable_limit,
            lower_limit=-10,
            upper_limit=10,
            enable_motor=self.enable_motor,
            max_motor_force=self.max_force,
            motor_speed=self.motor_speed,
            enable_spring=self.enable_spring,
            damping_ratio=self.spring_damping,
            hertz=self.spring_hertz,
        )
        self.body = body


class Driving(BaseTest, category="Joints", name="Driving"):
    """
    A fun demo that shows off the wheel joint with a driveable car.
    Use A/S/D keys to drive left/brake/right.
    """

    hertz = UI.int(5, min=0, max=20)
    damping = UI.float(0.7, 0, 10)
    speed = UI.int(35, 0, 100)
    torque = UI.float(5, 0, 10)
    car = None

    @hertz.callback
    @damping.callback
    @speed.callback
    @torque.callback
    def on_joint_change(self, key, value):
        if self.car:
            self.car.set_hertz(self.hertz)
            self.car.set_damping_ratio(self.damping)
            # self.car.set_speed(self.speed)
            self.car.set_torque(self.torque)

    def setup(self):
        # Create ground body and terrain
        ground = self.world.new_body().static()

        # Define points for terrain shape
        points = []

        # Base platform
        points.extend([(-20, -20), (-20, 0), (20, 0)])

        # Add hills
        heights = [0.25, 1.0, 4.0, 0.0, 0.0, -1.0, -2.0, -2.0, -1.25, 0.0]
        x = 20.0
        dx = 5.0

        for _ in range(2):
            for h in heights:
                points.append((x + dx, h))
                x += dx

        # Add flat sections and ramps
        points.extend(
            [
                (x + 40, 0),  # Flat before bridge
                (x + 40, -20),  # Back to base level
                (x + 80, 0),  # Bridge approach
                (x + 120, 0),  # Bridge end
                (x + 140, 0),  # Pre-ramp
                (x + 150, 5),  # Jump ramp
                (x + 160, 0),  # Landing
                (x + 200, 0),  # Final straight
                (x + 200, 20),  # End wall
            ]
        )

        # Create chain shape for ground
        ground = ground.chain(points[::-1]).build()

        # Create teeter platform
        teeter_pos = Vec2(140.0, 1.0)
        teeter = (
            self.world.new_body()
            .dynamic()
            .position(*teeter_pos)
            .angular_velocity(1.0)
            .box(20.0, 0.5)
            .build()
        )

        # Add revolute joint to teeter with angle limits
        teeter_j = self.world.add_revolute_joint(
            ground,
            teeter,
            anchor=teeter_pos,
            enable_limit=True,
            collide_connected=False,
            lower_angle=math.radians(-18),
            upper_angle=math.radians(18),
        )
        print(teeter_j.collide_connected)
        # Create bridge
        bridge_count = 20
        bridge_start = Vec2(161.0, -0.125)

        # Create bridge segments connected by revolute joints
        prev_body = ground
        for i in range(bridge_count):
            pos = bridge_start + Vec2(2.0 * i, 0)
            segment = (
                self.world.new_body()
                .dynamic()
                .position(*pos)
                .capsule(point1=(-1, 0), point2=(1, 0), radius=0.125)
                .build()
            )

            pivot = Vec2(160.0 + 2.0 * i, -0.125)
            self.world.add_revolute_joint(prev_body, segment, anchor=pivot)
            prev_body = segment

        # Connect final bridge segment to ground
        pivot = Vec2(160.0 + 2.0 * bridge_count, -0.125)
        self.world.add_revolute_joint(
            prev_body, ground, anchor=pivot, enable_motor=True, max_motor_torque=50.0
        )

        # Create stack of boxes
        box_builder = (
            self.world.new_body()
            .dynamic()
            .box(0.5, 0.5, density=0.25, friction=0.25, restitution=0.25)
        )

        for i in range(5):
            box_builder.position(230.0, 0.5 + i).build()

        self.car = Car(
            self.world,
            position=(0, 0),
            scale=1.0,
            hertz=self.hertz,
            damping_ratio=self.damping,
            torque=self.torque,
        )

    def on_key_down(self, key):
        """Handle keyboard input for car control"""
        if key == "a":  # Drive left
            self.car.set_torque(self.torque)
            self.car.set_speed(self.speed)
        elif key == "s":  # Brake
            self.car.set_torque(self.torque)
            self.car.set_speed(0.0)
        elif key == "d":  # Drive right
            self.car.set_torque(self.torque)
            self.car.set_speed(-self.speed)

    def on_key_up(self, key):
        """Handle key release"""
        if key in ["a", "s", "d"]:
            self.car.set_torque(0.0)
            self.car.set_speed(0.0)

    def debug_draw(self, debug_draw):
        """Display help text and speed"""
        debug_draw.draw_string((0, 5), "Keys: left = a, brake = s, right = d")

        velocity = self.car.chassis.linear_velocity
        kph = velocity.x * 3.6  # Convert m/s to km/h
        debug_draw.draw_string(self.car.chassis.position + (-1, 1), f"kph: {kph:.1f}")

    def after_step(self, dt):
        """Update camera to follow the car"""
        car_pos = self.car.chassis.position
        self.app_state.center = Vec2(car_pos.x, car_pos.y)


class DistanceJoints(BaseTest, category="Joints", name="Distance Joint"):
    """Test the distance joint and all options."""

    # UI Properties
    length = UI.float(1.0, min=0.1, max=4.0)
    count = UI.int(1, min=1, max=10)
    enable_spring = UI.bool(False)
    enable_limit = UI.bool(False)
    min_length = UI.float(1.0, min=0.1, max=4.0)
    max_length = UI.float(1.0, min=0.1, max=4.0)
    hertz = UI.float(2.0, min=0, max=15)
    damping_ratio = UI.float(0.5, min=0, max=4)

    def setup(self):
        """Initialize test objects."""
        # Create ground body
        self.ground = self.world.new_body().build()

        # Create new chain
        prev_body = self.ground
        radius = 0.25
        y_offset = 0.0

        # Configure distance joint parameters
        joint_params = {
            "hertz": self.hertz,
            "damping_ratio": self.damping_ratio,
            "length": self.length,
            "min_length": self.min_length,
            "max_length": self.max_length,
            "enable_spring": self.enable_spring,
            "enable_limit": self.enable_limit,
        }

        self.bodies = []
        self.joints = []

        # Create chain of bodies connected by distance joints
        for i in range(self.count):
            # Create body
            body = (
                self.world.new_body()
                .dynamic()
                .position(self.length * (i + 1), y_offset)
                .circle(radius=radius, density=20.0)
                .build()
            )
            self.bodies.append(body)

            # Create distance joint
            pivot_a = Vec2(0, 0)
            pivot_b = Vec2(0, 0)

            joint = self.world.add_distance_joint(
                prev_body,
                body,
                local_anchor_a=pivot_a,
                local_anchor_b=pivot_b,
                **joint_params,
            )
            self.joints.append(joint)

            prev_body = body

    @enable_spring.callback
    @enable_limit.callback
    @length.callback
    @min_length.callback
    @max_length.callback
    @hertz.callback
    @damping_ratio.callback
    def on_joint_change(self, key, value):
        """Update joint properties when toggles change."""
        for joint in self.joints:
            joint.spring_enabled = self.enable_spring
            joint.limit_enabled = self.enable_limit
            joint.length = self.length
            joint.min_length = self.min_length
            joint.max_length = self.max_length
            joint.spring_hertz = self.hertz
            joint.spring_damping_ratio = self.damping_ratio

            joint.wake_bodies()

    @count.callback
    def on_count_change(self, key, value):
        """Update number of bodies in chain."""
        self.on_reset(key, value)


class MotorJointTest(BaseTest, category="Joints", name="Motor Joint"):
    """Test the motor joint.

    A motor joint can be used to animate a dynamic body. With finite motor forces
    the body can be blocked by collision with other bodies.
    By setting the correction factor to zero, the motor joint acts
    like top-down dry friction.
    """

    # UI Properties
    enable_motion = UI.bool(True, label="Go")
    max_force = UI.float(500.0, min=0, max=1000)
    max_torque = UI.float(500.0, min=0, max=1000)
    correction_factor = UI.float(0.3, min=0, max=1.0)

    def setup(self):
        """Initialize the test."""
        # Set up camera
        self.app_state.center = Vec2(0, 7)
        self.app_state.zoom = 25.0 * 0.4

        # Create ground body with horizontal platform
        ground = self.world.new_body().segment((-20, 0), (20, 0)).build()

        # Create box body with motor joint
        self.box = (
            self.world.new_body()
            .dynamic()
            .position(0, 8)
            .box(2.0, 0.5, density=1.0)
            .build()
        )

        # Create motor joint
        self.motor = self.world.add_motor_joint(
            ground,
            self.box,
            max_force=self.max_force,
            max_torque=self.max_torque,
            correction_factor=self.correction_factor,
        )

        self.time = 0.0

    @enable_motion.callback
    @max_force.callback
    @max_torque.callback
    @correction_factor.callback
    def on_param_change(self, key, value):
        """Handle UI parameter changes."""
        if key == "max_force":
            self.motor.max_force = value
        elif key == "max_torque":
            self.motor.max_torque = value
        elif key == "correction_factor":
            self.motor.correction_factor = value

    def after_step(self, dt):
        """Update motor target position based on time."""
        if self.enable_motion and dt > 0:
            self.time += dt

            # Calculate new target position
            target_x = 6.0 * math.sin(2.0 * self.time)
            target_y = 8.0 + 4.0 * math.sin(1.0 * self.time)
            target_angle = math.pi * math.sin(-0.5 * self.time)

            # Update motor joint targets
            self.motor.linear_offset = (target_x, target_y)
            self.motor.angular_offset = target_angle

    def debug_draw(self, debug_draw):
        """Draw debug info."""
        force = self.motor.constraint_force
        torque = self.motor.constraint_torque
        debug_draw.draw_string(
            (5, 5), f"force = ({force.x:.1f}, {force.y:.1f}), torque = {torque:.1f}"
        )
        # Draw target transform for visualization
        debug_draw.draw_transform(
            Transform(self.motor.linear_offset, self.motor.angular_offset)
        )
