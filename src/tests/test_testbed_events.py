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


def touching_shapes(world):
    """Every shape in a touching contact, as Box2D sees it."""
    return {
        shape
        for body in world.bodies
        for contact in body.contact_data
        for shape in (contact.shape_a, contact.shape_b)
    }


def test_the_touching_count_keeps_the_ground_when_a_box_bounces_off_it(world):
    test = scenario(world, "Events", "Contact")
    # The boxes bounce, so each leaves the ground and lands again, while the
    # ground's other contacts carry on. By 8 s they have settled.
    run(test, 8.0)
    floor = world.bodies[0].shapes[0]
    assert floor in touching_shapes(world), "the boxes should be on the ground"

    assert len(test.touching) == len(touching_shapes(world))


def test_body_move_counts_the_boxes_asleep_now_not_every_time_one_slept(world):
    test = scenario(world, "Events", "Body Move")
    boxes = [body for body in world.bodies if body.type == "dynamic"]
    run(test, 4.0)
    assert not any(box.awake for box in boxes), "the pyramid should have slept"
    assert test.asleep == len(boxes)

    boxes[0].awake = True
    run(test, 1 / 60)
    assert test.asleep == 0, "waking one box wakes the whole pile"

    run(test, 4.0)
    assert not any(box.awake for box in boxes), "and it settles again"
    assert test.asleep == len(boxes)
