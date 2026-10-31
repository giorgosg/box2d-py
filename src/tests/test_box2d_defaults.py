"""box2d-py takes Box2D's defaults, unless it says why not.

Anything left unset -- a joint argument, a definition field, a world setting --
ends up as the value in Box2D's own ``b2Default*Def``. Where box2d-py chooses
otherwise, the reason is in the code and the docstring, and the difference is
listed here, so a new one cannot creep in unnoticed: these tests compare what
box2d-py hands Box2D, field by field, with Box2D's own default definition.

The wheel joint is why: its spring was off, at 0 Hz, where Box2D's wheel
joint starts sprung at 1 Hz and a damping ratio of 0.7.
"""

import math

import pytest

from box2d import World, WheelJointDef
from box2d.dataclasses import BodyDef
from box2d._box2d import ffi, lib
from box2d.joint import WheelJoint


def _differences(ours, theirs, skip=(), path=""):
    """The dotted paths of the fields where two C structs differ.

    Nested structs are compared field by field. Pointers are not compared:
    they hold data the call supplies, or an address of box2d-py's own.
    """
    found = []
    for name, field in ffi.typeof(theirs).fields:
        where = f"{path}{name}"
        if where in skip:
            continue
        mine, box2d = getattr(ours, name), getattr(theirs, name)
        kind = field.type.kind
        if kind == "struct":
            found += _differences(mine, box2d, skip, f"{where}.")
        elif kind == "primitive":
            both_nan = (
                isinstance(mine, float) and math.isnan(mine) and math.isnan(box2d)
            )
            if mine != box2d and not both_nan:
                found.append(where)
    return found


# --- joints ------------------------------------------------------------------

#: Each joint made with nothing but its bodies, beside Box2D's default
#: definition for it. Body a is at the origin and body b 3 m to its right.
_JOINTS = {
    "DistanceJoint": (
        lambda world, a, b: world.add_distance_joint(a, b),
        lib.b2DefaultDistanceJointDef,
    ),
    "FilterJoint": (
        lambda world, a, b: world.add_filter_joint(a, b),
        lib.b2DefaultFilterJointDef,
    ),
    "MotorJoint": (
        lambda world, a, b: world.add_motor_joint(a, b),
        lib.b2DefaultMotorJointDef,
    ),
    "MoverJoint": (
        lambda world, a, b: world.add_mover_joint(a, b),
        lib.b2DefaultMoverJointDef,
    ),
    "PogoJoint": (
        lambda world, a, b: world.add_pogo_joint(a, b),
        lib.b2DefaultPogoJointDef,
    ),
    "PrismaticJoint": (
        lambda world, a, b: world.add_prismatic_joint(a, b),
        lib.b2DefaultPrismaticJointDef,
    ),
    "RevoluteJoint": (
        lambda world, a, b: world.add_revolute_joint(a, b),
        lib.b2DefaultRevoluteJointDef,
    ),
    "WeldJoint": (
        lambda world, a, b: world.add_weld_joint(a, b),
        lib.b2DefaultWeldJointDef,
    ),
    "WheelJoint": (
        lambda world, a, b: world.add_wheel_joint(a, b),
        lib.b2DefaultWheelJointDef,
    ),
}

#: What every joint sets from the call itself: the bodies it joins.
_FROM_THE_CALL = ("base.bodyIdA", "base.bodyIdB")

#: Fields box2d-py fills in as Box2D would on making the joint, so they
#: differ in the definition but not in the joint Box2D stores.
_STORED_THE_SAME = {
    # Box2D raises the lower limit to its linear slop, 0.005 m; box2d-py
    # does so first to check the limits' order against what will be stored.
    "DistanceJoint": ("minLength",),
}

#: Where a joint's default is box2d-py's own rather than Box2D's, and why.
#: Each is explained where the default is chosen, and in the docstrings.
_JOINT_DIFFERENCES = {
    "PogoJoint": {
        # Box2D's normal is (0, 0), along which the spring pushes nowhere,
        # so box2d-py's points straight up.
        "normal.y",
    },
}


@pytest.fixture
def three_apart(world):
    a = world.new_body().dynamic().position(0, 0).circle(0.5).build()
    b = world.new_body().dynamic().position(3, 0).circle(0.5).build()
    return a, b


@pytest.mark.parametrize("name", sorted(_JOINTS))
def test_a_joint_left_to_its_defaults_gets_box2d_s(world, three_apart, name):
    make, box2d_default = _JOINTS[name]
    joint = make(world, *three_apart)
    assert type(joint).__name__ == name

    skip = _FROM_THE_CALL + _STORED_THE_SAME.get(name, ())
    differences = _differences(joint._def, box2d_default(), skip)
    assert set(differences) == _JOINT_DIFFERENCES.get(name, set())


