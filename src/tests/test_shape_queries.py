# tests/test_shape_queries.py
"""Asking the world about a region rather than a point.

A ray cast answers what a point would hit. Shape casting answers what
something of real size would hit, which is the question behind "can this
character fit through the gap" -- and it was the one query Box2D offers that
was not bound at all.

query_circle was the only shape overlap available, and it built its proxy by
hand; both now go through ShapeProxy, so the tests below cover the proxy
itself as well as the two queries.
"""

import math

import pytest

from box2d import MAX_PROXY_POINTS, ShapeProxy, Vec2, World


@pytest.fixture
def world():
    world = World()
    yield world
    world.destroy()


@pytest.fixture
def ground(world):
    body = world.add_body(position=(0, 0))
    body.add_box(20, 1)
    return body


# --- the proxy itself -------------------------------------------------------


def test_circle_proxy_is_one_point_and_a_radius():
    proxy = ShapeProxy.circle(0.5, center=(1, 2))
    assert proxy.points == [Vec2(1, 2)]
    assert proxy.radius == pytest.approx(0.5)


def test_capsule_proxy_keeps_both_centres():
    proxy = ShapeProxy.capsule((0, 0), (3, 0), 0.5)
    assert proxy.points == [Vec2(0, 0), Vec2(3, 0)]


def test_segment_proxy_has_no_radius():
    assert ShapeProxy.segment((0, 0), (1, 1)).radius == 0.0


def test_box_proxy_uses_full_width_like_add_box():
    """A 2x4 box spans -1..1 by -2..2, matching Body.add_box."""
    proxy = ShapeProxy.box(2, 4)
    assert min(point.x for point in proxy.points) == pytest.approx(-1)
    assert max(point.x for point in proxy.points) == pytest.approx(1)
    assert min(point.y for point in proxy.points) == pytest.approx(-2)
    assert max(point.y for point in proxy.points) == pytest.approx(2)


def test_box_proxy_is_placed_and_rotated():
    proxy = ShapeProxy.box(2, 2, center=(5, 0), rotation=math.pi / 4)
    assert sum(point.x for point in proxy.points) / 4 == pytest.approx(5)
    # A square turned 45 degrees is wider than the square itself.
    width = max(p.x for p in proxy.points) - min(p.x for p in proxy.points)
    assert width == pytest.approx(2 * math.sqrt(2), abs=1e-5)


def test_proxy_accepts_any_vector_like():
    proxy = ShapeProxy.capsule(Vec2(0, 0), [1, 1], 0.25)
    assert proxy.points == [Vec2(0, 0), Vec2(1, 1)]


def test_empty_proxy_is_rejected():
    with pytest.raises(ValueError, match="at least one point"):
        ShapeProxy(points=[])


def test_oversized_proxy_is_rejected():
    """Box2D's array is fixed at 8 points, and would be overrun silently."""
    with pytest.raises(ValueError, match="at most 8 points"):
        ShapeProxy(points=[(i, 0) for i in range(MAX_PROXY_POINTS + 1)])


def test_proxy_converts_to_c():
    proxy = ShapeProxy.capsule((0, 1), (2, 3), 0.5).b2ShapeProxy
    assert proxy.count == 2
    assert (proxy.points[1].x, proxy.points[1].y) == (2, 3)
    assert proxy.radius == pytest.approx(0.5)


# --- overlap ----------------------------------------------------------------


def test_query_shape_finds_an_overlapping_body(world, ground):
    hits = world.query_shape(ShapeProxy.box(4, 4, center=(0, 0)))
    assert ground.shapes[0] in hits


def test_query_shape_misses_a_distant_body(world, ground):
    assert world.query_shape(ShapeProxy.box(1, 1, center=(0, 50))) == []


def test_query_shape_respects_max_results(world):
    for x in range(5):
        body = world.add_body(body_type="dynamic", position=(x * 2, 0))
        body.add_circle(radius=0.4)
    assert len(world.query_shape(ShapeProxy.box(40, 4), max_results=3)) == 3


def test_query_circle_still_works_through_the_proxy(world, ground):
    """query_circle now delegates, so it must keep behaving the same."""
    assert ground.shapes[0] in world.query_circle((0, 0), 2.0)
    assert world.query_circle((0, 50), 1.0) == []


