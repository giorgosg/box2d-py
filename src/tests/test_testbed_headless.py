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
