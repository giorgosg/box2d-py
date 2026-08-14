# tests/test_jointdef.py
"""Joints are created from definitions, through one World.add_joint.

World carried seven joint factories totalling 488 of its 1229 lines, each a
long parameter list forwarded verbatim to a joint class, and each repeating the
same two pieces of logic: check both bodies belong to this world, and convert a
world anchor into local ones. Those live in add_joint now, and the parameter
lists are definitions.
"""

import math

import pytest

from box2d import (
    World,
    Vec2,
    DistanceJointDef,
    MotorJointDef,
    MouseJointDef,
    PrismaticJointDef,
    RevoluteJointDef,
    WeldJointDef,
    WheelJointDef,
)
from box2d.joint import (
    DistanceJoint,
    MotorJoint,
    MouseJoint,
    PrismaticJoint,
    RevoluteJoint,
    WeldJoint,
    WheelJoint,
)


@pytest.fixture
def world():
    world = World()
    yield world
    world.destroy()


@pytest.fixture
def bodies(world):
    a = world.add_body(body_type="dynamic", position=(0, 0))
    a.add_circle(radius=1.0)
    b = world.add_body(body_type="dynamic", position=(2, 0))
    b.add_circle(radius=1.0)
    return a, b


# --- add_joint builds the right joint from any definition -------------------


@pytest.mark.parametrize(
    "make_def,expected",
    [
        (lambda a, b: WeldJointDef(a, b, anchor=(1, 0)), WeldJoint),
        (lambda a, b: RevoluteJointDef(a, b, anchor=(1, 0)), RevoluteJoint),
        (lambda a, b: PrismaticJointDef(a, b, anchor=(1, 0)), PrismaticJoint),
        (lambda a, b: WheelJointDef(a, b, anchor=(1, 0)), WheelJoint),
        (lambda a, b: DistanceJointDef(a, b, length=2.0), DistanceJoint),
        (lambda a, b: MotorJointDef(a, b), MotorJoint),
    ],
    ids=["weld", "revolute", "prismatic", "wheel", "distance", "motor"],
)
def test_add_joint_creates_the_right_type(world, bodies, make_def, expected):
    joint = world.add_joint(make_def(*bodies))
    assert isinstance(joint, expected)
    assert joint.is_valid is True
    world.step(1 / 60, 4)


def test_add_joint_creates_a_mouse_joint(world, bodies):
    joint = world.add_joint(MouseJointDef(bodies[0], (1, 1)))
    assert isinstance(joint, MouseJoint)


def test_definition_settings_reach_the_joint(world, bodies):
    joint = world.add_joint(
        RevoluteJointDef(
            *bodies,
            anchor=(1, 0),
            enable_motor=True,
            max_motor_torque=100.0,
            motor_speed=2.0,
            enable_limit=True,
            lower_angle=-1.0,
            upper_angle=1.0,
        )
    )
    assert joint.motor_enabled is True
    assert joint.max_motor_torque == pytest.approx(100.0)
    assert joint.motor_speed == pytest.approx(2.0)
    assert joint.limit_enabled is True


def test_a_definition_can_build_several_joints(world):
    """Definitions hold no joint state, so one shape can be reused."""
    bodies = []
    for i in range(3):
        body = world.add_body(body_type="dynamic", position=(2 * i, 0))
        body.add_circle(radius=0.5)
        bodies.append(body)

    joints = [
        world.add_joint(
            RevoluteJointDef(a, b, anchor=(1, 0), enable_motor=True, max_motor_torque=5)
        )
        for a, b in zip(bodies, bodies[1:])
    ]
    assert len(joints) == 2
    assert all(j.max_motor_torque == pytest.approx(5.0) for j in joints)


def test_unset_fields_leave_box2d_defaults(world, bodies):
    """A field left as None is omitted rather than passed as None."""
    bare = world.add_joint(RevoluteJointDef(*bodies, anchor=(1, 0)))
    assert bare.motor_enabled is False
    assert bare.limit_enabled is False


# --- the checks that used to be copied into every factory -------------------


def test_world_anchor_becomes_both_local_anchors(world, bodies):
    a, b = bodies
    joint = world.add_joint(RevoluteJointDef(a, b, anchor=(1, 0)))
    # (1, 0) in world space is (1, 0) on a and (-1, 0) on b, which sits at (2, 0).
    assert joint.local_anchor_a == Vec2(1, 0)
    assert joint.local_anchor_b == Vec2(-1, 0)


def test_anchor_and_local_anchors_together_are_rejected(world, bodies):
    with pytest.raises(ValueError, match="not both"):
        world.add_joint(RevoluteJointDef(*bodies, anchor=(1, 0), local_anchor_a=(0, 0)))


def test_bodies_must_belong_to_this_world(world, bodies):
    other_world = World()
    try:
        stranger = other_world.add_body(body_type="dynamic")
        with pytest.raises(ValueError, match="must belong to this world"):
            world.add_joint(RevoluteJointDef(bodies[0], stranger, anchor=(0, 0)))
    finally:
        other_world.destroy()


