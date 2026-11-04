"""Definitions as plain data, both ways.

Every definition has a field table next to its dataclass, and works from it:
to_dict/from_dict for JSON-ready data, fields() to describe itself, a repr
that is code, and to_def() on live objects to read one back. These tests hold
each part to every definition, so a field added without a row in its table,
or a kind of value with no way to the dictionary, fails here.
"""

import dataclasses
import json
import math
import pathlib

import pytest

import box2d
from box2d import (
    DEFAULTS_VERSION,
    BodyDef,
    BoxDef,
    CapsuleDef,
    ChainDef,
    CircleDef,
    CollisionFilter,
    DefData,
    DistanceJointDef,
    FilterJointDef,
    MotorJointDef,
    MouseJointDef,
    MoverJointDef,
    PogoJointDef,
    PolygonDef,
    PrismaticJointDef,
    RevoluteJointDef,
    SegmentDef,
    ShapeDef,
    SurfaceMaterial,
    Vec2,
    WeldJointDef,
    WheelJointDef,
    World,
    def_from_dict,
)
from box2d.defdata import _rows

GEOMETRY = [CircleDef, CapsuleDef, SegmentDef, BoxDef, PolygonDef]
JOINTS = [
    FilterJointDef,
    WeldJointDef,
    RevoluteJointDef,
    PrismaticJointDef,
    WheelJointDef,
    DistanceJointDef,
    MotorJointDef,
    MoverJointDef,
    PogoJointDef,
    MouseJointDef,
]
EVERY = [BodyDef, ShapeDef, SurfaceMaterial, ChainDef, *GEOMETRY, *JOINTS]
#: Fields that are not data: the application's own, and a world anchor,
#: which a dictionary holds as the local anchors it stands for.
NOT_DATA = {"user_data", "anchor"}


@pytest.fixture
def scene(world):
    """A world with two bodies to join, and a way to name them in a dict."""
    a = world.add_body(body_type="dynamic")
    b = world.add_body(body_type="dynamic", position=(2, 0))
    names = {id(a): "a", id(b): "b"}
    bodies = {"a": a, "b": b}
    return world, a, b, (lambda body: names[id(body)]), bodies.__getitem__


# -- the table -----------------------------------------------------------------------


@pytest.mark.parametrize("cls", EVERY, ids=lambda cls: cls.__name__)
def test_every_field_has_a_row_in_its_rows(cls):
    declared = {field.name for field in dataclasses.fields(cls)} - NOT_DATA
    if cls is FilterJointDef:
        # It has no geometry, so these do nothing, and it takes them away.
        declared -= {"local_anchor_a", "local_anchor_b", "collide_connected"}
    assert set(_rows(cls)) == declared


@pytest.mark.parametrize("cls", EVERY, ids=lambda cls: cls.__name__)
def test_every_field_is_documented(cls):
    undocumented = [field.name for field in cls.fields() if not field.doc]
    assert not undocumented


def test_fields_describe_name_type_default_unit_and_range():
    rows = {field.name: field for field in BodyDef.fields()}
    damping = rows["linear_damping"]
    assert (damping.type, damping.default, damping.unit) == ("float", 0.0, "1/s")
    assert damping.range == (0.0, math.inf)
    assert "damping" in damping.doc.lower()
    assert rows["position"].type == "vec2" and rows["position"].unit == "m"
    assert rows["type"].default == "static"


def test_a_joint_left_to_its_defaults_says_what_they_are():
    rows = {field.name: field for field in WheelJointDef.fields()}
    # The wheel's suspension is on by default, at 1 Hz (PR #62).
    assert rows["enable_spring"].default is True
    assert rows["spring_hertz"].default == 1.0
    assert rows["spring_damping_ratio"].default == 0.7


def test_a_default_worked_out_when_made_is_none():
    rows = {field.name: field for field in DistanceJointDef.fields()}
    assert rows["rest_length"].default is None


