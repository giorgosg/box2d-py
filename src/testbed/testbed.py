import time
import math
import dearpygui.dearpygui as dpg

from box2d import World, Vec2, ScaledTransform
from base_test import get_first_test, get_all_tests
from debug_draw_dpg import DearpyguiDebugDraw
import tb_sample, tb_shapes, tb_benchmark

from dpg_ui import TestbedUI


class TestbedConfig:
    WIDTH = 1024
    HEIGHT = 768
    CENTER = (WIDTH // 2, HEIGHT // 2)
    SCALE = 30  # pixels per meter (initial zoom)


class TestbedSimulation:
    """
    Handles Box2D physics, world, and test switching.
    """

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.world = World(gravity=(0, -10))
        self.current_test = None
        self.simulation_paused = False

        self.physics_dt = 1.0 / 60.0  # default: 60 Hz
        self.substeps = 4
        self.step_counter = 0

        # Initialize physics timing metrics (in milliseconds)
        self.last_physics_time = 0.0
        self.physics_time_avg = 0.0

    def update_settings(self):
        """
        Read the physics timestep (Hertz) and substeps from the UI and update internal settings.
        This method is called only when the UI signals that a value has changed.
        """
        timestep_hz = dpg.get_value("timestep_input")
        if timestep_hz <= 0:
            timestep_hz = 60.0
        self.physics_dt = 1.0 / timestep_hz
        self.substeps = dpg.get_value("substeps_input")

    def load_test(self, test_cls):
        print(f"Test switch requested: {test_cls.__name__}")
        # Reinitialize the world.
        if self.world:
            self.world.destroy()
        self.world = World(gravity=(0, -10))
        self.step_counter = 0
        container = self.coordinator.ui.create_test_ui_window(test_cls)
        self.current_test = test_cls(self.world, self.coordinator.ui.debug_draw)
        self.current_test.setup()
        self.current_test.init_ui()
        # Build the test's custom UI defined via UI descriptors.
        self.coordinator.ui.build_test_ui(self.current_test)
        self.coordinator.reset_accumulator()

    def update_physics(self):
        """
        Update the world by stepping the physics simulation and
        record the physics update time in milliseconds.
        """
        start = time.perf_counter()
        self.world.step(self.physics_dt, self.substeps)
        elapsed = (time.perf_counter() - start) * 1000.0  # elapsed time in ms
        self.record_physics_time(elapsed)
        self.step_counter += 1

    def toggle_simulation(self, sender, app_data, user_data=None):
        self.simulation_paused = not self.simulation_paused
        return "Play" if self.simulation_paused else "Pause"

    def toggle_continuous(self, sender, app_data, user_data=None):
        if self.world:
            self.world.enable_continuous = dpg.get_value(sender)

    def toggle_sleep(self, sender, app_data, user_data=None):
        if self.world:
            self.world.enable_sleep = dpg.get_value(sender)

    def reset_current_test(self):
        if self.current_test:
            print(f"Resetting test: {self.current_test.__class__.__name__}")
            self.load_test(self.current_test.__class__)

    def draw(self):
        if self.world:
            self.world.draw(self.coordinator.ui.debug_draw)

    def record_physics_time(self, time_ms):
        smoothing = 0.9
        self.last_physics_time = time_ms
        self.physics_time_avg = self.physics_time_avg * smoothing + time_ms * (
            1 - smoothing
        )


class TestbedInput:
    """
    Handles mouse, viewport, and coordinate transforms.
    """

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.last_mouse_pos = None
        center = coordinator.config.CENTER
        scale = coordinator.config.SCALE
        self.view_transform = ScaledTransform(
            position=center, rotation=0, scale=(scale, -scale)
        )

    def on_mouse_scroll(self, sender, app_data):
        # Only zoom if the mouse is over the simulation canvas.
        if not dpg.is_item_hovered(self.coordinator.ui.simulation_canvas):
            return
        zoom_speed = 1.1
        current_zoom = abs(self.view_transform.scale.x)
        if app_data > 0:
            new_zoom = current_zoom * zoom_speed
        elif app_data < 0:
            new_zoom = current_zoom / zoom_speed
        else:
            new_zoom = current_zoom
        new_zoom = max(5, min(new_zoom, 200))
        self.view_transform.scale = Vec2(new_zoom, -new_zoom)

    def update_panning(self):
        # Only update panning if the mouse is over the simulation canvas.
        if not dpg.is_item_hovered(self.coordinator.ui.simulation_canvas):
            self.last_mouse_pos = None
            return

        if dpg.is_mouse_button_down(1):  # Right-click drag.
            current_mouse = dpg.get_mouse_pos()
            if self.last_mouse_pos is not None:
                dx = current_mouse[0] - self.last_mouse_pos[0]
                dy = current_mouse[1] - self.last_mouse_pos[1]
                self.view_transform.position = Vec2(
                    self.view_transform.position.x + dx,
                    self.view_transform.position.y + dy,
                )
            self.last_mouse_pos = current_mouse
        else:
            self.last_mouse_pos = None

    def global_mouse_down_handler(self, sender, app_data):
        if not dpg.is_item_hovered(self.coordinator.ui.simulation_canvas):
            return
        if self.coordinator.sim.current_test and hasattr(
            self.coordinator.sim.current_test, "on_mouse_down"
        ):
            pos = self.view_transform.inverse(dpg.get_drawing_mouse_pos())
            self.coordinator.sim.current_test.on_mouse_down(pos)

    def global_mouse_drag_handler(self, sender, app_data):
        if not dpg.is_item_hovered(self.coordinator.ui.simulation_canvas):
            return
        if self.coordinator.sim.current_test and hasattr(
            self.coordinator.sim.current_test, "on_mouse_drag"
        ):
            pos = self.view_transform.inverse(dpg.get_drawing_mouse_pos())
            self.coordinator.sim.current_test.on_mouse_drag(pos, Vec2(0, 0))

    def global_mouse_release_handler(self, sender, app_data):
        if not dpg.is_item_hovered(self.coordinator.ui.simulation_canvas):
            return
        if self.coordinator.sim.current_test and hasattr(
            self.coordinator.sim.current_test, "on_mouse_release"
        ):
            pos = self.view_transform.inverse(dpg.get_drawing_mouse_pos())
            self.coordinator.sim.current_test.on_mouse_release(pos)

    def set_view_center(self, new_center):
        self.view_transform.position = Vec2(*new_center)


class TestbedCoordinator:
    """
    Orchestrates the UI, simulation, and input managers.
    """

    def __init__(self):
        self.config = TestbedConfig()
        self.ui = TestbedUI(self)
        self.sim = TestbedSimulation(self)
        self.input = TestbedInput(self)
        self.accumulator = 0.0
        self.prev_time = time.perf_counter()

    def reset_accumulator(self):
        self.accumulator = 0.0

    def run(self):
        self.ui.initialize()
        self.sim.update_settings()
        self.prev_time = time.perf_counter()
        while dpg.is_dearpygui_running():
            # Process GUI events.
            jobs = dpg.get_callback_queue()
            dpg.run_callbacks(jobs)

            current_time = time.perf_counter()
            elapsed = current_time - self.prev_time
            self.prev_time = current_time

            if not self.sim.simulation_paused:
                self.accumulator += elapsed
            else:
                self.accumulator = 0.0

            self.input.update_panning()
            self.ui.update()

            # --- Physics update ---
            if not self.sim.simulation_paused:
                while self.accumulator >= self.sim.physics_dt:
                    self.sim.update_physics()
                    self.accumulator -= self.sim.physics_dt

            # --- Drawing ---
            self.ui.debug_draw.start_frame()
            self.sim.draw()
            if self.sim.current_test:
                self.sim.current_test.update(elapsed)
            self.ui.debug_draw.end_frame()

            # --- Update performance metrics in UI ---
            dpg.set_value("step_text", f"Step: {self.sim.step_counter}")
            if self.sim.simulation_paused:
                physics_time_text = f"Physics: {self.sim.last_physics_time:.2f} ms"
            else:
                physics_time_text = f"Physics: {self.sim.physics_time_avg:.2f} ms avg"
            dpg.set_value("physics_time_text", physics_time_text)
            dpg.set_value(
                "draw_time_text", f"Draw: {self.ui.debug_draw.draw_time_avg:.2f} ms"
            )

            dpg.render_dearpygui_frame()
            time.sleep(0.001)
        dpg.destroy_context()


if __name__ == "__main__":
    coordinator = TestbedCoordinator()
    coordinator.run()
