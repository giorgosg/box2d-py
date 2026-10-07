"""What the Bodies scenarios do, where a crash test cannot see it.

test_testbed.py and test_testbed_ui.py drive every scenario and every
control, but only check that nothing raises. A scene that runs cleanly and
shows the wrong thing passes both, which is how one of Body Type's four
boxes of cargo missed the platform it was meant to ride.
"""

import math

import pytest

from box2d_testbed import tb_bodies  # noqa: F401  (registers the scenarios)
from testbed_scenarios import (
    HERTZ,
    assert_view_takes_in_moving_bodies,
    press,
    run,
    scenario,
)


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


def test_enable_sleep_holds_for_the_scene_reset_builds(world):
    test = scenario(world, "Bodies", "Body Type")
    test.body_type = "static"
    test.enable_sleep = False

    press(test, "reset")
    run(test, 3.0)

    assert all(box.awake for box in test.cargo), "cargo at rest stays awake"
    assert not any(body.enable_sleep for body in [test.platform, *test.cargo])


def test_enable_sleep_lets_cargo_at_rest_sleep_again(world):
    test = scenario(world, "Bodies", "Body Type")
    test.body_type = "static"
    run(test, 3.0)
    assert not any(box.awake for box in test.cargo), "at rest, the cargo sleeps"

    test.enable_sleep = False
    assert all(box.awake for box in test.cargo), "and wakes when it may not"
    run(test, 3.0)
    assert all(box.awake for box in test.cargo)

    test.enable_sleep = True
    run(test, 3.0)
    assert not any(box.awake for box in test.cargo)


def test_every_launch_starts_from_where_the_first_did(world):
    test = scenario(world, "Bodies", "Set Velocity")
    starts = [tuple(box.position) for box in test.boxes]
    assert test.launches == 1

    for launch in range(2, 7):
        # At 12 m/s a launch lands within about three seconds.
        for _ in range(10 * HERTZ):
            run(test, 1 / HERTZ)
            if test.launches == launch:
                break
        assert test.launches == launch, f"launch {launch} never came"
        assert [tuple(box.position) for box in test.boxes] == starts


def test_a_box_off_the_end_of_the_ground_does_not_stop_the_launches(world):
    test = scenario(world, "Bodies", "Set Velocity")
    run(test, 0.5)
    # Past the end of the ground, as a fast or spinning launch can take one.
    test.boxes[-1].position = (45, 5)

    run(test, 10.0)

    assert test.launches > 1


def test_at_the_fastest_speed_the_boxes_go_off_the_end_and_are_launched_again(
    world,
):
    test = scenario(world, "Bodies", "Set Velocity")
    test.speed = type(test).speed.max_value
    test.launch()
    assert test.launches == 2

    lowest = 0.0
    for launch in (3, 4):
        # At 40 m/s a launch is down, or gone, within about eight seconds.
        for _ in range(12 * HERTZ):
            run(test, 1 / HERTZ)
            if test.launches == launch:
                break
            lowest = min([lowest, *(box.position.y for box in test.boxes)])
        assert test.launches == launch, f"launch {launch} never came"

    assert lowest < 0, "the boxes should have gone off the end of the ground"


def test_the_kinematic_platform_patrols_from_end_to_end(world):
    test = scenario(world, "Bodies", "Body Type")

    xs = []
    for _ in range(20 * HERTZ):
        run(test, 1 / HERTZ)
        xs.append(test.platform.position.x)

    # Out to 6 m either side and back, a step past at most, and level.
    limit, step = test.PATROL_LIMIT, test.PATROL_SPEED / HERTZ
    assert limit < max(xs) <= limit + step
    assert -limit - step <= min(xs) < -limit
    assert test.platform.position.y == 5.0
    assert test.platform.rotation == 0.0


def test_a_platform_made_static_stops_where_it_is(world):
    test = scenario(world, "Bodies", "Body Type")
    run(test, 1.0)
    where = test.platform.position

    test.body_type = "static"
    run(test, 2.0)

    assert test.platform.position == where
    assert tuple(test.platform.linear_velocity) == (0, 0)


def test_a_platform_made_dynamic_falls_to_the_ground_with_its_cargo(world):
    test = scenario(world, "Bodies", "Body Type")
    run(test, 1.0)

    test.body_type = "dynamic"
    run(test, 3.0)

    # Resting on the ground, half its 1 m thickness up, and the boxes down
    # with it: on it, or slid off it onto the ground.
    assert abs(test.platform.position.y - 0.5) < 0.05
    assert all(box.position.y < 1.55 for box in test.cargo)


def test_speed_and_spin_take_effect_at_the_next_launch(world):
    test = scenario(world, "Bodies", "Set Velocity")
    test.speed = 8.0
    test.spin = -5.0

    for _ in range(10 * HERTZ):
        run(test, 1 / HERTZ)
        if test.launches == 2:
            break
    assert test.launches == 2

    # Each 5 degrees steeper than the one before, from 30.
    for i, box in enumerate(test.boxes):
        angle = math.radians(30 + 5 * i)
        assert box.linear_velocity.x == pytest.approx(8.0 * math.cos(angle))
        assert box.linear_velocity.y == pytest.approx(8.0 * math.sin(angle))
        assert box.angular_velocity == pytest.approx(-5.0)


@pytest.mark.parametrize("name", ["Body Type", "Set Velocity"])
def test_the_view_takes_in_the_scene(world, name):
    test = scenario(world, "Bodies", name)
    assert_view_takes_in_moving_bodies(test)
