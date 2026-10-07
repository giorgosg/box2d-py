"""What the Character scenarios do, where a crash test cannot see it.

test_testbed.py and test_testbed_ui.py drive every scenario and every
control, but only check that nothing raises. A character that runs cleanly
and goes the wrong way, or off the end of the world, passes both.
"""

import pytest

from box2d_testbed.tb_character import Mover
from testbed_scenarios import press, run, scenario


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
