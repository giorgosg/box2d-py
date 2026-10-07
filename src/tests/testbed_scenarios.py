"""Helpers for the tests that check what a testbed scenario does.

Each test_testbed_<category>.py builds scenarios and runs them the way the
testbed does, through the scenario's own controls and its after_step hook.
The world they run in comes from the ``world`` fixture in conftest.py.
"""

from box2d_testbed.base_test import BaseTest

#: Steps per simulated second, as the testbed runs by default.
HERTZ = 60


def scenario(world, category, name):
    """Build the scenario registered as ``name`` under ``category``.

    Its module must have been imported, which is what registers it.
    """
    test = BaseTest.registry[category][name](world)
    test.setup()
    return test


def run(test, seconds):
    """Step the scenario's world for ``seconds``, calling after_step each step."""
    for _ in range(int(seconds * HERTZ)):
        test.world.step(1 / HERTZ, 4)
        test.after_step(1 / HERTZ)


def dynamic_bodies(world):
    """The world's dynamic bodies, in the order they were made."""
    return [body for body in world.bodies if body.type == "dynamic"]
