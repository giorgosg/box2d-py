# tb_joints.py

from .base_test import BaseTest, UIElement
from .shared import donut, create_random_polygon
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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui_elements += [
            UIElement(
                key="segments",
                control_type="int_input",
                max_value=100,
                min_value=4,
                default=30,
                label="Segments",
                callback=self.on_change,
            ),
            UIElement(
                key="hertz",
                control_type="int_input",
                max_value=200,
                min_value=1,
                default=12,
                label="Hertz",
                callback=self.on_change,
            ),
            UIElement(
                key="damping",
                control_type="int_input",
                max_value=10,
                min_value=0,
                default=2,
                label="Damping",
                callback=self.on_change,
            ),
        ]
        self.segments = 30
        self.radius = 5
        self.hertz = 12.0
        self.damping = 0.0

    def on_change(self, key, value):
        if key == "segments":
            self.segments = value
        elif key == "hertz":
            self.hertz = value
        elif key == "damping":
            self.damping = value
        if key in ("segments",):
            for body in self.world.bodies:
                body.destroy()
            self.setup()
        if key in ("hertz", "damping"):
            for joint in self.joints:
                joint.angular_damping_ratio = self.damping
                joint.angular_hertz = self.hertz

    def setup(self):
        ground = self.world.new_body().position(0, -5).box(100, 1).build()
        self.bodies, self.joints = donut(
            self.world, (0, 30), self.radius, self.segments, self.hertz, self.damping
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
    def __init__(self, world):
        super().__init__(world)
        self.ui_elements += [
            UIElement(
                key="enable_limit",
                control_type="toggle",
                default=True,
                label="Limit",
                callback=self.on_change,
            ),
            UIElement(
                key="enable_motor",
                control_type="toggle",
                default=False,
                label="Motor",
                callback=self.on_change,
            ),
            UIElement(
                key="max_force",
                label="Max Force",
                control_type="int_input",
                min_value=0,
                max_value=200,
                default=50,
                callback=self.on_change,
            ),
            UIElement(
                key="motor_speed",
                label="Speed",
                control_type="int_input",
                min_value=-40,
                max_value=40,
                default=10,
                callback=self.on_change,
            ),
            UIElement(
                key="enable_spring",
                control_type="toggle",
                default=False,
                label="Spring",
                callback=self.on_change,
            ),
            UIElement(
                key="spring_hertz",
                control_type="float_input",
                min_value=0,
                max_value=10,
                default=2,
                label="Hertz",
                callback=self.on_change,
            ),
            UIElement(
                key="spring_damping",
                control_type="float_input",
                min_value=0,
                max_value=2,
                default=0.1,
                label="Damping",
                callback=self.on_change,
            ),
        ]
        self.enable_limit = True
        self.enable_motor = False
        self.max_force = 50
        self.motor_speed = 10
        self.enable_spring = False
        self.spring_hertz = 2
        self.spring_damping = 0.1

    def on_change(self, key, value):
        if key == "enable_limit":
            self.enable_limit = value
        elif key == "enable_motor":
            self.enable_motor = value
        elif key == "max_force":
            self.max_force = value
        elif key == "motor_speed":
            self.motor_speed = value
        elif key == "enable_spring":
            self.enable_spring = value
        elif key == "spring_hertz":
            self.spring_hertz = value
        elif key == "spring_damping":
            self.spring_damping = value
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
