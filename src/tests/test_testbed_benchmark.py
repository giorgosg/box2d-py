"""What the Benchmark scenarios do, where a crash test cannot see it.

test_testbed.py and test_testbed_ui.py drive every scenario and every
control, but only check that nothing raises. A drum that boxes escape from,
or a heap that starts outside its ring, passes both.

These scenes are big, so the tests use the smaller ends of the controls
where they can.
"""

import math

import pytest

from box2d import ShapeProxy, Vec2
from box2d_testbed import tb_benchmark  # noqa: F401  (registers the scenarios)
from testbed_scenarios import (
    HERTZ,
    assert_view_takes_in_moving_bodies,
    dynamic_bodies,
    moved_from_start,
    run,
    scenario,
)


def test_the_tumbler_holds_its_boxes_without_crushing_them_together(world):
    test = scenario(world, "Benchmark", "Tumbler")

    # The feed takes a box a step, so all 400 are in within 7 s.
    run(test, 10.0)

    boxes = dynamic_bodies(world)
    assert len(boxes) == test.max_bodies
    # The boxes are 0.25 m squares, so two whose middles are under 0.15 m
    # apart overlap by 10 cm or more, whatever their angles. A drum too small
    # for them packs them into each other and into its walls.
    centres = [box.position for box in boxes]
    crushed = sum(
        1
        for i, a in enumerate(centres)
        for b in centres[i + 1 :]
        if (a - b).length < 0.15
    )
    assert crushed == 0, f"{crushed} pairs of boxes overlap"


def test_each_box_is_fed_into_the_tumbler_clear_of_the_others(world):
    test = scenario(world, "Benchmark", "Tumbler")
    test.max_bodies = 100

    starts = []
    for _ in range(test.max_bodies):
        before = set(dynamic_bodies(world))
        run(test, 1 / HERTZ)
        (fed,) = set(dynamic_bodies(world)) - before
        # 0.25 m squares overlap if their middles are any nearer than that.
        nearest = min(
            ((box.position - fed.position).length for box in before), default=1.0
        )
        starts.append(round(nearest, 3))

    assert min(starts) >= 0.25, starts


def test_every_spinner_piece_starts_inside_the_ring_and_clear_of_the_bar(world):
    test = scenario(world, "Benchmark", "Spinner")
    test.body_count = type(test).body_count.max_value

    bar, *pieces = dynamic_bodies(world)
    assert len(pieces) == test.body_count

    # The ring is 40 m in radius, round the origin. The corners of a piece's
    # AABB are further out than any part of it.
    def reach(piece):
        return max(
            Vec2(x, y).length
            for shape in piece.shapes
            for x in (shape.aabb.lower.x, shape.aabb.upper.x)
            for y in (shape.aabb.lower.y, shape.aabb.upper.y)
        )

    outside = [piece for piece in pieces if reach(piece) > 40.0]
    assert not outside, f"{len(outside)} pieces start outside the ring"

    # The bar is 0.8 m by 40 m, rounded by 0.2 m, and starts upright with
    # its middle at (0, -20).
    bar_shape = ShapeProxy.polygon(
        [(-0.4, -40), (0.4, -40), (0.4, 0), (-0.4, 0)], radius=0.2
    )
    in_the_bar = [
        shape for shape in world.query_shape(bar_shape) if shape.body in pieces
    ]
    assert not in_the_bar, f"{len(in_the_bar)} pieces start inside the bar"


def test_the_pyramid_stands_centred_on_the_origin(world):
    test = scenario(world, "Benchmark", "Pyramid")
    test.base_count = 6
    boxes = dynamic_bodies(world)

    # Six boxes along the bottom, five on them and so on up to one at the top.
    assert len(boxes) == 21
    bottom = sorted(box.position.x for box in boxes if box.position.y < 1)
    assert bottom == [-2.5, -1.5, -0.5, 0.5, 1.5, 2.5]
    (top,) = (box.position for box in boxes if box.position.y > 5)
    assert tuple(top) == (0, 5.5)


