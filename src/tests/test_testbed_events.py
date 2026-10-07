"""What the Events scenarios do, where a crash test cannot see it.

test_testbed.py and test_testbed_ui.py drive every scenario and every
control, but only check that nothing raises. A scenario that runs cleanly
and reports the wrong thing passes both, which is how the Contact scene's
count of touching shapes lost the ground the first time a box bounced.
"""

import copy

import pytest

from box2d import Vec2, World
from box2d_testbed import tb_events  # noqa: F401  (registers the scenarios)
from testbed_scenarios import HERTZ, run, scenario


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


@pytest.fixture(params=[1, 4], ids=["1 thread", "4 threads"])
def threaded_world(request):
    """A world stepped on one thread, and one stepped on four.

    With more than one, Box2D runs pre-solve on its worker threads.
    """
    world = World(threads=request.param)
    yield world
    world.destroy()


def jump_under_the_static_platform(world):
    """The Platformer with its player stood under the left-hand platform,
    whose top is at y = 6.5, and jumping."""
    test = scenario(world, "Events", "Platformer")
    test.player.position = (-6, 0.5)
    run(test, 0.5)
    test.on_key_down("space")
    test.on_key_up("space")
    return test


def player_bottom(test):
    # The capsule runs from y = 0 to 1 on the body, with radius 0.5.
    return test.player.position.y - 0.5


def test_the_player_jumps_up_through_a_platform_and_lands_on_it(threaded_world):
    test = jump_under_the_static_platform(threaded_world)
    highest = 0.0
    for _ in range(60):
        run(test, 1 / 60)
        highest = max(highest, player_bottom(test))
    assert highest > 6.5, "the platform stopped the player on the way up"

    run(test, 2.0)

    assert player_bottom(test) == pytest.approx(6.5, abs=0.05)
    assert test.player.linear_velocity.length < 0.01


def test_pre_solve_changes_nothing_but_the_contact(threaded_world):
    test = jump_under_the_static_platform(threaded_world)
    highest = 0.0
    for _ in range(120):
        # Copies of the containers; anything else is replaced, not changed.
        before = {
            name: copy.copy(value) if isinstance(value, (set, list, dict)) else value
            for name, value in vars(test).items()
        }
        threaded_world.step(1 / 60, 4)
        changed = [name for name, value in vars(test).items() if before[name] != value]
        assert not changed, "the scenario changed during the step, from pre-solve"
        test.after_step(1 / 60)
        highest = max(highest, player_bottom(test))

    assert highest > 6.5, "pre-solve should have let the player through"


def test_the_platformer_knows_what_the_player_stands_on(world):
    test = scenario(world, "Events", "Platformer")
    ground, platform = world.bodies[0], world.bodies[1]
    run(test, 0.5)
    assert test.standing_on is ground

    test.player.position = (-6, 0.5)
    test.on_key_down("space")
    run(test, 0.25)
    assert test.standing_on is None, "in the air"

    run(test, 2.0)
    assert test.standing_on is platform


def test_the_player_cannot_jump_again_in_mid_air(world):
    test = scenario(world, "Events", "Platformer")
    run(test, 0.5)
    test.on_key_down("space")
    test.on_key_up("space")
    run(test, 0.25)
    rising = test.player.linear_velocity.y
    assert rising > 1.0, "the first jump should have left the ground"

    test.on_key_down("space")
    test.on_key_up("space")

    assert test.player.linear_velocity.y == rising


def test_a_figure_dragged_into_the_outlet_lets_go_of_the_mouse(world):
    test = scenario(world, "Events", "Sensor Funnel")
    figure = test.elements[0]
    head = figure.head
    test.on_mouse_down(head.position)
    assert test.mouse_joint is not None, "the figure should be held"

    outlet = Vec2(0, -30.5)
    for _ in range(5 * HERTZ):
        test.on_mouse_drag(outlet, Vec2(0, 0))
        run(test, 1 / HERTZ)
        if figure not in test.elements:
            break
    assert figure not in test.elements, "the figure should have been delivered"

    # The figure went, and the mouse joint with it.
    test.on_mouse_drag(outlet, Vec2(0, 0))
    test.on_mouse_release(outlet)
    assert test.mouse_joint is None


def test_ragdolls_in_the_funnel_together_never_share_a_group(world):
    # A figure's bones share a negative group index, so that they pass
    # through one another. Two figures with the same one would pass through
    # each other too.
    test = scenario(world, "Events", "Sensor Funnel")
    for _ in range(20):
        run(test, 1.0)
        groups = [figure.head.shapes[0].filter.group for figure in test.elements]
        assert len(set(groups)) == len(groups), sorted(groups)
    assert test.delivered > 5, "figures should have come and gone"


def test_the_funnel_drops_one_figure_every_half_second_from_the_start(world):
    test = scenario(world, "Events", "Sensor Funnel")
    counts = [len(test.elements)]
    run(test, 0.25)
    for _ in range(3):
        counts.append(len(test.elements))
        run(test, 0.5)

    # The first comes with the scene, then one at 0.5 s and one at 1 s.
    assert counts == [1, 1, 2, 3]


def test_raising_the_hit_threshold_above_any_landing_silences_the_hits(world):
    test = scenario(world, "Events", "Contact")
    # The boxes land at up to 16 m/s.
    test.hit_threshold = 20.0
    run(test, 8.0)

    assert test.hit_count == 0


def test_a_raised_threshold_reaches_the_links_already_built(world):
    test = scenario(world, "Events", "Joint")
    # At the default 2000 N every link breaks 0.75 s in.
    test.threshold = 10000.0
    run(test, 1.0)

    assert test.broken == 0


def test_choosing_donuts_empties_the_funnel_and_drops_donuts(world):
    test = scenario(world, "Events", "Sensor Funnel")
    run(test, 2.0)
    heads = [figure.head for figure in test.elements]

    test.shape = "donut"
    run(test, 1.0)

    assert not any(head.is_valid for head in heads), "the ragdolls should be gone"
    assert test.elements, "donuts should be falling"
    assert all(isinstance(element, list) for element in test.elements)
