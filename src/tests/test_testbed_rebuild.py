"""A rebuilt scene is numbered, and so solved, as a fresh one is.

rebuild() builds the scene again inside the world it already lives in, since
the testbed, its panel and the scenario all hold that world. Box2D reuses the
ids it frees, and its solve order follows ids, so a scene rebuilt with its ids
in another order is simulated differently: Ragdoll's Respawn used to drop the
figure somewhere other than where it first landed.
"""

import random

import pytest

from box2d import World
from box2d_testbed import (  # noqa: F401  (registers the scenarios)
    tb_benchmark,
    tb_bodies,
    tb_character,
    tb_collision,
    tb_continuous,
    tb_events,
    tb_joints,
    tb_shapes,
    tb_stacking,
)
from box2d_testbed.base_test import BaseTest
from testbed_scenarios import run, scenario

#: Enough for every scene to have collided, stacked or swung: an id order
#: that matters has diverged by then.
SECONDS = 2.0

#: Several scenarios build from Python's random numbers, so both builds of a
#: scene draw the same ones.
SEED = 1234


def every_scenario():
    return [
        pytest.param(category, name, id=f"{category}-{name}".replace(" ", "-"))
        for category, tests in sorted(BaseTest.registry.items())
        for name in sorted(tests)
    ]


@pytest.fixture(autouse=True)
def random_left_as_it_was():
    saved = random.getstate()
    yield
    random.setstate(saved)


@pytest.fixture
def fresh_world():
    world = World()
    yield world
    world.destroy()


def motion(world):
    """Every body's position, rotation and velocities, in creation order."""
    return [
        (
            tuple(body.position),
            body.rotation,
            tuple(body.linear_velocity),
            body.angular_velocity,
        )
        for body in world.bodies
    ]


@pytest.mark.parametrize("category, name", every_scenario())
def test_a_rebuilt_scene_runs_exactly_as_a_fresh_one(
    world, fresh_world, category, name
):
    """Compared bit for bit: a solve order that differs shows up as a
    difference somewhere, even in a scene that ends up looking the same.

    The rebuild comes before the scene has run. Once it has, Box2D has handed
    out contact ids that a rebuild cannot give back in order, which
    BaseTest.rebuild explains.
    """
    random.seed(SEED)
    fresh = scenario(fresh_world, category, name)
    run(fresh, SECONDS)

    random.seed(SEED)
    rebuilt = scenario(world, category, name)
    random.seed(SEED)
    rebuilt.rebuild()
    run(rebuilt, SECONDS)

    assert motion(world) == motion(fresh_world)
