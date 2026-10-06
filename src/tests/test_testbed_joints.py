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


def test_a_motor_too_weak_to_hold_the_box_up_lets_it_land_on_the_platform(world):
    test = scenario(world, "Motor Joint")
    # The box weighs 10 N, so this cannot hold it up.
    test.max_velocity_force = 2.0
    run(test, 4.0)

    # Resting on the platform, whose top is y = 0; the box is 0.5 tall.
    assert motor_box(test).position.y == pytest.approx(0.25, abs=0.05)


def test_lowering_the_force_cap_drops_a_box_that_go_stopped(world):
    test = scenario(world, "Motor Joint")
    run(test, 1.0)
    test.enable_motion = False
    run(test, 3.0)
    assert not motor_box(test).awake, "a box held still goes to sleep"

    test.max_velocity_force = 2.0
    run(test, 4.0)

    assert motor_box(test).position.y == pytest.approx(0.25, abs=0.05)


def test_collide_connected_changes_the_cantilever_without_rebuilding_it(world):
    test = scenario(world, "Cantilever")
    run(test, 1.0)
    sagging = test.status()
    assert sagging != "tip y = 0.00"

    test.collide_connected = True

    assert test.status() == sagging, "the beam was rebuilt straight"
    assert all(joint.collide_connected for joint in test.joints)


def test_the_driving_course_ends_in_a_wall(world):
    scenario(world, "Driving")

    # Along the last flat stretch, towards the end of the course at x = 320.
    hits = world.ray_cast((310, 5), (20, 0), first_hit_only=True)

    assert hits, "nothing there: the car would drive off the end"
    assert hits[0].point.x == pytest.approx(320)


def test_the_user_constraint_ropes_pull_but_never_push(world):
    test = scenario(world, "User Constraint")
    tensions = []
    for _ in range(3 * HERTZ):
        run(test, 1 / HERTZ)
        # "rope tension 152.8, 211.1 N"
        numbers = test.status().removeprefix("rope tension ").removesuffix(" N")
        tensions += [float(n) for n in numbers.split(", ")]

    assert max(tensions) > 100, "the ropes should be holding the box up"
    assert min(tensions) >= 0, "a rope pushed the box away"


def test_the_soft_body_springs_retune_a_ring_that_has_settled(world):
    test = scenario(world, "Soft Body")
    # It lands, bounces and wobbles; by 30 s it has fallen asleep.
    run(test, 35.0)
    ring = [joint.body_a for joint in test.joints]
    assert not any(body.awake for body in ring), "a settled ring goes to sleep"

    test.hertz = 2.0

    assert all(body.awake for body in ring), "asleep, it ignores the new spring"


def coasting_speed(world, control=None, value=None):
    """Drive right for 2 s, let go, and report the speed 1.5 s later.

    If a control is given, it is set half a second into the coast.
    """
    test = scenario(world, "Driving")
    test.on_key_down("d")
    run(test, 2.0)
    test.on_key_up("d")
    run(test, 0.5)
    if control is not None:
        setattr(test, control, value)
    run(test, 1.5)
    return test.car.chassis.linear_velocity.x


@pytest.mark.parametrize("control, value", [("hertz", 6.0), ("damping", 1.0)])
def test_the_suspension_sliders_do_not_brake_a_coasting_car(control, value):
    worlds = World(), World()
    try:
        untouched = coasting_speed(worlds[0])
        retuned = coasting_speed(worlds[1], control, value)
    finally:
        for world in worlds:
            world.destroy()

    assert untouched > 5, "the car should be rolling"
    # A stiffer or softer spring changes the ride a little, not the speed.
    assert retuned == pytest.approx(untouched, rel=0.02)


def test_the_torque_slider_does_not_brake_a_coasting_car():
    worlds = World(), World()
    try:
        untouched = coasting_speed(worlds[0])
        retuned = coasting_speed(worlds[1], "torque", 8.0)
    finally:
        for world in worlds:
            world.destroy()

    assert retuned == pytest.approx(untouched, rel=0.02)


def test_the_torque_slider_reaches_a_car_being_driven(world):
    test = scenario(world, "Driving")
    test.on_key_down("d")
    test.torque = 8.0

    assert test.car.rear_axle.max_motor_torque == pytest.approx(8.0)
