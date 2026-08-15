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

import os
import pathlib
import re

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


def test_every_debug_draw_toggle_reaches_the_c_struct():
    """The settings loop sets draw_<key>; a rename would silently do nothing.

    Checks the value actually lands on b2DebugDraw rather than just that an
    attribute exists, which is what would break: a plain instance attribute
    would accept the write and change nothing.
    """
    from box2d_testbed.testbed_state import DebugDrawSettings

    settings = DebugDrawSettings()
    keys = [key for key, _, _ in settings.get_current()]
    assert keys, "no debug draw settings found"

    draw = DebugDraw()
    for key in keys:
        name = "draw_" + key
        assert hasattr(
            type(draw), name
        ), f"DebugDraw.{name} is missing, so the {key!r} toggle would do nothing"

        before = getattr(draw, name)
        setattr(draw, name, not before)
        assert getattr(draw, name) is (not before), f"{name} did not change"
        # The struct is the thing Box2D reads, so check it directly.
        field = type(draw).__dict__[name]._field
        assert bool(getattr(draw._debug_draw, field)) is (not before)
        setattr(draw, name, before)


def test_all_fifteen_box2d_draw_flags_are_bound():
    """Box2D has fifteen; six were unbound and so unreachable from the UI."""
    from box2d._box2d import ffi
    from box2d.debug_draw import _DrawFlag

    struct_flags = {
        name
        for name in dir(ffi.new("b2DebugDraw*"))
        if name.startswith("draw") and name != "drawingBounds"
    }
    bound = {
        flag._field for flag in vars(DebugDraw).values() if isinstance(flag, _DrawFlag)
    }
    assert struct_flags - bound == set(), f"unbound draw flags: {struct_flags - bound}"


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


# --- camera framing ---------------------------------------------------------


def test_view_uses_declared_values_when_a_scenario_sets_them():
    from box2d import Vec2, World
    from box2d_testbed.base_test import BaseTest

    class Framed(BaseTest, category="_Test", name="Framed"):
        camera_center = (3.0, 4.0)
        camera_zoom = 7.0

        def setup(self):
            body = self.world.add_body(body_type="dynamic", position=(100, 100))
            body.add_box(1, 1)

    world = World()
    test = Framed(world)
    test.setup()

    center, zoom = test.view()
    assert center == Vec2(3, 4), "a declared centre should win over the contents"
    assert zoom == 7.0
    world.destroy()
    del BaseTest.registry["_Test"]


def test_view_frames_the_moving_bodies_not_the_ground():
    """The reason framing is not simply world bounds: ground dwarfs the scene."""
    from box2d import World
    from box2d_testbed.base_test import BaseTest

    class Wide(BaseTest, category="_Test", name="Wide"):
        def setup(self):
            ground = self.world.add_body(position=(0, 0))
            ground.add_box(2000, 1)  # a kilometre either way
            box = self.world.add_body(body_type="dynamic", position=(0, 5))
            box.add_box(2, 2)

    world = World()
    test = Wide(world)
    test.setup()

    center, zoom = test.view()
    assert zoom < 20, "framing the ground would zoom out to a kilometre"
    assert center.y > 3, "the box, not the ground, is what matters"
    world.destroy()
    del BaseTest.registry["_Test"]


def test_view_falls_back_to_the_whole_world_when_nothing_moves():
    """Query scenarios have only static geometry, which is the whole scene."""
    from box2d import World
    from box2d_testbed.base_test import BaseTest

    class Static(BaseTest, category="_Test", name="Static"):
        def setup(self):
            for x in (-8, 8):
                body = self.world.add_body(position=(x, 0))
                body.add_circle(radius=1)

    world = World()
    test = Static(world)
    test.setup()

    assert test.moving_bounds() is None
    center, zoom = test.view()
    assert zoom < 20.0, "it should frame the static shapes rather than give up"
    assert abs(center.x) < 1.0
    world.destroy()
    del BaseTest.registry["_Test"]


