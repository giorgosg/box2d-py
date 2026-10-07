"""Helpers for the tests that check what a testbed scenario does.

Each test_testbed_<category>.py builds scenarios and runs them the way the
testbed does, through the scenario's own controls and its after_step hook.
The world they run in comes from the ``world`` fixture in conftest.py.
"""

import pytest

from box2d_testbed.base_test import BaseTest

#: Steps per simulated second, as the testbed runs by default.
HERTZ = 60


def every_scenario():
    """Every registered scenario, as (category, name) pytest params.

    Only the scenarios whose modules have been imported are registered, so a
    test module imports them all before calling this. Sorted, so the ids and
    the order the tests run in do not depend on the order of those imports.
    """
    return [
        pytest.param(category, name, id=f"{category}-{name}".replace(" ", "-"))
        for category, tests in sorted(BaseTest.registry.items())
        for name in sorted(tests)
    ]


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


def moved_from_start(test, seconds):
    """Run the scenario for ``seconds``: each dynamic body, and how far each
    has moved from where it started."""
    bodies = dynamic_bodies(test.world)
    start = [body.position for body in bodies]
    run(test, seconds)
    return bodies, [(body.position - p).length for body, p in zip(bodies, start)]


def assert_view_takes_in_moving_bodies(test):
    """Check the scenario's camera has every body that can move in view."""
    (left, bottom), (right, top) = test.moving_bounds()

    center, zoom = test.view()

    # zoom is half the visible height; the view is at least 1.6 times as wide.
    assert center.y - zoom <= bottom and top <= center.y + zoom
    assert center.x - 1.6 * zoom <= left and right <= center.x + 1.6 * zoom


def press(test, button):
    """Press one of the scenario's buttons, the way its panel does."""
    setattr(test, button, (getattr(test, button) or 0) + 1)
