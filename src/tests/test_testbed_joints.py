"""What the Joints scenarios do, where a crash test cannot see it.

test_testbed.py and test_testbed_ui.py drive every scenario and every
control, but only check that nothing raises. A control that runs cleanly and
does the wrong thing passes both, which is how unticking the Motor Joint's
"Go" left its box sailing off the edge of the world.
"""

import pytest

from box2d import World
from box2d_testbed import tb_joints  # noqa: F401  (registers the scenarios)
from box2d_testbed.base_test import BaseTest

HERTZ = 60


@pytest.fixture
def world():
    world = World()
    yield world
    world.destroy()


def scenario(world, name):
    test = BaseTest.registry["Joints"][name](world)
    test.setup()
    return test


def run(test, seconds):
    for _ in range(int(seconds * HERTZ)):
        test.world.step(1 / HERTZ, 4)
        test.after_step(1 / HERTZ)


def motor_box(test):
    return test.motor.body_b


def test_unticking_go_stops_the_motor_joint_box(world):
    test = scenario(world, "Motor Joint")
    run(test, 1.0)
    assert abs(motor_box(test).linear_velocity.x) > 1.0, "it should be moving"

    test.enable_motion = False
    run(test, 1.0)
    stopped_at = motor_box(test).position
    run(test, 2.0)

    assert motor_box(test).linear_velocity.length < 0.01
    assert (motor_box(test).position - stopped_at).length < 0.01


def test_ticking_go_again_restarts_a_box_that_fell_asleep(world):
    test = scenario(world, "Motor Joint")
    run(test, 1.0)
    test.enable_motion = False
    run(test, 3.0)
    assert not motor_box(test).awake, "a box held still goes to sleep"

    start = motor_box(test).position
    test.enable_motion = True
    run(test, 1.0)

    # The path picks up where it stopped: 0.47 m along it in the next second.
    assert (motor_box(test).position - start).length > 0.3