def test_view_handles_an_empty_world():
    from box2d import World
    from box2d_testbed.base_test import BaseTest

    class Empty(BaseTest, category="_Test", name="Empty"):
        def setup(self):
            pass

    world = World()
    test = Empty(world)
    test.setup()

    center, zoom = test.view()
    assert zoom == 20.0, "an empty scenario should fall back, not divide by zero"
    world.destroy()
    del BaseTest.registry["_Test"]


def test_auto_zoom_stays_within_its_bounds():
    from box2d import World
    from box2d_testbed.base_test import BaseTest

    class Huge(BaseTest, category="_Test", name="Huge"):
        def setup(self):
            for x in (-5000, 5000):
                body = self.world.add_body(body_type="dynamic", position=(x, 0))
                body.add_box(10, 10)

    world = World()
    test = Huge(world)
    test.setup()
    _, zoom = test.view()

    assert zoom == BaseTest.MAX_AUTO_ZOOM
    world.destroy()
    del BaseTest.registry["_Test"]


def test_every_scenario_frames_its_moving_parts():
    """A scenario should not open looking at empty space."""
    from box2d import World
    from box2d_testbed.base_test import BaseTest

    for category, tests in BaseTest.registry.items():
        for name, test_cls in tests.items():
            world = World()
            test = test_cls(world)
            test.setup()
            center, zoom = test.view()
            bounds = test.moving_bounds()

            if bounds is not None:
                # Overlap, not centring: a scenario like Driving spreads its
                # bodies over 200m, and the right view is the car's end of it
                # rather than the midpoint of everything.
                (lower_x, lower_y), (upper_x, upper_y) = bounds
                view_lower_x, view_upper_x = (
                    center.x - zoom * 1.6,
                    center.x + zoom * 1.6,
                )
                view_lower_y, view_upper_y = center.y - zoom, center.y + zoom
                assert (
                    lower_x <= view_upper_x and upper_x >= view_lower_x
                ), f"{category}/{name} opens with its contents off screen"
                assert (
                    lower_y <= view_upper_y and upper_y >= view_lower_y
                ), f"{category}/{name} opens with its contents off screen"
            world.destroy()


# --- debug draw callbacks ---------------------------------------------------


def test_every_box2d_draw_callback_is_bound():
    """An unbound callback is silent, not fatal, so it goes unnoticed.

    b2DefaultDebugDraw installs a stub for each function pointer. Leaving one
    unassigned therefore does nothing at all rather than crashing, which is
    how the AABB toggle stayed dead after 3.2 moved bounds off draw_polygon
    onto their own DrawBoundsFcn.
    """
    from box2d._box2d import ffi, lib
    from box2d import DebugDraw, Vec2

    draw = DebugDraw()
    struct_callbacks = {
        name for name in dir(ffi.new("b2DebugDraw*")) if name.endswith("Fcn")
    }

    unbound = []
    for name in struct_callbacks:
        # A bound callback points at one of this module's trampolines; an
        # unbound one still points at Box2D's stub, so compare against a
        # freshly defaulted struct.
        default = lib.b2DefaultDebugDraw()
        if getattr(draw._debug_draw, name) == getattr(default, name):
            unbound.append(name)

    assert unbound == [], f"callbacks still pointing at Box2D's stub: {unbound}"


def test_aabb_toggle_actually_produces_bounds():
    """The toggle was wired to a callback Box2D no longer calls for bounds."""
    from box2d import DebugDraw, World

    class Recorder(DebugDraw):
        def __init__(self):
            super().__init__()
            self.bounds = []

        def draw_bounds(self, aabb, color):
            self.bounds.append(aabb)

    world = World()
    ground = world.add_body(position=(0, 0))
    ground.add_box(20, 1)
    ball = world.add_body(body_type="dynamic", position=(0, 5))
    ball.add_circle(radius=0.5)
    world.step(1 / 60, 4)

    recorder = Recorder()
    recorder.draw_aabbs = False
    world.draw(recorder)
    assert recorder.bounds == [], "bounds should be off by default"

    recorder.draw_aabbs = True
    world.draw(recorder)
    assert len(recorder.bounds) == 2, "one box per shape, static and dynamic alike"

    # The dynamic ball's box should surround it, with Box2D's fattening.
    ball_box = max(recorder.bounds, key=lambda aabb: aabb.lower.y)
    assert ball_box.lower.x < -0.5 and ball_box.upper.x > 0.5
    assert ball_box.lower.y < 4.5 and ball_box.upper.y > 5.5
    world.destroy()


