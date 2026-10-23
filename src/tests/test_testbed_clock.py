"""What the Pendulum Clock does, where a crash test cannot see it.

A clock whose escapement jams still steps without raising: the pendulum
swings on by itself and the wheels sit still. So these count teeth.
"""

import math

import pytest

from box2d import Vec2
from box2d_testbed import tb_clock  # noqa: F401  (registers the scenario)
from box2d_testbed.tb_clock import polar
from testbed_scenarios import assert_view_takes_in_moving_bodies, press, run, scenario


class Turns:
    """Follows how far a body has turned, over any number of turns."""

    def __init__(self, body):
        self.body = body
        self.last = body.rotation
        self.total = 0.0

    def update(self):
        rotation = self.body.rotation
        self.total += (rotation - self.last + math.pi) % (2 * math.pi) - math.pi
        self.last = rotation

    @property
    def clockwise(self):
        """Clockwise turns so far, as a fraction of a whole turn."""
        return -self.total / (2 * math.pi)


def run_counting(test, seconds, *bodies):
    """Run the clock for ``seconds``, following how far each body turns."""
    turns = [Turns(body) for body in bodies]
    for _ in range(int(seconds)):
        run(test, 1.0)
        for turn in turns:
            turn.update()
    return turns


def nearly_run_down(test):
    """Lower the weight to within a tooth of the end of the rack.

    By whole teeth, so the rack still meshes with the drive pinion as it did.
    What is left takes the clock up to 5 minutes to run down.
    """
    teeth = math.floor((test.RUN - test.fallen) / test.rack_pitch)
    test.rack.position = test.rack.position - (0, teeth * test.rack_pitch)


def step_as_the_testbed_does(test, seconds):
    """Like run, but at the testbed's 20 sub-steps rather than 4."""
    for _ in range(int(seconds * 60)):
        test.world.step(1 / 60, 20)
        test.after_step(1 / 60)


def mean_swing(test, swings):
    """How far the pendulum swings either way over the next ``swings``
    swings, on average, in degrees.

    Averaged, because from one swing to the next it varies by a degree or
    two, as the teeth happen to catch the pins.
    """
    total, last = 0.0, test.swings
    for _ in range(swings):
        while test.swings == last:
            run(test, 1 / 60)
        last = test.swings
        total += math.degrees(test.amplitude)
    return total / swings


def test_the_escape_wheel_lets_one_tooth_go_every_two_swings(world):
    test = scenario(world, "Machines", "Pendulum Clock")

    (escape,) = run_counting(test, 120, test.escape_wheel)

    teeth = escape.clockwise * test.ESCAPE_TEETH
    # A tooth goes by each pin in turn: half a tooth a swing. A wheel that
    # slipped would turn tens of teeth more, and one that jammed tens less;
    # within a tooth and a half is where in a tick the count happens to stop.
    assert test.swings > 40
    assert abs(teeth - test.swings / 2) < 1.5, (teeth, test.swings)


def test_the_weight_keeps_the_pendulum_swinging(world):
    test = scenario(world, "Machines", "Pendulum Clock")

    run(test, 120)

    # It starts 5.7 degrees over, and the shoves from the escape wheel make
    # the swing grow from there.
    assert math.degrees(test.amplitude) > 7.0


def test_the_hands_turn_at_the_rates_of_a_clock(world):
    test = scenario(world, "Machines", "Pendulum Clock")

    escape, center, hour = run_counting(
        test, 300, test.escape_wheel, test.center_wheel, test.hour_wheel
    )

    # The center wheel turns 60 times slower than the escape wheel, and the
    # hour wheel 12 times slower again, give or take the play between teeth.
    assert escape.clockwise > 3.0
    assert abs(escape.clockwise / 60 - center.clockwise) < 0.003
    assert abs(center.clockwise / 12 - hour.clockwise) < 0.005


def test_the_weight_falls_as_the_train_turns(world):
    test = scenario(world, "Machines", "Pendulum Clock")

    (center,) = run_counting(test, 120, test.center_wheel)

    # The rack comes down as far as the drive pinion rolls along it.
    rolled = center.clockwise * 2 * math.pi * test.drive_radius
    assert abs(test.fallen - rolled) < 0.03, (test.fallen, rolled)


def test_with_no_weight_the_pendulum_dies_away(world):
    test = scenario(world, "Machines", "Pendulum Clock")
    test.weight = 0.0

    run(test, 30)
    (escape,) = run_counting(test, 90, test.escape_wheel)

    assert abs(escape.clockwise) < 0.02
    # The air drags on it and nothing makes that up: from 5.7 degrees it
    # loses half its swing about every 30 seconds.
    assert math.degrees(test.amplitude) < 1.5