def test_mouse_joint_body_is_checked_too(world):
    """The mouse joint factory never validated its body before."""
    other_world = World()
    try:
        stranger = other_world.add_body(body_type="dynamic")
        with pytest.raises(ValueError, match="must belong to this world"):
            world.add_joint(MouseJointDef(stranger, (0, 0)))
    finally:
        other_world.destroy()


# --- the shorthand methods still work exactly as before ---------------------


def test_shorthand_matches_add_joint(world, bodies):
    a, b = bodies
    direct = world.add_joint(
        RevoluteJointDef(a, b, anchor=(1, 0), max_motor_torque=25.0)
    )
    shorthand = world.add_revolute_joint(a, b, anchor=(1, 0), max_motor_torque=25.0)

    assert type(direct) is type(shorthand)
    assert direct.max_motor_torque == shorthand.max_motor_torque
    assert direct.local_anchor_a == shorthand.local_anchor_a


def test_shorthand_accepts_positional_anchors(world, bodies):
    joint = world.add_distance_joint(*bodies, (0, 0), (0, 0), length=2.0)
    assert isinstance(joint, DistanceJoint)
    assert joint.length == pytest.approx(2.0)


def test_prismatic_and_wheel_default_their_axis(world, bodies):
    """Both joints need an axis, so the definition supplies the usual one."""
    assert PrismaticJointDef(*bodies).axis == (1, 0)
    assert WheelJointDef(*bodies).axis == (1, 0)
    assert isinstance(world.add_prismatic_joint(*bodies, anchor=(1, 0)), PrismaticJoint)


def test_revolute_runtime_surface_matches_the_other_joints(world, bodies):
    """RevoluteJoint could be created with a motor but never toggled after."""
    joint = world.add_joint(RevoluteJointDef(*bodies, anchor=(1, 0)))

    joint.motor_enabled = True
    joint.limit_enabled = True
    joint.spring_enabled = True
    joint.spring_hertz = 3.0
    joint.spring_damping_ratio = 0.5
    joint.target_angle = math.pi / 8
    world.step(1 / 60, 4)

    assert joint.motor_enabled is True
    assert joint.limit_enabled is True
    assert joint.spring_enabled is True
    assert joint.spring_hertz == pytest.approx(3.0)
    assert joint.spring_damping_ratio == pytest.approx(0.5)
    assert joint.target_angle == pytest.approx(math.pi / 8)
    assert isinstance(joint.motor_torque, float)


# --- the filter joint, which had no binding at all --------------------------


def test_filter_joint_stops_two_bodies_colliding(world):
    """Categories work per shape and in groups; this names an exact pair."""
    ground = world.add_body(position=(0, 0))
    ground.add_box(20, 1)
    lower = world.add_body(body_type="dynamic", position=(0, 3))
    lower.add_box(1, 1)
    upper = world.add_body(body_type="dynamic", position=(0, 5))
    upper.add_box(1, 1)

    world.add_filter_joint(lower, upper)
    for _ in range(180):
        world.step(1 / 60, 4)

    assert abs(lower.position.y - upper.position.y) < 0.5, "they should overlap"


def test_without_a_filter_joint_they_stack(world):
    """The control for the test above."""
    ground = world.add_body(position=(0, 0))
    ground.add_box(20, 1)
    lower = world.add_body(body_type="dynamic", position=(0, 3))
    lower.add_box(1, 1)
    upper = world.add_body(body_type="dynamic", position=(0, 5))
    upper.add_box(1, 1)

    for _ in range(180):
        world.step(1 / 60, 4)

    assert abs(lower.position.y - upper.position.y) > 0.9


def test_filter_joint_still_collides_with_everything_else(world):
    ground = world.add_body(position=(0, 0))
    ground.add_box(20, 1)
    a = world.add_body(body_type="dynamic", position=(0, 3))
    a.add_box(1, 1)
    b = world.add_body(body_type="dynamic", position=(0, 5))
    b.add_box(1, 1)
    world.add_filter_joint(a, b)

    for _ in range(180):
        world.step(1 / 60, 4)

    assert a.position.y == pytest.approx(1.0, abs=0.2), "still lands on the ground"


def test_filter_joint_via_add_joint(world):
    from box2d import FilterJoint, FilterJointDef

    a = world.add_body(body_type="dynamic", position=(0, 0))
    b = world.add_body(body_type="dynamic", position=(1, 0))
    joint = world.add_joint(FilterJointDef(a, b))

    assert isinstance(joint, FilterJoint)
    assert joint.is_valid is True


def test_filter_joint_can_be_destroyed(world):
    a = world.add_body(body_type="dynamic", position=(0, 0))
    b = world.add_body(body_type="dynamic", position=(1, 0))
    joint = world.add_filter_joint(a, b)

    joint.destroy()
    assert joint.is_valid is False
