"""What the Stacking scenarios do, where a crash test cannot see it.

test_testbed.py and test_testbed_ui.py drive every scenario and every
control, but only check that nothing raises. A stack that falls over, or a
scene that never shows what its docstring promises, passes both.
"""

from box2d_testbed import tb_stacking  # noqa: F401  (registers the scenarios)
from testbed_scenarios import dynamic_bodies, press, run, scenario


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
