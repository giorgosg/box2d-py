"""
Helpers that more than one scenario builds from.

``random_polygon`` is Box2D's ``RandomPolygon``, from ``shared/utils.c``, and
``donut`` and ``Car`` are ported from the ``Donut`` and ``Car`` in Box2D's
samples. ``parse_svg_path`` turns the terrain the character scenarios are
drawn from into chain points.

Scenarios of your own can import them too:
``from box2d_testbed.shared import donut``.
"""

import math
import random
from itertools import pairwise

from box2d import PolygonDef, Vec2, World


def random_polygon(extent):
    """A random convex polygon with rounded corners, for piles of odd shapes.

    Three to eight points are scattered over a square reaching ``extent`` from
    the origin, and the polygon is their convex hull. Now and then the points
    have no hull -- too few survive Box2D merging those that nearly coincide,
    or they lie nearly in a line -- and the square itself is used instead.

    Args:
        extent: How far the polygon may reach from its body's origin, along
            each axis, before rounding.

    Returns:
        PolygonDef: The polygon, valid for ``BodyBuilder.polygon``.

    Example::

        polygon = random_polygon(0.5)
        world.new_body().dynamic().polygon(polygon.vertices, polygon.radius).build()
    """
    count = 3 + random.randint(0, 5)
    vertices = [
        Vec2(random.uniform(-extent, extent), random.uniform(-extent, extent))
        for _ in range(count)
    ]
    radius = random.uniform(extent / 10, extent / 4)
    polygon = PolygonDef(vertices, radius)
    if polygon.is_valid:
        return polygon
    corners = [
        (-extent, -extent),
        (extent, -extent),
        (extent, extent),
        (-extent, extent),
    ]
    return PolygonDef(corners, radius)


def donut(world: World, position, radius, segments=10, hertz=5.0, damping_ratio=0.0):
    """A ring of capsules welded end to end, a soft body that squashes and recovers.

    The welds are rigid along the ring but springy in angle, so the ring keeps
    its length while it bends. The springs are what pull it back round.

    Args:
        world: The world to build the ring in.
        position: The centre of the ring.
        radius: Distance from the centre to the welds.
        segments: How many capsules make up the ring.
        hertz: Stiffness of each weld's angular spring.
        damping_ratio: Damping of that spring. At 0 the ring wobbles until
            friction or a collision settles it.

    Returns:
        tuple[list[Body], list[WeldJoint]]: The capsules, anticlockwise from
        the one on the right of the centre, and the welds, each joining a
        capsule to the next.
    """
    delta_angle = 2 * math.pi / segments
    # The capsules are the sides of a regular polygon with its corners on the
    # circle, so each sits a little inside it, at the apothem. That way the
    # welds already meet when the ring is built. This deliberately differs
    # from Box2D's donut.cpp, which centres its capsules on the circle and
    # sizes them by arc length, so its welds start slightly apart and the
    # first steps pull them together.
    half_length = radius * math.sin(math.pi / segments)
    apothem = radius * math.cos(math.pi / segments)
    center = Vec2(position)
    builder = (
        world.new_body()
        .dynamic()
        .capsule((0, -half_length), (0, half_length), 0.8 * half_length)
    )
    bodies = []
    for i in range(segments):
        angle = i * delta_angle
        offset = Vec2(math.cos(angle), math.sin(angle)) * apothem
        bodies.append(builder.position(center + offset).rotation(angle).build())

    joints = [
        world.add_weld_joint(
            body,
            next_body,
            local_anchor_a=(0, half_length),
            local_anchor_b=(0, -half_length),
            # Each capsule is turned a step further round than the one before,
            # and the weld holds that bend rather than straightening it.
            reference_angle=delta_angle,
            angular_hertz=hertz,
            angular_damping_ratio=damping_ratio,
        )
        for body, next_body in pairwise(bodies + bodies[:1])
    ]
    return bodies, joints


