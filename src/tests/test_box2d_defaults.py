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

from box2d import DistanceJointDef, SurfaceMaterial, World, WheelJointDef
from box2d.dataclasses import BodyDef
from box2d.shapedef import ChainDef, ShapeDef
from box2d._box2d import ffi, lib
from box2d.joint import DistanceJoint, WheelJoint


def _differences(ours, theirs, skip=(), path=""):
    """The dotted paths of the fields where two C structs differ.

    Nested structs are compared field by field, and primitive and enum fields
    by value. Pointers are not compared:
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
        elif kind in ("primitive", "enum"):
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
    "DistanceJoint": {
        # Box2D's rest length is 1 m, wherever the anchors are; box2d-py's is
        # how far apart they are, 3 m here.
        "length",
    },
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


# --- a distance joint's rest length ------------------------------------------


def test_a_distance_joint_holds_its_bodies_as_far_apart_as_they_are(world, three_apart):
    """Not Box2D's 1 m, which would pull bodies 3 m apart together at once."""
    for joint in (
        world.add_distance_joint(*three_apart),
        world.add_joint(DistanceJointDef(*three_apart)),
        DistanceJoint(world, *three_apart, (0, 0), (0, 0)),
    ):
        assert joint.rest_length == pytest.approx(3.0)
        assert joint.current_length == pytest.approx(3.0)


def test_the_rest_length_is_between_the_anchors_not_the_bodies(world):
    a = world.new_body().dynamic().position(0, 0).build()
    # Turned a quarter turn, so its local x axis points along the world's y.
    b = world.new_body().dynamic().position(3, 0).rotation(math.pi / 2).build()
    joint = world.add_distance_joint(
        a, b, local_anchor_a=(0.5, 0), local_anchor_b=(1, 0.5)
    )
    # Anchor a is at (0.5, 0); anchor b at (3 - 0.5, 1).
    assert joint.rest_length == pytest.approx(math.hypot(2.0, 1.0))
    assert joint.rest_length == pytest.approx(joint.current_length)


def test_a_rest_length_given_is_kept(world, three_apart):
    assert world.add_distance_joint(*three_apart, rest_length=2.0).rest_length == (
        pytest.approx(2.0)
    )
    joint = world.add_joint(DistanceJointDef(*three_apart, rest_length=5.0))
    assert joint.rest_length == pytest.approx(5.0)


def test_a_distance_joint_with_both_anchors_at_one_point_rests_at_the_floor(
    world, three_apart
):
    """Box2D holds a rest length to at least its linear slop, 0.005 m."""
    joint = world.add_distance_joint(*three_apart, anchor=(1, 0))
    assert joint.rest_length == pytest.approx(0.005)


def test_a_rest_length_from_anchors_past_the_cap_is_lowered_to_it(world):
    """Box2D holds a rest length to at most B2_HUGE, 100 km."""
    a = world.new_body().dynamic().position(0, 0).build()
    b = world.new_body().dynamic().position(200_000, 0).build()
    joint = world.add_distance_joint(a, b)
    assert joint.rest_length == pytest.approx(100_000.0)


def test_a_rest_length_from_anchors_still_has_its_limits_checked(world, three_apart):
    with pytest.raises(ValueError, match="lower 4.0 is above upper 2.0"):
        world.add_distance_joint(*three_apart, lower_limit=4.0, upper_limit=2.0)


def test_the_bodies_stay_where_they_were_put(world, three_apart):
    a, b = three_apart
    world.gravity = (0, 0)
    world.add_distance_joint(a, b)
    for _ in range(60):
        world.step(1 / 60, 4)
    assert (b.position - a.position).length == pytest.approx(3.0, abs=1e-3)


# --- shapes and chains -------------------------------------------------------


def test_a_shape_definition_left_to_its_defaults_is_box2d_s():
    assert _differences(ShapeDef().b2ShapeDef, lib.b2DefaultShapeDef()) == []


def test_a_shape_made_with_no_settings_has_box2d_s(world):
    box2d = lib.b2DefaultShapeDef()
    body = world.new_body().dynamic().build()
    for shape in (
        body.add_circle(0.5),
        body.add_box(1, 1),
        body.add_capsule((0, 0), (1, 0), 0.25),
        body.add_polygon([(0, 0), (1, 0), (0, 1)]),
        body.add_segment((0, 0), (1, 0)),
    ):
        assert shape.friction == pytest.approx(box2d.material.friction)
        assert shape.restitution == box2d.material.restitution
        assert shape.rolling_resistance == box2d.material.rollingResistance
        assert shape.tangent_speed == box2d.material.tangentSpeed
        assert shape.user_material == box2d.material.userMaterialId
        assert shape.density == box2d.density
        assert shape.is_sensor == box2d.isSensor
        assert shape.enable_sensor_events == box2d.enableSensorEvents
        assert shape.enable_contact_events == box2d.enableContactEvents
        assert shape.enable_hit_events == box2d.enableHitEvents
        assert shape.enable_pre_solve_events == box2d.enablePreSolveEvents
        filter = shape.filter
        assert filter.category == box2d.filter.categoryBits
        assert filter.mask == box2d.filter.maskBits
        assert filter.group == box2d.filter.groupIndex


