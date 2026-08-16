# tests/test_testbed_ui.py
"""Drive every control of every scenario, looking for crashes.

The scenario tests elsewhere run each scenario at its defaults. That leaves
most of the code in a scenario untouched: the callbacks behind its sliders,
the branches a select switches between, what a button does the second time.
Those are exactly the paths a person exercises within seconds of opening the
testbed, and several bugs found this week lived there -- a callback firing
before setup, a control rebuilding a scene while the old one was still
referenced.

So this walks every UI element of every scenario, sets it to each interesting
value, and keeps simulating and drawing throughout. It asserts nothing about
what the scenarios do; the assertion is that nothing raises.
"""

import itertools

import pytest

from box2d import DebugDraw, Vec2, World
from box2d_testbed.base_test import BaseTest
from box2d_testbed.testbed_state import DebugDrawSettings

# Imported for the side effect of registering every scenario.
from box2d_testbed import (  # noqa: F401
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

ALL_SCENARIOS = [
    (category, name) for category, tests in BaseTest.registry.items() for name in tests
]


class Renderer(DebugDraw):
    """Reads its arguments the way the GL layer does, so type errors surface."""

    def _point(self, p):
        point = Vec2(p)
        return point.x, point.y

    def draw_segment(self, p1, p2, color):
        self._point(p1), self._point(p2), color.hex

    def draw_point(self, p, size, color):
        self._point(p), float(size), color.hex

    def draw_circle(self, center, radius, color):
        self._point(center), float(radius), color.hex

    def draw_string(self, p, s, color=None):
        self._point(p), str(s)

    def draw_solid_capsule(self, p1, p2, radius, color):
        self._point(p1), self._point(p2), color.hex

    def draw_polygon(self, transform, vertices, color):
        [self._point(transform(v)) for v in vertices], color.hex

    def draw_solid_polygon(self, transform, vertices, radius, color):
        transform.p.x, transform.q.c
        [self._point(v) for v in vertices], color.hex

    def draw_solid_circle(self, transform, center, radius, color):
        transform.p.x, self._point(center)

    def draw_bounds(self, aabb, color):
        aabb.lower.x, aabb.upper.y, color.hex

    def draw_transform(self, transform):
        transform.p.x


def interesting_values(element):
    """The values worth setting a control to.

    The ends of a range and the default, rather than a sweep: a slider's
    callback either copes with its whole range or it does not, and the ends
    are where clamping and division-by-zero live.
    """
    if element.type == "bool":
        return [True, False, element.value]
    if element.type in ("int", "float"):
        values = [element.value]
        if element.min_value is not None:
            values.append(element.min_value)
        if element.max_value is not None:
            values.append(element.max_value)
            if element.min_value is not None:
                middle = (element.min_value + element.max_value) / 2
                values.append(int(middle) if element.type == "int" else middle)
        return values
    if element.type == "select":
        return list(element.options)
    if element.type == "button":
        # Pressing a button is bumping its value; twice, since the second
        # press is the one that has to cope with what the first built.
        return [1, 2]
    return []


def run(test, steps, renderer):
    for _ in range(steps):
        test.world.step(1 / 60, 4)
        test.after_step(1 / 60)
    test.world.draw(renderer)
    test.debug_draw(renderer)


@pytest.mark.parametrize("category,name", ALL_SCENARIOS)
def test_every_control_of_every_scenario(category, name):
    """Set each control to each interesting value, simulating throughout."""
    world = World()
    test = BaseTest.registry[category][name](world)
    test.setup()

    renderer = Renderer()
    for flag in ("draw_aabbs", "draw_joints", "draw_contacts", "draw_mass"):
        setattr(renderer, flag, True)

    try:
        run(test, 5, renderer)
        for element_name, element in test.ui_elements:
            for value in interesting_values(element):
                setattr(test, element_name, value)
                run(test, 3, renderer)
    finally:
        world.destroy()


@pytest.mark.parametrize("category,name", ALL_SCENARIOS)
def test_every_scenario_survives_a_reset_mid_flight(category, name):
    """Reset rebuilds the scene while the old one is still referenced."""
    world = World()
    test = BaseTest.registry[category][name](world)
    test.setup()
    renderer = Renderer()

    try:
        for _ in range(3):
            run(test, 10, renderer)
            test.reset = (test.reset or 0) + 1
            run(test, 5, renderer)
    finally:
        world.destroy()


def test_every_debug_draw_flag_can_be_on_at_once():
    """The overlays are drawn by Box2D, so a scenario cannot break them --
    but the handlers they call are ours, and several were never exercised."""
    settings = DebugDrawSettings()
    world = World()
    test = BaseTest.registry["Joints"]["Ragdoll"](world)
    test.setup()

    renderer = Renderer()
    for key, _, _ in settings.get_current():
        setattr(renderer, "draw_" + key, True)

    try:
        run(test, 30, renderer)
    finally:
        world.destroy()


def test_switching_between_every_pair_of_scenarios():
    """Opening one scenario after another, the way clicking down the list does.

    A scenario that leaves something behind -- a callback holding a destroyed
    body, state on the shared testbed object -- shows up when the next one
    runs in the same process rather than in isolation.
    """
    renderer = Renderer()
    ordered = ALL_SCENARIOS

    for (category, name), (next_category, next_name) in itertools.pairwise(
        ordered + ordered[:1]
    ):
        world = World()
        test = BaseTest.registry[category][name](world)
        test.setup()
        run(test, 5, renderer)
        world.destroy()

        world = World()
        following = BaseTest.registry[next_category][next_name](world)
        following.setup()
        run(following, 5, renderer)
        world.destroy()


def test_every_scenario_declares_its_controls_with_labels():
    """A control with no label is invisible in the panel."""
    missing = []
    for category, name in ALL_SCENARIOS:
        world = World()
        test = BaseTest.registry[category][name](world)
        for element_name, element in test.ui_elements:
            if not element.label:
                missing.append(f"{category}/{name}.{element_name}")
        world.destroy()
    assert missing == [], f"controls without a label: {missing}"