# -- to_dict and from_dict -------------------------------------------------------------


def test_only_what_differs_from_the_defaults_is_written():
    assert BodyDef().to_dict() == {}
    assert BodyDef(type="dynamic", linear_damping=0.5).to_dict() == {
        "type": "dynamic",
        "linear_damping": 0.5,
    }


def test_values_are_json_ready():
    body_def = BodyDef(
        type="kinematic", position=(1, 2), rotation=0.5, name="lift", lock_x=True
    )
    assert body_def.to_dict() == {
        "type": "kinematic",
        "position": [1.0, 2.0],
        "rotation": 0.5,
        "name": "lift",
        "lock_x": True,
    }


@pytest.mark.parametrize("cls", [BodyDef, ShapeDef, SurfaceMaterial])
def test_full_writes_every_field_and_reads_back(cls):
    data = cls().to_dict(full=True)
    assert set(data) == {field.name for field in cls.fields()}
    json.dumps(data, allow_nan=False)
    assert cls.from_dict(data).to_dict() == {}


def test_a_body_round_trips():
    body_def = BodyDef(
        type="dynamic",
        position=(1, 2),
        rotation=0.25,
        linear_velocity=(3, 0),
        gravity_scale=0.5,
        is_bullet=True,
        name="ball",
    )
    assert BodyDef.from_dict(body_def.to_dict()) == body_def


def test_a_shape_dict_is_flat_and_carries_its_kind():
    circle = CircleDef(
        0.5,
        center=(1, 0),
        shape=ShapeDef(
            density=2.0,
            material=SurfaceMaterial(friction=0.1),
            filter=CollisionFilter(0x2, 0x4),
            is_sensor=True,
        ),
    )
    data = circle.to_dict()
    assert data == {
        "kind": "circle",
        "radius": 0.5,
        "center": [1.0, 0.0],
        "material": {"friction": 0.1},
        "density": 2.0,
        "filter": {"category": 2, "mask": 4, "group": 0},
        "is_sensor": True,
    }
    again = def_from_dict(data)
    assert isinstance(again, CircleDef)
    assert again.to_dict() == data


@pytest.mark.parametrize(
    "geometry",
    [
        CircleDef(0.5),
        CapsuleDef((0, 0), (1, 0), 0.2),
        SegmentDef((0, 0), (1, 1)),
        BoxDef(2, 1, radius=0.1, offset=(1, 0), rotation=0.5),
        PolygonDef([(0, 0), (1, 0), (0, 1)], radius=0.05),
        ChainDef([(0, 0), (1, 0), (2, 1)], materials=[SurfaceMaterial(friction=0)]),
        ChainDef([(0, 0), (1, 0), (1, 1)], is_loop=True),
    ],
    ids=lambda geometry: type(geometry).__name__,
)
def test_every_shape_kind_round_trips(geometry):
    data = geometry.to_dict()
    json.dumps(data, allow_nan=False)
    again = def_from_dict(data)
    assert type(again) is type(geometry)
    assert again.to_dict() == data
    assert again.to_dict(full=True) == geometry.to_dict(full=True)


def test_a_chains_straight_ghosts_are_left_out_but_others_are_kept():
    assert "ghost1" not in ChainDef([(0, 0), (1, 0)]).to_dict()
    bent = ChainDef([(0, 0), (1, 0)], ghost1=(-1, -1))
    assert bent.to_dict()["ghost1"] == [-1.0, -1.0]
    assert ChainDef.from_dict(bent.to_dict()).ghost1 == Vec2(-1, -1)


@pytest.mark.parametrize("cls", JOINTS, ids=lambda cls: cls.__name__)
def test_every_joint_kind_round_trips_with_the_callers_body_names(cls, scene):
    world, a, b, name, find = scene
    if cls is MouseJointDef:
        definition = cls(body=b, target=(3, 1), hertz=2.0)
    else:
        definition = cls(body_a=a, body_b=b, collide_connected=True)
    data = definition.to_dict(body_ref=name)
    json.dumps(data, allow_nan=False)
    assert data["kind"] == cls.kind
    again = def_from_dict(data, resolve=find)
    assert type(again) is cls
    assert again.to_dict(body_ref=name) == data
    world.add_joint(again)