# --- casting ----------------------------------------------------------------


def test_cast_shape_finds_the_ground(world, ground):
    hits = world.cast_shape(ShapeProxy.circle(0.5, (0, 10)), (0, -20))

    assert hits, "a circle dropped onto the ground should hit it"
    assert hits[0].shape is ground.shapes[0]
    assert hits[0].point.y == pytest.approx(0.5, abs=0.05)
    assert hits[0].normal.y == pytest.approx(1.0, abs=0.05)


def test_cast_shape_stops_at_the_shape_surface_not_its_centre(world, ground):
    """The difference from a ray cast: the radius is accounted for."""
    ray = world.ray_cast((0, 10), (0, -20))
    cast = world.cast_shape(ShapeProxy.circle(2.0, (0, 10)), (0, -20))

    assert ray[0].point.y == pytest.approx(0.5, abs=0.05)
    # A smaller fraction is less of the way along the sweep, i.e. stopped sooner.
    assert cast[0].fraction < ray[0].fraction, "the big circle stops sooner"


def test_cast_shape_reports_hits_nearest_first(world):
    for y in (0, -5, -10):
        body = world.add_body(position=(0, y))
        body.add_box(10, 0.5)

    hits = world.cast_shape(ShapeProxy.circle(0.2, (0, 5)), (0, -20))
    assert len(hits) == 3
    assert [hit.fraction for hit in hits] == sorted(hit.fraction for hit in hits)


def test_cast_shape_first_hit_only(world):
    for y in (0, -5, -10):
        body = world.add_body(position=(0, y))
        body.add_box(10, 0.5)

    hits = world.cast_shape(
        ShapeProxy.circle(0.2, (0, 5)), (0, -20), first_hit_only=True
    )
    assert len(hits) == 1
    assert hits[0].point.y == pytest.approx(0.25, abs=0.05), "the nearest one"


def test_cast_shape_finds_nothing_in_an_empty_world(world):
    assert world.cast_shape(ShapeProxy.circle(1, (0, 0)), (0, -50)) == []


def test_cast_shape_answers_whether_something_fits(world):
    """The question shape casting exists for, which a ray cannot answer."""
    for x in (-3, 3):
        post = world.add_body(position=(x, 0))
        post.add_box(2, 4)  # posts span |x| 2..4, leaving a 4m gap

    # A ray straight down the middle sees nothing either way.
    assert world.ray_cast((0, 10), (0, -20)) == []

    narrow = world.cast_shape(ShapeProxy.circle(1.5, (0, 10)), (0, -20))
    wide = world.cast_shape(ShapeProxy.circle(2.5, (0, 10)), (0, -20))

    assert narrow == [], "a 3m-wide mover fits through a 4m gap"
    assert wide, "a 5m-wide mover does not"


def test_cast_shape_reports_initial_overlap_at_fraction_zero(world, ground):
    """Starting inside geometry is reported, not skipped.

    b2ShapeCast documents initial overlap as a miss, so it would be fair to
    assume b2World_CastShape does the same; it does not.
    """
    inside = world.cast_shape(ShapeProxy.circle(0.5, (0, 0)), (0, -20))

    assert inside, "a cast starting inside the ground should say so"
    assert inside[0].shape is ground.shapes[0]
    assert inside[0].fraction == 0.0


def test_cast_shape_respects_the_filter(world):
    from box2d import CollisionFilter

    body = world.add_body(position=(0, 0))
    body.add_box(10, 1, filter=CollisionFilter(category=0b0010))

    proxy = ShapeProxy.circle(0.5, (0, 10))
    assert world.cast_shape(proxy, (0, -20), filter=CollisionFilter(mask=0b0010))
    assert not world.cast_shape(proxy, (0, -20), filter=CollisionFilter(mask=0b0001))


def test_cast_a_box_not_only_a_circle(world, ground):
    hits = world.cast_shape(ShapeProxy.box(2, 2, center=(0, 10)), (0, -20))
    assert hits
    assert hits[0].point.y == pytest.approx(0.5, abs=0.1)
