"""The dynamic character controller behind the Dynamic Mover scenario.

Ported from Box2D's samples/dynamic_mover.cpp. Each test builds a small world
of its own, so what is being checked -- a staircase, a slope, a jump -- is not
mixed up with the rest of the scenario's course.
"""

import pytest

from box2d import World
from box2d_testbed.dynamic_mover import DynamicMover
from box2d_testbed.shared import parse_svg_path

STEP = 1 / 60
#: Where the body sits above the ground: the capsule's lower centre is 0.5
#: below the body origin, and the pogo holds that point at its rest length.
STANDING_HEIGHT = 0.5 + 0.9


@pytest.fixture
def world():
    world = World(gravity=(0, -10))
    yield world
    world.destroy()


def flat_ground(world, length=200):
    ground = world.add_body()
    ground.add_segment((-length / 2, 0), (length / 2, 0))
    return ground


def run(world, mover, steps, throttle=0.0):
    for _ in range(steps):
        mover.update(STEP, throttle)
        world.step(STEP, 4)


def test_settles_on_its_pogo_above_the_ground(world):
    flat_ground(world)
    mover = DynamicMover(world, position=(0, 3))
    run(world, mover, 120)

    assert mover.on_ground and mover.walkable
    assert mover.position.y == pytest.approx(STANDING_HEIGHT, abs=0.02)
    assert mover.pogo_length == pytest.approx(0.9, abs=0.02)


def test_runs_at_its_max_speed(world):
    flat_ground(world)
    mover = DynamicMover(world, position=(0, STANDING_HEIGHT), max_speed=6.0)
    run(world, mover, 120, throttle=1.0)
    assert mover.body.linear_velocity.x == pytest.approx(6.0, abs=0.05)


def test_friction_stops_it_when_the_input_is_released(world):
    flat_ground(world)
    mover = DynamicMover(world, position=(0, STANDING_HEIGHT))
    run(world, mover, 60, throttle=1.0)
    run(world, mover, 60)
    assert abs(mover.body.linear_velocity.x) < 0.01


def test_climbs_stairs_without_jumping(world):
    """The point of the pogo: the capsule floats over steps it would catch on."""
    ground = world.add_body()
    ground.add_segment((-10, 0), (2, 0))
    for i in range(8):
        x, y = 2 + i, 0.25 * i
        ground.add_segment((x, y), (x, y + 0.25))
        ground.add_segment((x, y + 0.25), (x + 1, y + 0.25))
    ground.add_segment((10, 2.0), (30, 2.0))

    mover = DynamicMover(world, position=(-4, STANDING_HEIGHT))
    run(world, mover, 240, throttle=1.0)

    assert mover.position.x > 12, "it should have made it up and past the stairs"
    assert mover.position.y == pytest.approx(2.0 + STANDING_HEIGHT, abs=0.05)
    assert not mover.jumping


def test_a_steep_slope_is_not_walkable(world):
    ground = world.add_body()
    ground.add_segment((-10, 0), (0, 0))
    ground.add_segment((0, 0), (5, 10))  # about 63 degrees
    # The slope is at y = 3 under x = 1.5; put the ray's start 0.5 above it.
    mover = DynamicMover(world, position=(1.5, 4.0))
    mover.update(STEP, 0.0)
    assert mover.cast is not None
    assert mover.cast.normal.y < mover.min_ground_normal_y
    assert not mover.walkable


def test_jumps_only_from_the_ground(world):
    flat_ground(world)
    mover = DynamicMover(world, position=(0, STANDING_HEIGHT), jump_speed=7.0)
    run(world, mover, 30)

    assert mover.jump() is True
    assert mover.jumping
    run(world, mover, 5)
    assert mover.jump() is False, "no jumping again in mid air"


def test_a_jump_reaches_the_height_its_speed_gives(world):
    flat_ground(world)
    mover = DynamicMover(
        world, position=(0, STANDING_HEIGHT), jump_speed=7.0, gravity_scale=1.5
    )
    run(world, mover, 30)
    start = mover.position.y

    mover.jump()
    peak = start
    for _ in range(120):
        run(world, mover, 1)
        peak = max(peak, mover.position.y)

    # v^2 / 2g, with the character's own heavier gravity.
    expected = 7.0**2 / (2 * 10 * 1.5)
    assert peak - start == pytest.approx(expected, rel=0.05)
    assert mover.position.y == pytest.approx(STANDING_HEIGHT, abs=0.05), "and lands"


def test_gravity_scale_reaches_the_body(world):
    mover = DynamicMover(world, position=(0, 5))
    mover.gravity_scale = 3.0
    assert mover.body.gravity_scale == pytest.approx(3.0)


def test_destroy_removes_its_bodies(world):
    flat_ground(world)
    before = len(world.bodies)
    mover = DynamicMover(world, position=(0, STANDING_HEIGHT))
    run(world, mover, 10)
    mover.destroy()
    assert len(world.bodies) == before


# --- the SVG paths the course is drawn from ----------------------------------


def test_svg_path_absolute_and_relative_commands():
    points = parse_svg_path("M 0,0 H 10 V -5 L 2,-5 l -1,1 h -1 v 2")
    assert [(p.x, p.y) for p in points] == [
        (0, 0),
        (10, 0),
        (10, 5),
        (2, 5),
        (1, 4),
        (0, 4),
        (0, 2),
    ]


def test_svg_path_repeats_an_implied_command():
    points = parse_svg_path("M 0,0 l 1,0 1,0 1,0")
    assert [p.x for p in points] == [0, 1, 2, 3]


def test_svg_path_offsets_flips_and_scales():
    (point,) = parse_svg_path("M 10,20", offset=(-5, -10), scale=0.5)
    assert (point.x, point.y) == (2.5, -5.0)


def test_svg_path_drops_a_closing_point():
    points = parse_svg_path("M 0,0 H 10 V 10 H 0 V 0")
    assert len(points) == 4