def test_a_world_anchor_is_written_as_the_local_anchors(scene):
    world, a, b, name, find = scene
    hinge = RevoluteJointDef(a, b, anchor=(1, 0))
    data = hinge.to_dict(body_ref=name)
    assert "anchor" not in data
    assert data["local_anchor_a"] == [1.0, 0.0]
    assert data["local_anchor_b"] == [-1.0, 0.0]


def test_a_joint_needs_the_callers_names_for_its_bodies(scene):
    world, a, b, name, find = scene
    with pytest.raises(TypeError, match="body_ref"):
        WeldJointDef(a, b).to_dict()
    data = WeldJointDef(a, b).to_dict(body_ref=name)
    with pytest.raises(TypeError, match="resolve"):
        WeldJointDef.from_dict(data)


def test_full_writes_every_joint_field_with_none_for_what_is_worked_out(scene):
    world, a, b, name, find = scene
    data = DistanceJointDef(a, b).to_dict(full=True, body_ref=name)
    assert data["rest_length"] is None
    assert data["enable_spring"] is False
    assert DistanceJointDef.from_dict(data, resolve=find).rest_length is None


# -- strictness ----------------------------------------------------------------------


def test_an_unknown_key_names_the_near_miss():
    with pytest.raises(ValueError, match="did you mean 'position'"):
        BodyDef.from_dict({"positon": [1, 2]})
    with pytest.raises(ValueError, match="did you mean 'density'"):
        def_from_dict({"kind": "circle", "radius": 1, "densty": 2})


def test_a_value_of_the_wrong_kind_is_refused():
    with pytest.raises(TypeError, match="position"):
        BodyDef.from_dict({"position": [1]})
    with pytest.raises(TypeError, match="is_bullet"):
        BodyDef.from_dict({"is_bullet": 1})
    with pytest.raises(TypeError, match="type"):
        BodyDef.from_dict({"type": "wobbly"})
    with pytest.raises(TypeError, match="material.friction"):
        ShapeDef.from_dict({"material": {"friction": "lots"}})


def test_a_kind_must_be_known_and_match():
    with pytest.raises(ValueError, match="did you mean 'circle'"):
        def_from_dict({"kind": "circel", "radius": 1})
    with pytest.raises(ValueError, match="BodyDef.from_dict"):
        def_from_dict({"type": "dynamic"})
    with pytest.raises(ValueError, match="'circle', not a 'box'"):
        CircleDef.from_dict({"kind": "box", "radius": 1})


# -- repr --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "definition",
    [
        BodyDef(),
        BodyDef(type="dynamic", position=(1, 2), rotation=0.5, angular_damping=0.1),
        CircleDef(0.5, shape=ShapeDef(density=3.0, is_sensor=True)),
        BoxDef(1, 2, rotation=0.25),
        PolygonDef([(0, 0), (1, 0), (0, 1)]),
        ChainDef([(0, 0), (1, 0), (2, 1)], is_loop=True),
        ShapeDef(filter=CollisionFilter(0x2), material=SurfaceMaterial(restitution=1)),
    ],
    ids=repr,
)
def test_a_repr_is_code_for_an_equal_definition(definition):
    namespace = vars(box2d)
    assert eval(repr(definition), namespace).to_dict() == definition.to_dict()


def test_a_repr_leaves_out_the_defaults():
    assert repr(BodyDef()) == "BodyDef()"
    assert repr(BodyDef(type="dynamic", position=(1, 2))) == (
        "BodyDef(type='dynamic', position=Vec2(1.0, 2.0))"
    )


