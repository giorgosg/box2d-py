# tests/test_accessors.py
"""Properties backed by a pair of Box2D functions are declared, not written out.

Around 170 properties were eight near-identical lines each, restating the
coercion and the id lookup every time. Each restatement was a place the rule
could be got wrong, which is how joint anchors ended up rejecting b2Vec2.
"""

import pytest

from box2d import World, DestroyedError, Vec2
from box2d.accessors import B2Accessor, b2_bool, b2_float, b2_value, b2_vector
from box2d.body import Body
from box2d.joint import RevoluteJoint
from box2d.lifetime import IdRef
from box2d.shape import Shape


@pytest.fixture
def world():
    world = World()
    yield world
    world.destroy()


@pytest.fixture
def body(world):
    return world.add_body(body_type="dynamic", position=(1, 2))


@pytest.fixture
def shape(body):
    return body.add_circle(radius=1.0)


# --- the descriptor itself --------------------------------------------------


def test_coercion_happens_on_assignment(shape):
    """b2_float coerces, so an int or a numeric string is accepted."""
    shape.friction = 1
    assert shape.friction == pytest.approx(1.0)
    shape.friction = "0.25"
    assert shape.friction == pytest.approx(0.25)


def test_bool_accessor_coerces(shape):
    shape.enable_hit_events = 1
    assert shape.enable_hit_events is True
    shape.enable_hit_events = 0
    assert shape.enable_hit_events is False


def test_read_only_accessor_rejects_assignment(shape):
    with pytest.raises(AttributeError, match="read-only"):
        shape.is_sensor = True


def test_extra_setter_arguments_are_passed(body):
    """Shape.density's setter takes Box2D's updateBodyMass flag after the value."""
    shape = body.add_box(2, 2)
    before = body.mass
    shape.density = 10.0
    assert shape.density == pytest.approx(10.0)
    assert body.mass > before, "the extra updateBodyMass argument was not passed"


def test_accessors_read_through_the_lifetime_guard(world, shape):
    """The guard is not repeated per accessor; it comes from the IdRef."""
    world.destroy()
    with pytest.raises(DestroyedError):
        shape.friction
    with pytest.raises(DestroyedError):
        shape.friction = 0.5


def test_accessing_on_the_class_returns_the_descriptor():
    assert isinstance(Shape.friction, B2Accessor)
    assert isinstance(Body.angular_velocity, B2Accessor)


def test_a_class_without_an_idref_is_rejected():
    """The id attribute is found automatically, so its absence must be loud."""
    with pytest.raises(TypeError, match="has no IdRef"):

        class Broken:
            value = b2_float(lambda i: 0.0)


def test_idref_is_found_through_the_base_class():
    """Joint subclasses declare accessors but inherit the IdRef from Joint."""
    assert isinstance(RevoluteJoint.motor_speed, B2Accessor)
    assert RevoluteJoint.motor_speed._id == "_joint_id"


def test_vector_accessor_round_trips():
    calls = {}

    class Fake:
        _id = IdRef(lambda raw: True, "fake")
        point = b2_vector(
            lambda i: calls["stored"],
            lambda i, v: calls.__setitem__("stored", v),
            doc="A point.",
        )

    obj = Fake()
    obj._id = object()
    calls["stored"] = Vec2(0, 0).b2Vec2[0]

    obj.point = (3, 4)
    assert obj.point == Vec2(3, 4)
    obj.point = Vec2(5, 6)
    assert obj.point == Vec2(5, 6)


# --- the properties they replaced still behave the same ---------------------


def test_converted_body_properties(body):
    body.angular_velocity = 2.5
    body.linear_damping = 0.75
    body.gravity_scale = 0.5
    body.is_bullet = True

    assert body.angular_velocity == pytest.approx(2.5)
    assert body.linear_damping == pytest.approx(0.75)
    assert body.gravity_scale == pytest.approx(0.5)
    assert body.is_bullet is True


def test_converted_joint_properties(world):
    a = world.add_body(body_type="dynamic", position=(0, 0))
    a.add_circle(radius=1.0)
    b = world.add_body(body_type="dynamic", position=(2, 0))
    b.add_circle(radius=1.0)
    joint = world.add_revolute_joint(a, b, anchor=(1, 0))

    joint.motor_speed = 3.0
    joint.max_motor_torque = 40.0
    joint.motor_enabled = True

    assert joint.motor_speed == pytest.approx(3.0)
    assert joint.max_motor_torque == pytest.approx(40.0)
    assert joint.motor_enabled is True


def test_docstrings_survived_the_conversion():
    """Sphinx documents these, so losing the docs would empty the API reference."""
    for owner, name in (
        (Shape, "friction"),
        (Shape, "density"),
        (Body, "angular_velocity"),
        (RevoluteJoint, "motor_speed"),
    ):
        doc = getattr(owner, name).__doc__
        assert doc and doc.strip(), f"{owner.__name__}.{name} has no docstring"
