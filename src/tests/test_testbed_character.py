"""What the Character scenarios do, where a crash test cannot see it.

test_testbed.py and test_testbed_ui.py drive every scenario and every
control, but only check that nothing raises. A character that runs cleanly
and goes the wrong way, or off the end of the world, passes both.
"""

import pytest

from box2d import Vec2
from box2d_testbed.tb_character import Mover
from box2d_testbed.testbed_state import state
from testbed_scenarios import HERTZ, press, run, scenario


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
    run(test, 0.25)

    # 8 m/s for a quarter of a second, along flat ground either way.
    assert (test.position.x - start.x) * direction == pytest.approx(2.0, abs=0.1)


def test_the_mover_cannot_walk_off_the_left_end(world):
    test = mover(world)

    # Long enough to reach the end at 8 m/s, and stand there.
    test.on_key_down("left")
    run(test, 3.0)

    assert test.on_ground
    assert test.position.x > -20.0


def test_the_mover_stands_still_and_level_against_the_right_wall(world):
    test = mover(world)

    # Over the ledge, which is in the way, and on across the ramp.
    test.on_key_down("right")
    run(test, 0.25)
    test.on_key_down("space")
    run(test, 4.0)

    assert test.position.x == pytest.approx(8.5 - Mover.RADIUS, abs=0.01)
    assert test.on_ground
    assert test.velocity.length < 0.01, "pressed against the wall, it stands still"
    assert test.position.y == pytest.approx(0.8, abs=0.01), "on the ground, not in it"


def test_the_mover_can_jump_up_onto_the_ledge(world):
    test = mover(world)

    # Walk right towards the ledge, jump, and keep going.
    test.on_key_down("right")
    run(test, 0.25)
    test.on_key_down("space")
    run(test, 0.5)
    test.on_key_up("right")
    run(test, 0.5)

    assert test.on_ground
    assert -11.0 < test.position.x < -5.0, "over the ledge"
    assert test.position.y > 1.5, "on top of it, not under it"


def in_view(test, body):
    """Whether the whole of a body is inside the scenario's opening view."""
    center, zoom = test.view()
    return all(
        center.x - 1.6 * zoom <= shape.aabb.lower.x
        and shape.aabb.upper.x <= center.x + 1.6 * zoom
        and center.y - zoom <= shape.aabb.lower.y
        and shape.aabb.upper.y <= center.y + zoom
        for shape in body.shapes
    )


def test_the_dynamic_mover_opens_on_its_character(world):
    test = scenario(world, "Character", "Dynamic Mover")
    assert in_view(test, test.mover.body)


def test_a_reset_dynamic_mover_starts_with_the_sliders_settings(world):
    test = scenario(world, "Character", "Dynamic Mover")
    test.gravity_scale = 3.0
    test.jump_speed = 12.0

    press(test, "reset")

    # Before the first step: it falls from the start at the gravity chosen.
    assert test.mover.gravity_scale == pytest.approx(3.0)
    assert test.mover.jump_speed == pytest.approx(12.0)


# --- what already worked -----------------------------------------------------


def test_the_mover_view_takes_in_the_whole_course(world):
    test = scenario(world, "Character", "Mover")
    center, zoom = test.view()
    bounds = world.bounds
    assert (
        center.x - 1.6 * zoom <= bounds.lower.x
        and bounds.upper.x <= center.x + 1.6 * zoom
    )
    assert center.y - zoom <= bounds.lower.y and bounds.upper.y <= center.y + zoom
    (_, bottom), (_, top) = test.capsule()
    assert center.y - zoom <= bottom - Mover.RADIUS
    assert top + Mover.RADIUS <= center.y + zoom


def test_the_mover_speed_slider_changes_its_walk_in_place(world):
    test = mover(world)
    start = test.position

    test.speed = 15.0
    assert test.position == start, "the scene is not rebuilt"
    test.on_key_down("left")
    run(test, 0.25)

    assert start.x - test.position.x == pytest.approx(15.0 * 0.25, abs=0.1)


def jump_height(test, jump):
    """How far a jump lifts the character, in m."""
    ground = test.position.y
    jump()
    top = ground
    for _ in range(2 * HERTZ):
        run(test, 1 / HERTZ)
        top = max(top, test.position.y)
    assert test.on_ground, "it should have landed"
    return top - ground


@pytest.mark.parametrize(
    "jump_speed, gravity", [(10.0, 30.0), (12.0, 30.0), (10.0, 15.0)]
)
def test_the_mover_jumps_as_high_as_jump_speed_and_gravity_say(
    world, jump_speed, gravity
):
    test = mover(world)
    test.jump_speed = jump_speed
    test.gravity = gravity

    height = jump_height(test, lambda: test.on_key_down("space"))

    # v^2 / 2g, less a little for stepping at 60 Hz.
    assert height == pytest.approx(jump_speed**2 / (2 * gravity), abs=0.15)


def test_the_mover_cannot_jump_again_in_mid_air(world):
    test = mover(world)
    test.on_key_down("space")
    run(test, 0.2)
    rising = test.velocity.y

    test.on_key_up("space")
    test.on_key_down("space")

    assert test.velocity.y == rising


def test_the_mover_holding_both_ways_stands_still(world):
    test = mover(world)
    start = test.position

    test.on_key_down("left")
    test.on_key_down("d")
    run(test, 0.5)

    assert (test.position - start).length < 1e-6


def dynamic_mover(world, **settings):
    """The Dynamic Mover scenario, its sliders set, its character landed."""
    test = scenario(world, "Character", "Dynamic Mover")
    for name, value in settings.items():
        setattr(test, name, value)
    run(test, 1.5)
    assert test.mover.on_ground and test.mover.walkable
    return test


