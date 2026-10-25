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
    MoverJointDef,
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
        (lambda a, b: DistanceJointDef(a, b, rest_length=2.0), DistanceJoint),
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
            target_motor_speed=2.0,
            enable_limit=True,
            lower_limit=-1.0,
            upper_limit=1.0,
        )
    )
    assert joint.enable_motor is True
    assert joint.max_motor_torque == pytest.approx(100.0)
    assert joint.target_motor_speed == pytest.approx(2.0)
    assert joint.enable_limit is True


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
    assert bare.enable_motor is False
    assert bare.enable_limit is False


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
    joint = world.add_distance_joint(*bodies, (0, 0), (0, 0), rest_length=2.0)
    assert isinstance(joint, DistanceJoint)
    assert joint.rest_length == pytest.approx(2.0)


def test_prismatic_and_wheel_default_their_axis(world, bodies):
    """Both joints need an axis, so the definition supplies the usual one."""
    assert PrismaticJointDef(*bodies).axis == (1, 0)
    assert WheelJointDef(*bodies).axis == (1, 0)
    assert isinstance(world.add_prismatic_joint(*bodies, anchor=(1, 0)), PrismaticJoint)


def test_revolute_runtime_surface_matches_the_other_joints(world, bodies):
    """RevoluteJoint could be created with a motor but never toggled after."""
    joint = world.add_joint(RevoluteJointDef(*bodies, anchor=(1, 0)))

    joint.enable_motor = True
    joint.enable_limit = True
    joint.enable_spring = True
    joint.spring_hertz = 3.0
    joint.spring_damping_ratio = 0.5
    joint.target_angle = math.pi / 8
    world.step(1 / 60, 4)

    assert joint.enable_motor is True
    assert joint.enable_limit is True
    assert joint.enable_spring is True
    assert joint.spring_hertz == pytest.approx(3.0)
    assert joint.spring_damping_ratio == pytest.approx(0.5)
    assert joint.target_angle == pytest.approx(math.pi / 8)
    assert isinstance(joint.current_motor_torque, float)


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


# --- conformance with Box2D's own definitions -------------------------------

#: Where our field name differs from the C one by choice rather than omission.
#: Each is named as the joint property it sets, which Box2D 3.2 renamed in its
#: functions but not in its definition structs.
_SPRING = {"hertz": "spring_hertz", "dampingRatio": "spring_damping_ratio"}
_MOTOR = {"motorSpeed": "target_motor_speed"}
_DEF_ALIASES = {
    "RevoluteJointDef": {
        **_SPRING,
        **_MOTOR,
        "lowerAngle": "lower_limit",
        "upperAngle": "upper_limit",
    },
    "PrismaticJointDef": {
        **_SPRING,
        **_MOTOR,
        "lowerTranslation": "lower_limit",
        "upperTranslation": "upper_limit",
    },
    "WheelJointDef": {
        **_SPRING,
        **_MOTOR,
        "lowerTranslation": "lower_limit",
        "upperTranslation": "upper_limit",
    },
    "DistanceJointDef": {
        **_SPRING,
        **_MOTOR,
        "length": "rest_length",
        "minLength": "lower_limit",
        "maxLength": "upper_limit",
    },
    "PogoJointDef": _SPRING,
}


def _camel(name):
    head, *rest = name.split("_")
    return head + "".join(part.title() for part in rest)


@pytest.mark.parametrize(
    "name",
    [
        "RevoluteJointDef",
        "PrismaticJointDef",
        "WheelJointDef",
        "DistanceJointDef",
        "WeldJointDef",
        "MotorJointDef",
        "PogoJointDef",
    ],
)
def test_joint_def_covers_box2d_s_own(name):
    """A field missing from a def cannot be set at creation time.

    RevoluteJointDef had no spring fields at all, so a jointed figure could
    not be given springy limbs without reaching past the definition. The same
    check found PrismaticJointDef missing target_translation and
    DistanceJointDef missing its spring force range.
    """
    from dataclasses import fields

    import box2d.jointdef as jointdef
    from box2d._box2d import ffi

    definition = getattr(jointdef, name)
    base_fields = {
        "body_a",
        "body_b",
        "local_anchor_a",
        "local_anchor_b",
        "anchor",
        "collide_connected",
    }
    ours = {field.name for field in fields(definition)} - base_fields
    ours_camel = {_camel(field) for field in ours}

    struct = ffi.new(f"b2{name}*")
    aliases = _DEF_ALIASES.get(name, {})
    missing = [
        c_name
        for c_name in dir(struct)
        if c_name not in ("base", "internalValue")
        and c_name not in ours_camel
        and aliases.get(c_name) not in ours
    ]
    assert missing == [], f"{name} cannot set: {missing}"