# -- reading live objects back -------------------------------------------------------


def test_a_body_reads_back_as_its_definition(world):
    made = BodyDef(
        type="dynamic",
        position=(1, 2),
        rotation=0.5,
        linear_velocity=(0, 3),
        angular_velocity=1.5,
        linear_damping=0.7,
        angular_damping=0.2,
        gravity_scale=0.5,
        sleep_threshold=0.1,
        name="crate",
        enable_sleep=False,
        lock_rotation=True,
        is_bullet=True,
    )
    body = box2d.Body(world, made)
    assert body.to_def().to_dict() == made.to_dict()


def test_a_live_reading_is_as_written_not_as_stored(world):
    body = world.add_body(body_type="dynamic", linear_damping=0.7)
    # Box2D stores 0.699999988079071.
    assert body.to_def().linear_damping == 0.7


@pytest.mark.parametrize(
    "geometry",
    [
        CircleDef(0.5, center=(0.25, 0)),
        CapsuleDef((0, 0), (1, 0), 0.2),
        SegmentDef((0, 0), (1, 1)),
        BoxDef(2, 1, radius=0.1, offset=(1, 0.5), rotation=0.3),
        PolygonDef([(0, 0), (1, 0), (0, 1)], radius=0.05),
        ChainDef([(0, 0), (1, 0), (2, 1)]),
        ChainDef([(0, 0), (1, 0), (1, 1)], is_loop=True),
    ],
    ids=lambda geometry: type(geometry).__name__,
)
def test_a_shape_made_from_a_definition_reads_back_as_it(world, geometry):
    settings = ShapeDef(
        density=2.5,
        material=SurfaceMaterial(friction=0.2, restitution=0.5, user_material=3),
        filter=CollisionFilter(0x4, 0x5, -1),
        enable_contact_events=True,
        enable_sensor_events=True,
    )
    if isinstance(geometry, ChainDef):
        geometry = dataclasses.replace(
            geometry,
            materials=[settings.material],
            filter=settings.filter,
            enable_sensor_events=True,
        )
    else:
        geometry = dataclasses.replace(geometry, shape=settings)
    body = world.add_body(body_type="dynamic")
    made = body.add_shape(geometry)

    assert made.to_def().to_dict() == geometry.to_dict()


def test_a_joint_reads_back_as_its_definition(scene):
    world, a, b, name, find = scene
    made = [
        RevoluteJointDef(
            a,
            b,
            anchor=(1, 0),
            reference_angle=0.3,
            enable_limit=True,
            lower_limit=-0.5,
            upper_limit=0.5,
            spring_hertz=4.0,
        ),
        PrismaticJointDef(a, b, axis=(0, 1), reference_angle=0.2, max_motor_force=9.0),
        WheelJointDef(a, b, axis=(0.6, 0.8), spring_hertz=2.0),
        WeldJointDef(a, b, linear_hertz=3.0, reference_angle=-0.4),
        DistanceJointDef(a, b, rest_length=1.5, enable_spring=True, spring_hertz=5.0),
        MotorJointDef(a, b, linear_velocity=(1, 0), max_velocity_force=20.0),
        MoverJointDef(a, b, linear_velocity=(0, 2), max_velocity_force=(5, 5)),
        PogoJointDef(a, b, rest_length=0.5, impulse=1.0),
        MouseJointDef(b, target=(3, 1), max_force=50.0),
        FilterJointDef(a, b),
    ]
    for definition in made:
        joint = world.add_joint(definition)
        back = joint.to_def()
        assert type(back) is type(definition)
        assert back.to_dict(body_ref=name) == definition.to_dict(body_ref=name), type(
            definition
        ).__name__


