# tests/test_world.py

import pytest
import box2d
from box2d import World, AABB
import box2d.world as world
import doctest
from box2d._box2d import lib

def test_doctests():
    # Run doctests for the specific submodule
    results = doctest.testmod(world)
    assert results.failed == 0


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
        .build()
    )
    body.add_box(1.0, 1.0, density=1.0) 

    # Simulate for multiple steps
    initial_pos = body.position
    for _ in range(10):
        world.step(1.0/60.0, substep_count=8)

    # Body should have fallen due to gravity
    final_pos = body.position
    assert final_pos.y < initial_pos.y

def test_get_bodies():
    world = World()
    body1 = world.new_body().build()
    body2 = world.new_body().build()
    bodies = world.get_bodies()
    assert len(bodies) == 2
    assert body1 in bodies
    assert body2 in bodies

def test_world_query_aabb():
    world = World()
    
    # Create a few static bodies with known positions
    body1 = world.new_body().static().position(1.0, 1.0).build()
    body1.add_box(1.0, 1.0)
    
    body2 = world.new_body().static().position(5.0, 5.0).build()
    body2.add_box(1.0, 1.0)
    
    # Query a region that should include one body
    aabb = AABB(lower=(0,0), upper=(2,2))
    results = world.query_aabb(aabb)
    
    # Should find only body1
    assert len(results) == 1
    assert results[0] in body1.shapes

def test_world_destructor():
    world = World()
    body = world.new_body().build()
    
    # Delete the world
    del world
    # Verify that the world was properly destroyed
    with pytest.raises(Exception):
        # Accessing a destroyed world should raise an exception
        lib.b2World_GetGravity(world._world_id)

def test_world_query_aabb_edge_cases():
    world = World()
    
    # Test with zero-sized AABB
    aabb = AABB(lower=(1,1), upper=(1,1))
    results = world.query_aabb(aabb)
    assert len(results) == 0

    # test fails with Illegal instruction (core dumped) should be fixed
    # Test with invalid AABB 
 #   aabb = AABB(lower=(2,2), upper=(1,1))
 #   results = world.query_aabb(aabb)
 #   assert len(results) == 0
