# tests/test_mover.py
"""Kinematic character movement.

A character controller usually should not be a dynamic body: it wants to stop
dead against a wall rather than bounce, and not be tipped over by the solver.
Box2D 3.2 provides the pieces for doing it by hand, none of which were bound.

Nothing here moves anything. These are queries and geometry: the caller keeps
the character's position.
"""

import math

import pytest

from box2d import CollisionPlane, Vec2, World, clip_vector, solve_planes


@pytest.fixture
def world():
    world = World()
    yield world
    world.destroy()


@pytest.fixture
def room(world):
    """Ground at y=0 and a wall whose inner face is at x=3."""
    ground = world.add_body(position=(0, 0))
    ground.add_box(40, 1)
    wall = world.add_body(position=(4, 3))
    wall.add_box(2, 6)
    return ground, wall


STANDING = ((0, 1.0), (0, 2.0), 0.5)  # a capsule resting on the ground


# --- cast_mover -------------------------------------------------------------


def test_cast_mover_reports_a_clear_path(room, world):
    fraction = world.cast_mover(*STANDING, (0, 10))
    assert fraction == pytest.approx(1.0)


def test_cast_mover_stops_at_an_obstacle(room, world):
    fraction = world.cast_mover(*STANDING, (10, 0))
    assert 0.0 < fraction < 1.0, "the wall is 10 units away at most"


def test_cast_mover_respects_the_filter(room, world):
    from box2d import CollisionFilter

    blocked = world.cast_mover(*STANDING, (10, 0))
    ignored = world.cast_mover(*STANDING, (10, 0), filter=CollisionFilter(mask=0))
    assert blocked < 1.0
    assert ignored == pytest.approx(1.0), "filtering everything out clears the path"


# --- collide_mover ----------------------------------------------------------


def test_collide_mover_finds_the_ground(room, world):
    planes = world.collide_mover(*STANDING)

    assert planes, "a capsule resting on the ground should touch something"
    plane = planes[0]
    assert isinstance(plane, CollisionPlane)
    assert plane.plane.normal.y > 0.9, "the ground's normal points up"
    assert plane.shape is not None, "the plane knows which shape it came from"


def test_collide_mover_finds_nothing_in_open_space(world):
    assert world.collide_mover((0, 50), (0, 51), 0.5) == []


def test_collide_mover_reports_each_surface(room, world):
    """Standing in a corner touches both the floor and the wall."""
    planes = world.collide_mover((2.6, 1.0), (2.6, 2.0), 0.5)
    normals = [plane.plane.normal for plane in planes]
    assert any(n.y > 0.9 for n in normals), "the floor"
    assert any(abs(n.x) > 0.9 for n in normals), "the wall"


# --- solve_planes -----------------------------------------------------------


def test_solve_planes_keeps_movement_along_a_surface(room, world):
    planes = world.collide_mover(*STANDING)
    result = solve_planes((1.0, -1.0), planes)

    assert result.translation.x == pytest.approx(1.0, abs=0.01), "sideways is fine"
    assert result.translation.y > -0.1, "but it cannot sink into the ground"
    assert result.iterations >= 1


def test_solve_planes_allows_movement_away(room, world):
    planes = world.collide_mover(*STANDING)
    result = solve_planes((0.0, 1.0), planes)
    assert result.translation.y == pytest.approx(1.0, abs=0.01)


def test_solve_planes_records_the_push(room, world):
    """clip_vector reads the push, so solve_planes must write it back."""
    planes = world.collide_mover(*STANDING)
    assert all(plane.push == 0.0 for plane in planes)

    solve_planes((0.0, -1.0), planes)
    assert any(plane.push > 0.0 for plane in planes)


def test_solve_planes_with_no_planes_moves_freely():
    result = solve_planes((3.0, -4.0), [])
    assert result.translation == Vec2(3.0, -4.0)


# --- clip_vector ------------------------------------------------------------


def test_clip_vector_removes_motion_into_a_plane(room, world):
    planes = world.collide_mover(*STANDING)
    solve_planes((0.0, -1.0), planes)

    clipped = clip_vector((1.0, -5.0), planes)
    assert clipped.x == pytest.approx(1.0, abs=0.01), "sideways survives"
    assert clipped.y == pytest.approx(0.0, abs=0.01), "downward is removed"


def test_clip_vector_leaves_motion_away_alone(room, world):
    planes = world.collide_mover(*STANDING)
    solve_planes((0.0, -1.0), planes)

    clipped = clip_vector((0.0, 5.0), planes)
    assert clipped.y == pytest.approx(5.0, abs=0.01), "jumping is not clipped"


def test_clip_vector_with_no_planes_is_a_no_op():
    assert clip_vector((1.0, 2.0), []) == Vec2(1.0, 2.0)


def test_clip_vector_skips_planes_that_did_not_push(room, world):
    """Planes with no push are ignored, which is why solve comes first."""
    planes = world.collide_mover(*STANDING)
    # No solve_planes call, so every push is still zero.
    assert clip_vector((1.0, -5.0), planes) == Vec2(1.0, -5.0)


# --- the loop the pieces are for --------------------------------------------


def test_a_character_walks_along_the_ground_and_stops_at_the_wall(world):
    ground = world.add_body(position=(0, 0))
    ground.add_box(40, 1)
    wall = world.add_body(position=(6, 3))
    wall.add_box(2, 6)

    position = Vec2(-5, 1.5)
    velocity = Vec2(0, 0)
    radius, height, dt = 0.4, 0.8, 1 / 60

    for _ in range(400):
        velocity = Vec2(6.0, velocity.y - 30.0 * dt)
        point1 = (position.x, position.y - height / 2)
        point2 = (position.x, position.y + height / 2)
        planes = world.collide_mover(point1, point2, radius)
        position = position + solve_planes(velocity * dt, planes).translation
        velocity = clip_vector(velocity, planes)

    assert position.x == pytest.approx(4.6, abs=0.3), "stopped at the wall face"
    # Ground top is y=0.5 and the capsule reaches 0.8 below its centre.
    assert position.y == pytest.approx(1.3, abs=0.1), "still standing on the ground"
    assert velocity.y == pytest.approx(0.0, abs=0.5), "not accelerating into the floor"
