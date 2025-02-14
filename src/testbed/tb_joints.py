# tb_joints.py

from base_test import BaseTest


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
