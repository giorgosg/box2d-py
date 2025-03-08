from .testbed_state import state
from . import tb_benchmark, tb_joints, tb_shapes, tb_collision, tb_events
from box2d import World, Vec2
from .base_test import BaseTest
import time


class TestbedSimulation:
    """
    Handles Box2D physics, world, and test switching.
    """

    def __init__(self, debug_draw):
        self.world = None
        self.enable_continuous = state.enable_continuous
        self.enable_sleep = state.enable_sleep
        self.threads = state.threads
        self.debug_draw = debug_draw
        self.debug_draw.camera.center = Vec2(0.0, 20.0)  # Set initial camera position
        self.debug_draw.camera.zoom = 1.0  # Set initial zoom

        state.all_tests = BaseTest.get_all_tests()
        state.current_test_cls = BaseTest.get_first_test()
        self.current_test_cls = state.current_test_cls
        self.current_test_obj = None
        self.init_test()

    def init_test(self):
        self.current_test_cls = state.current_test_cls
        self.threads = state.threads
        print(f"Initializing test: {self.current_test_cls.__name__}")
        if self.world:
            self.world.destroy()
        self.world = World(gravity=state.gravity, threads=state.threads)
        self.world.enable_continuous = state.enable_continuous
        self.world.enable_sleep = state.enable_sleep
        state.step_count = 0
        self.current_test_obj = state.current_test_cls(self.world)
        self.current_test_obj.setup()
        state.current_test_obj = self.current_test_obj
        state.perf.physics_ms_max = 0
        state.perf.draw_ms_max = 0

    def update_physics(self):
        if (
            self.current_test_cls != state.current_test_cls
            or self.threads != state.threads
        ):
            self.init_test()
        if (
            self.enable_continuous != state.enable_continuous
            or self.enable_sleep != state.enable_sleep
        ):
            self.enable_continuous = state.enable_continuous
            self.enable_sleep = state.enable_sleep
            self.world.enable_continuous = self.enable_continuous
            self.world.enable_sleep = self.enable_sleep

        start = time.perf_counter()
        self.world.step(1 / state.hertz, state.substeps)
        elapsed = (time.perf_counter() - start) * 1000.0  # elapsed time in ms
        self.current_test_obj.after_step(1 / state.hertz)
        smoothing = state.perf.smoothing_avg
        state.perf.physics_ms = elapsed
        state.perf.physics_ms_avg *= smoothing
        state.perf.physics_ms_avg += elapsed * (1 - smoothing)
        state.perf.physics_ms_max = max(state.perf.physics_ms_max, elapsed)
        state.step_count += 1

    def draw(self):
        self.debug_draw.start_frame()
        self.world.draw(self.debug_draw)
        self.current_test_obj.debug_draw(self.debug_draw)
        self.debug_draw.end_frame()
