# tb_joints.py

from .base_test import BaseTest, UIElement
from .shared import donut, create_random_polygon
import math
from box2d import Vec2, World, Body


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