def test_dynamic_shapes_reach_the_draw_callbacks():
    """Every scenario should hand over each of its moving shapes to be drawn."""
    from box2d import DebugDraw, World
    from box2d_testbed.base_test import BaseTest

    class Counter(DebugDraw):
        def __init__(self):
            super().__init__()
            self.solids = 0

        def draw_solid_polygon(self, *args):
            self.solids += 1

        def draw_solid_circle(self, *args):
            self.solids += 1

        def draw_solid_capsule(self, *args):
            self.solids += 1

    for category, tests in BaseTest.registry.items():
        for name, test_cls in tests.items():
            world = World()
            test = test_cls(world)
            test.setup()
            for _ in range(10):
                world.step(1 / 60, 4)
                test.after_step(1 / 60)

            moving_shapes = sum(
                len(body.shapes) for body in world.bodies if body.type != "static"
            )
            counter = Counter()
            world.draw(counter)
            assert counter.solids >= moving_shapes, (
                f"{category}/{name} drew {counter.solids} solid shapes "
                f"but has {moving_shapes} moving ones"
            )
            world.destroy()


# --- shader loading ---------------------------------------------------------


def test_draw_module_keeps_its_own_file_attribute():
    """A module's __file__ must be its own.

    Replacing `from OpenGL.GL import *` with an explicit list pulled in
    __file__ along with the GL names, because it is a module attribute rather
    than a GL one. That rebound draw.__file__ to PyOpenGL's, so every shader
    path resolved into site-packages and no shader loaded: solid shapes
    stopped rendering entirely while lines and points carried on.
    """
    from box2d_testbed import draw

    assert draw.__file__.endswith(
        os.path.join("box2d_testbed", "draw.py")
    ), f"draw.__file__ is {draw.__file__}, not its own path"


def test_every_shader_the_testbed_loads_exists():
    """The paths are built at runtime, so a missing file fails only on launch."""
    from box2d_testbed import draw

    package_dir = os.path.dirname(os.path.abspath(draw.__file__))
    source = pathlib.Path(package_dir, "draw.py").read_text()

    referenced = set(re.findall(r'"(\w+\.(?:vs|fs))"', source))
    assert referenced, "no shader files referenced; has the loading changed?"

    missing = [
        name
        for name in sorted(referenced)
        if not os.path.exists(os.path.join(package_dir, "shaders", name))
    ]
    assert missing == [], f"shaders referenced but not present: {missing}"


def test_shaders_are_packaged():
    """They are data files, so they must be declared to ship with the wheel."""
    config = pathlib.Path("pyproject.toml").read_text()
    assert (
        "shaders" in config or "package-data" in config or "*.vs" in config
    ), "shaders may not be included in the installed package"


# --- scenarios must survive being drawn --------------------------------------


class _StrictRenderer(DebugDraw):
    """A stand-in that touches its arguments exactly as the GL layer does.

    Scenario debug_draw() code was never exercised headlessly beyond being
    called, so anything it passed was accepted by a permissive test double and
    only failed against real OpenGL.
    """

    def __init__(self):
        super().__init__()
        self.calls = 0

    def _point(self, p):
        # Vec2 accepts any vector-like, exactly as DebugDrawGL does before
        # handing points to the GL batchers. Reading .x/.y afterwards is what
        # makes a None, a string or a wrong-length sequence fail here rather
        # than only against real OpenGL.
        self.calls += 1
        point = Vec2(p)
        return (point.x, point.y)

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


