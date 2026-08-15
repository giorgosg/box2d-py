"""Run the testbed's Python inside WebAssembly.

There is no canvas under node, so this is not the app drawing to a screen --
it is everything up to that: the scenarios, the physics, the imgui renderer's
geometry, and the app module importing at all without PyOpenGL.
"""

import os
import sys

# There is no PyOpenGL in a browser, so the imgui renderer is the only choice.
os.environ["BOX2D_TESTBED_RENDERER"] = "imgui"

print(f"platform: {sys.platform}")

import box2d

print(f"box2d    : HAS_THREADS={box2d.HAS_THREADS}")

from imgui_bundle import imgui  # noqa: E402
import imgui_bundle  # noqa: E402

print(f"imgui    : {imgui_bundle.__version__}")

# The app module itself: this used to drag in PyOpenGL and fail.
import box2d_testbed.testbed as testbed  # noqa: E402
from box2d_testbed.debug_draw_imgui import ImGuiDebugDraw, expand_polygon  # noqa: E402

print("testbed  : imported, with no PyOpenGL")

from box2d_testbed.base_test import BaseTest  # noqa: E402
from box2d_testbed import (  # noqa: E402,F401
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

scenarios = sum(len(tests) for tests in BaseTest.registry.values())
print(f"scenarios: {scenarios} registered\n")


# Every scenario, built and simulated, drawn through a renderer that records
# what it was asked for. No GL, no window, no canvas.
class Recorder(box2d.DebugDraw):
    def __init__(self):
        super().__init__()
        self.primitives = 0

    def draw_solid_polygon(self, transform, vertices, radius, color):
        self.primitives += 1

    def draw_solid_circle(self, transform, center, radius, color):
        self.primitives += 1

    def draw_solid_capsule(self, p1, p2, radius, color):
        self.primitives += 1

    def draw_segment(self, p1, p2, color):
        self.primitives += 1


failures = []
total_primitives = 0
for category, tests in sorted(BaseTest.registry.items()):
    for name, test_cls in sorted(tests.items()):
        world = box2d.World()
        try:
            test = test_cls(world)
            test.setup()
            for _ in range(20):
                world.step(1 / 60, 4)
                test.after_step(1 / 60)
            recorder = Recorder()
            world.draw(recorder)
            test.debug_draw(recorder)
            total_primitives += recorder.primitives
        except Exception as error:
            failures.append(f"{category}/{name}: {type(error).__name__}: {error}")
        finally:
            world.destroy()

print(f"ran {scenarios} scenarios, drawing {total_primitives} primitives")
print(f"failures: {failures if failures else 'none'}")

# The renderer's own geometry, which is pure Python and should be identical.
grown = expand_polygon(
    [(0, 0), (100, 0), (100, 100), (0, 100)], 10.0, segments_per_corner=64
)
area = (
    abs(
        sum(
            grown[i][0] * grown[(i + 1) % len(grown)][1]
            - grown[(i + 1) % len(grown)][0] * grown[i][1]
            for i in range(len(grown))
        )
    )
    / 2
)
expected = 100 * 100 + 400 * 10 + 3.141592653589793 * 100
print(f"\nrounded outline area: {area:.1f} (expected {expected:.1f})")

print(
    f"\nrenderer choice honoured: " f"{testbed.TestbedApp.debug_draw_class().__name__}"
)
# The testbed used to default to four threads regardless of the build, which
# made it unstartable here: the first thing it did was ask for a scheduler
# this build does not carry.
from box2d_testbed.testbed_state import state  # noqa: E402

print(f"default threads         : {state.threads} (HAS_THREADS={box2d.HAS_THREADS})")
assert state.threads == 1, "a build with no scheduler must default to one thread"
box2d.World(threads=state.threads).destroy()
print("a world builds with the testbed's default settings")

print("\nThe testbed's Python runs in WebAssembly.")
