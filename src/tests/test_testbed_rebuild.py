"""A rebuilt scene is numbered, and so solved, as a fresh one is.

rebuild() builds the scene again inside the world it already lives in, since
the testbed, its panel and the scenario all hold that world. Box2D reuses the
ids it frees, and its solve order follows ids, so a scene rebuilt with its ids
in another order is simulated differently: Ragdoll's Respawn, pressed as the
first figure fell, dropped the next one somewhere a fresh one would not land.
Pressed after the figure has landed it still does, because of the contact ids
the first figure used, which BaseTest.rebuild explains.
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
from testbed_scenarios import every_scenario, run, scenario

#: Enough for every scene to have collided, stacked or swung: an id order
#: that matters has diverged by then.
SECONDS = 2.0

#: Several scenarios build from Python's random numbers, so both builds of a
#: scene draw the same ones.
SEED = 1234

# These tests seed Python's random numbers; put them back afterwards.
pytestmark = pytest.mark.usefixtures("random_left_as_it_was")


@pytest.fixture
def fresh_world():
    """A second fresh world, for the scene built once, destroyed after the test."""
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

    # Seeded differently, so a scene with random parts that was never rebuilt
    # would not match.
    random.seed(SEED + 1)
    rebuilt = scenario(world, category, name)
    first = world.bodies
    random.seed(SEED)
    rebuilt.rebuild()
    assert not any(body.is_valid for body in first), "the first scene is gone"
    run(rebuilt, SECONDS)

    assert motion(world) == motion(fresh_world)


def test_compound_count_builds_the_scene_a_fresh_world_would(world, fresh_world):
    """Count used to destroy and set up by hand, in creation order, so the
    smaller scene it built came out in reverse id order."""
    # The pieces fall a while before they land on each other.
    seconds = 3.0

    fresh = BaseTest.registry["Benchmark"]["Compound"](fresh_world)
    fresh.count = 2
    fresh.setup()
    run(fresh, seconds)

    changed = scenario(world, "Benchmark", "Compound")
    changed.count = 2
    run(changed, seconds)

    assert motion(world) == motion(fresh_world)
