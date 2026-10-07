"""What the Bodies scenarios do, where a crash test cannot see it.

test_testbed.py and test_testbed_ui.py drive every scenario and every
control, but only check that nothing raises. A scene that runs cleanly and
shows the wrong thing passes both, which is how one of Body Type's four
boxes of cargo missed the platform it was meant to ride.
"""

from box2d_testbed import tb_bodies  # noqa: F401  (registers the scenarios)
from testbed_scenarios import press, run, scenario


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


def test_a_platform_made_kinematic_while_turning_stops_turning(world):
    test = scenario(world, "Bodies", "Body Type")
    test.body_type = "dynamic"
    run(test, 0.25)
    # Tumbling, as it might be when it lands on the ground or the boxes.
    test.platform.angular_velocity = 1.0

    test.body_type = "kinematic"

    # A kinematic body keeps whatever velocity it has, and nothing slows it.
    turned = test.platform.rotation
    run(test, 2.0)
    assert test.platform.angular_velocity == 0.0
    assert test.platform.rotation == turned


def test_reset_with_dynamic_chosen_drops_the_platform_straight_down(world):
    test = scenario(world, "Bodies", "Body Type")
    test.body_type = "dynamic"

    press(test, "reset")

    assert test.platform.type == "dynamic"
    assert tuple(test.platform.linear_velocity) == (0, 0)
    # Down onto the ground, where landing nudges it a few millimetres.
    run(test, 1.0)
    assert abs(test.platform.position.x) < 0.05