def test_what_cannot_be_read_back_is_known():
    """Box2D keeps no way to read these, so to_def gives their defaults."""
    unreadable = {
        cls.__name__: sorted(f.name for f in cls.fields() if not f.readable)
        for cls in EVERY
        if any(not f.readable for f in cls.fields())
    }
    assert unreadable == {
        "BodyDef": ["allow_fast_rotation"],
        "ShapeDef": [
            "enable_custom_filtering",
            "invoke_contact_creation",
            "update_body_mass",
        ],
        "PolygonDef": ["offset", "rotation"],
        "PogoJointDef": [
            "max_compression_force",
            "max_tension_force",
            "normal",
            "velocity",
        ],
    }


def test_a_chain_segment_points_to_its_chain(world):
    chain = world.add_body().add_chain([(0, 0), (1, 0), (2, 1)])
    with pytest.raises(TypeError, match="parent_chain"):
        chain.segments[0].to_def()


def test_a_mapped_joint_class_reads_back_as_its_kind():
    class Hinge(box2d.RevoluteJoint):
        pass

    world = World(classes={box2d.RevoluteJoint: Hinge})
    try:
        a, b = world.add_body(), world.add_body(body_type="dynamic", position=(1, 0))
        assert type(world.add_revolute_joint(a, b).to_def()) is RevoluteJointDef
    finally:
        world.destroy()


# -- the defaults ------------------------------------------------------------------

SNAPSHOT = pathlib.Path(__file__).parent / "data" / f"defaults-{DEFAULTS_VERSION}.json"


def every_default():
    return {cls.__name__: {f.name: f.default for f in cls.fields()} for cls in EVERY}


def test_the_defaults_are_the_set_defaults_version_names():
    """A dictionary leaves out defaults, so changing one changes what every
    file written before means. When this fails because a default changed on
    purpose, bump DEFAULTS_VERSION and write the new set's snapshot with
    ``python src/tests/test_defdata.py``.
    """
    assert json.loads(SNAPSHOT.read_text()) == every_default()


@pytest.mark.parametrize("cls", EVERY, ids=lambda cls: cls.__name__)
def test_every_c_name_is_a_field_of_box2ds_structure(cls):
    from box2d._box2d import ffi

    if cls._c_struct is None:
        return
    for field in cls.fields():
        if field.c_name is None:
            continue
        ctype = ffi.typeof(cls._c_struct)
        for part in field.c_name.split("."):
            ctype = dict(ctype.fields)[part].type


# -- what review found -----------------------------------------------------------


def test_a_definition_read_back_equals_itself_through_data_and_code(world):
    body = world.add_body(body_type="dynamic", position=(1, 2), linear_damping=0.7)
    shape = body.add_circle(1, friction=0.3, filter=CollisionFilter(0x2))
    for definition in (body.to_def(), shape.to_def()):
        assert type(definition).from_dict(definition.to_dict()) == definition
        assert eval(repr(definition), vars(box2d)) == definition


def test_a_field_left_out_equals_its_default():
    assert ShapeDef() == ShapeDef(filter=CollisionFilter())
    assert BoxDef(1, 1) == BoxDef(1, 1, rotation=0.0)
    assert CircleDef(1) == CircleDef(1, shape=ShapeDef())
    assert CircleDef(1) != CircleDef(1, shape=ShapeDef(density=2.0))
    assert ShapeDef(user_data=1) != ShapeDef(user_data=2)


def test_an_angle_is_written_as_it_was_given():
    assert BodyDef(rotation=0.559).to_dict() == {"rotation": 0.559}
    assert BodyDef(rotation=-0.692).to_dict() == {"rotation": -0.692}


def test_a_static_or_disabled_body_reads_back_as_made_awake(world):
    assert world.add_body().to_def().to_dict() == {}
    assert "is_awake" not in world.add_body(is_enabled=False).to_def().to_dict()
    sleeping = world.add_body(body_type="dynamic", is_awake=False)
    assert sleeping.to_def().to_dict()["is_awake"] is False


def test_a_polygon_without_rounding_writes_no_radius(world):
    body = world.add_body()
    assert "radius" not in body.add_polygon([(0, 0), (1, 0), (0, 1)]).to_def().to_dict()


