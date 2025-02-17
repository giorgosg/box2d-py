# If running directly from the 'src/testbed' directory, adjust sys.path and __package__
if __name__ == "__main__" and __package__ is None:
    import os
    import sys

    print("running with source box2d")
    # Add the parent directory (the project root's "src" directory) to sys.path.
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    # Set the package name so relative imports work.
    __package__ = "testbed"

import time
import math
import dearpygui.dearpygui as dpg

from box2d import World, Vec2, ScaledTransform
from .base_test import get_first_test, get_all_tests
from .debug_draw_dpg import DearpyguiDebugDraw
from .dpg_ui import TestbedUI
from .simulation_settings import settings
from . import tb_sample, tb_sample, tb_shapes, tb_benchmark, tb_joints


class TestbedSimulation:
    """
    Handles Box2D physics, world, and test switching.
    """

    def __init__(self, debug_draw):
        self.world = World(gravity=settings.gravity, threads=settings.threads)
        self.debug_draw = debug_draw
        settings.subscribe(self.toggle_continuous, "enable_continuous")
        settings.subscribe(self.toggle_sleep, "enable_sleep")
        settings.subscribe(self.init_test, "current_test")
        settings.subscribe(self.init_test, "threads")

    def init_test(self, key=None, value=None):
        print(f"Initializing test: {settings.current_test.__name__}")
        if self.world:
            self.world.destroy()
        self.world = World(gravity=settings.gravity, threads=settings.threads)
        self.world.enable_continuous = settings.enable_continuous
        self.world.enable_sleep = settings.enable_sleep
        settings.step_count = 0
        current_test_obj = settings.current_test(self.world)
        current_test_obj.setup()
        self.current_test = current_test_obj
        settings.current_test_obj = current_test_obj

    def update_physics(self):
        start = time.perf_counter()
        self.world.step(1 / settings.hertz, settings.substeps)
        elapsed = (time.perf_counter() - start) * 1000.0  # elapsed time in ms
        self.current_test.after_step(1 / settings.hertz)
        smoothing = 0.9
        settings.physics_ms = elapsed
        settings.physics_ms_avg = settings.physics_ms_avg * smoothing + elapsed * (
            1 - smoothing
        )
        settings.step_count = settings.step_count + 1

    def toggle_continuous(self, key, value):
        self.world.enable_continuous = value

    def toggle_sleep(self, key, value):
        self.world.enable_sleep = value

    def draw(self, debug_draw):
        debug_draw.start_frame()
        self.world.draw(debug_draw)
        self.current_test.debug_draw(debug_draw)
        debug_draw.end_frame()


class TestbedCoordinator:
    def __init__(self):
        self.ui = TestbedUI()
        self.sim = TestbedSimulation(self.ui.debug_draw)
        settings.all_tests = get_all_tests()
        settings.current_test = get_first_test()

    def run(self):
        self.ui.initialize()
        prev_time = time.perf_counter()
        while dpg.is_dearpygui_running():
            # Process GUI events.
            jobs = dpg.get_callback_queue()
            dpg.run_callbacks(jobs)

            current_time = time.perf_counter()
            elapsed = current_time - prev_time

            # --- Physics update ---
            if (not settings.simulation_paused) or (settings.step_number >= 1):
                dt = 1.0 / settings.hertz
                if elapsed >= dt:
                    self.sim.update_physics()
                    prev_time = current_time
                settings.step_number -= 1 if settings.step_number else 0

            # --- Drawing ---
            self.sim.draw(self.ui.debug_draw)

            dpg.render_dearpygui_frame()
            time.sleep(0.001)
        dpg.destroy_context()


def main():
    coordinator = TestbedCoordinator()
    coordinator.run()


if __name__ == "__main__":
    main()
