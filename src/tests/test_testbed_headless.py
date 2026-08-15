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
