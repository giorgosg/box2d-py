"""InvalidInputError as data: which function, which check, which field, what value.

An inspector marks the field that was refused, so the error says which one it
was in Python's own names, read from the same field table definitions use.
The last section walks every check in Box2D's sources, so a Box2D update
cannot leave one of them without an answer.
"""

import inspect
import math
import pathlib
import pickle
import re

import pytest

import box2d
from box2d import (
    BodyDef,
    CircleDef,
    InvalidInputError,
    SurfaceMaterial,
    Vec2,
    World,
)
from box2d._box2d import ffi, lib as raw_lib
from box2d.dataclasses import MassData
from box2d._checked import _on_log, _pending, _raise_pending
from box2d._failed_check import _PARAMETER, _struct_name, describe
from box2d.defdata import _structs

NAN = math.nan


def caught(call, *args, **keywords):
    with pytest.raises(InvalidInputError) as info:
        call(*args, **keywords)
    return info.value


@pytest.fixture
def body(world):
    return world.new_body().dynamic().circle(0.5).build()


@pytest.fixture
def anchor(world):
    return world.add_body()


# -- a definition's field ------------------------------------------------------------


def test_a_field_of_a_body_definition(world):
    error = caught(world.add_body_def, BodyDef(linear_damping=-1))
    assert error.function == "b2CreateBody"
    assert error.condition == (
        "b2IsValidFloat( def->linearDamping ) && def->linearDamping >= 0.0f"
    )
    assert error.field == "linear_damping"
    assert error.value == -1.0


def test_the_value_is_what_was_given_not_its_32_bit_neighbour(world):
    assert caught(world.add_body, linear_damping=-0.1).value == -0.1


def test_a_point_field_comes_back_as_a_point(world):
    error = caught(world.add_body, linear_velocity=(NAN, 1))
    assert error.field == "linear_velocity"
    assert isinstance(error.value, Vec2)
    assert math.isnan(error.value.x) and error.value.y == 1


def test_a_rotation_comes_back_as_an_angle(world):
    error = caught(world.add_body, rotation=NAN)
    assert error.field == "rotation"
    assert math.isnan(error.value)


def test_a_field_named_differently_in_c_uses_the_python_name(world, anchor, body):
    error = caught(world.add_pogo_joint, anchor, body, spring_hertz=NAN)
    assert error.field == "spring_hertz"
    assert "def->hertz" in error.condition
    assert math.isnan(error.value)


def test_a_check_in_a_helper_still_names_the_function_called(body):
    error = caught(body.add_circle, radius=1, density=-1)
    assert error.function == "b2CreateCircleShape"
    assert error.field == "density"
    assert error.value == -1.0
    assert "(in b2CreateShape)" in str(error)


def test_a_world_definition_has_no_table_and_is_still_told():
    error = caught(World, gravity=(NAN, 0))
    assert error.field == "gravity"
    assert math.isnan(error.value.x)


# -- one check over several fields ----------------------------------------------------


@pytest.mark.parametrize("name", ["friction", "restitution", "rolling_resistance"])
def test_a_material_check_finds_the_field(body, name):
    error = caught(body.add_circle, radius=1, **{name: -1})
    assert "b2IsValidMaterial" in error.condition
    assert (error.field, error.value) == (name, -1.0)


def test_a_material_check_on_a_shape(body):
    (shape,) = body.shapes
    error = caught(setattr, shape, "surface_material", SurfaceMaterial(friction=-2))
    assert (error.field, error.value) == ("friction", -2.0)


@pytest.mark.parametrize(
    "keywords, field",
    [
        ({"radius": -1}, "radius"),
        ({"radius": 1, "center": (NAN, 0)}, "center"),
    ],
)
def test_a_circle_check_finds_the_field(body, keywords, field):
    error = caught(body.add_circle, **keywords)
    assert "b2IsValidCircle" in error.condition
    assert error.field == field


def test_a_capsule_uses_the_python_names_of_its_ends(body):
    assert caught(body.add_capsule, (NAN, 0), (1, 0), 0.5).field == "vertex1"
    assert caught(body.add_capsule, (0, 0), (1, 0), -1).field == "radius"


def test_a_segment_uses_the_python_names_of_its_ends(body):
    assert caught(body.add_segment, (0, 0), (NAN, 0)).field == "vertex2"