def test_revolute_spring_reaches_the_joint():
    """Set at creation, not just accepted."""
    import math

    from box2d import RevoluteJointDef, World

    world = World()
    ground = world.add_body(position=(0, 0))
    arm = world.add_body(body_type="dynamic", position=(1, 0))
    arm.add_box(2, 0.2)

    joint = world.add_joint(
        RevoluteJointDef(
            ground,
            arm,
            anchor=(0, 0),
            enable_spring=True,
            spring_hertz=4.0,
            spring_damping_ratio=0.5,
            target_angle=0.25 * math.pi,
        )
    )

    assert joint.enable_spring is True
    assert joint.spring_hertz == pytest.approx(4.0)
    assert joint.spring_damping_ratio == pytest.approx(0.5)
    assert joint.target_angle == pytest.approx(0.25 * math.pi)
    world.destroy()


def test_revolute_spring_pulls_towards_its_target():
    """The reason the field matters: it holds a limb up against gravity."""
    from box2d import RevoluteJointDef, World

    def lowest_point(enable_spring):
        """The deepest the arm ever dips.

        Comparing final positions would not do: without the spring the arm is
        an undamped pendulum, so where it ends up depends entirely on which
        step you stop at, and it passes back through horizontal every swing.
        """
        world = World()
        ground = world.add_body(position=(0, 0))
        arm = world.add_body(body_type="dynamic", position=(1, 0))
        arm.add_box(2, 0.2)
        world.add_joint(
            RevoluteJointDef(
                ground,
                arm,
                anchor=(0, 0),
                enable_spring=enable_spring,
                spring_hertz=3.0,
                spring_damping_ratio=0.8,
                target_angle=0.0,
            )
        )
        lowest = 0.0
        for _ in range(240):
            world.step(1 / 60, 4)
            lowest = min(lowest, arm.position.y)
        world.destroy()
        return lowest

    sprung, free = lowest_point(True), lowest_point(False)
    assert sprung > -0.3, f"the sprung arm should barely dip, got {sprung:.2f}"
    assert free < -0.9, f"the free arm should swing right down, got {free:.2f}"


# --- one name per setting ---------------------------------------------------

#: Definition fields with no property of the same name, and why.
_CREATION_ONLY = {
    "body",  # the body a mouse joint drags, fixed for the joint's life
    # These become the rotation of the joint's local frames, and are changed
    # later through local_frame_a and local_frame_b.
    "axis",
    "reference_angle",
    # A pogo joint is rebuilt every step rather than changed, and Box2D has
    # no setter for any of these.
    "normal",
    "max_tension_force",
    "max_compression_force",
    # A pogo's starting state, carried over from the previous pogo. PogoJoint
    # reads them back, but only to pass them on.
    "impulse",
    "velocity",
}


def _joint_definitions():
    from dataclasses import is_dataclass

    import box2d.jointdef as jointdef

    return [
        value
        for value in vars(jointdef).values()
        if isinstance(value, type)
        and is_dataclass(value)
        and getattr(value, "joint_class", None) is not None
    ]


@pytest.mark.parametrize("definition", _joint_definitions(), ids=lambda d: d.__name__)
def test_a_joint_is_changed_by_the_names_it_was_made_with(definition):
    """Every setting a joint can change later is a property named as at creation.

    A joint made with enable_motor= used to be changed with motor_enabled,
    made with hertz= changed with spring_hertz, made with lower_angle= changed
    with lower_limit. Two testbed controls set a name the joint did not have
    because of it.
    """
    import inspect
    from dataclasses import fields

    from box2d.jointdef import JointDef

    common = {field.name for field in fields(JointDef)}
    joint_class = definition.joint_class
    for field in fields(definition):
        if field.name in common or field.name in _CREATION_ONLY:
            continue
        attribute = inspect.getattr_static(joint_class, field.name, None)
        # Having __set__ is not enough: a read-only accessor has one too, and
        # it raises. No attribute at all is not settable either.
        if isinstance(attribute, property):
            settable = attribute.fset is not None
        else:
            settable = getattr(attribute, "settable", False)
        assert settable, (
            f"{definition.__name__}.{field.name} has no settable "
            f"{joint_class.__name__}.{field.name}"
        )


