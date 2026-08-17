from .testbed_state import state

# Imported for their side effect: each module registers its scenarios on
# BaseTest.registry when it loads.
from . import (  # noqa: F401
    tb_benchmark,
    tb_joints,
    tb_shapes,
    tb_collision,
    tb_events,
    tb_stacking,
    tb_character,
    tb_bodies,
    tb_continuous,
)
from box2d import World
from .base_test import BaseTest
from .scenario_loader import loader
from .scenario_store import UserStore, user_scenario_dir
import time
import traceback


class TestbedSimulation:
    """
    Handles Box2D physics, world, and test switching.
    """

    def __init__(self, debug_draw):
        self.world = None
        self._applied_settings = None
        self.threads = state.threads
        self.debug_draw = debug_draw

        # The user's own scenarios, so they are in the Tests panel from the
        # start rather than only after the editor has been opened. Loaded after
        # the builtins above, which keeps the first scenario a builtin one.
        for ref, error in loader.load_store(UserStore(user_scenario_dir())):
            print(f"skipping user scenario {ref.name}: {error.message}")

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
        self.apply_world_settings()
        state.step_count = 0
        state.scenario_error = None
        self._failed_hooks = set()

        # A scenario being edited is a scenario that breaks, and taking the
        # whole app down with it would mean losing the editor holding the fix.
        # So a failure here leaves an empty world and no current scenario, and
        # everything that would have driven one checks for that; the error goes
        # where the scenario's own panel was.
        try:
            self.current_test_obj = state.current_test_cls(self.world)
            self.current_test_obj.setup()
        except BaseException:
            state.scenario_error = traceback.format_exc()
            print(state.scenario_error, end="")
            self.current_test_obj = None
        state.current_test_obj = self.current_test_obj

        # Frame the new scenario. Without this a pan carried into whatever you
        # opened next, which usually meant looking at empty space with no clue
        # which way the scene was. The Reset button does not come through here,
        # so restarting a scenario keeps the view you had set up.
        self.reset_view()
        state.perf.physics_ms_max = 0
        state.perf.draw_ms_max = 0

    @staticmethod
    def world_settings():
        """The world settings the UI can change, as a comparable snapshot."""
        return (
            state.enable_continuous,
            state.enable_sleep,
            state.enable_warm_starting,
            state.enable_speculative,
            state.maximum_linear_speed,
            state.contact_recycle_distance,
        )

    def apply_world_settings(self):
        """Push the UI's world settings onto the world.

        Kept in one place so a setting added to the panel cannot be applied on
        a fresh world but forgotten when it is changed later, or the reverse.
        """
        self.world.enable_continuous = state.enable_continuous
        self.world.enable_sleep = state.enable_sleep
        self.world.enable_warm_starting = state.enable_warm_starting
        self.world.maximum_linear_speed = state.maximum_linear_speed
        self.world.contact_recycle_distance = state.contact_recycle_distance
        # No getter for this one, so it is written rather than compared.
        self.world.enable_speculative(state.enable_speculative)
        self._applied_settings = self.world_settings()

    def reset_view(self):
        """Point the camera at the current scenario."""
        if self.current_test_obj is not None:
            self.current_test_obj.apply_view()

    def _run_hook(self, name, *args):
        """Call one of the scenario's per-frame hooks.

        A hook that raises is not called again until the scenario is rebuilt.
        Left to raise it would either take the app down or, once caught, print
        a traceback per frame for as long as the window is open -- and the
        scene is still worth looking at while the hook driving it is broken.
        """
        test = self.current_test_obj
        if test is None or name in self._failed_hooks:
            return
        try:
            getattr(test, name)(*args)
        except BaseException:
            self._failed_hooks.add(name)
            state.scenario_error = traceback.format_exc()
            print(
                f"{name} raised; not calling it again:\n{state.scenario_error}", end=""
            )

    def update_physics(self):
        if (
            self.current_test_cls != state.current_test_cls
            or self.threads != state.threads
        ):
            self.init_test()
        if self.world_settings() != self._applied_settings:
            self.apply_world_settings()

        start = time.perf_counter()
        self.world.step(1 / state.hertz, state.substeps)
        elapsed = (time.perf_counter() - start) * 1000.0  # elapsed time in ms
        self._run_hook("after_step", 1 / state.hertz)
        smoothing = state.perf.smoothing_avg
        state.perf.physics_ms = elapsed
        state.perf.physics_ms_avg *= smoothing
        state.perf.physics_ms_avg += elapsed * (1 - smoothing)
        state.perf.physics_ms_max = max(state.perf.physics_ms_max, elapsed)
        state.perf.profile = self.world.profile
        state.perf.counters = self.world.counters
        state.perf.awake = self.world.awake_body_count
        state.step_count += 1

    def draw(self):
        self.debug_draw.start_frame()
        self.world.draw(self.debug_draw)
        self._run_hook("debug_draw", self.debug_draw)
        self.debug_draw.end_frame()