def test_a_polygon_reports_its_vertices(body):
    error = caught(body.add_box, NAN, 1)
    assert error.field == "vertices"
    assert any(math.isnan(point.x) for point in error.value)


def test_a_new_geometry_is_checked_too(body):
    (shape,) = body.shapes
    with pytest.raises(InvalidInputError) as info:
        shape.geometry = CircleDef(radius=-3)
    assert (info.value.field, info.value.value) == ("radius", -3.0)


def test_a_joint_base_check_finds_the_anchor(world, anchor, body):
    error = caught(world.add_weld_joint, anchor, body, local_anchor_a=(NAN, 0))
    assert "b2IsValidJointDef" in error.condition
    assert error.field == "local_anchor_a"
    assert math.isnan(error.value.x)


def test_a_chain_reports_its_vertices(body):
    points = [(0, 0), (1, 0), (NAN, 1), (3, 3)]
    error = caught(body.add_chain, points)
    assert error.field == "vertices"
    assert len(error.value) == 4


def test_a_chain_material_finds_the_field(body):
    materials = [SurfaceMaterial(), SurfaceMaterial(restitution=-1)]
    error = caught(
        body.add_chain, [(0, 0), (1, 0), (2, 1), (3, 3)], materials=materials[1:]
    )
    assert (error.field, error.value) == ("restitution", -1.0)


# -- a setter's or method's argument --------------------------------------------------


def test_a_property_is_told_by_its_own_name(body):
    error = caught(setattr, body, "linear_damping", -1)
    assert error.function == "b2Body_SetLinearDamping"
    assert (error.field, error.value) == ("linear_damping", -1.0)


def test_a_property_whose_parameter_is_named_otherwise(world, anchor, body):
    joint = world.add_revolute_joint(anchor, body, anchor=(0, 0))
    error = caught(setattr, joint, "max_motor_torque", NAN)
    assert "b2IsValidFloat( torque )" == error.condition
    assert error.field == "max_motor_torque"
    assert math.isnan(error.value)


def test_the_second_of_two_arguments(body):
    error = caught(body.apply_force, (1, 0), (NAN, 0))
    assert error.field == "point"
    assert math.isnan(error.value.x)


def test_the_first_of_two_arguments(body):
    error = caught(body.apply_force, (NAN, 0), (1, 0))
    assert error.field == "force"
    assert error.value.y == 0


def test_a_property_sharing_a_function_with_others(world):
    error = caught(setattr, world, "contact_hertz", NAN)
    assert error.function == "b2World_SetContactTuning"
    assert error.field == "contact_hertz"
    assert caught(setattr, world, "contact_push_speed", NAN).field == (
        "contact_push_speed"
    )


def test_a_frame_comes_back_as_a_transform(world, anchor, body):
    joint = world.add_revolute_joint(anchor, body, anchor=(0, 0))
    error = caught(setattr, joint, "local_anchor_a", (NAN, 0))
    assert error.field == "local_frame_a"
    assert math.isnan(error.value.p.x)


def test_a_position_and_a_rotation(body):
    assert caught(setattr, body, "position", (NAN, 0)).field == "position"
    error = caught(setattr, body, "rotation", NAN)
    assert error.field == "rotation"
    assert math.isnan(error.value)


def test_a_field_of_a_structure_passed_as_a_whole(world, body):
    error = caught(setattr, body, "mass_data", MassData(-1, Vec2(0, 0), 1))
    assert (error.field, error.value) == ("mass", -1.0)
    error = caught(world.explode, (0, 0), -1, 1)
    assert (error.field, error.value) == ("radius", -1.0)


def test_a_method_argument(world):
    error = caught(world.step, NAN, 4)
    assert error.field == "time_step"
    assert math.isnan(error.value)


def test_a_field_worked_out_from_another_is_the_one_that_reached_box2d(body):
    assert caught(body.add_box, 1, 1, offset=(NAN, 0)).field == "vertices"


# -- the error as an object ----------------------------------------------------------


def test_the_message_is_unchanged(body):
    error = caught(setattr, body, "linear_velocity", (NAN, 0))
    assert str(error) == (
        "b2Body_SetLinearVelocity rejected its input: b2IsValidVec2( linearVelocity )"
    )


