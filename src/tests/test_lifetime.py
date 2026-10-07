# tests/test_lifetime.py
"""Using a destroyed Box2D object must raise, not segfault.

Box2D ids name engine-owned storage. Before these guards existed, touching a
body after its world was destroyed took the interpreter down with SIGSEGV
(exit code 139) -- no traceback, no exception, nothing to catch.
"""

import pytest
from box2d import World, DestroyedError


@pytest.fixture
def world():
    return World()


def test_body_after_world_destroy(world):
    body = world.new_body().dynamic().position(1, 2).build()
    world.destroy()

    with pytest.raises(DestroyedError):
        body.position


def test_shape_after_world_destroy(world):
    body = world.new_body().dynamic().build()
    shape = body.add_circle(radius=1.0)
    world.destroy()

    with pytest.raises(DestroyedError):
        shape.density


def test_shape_after_body_destroy(world):
    body = world.new_body().dynamic().build()
    shape = body.add_circle(radius=1.0)
    body.destroy()

    with pytest.raises(DestroyedError):
        shape.density


def test_body_after_own_destroy(world):
    body = world.new_body().dynamic().build()
    body.destroy()

    with pytest.raises(DestroyedError):
        body.position


def test_joint_after_bodies_destroyed(world):
    body_a = world.new_body().dynamic().position(0, 0).build()
    body_a.add_circle(radius=1.0)
    body_b = world.new_body().dynamic().position(1, 0).build()
    body_b.add_circle(radius=1.0)
    joint = world.add_revolute_joint(body_a, body_b, (0, 0), (0, 0))

    body_a.destroy()
    body_b.destroy()

    with pytest.raises(DestroyedError):
        joint.body_a


def _mouse_joint_gone_with_its_body(world):
    body = world.new_body().dynamic().circle(radius=1.0).build()
    joint = world.add_mouse_joint(body, (0, 0))
    body.destroy()
    return joint


def _mouse_joint_gone_with_its_body_then_destroyed(world):
    joint = _mouse_joint_gone_with_its_body(world)
    joint.destroy()  # what tidying up does; it removes the proxy body
    return joint


def _mouse_joint_destroyed(world):
    body = world.new_body().dynamic().circle(radius=1.0).build()
    joint = world.add_mouse_joint(body, (0, 0))
    joint.destroy()
    return joint


@pytest.mark.parametrize(
    "gone",
    [
        _mouse_joint_gone_with_its_body,
        _mouse_joint_gone_with_its_body_then_destroyed,
        _mouse_joint_destroyed,
    ],
)
def test_mouse_joint_target_after_the_joint_is_gone(world, gone):
    """The target lives on a proxy body rather than the joint, so it needs
    the same check as everything else on a joint: it used to return the
    position of a body nothing was joined to, or raise AttributeError once
    destroy() had dropped the proxy."""
    joint = gone(world)

    with pytest.raises(DestroyedError):
        joint.target
    with pytest.raises(DestroyedError):
        joint.target = (1, 1)


def test_world_step_after_destroy(world):
    world.destroy()

    with pytest.raises(DestroyedError):
        world.step(1 / 60, 4)


def test_destroy_is_idempotent(world):
    body = world.new_body().dynamic().build()

    body.destroy()
    body.destroy()  # must not raise

    world.destroy()
    world.destroy()  # must not raise


def test_is_valid_reports_destruction(world):
    body = world.new_body().dynamic().build()
    shape = body.add_circle(radius=1.0)

    assert world.is_valid is True
    assert body.is_valid is True
    assert shape.is_valid is True

    world.destroy()

    assert world.is_valid is False
    assert body.is_valid is False
    assert shape.is_valid is False


def test_live_objects_are_unaffected(world):
    """The guard must not disturb normal use."""
    body = world.new_body().dynamic().position(0, 10).build()
    body.add_circle(radius=0.5)

    for _ in range(10):
        world.step(1 / 60, 4)

    assert body.is_valid is True
    assert body.position.y < 10  # it fell


def test_destroying_one_body_leaves_others_usable(world):
    keep = world.new_body().dynamic().position(0, 0).build()
    drop = world.new_body().dynamic().position(5, 0).build()

    drop.destroy()

    assert keep.is_valid is True
    assert keep.position == (0, 0)
    world.step(1 / 60, 4)


def test_is_valid_is_a_property_everywhere():
    """Shape and Chain had it as a method while the rest had a property.

    Mixing the two up went unnoticed one way round: a method used as
    ``if shape.is_valid:`` is a bound method, always true.
    """
    from box2d import Body, Chain, Contact, Joint, Shape

    for cls in (World, Body, Shape, Chain, Joint, Contact):
        assert isinstance(cls.__dict__.get("is_valid"), property), cls.__name__
