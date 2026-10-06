"""What the Events scenarios do, where a crash test cannot see it.

test_testbed.py and test_testbed_ui.py drive every scenario and every
control, but only check that nothing raises. A scenario that runs cleanly
and reports the wrong thing passes both, which is how the Contact scene's
count of touching shapes lost the ground the first time a box bounced.
"""

from box2d_testbed import tb_events  # noqa: F401  (registers the scenarios)
from testbed_scenarios import run, scenario


def test_the_foot_sensor_player_walks_with_the_arrow_keys(world):
    test = scenario(world, "Events", "Foot Sensor")
    run(test, 1.0)

    test.on_key_down("left")
    run(test, 0.5)

    assert test.player.linear_velocity.x < -2.0


def test_letting_go_of_one_of_two_walk_keys_keeps_the_other(world):
    test = scenario(world, "Events", "Foot Sensor")
    run(test, 1.0)
    test.on_key_down("d")
    test.on_key_down("a")
    run(test, 0.25)

    test.on_key_up("a")
    run(test, 0.25)

    assert test.player.linear_velocity.x > 2.0, "D is still held"


def test_the_foot_counts_the_ground_it_overlaps_until_the_player_walks_off(world):
    test = scenario(world, "Events", "Foot Sensor")
    test.on_key_down("right")
    counts = []
    for _ in range(3 * 60):
        run(test, 1 / 60)
        counts.append((test.overlaps, len(test.foot.sensor_overlaps)))

    events, overlaps = zip(*counts)
    assert events == overlaps, "the events lost track of the ground"
    assert 2 in events, "the foot should straddle two segments as it walks"
    assert events[-1] == 0, "the player should have run off the end"
