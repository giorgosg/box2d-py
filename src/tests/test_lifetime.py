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
    assert shape.is_valid() is True

    world.destroy()

    assert world.is_valid is False
    assert body.is_valid is False
    assert shape.is_valid() is False


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
