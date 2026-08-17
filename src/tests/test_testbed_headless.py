# tests/test_testbed_headless.py
"""Run the whole testbed with no window and no GL.

The gui tests need a display, so they are excluded by default and never run
in CI -- which left the app shell, the docking, the panels and the renderer
untested anywhere it matters. The imgui renderer changes that: it draws
through imgui's draw list rather than OpenGL, so hello_imgui's null backends
can run the entire app with no display at all.

These are the same checks as the gui tests, without needing a screen.
"""

import os

import pytest

# These run the app itself, on hello_imgui's null backends. Without the GUI
# stack there is nothing to run, so they skip rather than error -- CI and a
# plain `pip install -e .[dev]` both lack it.
pytest.importorskip("imgui_bundle", reason="needs the testbed extra")


def run_headless(frame_count, on_frame=None, renderer="imgui"):
    """Run the testbed on null backends for a set number of frames.

    Returns:
        tuple: (frames rendered, the app).
    """
    from imgui_bundle import hello_imgui, imgui

    os.environ["BOX2D_TESTBED_RENDERER"] = renderer
    import box2d_testbed.testbed as testbed_module

    app = testbed_module.TestbedApp()
    runner = app.runner_params
    runner.platform_backend_type = hello_imgui.PlatformBackendType.null
    runner.renderer_backend_type = hello_imgui.RendererBackendType.null

    previous_post_init = runner.callbacks.post_init

    def post_init():
        if previous_post_init is not None:
            previous_post_init()
        # The null renderer uploads no textures, so imgui refuses to draw
        # against an unbuilt font atlas. Declaring that textures are handled
        # dynamically is what lets a backend with no upload path run at all.
        imgui.get_io().backend_flags |= imgui.BackendFlags_.renderer_has_textures

    rendered = {"count": 0}
    previous_pre_frame = runner.callbacks.pre_new_frame

    def pre_new_frame():
        if previous_pre_frame is not None:
            previous_pre_frame()
        rendered["count"] += 1
        if on_frame is not None:
            on_frame(app, rendered["count"])
        if rendered["count"] >= frame_count:
            runner.app_shall_exit = True

    runner.callbacks.post_init = post_init
    runner.callbacks.pre_new_frame = pre_new_frame
    app.run()
    return rendered["count"], app


def test_the_testbed_runs_without_a_display():
    """The whole app: docking, panels, physics and drawing, no screen."""
    frames, app = run_headless(40)

    assert frames >= 40
    assert type(app.debug_draw).__name__ == "ImGuiDebugDraw"


def test_the_gl_renderer_still_needs_a_context():
    """Which is the reason the imgui renderer exists.

    Not a complaint about the GL renderer -- it is faster. But it cannot run
    where there is no GL, and that includes CI and a browser.
    """
    with pytest.raises(Exception):
        run_headless(5, renderer="opengl")


