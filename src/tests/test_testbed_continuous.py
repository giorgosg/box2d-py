"""What the Continuous scenarios do, where a crash test cannot see it.

test_testbed.py and test_testbed_ui.py drive every scenario and every
control, but only check that nothing raises. A scenario that runs cleanly
and shows the wrong thing passes both, which is how Pinball's flippers sat
level until a key had been pressed and let go.
"""

import random

import pytest

from box2d import Capsule
from box2d_testbed.tb_continuous import SkinnyBox
from testbed_scenarios import HERTZ, press, run, scenario


def test_the_pinball_flippers_rest_down_before_any_key_is_pressed(world):
    test = scenario(world, "Continuous", "Pinball")
    run(test, 1.0)

    # Down is the left flipper turned clockwise and the right anticlockwise,
    # each against one of its limits.
    left, right = test.left_joint, test.right_joint
    assert left.angle == pytest.approx(left.lower_limit, abs=0.01)
    assert right.angle == pytest.approx(right.upper_limit, abs=0.01)


@pytest.mark.usefixtures("random_left_as_it_was")
def test_a_box_that_skids_off_the_end_of_the_floor_has_not_tunnelled(world):
    # A box spinning as it lands can turn the spin into a skid fast enough to
    # take it off the end of the floor, and then it falls below it.
    random.seed(1)
    test = scenario(world, "Continuous", "Skinny Box")
    through = skidded = 0
    for _ in range(40):
        run(test, 1.0)
        projectile = test.projectile
        if projectile.position.y < -1.0:
            if abs(projectile.position.x) > SkinnyBox.FLOOR_HALF_WIDTH:
                skidded += 1
            else:
                through += 1
        press(test, "launch")
    assert skidded > 0, "no box went off the end, so this tested nothing"

    assert test.passed_through == through


def test_each_arrow_key_works_its_own_flipper(world):
    test = scenario(world, "Continuous", "Pinball")
    left, right = test.left_joint, test.right_joint
    run(test, 0.5)

    test.on_key_down("left")
    run(test, 0.25)
    assert left.angle == pytest.approx(left.upper_limit, abs=0.01), "left is up"
    assert right.angle == pytest.approx(right.upper_limit, abs=0.01), "right rests"

    test.on_key_up("left")
    test.on_key_down("right")
    run(test, 0.25)
    assert left.angle == pytest.approx(left.lower_limit, abs=0.01), "left rests"
    assert right.angle == pytest.approx(right.lower_limit, abs=0.01), "right is up"


def test_flipper_torque_reaches_both_flippers(world):
    test = scenario(world, "Continuous", "Pinball")

    test.flipper_torque = 3000.0

    assert test.left_joint.max_motor_torque == pytest.approx(3000.0)
    assert test.right_joint.max_motor_torque == pytest.approx(3000.0)


def test_a_new_ball_speed_serves_a_ball_at_that_speed(world):
    test = scenario(world, "Continuous", "Pinball")
    run(test, 1.0)
    first = test.ball

    test.ball_speed = 40.0

    assert not first.is_valid, "the old ball should be gone"
    assert test.ball.linear_velocity.y == pytest.approx(-40.0)


@pytest.mark.usefixtures("random_left_as_it_was")
def test_with_continuous_collision_off_every_box_goes_through_the_floor(world):
    random.seed(1)
    test = scenario(world, "Continuous", "Skinny Box")
    test.continuous = False
    for _ in range(5):
        run(test, 1.0)
        assert test.projectile.position.y < -10.0
        press(test, "launch")

    assert not world.enable_continuous
    # The first box, dropped with continuous collision on, is not counted.
    assert test.passed_through == 5


def test_with_continuous_collision_on_a_box_without_spin_lands(world):
    test = scenario(world, "Continuous", "Skinny Box")
    test.spin = False
    for capsule in (False, True):
        test.capsule = capsule
        # It lands on its end and topples over.
        run(test, 3.0)

        box = test.projectile
        assert box.linear_velocity.length < 0.1, "it should have come to rest"
        assert box.position.y > 0.0
    assert isinstance(box.shapes[0], Capsule)
    assert test.passed_through == 0


def test_speed_and_spin_set_the_next_box_going(world):
    test = scenario(world, "Continuous", "Skinny Box")

    test.speed = 100.0
    assert test.projectile.linear_velocity.y == pytest.approx(-100.0)

    test.spin = False
    assert test.projectile.angular_velocity == 0.0


def test_the_ragdolls_stay_in_the_bouncy_box(world):
    test = scenario(world, "Continuous", "Bounce Humans")
    for _ in range(20):
        run(test, 1.0)
        bones = [bone.body for human in test.humans for bone in human.bones]
        # The walls are segments at +-10.
        assert all(abs(b.position.x) < 10 and abs(b.position.y) < 10 for b in bones)

    assert len(test.humans) == 5
    assert max(b.linear_velocity.length for b in bones) > 5.0, "they should fly"


def test_the_fastest_speed_the_slider_allows_is_the_speed_the_box_falls(world):
    test = scenario(world, "Continuous", "Skinny Box")
    fastest = SkinnyBox.speed.max_value

    test.speed = fastest
    run(test, 1 / HERTZ)

    # Still in the air: a step at 400 m/s takes it from 8 m to 1.3 m.
    assert test.projectile.position.y > 1.0
    assert test.projectile.linear_velocity.y == pytest.approx(-fastest, rel=1e-3)
