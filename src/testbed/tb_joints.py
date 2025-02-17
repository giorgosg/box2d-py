# tb_joints.py

from .base_test import BaseTest, UIElement
from .shared import donut


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
                max_value=30,
                min_value=4,
                default=15,
                label="Segments",
                callback=self.on_change,
            ),
            UIElement(
                key="radius",
                control_type="int_input",
                max_value=30,
                min_value=1,
                default=5,
                label="Radius",
                callback=self.on_change,
            ),
            UIElement(
                key="hertz",
                control_type="int_input",
                max_value=60,
                min_value=1,
                default=5,
                label="Hertz",
                callback=self.on_change,
            ),
            UIElement(
                key="damping",
                control_type="int_input",
                max_value=10,
                min_value=0,
                default=1,
                label="Damping",
                callback=self.on_change,
            ),
        ]
        self.segments = 15
        self.radius = 5
        self.hertz = 5.0
        self.damping = 0.0

    def on_change(self, key, value):
        if key == "segments":
            self.segments = value
        elif key == "radius":
            self.radius = value
        elif key == "hertz":
            self.hertz = value
        elif key == "damping":
            self.damping = value
        for body in self.world.bodies:
            body.destroy()
        self.setup()

    def setup(self):
        ground = self.world.new_body().position(0, -5).box(100, 1).build()
        soft_body = donut(
            self.world, (0, 20), self.radius, self.segments, self.hertz, self.damping
        )
