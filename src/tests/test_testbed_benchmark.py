"""What the Benchmark scenarios do, where a crash test cannot see it.

test_testbed.py and test_testbed_ui.py drive every scenario and every
control, but only check that nothing raises. A drum that boxes escape from,
or a heap that starts outside its ring, passes both.

These scenes are big, so the tests use the smaller ends of the controls
where they can.
"""

from box2d import ShapeProxy, Vec2
from box2d_testbed import tb_benchmark  # noqa: F401  (registers the scenarios)
from testbed_scenarios import dynamic_bodies, run, scenario


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
        run(test, 1 / 60)
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