def test_it_survives_a_pickle(body):
    error = caught(setattr, body, "linear_velocity", (NAN, 0))
    copy = pickle.loads(pickle.dumps(error))
    assert str(copy) == str(error)
    assert (copy.function, copy.condition, copy.field) == (
        error.function,
        error.condition,
        error.field,
    )
    assert math.isnan(copy.value.x)


def test_it_can_be_made_with_just_a_message():
    error = InvalidInputError("no")
    assert (str(error), error.function, error.condition) == ("no", "", "")
    assert error.field is None and error.value is None


def test_a_check_in_no_known_form_is_kept_whole():
    _on_log(ffi.new("char[]", b"invalid input in a new way\n"))
    with pytest.raises(InvalidInputError) as info:
        _raise_pending("b2Something", ())
    assert info.value.function == "b2Something"
    assert info.value.condition == "invalid input in a new way"
    assert info.value.field is None
    assert not _pending.checks


def test_two_failures_together_are_described_by_the_first():
    for text in (b"invalid input: a in b2A\n", b"invalid input: b in b2B\n"):
        _on_log(ffi.new("char[]", text))
    with pytest.raises(InvalidInputError) as info:
        _raise_pending("b2A", ())
    assert info.value.condition == "a"
    assert "a" in str(info.value) and "b2B" in str(info.value)


def test_a_condition_about_nothing_known_has_no_field():
    assert describe("b2Nothing_Do", "true == false", ()) == (None, None)
    assert describe("b2CreateBody", "def->linearDamping", ()) == (None, None)
    world_def = ffi.new("b2WorldDef*", raw_lib.b2DefaultWorldDef())
    assert describe("b2CreateWorld", "def->nosuch", (world_def,)) == (None, None)
    assert describe("b2Body_ApplyForce", "somethingNew > 0", (1,)) == (None, None)
    # An argument the call did not get.
    assert describe("b2Body_ApplyForce", "b2IsValidPos( point )", (1,)) == (None, None)


# -- every check in Box2D --------------------------------------------------------------

SOURCES = pathlib.Path(__file__).parents[2] / "box2d" / "src"
needs_source = pytest.mark.skipif(not SOURCES.is_dir(), reason="needs Box2D's sources")
FUNCTION = re.compile(r"^[A-Za-z_][\w \*]*?\b(\w+)\(([^;{}]*)\)\s*\n?\{", re.M)
CHECK = re.compile(
    r"B2_CHECK_INPUT(?:_RETURN)?\(\s*(.*?)"
    r"(?:,\s*(?:b2_null\w+|\(\w+\)\{ 0 \}))?\s*\);"
)
VALIDATOR = re.compile(r"^(?:static )?bool (b2IsValid\w+)\([^)]*\)\s*\{", re.M)
MEMBER = re.compile(r"\b\w+->(\w+)")

#: One check over several fields, each validator with the definition holding
#: them; nothing is wrong with the zeros and defaults these tests pass, so no
#: field is found.
OVER_SEVERAL = re.compile(
    r"b2IsValid(Material|JointDef|Circle|Capsule|Polygon|Segment)\("
)

#: What each validator looks at, by the definition with those fields.
VALIDATED = {
    "b2IsValidMaterial": box2d.SurfaceMaterial,
    "b2IsValidCircle": box2d.CircleDef,
    "b2IsValidCapsule": box2d.CapsuleDef,
    "b2IsValidSegment": box2d.SegmentDef,
    "b2IsValidPolygon": box2d.PolygonDef,
}

#: Fields validators look at which no definition sets, or which Box2D works
#: out itself: the checks on them cannot fail from Python.
NEVER_SET = {
    "b2IsValidJointDef": {
        "constraintDampingRatio",
        "constraintHertz",
        "drawScale",
        "forceThreshold",
        "torqueThreshold",
    },
    "b2IsValidPolygon": {"centroid", "count", "normals"},
}

#: A pose checked whole, which Python takes as a position and a rotation.
TOLD_NOTHING = {
    ("b2Body_SetTargetTransform", "b2IsValidWorldTransform( target )"),
}

#: Checked functions no wrapper calls.
NOT_BOUND = {
    "b2CreateChainSegmentShape",
    "b2SetLengthUnitsPerMeter",
    "b2Shape_SetChainSegment",
}

JOINT_CREATE = re.compile(r"b2Create(\w+Joint)$")


