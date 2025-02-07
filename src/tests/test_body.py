# src/tests/test_body.py
import pytest
import box2d
from box2d import World, Vec2
from box2d._box2d import lib
from pytest import approx

def aprx(a):
    return approx(a, rel=1e-3, abs=1e-3)

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
        world.new_body().build()
        .add_box(1.0, 2.0)
    )
    # Basic shape existence check
    assert lib.b2Body_GetShapeCount(body._body_id) == 1

def test_circle_shape():
    world = World()
    body = (
        world.new_body().build()
        .add_circle(1.0)
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
        world.new_body().build()
        .add_box(1.0, 2.0)
        .add_circle(0.5)
    )
    assert lib.b2Body_GetShapeCount(body._body_id) == 2

def test_position_updates():
    world = World()
    body = world.new_body().dynamic().position(1.0, 2.0).build()
    
    # Test initial position
    assert body.position == Vec2(1.0, 2.0)
    
    # Update position
    body.position = (3.0, 4.0)
    assert body.position == Vec2(3.0, 4.0)

def test_zero_velocity():
    world = World()
    body = world.new_body().dynamic().build()
    
    # Set zero velocity
    body.linear_velocity = (0.0, 0.0)
    body.angular_velocity = 0.0
    
    # Verify values
    assert body.linear_velocity == Vec2(0.0, 0.0)
    assert body.angular_velocity == 0.0

def test_body_type():
    world = World()
    
    # Dynamic body
    dynamic_body = world.new_body().dynamic().build()
    assert dynamic_body.type == "dynamic"

    # Static body
    static_body = world.new_body().static().build()
    assert static_body.type == "static"

    # Kinematic body
    kinematic_body = world.new_body().kinematic().build()
    assert kinematic_body.type == "kinematic"

def test_circle_shape_with_custom_center():
    world = World()
    body = (
        world.new_body().build()
        .add_circle(0.5, center=(1.0, 2.0), density=0.5)
    )
    
    # Verify shape count and properties
    assert lib.b2Body_GetShapeCount(body._body_id) == 1

def test_static_body_type():
    world = World()
    body = world.new_body().build()
    assert body.type == "static"

def test_initial_velocity():
    world = World()
    body = world.new_body().dynamic().linear_velocity(2.0, 3.0).angular_velocity(1.5).build()

    # Test initial linear velocity
    assert body.linear_velocity == Vec2(2.0, 3.0)

    # Test initial angular velocity
    assert pytest.approx(body.angular_velocity) == 1.5

def test_sleep_enabled():
    world = World()
    body = world.new_body().dynamic().enable_sleep(False).build()
    
    # Verify sleep is disabled
    assert not body.is_sleep_enabled()

def test_initial_position_reuse():
    world = World()
    body = world.new_body().dynamic().position(1.0, 2.0).build()
    
    # Test initial position
    assert body.position == Vec2(1.0, 2.0)

    # Update position using builder pattern
    body.position = (3.0, 4.0)
    assert body.position == Vec2(3.0, 4.0)

def test_restitution_and_sensors():
    world = World(gravity=(0, -10))
    
    # Create a bouncing ball
    ball = (
        world.new_body()
        .dynamic()
        .position(0, 5)
        .build()
        .add_circle(0.5, restitution=0.8)  # High restitution
    )
    
    # Create static ground
    ground = (
        world.new_body()
        .static()
        .position(0, 0)
        .build()
        .add_box(10, 1)
    )
    
    # Simulate drop
    y_positions = []
    for _ in range(10):
        world.step(1/60, 6)
        y_positions.append(ball.position.y)
    
    # Should bounce higher than 1 unit
    assert max(y_positions) > 1.0

def test_sensor_shape():
    world = World(gravity=(0, 0))
    
    # Create sensor
    sensor_body = (
        world.new_body()
        .static()
        .build()
        .add_box(2, 2, is_sensor=True)
    )
    
    # Create overlapping dynamic body
    dynamic_body = (
        world.new_body()
        .dynamic()
        .position(0, 0)
        .build()
        .add_box(1, 1)
    )
    
    # Sensor should detect overlap but no collision response
    for _ in range(50):
        world.step(1/60, 6)
    assert dynamic_body.position.x == aprx(0)
    assert dynamic_body.position.y == aprx(0)

def test_shape_removal():
    world = World()
    body = world.new_body().build()
    
    # Add two shapes
    body.add_box(1, 1)
    body.add_circle(0.5)
    
    assert lib.b2Body_GetShapeCount(body._body_id) == 2
    
    # Remove one shape
    body.remove_shape(body._shapes[0])
    
    assert lib.b2Body_GetShapeCount(body._body_id) == 1

def test_body_damping():
    world = World()
    
    body = (
        world.new_body()
        .dynamic()
        .linear_damping(0.5)
        .angular_damping(0.5)
        .linear_velocity(10, 0)
        .angular_velocity(5)
        .build()
    )
    
    # Initial velocities
    assert body.linear_velocity.x == 10
    assert body.angular_velocity == 5
    
    # Simulate damping
    for _ in range(50):
        world.step(1/60, 6)
    
    # Velocities should be reduced
    assert body.linear_velocity.x < 9
    assert body.angular_velocity < 4