@pytest.mark.parametrize(
    "cls, data",
    [
        (BodyDef, {"linear_damping": None}),
        (BoxDef, {"width": None, "height": 1}),
        (WeldJointDef, {"body_a": None, "body_b": None}),
    ],
    ids=["float", "required", "body"],
)
def test_none_is_refused_where_a_field_has_a_default_or_must_be_given(cls, data):
    with pytest.raises(TypeError, match="cannot be None"):
        cls.from_dict(data, resolve=str)


def test_what_is_written_is_plain_python():
    data = BodyDef(is_bullet=1, name="x").to_dict()
    assert data["is_bullet"] is True


def test_changing_a_dictionary_cannot_change_the_defaults():
    data = ShapeDef().to_dict(full=True)
    data["filter"]["mask"] = 1
    {f.name: f for f in ShapeDef.fields()}["filter"].default["mask"] = 1
    assert ShapeDef().to_dict(full=True)["filter"]["mask"] == CollisionFilter.ALL


def test_a_definition_of_ones_own_with_a_kind_harms_nothing():
    @dataclasses.dataclass(repr=False, eq=False)
    class Spring(CircleDef):
        kind = "test-spring"

    assert isinstance(def_from_dict({"kind": "circle", "radius": 1}), CircleDef)


def test_a_box_that_is_no_longer_a_rectangle_reads_back_as_a_polygon(world):
    box = world.add_body().add_box(2, 1)
    box.geometry = PolygonDef([(0, 0), (2, 0), (1.5, 1), (0.5, 1)])
    assert isinstance(box.to_def(), PolygonDef)
    box.geometry = PolygonDef([(0, 0), (2, 0), (1, 1)])
    assert isinstance(box.to_def(), PolygonDef)


def test_a_repr_never_raises(world):
    a, b = world.add_body(), world.add_body()
    both = WeldJointDef(a, b, anchor=(0, 0), local_anchor_a=(1, 0))
    assert "anchor=" in repr(both)
    a.destroy()
    assert "WeldJointDef" in repr(WeldJointDef(a, b, anchor=(0, 0)))
    assert "type=3" in repr(BodyDef(type=3))
    named = BodyDef()
    named.type = "dynamic"
    assert "type='dynamic'" in repr(named)


def test_a_subclass_with_fields_of_its_own_still_works(world):
    @dataclasses.dataclass(repr=False, eq=False)
    class Tagged(WeldJointDef):
        tag: str = "x"

    a, b = world.add_body(), world.add_body()
    definition = Tagged(a, b, tag="y")
    assert "tag='y'" in repr(definition)
    assert definition != Tagged(a, b, tag="z")
    assert "tag" not in definition.to_dict(body_ref=str)


def test_add_shape_refuses_what_is_not_a_shape_definition(world):
    body = world.add_body()
    for wrong in (ShapeDef(), 42):
        with pytest.raises(TypeError, match="not a shape or chain"):
            body.add_shape(wrong)


def test_a_body_definition_makes_a_body_the_world_reports():
    class Ball(box2d.Body):
        pass

    seen = []

    class Game(World):
        def object_created(self, obj):
            seen.append(obj)

    world = Game(classes={box2d.Body: Ball})
    try:
        body = world.add_body_def(BodyDef(type="dynamic"))
        assert type(body) is Ball and seen == [body]
    finally:
        world.destroy()


def test_def_data_is_shared_by_every_definition():
    assert all(issubclass(cls, DefData) for cls in EVERY)


if __name__ == "__main__":
    if SNAPSHOT.exists():
        raise SystemExit(f"{SNAPSHOT} exists: bump DEFAULTS_VERSION first")
    SNAPSHOT.write_text(json.dumps(every_default(), indent=2) + "\n")
    print(f"wrote {SNAPSHOT}")