#: A chain's fields that hold what the call supplies: its points.
_CHAIN_FROM_THE_CALL = ("pointCount",)

#: Where a chain's default is box2d-py's own rather than Box2D's, and why.
_CHAIN_DIFFERENCES = {
    # Box2D leaves the ghosts at infinity, a sentinel it refuses to build an
    # open chain with, so box2d-py carries each end segment straight on.
    "ghost1.x",
    "ghost1.y",
    "ghost2.x",
    "ghost2.y",
}


def test_a_chain_definition_left_to_its_defaults_is_box2d_s():
    ours = ChainDef([(0, 0), (1, 0), (2, 0)]).b2ChainDef
    box2d = lib.b2DefaultChainDef()
    differences = _differences(ours, box2d, _CHAIN_FROM_THE_CALL)
    assert set(differences) == _CHAIN_DIFFERENCES
    assert ours.materialCount == box2d.materialCount == 1
    assert _differences(ours.materials[0], box2d.materials[0]) == []


def test_a_chain_made_with_no_settings_has_box2d_s(world):
    """Each segment has Box2D's chain material, id included, and filter.

    Chain.create made a new SurfaceMaterial for every chain, so each chain's
    segments carried an id of their own -- 1, 2, 3 -- rather than Box2D's 0.
    """
    box2d = lib.b2DefaultChainDef()
    material, filter = box2d.materials[0], box2d.filter
    body = world.new_body().static().build()
    built = world.new_body().static().chain([(0, 1), (1, 1), (2, 1)]).build().chains[0]
    for chain in (body.add_chain([(0, 0), (1, 0), (2, 0)]), built):
        for segment in chain.segments:
            assert segment.user_material == material.userMaterialId == 0
            assert segment.friction == pytest.approx(material.friction)
            assert segment.restitution == material.restitution
            assert segment.rolling_resistance == material.rollingResistance
            assert segment.tangent_speed == material.tangentSpeed
            assert segment.enable_sensor_events == box2d.enableSensorEvents
            assert segment.filter.category == filter.categoryBits
            assert segment.filter.mask == filter.maskBits
            assert segment.filter.group == filter.groupIndex


def test_a_chain_given_one_material_field_keeps_box2d_s_others(world):
    chain = world.new_body().static().build().add_chain([(0, 0), (1, 0)], friction=0.1)
    box2d = lib.b2DefaultChainDef().materials[0]
    segment = chain.segments[0]
    assert segment.friction == pytest.approx(0.1)
    assert segment.restitution == box2d.restitution


def test_a_differing_enum_field_is_found():
    """b2BodyDef.type is an enum, which cffi reports apart from primitives."""
    ours = BodyDef(type=lib.b2_dynamicBody).b2BodyDef
    assert _differences(ours, lib.b2DefaultBodyDef()) == ["type"]


def test_a_material_left_to_its_defaults_is_box2d_s():
    """Its id included: 0, as in Box2D.

    Each material used to number itself from a counter, 1, 2, 3, so that a
    registry could find it by its id, where Box2D's default id is 0.
    """
    material = SurfaceMaterial()
    assert (
        _differences(material.b2SurfaceMaterial, lib.b2DefaultSurfaceMaterial()) == []
    )


# --- sensor events -----------------------------------------------------------


def _seen_by(world, sensor_flag, visitor_flags):
    """The visitors a sensor box at the origin reports over half a second.

    Each visitor is a small ball inside the box, with its own
    enable_sensor_events setting.
    """
    world.new_body().static().box(
        4, 4, is_sensor=True, enable_sensor_events=sensor_flag
    ).build()
    visitors = [
        world.new_body()
        .dynamic()
        .position(index - 1, 0)
        .circle(0.25, enable_sensor_events=flag)
        .build()
        .shapes[0]
        for index, flag in enumerate(visitor_flags)
    ]
    seen = []
    for _ in range(30):
        world.step(1 / 60, 4)
        seen += [event.visitor for event in world.get_sensor_events().begin]
    return [visitors.index(visitor) for visitor in seen]


def test_a_sensor_sees_only_the_shapes_that_opt_in(world):
    assert _seen_by(world, True, [False, True]) == [1]


def test_a_sensor_that_has_not_opted_in_sees_nothing(world):
    """Sensor events are opt-in on both shapes, as in Box2D."""
    assert _seen_by(world, False, [True, True]) == []


def test_a_chain_can_opt_in_to_sensor_events(world):
    chain = (
        world.new_body()
        .static()
        .build()
        .add_chain([(-1, 0), (1, 0)], enable_sensor_events=True)
    )
    assert all(segment.enable_sensor_events for segment in chain.segments)
    assert ChainDef([(0, 0), (1, 0)]).enable_sensor_events is False
