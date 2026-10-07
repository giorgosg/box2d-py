"""What the Collision scenarios do, where a crash test cannot see it.

test_testbed.py and test_testbed_ui.py drive every scenario and every
control, but only check that nothing raises. A query scene that draws
something passes both, whatever it draws: Ray Cast's Max Hits went up to
five on a ray that crossed two shapes.
"""

import random

import pytest

from box2d import DebugDraw, ShapeProxy, Vec2, World
from box2d_testbed import tb_collision  # noqa: F401  (registers the scenarios)
from testbed_scenarios import press, scenario


@pytest.fixture(autouse=True)
def random_left_as_it_was():
    """Some tests seed Python's random numbers; put them back afterwards."""
    saved = random.getstate()
    yield
    random.setstate(saved)


def layout(world):
    """Every static shape, as its kind and where its bounding box is."""
    return [
        (
            type(shape).__name__,
            tuple(shape.aabb.lower),
            tuple(shape.aabb.upper),
        )
        for body in world.bodies
        for shape in body.shapes
    ]


def test_ray_cast_lays_out_the_same_shapes_every_time(world):
    random.seed(1)
    first = layout(scenario(world, "Collision", "Ray Cast").world)

    other = World()
    try:
        random.seed(2)
        again = scenario(other, "Collision", "Ray Cast")
        assert layout(other) == first, "opened again"
        press(again, "reset")
        assert layout(other) == first, "reset"
    finally:
        other.destroy()


def test_ray_cast_leaves_pythons_random_numbers_alone(world):
    before = random.getstate()

    scenario(world, "Collision", "Ray Cast")

    assert random.getstate() == before


def test_each_max_hits_shows_that_many_hits_along_the_first_ray(world):
    test = scenario(world, "Collision", "Ray Cast")
    control = type(test).max_hits

    shown = {}
    for max_hits in range(control.min_value, control.max_value + 1):
        test.max_hits = max_hits
        shown[max_hits] = test.cast()

    assert {n: len(hits) for n, hits in shown.items()} == {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}
    # Each is the nearest that many: the closest alone, then one more each.
    for n in range(2, 6):
        assert shown[n][: n - 1] == shown[n - 1]
    fractions = [hit.fraction for hit in shown[5]]
    assert fractions == sorted(fractions)


@pytest.mark.parametrize("mover", ["circle", "box", "capsule"])
def test_shape_cast_opens_aimed_through_the_gap_in_the_wall(world, mover):
    test = scenario(world, "Collision", "Shape Cast")
    test.mover = mover

    assert test.cast() == [], "at the size it opens with, it fits"

    test.size = 1.5
    (hit,) = test.cast()
    # The wall is 0.6 m thick, standing on x = 0, with a gap from y = -2 to
    # y = 2; nothing else is in the way.
    assert abs(hit.point.x) <= 0.3 + 1e-4 and abs(hit.point.y) >= 2 - 1e-4, hit
    assert 0 < hit.fraction < 1


@pytest.mark.parametrize(
    "name, start, end",
    [("Ray Cast", "ray_start", "ray_end"), ("Shape Cast", "cast_start", "cast_end")],
)
def test_pressing_starts_a_new_cast_where_the_mouse_is(world, name, start, end):
    test = scenario(world, "Collision", name)

    # Before the mouse has moved, there is no cast to the old end.
    test.on_mouse_down(Vec2(2, 3))
    assert getattr(test, start) == Vec2(2, 3)
    assert getattr(test, end) == Vec2(2, 3)
    test.cast()

    test.on_mouse_drag(Vec2(4, 1), Vec2(2, -2))
    test.on_mouse_release(Vec2(5, 1))
    assert getattr(test, start) == Vec2(2, 3)
    assert getattr(test, end) == Vec2(5, 1)


class Drawn(DebugDraw):
    """Keeps the points drawn, and the circles: what the scenarios mark hits
    and the circle mover with."""

    def __init__(self):
        super().__init__()
        self.points = []
        self.circles = []

    def draw_point(self, p, size, color):
        self.points.append(Vec2(p))

    def draw_circle(self, center, radius, color):
        self.circles.append((Vec2(center), radius))

    def draw_segment(self, p1, p2, color):
        pass

    def draw_solid_capsule(self, p1, p2, radius, color):
        pass


def test_ray_cast_marks_the_hits_the_query_returns(world):
    test = scenario(world, "Collision", "Ray Cast")
    test.max_hits = 4

    drawn = Drawn()
    test.debug_draw(drawn)

    hits = world.ray_cast(test.ray_start, test.ray_end - test.ray_start)
    assert drawn.points == [hit.point for hit in hits[:4]]


def test_shape_cast_draws_the_mover_where_the_first_hit_stops_it(world):
    test = scenario(world, "Collision", "Shape Cast")
    test.size = 1.5
    test.all_hits = True

    drawn = Drawn()
    test.debug_draw(drawn)

    translation = test.cast_end - test.cast_start
    hits = world.cast_shape(ShapeProxy.circle(1.5, test.cast_start), translation)
    # Through the gap the circle would touch the lower wall, the upper one
    # and a post beyond it, and it stops at the first.
    assert len(hits) == 3
    assert drawn.points == [hit.point for hit in hits]
    (start, _), (stopped, radius) = drawn.circles
    assert start == test.cast_start
    # Stopped touching the wall where it hit, on the line of the cast.
    assert radius == 1.5
    assert (stopped - hits[0].point).length == pytest.approx(1.5, abs=0.01)
    assert (stopped - test.cast_start).cross(translation) == pytest.approx(0, abs=1e-4)


def test_shape_cast_draws_a_clear_mover_at_the_end(world):
    test = scenario(world, "Collision", "Shape Cast")

    drawn = Drawn()
    test.debug_draw(drawn)

    assert drawn.points == []
    assert drawn.circles == [(test.cast_start, 0.5), (test.cast_end, 0.5)]


@pytest.mark.parametrize(
    "name, start, end",
    [("Ray Cast", "ray_start", "ray_end"), ("Shape Cast", "cast_start", "cast_end")],
)
def test_reset_puts_the_first_cast_back(world, name, start, end):
    test = scenario(world, "Collision", name)
    first = getattr(test, start), getattr(test, end)
    test.on_mouse_down(Vec2(1, 1))
    test.on_mouse_release(Vec2(2, 2))

    press(test, "reset")

    assert (getattr(test, start), getattr(test, end)) == first


@pytest.mark.parametrize(
    "name, start, end",
    [("Ray Cast", "ray_start", "ray_end"), ("Shape Cast", "cast_start", "cast_end")],
)
def test_the_view_takes_in_the_shapes_and_the_first_cast(world, name, start, end):
    test = scenario(world, "Collision", name)
    center, zoom = test.view()
    bounds = world.bounds
    xs = [bounds.lower.x, bounds.upper.x, getattr(test, start).x, getattr(test, end).x]
    ys = [bounds.lower.y, bounds.upper.y, getattr(test, start).y, getattr(test, end).y]

    # zoom is half the visible height; the view is at least 1.6 times as wide.
    assert center.y - zoom <= min(ys) and max(ys) <= center.y + zoom
    assert center.x - 1.6 * zoom <= min(xs) and max(xs) <= center.x + 1.6 * zoom