def test_every_joint_with_a_box2d_definition_is_compared():
    """A joint added later is compared too, once it is listed above."""
    import box2d.joint as joint_module

    with_definitions = {
        name
        for name in dir(joint_module)
        if name.endswith("Joint")
        and name not in ("Joint", "MouseJoint")
        and hasattr(lib, f"b2Default{name}Def")
    }
    assert with_definitions == set(_JOINTS)


def test_a_wheel_joint_is_sprung_as_box2d_s_is(world, three_apart):
    box2d = lib.b2DefaultWheelJointDef()
    for joint in (
        world.add_wheel_joint(*three_apart),
        world.add_joint(WheelJointDef(*three_apart)),
        WheelJoint(world, *three_apart, (0, 0), (0, 0), axis=(1, 0)),
    ):
        assert joint.enable_spring is True
        assert joint.spring_hertz == pytest.approx(box2d.hertz) == 1.0
        assert joint.spring_damping_ratio == pytest.approx(box2d.dampingRatio)
        assert joint.spring_damping_ratio == pytest.approx(0.7)


def test_a_wheel_joint_s_spring_can_still_be_turned_off(world, three_apart):
    joint = world.add_wheel_joint(*three_apart, enable_spring=False)
    assert joint.enable_spring is False


def test_a_default_wheel_holds_its_wheel_up(world):
    """Sprung by default, a wheel hangs on its axle instead of falling off it.

    With the old defaults the spring was off, so nothing held the wheel along
    the axis and it fell freely.
    """
    chassis = world.new_body().static().position(0, 2).build()
    wheel = world.new_body().dynamic().position(0, 1).circle(0.4).build()
    world.add_wheel_joint(chassis, wheel, anchor=wheel.position, axis=(0, 1))
    for _ in range(240):
        world.step(1 / 60, 4)
    assert wheel.position.y > 0


# --- bodies ------------------------------------------------------------------


def test_a_body_definition_left_to_its_defaults_is_box2d_s():
    assert _differences(BodyDef().b2BodyDef, lib.b2DefaultBodyDef()) == []


def test_a_body_made_with_no_arguments_is_box2d_s_default(world):
    box2d = lib.b2DefaultBodyDef()
    assert box2d.type == lib.b2_staticBody
    assert world.add_body().type == "static"

    # A static body is never awake, so the rest are read from a dynamic one.
    body = world.add_body(body_type="dynamic")
    assert body.gravity_scale == box2d.gravityScale
    assert body.sleep_threshold == pytest.approx(box2d.sleepThreshold)
    assert body.safety_factor == pytest.approx(box2d.safetyFactor)
    assert body.enable_sleeping == box2d.enableSleep
    assert body.awake == box2d.isAwake
    assert body.enabled == box2d.isEnabled
    assert body.is_bullet == box2d.isBullet


# --- worlds ------------------------------------------------------------------

#: b2WorldDef's fields, each beside the World property that reads it back.
_WORLD_SETTINGS = {
    "restitutionThreshold": "restitution_threshold",
    "restitutionIterations": "restitution_iterations",
    "enableRestitutionPropagation": "enable_restitution_propagation",
    "hitEventThreshold": "hit_event_threshold",
    "contactHertz": "contact_hertz",
    "contactDampingRatio": "contact_damping_ratio",
    "contactSpeed": "contact_push_speed",
    "maximumLinearSpeed": "max_linear_speed",
    "enableSleep": "enable_sleeping",
    "enableContinuous": "enable_continuous",
}

#: The rest of b2WorldDef, and why no property is compared with it.
_WORLD_NOT_COMPARED = {
    # World(gravity=...) defaults to (0, -10), compared on its own below.
    "gravity",
    # World(threads=1): Box2D raises its 0 to 1 worker.
    "workerCount",
    # Callbacks, the task system and user data are box2d-py's to fill in.
    "frictionCallback",
    "restitutionCallback",
    "enqueueTask",
    "finishTask",
    "userTaskContext",
    "userData",
    # World(capacity=None) leaves it as Box2D's: see test_world.py.
    "capacity",
    "internalValue",
}


def test_every_world_setting_is_compared():
    fields = {name for name, _ in ffi.typeof(lib.b2DefaultWorldDef()).fields}
    assert fields == set(_WORLD_SETTINGS) | _WORLD_NOT_COMPARED


def test_a_world_made_with_no_arguments_has_box2d_s_settings():
    box2d = lib.b2DefaultWorldDef()
    world = World()
    try:
        assert world.gravity == (box2d.gravity.x, box2d.gravity.y)
        assert world.worker_count == max(box2d.workerCount, 1)
        for field, setting in _WORLD_SETTINGS.items():
            ours = getattr(world, setting)
            assert ours == pytest.approx(getattr(box2d, field)), setting
    finally:
        world.destroy()
