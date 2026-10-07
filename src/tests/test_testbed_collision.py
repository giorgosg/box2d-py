"""What the Collision scenarios do, where a crash test cannot see it.

test_testbed.py and test_testbed_ui.py drive every scenario and every
control, but only check that nothing raises. A query scene that draws
something passes both, whatever it draws: Ray Cast's Max Hits went up to
five on a ray that crossed two shapes.
"""

import random

import pytest

from box2d import World
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