@pytest.mark.parametrize(
    "category,name",
    [
        (category, name)
        for category, tests in BaseTest.registry.items()
        for name in tests
    ],
)
def test_scenario_survives_being_drawn(category, name):
    """Run a scenario through a renderer as picky as the real one."""
    from box2d import World

    world = World()
    test = BaseTest.registry[category][name](world)
    test.setup()

    renderer = _StrictRenderer()
    # On, so the debug overlays are exercised too rather than skipped.
    for flag in ("draw_aabbs", "draw_joints", "draw_contacts", "draw_mass"):
        setattr(renderer, flag, True)

    try:
        for _ in range(20):
            world.step(1 / 60, 4)
            test.after_step(1 / 60)
            world.draw(renderer)
            test.debug_draw(renderer)
    finally:
        world.destroy()

    assert renderer.calls > 0, "nothing was drawn at all"


def test_the_gl_renderer_accepts_plain_tuples():
    """Scenario code writes (x, y); the GL batchers read .x and .y.

    Twenty of the forty-four scenarios passed tuples, and each crashed the
    testbed as soon as it was opened -- Wind died on
    draw_segment((0, 0), ...). The renderer normalises now, so this pins that
    it keeps doing so.

    GLDebugDraw needs an OpenGL context to construct, so the instance is built
    without __init__ and its batchers replaced by recorders. That exercises
    the real methods, which is the point: a test double of the renderer could
    normalise while the renderer itself stopped.
    """
    from box2d import Color
    from box2d_testbed.debug_draw_gl import GLDebugDraw

    class Batcher:
        def __init__(self):
            self.received = []

        def _record(self, *args):
            # Fails the same way draw.py would if a raw tuple got through.
            self.received.append([(a.x, a.y) for a in args if hasattr(a, "x")])

        add_line = add_point = add_circle = add_capsule = add_polygon = _record

    renderer = GLDebugDraw.__new__(GLDebugDraw)
    renderer.lines = Batcher()
    renderer.points = Batcher()
    renderer.circles = Batcher()
    renderer.solid_capsules = Batcher()
    renderer.debug_strings = []

    white = Color(255, 255, 255, 255)
    renderer.draw_segment((0, 0), (1, 2), white)
    renderer.draw_point((3, 4), 5.0, white)
    renderer.draw_circle((5, 6), 1.0, white)
    renderer.draw_solid_capsule((0, 0), (1, 0), 0.5, white)
    renderer.draw_string((7, 8), "hello", white)

    assert renderer.lines.received == [[(0.0, 0.0), (1.0, 2.0)]]
    assert renderer.points.received == [[(3.0, 4.0)]]
    assert renderer.circles.received == [[(5.0, 6.0)]]
    assert renderer.solid_capsules.received == [[(0.0, 0.0), (1.0, 0.0)]]

    position = renderer.debug_strings[0][0]
    assert (position.x, position.y) == (7.0, 8.0), "strings are placed later"

    # Vec2 must still work, since Box2D's own callbacks pass them.
    renderer.draw_segment(Vec2(1, 1), Vec2(2, 2), white)
    assert renderer.lines.received[-1] == [(1.0, 1.0), (2.0, 2.0)]


def test_our_menus_do_not_collide_with_hello_imgui_s():
    """hello_imgui adds its own menus, and a repeated name shows up twice.

    A "View" menu holding only Reset view appeared next to hello_imgui's own
    View menu, which holds the docking layout and themes. Neither knows about
    the other, so both render. That item is a button in the scenario panel
    now, but the check stays: the next menu added could collide too.
    """
    from imgui_bundle import hello_imgui

    source = pathlib.Path("src/box2d_testbed/testbed.py").read_text()
    ours = set(re.findall(r'imgui\.begin_menu\(\s*"([^"]+)"', source))
    assert ours, "no menus found; has the menu code moved?"

    params = hello_imgui.RunnerParams().imgui_window_params
    reserved = set()
    if params.show_menu_view:
        reserved.add("View")
    if params.show_menu_app:
        reserved.add(params.menu_app_title or "App")

    # show_menu_app is turned off in TestbedApp, so only View is really taken;
    # read it from the source rather than assuming.
    if "show_menu_app = False" in source:
        reserved.discard("App")
        reserved.discard(params.menu_app_title or "App")

    assert (
        ours & reserved == set()
    ), f"menu name(s) {sorted(ours & reserved)} clash with hello_imgui's own"


