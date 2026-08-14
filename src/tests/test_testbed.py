# tests/test_testbed.py
"""Every testbed scenario must build and simulate without a GUI.

The testbed is by far the largest consumer of this API -- 18 scenarios
covering joints, sensors, chains, raycasts and compound shapes -- but it sat
entirely outside the test suite, so an API break only surfaced when someone
launched the GUI and clicked through it by hand. That is how a body built with
a rotation stayed broken.

Scenario setup(), after_step() and debug_draw() touch only the physics and
drawing APIs, never GL, so they run headless. Only the window, input and
GL-backed renderer need a display, and none of those are exercised here.
"""

import pytest

from box2d import World, DebugDraw

# Importing the scenario modules is what registers them on BaseTest.registry.
from box2d_testbed import (  # noqa: F401
    tb_benchmark,
    tb_collision,
    tb_events,
    tb_joints,
    tb_shapes,
)
from box2d_testbed.base_test import BaseTest


def scenarios():
    """Every registered testbed scenario, as pytest params."""
    return [
        pytest.param(cls, id=f"{category}-{name}".replace(" ", "-"))
        for category, tests in sorted(BaseTest.registry.items())
        for name, cls in sorted(tests.items())
    ]


class RecordingDraw(DebugDraw):
    """A DebugDraw that counts calls instead of issuing GL commands."""

    def __init__(self):
        super().__init__()
        self.calls = 0
        self.draw_shapes = True
        self.draw_joints = True

    def draw_solid_polygon(self, transform, vertices, radius, color):
        self.calls += 1

    def draw_circle(self, center, radius, color):
        self.calls += 1

    def draw_solid_circle(self, transform, radius, color):
        self.calls += 1

    def draw_solid_capsule(self, p1, p2, radius, color):
        self.calls += 1

    def draw_segment(self, p1, p2, color):
        self.calls += 1

    def draw_point(self, p, size, color):
        self.calls += 1

    def draw_string(self, p, s, color=None):
        # Scenarios call this with two arguments; only the base class declares
        # color as required, and the GL renderer defaults it too.
        self.calls += 1

    def draw_transform(self, transform):
        self.calls += 1


def test_registry_is_populated():
    """Guard against the imports above silently registering nothing."""
    total = sum(len(tests) for tests in BaseTest.registry.values())
    assert total >= 18, f"only {total} scenarios registered"


@pytest.mark.parametrize("scenario", scenarios())
def test_scenario_builds_and_steps(scenario):
    """Constructing and simulating a scenario must not raise."""
    world = World()
    try:
        test = scenario(world)
        test.setup()
        for _ in range(30):
            world.step(1 / 60, 4)
            test.after_step(1 / 60)
    finally:
        world.destroy()


@pytest.mark.parametrize("scenario", scenarios())
def test_scenario_draws(scenario):
    """Each scenario must render something through the debug draw path."""
    world = World()
    try:
        test = scenario(world)
        test.setup()
        world.step(1 / 60, 4)

        draw = RecordingDraw()
        world.draw(draw)
        test.debug_draw(draw)

        assert draw.calls > 0, "scenario drew nothing"
    finally:
        world.destroy()
