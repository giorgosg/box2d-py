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

def test_create_multiple_worlds():
    worlds = [World(gravity=(0, -9.81)) for _ in range(5)]
    try:
        for w in worlds:
            # Check the gravity is as set.
            g = w.gravity
            assert g.x == 0.0 and pytest.approx(g.y, abs=1e-5) == -9.81
            # Run a single simulation step
            w.step(1/60)
    finally:
        # Ensure that all worlds are destroyed
        for w in worlds:
            w.destroy()


def test_duplicate_destruction():
    world_instance = World()
    # First destruction
    world_instance.destroy()
    
    # Attempt to destroy the same world again should not raise an error.
    try:
        world_instance.destroy()
    except Exception as e:
        pytest.fail(f"Destroying world twice raised an exception: {e}")


def test_destroy_one_world_does_not_affect_others():
    w1 = World(gravity=(0, -10))
    w2 = World(gravity=(0, -5))
    
    # Destroy the first world
    w1.destroy()
    
    # Verify that w2 still works by checking its gravity vector and stepping the simulation.
    try:
        g2 = w2.gravity
        assert g2.x == 0.0 and pytest.approx(g2.y, abs=1e-5) == -5
        w2.step(1/60)
    except Exception as ex:
        pytest.fail(f"Second world failed after the first was destroyed: {ex}")
    finally:
        w2.destroy()

def test_destroy_world_with_active_body_and_recreate():
    # Create initial world with gravity and an active body.
    world = World(gravity=(0, -9.81))
    # Create a dynamic body starting at (0, 10) with a box shape.
    body = world.new_body().dynamic().position(0, 10).box(1, 1, density=1.0).build()

    # Simulate a few steps to allow gravity to affect the body.
    for _ in range(10):
        world.step(1/60, substep_count=8)
    pos_before_destroy = body.position.y

    # Destroy the world (which has active bodies).
    world.destroy()

    # Create a new world and add a similar dynamic body.
    new_world = World(gravity=(0, -9.81))
    new_body = new_world.new_body().dynamic().position(0, 10).box(1, 1, density=1.0).build()

    # Simulate several steps in the new world.
    for _ in range(10):
        new_world.step(1/60, substep_count=8)
    pos_after = new_body.position.y

    # Under gravity, the new body's y position should decrease.
    assert pos_after < 10
    new_world.destroy()


def test_recreate_multiple_worlds_after_destroying_active_bodies():
    # Create and simulate an initial world with an active body.
    initial_world = World(gravity=(0, -9.81))
    body = initial_world.new_body().dynamic().position(0, 20).box(2, 2, density=1.0).build()
    for _ in range(10):
        initial_world.step(1/60, substep_count=8)
    initial_world.destroy()

    # Define test cases for new worlds with various gravity vectors.
    test_cases = [
        {"gravity": (0, -9.81), "axis": "y", "initial": 10, "check_decrease": True},
        {"gravity": (-9.81, 0), "axis": "x", "initial": 10, "check_decrease": True},
        {"gravity": (9.81, 0), "axis": "x", "initial": 10, "check_decrease": False},
        {"gravity": (0, 9.81), "axis": "y", "initial": 10, "check_decrease": False},
    ]

    for case in test_cases:
        g = case["gravity"]
        axis = case["axis"]
        initial_position = case["initial"]

        new_world = World(gravity=g)
        new_body = new_world.new_body().dynamic().position(0, initial_position).box(1, 1, density=1.0).build()

        # Capture the initial coordinate value based on the specified axis.
        if axis == "y":
            init_val = new_body.position.y
        else:
            init_val = new_body.position.x

        # Simulate multiple steps to amplify the effect of gravity.
        for _ in range(10):
            new_world.step(1/60, substep_count=8)

        if axis == "y":
            final_val = new_body.position.y
        else:
            final_val = new_body.position.x

        # With negative gravity along an axis, expect a decrease; with positive, an increase.
        if case["check_decrease"]:
            assert final_val < init_val, (
                f"For gravity {g}, expected {axis} coordinate to decrease (from {init_val} to {final_val})."
            )
        else:
            assert final_val > init_val, (
                f"For gravity {g}, expected {axis} coordinate to increase (from {init_val} to {final_val})."
            )
        new_world.destroy()