def test_reset_view_button_reframes_the_scenario():
    """The Reset View button is how you recover after panning away."""
    from box2d import World
    from box2d_testbed.testbed_state import state

    world = World()
    test = BaseTest.registry["Shapes"]["Chain Materials"](world)
    test.setup()
    test.apply_view()
    framed = (state.center, state.scale)

    state.center, state.scale = (500.0, -400.0), 3.0
    # Pressing a button in the UI bumps its value, which fires the callback.
    test.reset_view = (test.reset_view or 0) + 1

    assert (state.center, state.scale) == framed
    world.destroy()


def test_reset_does_not_move_the_camera():
    """Restarting a scenario keeps the view you set up, as in the C++ testbed."""
    from box2d import World
    from box2d_testbed.testbed_state import state

    world = World()
    test = BaseTest.registry["Stacking"]["Card House"](world)
    test.setup()

    state.center, state.scale = (500.0, -400.0), 3.0
    test.reset = (test.reset or 0) + 1

    assert (state.center, state.scale) == ((500.0, -400.0), 3.0)
    world.destroy()


def test_reset_and_reset_view_are_the_first_two_controls():
    """They are declared on BaseTest, so every scenario gets them in order."""
    from box2d import World

    world = World()
    test = BaseTest.registry["Shapes"]["Wind"](world)
    test.setup()

    names = [name for name, _ in test.ui_elements]
    assert names[:2] == ["reset", "reset_view"]
    assert all(
        element.type == "button" for _, element in test.ui_elements[:2]
    ), "they share a row only while both are buttons"
    world.destroy()


# --- copying the current view -----------------------------------------------


def test_view_declaration_is_pasteable_source():
    """The status bar's Copy button exists to move numbers into the class."""
    from box2d_testbed.base_test import format_view_declaration

    declaration = format_view_declaration(Vec2(0.75, 0.9), 4.0)
    assert declaration == "camera_center = (0.75, 0.9)\ncamera_zoom = 4.0"


def test_view_declaration_accepts_whatever_the_camera_holds():
    """state.center is a tuple after framing and a Vec2 after panning."""
    from box2d_testbed.base_test import format_view_declaration

    assert format_view_declaration((1.0, 2.0), 3.0) == format_view_declaration(
        Vec2(1.0, 2.0), 3.0
    )


def test_view_declaration_rounds_off_panning_noise():
    """Dragging leaves long floats that nobody wants pasted into source."""
    from box2d_testbed.base_test import format_view_declaration

    declaration = format_view_declaration(Vec2(-39.5123456, 19.80000001), 27.500001)
    assert declaration == "camera_center = (-39.51, 19.8)\ncamera_zoom = 27.5"


def test_view_declaration_round_trips_into_a_scenario():
    """Pasting the output back must actually reproduce the framing."""
    from box2d import World
    from box2d_testbed.base_test import format_view_declaration

    declaration = format_view_declaration(Vec2(3.25, -1.5), 7.5)

    namespace = {}
    exec(declaration, {}, namespace)

    class Pasted(BaseTest, category="_Test", name="Pasted"):
        camera_center = namespace["camera_center"]
        camera_zoom = namespace["camera_zoom"]

        def setup(self):
            body = self.world.add_body(body_type="dynamic", position=(3, -1))
            body.add_box(1, 1)

    world = World()
    test = Pasted(world)
    test.setup()
    center, zoom = test.view()

    assert (center.x, center.y) == (3.25, -1.5)
    assert zoom == 7.5
    world.destroy()
    del BaseTest.registry["_Test"]


def test_status_bar_reports_the_view_it_would_copy():
    """The readout and the button must not drift apart."""
    source = pathlib.Path("src/box2d_testbed/testbed.py").read_text()
    status = source[
        source.index("def show_status") : source.index("def show_test_list")
    ]

    assert "state.center" in status and "state.scale" in status
    assert "format_view_declaration(state.center, state.scale)" in status
    assert "set_clipboard_text" in status