def sites():
    """Every (function, its parameters, condition) in Box2D's input checks."""
    found = []
    for path in sorted(SOURCES.glob("*.c")):
        text = path.read_text()
        functions = list(FUNCTION.finditer(text))
        for each, function in enumerate(functions):
            end = functions[each + 1].start() if each + 1 < len(functions) else None
            words = [part.split() for part in function[2].split(",") if part.strip()]
            parameters = [word[-1].lstrip("*") for word in words]
            for condition in CHECK.findall(text[function.end() : end]):
                found.append((function[1], parameters, condition))
    return found


def blank(kind, position=0):
    """A C value of a type, distinct from one at another position."""
    if kind.kind == "pointer":
        return ffi.new(kind) if kind.item.kind == "struct" else ffi.NULL
    if kind.kind == "struct":
        made = ffi.new(f"{kind.cname}*")
        if kind.cname == "struct b2Vec2":
            made.x = 1000 + position
        return made[0]
    return 1000 + position if kind.cname != "_Bool" else 0


def blanks(function):
    kinds = ffi.typeof(getattr(raw_lib, function)).args
    return tuple(blank(kind, each) for each, kind in enumerate(kinds))


def definition_of(function):
    """The default definition a create function takes."""
    joint = JOINT_CREATE.match(function)
    name = joint[1] if joint else function.removeprefix("b2Create")
    return ffi.new(f"b2{name}Def*", getattr(raw_lib, f"b2Default{name}Def")())


def python_class(function):
    return getattr(box2d, function[2:].partition("_")[0], None)


def names_of(owner):
    """Every attribute of a class and parameter of its methods."""
    names = set(dir(owner))
    for each in vars(owner).values():
        if inspect.isfunction(each):
            names.update(inspect.signature(each).parameters)
    return names


def in_definitions():
    return [site for site in sites() if "def->" in site[2]]


def in_arguments():
    return [
        site for site in sites() if "def->" not in site[2] and hasattr(raw_lib, site[0])
    ]


@needs_source
def test_the_walk_sees_every_check():
    written = sum(
        len(re.findall(r"^\s*B2_CHECK_INPUT(?:_RETURN)?\(", path.read_text(), re.M))
        for path in SOURCES.glob("*.c")
    )
    assert len(sites()) == written > 0


@needs_source
@pytest.mark.parametrize("function, parameters, condition", in_definitions())
def test_every_definition_check_has_an_answer(function, parameters, condition):
    field, _ = describe(function, condition, (0, definition_of(function)))
    if OVER_SEVERAL.match(condition):
        assert field is None
    elif function == "b2CreateWorld":
        assert field == ("gravity" if "gravity" in condition else None)
    else:
        table = _structs[_struct_name(definition_of(function))]
        assert field in {each.name for each in table.fields()}


@needs_source
@pytest.mark.parametrize("function, parameters, condition", in_arguments())
def test_every_argument_check_has_an_answer(function, parameters, condition):
    field, value = describe(function, condition, blanks(function))
    if (function, condition) in TOLD_NOTHING or OVER_SEVERAL.match(condition):
        assert field is None
        return
    assert isinstance(field, str)
    if function not in NOT_BOUND and python_class(function):
        assert field in names_of(python_class(function))
    # The value must be the argument the check is about, not its neighbour.
    parameter, member = _PARAMETER.search(condition).groups()
    if parameter in parameters and member is None:
        position = parameters.index(parameter)
        expected = blanks(function)[position]
        if isinstance(value, Vec2):
            assert value.x == expected.x
        elif isinstance(expected, (int, float)):
            assert value == expected


@needs_source
@pytest.mark.parametrize(
    "validator, table",
    [("b2IsValidJointDef", box2d.DistanceJointDef), *VALIDATED.items()],
)
def test_every_field_a_validator_looks_at_is_in_a_table(validator, table):
    found = {}
    for path in SOURCES.glob("*.c"):
        text = path.read_text()
        for match in VALIDATOR.finditer(text):
            found.setdefault(match[1], text[match.end() :].partition("\n}")[0])
    names = set(MEMBER.findall(found[validator])) - NEVER_SET.get(validator, set())
    paths = [row.c_name for row in table.fields() if row.c_name]
    missing = {
        name for name in names if not any(name in path.split(".") for path in paths)
    }
    assert not missing