@pytest.mark.parametrize("key", ["right", "d"])
@pytest.mark.parametrize("max_speed", [3.0, 6.0, 10.0])
def test_the_dynamic_mover_walks_at_max_speed(world, key, max_speed):
    test = dynamic_mover(world, max_speed=max_speed)

    test.on_key_down(key)
    run(test, 0.6)

    assert test.mover.body.linear_velocity.x == pytest.approx(max_speed)


def test_the_dynamic_mover_accelerate_slider_sets_how_soon_it_gets_going(world):
    def speed_after_a_tenth_of_a_second(accelerate):
        test = dynamic_mover(world, accelerate=accelerate)
        test.on_key_down("d")
        run(test, 0.1)
        return test.mover.body.linear_velocity.x

    # At 20, each step asks for 2 m/s more, five times what ground friction
    # takes off. At 2 it asks for 0.2 m/s, less than friction's 0.4 -- Stop
    # Speed times Friction per second, at 60 Hz -- and the character creeps.
    assert speed_after_a_tenth_of_a_second(20.0) > 4.0
    assert speed_after_a_tenth_of_a_second(2.0) < 0.5


def slide_after_letting_go(world, **settings):
    """How far the character runs on once the walk key is let go, in m."""
    test = dynamic_mover(world, **settings)
    test.on_key_down("d")
    run(test, 0.5)
    test.on_key_up("d")
    start = test.mover.position.x
    run(test, 1.0)
    return test.mover.position.x - start


def test_the_dynamic_mover_friction_sliders_set_how_far_it_slides(world):
    default = slide_after_letting_go(world)
    assert 0.3 < default < 1.0
    assert slide_after_letting_go(world, friction=1.0) > 3 * default
    assert slide_after_letting_go(world, stop_speed=9.0) < 0.75 * default


@pytest.mark.parametrize(
    "jump_speed, gravity_scale", [(7.0, 1.5), (14.0, 1.5), (7.0, 3.0)]
)
def test_the_dynamic_mover_jumps_as_high_as_its_sliders_say(
    world, jump_speed, gravity_scale
):
    test = dynamic_mover(world, jump_speed=jump_speed, gravity_scale=gravity_scale)
    ground = test.mover.position.y

    test.on_key_down("space")
    top = ground
    for _ in range(2 * HERTZ):
        run(test, 1 / HERTZ)
        top = max(top, test.mover.position.y)

    gravity = world.gravity.length * gravity_scale
    assert top - ground == pytest.approx(jump_speed**2 / (2 * gravity), rel=0.05)


def test_space_held_in_the_air_jumps_once_on_landing(world):
    test = scenario(world, "Character", "Dynamic Mover")
    test.on_key_down("space")  # while it drops in at the start

    jumps = 0
    jumping = False
    for _ in range(3 * HERTZ):
        run(test, 1 / HERTZ)
        jumps += test.mover.jumping and not jumping
        jumping = test.mover.jumping

    assert jumps == 1


def test_with_air_steer_at_zero_the_dynamic_mover_cannot_steer_in_the_air(world):
    def speed_gained_in_the_air(air_steer):
        test = dynamic_mover(world, air_steer=air_steer)
        test.on_key_down("space")
        run(test, 2 / HERTZ)
        test.on_key_down("d")
        run(test, 0.2)
        assert not test.mover.on_ground
        return test.mover.body.linear_velocity.x

    assert speed_gained_in_the_air(0.5) > 2.0
    assert speed_gained_in_the_air(0.0) == pytest.approx(0.0, abs=0.01)


def test_the_pogo_sliders_reach_the_spring_in_place(world):
    test = dynamic_mover(world)
    start = test.mover.position

    test.pogo_hertz = 20.0
    test.pogo_damping = 2.0
    run(test, 1 / HERTZ)

    assert test.mover.pogo_joint.hertz == pytest.approx(20.0)
    assert test.mover.pogo_joint.damping_ratio == pytest.approx(2.0)
    assert (test.mover.position - start).length < 0.1, "the scene is not rebuilt"


@pytest.mark.parametrize("lock", [True, False])
def test_lock_camera_keeps_the_view_on_the_dynamic_mover(world, lock):
    test = dynamic_mover(world, lock_camera=lock)
    state.center = (0.0, 9.0)

    test.on_key_down("d")
    run(test, 1.0)

    expected = test.mover.position.x if lock else 0.0
    assert Vec2(state.center) == Vec2(expected, 9.0)


def test_the_dynamic_mover_jumps_up_through_the_elevator_and_rides_it(world):
    test = scenario(world, "Character", "Dynamic Mover")
    test.mover.body.position = (112.0, 6.0)  # on the ground under the elevator

    # The elevator comes back down to its lowest, just over the character's
    # head, at 2 pi seconds.
    run(test, 6.3)
    test.on_key_down("space")
    run(test, 0.1)
    test.on_key_up("space")
    top = 0.0
    for _ in range(3 * HERTZ):
        run(test, 1 / HERTZ)
        top = max(top, test.mover.position.y)

    assert test.mover.cast.shape.body is test.elevator, "standing on it"
    assert top > 14.0, "carried up to the top"


def test_the_dynamic_mover_comes_to_rest_with_min_speed_at_zero(world):
    test = dynamic_mover(world, min_speed=0.0)
    test.on_key_down("d")
    run(test, 0.5)
    test.on_key_up("d")

    # Friction brings it to an exact stop, which must not divide by zero.
    run(test, 1.0)

    assert test.mover.body.linear_velocity.x == pytest.approx(0.0, abs=1e-6)
