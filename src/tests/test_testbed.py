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

from box2d import World, DebugDraw, Vec2

# Importing the scenario modules is what registers them on BaseTest.registry.
from box2d_testbed import (  # noqa: F401
    tb_benchmark,
    tb_collision,
    tb_events,
    tb_joints,
    tb_shapes,
    tb_stacking,
    tb_character,
    tb_bodies,
    tb_continuous,
)
from box2d_testbed.base_test import BaseTest


@pytest.fixture
def world():
    world = World()
    yield world
    world.destroy()


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

    def draw_solid_circle(self, transform, center, radius, color):
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


def test_drag_cycle(world):
    """Grab, drag and release a body, the way the testbed's mouse does.

    Releasing crashed with "b2DestroyJoint expected 2 arguments, got 1": the
    scenario harness only drives setup and stepping, so nothing reached the
    input handlers.
    """
    scenario = BaseTest.registry["Shapes"]["Friction"]
    test = scenario(world)
    test.setup()
    for _ in range(30):
        world.step(1 / 60, 4)

    target = next(body for body in world.bodies if body.type == "dynamic")
    grab = target.position
    before = len(world.bodies)

    test.on_mouse_down(Vec2(grab))
    assert test.mouse_joint is not None

    for step in range(1, 21):
        test.on_mouse_drag(Vec2(grab.x + step * 0.1, grab.y + step * 0.1), None)
        world.step(1 / 60, 4)
    assert target.position != grab

    test.on_mouse_release(Vec2(target.position))
    assert test.mouse_joint is None
    assert len(world.bodies) == before, "the drag proxy body was left behind"

    world.step(1 / 60, 4)


def test_drag_can_be_repeated(world):
    scenario = BaseTest.registry["Shapes"]["Friction"]
    test = scenario(world)
    test.setup()
    world.step(1 / 60, 4)

    target = next(body for body in world.bodies if body.type == "dynamic")
    for _ in range(3):
        test.on_mouse_down(Vec2(target.position))
        test.on_mouse_drag(Vec2(target.position + (0.5, 0.5)), None)
        world.step(1 / 60, 4)
        test.on_mouse_release(Vec2(target.position))
    assert test.mouse_joint is None


# --- app wiring that needs no GL context ------------------------------------


def test_layout_is_well_formed():
    """The docking layout is pure data, so it can be built without a window."""
    from box2d_testbed.testbed import TestbedApp

    app = TestbedApp.__new__(TestbedApp)
    params = app.create_layout()

    assert len(params.docking_splits) == 4
    labels = [w.label for w in params.dockable_windows]
    assert labels == ["Simulation", "Tests", "Performance", "Controls", "Test UI"]

    # Every window must dock into a space some split actually creates.
    created = {"MainDockSpace"} | {s.new_dock for s in params.docking_splits}
    for window in params.dockable_windows:
        assert window.dock_space_name in created, window.label
        assert window.gui_function is not None, window.label


def test_every_debug_draw_toggle_maps_to_a_real_property():
    """The settings loop sets draw_<key>; a rename would silently do nothing."""
    from box2d_testbed.testbed_state import DebugDrawSettings

    settings = DebugDrawSettings()
    keys = [key for key, _, _ in settings.get_current()]
    assert keys, "no debug draw settings found"

    for key in keys:
        name = "draw_" + key
        assert isinstance(
            getattr(DebugDraw, name, None), property
        ), f"DebugDraw.{name} is missing, so the {key!r} toggle would do nothing"


def test_debug_draw_settings_labels_are_readable():
    from box2d_testbed.testbed_state import DebugDrawSettings

    labels = {display for _, _, display in DebugDrawSettings().get_current()}
    assert "Contact normals" in labels
    assert all("_" not in label for label in labels)


# --- the UI controls, which nothing exercised -------------------------------


def ui_properties(scenario):
    """The scenario's declared UI controls, as (name, UIProperty)."""
    from box2d_testbed.ui import UIProperty

    found = {}
    for klass in reversed(scenario.__mro__):
        for name, value in vars(klass).items():
            if isinstance(value, UIProperty):
                found[name] = value
    return sorted(found.items())


def a_different_value(prop, current):
    """A plausible new setting for a control, different from the current one."""
    if prop.type == "bool":
        return not current
    if prop.type == "button":
        return None  # pressing a button is just assigning to it
    if prop.type == "select":
        options = list(prop.options or [])
        for option in options:
            if option != current:
                return option
        return current
    if prop.type in ("float", "int"):
        low = prop.min_value if prop.min_value is not None else 0
        high = prop.max_value if prop.max_value is not None else low + 1
        middle = (low + high) / 2
        if prop.type == "int":
            middle = int(middle)
            return middle if middle != current else max(int(low), current - 1)
        return middle if middle != current else (low + middle) / 2
    return current


@pytest.mark.parametrize("scenario", scenarios())
def test_scenario_ui_controls_work(world, scenario):
    """Change every control the scenario declares, as the GUI would.

    Setting a UI property fires its callbacks, and those are where scenarios
    rebuild themselves, retune joints or fire one-shot actions. The harness
    only drove setup and stepping, so none of that was covered -- which is how
    a shape swap, a conveyor's tangent speed and a whole drag cycle all reached
    the GUI broken.
    """
    test = scenario(world)
    test.setup()
    world.step(1 / 60, 4)

    for name, prop in ui_properties(scenario):
        setattr(test, name, a_different_value(prop, getattr(test, name)))
        # A control that rebuilds the scene must leave it usable.
        world.step(1 / 60, 4)
        test.after_step(1 / 60)


@pytest.mark.parametrize("scenario", scenarios())
def test_scenario_input_handlers_are_safe(world, scenario):
    """Keys and mouse events must not raise, whether the scenario uses them or not."""
    test = scenario(world)
    test.setup()
    world.step(1 / 60, 4)

    for key in ("left", "right", "up", "down", "space", "a", "z"):
        test.on_key_down(key)
        test.on_key_up(key)

    point = Vec2(0, 0)
    test.on_mouse_down(point)
    test.on_mouse_drag(point, Vec2(0, 0))
    test.on_mouse_release(point)
    world.step(1 / 60, 4)
