"""The helpers in box2d_testbed.shared that several scenarios build from."""

import random

import pytest

from box2d import World

from box2d_testbed import shared
from box2d_testbed.shared import donut, random_polygon


@pytest.mark.usefixtures("random_left_as_it_was")
def test_random_polygon_is_one_box2d_can_build():
    random.seed(0)
    for _ in range(200):
        polygon = random_polygon(0.5)
        assert polygon.is_valid
        assert all(abs(v.x) <= 0.5 and abs(v.y) <= 0.5 for v in polygon.vertices)
        assert 0.05 <= polygon.radius <= 0.125


def test_random_polygon_falls_back_to_a_square_of_the_same_extent(monkeypatch):
    # Every point drawn at the same corner: there is no hull to make.
    monkeypatch.setattr(shared.random, "uniform", lambda low, high: low)
    polygon = random_polygon(0.5)
    assert polygon.is_valid
    assert sorted((v.x, v.y) for v in polygon.vertices) == [
        (-0.5, -0.5),
        (-0.5, 0.5),
        (0.5, -0.5),
        (0.5, 0.5),
    ]
    assert polygon.radius == 0.05


def test_donut_is_built_with_its_joints_closed():
    """Built where its welds already meet, a donut floating free stays still.

    The capsules used to be centred on the circle rather than inside it, so
    the first steps snapped the ring inwards.
    """
    world = World(gravity=(0, 0))
    try:
        bodies, joints = donut(world, (0, 0), radius=5, segments=10)
        assert len(bodies) == len(joints) == 10
        start = [body.position for body in bodies]
        for _ in range(60):
            world.step(1 / 60, 4)
        moved = max((b.position - p).length for b, p in zip(bodies, start))
        assert moved < 1e-3
    finally:
        world.destroy()