def test_scenarios_can_be_switched_headlessly():
    """Every scenario draws different primitives; this reaches paths one
    scenario alone never touches."""
    from box2d_testbed.base_test import BaseTest
    from box2d_testbed.testbed_state import state

    ordered = [
        test_cls
        for tests in BaseTest.get_all_tests().values()
        for test_cls in tests.values()
    ]
    chosen = ordered[:: max(1, len(ordered) // 8)][:8]

    def switch(app, frame):
        if frame % 6 == 0:
            index = frame // 6
            if index < len(chosen):
                state.current_test_cls = chosen[index]
                app.simulation.init_test()

    frames, _ = run_headless(6 * (len(chosen) + 1), switch)
    assert frames > 0


def test_every_overlay_draws_headlessly():
    """All fifteen debug-draw flags at once, through the imgui renderer."""
    from box2d_testbed.testbed_state import state

    def enable_everything(app, frame):
        if frame == 3:
            for key, _, _ in state.show_dd.get_current():
                setattr(state.show_dd, key, True)

    frames, _ = run_headless(30, enable_everything)
    assert frames >= 30


def test_the_renderer_choice_is_honoured():
    from box2d_testbed.debug_draw_gl import GLDebugDraw
    from box2d_testbed.debug_draw_imgui import ImGuiDebugDraw
    from box2d_testbed.testbed import TestbedApp

    # The class, not an instance: constructing a GLDebugDraw compiles
    # shaders, which needs the context this test does not have.
    os.environ["BOX2D_TESTBED_RENDERER"] = "imgui"
    assert TestbedApp.debug_draw_class() is ImGuiDebugDraw

    os.environ["BOX2D_TESTBED_RENDERER"] = "opengl"
    assert TestbedApp.debug_draw_class() is GLDebugDraw

    os.environ.pop("BOX2D_TESTBED_RENDERER", None)
    assert TestbedApp.debug_draw_class() is GLDebugDraw, "OpenGL is the default"

    os.environ["BOX2D_TESTBED_RENDERER"] = "nonsense"
    with pytest.raises(SystemExit, match="unknown renderer"):
        TestbedApp.debug_draw_class()

    os.environ.pop("BOX2D_TESTBED_RENDERER", None)


def test_colours_pack_the_way_imgui_wants_them():
    """imgui puts alpha high and red low, the reverse of Box2D's RGB."""
    from box2d.debug_draw import Color
    from box2d_testbed.debug_draw_imgui import pack_color

    assert pack_color(Color(0xAA, 0xBB, 0xCC, 0xDD)) == 0xDDCCBBAA
    # Alpha can be overridden, which is how fills are made translucent.
    assert pack_color(Color(0x11, 0x22, 0x33, 0xFF), 0x80) == 0x80332211


def test_what_is_drawn_moves_as_the_world_does():
    """A renderer that drew the first frame forever would pass every test
    above: they check that drawing happens, not that it changes.

    So this records the screen position of a falling body each frame and
    checks it descends, and that it descends in step with the physics rather
    than drifting on its own.
    """
    from box2d import World
    from box2d_testbed.base_test import BaseTest
    from box2d_testbed.testbed_state import state

    class Falling(BaseTest, category="_Headless", name="Falling"):
        camera_center = (0, 5)
        camera_zoom = 12.0

        def setup(self):
            ground = self.world.add_body(position=(0, 0))
            ground.add_box(20, 1)
            self.ball = self.world.add_body(body_type="dynamic", position=(0, 10))
            self.ball.add_circle(radius=0.5)

    drawn_y = []
    world_y = []

    def sample(app, frame):
        renderer = app.debug_draw
        if frame == 1:
            state.current_test_cls = Falling
            app.simulation.init_test()
            return
        test = state.current_test_obj
        if isinstance(test, Falling):
            # Physics is driven by the wall clock, and with no vsync the null
            # backend runs these frames in a few milliseconds -- so left to
            # the timer the ball would barely move. Stepping it here makes the
            # test about the renderer tracking the world, which is the point.
            app.simulation.update_physics()
            # Where the renderer would put it, and where it actually is.
            drawn_y.append(renderer.to_screen(test.ball.position)[1])
            world_y.append(test.ball.position.y)

    try:
        run_headless(60, sample)
    finally:
        del BaseTest.registry["_Headless"]

    assert len(drawn_y) > 30, "the scenario never ran"
    assert len(set(round(value, 1) for value in drawn_y)) > 5, "nothing moved"

    # Screen y grows downwards, so a falling body's drawn position increases
    # while its world position decreases.
    assert drawn_y[-1] > drawn_y[0], "the ball should have been drawn lower"
    assert world_y[-1] < world_y[0], "and should actually have fallen"

    # The two must agree: a fixed camera means the drawn distance is the
    # world distance times a constant scale.
    world_drop = world_y[0] - world_y[-1]
    drawn_drop = drawn_y[-1] - drawn_y[0]
    scale = drawn_drop / world_drop
    for index in range(1, len(drawn_y)):
        expected = drawn_y[0] + (world_y[0] - world_y[index]) * scale
        assert abs(drawn_y[index] - expected) < 1.0, (
            f"frame {index}: drawn at {drawn_y[index]:.1f}, "
            f"but the world says {expected:.1f}"
        )


# --- rounded shapes ----------------------------------------------------------


def polygon_area(points):
    total = 0.0
    for index in range(len(points)):
        x0, y0 = points[index]
        x1, y1 = points[(index + 1) % len(points)]
        total += x0 * y1 - x1 * y0
    return abs(total) / 2.0


def polygon_perimeter(points):
    import math

    return sum(
        math.hypot(
            points[(index + 1) % len(points)][0] - points[index][0],
            points[(index + 1) % len(points)][1] - points[index][1],
        )
        for index in range(len(points))
    )


SQUARE = [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)]
TRIANGLE = [(0.0, 0.0), (120.0, 0.0), (60.0, 90.0)]


@pytest.mark.parametrize("radius", [1.0, 5.0, 20.0])
@pytest.mark.parametrize(
    "polygon,name",
    [(SQUARE, "square"), (SQUARE[::-1], "square reversed"), (TRIANGLE, "triangle")],
)
def test_growing_a_polygon_has_the_area_a_minkowski_sum_should(polygon, name, radius):
    """A convex shape grown by a disc has an area that is known exactly.

    area + perimeter * radius + pi * radius^2. That makes this checkable
    rather than a matter of looking at it, and it catches the mistake that
    is easy to make here: growing the shape inwards. The first version had
    the normals reversed, which shrank every rounded shape instead --
    visibly wrong on screen, but only once you knew to look.
    """
    import math

    from box2d_testbed.debug_draw_imgui import expand_polygon

    grown = expand_polygon(polygon, radius, segments_per_corner=64)
    expected = (
        polygon_area(polygon)
        + polygon_perimeter(polygon) * radius
        + math.pi * radius * radius
    )
    assert polygon_area(grown) == pytest.approx(expected, rel=0.001)


def test_growing_a_polygon_works_for_either_winding():
    """Screen space flips y, so Box2D's winding cannot be assumed."""
    from box2d_testbed.debug_draw_imgui import expand_polygon

    clockwise = expand_polygon(SQUARE, 10.0, segments_per_corner=32)
    anticlockwise = expand_polygon(SQUARE[::-1], 10.0, segments_per_corner=32)

    assert polygon_area(clockwise) == pytest.approx(polygon_area(anticlockwise))


def test_growing_by_nothing_changes_nothing():
    from box2d_testbed.debug_draw_imgui import expand_polygon

    assert expand_polygon(SQUARE, 0.0) == SQUARE
    assert expand_polygon(SQUARE, -1.0) == SQUARE


def test_a_degenerate_polygon_is_left_alone():
    """Fewer than three points is not a polygon to grow."""
    from box2d_testbed.debug_draw_imgui import expand_polygon

    assert expand_polygon([(0.0, 0.0), (1.0, 1.0)], 5.0) == [(0.0, 0.0), (1.0, 1.0)]


def test_the_grown_outline_stays_convex():
    """add_convex_poly_filled will render a concave outline wrongly."""
    import math

    from box2d_testbed.debug_draw_imgui import expand_polygon

    grown = expand_polygon(TRIANGLE, 15.0, segments_per_corner=8)
    count = len(grown)
    signs = []
    for index in range(count):
        ax, ay = grown[index]
        bx, by = grown[(index + 1) % count]
        cx, cy = grown[(index + 2) % count]
        cross = (bx - ax) * (cy - by) - (by - ay) * (cx - bx)
        if abs(cross) > 1e-9:
            signs.append(cross > 0)
    assert len(set(signs)) == 1, "the outline turns both ways, so it is not convex"


def test_a_rounded_shape_is_drawn_once_not_layered():
    """The fill and the stroke used to overlap.

    With translucent colours that blended twice and drew a dark band inside
    every edge, and imgui's joins left notches on the outside of the
    corners. One grown outline, filled once, has neither problem -- so the
    renderer should submit exactly one fill per polygon.
    """
    from box2d import Transform, Vec2
    from box2d.debug_draw import Color
    from box2d_testbed.debug_draw_imgui import ImGuiDebugDraw

    class Recorder:
        def __init__(self):
            self.fills = 0
            self.polylines = 0

        def add_convex_poly_filled(self, points, color):
            self.fills += 1

        def add_polyline(self, points, color, thickness, flags):
            self.polylines += 1

    renderer = ImGuiDebugDraw.__new__(ImGuiDebugDraw)
    renderer._lower = Vec2(0.0, 0.0)
    renderer._scale_x = renderer._scale_y = 10.0
    renderer._origin_x = renderer._origin_y = 0.0
    renderer._height = 500.0
    recorder = Recorder()
    renderer._draw_list = recorder

    square = [Vec2(-1, -1), Vec2(1, -1), Vec2(1, 1), Vec2(-1, 1)]
    renderer.draw_solid_polygon(Transform(Vec2(0, 0)), square, 0.2, Color(255, 0, 0))

    assert recorder.fills == 1, "a rounded shape should be filled exactly once"
    assert recorder.polylines == 1, "and outlined once, with no thick stroke pass"


def test_every_primitive_reaches_the_installed_draw_list():
    """The renderer's calls, against a real ImDrawList rather than a stand-in.

    imgui_bundle swapped add_polyline's thickness and flags arguments between
    1.92.4, which is the version Pyodide ships, and 1.92.900. The order that
    was right on a desktop raised TypeError in a browser, and nothing failed:
    Box2D calls the renderer through a CFFI callback, which prints the
    exception and carries on, so the testbed ran on and drew every polygon
    with no outline at all.

    A recorder cannot catch that -- it accepts whatever it is handed. Only the
    installed binding knows what it takes, so the primitives are driven
    against it here, where a rejected call is a failure.
    """
    from imgui_bundle import imgui

    from box2d import AABB, Transform, Vec2
    from box2d.debug_draw import Color
    from box2d_testbed.debug_draw_imgui import ImGuiDebugDraw

    context = imgui.create_context()
    try:
        io = imgui.get_io()
        io.display_size = imgui.ImVec2(200.0, 200.0)
        io.delta_time = 1.0 / 60.0
        # As in run_headless: with no backend there is no font upload path.
        io.backend_flags |= imgui.BackendFlags_.renderer_has_textures
        imgui.new_frame()

        renderer = ImGuiDebugDraw()
        renderer._draw_list = imgui.get_background_draw_list()
        renderer._scale_x = renderer._scale_y = 10.0
        renderer._height = 200.0

        white = Color(255, 255, 255, 255)
        identity = Transform(Vec2(0.0, 0.0))
        square = [Vec2(-1, -1), Vec2(1, -1), Vec2(1, 1), Vec2(-1, 1)]

        renderer.draw_polygon(identity, square, white)
        renderer.draw_solid_polygon(identity, square, 0.0, white)
        renderer.draw_solid_polygon(identity, square, 0.2, white)
        renderer.draw_circle(Vec2(0.0, 0.0), 1.0, white)
        renderer.draw_solid_circle(identity, Vec2(0.0, 0.0), 1.0, white)
        renderer.draw_solid_capsule(Vec2(-1.0, 0.0), Vec2(1.0, 0.0), 0.5, white)
        renderer.draw_segment(Vec2(-1.0, 0.0), Vec2(1.0, 0.0), white)
        renderer.draw_point(Vec2(0.0, 0.0), 5.0, white)
        renderer.draw_bounds(AABB(lower=Vec2(-1, -1), upper=Vec2(1, 1)), white)
        renderer.draw_transform(identity)
        # Text is held until end_frame, which is the only add_text call.
        renderer.draw_string(Vec2(0.0, 0.0), "held until end_frame", white)
        renderer.end_frame()
    finally:
        # imgui's own frame, not the renderer's: left open, it trips the
        # "forgot to call Render or EndFrame" assertion in whatever runs the
        # app next, which for a long time was nothing.
        imgui.end_frame()
        imgui.destroy_context(context)


def test_the_testbed_imports_without_pyopengl():
    """A browser has no PyOpenGL, and the imgui renderer does not need one.

    The package used to import OpenGL at module scope, to set ERROR_CHECKING
    before anything pulled in OpenGL.GL. Sound reasoning, but it made the
    whole package unimportable where there is no PyOpenGL, however lazy
    everything downstream was.
    """
    import subprocess
    import sys
    import textwrap

    program = textwrap.dedent(
        """
        import sys

        # Nothing may import PyOpenGL during this. find_spec, not find_module:
        # the latter was removed in Python 3.12, so a finder defining only it
        # is ignored -- this test blocked nothing at all until now.
        class Blocked:
            def find_spec(self, name, path=None, target=None):
                if name == "OpenGL" or name.startswith("OpenGL."):
                    raise ImportError(f"{name} is not available here")
                return None

        sys.meta_path.insert(0, Blocked())

        assert __import__("importlib").util.find_spec is not None
        try:
            import OpenGL  # noqa: F401
            raise AssertionError("the block did not work, so this proves nothing")
        except ImportError:
            pass

        import box2d_testbed
        import box2d_testbed.testbed
        from box2d_testbed.debug_draw_imgui import ImGuiDebugDraw
        from box2d_testbed.camera import Camera

        assert box2d_testbed.testbed.TestbedApp.debug_draw_class is not None
        print("OK")
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", program], capture_output=True, text=True
    )
    assert (
        "OK" in result.stdout
    ), f"the testbed cannot be imported without PyOpenGL:\n{result.stderr[-1500:]}"


def test_the_testbed_defaults_to_a_thread_count_the_build_supports():
    """The testbed defaulted to four threads regardless of the build.

    A WebAssembly build has no task scheduler and raises rather than
    degrading, so the testbed could not start in a browser at all -- the
    first thing it did was ask for four threads.
    """
    from box2d import HAS_THREADS, World
    from box2d_testbed.testbed_state import state

    assert state.threads >= 1
    if not HAS_THREADS:
        assert state.threads == 1, "a build with no scheduler must default to one"

    # Whatever the default is, a world must be constructible with it.
    world = World(threads=state.threads)
    world.destroy()


def test_the_thread_slider_is_hidden_when_there_is_no_scheduler():
    """Offering a control that raises when used is worse than not offering it."""
    import ast
    import pathlib

    source = pathlib.Path("src/box2d_testbed/testbed.py").read_text()
    tree = ast.parse(source)
    controls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "show_controls"
    ]
    assert controls, "show_controls not found"
    body = ast.unparse(controls[0])

    assert "Threads" in body
    assert "HAS_THREADS" in body, "the thread control is offered unconditionally"


@pytest.fixture
def scenario_dir(tmp_path, monkeypatch):
    """A scenario directory of this test's own, and a registry put back after.

    The registry is global and these tests load scenarios into it, which would
    otherwise leave scenarios behind for whatever runs next to trip over.
    """
    from box2d_testbed.base_test import BaseTest

    # Imported for the side effect of registering the builtins, before the
    # snapshot rather than after: run_headless is what would otherwise pull
    # them in, and a snapshot taken while the registry was still empty would
    # have this fixture delete every scenario in the process on the way out.
    import box2d_testbed.testbed_simulation  # noqa: F401

    monkeypatch.setenv("BOX2D_TESTBED_SCENARIOS", str(tmp_path))
    snapshot = {c: dict(tests) for c, tests in BaseTest.registry.items()}
    try:
        yield tmp_path
    finally:
        for category in list(BaseTest.registry):
            if category not in snapshot:
                del BaseTest.registry[category]
        for category, tests in snapshot.items():
            current = BaseTest.registry.setdefault(category, {})
            current.clear()
            current.update(tests)


EDITED_SCENARIO = """from box2d_testbed.base_test import BaseTest, UI


class Edited(BaseTest, category="User", name="edited"):
    def setup(self):
        self.world.new_body().static().segment((-10, 0), (10, 0)).build()
        for i in range(3):
            self.world.new_body().dynamic().position(i, 5).box(1, 1).build()
"""


def body_count(app):
    return len(list(app.simulation.world.bodies))


def test_the_editing_loop_rebuilds_the_world_from_the_edited_source(scenario_dir):
    """New, type, save, watch: the whole point of the editor.

    Driven through the running app rather than the loader alone, because what
    is being checked is that a save reaches the world on screen.
    """
    from box2d_testbed.testbed_state import state

    seen = {}

    def script(app, frame):
        if frame == 3:
            app.editor.new()
            seen["opened"] = app.editor.ref.name
            seen["running"] = state.current_test_cls.name
            seen["template_bodies"] = body_count(app)
        elif frame == 6:
            app.editor.editor.set_text(EDITED_SCENARIO)
            seen["dirty"] = app.editor.dirty
            app.editor.save()
        elif frame == 9:
            seen["after_save"] = (state.current_test_cls.name, body_count(app))
            seen["still_dirty"] = app.editor.dirty
            seen["error"] = state.scenario_error

    frames, _ = run_headless(14, script)

    assert frames >= 14, "the app kept running throughout"
    assert seen["opened"] == "untitled"
    # The template is built and put on screen, not merely written out.
    assert seen["running"] == "untitled"
    assert seen["template_bodies"] == 2, "the template's ground and its one box"
    assert seen["dirty"] is True
    assert seen["after_save"] == ("edited", 4), "the edited scenario, in the world"
    assert seen["still_dirty"] is False
    assert seen["error"] is None
    assert "class Edited" in (scenario_dir / "untitled.py").read_text()


def test_a_save_that_will_not_compile_leaves_the_running_scene_alone(scenario_dir):
    """Which is the whole reason the loader reports instead of raising: the
    editor holding the fix is inside the app that would have died."""
    from box2d_testbed.testbed_state import state

    seen = {}

    def script(app, frame):
        if frame == 3:
            app.editor.new()
        elif frame == 6:
            app.editor.editor.set_text("class Broken(:\n")
            app.editor.save()
        elif frame == 9:
            seen["message"] = app.editor.message
            seen["is_error"] = app.editor.message_is_error
            seen["running"] = state.current_test_cls.name
            seen["bodies"] = body_count(app)
            # Sampled here rather than after the run: the recovery below
            # overwrites it.
            seen["on_disk"] = (scenario_dir / "untitled.py").read_text()
        elif frame == 12:
            # And the fix takes hold without restarting anything.
            app.editor.editor.set_text(EDITED_SCENARIO)
            app.editor.save()
        elif frame == 15:
            seen["recovered"] = (state.current_test_cls.name, body_count(app))

    frames, _ = run_headless(20, script)

    assert frames >= 20
    assert seen["is_error"] is True
    assert "invalid syntax" in seen["message"]
    assert seen["running"] == "untitled", "still the scenario that worked"
    assert seen["bodies"] == 2, "and its world was not torn down"
    # Saving writes first and loads second, so the broken text is not lost.
    assert seen["on_disk"] == "class Broken(:\n"
    assert seen["recovered"] == ("edited", 4)


def test_a_scenario_that_raises_while_building_does_not_take_the_app_down(
    scenario_dir,
):
    """The other half of it: source that imports cleanly and then throws."""
    from box2d_testbed.testbed_state import state

    seen = {}
    boom = (
        "from box2d_testbed.base_test import BaseTest\n\n\n"
        'class Boom(BaseTest, category="User", name="boom"):\n'
        "    def setup(self):\n"
        "        raise ValueError('kaboom')\n"
    )

    def script(app, frame):
        if frame == 3:
            app.editor.new()
        elif frame == 6:
            app.editor.editor.set_text(boom)
            app.editor.save()
        elif frame == 9:
            seen["loaded"] = app.editor.message
            seen["error"] = state.scenario_error
            seen["object"] = state.current_test_obj
        elif frame == 12:
            app.editor.editor.set_text(EDITED_SCENARIO)
            app.editor.save()
        elif frame == 15:
            seen["recovered"] = (state.current_test_cls.name, state.scenario_error)

    frames, _ = run_headless(20, script)

    assert frames >= 20, "the window survived a scenario that raised"
    assert seen["loaded"] == "loaded boom", "the file itself loaded fine"
    assert "ValueError: kaboom" in seen["error"]
    assert seen["object"] is None, "there is no half-built scenario to drive"
    assert seen["recovered"] == ("edited", None)


def test_a_hook_that_raises_is_reported_once_and_then_left_alone(scenario_dir):
    """A broken after_step must neither kill the app nor print every frame."""
    from box2d_testbed.testbed_state import state

    seen = {}
    broken_hook = (
        "from box2d_testbed.base_test import BaseTest\n\n\n"
        'class Hook(BaseTest, category="User", name="hook"):\n'
        "    def setup(self):\n"
        "        self.steps = 0\n"
        "        self.world.new_body().static().segment((-5, 0), (5, 0)).build()\n"
        "    def after_step(self, dt):\n"
        "        self.steps += 1\n"
        "        raise RuntimeError('every step')\n"
    )

    def script(app, frame):
        if frame == 3:
            app.editor.new()
        elif frame == 6:
            app.editor.editor.set_text(broken_hook)
            app.editor.save()
        elif frame > 6:
            # Step it by hand: the physics timer is driven by the wall clock,
            # and these frames go by too fast for it to fire on its own.
            app.simulation.update_physics()
        if frame == 20:
            seen["error"] = state.scenario_error
            seen["calls"] = state.current_test_obj.steps
            seen["scene"] = body_count(app)

    frames, _ = run_headless(24, script)

    assert frames >= 24
    assert "RuntimeError: every step" in seen["error"]
    assert seen["calls"] == 1, "called once, then not again"
    assert seen["scene"] == 1, "and the scene it built is still there to look at"


def test_the_editor_and_console_panels_draw(scenario_dir):
    """Both panels, drawn by the real app for real frames.

    The rest of these tests call into the editor and the console directly, so
    without this their gui functions would never run at all. The editor has to
    be focused first: it opens as a background tab, and imgui does not call the
    gui function of a tab nobody can see -- which would make this vacuous.
    """
    seen = {}
    drawn = {"editor": 0, "console": 0}

    def script(app, frame):
        if frame == 1:
            editor_gui, console_gui = app.editor.gui, app.console.gui

            def count(name, wrapped):
                def counted():
                    drawn[name] += 1
                    wrapped()

                return counted

            # Rebuilt because the layout holds the functions it was given.
            app.editor.gui = count("editor", editor_gui)
            app.console.gui = count("console", console_gui)
            app.runner_params.docking_params = app.create_layout()
        elif frame == 4:
            app.editor.new()
            app.focus_editor()
            app.console.submit("len(list(world.bodies))")
        elif frame == 8:
            # A builtin, which draws the read-only path and the picker's
            # second group.
            builtin = next(r for r in app.editor.refs() if r.name == "tb_bodies")
            app.editor.open(builtin)
            seen["read_only"] = app.editor.editor.is_read_only_enabled()
        elif frame == 11:
            app.console.submit("no_such_name")
            seen["console"] = [text for text, _ in app.console.lines]

    frames, _ = run_headless(18, script)

    assert frames >= 18
    assert drawn["editor"] > 4, f"the editor panel hardly drew: {drawn}"
    assert drawn["console"] > 4, f"the console panel hardly drew: {drawn}"
    assert seen["read_only"] is True, "a builtin cannot be typed into"
    assert "2" in seen["console"], "the console saw the template's two bodies"
    assert any("NameError" in line for line in seen["console"])


def test_ctrl_s_saves_the_scenario_being_edited(scenario_dir):
    """The shortcut the README documents, driven as a real key press.

    Only while the editor has the keyboard, which is why it is pressed after
    focusing it: the same chord over the simulation must not reach the editor.
    """
    from imgui_bundle import imgui

    seen = {}

    def script(app, frame):
        if frame == 3:
            app.editor.new()
            app.focus_editor()
        elif frame == 6:
            app.editor.editor.set_text("# edited by hand\n" + app.editor.loaded_text)
            seen["dirty"] = app.editor.dirty
        elif frame == 7:
            imgui.get_io().add_key_event(imgui.Key.mod_ctrl, True)
            imgui.get_io().add_key_event(imgui.Key.s, True)
        elif frame == 8:
            imgui.get_io().add_key_event(imgui.Key.s, False)
            imgui.get_io().add_key_event(imgui.Key.mod_ctrl, False)
            seen["dirty_after"] = app.editor.dirty
            seen["message"] = app.editor.message

    frames, _ = run_headless(12, script)

    assert frames >= 12
    assert seen["dirty"] is True, "the buffer was changed"
    assert seen["dirty_after"] is False, "and Ctrl+S saved it"
    assert seen["message"] == "loaded untitled", "and loaded it"
    assert (scenario_dir / "untitled.py").read_text().startswith("# edited by hand")


def test_the_running_builtin_can_be_opened_and_forked(scenario_dir):
    """How a scenario of your own usually starts: from one that already works.

    The builtin opens read-only, the fork is writable, and the fork's scenarios
    are renamed so it appears beside the original rather than replacing it.
    """
    from box2d_testbed.base_test import BaseTest
    from box2d_testbed.testbed_state import state

    seen = {}

    def script(app, frame):
        if frame == 3:
            state.current_test_cls = BaseTest.registry["Bodies"]["Body Type"]
            app.simulation.init_test()
        elif frame == 5:
            app.editor.open_current_scenario()
            seen["opened"] = app.editor.ref.name
            seen["writable"] = app.editor.ref.writable
        elif frame == 7:
            app.editor.fork()
            seen["fork"] = app.editor.ref.name
            seen["fork_writable"] = app.editor.ref.writable
            seen["running"] = state.current_test_cls.name
            seen["original_kept"] = "Body Type" in BaseTest.registry["Bodies"]
            seen["copy_registered"] = "Body Type copy" in BaseTest.registry["Bodies"]

    frames, _ = run_headless(12, script)

    assert frames >= 12
    assert seen["opened"] == "tb_bodies", "the file the running scenario came from"
    assert seen["writable"] is False, "a builtin is not edited in place"
    assert seen["fork"] == "tb_bodies_copy"
    assert seen["fork_writable"] is True
    assert seen["running"] == "Body Type copy", "the fork is what you are now editing"
    assert seen["original_kept"], "and the builtin is still there beside it"
    assert seen["copy_registered"]
    # A standalone file: the builtin's relative imports would not resolve.
    assert (
        "from box2d_testbed.base_test import"
        in (scenario_dir / "tb_bodies_copy.py").read_text()
    )


def test_deleting_a_scenario_takes_it_out_of_the_panel_too(scenario_dir):
    """Not just off disk: the class it registered has to go with it, or the
    Tests panel offers a scenario whose file is gone."""
    from box2d_testbed.base_test import BaseTest
    from box2d_testbed.testbed_state import state

    seen = {}

    def script(app, frame):
        if frame == 3:
            app.editor.new()
        elif frame == 6:
            seen["before"] = "untitled" in BaseTest.registry.get("User", {})
            app.editor.delete()
        elif frame == 9:
            seen["after"] = "untitled" in BaseTest.registry.get("User", {})
            seen["file"] = (scenario_dir / "untitled.py").exists()
            seen["ref"] = app.editor.ref
            seen["running"] = state.current_test_cls.name
            seen["error"] = state.scenario_error

    frames, _ = run_headless(14, script)

    assert frames >= 14
    assert seen["before"] is True
    assert seen["after"] is False, "the scenario is out of the registry"
    assert seen["file"] is False
    assert seen["ref"] is None, "and nothing is open in the editor"
    # It was the running scenario, so something else had to be put on screen.
    assert seen["running"] != "untitled"
    assert seen["error"] is None, "whatever replaced it built cleanly"


def test_scenarios_saved_earlier_are_there_at_the_next_start(scenario_dir):
    """The point of saving to a file: it is still there tomorrow.

    Startup loading happens in TestbedSimulation, before the editor exists, so
    a saved scenario is in the Tests panel whether or not the editor is opened.
    """
    from box2d_testbed.base_test import BaseTest
    from box2d_testbed.testbed_state import state

    (scenario_dir / "kept.py").write_text(EDITED_SCENARIO)
    # One that will not load, which must not keep the other out or stop the app.
    (scenario_dir / "rotten.py").write_text("class Broken(:\n")

    seen = {}

    def script(app, frame):
        if frame == 3:
            seen["registered"] = "edited" in BaseTest.registry.get("User", {})
            seen["rotten_skipped"] = len(BaseTest.registry.get("User", {}))
            # And it is a scenario like any other: selectable from the panel.
            state.current_test_cls = BaseTest.registry["User"]["edited"]
            app.simulation.init_test()
        elif frame == 6:
            seen["running"] = state.current_test_cls.name
            seen["bodies"] = body_count(app)
            seen["error"] = state.scenario_error

    frames, _ = run_headless(10, script)

    assert frames >= 10, "a rotten scenario file did not stop the testbed starting"
    assert seen["registered"] is True
    assert seen["rotten_skipped"] == 1, "the broken one was skipped, not registered"
    assert seen["running"] == "edited"
    assert seen["bodies"] == 4
    assert seen["error"] is None


def test_the_console_draws_its_prompt_completions_and_search(scenario_dir):
    """Every part of the panel's footer, drawn by the real app.

    The footer's height is measured from what it drew last frame, so a branch
    that is never drawn in a test is a branch whose height is never checked.
    """
    seen = {}

    def script(app, frame):
        console = app.console
        if frame == 3:
            console.submit("world.gravity")
            console.submit("test.camera_zoom")
        elif frame == 5:
            # A block at the prompt: the input grows to fit it.
            console.input = "for body in world.bodies:\n    print(body.position)"
            seen["rows"] = console._rows()
        elif frame == 7:
            console.completions = [f"world.attribute_{i}" for i in range(20)]
            console.searching = True
            console.search_query = "world"
        elif frame == 10:
            seen["footer"] = console._footer_height
            seen["matches"] = console.search_matches()

    frames, _ = run_headless(14, script)

    assert frames >= 14
    assert seen["rows"] == 2, "the prompt grew to the block typed into it"
    # Prompt, completions, search box, its match and the hint line: the footer
    # is a good deal taller than one row, and measured rather than assumed.
    assert seen["footer"] > 5 * 10.0
    assert seen["matches"] == ["world.gravity"]


def type_characters(text):
    """Push characters at imgui the way a keyboard would."""
    from imgui_bundle import imgui

    for character in text:
        imgui.get_io().add_input_character(ord(character))


def test_typing_carries_on_after_enter(scenario_dir):
    """The prompt has to keep the keyboard once a command has run.

    It did not: the prompt is a child window rather than a plain item, so
    imgui's set_keyboard_focus_here left the keyboard nowhere and the next thing
    typed went into the void.
    """
    from imgui_bundle import imgui

    seen = {}

    def script(app, frame):
        console = app.console
        if frame == 3:
            console._focus_input = True
            console.input = "6 * 7"
        elif frame == 6:
            imgui.get_io().add_key_event(imgui.Key.enter, True)
        elif frame == 7:
            imgui.get_io().add_key_event(imgui.Key.enter, False)
        elif frame == 9:
            seen["ran"] = [text for text, _ in console.lines][-2:]
            seen["prompt_cleared"] = console.input
        elif frame == 11:
            type_characters("world")
        elif frame == 14:
            seen["typed_after"] = console.input

    frames, _ = run_headless(18, script)

    assert frames >= 18
    assert seen["ran"] == [">>> 6 * 7", "42"], "Enter ran it"
    assert seen["prompt_cleared"] == ""
    assert seen["typed_after"] == "world", "and what was typed next reached the prompt"


def test_the_transcript_can_be_selected_and_copied(scenario_dir):
    """Output is a read-only editor, so it can be dragged over and copied.

    A column of text() calls looks identical and cannot be selected at all,
    which is what this replaced.
    """
    from imgui_bundle import imgui

    seen = {}

    def script(app, frame):
        console = app.console
        if frame == 3:
            console.submit("'a value worth copying'")
        elif 6 <= frame <= 12:
            # Dragged over several frames: one big jump is below imgui's drag
            # threshold and selects nothing, which is a fact about the test
            # rather than about the widget.
            lower, _ = console._transcript_rect
            imgui.get_io().add_mouse_pos_event(
                lower.x + 60 + (frame - 6) * 30, lower.y + 10
            )
            if frame == 6:
                imgui.get_io().add_mouse_button_event(0, True)
            elif frame == 12:
                imgui.get_io().add_mouse_button_event(0, False)
        elif frame == 14:
            seen["selected"] = console.transcript.any_cursor_has_selection()
            if seen["selected"]:
                console.transcript.copy()
                seen["clipboard"] = imgui.get_clipboard_text()
            # A selection means the transcript keeps the keyboard, so that
            # Ctrl+C goes to it rather than to the prompt.
            seen["kept_focus"] = console._focus_input

    frames, _ = run_headless(18, script)

    assert frames >= 18
    assert seen["selected"] is True, "dragging over the output selected something"
    assert seen["clipboard"], "and it could be copied"
    assert seen["kept_focus"] is False


def test_a_plain_click_in_the_transcript_hands_the_keyboard_back(scenario_dir):
    """Click to read something, then carry on typing -- no click back needed."""
    from imgui_bundle import imgui

    seen = {}

    def script(app, frame):
        console = app.console
        if frame == 3:
            console.submit("1 + 1")
        elif frame == 6:
            lower, _ = console._transcript_rect
            imgui.get_io().add_mouse_pos_event(lower.x + 20, lower.y + 4)
            imgui.get_io().add_mouse_button_event(0, True)
        elif frame == 7:
            imgui.get_io().add_mouse_button_event(0, False)
        elif frame == 9:
            seen["no_selection"] = not console.transcript.any_cursor_has_selection()
        elif frame == 11:
            type_characters("xyz")
        elif frame == 14:
            seen["typed"] = console.input

    frames, _ = run_headless(18, script)

    assert frames >= 18
    assert seen["no_selection"] is True, "a click without a drag selects nothing"
    assert seen["typed"] == "xyz", "so typing goes to the prompt"


def test_tab_completes_a_name_and_indents_when_there_is_none(scenario_dir):
    """Tab rather than a chord: it is what a Python prompt uses, and it keeps
    completion off Ctrl, which is not always where the keyboard says it is.

    The widget takes Tab for itself and indents at the cursor, so completing on
    it means undoing that first -- and only when it actually happened, which is
    what the second half of this checks.
    """
    from imgui_bundle import imgui

    seen = {}

    def script(app, frame):
        console = app.console
        if frame == 3:
            console._focus_input = True
            console.input = "world.grav"
            console.editor.set_cursor(_doc_pos(0, len("world.grav")))
        elif frame == 6:
            imgui.get_io().add_key_event(imgui.Key.tab, True)
        elif frame == 7:
            imgui.get_io().add_key_event(imgui.Key.tab, False)
        elif frame == 9:
            seen["completed"] = console.input
            # Now with nothing to complete: Tab should indent instead.
            console.input = "if True:\n"
            console.editor.set_cursor(_doc_pos(1, 0))
        elif frame == 12:
            imgui.get_io().add_key_event(imgui.Key.tab, True)
        elif frame == 13:
            imgui.get_io().add_key_event(imgui.Key.tab, False)
        elif frame == 16:
            seen["indented"] = console.input

    frames, _ = run_headless(20, script)

    assert frames >= 20
    assert seen["completed"] == "world.gravity", "Tab completed the name"
    assert seen["indented"] != "if True:\n", "and indents where there is no name"
    assert seen["indented"].startswith(
        "if True:\n"
    ), "without disturbing the line above"


def _doc_pos(line, index):
    from box2d_testbed.scenario_editor import TextEditor

    return TextEditor.DocPos(line, index)
