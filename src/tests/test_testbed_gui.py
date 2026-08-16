# tests/test_testbed_gui.py
"""Launch the real testbed for a few frames.

Everything else in the suite runs headless, which is what makes it fast and
CI-friendly -- but it means the window, the imgui shell and the whole
OpenGL renderer are never executed at all. That gap hid a broken shader path
for weeks, and it is where an imgui_bundle upgrade breaks things.

So this opens a real window, runs a hundred frames through several
scenarios, and closes it. It needs a display, and it is deliberately marked
so it can be deselected:

    pytest -m "not gui"
"""

import os

import pytest

pytestmark = pytest.mark.gui

HAS_DISPLAY = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
needs_display = pytest.mark.skipif(HAS_DISPLAY is False, reason="no display available")


def run_frames(frame_count, on_frame=None):
    """Run the testbed for a set number of frames, then let it exit.

    Returns:
        int: the number of frames actually rendered.
    """
    import box2d_testbed.testbed as tb

    app = tb.TestbedApp()
    runner = app.runner_params
    rendered = {"count": 0}
    previous = runner.callbacks.pre_new_frame

    def pre_new_frame():
        if previous is not None:
            previous()
        rendered["count"] += 1
        if on_frame is not None:
            on_frame(app, rendered["count"])
        if rendered["count"] >= frame_count:
            runner.app_shall_exit = True

    runner.callbacks.pre_new_frame = pre_new_frame
    app.run()
    return rendered["count"]


@needs_display
def test_the_testbed_opens_and_runs():
    """The whole stack: window, imgui shell, GL renderer, physics."""
    assert run_frames(60) >= 60


@needs_display
def test_the_testbed_renders_several_scenarios():
    """Switching scenarios rebuilds the world under a live renderer.

    Every scenario draws different primitives, so this reaches paths a
    single scenario never touches -- chains, capsules, joints and text.
    """
    from box2d_testbed.base_test import BaseTest
    from box2d_testbed.testbed_state import state

    ordered = [
        test_cls
        for tests in BaseTest.get_all_tests().values()
        for test_cls in tests.values()
    ]
    # A spread across categories rather than all of them, to keep this brief.
    chosen = ordered[:: max(1, len(ordered) // 6)][:6]

    def switch(app, frame):
        if frame % 15 == 0:
            index = frame // 15
            if index < len(chosen):
                state.current_test_cls = chosen[index]
                app.simulation.init_test()

    assert run_frames(15 * (len(chosen) + 1)) > 0


@needs_display
def test_every_debug_draw_flag_renders():
    """Turn every overlay on and draw with them, which the GL layer must survive."""
    from box2d_testbed.testbed_state import state

    def enable_everything(app, frame):
        if frame == 5:
            for key, _, _ in state.show_dd.get_current():
                setattr(state.show_dd, key, True)

    assert run_frames(40, enable_everything) >= 40