# --- limits stay ordered ----------------------------------------------------
# Box2D asserts lower <= upper only in debug builds; release builds swap the
# two, so setting one bound past the other silently moved the other one.

_LIMITED = {
    "revolute": RevoluteJointDef,
    "prismatic": PrismaticJointDef,
    "wheel": WheelJointDef,
    # Distance limits are lengths, which Box2D clamps to be positive, so the
    # values below are all positive.
    "distance": DistanceJointDef,
}

#: Box2D defaults both limits of these to zero.
_ZERO_DEFAULT_LIMITS = {
    name: definition for name, definition in _LIMITED.items() if name != "distance"
}


@pytest.fixture(params=list(_LIMITED), ids=list(_LIMITED))
def limited_joint(request, world, bodies):
    return world.add_joint(_LIMITED[request.param](*bodies, anchor=(1, 0)))


def test_each_limit_can_be_set_on_its_own(limited_joint):
    limited_joint.set_limits(1.0, 3.0)
    limited_joint.lower_limit = 1.5
    limited_joint.upper_limit = 2.75
    assert limited_joint.lower_limit == pytest.approx(1.5)
    assert limited_joint.upper_limit == pytest.approx(2.75)


def test_limits_that_cross_are_refused(limited_joint):
    limited_joint.set_limits(1.0, 3.0)
    with pytest.raises(ValueError, match="lower 2.0 is above upper 1.0"):
        limited_joint.set_limits(2.0, 1.0)
    with pytest.raises(ValueError, match="above upper"):
        limited_joint.lower_limit = 3.5
    with pytest.raises(ValueError, match="above upper"):
        limited_joint.upper_limit = 0.5
    assert (limited_joint.lower_limit, limited_joint.upper_limit) == (1.0, 3.0)


# Box2D holds a distance joint's limits to at least its linear slop, 0.005 m,
# and at most 100 km. The ordering check has to compare what it will store.
_SLOP = 0.005


def test_a_distance_limit_below_the_floor_is_raised_to_it(world, bodies):
    joint = world.add_joint(DistanceJointDef(*bodies, upper_limit=0.003))
    assert joint.lower_limit == pytest.approx(_SLOP)
    assert joint.upper_limit == pytest.approx(_SLOP), "not left below the lower"


def test_a_distance_upper_limit_below_the_floor_meets_the_default_lower(world, bodies):
    """The lower defaults to the floor, so an upper below it is not crossed."""
    joint = world.add_joint(DistanceJointDef(*bodies))
    joint.upper_limit = 0.004
    assert (joint.lower_limit, joint.upper_limit) == pytest.approx((_SLOP, _SLOP))


def test_distance_limits_below_the_floor_both_become_it(world, bodies):
    joint = world.add_joint(DistanceJointDef(*bodies))
    joint.set_limits(-2.0, -1.0)
    assert (joint.lower_limit, joint.upper_limit) == pytest.approx((_SLOP, _SLOP))


def test_crossed_distance_limits_are_reported_as_given(world, bodies):
    """Even when one of them would be raised to the floor."""
    joint = world.add_joint(DistanceJointDef(*bodies))
    with pytest.raises(ValueError, match="lower 3.0 is above upper -1.0"):
        joint.set_limits(3.0, -1.0)
    with pytest.raises(ValueError, match="lower 3.0 is above upper -1.0"):
        world.add_joint(DistanceJointDef(*bodies, lower_limit=3.0, upper_limit=-1.0))


def test_a_distance_limit_past_the_cap_is_lowered_to_it(world, bodies):
    joint = world.add_joint(DistanceJointDef(*bodies))
    joint.set_limits(1.0, 1e9)
    assert joint.upper_limit == pytest.approx(100_000.0)


def test_an_infinite_distance_limit_is_still_refused(world, bodies):
    from box2d import InvalidInputError

    joint = world.add_joint(DistanceJointDef(*bodies))
    with pytest.raises(InvalidInputError):
        joint.set_limits(1.0, math.inf)


@pytest.mark.parametrize("definition", list(_LIMITED.values()), ids=list(_LIMITED))
def test_a_joint_cannot_be_made_with_crossed_limits(world, bodies, definition):
    crossed = definition(*bodies, anchor=(1, 0), lower_limit=1.0, upper_limit=-1.0)
    with pytest.raises(ValueError, match="above upper"):
        world.add_joint(crossed)


