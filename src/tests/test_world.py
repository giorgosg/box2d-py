# tests/test_world.py

import pytest
import box2d
from box2d import World, Vec2

def test_import():
    assert box2d is not None

def test_world_creation():
    world = World()
    assert world is not None
    assert hasattr(world, '_world_id')  # Check internal id exists

def test_gravity():
    world = World()
    world.gravity = (0.0, -10.0)
    assert world.gravity == (0.0, -10.0)

def test_world_step():
    world = World()
    world.step(1.0/60.0, 4)

def invalidgrav():
    world = box2d.World(gravity=-10)

def test_invalid():
    with pytest.raises(Exception):
        invalidgrav()


def test_world_with_custom_gravity():
    gravities = [
        (0.0, 0.0),   # Zero gravity
        (10.0, 0.0),  # Horizontal gravity
        (-5.0, 5.0),  # Diagonal gravity
        (0.0, 98.1),  # Very strong vertical gravity
    ]
    for gx, gy in gravities:
        world = World(gravity=(gx, gy))
        g = world.gravity
        assert pytest.approx(g.x, abs=1e-5) == gx
        assert pytest.approx(g.y, abs=1e-5) == gy

def test_multiple_step_simulation():
    world = World()
    body = (
        world.new_body()
        .dynamic()
        .position(0.0, 10.0)
        .add_box(1.0, 1.0, density=1.0) 
        .build()
    )

    # Simulate for multiple steps
    initial_pos = body.position
    for _ in range(10):
        world.step(1.0/60.0, velocity_iterations=8)

    # Body should have fallen due to gravity
    final_pos = body.position
    assert final_pos.y < initial_pos.y

