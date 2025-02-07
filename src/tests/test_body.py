# src/tests/test_body.py
import pytest
import box2d
from box2d import World
from box2d._box2d import lib

def test_basic_body():
    world = World()
    body = world.new_body().build()
    assert body.position == (0, 0)

def test_dynamic_body():
    world = World()
    body = (
        world.new_body()
        .dynamic()
        .position(2.0, 3.0)
        .build()
    )
    assert body.position == (2.0, 3.0)

def test_box_shape():
    world = World()
    body = (
        world.new_body()
        .add_box(1.0, 2.0)
        .build()
    )
    # Basic shape existence check
    assert lib.b2Body_GetShapeCount(body._body_id) == 1

def test_circle_shape():
    world = World()
    body = (
        world.new_body()
        .add_circle(1.0)
        .build()
    )
    # Verify shape count
    assert lib.b2Body_GetShapeCount(body._body_id) == 1

def test_velocity_properties():
    world = World()
    body = world.new_body().dynamic().build()

    # Test linear velocity
    body.linear_velocity = (2.0, 3.0)
    assert body.linear_velocity == (2.0, 3.0)

    # Test angular velocity
    body.angular_velocity = 1.5
    assert pytest.approx(body.angular_velocity) == 1.5

def test_multiple_shapes():
    world = World()
    body = (
        world.new_body()
        .add_box(1.0, 2.0)
        .add_circle(0.5)
        .build()
    )
    assert lib.b2Body_GetShapeCount(body._body_id) == 2