def test_a_limit_can_be_set_equal_to_the_other(limited_joint):
    """Box2D stores limits as 32-bit floats, so the bound read back is not
    the 0.1 that was set; equal bounds must still be accepted."""
    limited_joint.set_limits(0.1, 0.2)
    limited_joint.upper_limit = 0.1
    limited_joint.lower_limit = 0.1
    assert limited_joint.upper_limit == pytest.approx(0.1)


@pytest.mark.parametrize(
    "definition", list(_ZERO_DEFAULT_LIMITS.values()), ids=list(_ZERO_DEFAULT_LIMITS)
)
def test_one_limit_alone_is_checked_against_the_others_default(
    world, bodies, definition
):
    """Box2D defaults both limits to zero, so a lower limit of 0.5 given alone
    crosses an upper limit nobody set -- the error has to say so."""
    with pytest.raises(ValueError, match="a limit not given is 0"):
        world.add_joint(definition(*bodies, anchor=(1, 0), lower_limit=0.5))


# --- definitions refuse names they do not have -------------------------------


@pytest.mark.parametrize("definition", _joint_definitions(), ids=lambda d: d.__name__)
def test_a_definition_refuses_a_field_it_does_not_have(world, bodies, definition):
    """A misspelt or renamed field must fail, not be silently ignored.

    motor_speed became target_motor_speed; a definition that took
    ``d.motor_speed = 5`` would build its joint with the motor stopped.
    """
    if definition is MouseJointDef:
        made = definition(bodies[0], target=(0, 0))
    else:
        made = definition(*bodies)
    with pytest.raises(AttributeError):
        made.motor_speed = 5.0


@pytest.mark.parametrize(
    "definition", [MotorJointDef, MoverJointDef], ids=lambda d: d.__name__
)
def test_definitions_that_drop_anchors_still_build(world, bodies, definition):
    """These override joint_arguments and call the base class's."""
    arguments = definition(*bodies).joint_arguments()
    assert "local_anchor_a" not in arguments
    assert world.add_joint(definition(*bodies)).is_valid


def test_a_definition_copies_and_compares_by_value(bodies):
    import copy

    made = RevoluteJointDef(*bodies, anchor=(1, 0), target_motor_speed=2.0)
    duplicate = copy.copy(made)
    assert duplicate == made
    duplicate.target_motor_speed = 3.0
    assert made.target_motor_speed == 2.0


# --- a prismatic joint's reference angle --------------------------------------
# Box2D 3.2 has no referenceAngle field, but a prismatic joint holds the two
# bodies' frames at the same rotation, so the reference angle is the
# difference between the frames' rotations: frame A carries the axis, and
# frame B is turned back from it by the reference angle.


def _slider(world, angle_b, axis=(1, 0), **settings):
    """A static body at the origin and a dynamic one at (2, 0), turned by
    angle_b, joined by a prismatic joint."""
    base = world.new_body().static().position(0, 0).box(0.5, 0.5).build()
    slider = (
        world.new_body().dynamic().position(2, 0).rotation(angle_b).box(1, 0.5).build()
    )
    joint = world.add_prismatic_joint(
        base, slider, anchor=(2, 0), axis=axis, **settings
    )
    return slider, joint


def _run(world, steps=120):
    for _ in range(steps):
        world.step(1 / 60, 4)


def test_prismatic_reference_angle_holds_the_bodies_at_that_angle(world):
    slider, _ = _slider(world, 0.7, reference_angle=0.7)
    _run(world)
    assert slider.rotation == pytest.approx(0.7, abs=1e-3)


def test_prismatic_default_reference_angle_turns_the_bodies_level(world):
    slider, _ = _slider(world, 0.7)
    _run(world)
    assert slider.rotation == pytest.approx(0.0, abs=1e-3)


def test_prismatic_reference_angle_leaves_the_axis_alone(world):
    """On a vertical axis the slider still drops along it, turned as given."""
    slider, joint = _slider(world, 0.7, axis=(0, 1), reference_angle=0.7)
    _run(world, 30)
    assert slider.position.x == pytest.approx(2.0, abs=1e-3)
    assert slider.position.y < -0.5, "gravity should slide it down the axis"
    assert joint.current_translation == pytest.approx(slider.position.y, abs=1e-3)
    assert slider.rotation == pytest.approx(0.7, abs=1e-3)
