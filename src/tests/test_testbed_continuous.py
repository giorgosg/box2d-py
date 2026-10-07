"""What the Continuous scenarios do, where a crash test cannot see it.

test_testbed.py and test_testbed_ui.py drive every scenario and every
control, but only check that nothing raises. A scenario that runs cleanly
and shows the wrong thing passes both, which is how Pinball's flippers sat
level until a key had been pressed and let go.
"""

import random

import pytest

from box2d_testbed import tb_continuous  # noqa: F401  (registers the scenarios)
from testbed_scenarios import press, run, scenario


def test_the_pinball_flippers_rest_down_before_any_key_is_pressed(world):
    test = scenario(world, "Continuous", "Pinball")
    run(test, 1.0)

    # Down is the left flipper turned clockwise and the right anticlockwise,
    # each against one of its limits.
    left, right = test.left_joint, test.right_joint
    assert left.angle == pytest.approx(left.lower_limit, abs=0.01)
    assert right.angle == pytest.approx(right.upper_limit, abs=0.01)


def test_a_box_that_skids_off_the_end_of_the_floor_has_not_tunnelled(world):
    # A box spinning as it lands can turn the spin into a skid fast enough to
    # take it off the end of the floor, and then it falls below it.
    random.seed(1)
    test = scenario(world, "Continuous", "Skinny Box")
    through = skidded = 0
    for _ in range(40):
        run(test, 1.0)
        box = test.projectile
        if box.position.y < -1.0:
            if abs(box.position.x) > 10.0:
                skidded += 1
            else:
                through += 1
        press(test, "launch")
    assert skidded > 0, "no box went off the end, so this tested nothing"

    assert test.passed_through == through
