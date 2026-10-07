"""What the Stacking scenarios do, where a crash test cannot see it.

test_testbed.py and test_testbed_ui.py drive every scenario and every
control, but only check that nothing raises. A stack that falls over, or a
scene that never shows what its docstring promises, passes both.
"""

import math

import pytest

from box2d_testbed import tb_stacking  # noqa: F401  (registers the scenarios)
from testbed_scenarios import (
    assert_view_takes_in_moving_bodies,
    dynamic_bodies,
    moved_from_start,
    press,
    run,
    scenario,
)


def fire_into_the_vertical_stack(world, bullet):
    """The Vertical Stack, settled, with a ball fired into it and given a
    moment to arrive; and how far each box moved meanwhile."""
    test = scenario(world, "Stacking", "Vertical Stack")
    test.bullet = bullet
    run(test, 2.0)
    boxes = dynamic_bodies(world)
    before = [box.position for box in boxes]

    press(test, "fire")
    run(test, 0.25)

    moved = [(box.position - start).length for box, start in zip(boxes, before)]
    return test, moved


def test_a_ball_that_is_not_a_bullet_passes_every_column_to_the_wall(world):
    test, moved = fire_into_the_vertical_stack(world, bullet=False)

    # The wall is at x = 10, and the ball's radius 0.25.
    assert test.ball.position.x > 9.5
    assert max(moved) < 0.01, "the ball should not have touched a box"


def test_the_bullet_hits_the_first_column(world):
    test, moved = fire_into_the_vertical_stack(world, bullet=True)

    assert test.ball.position.x < 9.0, "the ball reached the wall"
    assert max(moved) > 0.5, "the ball should have knocked boxes about"


@pytest.mark.parametrize("mirror", [False, True], ids=["right", "mirrored"])
def test_every_body_on_the_cliff_goes_over_its_edge_to_the_ground(world, mirror):
    test = scenario(world, "Stacking", "Cliff")
    test.mirror = mirror
    bodies = dynamic_bodies(world)
    start = [body.position.x for body in bodies]
    # The circles, rolling furthest at the slowest, are down a little over
    # 6 s in.
    run(test, 8.0)

    # The ledges' tops are 4 m up or more, and the ground's is at 0.
    heights = [round(body.position.y, 2) for body in bodies]
    assert all(height < 1.0 for height in heights), heights
    # And each went the way it was sent, well past where it started.
    travelled = [body.position.x - x for body, x in zip(bodies, start)]
    sign = -1 if mirror else 1
    assert all(sign * distance > 3.0 for distance in travelled), travelled


@pytest.mark.parametrize(
    "name, settling",
    [
        # Cards pressed into the floor and the flat cards above.
        ("Card House", 0.05),
        # The keystone sinks under the load.
        ("Arch", 0.35),
        # Each box drops 1 cm onto the one below, so the top one 12 cm.
        ("Vertical Stack", 0.2),
    ],
)
def test_the_structure_stands(world, name, settling):
    test = scenario(world, "Stacking", name)

    bodies, moved = moved_from_start(test, 3.0)

    assert max(moved) < settling
    assert not any(body.awake for body in bodies), "it should have come to rest"


def test_the_card_house_view_takes_in_the_tallest_house(world):
    test = scenario(world, "Stacking", "Card House")
    test.rows = type(test).rows.max_value

    assert_view_takes_in_moving_bodies(test)


def test_a_card_house_of_three_rows_stands_too(world):
    test = scenario(world, "Stacking", "Card House")
    test.rows = 3

    bodies, moved = moved_from_start(test, 3.0)

    # Two leaning cards a pair and a flat one between pairs: 6 + 2, 4 + 1, 2.
    assert len(bodies) == 15
    assert max(moved) < 0.05


def test_the_capsules_stack_upright_and_come_to_rest(world):
    test = scenario(world, "Stacking", "Capsule Stack")
    capsules = dynamic_bodies(world)

    run(test, 5.0)

    assert not any(capsule.awake for capsule in capsules)
    assert max(abs(capsule.position.x) for capsule in capsules) < 0.05
    # Twenty capsules half a metre thick put the top one's middle at 9.75 m,
    # less a few millimetres at each contact. One slipping out of the stack
    # would take half a metre off.
    assert capsules[-1].position.y > 9.5


def test_rolling_resistance_reaches_every_capsule(world):
    test = scenario(world, "Stacking", "Capsule Stack")
    test.rolling_resistance = 0.2

    shapes = [shape for body in dynamic_bodies(world) for shape in body.shapes]
    assert len(shapes) == 20
    assert all(shape.rolling_resistance == pytest.approx(0.2) for shape in shapes)


def test_the_confined_circles_come_to_rest_inside_the_box(world):
    test = scenario(world, "Stacking", "Confined")
    circles = dynamic_bodies(world)

    run(test, 3.0)

    assert not any(circle.awake for circle in circles)
    # The walls are capsules of radius 0.5 around x = +-10.5, y = 0 and 20.5.
    assert all(-10 < c.position.x < 10 and 0.5 < c.position.y < 20 for c in circles)


def test_the_dominoes_fall_once_leaning_and_again_flat(world):
    test = scenario(world, "Stacking", "Double Domino")
    first, *_, last = dominoes = dynamic_bodies(world)

    run(test, 5.0)
    # The first rests on the second, about 75 degrees over; the last has not
    # been reached yet.
    assert 1.2 < abs(first.rotation) < 1.45
    assert abs(last.rotation) < 0.01

    run(test, 7.0)
    assert all(abs(abs(d.rotation) - math.pi / 2) < 0.02 for d in dominoes)


def test_the_domino_controls_rebuild_the_row(world):
    test = scenario(world, "Stacking", "Double Domino")
    test.count = 30
    assert len(dynamic_bodies(world)) == 30

    test.nudge = 0.0
    run(test, 3.0)
    assert all(abs(d.rotation) < 0.01 for d in dynamic_bodies(world))


def tilted_column(world, lean):
    """One ten-row column of the Tilted Stack, leaning ``lean`` m a row."""
    test = scenario(world, "Stacking", "Tilted Stack")
    test.columns = 1
    test.lean = lean
    return test, dynamic_bodies(world)[-1]


@pytest.mark.parametrize(
    "lean, falls", [(0.08, False), (0.085, True), (0.09, True), (0.2, True)]
)
def test_a_tilted_column_stands_only_while_it_leans_little_enough(world, lean, falls):
    test, top = tilted_column(world, lean)
    start = top.position

    run(test, 6.0)

    assert ((top.position - start).length > 2.0) is falls
