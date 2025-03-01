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
