"""Box2D's input checks, raised as exceptions.

In a release build Box2D handles a failed check by logging a line and
returning early, so a bad setter did nothing and a bad create returned a null
id that only failed later, somewhere else. These check that the failure is now
raised by the call that caused it, names the Box2D function, and leaves the
world as it was.
"""

import logging
import math
import pathlib
import re
import types

import pytest

import box2d
from box2d import World, InvalidInputError
from box2d._box2d import ffi, lib as raw_lib
from box2d._checked import _on_log, is_checked, lib

NAN = math.nan


@pytest.fixture
def world():
    world = World()
    yield world
    world.destroy()


@pytest.fixture
def body(world):
    body = world.add_body(body_type="dynamic")
    body.add_circle(radius=0.5)
    return body


def test_is_exported_and_is_a_value_error():
    assert box2d.InvalidInputError is InvalidInputError
    assert issubclass(InvalidInputError, ValueError)


# --- create functions -------------------------------------------------------


def test_a_bad_body_raises_instead_of_returning_a_null_id(world):
    before = len(world.bodies)
    with pytest.raises(InvalidInputError, match="b2CreateBody"):
        world.add_body(body_type="dynamic", position=(NAN, 0))
    assert len(world.bodies) == before, "nothing half-made is left behind"


def test_a_bad_joint_raises_where_it_is_made(world, body):
    """This used to surface as a DestroyedError from the joint's constructor."""
    anchor = world.add_body()
    with pytest.raises(InvalidInputError, match="b2CreatePogoJoint"):
        world.add_pogo_joint(anchor, body, rest_length=-1)


def test_a_bad_shape_raises(body):
    with pytest.raises(InvalidInputError, match="b2CreateCircleShape"):
        body.add_circle(radius=0.5, density=-1)


# --- setters ----------------------------------------------------------------


def test_a_rejected_setter_raises_and_keeps_the_old_value(body):
    body.linear_damping = 0.25
    with pytest.raises(InvalidInputError, match="b2Body_SetLinearDamping"):
        body.linear_damping = -1
    assert body.linear_damping == pytest.approx(0.25)


def test_world_settings_are_checked(world):
    with pytest.raises(InvalidInputError, match="b2World_SetGravity"):
        world.gravity = (0, NAN)
    assert world.gravity == (0, -10)


def test_the_message_names_the_failed_check(body):
    with pytest.raises(InvalidInputError) as caught:
        body.angular_velocity = NAN
    assert "b2Body_SetAngularVelocity rejected its input" in str(caught.value)
    assert "b2IsValidFloat" in str(caught.value)


def test_a_good_call_after_a_bad_one_works(body):
    with pytest.raises(InvalidInputError):
        body.linear_damping = -1
    body.linear_damping = 0.5
    assert body.linear_damping == pytest.approx(0.5)


# --- other log messages -----------------------------------------------------


def test_other_box2d_messages_go_to_the_box2d_logger(caplog):
    with caplog.at_level(logging.WARNING, logger="box2d"):
        _on_log(ffi.new("char[]", b"unstable: wheel\n"))
    assert caplog.records[-1].name == "box2d"
    assert caplog.records[-1].getMessage() == "unstable: wheel"


# --- which functions are checked -------------------------------------------


def test_getters_and_validity_checks_stay_unwrapped():
    """They contain no checks and are the hot path, so they pay nothing."""
    for name in ("b2Body_GetPosition", "b2Body_IsValid", "b2World_IsValid"):
        assert not is_checked(name)
        assert isinstance(getattr(lib, name), types.BuiltinFunctionType)


def test_constants_and_function_pointers_pass_through():
    assert lib.b2_dynamicBody == raw_lib.b2_dynamicBody
    assert type(lib.b2Vec2_zero) is type(raw_lib.b2Vec2_zero)


BOX2D_SOURCE = pathlib.Path(__file__).parents[2] / "box2d" / "src"


def braced_body(text, start):
    """The text from ``start``, just inside an opening brace, to its match."""
    depth, end = 1, start
    while depth and end < len(text):
        depth += {"{": 1, "}": -1}.get(text[end], 0)
        end += 1
    return text[start:end]


def functions_with_input_checks():
    """Every non-static Box2D function whose body contains an input check."""
    signature = re.compile(
        r"^(?!static)[A-Za-z_][\w \*]*?\b(b2\w+)\s*\([^;{]*\)\s*\n\{", re.M
    )
    names = set()
    for path in BOX2D_SOURCE.glob("*.c"):
        text = path.read_text()
        for match in signature.finditer(text):
            if "B2_CHECK_INPUT" in braced_body(text, match.end()):
                names.add(match.group(1))
    return names


@pytest.mark.skipif(not BOX2D_SOURCE.is_dir(), reason="needs the Box2D source tree")
def test_every_function_with_an_input_check_is_wrapped():
    """Fails when a Box2D update adds a check to a function the exclusion
    pattern skips, which would otherwise go back to failing silently."""
    names = functions_with_input_checks()
    assert len(names) > 50, "the source scan found too little to be working"
    unwrapped = sorted(name for name in names if not is_checked(name))
    assert not unwrapped, f"checked in C but not in Python: {unwrapped}"


#: b2IsValidPolygon as PolygonDef.is_valid's _is_valid_polygon follows it.
#: Box2D keeps it static, so the Python side is a copy that an upgrade could
#: leave behind.
B2_IS_VALID_POLYGON = """
    if ( polygon->count < 1 || polygon->count > B2_MAX_POLYGON_VERTICES )
    {
        return false;
    }

    if ( b2IsValidFloat( polygon->radius ) == false || polygon->radius < 0.0f )
    {
        return false;
    }

    if ( b2IsValidVec2( polygon->centroid ) == false )
    {
        return false;
    }

    for ( int i = 0; i < polygon->count; ++i )
    {
        if ( b2IsValidVec2( polygon->vertices[i] ) == false
            || b2IsValidVec2( polygon->normals[i] ) == false )
        {
            return false;
        }
    }

    return true;
}
"""


@pytest.mark.skipif(not BOX2D_SOURCE.is_dir(), reason="needs the Box2D source tree")
def test_polygon_validity_still_matches_box2d():
    """Fails when a Box2D update changes the polygon check is_valid copies."""
    text = (BOX2D_SOURCE / "shape.c").read_text()
    match = re.search(r"static bool b2IsValidPolygon\([^)]*\)\s*\{", text)
    assert match, "b2IsValidPolygon is gone from shape.c"
    body = braced_body(text, match.end())
    assert body.split() == B2_IS_VALID_POLYGON.split(), (
        "b2IsValidPolygon changed: update _is_valid_polygon in "
        "box2d/shapedef.py to match, then the copy here"
    )