def test_the_compounds_land_in_the_valley_and_come_to_rest(world):
    test = scenario(world, "Benchmark", "Compound")
    compounds = dynamic_bodies(world)
    # Three by three of them, each three boxes by three.
    assert [len(body.shapes) for body in compounds] == [9] * 9

    run(test, 9.0)

    assert not any(body.awake for body in compounds)
    # The valley's sides rise a metre a step from the middle, to 13.5 m.
    assert all(abs(body.position.x) < body.position.y + 1.5 for body in compounds)
    assert all(body.position.y < 14 for body in compounds)


def test_the_valley_has_one_box_in_each_place(world):
    scenario(world, "Benchmark", "Compound")
    (valley,) = (body for body in world.bodies if body.type == "static")

    places = [
        (round(shape.aabb.center.x, 3), round(shape.aabb.center.y, 3))
        for shape in valley.shapes
    ]

    assert len(places) == len(set(places))
    # Fourteen rows: 27 boxes along the bottom, and on it a side of 13 boxes
    # either way, narrowing by one each row up.
    assert len(places) == 27 + 2 * sum(range(1, 14))


def test_compound_count_sets_how_many_bodies_there_are(world):
    test = scenario(world, "Benchmark", "Compound")
    test.count = 2
    assert len(dynamic_bodies(world)) == 4


@pytest.mark.parametrize(
    "name, control, value, boxes",
    [
        # Twenty boxes along the bottom: 20 + 19 + ... + 1.
        ("Pyramid", None, None, 210),
        # Two by two pyramids of 55 boxes.
        ("Many Pyramids", "grid", 2, 220),
    ],
)
def test_the_pyramids_stand_and_fall_asleep(world, name, control, value, boxes):
    test = scenario(world, "Benchmark", name)
    if control is not None:
        setattr(test, control, value)
    assert len(dynamic_bodies(world)) == boxes

    bodies, moved = moved_from_start(test, 1.5)

    assert max(moved) < 0.05
    assert not any(body.awake for body in bodies)


def test_the_spinner_turns_at_full_speed_and_keeps_its_pieces_in(world):
    test = scenario(world, "Benchmark", "Spinner")
    test.body_count = 150
    bar, *pieces = dynamic_bodies(world)
    assert len(pieces) == 150

    run(test, 2.0)
    # Over the third second, a step at a time.
    speeds = []
    for _ in range(HERTZ):
        run(test, 1 / HERTZ)
        speeds.append(bar.angular_velocity)

    assert sum(speeds) / len(speeds) == pytest.approx(5.0, abs=0.1)
    assert all(piece.position.length < 40 for piece in pieces)


def test_the_tumbler_speed_turns_the_drum_at_once(world):
    test = scenario(world, "Benchmark", "Tumbler")
    assert test.drum.angular_velocity == pytest.approx(math.radians(25))

    test.angular_speed = -60.0

    assert test.drum.angular_velocity == pytest.approx(math.radians(-60))
    run(test, 0.5)
    assert test.drum.rotation == pytest.approx(math.radians(-30), abs=1e-3)


def test_max_bodies_stops_and_restarts_the_tumbler_feed(world):
    test = scenario(world, "Benchmark", "Tumbler")
    test.max_bodies = 30
    run(test, 1.0)
    assert len(dynamic_bodies(world)) == 30

    test.max_bodies = 40
    run(test, 1.0)
    assert len(dynamic_bodies(world)) == 40

    # Lowering it feeds no more, and takes none out.
    test.max_bodies = 10
    run(test, 1.0)
    assert len(dynamic_bodies(world)) == 40


def test_the_tumbling_boxes_never_fall_asleep(world):
    test = scenario(world, "Benchmark", "Tumbler")
    test.max_bodies = 100

    run(test, 10.0)

    assert all(box.awake for box in dynamic_bodies(world))


@pytest.mark.parametrize(
    "name", ["Compound", "Pyramid", "Many Pyramids", "Spinner", "Tumbler"]
)
def test_the_view_takes_in_the_scene_as_it_opens(world, name):
    test = scenario(world, "Benchmark", name)

    assert_view_takes_in_moving_bodies(test)
