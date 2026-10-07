"""What the Bodies scenarios do, where a crash test cannot see it.

test_testbed.py and test_testbed_ui.py drive every scenario and every
control, but only check that nothing raises. A scene that runs cleanly and
shows the wrong thing passes both, which is how one of Body Type's four
boxes of cargo missed the platform it was meant to ride.
"""

from box2d_testbed import tb_bodies  # noqa: F401  (registers the scenarios)
from testbed_scenarios import run, scenario


def test_all_the_cargo_lands_on_a_static_platform(world):
    test = scenario(world, "Bodies", "Body Type")
    test.body_type = "static"

    run(test, 3.0)

    # The platform is 1 m thick and the boxes 1 m square, so a box resting
    # on it has its middle a metre above the platform's.
    platform = test.platform.position
    heights = [box.position.y - platform.y for box in test.cargo]
    assert all(abs(height - 1.0) < 0.05 for height in heights), heights


def test_the_patrolling_platform_keeps_all_its_cargo(world):
    test = scenario(world, "Bodies", "Body Type")
    assert test.body_type == "kinematic"

    # Long enough to turn round at either end several times.
    run(test, 30.0)

    platform = test.platform.position
    heights = [box.position.y - platform.y for box in test.cargo]
    assert all(abs(height - 1.0) < 0.05 for height in heights), heights
