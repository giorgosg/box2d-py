from box2d import Vec2, BodyBuilder, World
import random, math
from itertools import pairwise


@BodyBuilder.extend
def create_random_polygon(self, extent, **kwargs):
    count = 3 + random.randint(0, 5)
    vertices = [
        Vec2(random.uniform(-extent, extent), random.uniform(-extent, extent))
        for _ in range(count)
    ]
    radius = random.uniform(extent / 10, extent / 4)
    try:
        self.polygon(vertices, radius, **kwargs)
    except ValueError:
        self.box(extent, extent, radius, **kwargs)
    return self


def donut(world: World, position, radius, segments=10, hertz=5.0, damping=0.0):
    delta_angle = 2 * math.pi / segments
    length = 2 * radius * math.sin(math.pi / segments)
    capsule_points = ((0, -length / 2), (0, length / 2))
    capsule_r = 0.4 * length
    center = Vec2(*position)
    bb = (
        world.new_body()
        .dynamic()
        .capsule(capsule_points[0], capsule_points[1], capsule_r)
    )
    angles = [delta_angle * i for i in range(segments)]
    positions = [
        (radius * math.cos(angle) + center.x, radius * math.sin(angle) + center.y)
        for angle in angles
    ]
    bodies = [
        bb.position(*position).rotation(angle).build()
        for position, angle in zip(positions, angles)
    ]
    joint_kw = {
        "angular_hertz": hertz,
        "angular_damping_ratio": damping,
        "local_anchor_a": capsule_points[0],
        "local_anchor_b": capsule_points[1],
    }
    joints = [
        world.add_weld_joint(
            body_b,
            body_a,
            reference_angle=body_b.rotation - body_a.rotation,
            **joint_kw,
        )
        for body_a, body_b in pairwise(bodies + bodies[:1])
    ]
    return bodies, joints


class Car:
    """A 2D vehicle with wheel suspension using wheel joints."""

    def __init__(
        self,
        world: World,
        position,
        scale=1.0,
        hertz=5.0,
        damping_ratio=0.7,
        torque=2.5,
    ):
        """Initialize an empty car instance."""
        self.chassis = None
        self.rear_wheel = None
        self.front_wheel = None
        self.rear_axle = None
        self.front_axle = None
        self._is_spawned = False
        self.spawn(world, position, scale, hertz, damping_ratio, torque)

    def spawn(
        self,
        world: World,
        position,
        scale=1.0,
        hertz=5.0,
        damping_ratio=0.7,
        torque=2.5,
    ):
        """Create the car in the physics world.

        Args:
            world: The physics World instance
            position: (x,y) spawn position
            scale: Size multiplier (default 1.0)
            hertz: Suspension spring frequency in Hz (default 5.0)
            damping_ratio: Suspension damping ratio (default 0.7)
            torque: Maximum motor torque (default 2.5)
        """
        assert not self._is_spawned

        # Create chassis polygon
        vertices = [
            (-1.5, -0.5),
            (1.5, -0.5),
            (1.5, 0.0),
            (0.0, 0.9),
            (-1.15, 0.9),
            (-1.5, 0.2),
        ]
        scaled_vertices = [(0.85 * scale * x, 0.85 * scale * y) for x, y in vertices]

        # Create chassis body
        self.chassis = (
            world.new_body()
            .dynamic()
            .position(position[0], position[1] + scale)
            .polygon(
                scaled_vertices, radius=0.15 * scale, density=1.0 / scale, friction=0.2
            )
            .build()
        )

        # Create wheels
        wheel_def = {"density": 2.0 / scale, "friction": 1.5, "radius": 0.4 * scale}

        self.rear_wheel = (
            world.new_body()
            .dynamic()
            .position(position[0] - scale, position[1] + 0.35 * scale)
            .circle(**wheel_def)
            .build()
        )

        self.front_wheel = (
            world.new_body()
            .dynamic()
            .position(position[0] + scale, position[1] + 0.4 * scale)
            .circle(**wheel_def)
            .build()
        )

        # Create suspension joints
        joint_def = {
            "axis": (0, 1),
            "enable_motor": True,
            "motor_speed": 0,
            "max_motor_torque": torque * scale,
            "enable_limit": True,
            "lower_translation": -0.25 * scale,
            "upper_translation": 0.25 * scale,
            "enable_spring": True,
            "spring_hertz": hertz,
            "spring_damping_ratio": damping_ratio,
        }

        # Rear axle
        rear_anchor = self.rear_wheel.position
        self.rear_axle = world.add_wheel_joint(
            self.chassis, self.rear_wheel, anchor=rear_anchor, **joint_def
        )

        # Front axle
        front_anchor = self.front_wheel.position
        self.front_axle = world.add_wheel_joint(
            self.chassis, self.front_wheel, anchor=front_anchor, **joint_def
        )

        self._is_spawned = True

    def destroy(self):
        """Remove the car from the physics world."""
        assert self._is_spawned

        self.rear_axle.destroy()
        self.front_axle.destroy()
        self.rear_wheel.destroy()
        self.front_wheel.destroy()
        self.chassis.destroy()

        self._is_spawned = False

    def set_speed(self, speed):
        """Set the motor speed for both wheels.

        Args:
            speed: Angular velocity in radians/second
        """
        self.rear_axle.motor_speed = speed
        self.front_axle.motor_speed = speed
        self.rear_axle.wake_bodies()

    def set_torque(self, torque):
        """Set the maximum motor torque for both wheels.

        Args:
            torque: Maximum torque in N-m
        """
        self.rear_axle.max_motor_torque = torque
        self.front_axle.max_motor_torque = torque

    def set_hertz(self, hertz):
        """Set the suspension spring frequency.

        Args:
            hertz: Spring frequency in Hz
        """
        self.rear_axle.spring_hertz = hertz
        self.front_axle.spring_hertz = hertz

    def set_damping_ratio(self, damping_ratio):
        """Set the suspension damping ratio.

        Args:
            damping_ratio: Damping ratio (non-dimensional)
        """
        self.rear_axle.spring_damping_ratio = damping_ratio
        self.front_axle.spring_damping_ratio = damping_ratio