class Car:
    """A car with sprung wheels driven by motors, ported from Box2D's samples.

    Each wheel hangs from the chassis on a wheel joint. Its spring, along the
    chassis's up axis, is the suspension, and its motor turns the wheel.

    Attributes:
        chassis, rear_wheel, front_wheel: The car's bodies.
        rear_axle, front_axle: The wheel joints holding the wheels on.
    """

    def __init__(
        self,
        world: World,
        position,
        scale=1.0,
        hertz=5.0,
        damping_ratio=0.7,
        torque=2.5,
    ):
        """Build the car standing on the ground at ``position``.

        Args:
            world: The world to build the car in.
            position: The point on the ground below the middle of the car.
            scale: Size multiplier. Densities are divided by it, so the mass
                grows in proportion to the scale rather than to its square.
            hertz: Suspension spring frequency, in Hz.
            damping_ratio: Suspension damping ratio.
            torque: The most torque each wheel's motor may apply, in N·m.
        """
        x, y = position
        vertices = [
            (-1.5, -0.5),
            (1.5, -0.5),
            (1.5, 0.0),
            (0.0, 0.9),
            (-1.15, 0.9),
            (-1.5, 0.2),
        ]
        self.chassis = (
            world.new_body()
            .dynamic()
            .position(x, y + scale)
            .polygon(
                [(0.85 * scale * vx, 0.85 * scale * vy) for vx, vy in vertices],
                radius=0.15 * scale,
                density=1.0 / scale,
                friction=0.2,
            )
            .build()
        )

        wheel_builder = (
            world.new_body()
            .dynamic()
            .circle(0.4 * scale, density=2.0 / scale, friction=1.5)
        )
        self.rear_wheel = wheel_builder.position(x - scale, y + 0.35 * scale).build()
        self.front_wheel = wheel_builder.position(x + scale, y + 0.4 * scale).build()

        axle_def = {
            "axis": (0, 1),
            # A motor held at zero speed resists the wheel turning, up to its
            # torque: that is the brake, and the car starts with it on.
            "enable_motor": True,
            "motor_speed": 0,
            "max_motor_torque": torque,
            "enable_limit": True,
            "lower_limit": -0.25 * scale,
            "upper_limit": 0.25 * scale,
            "enable_spring": True,
            "spring_hertz": hertz,
            "spring_damping_ratio": damping_ratio,
        }
        self.rear_axle = world.add_wheel_joint(
            self.chassis, self.rear_wheel, anchor=self.rear_wheel.position, **axle_def
        )
        self.front_axle = world.add_wheel_joint(
            self.chassis, self.front_wheel, anchor=self.front_wheel.position, **axle_def
        )

    def destroy(self):
        """Remove the car from the world."""
        self.rear_axle.destroy()
        self.front_axle.destroy()
        self.rear_wheel.destroy()
        self.front_wheel.destroy()
        self.chassis.destroy()

    def set_speed(self, speed):
        """Set the motor speed for both wheels.

        Args:
            speed: Angular velocity in radians/second. Positive turns the
                wheels anticlockwise, which drives the car left.
        """
        self.rear_axle.motor_speed = speed
        self.front_axle.motor_speed = speed
        # A parked car falls asleep, and a new speed does not wake it. The
        # whole car is one island, so waking one axle's bodies wakes it all.
        self.rear_axle.wake_bodies()

    def set_torque(self, torque):
        """Set the most torque each wheel's motor may apply.

        Args:
            torque: Maximum torque in N·m.
        """
        self.rear_axle.max_motor_torque = torque
        self.front_axle.max_motor_torque = torque

    def set_hertz(self, hertz):
        """Set the suspension spring frequency.

        Args:
            hertz: Spring frequency in Hz.
        """
        self.rear_axle.spring_hertz = hertz
        self.front_axle.spring_hertz = hertz

    def set_damping_ratio(self, damping_ratio):
        """Set the suspension damping ratio.

        Args:
            damping_ratio: Damping ratio (non-dimensional).
        """
        self.rear_axle.spring_damping_ratio = damping_ratio
        self.front_axle.spring_damping_ratio = damping_ratio


def parse_svg_path(path, offset=(0.0, 0.0), scale=1.0, slop=0.005):
    """Turn an SVG path into chain points, the way Box2D's samples do.

    Handles the line commands an editor like Inkscape writes for a polyline --
    M/L, H, V and their relative forms -- including a command left implied
    before a run of coordinates. SVG's y axis points down, so it is flipped,
    after the offset is added and before scaling. A closing point that lands
    back on the first is dropped, since a chain loop closes itself.

    Args:
        path: The SVG path data, the ``d`` attribute.
        offset: Added to every point before scaling, in SVG units.
        scale: World units per SVG unit.
        slop: How close the last point must be to the first to be dropped.

    Returns:
        list[Vec2]: The points, in world coordinates.
    """
    commands = "MLHVmlhv"
    x = y = 0.0
    command = None
    points = []
    for token in path.split():
        if token[0] in commands:
            command = token[0]
            continue
        if token[0] in "zZ":
            break
        if command in "ML":
            x, y = (float(v) for v in token.split(","))
        elif command in "ml":
            dx, dy = (float(v) for v in token.split(","))
            x, y = x + dx, y + dy
        elif command == "H":
            x = float(token)
        elif command == "h":
            x += float(token)
        elif command == "V":
            y = float(token)
        elif command == "v":
            y += float(token)
        else:
            raise ValueError(f"unsupported SVG path command {command!r}")
        points.append(Vec2(scale * (x + offset[0]), -scale * (y + offset[1])))

    if len(points) > 2 and (points[0] - points[-1]).length <= slop:
        points.pop()
    return points
