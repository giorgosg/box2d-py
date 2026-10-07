"""What the Joints scenarios do, where a crash test cannot see it.

test_testbed.py and test_testbed_ui.py drive every scenario and every
control, but only check that nothing raises. A control that runs cleanly and
does the wrong thing passes both, which is how unticking the Motor Joint's
"Go" left its box sailing off the edge of the world.
"""

import pytest

from box2d import World
from box2d_testbed import tb_joints  # noqa: F401  (registers the scenarios)
from testbed_scenarios import HERTZ, run, scenario


def motor_box(test):
    return test.motor.body_b


def test_unticking_go_stops_the_motor_joint_box(world):
    test = scenario(world, "Joints", "Motor Joint")
    run(test, 1.0)
    assert abs(motor_box(test).linear_velocity.x) > 1.0, "it should be moving"

    test.enable_motion = False
    run(test, 1.0)
    stopped_at = motor_box(test).position
    run(test, 2.0)

    assert motor_box(test).linear_velocity.length < 0.01
    assert (motor_box(test).position - stopped_at).length < 0.01


def test_ticking_go_again_restarts_a_box_that_fell_asleep(world):
    test = scenario(world, "Joints", "Motor Joint")
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
    test = scenario(world, "Joints", "Motor Joint")
    # The box weighs 10 N, so this cannot hold it up.
    test.max_velocity_force = 2.0
    run(test, 4.0)

    # Resting on the platform, whose top is y = 0; the box is 0.5 tall.
    assert motor_box(test).position.y == pytest.approx(0.25, abs=0.05)


def test_lowering_the_force_cap_drops_a_box_that_go_stopped(world):
    test = scenario(world, "Joints", "Motor Joint")
    run(test, 1.0)
    test.enable_motion = False
    run(test, 3.0)
    assert not motor_box(test).awake, "a box held still goes to sleep"

    test.max_velocity_force = 2.0
    run(test, 4.0)

    assert motor_box(test).position.y == pytest.approx(0.25, abs=0.05)


def test_collide_connected_changes_the_cantilever_without_rebuilding_it(world):
    test = scenario(world, "Joints", "Cantilever")
    run(test, 1.0)
    sagging = test.tip.position
    assert sagging.y < -1.0, "the beam should have drooped"

    test.collide_connected = True

    # A rebuild would make a new, level beam with its tip back at (7.5, 0).
    assert test.tip.position == sagging, "the beam was rebuilt straight"
    assert all(joint.collide_connected for joint in test.joints)


def test_the_driving_course_ends_in_a_wall(world):
    scenario(world, "Joints", "Driving")

    # Along the last flat stretch, towards the end of the course at x = 320.
    hits = world.ray_cast((310, 5), (20, 0), first_hit_only=True)

    assert hits, "nothing there: the car would drive off the end"
    assert hits[0].point.x == pytest.approx(320)


def test_the_user_constraint_ropes_pull_but_never_push(world):
    test = scenario(world, "Joints", "User Constraint")
    tensions = []
    for _ in range(3 * HERTZ):
        run(test, 1 / HERTZ)
        tensions += test.tension

    assert max(tensions) > 100, "the ropes should be holding the box up"
    assert min(tensions) >= 0, "a rope pushed the box away"


def test_the_soft_body_springs_retune_a_ring_that_has_settled(world):
    test = scenario(world, "Joints", "Soft Body")
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
    test = scenario(world, "Joints", "Driving")
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
    test = scenario(world, "Joints", "Driving")
    test.on_key_down("d")
    test.torque = 8.0

    assert test.car.rear_axle.max_motor_torque == pytest.approx(8.0)


def drive_target(test):
    """The speed and torque the car's motors are set to, front and rear alike."""
    rear, front = test.car.rear_axle, test.car.front_axle
    assert (rear.motor_speed, rear.max_motor_torque) == (
        front.motor_speed,
        front.max_motor_torque,
    )
    return rear.motor_speed, rear.max_motor_torque


def test_the_speed_slider_reaches_a_car_being_driven(world):
    test = scenario(world, "Joints", "Driving")
    test.on_key_down("d")
    test.speed = 50.0

    # Negative turns the wheels clockwise, which drives right.
    assert drive_target(test) == (pytest.approx(-50.0), pytest.approx(test.torque))


def test_letting_go_of_one_of_two_drive_keys_keeps_the_other(world):
    test = scenario(world, "Joints", "Driving")
    test.on_key_down("d")
    test.on_key_down("a")
    assert drive_target(test)[0] == pytest.approx(test.speed), "A, pressed last"

    test.on_key_up("a")

    assert drive_target(test) == (
        pytest.approx(-test.speed),
        pytest.approx(test.torque),
    ), "D is still held, so the car drives right"


def test_braking_while_driving_and_letting_go_of_the_brake(world):
    test = scenario(world, "Joints", "Driving")
    test.on_key_down("d")
    test.on_key_down("s")
    assert drive_target(test) == (0.0, pytest.approx(test.torque)), "braking"

    test.on_key_up("s")
    assert drive_target(test)[0] == pytest.approx(-test.speed), "driving again"

    test.on_key_up("d")
    assert drive_target(test) == (0.0, 0.0), "coasting: no motor, no brake"


@pytest.mark.parametrize(
    "control, value", [("friction", 0.0), ("hertz", 0.0), ("damping", 2.0)]
)
def test_the_ragdoll_sliders_wake_a_figure_that_has_settled(world, control, value):
    test = scenario(world, "Joints", "Ragdoll")
    # It lands by 2 s and is asleep by 5 s.
    run(test, 8.0)
    bones = [bone.body for bone in test.human.bones]
    assert not any(body.awake for body in bones), "a settled figure goes to sleep"

    setattr(test, control, value)

    assert all(body.awake for body in bones), "asleep, it ignores the new joints"
