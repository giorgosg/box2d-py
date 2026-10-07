"""What the Continuous scenarios do, where a crash test cannot see it.

test_testbed.py and test_testbed_ui.py drive every scenario and every
control, but only check that nothing raises. A scenario that runs cleanly
and shows the wrong thing passes both, which is how Pinball's flippers sat
level until a key had been pressed and let go.
"""

import pytest

from box2d_testbed import tb_continuous  # noqa: F401  (registers the scenarios)
from testbed_scenarios import run, scenario


def test_the_pinball_flippers_rest_down_before_any_key_is_pressed(world):
    test = scenario(world, "Continuous", "Pinball")
    run(test, 1.0)

    # Down is the left flipper turned clockwise and the right anticlockwise,
    # each against one of its limits.
    left, right = test.left_joint, test.right_joint
    assert left.angle == pytest.approx(left.lower_limit, abs=0.01)
    assert right.angle == pytest.approx(right.upper_limit, abs=0.01)
