"""What the Character scenarios do, where a crash test cannot see it.

test_testbed.py and test_testbed_ui.py drive every scenario and every
control, but only check that nothing raises. A character that runs cleanly
and goes the wrong way, or off the end of the world, passes both.
"""

import pytest

from box2d_testbed import tb_character  # noqa: F401  (registers the scenarios)
from testbed_scenarios import run, scenario


def mover(world):
    """The Mover scenario, its character landed on the ground."""
    test = scenario(world, "Character", "Mover")
    run(test, 1.0)
    assert test.on_ground
    return test


@pytest.mark.parametrize("key, direction", [("a", -1), ("d", 1)])
def test_the_mover_walks_with_a_and_d_too(world, key, direction):
    test = mover(world)
    start = test.position

    test.on_key_down(key)
    run(test, 0.5)

    # 8 m/s for half a second, along flat ground either way.
    assert (test.position.x - start.x) * direction == pytest.approx(4.0, abs=0.2)


def test_the_mover_cannot_walk_off_the_left_end(world):
    test = mover(world)

    # Long enough to reach the end at 8 m/s, and stand there.
    test.on_key_down("left")
    run(test, 3.0)

    assert test.on_ground
    assert test.position.x > -20.0