@pytest.mark.parametrize(
    "kilograms, lowest, highest", [(10, 4.5, 6.0), (80, 9.0, 11.0)]
)
def test_the_weight_sets_how_far_the_pendulum_swings(world, kilograms, lowest, highest):
    test = scenario(world, "Machines", "Pendulum Clock")
    test.weight = kilograms
    run(test, 200)

    # It settles where the shoves make up for what the air takes: more
    # weight, harder shoves, a wider swing.
    assert lowest < mean_swing(test, 40) < highest


def test_dragged_wider_the_swing_shrinks_back(world):
    test = scenario(world, "Machines", "Pendulum Clock")
    run(test, 200)
    usual = mean_swing(test, 10)

    # Dragged out to 20 degrees by its bob, and let go.
    length = test.PENDULUM_LENGTH
    bob = test.pendulum.get_world_point((0, -length))
    test.on_mouse_down(bob)
    for step in range(180):
        angle = -math.pi / 2 + math.radians(20) * min(1, step / 120)
        test.on_mouse_drag(test.pivot + polar(length, angle), Vec2(0, 0))
        run(test, 1 / 60)
    test.on_mouse_release(bob)
    assert mean_swing(test, 2) > usual + 3

    # The air takes the extra away, and the escapement does not put it back.
    run(test, 60)
    assert mean_swing(test, 10) < usual + 1.5


def test_weight_sets_the_mass_of_the_weight(world):
    test = scenario(world, "Machines", "Pendulum Clock")
    before = test.rack.mass

    test.weight = test.weight + 10.0

    assert abs(test.rack.mass - before - 10.0) < 0.01


def test_wind_lifts_the_weight_and_the_clock_goes_on(world):
    test = scenario(world, "Machines", "Pendulum Clock")
    run(test, 120)
    assert test.fallen > 0.1

    press(test, "wind")

    assert test.fallen < test.rack_pitch / 2
    swings = test.swings
    (escape,) = run_counting(test, 60, test.escape_wheel)
    teeth = escape.clockwise * test.ESCAPE_TEETH
    assert test.swings - swings > 20
    assert abs(teeth - (test.swings - swings) / 2) < 1.5


def test_the_clock_stops_when_the_weight_is_down(world):
    test = scenario(world, "Machines", "Pendulum Clock")
    # Most of the way down already, so the test does not run for an hour.
    nearly_run_down(test)

    run(test, 330)
    (escape,) = run_counting(test, 30, test.escape_wheel)

    assert abs(test.fallen - test.RUN) < 0.05
    # Not still: the pins rock it about in the play of the train, which
    # nothing holds tight any more. But not by as much as a tooth.
    assert abs(escape.clockwise) * test.ESCAPE_TEETH < 1.0
    assert "0%" in test.status()


def test_wound_and_pushed_a_stopped_clock_goes_again(world):
    test = scenario(world, "Machines", "Pendulum Clock")
    nearly_run_down(test)
    run(test, 330)

    press(test, "wind")
    press(test, "push")
    run(test, 30)

    swings = test.swings
    (escape,) = run_counting(test, 60, test.escape_wheel)
    teeth = escape.clockwise * test.ESCAPE_TEETH
    assert test.swings - swings > 20
    assert abs(teeth - (test.swings - swings) / 2) < 1.5


def test_once_the_weight_is_down_the_pendulum_dies_away(world):
    test = scenario(world, "Machines", "Pendulum Clock")
    step_as_the_testbed_does(test, 240)
    nearly_run_down(test)

    step_as_the_testbed_does(test, 420)

    assert abs(test.fallen - test.RUN) < 0.05
    assert math.degrees(test.amplitude) < 1.5


def test_push_sets_a_stopped_pendulum_swinging(world):
    test = scenario(world, "Machines", "Pendulum Clock")
    test.weight = 0.0
    run(test, 240)
    assert math.degrees(test.amplitude) < 1.0

    test.weight = 40.0
    press(test, "push")
    swings = test.swings
    run(test, 60)

    assert test.swings - swings > 20
    assert math.degrees(test.amplitude) > 6.0


def test_the_view_takes_in_the_whole_clock(world):
    test = scenario(world, "Machines", "Pendulum Clock")
    assert_view_takes_in_moving_bodies(test)
