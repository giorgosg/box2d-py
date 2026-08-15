# If running directly from the 'src/testbed' directory, adjust sys.path and __package__
if __name__ == "__main__" and __package__ is None:
    import os
    import sys

    print("running with source box2d")
    # Add the parent directory (the project root's "src" directory) to sys.path.
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    # Set the package name so relative imports work.
    __package__ = "box2d_testbed"

from imgui_bundle import hello_imgui, imgui, icons_fontawesome_6
from .testbed_state import state
from .testbed_simulation import TestbedSimulation
from .base_test import BaseTest
import time
from .debug_draw_gl import GLDebugDraw
from OpenGL import GL as gl
from box2d import Vec2


class TestbedApp:
    def __init__(self):
        self.simulation = None
        self.runner_params = hello_imgui.RunnerParams()
        self.debug_draw = None
        self.simulation = None
        self.last_step_time = time.perf_counter()
        self.triangle_vao = None
        self.triangle_program = None
        self.init_app()

    def init_app(self):
        # Set window type back to docking with default window
        self.runner_params.imgui_window_params.default_imgui_window_type = (
            hello_imgui.DefaultImGuiWindowType.provide_full_screen_dock_space
        )
        self.runner_params.app_window_params.window_geometry.size = (1024, 768)
        # Initialize simulation and debug draw in post_init
        self.runner_params.callbacks.post_init = self.post_gl_init

        # Menu setup
        self.runner_params.imgui_window_params.show_menu_bar = True
        self.runner_params.callbacks.show_menus = self.show_menus
        self.runner_params.imgui_window_params.show_menu_app = False

        # Status bar
        self.runner_params.imgui_window_params.show_status_bar = True
        self.runner_params.imgui_window_params.show_status_fps = False
        self.runner_params.fps_idling.enable_idling = False

        self.runner_params.callbacks.show_status = self.show_status

        # Docking layout
        self.runner_params.docking_params = self.create_layout()
        self.runner_params.docking_params.main_dock_space_node_flags = (
            imgui.DockNodeFlags_.none
        )

        self.runner_params.callbacks.pre_new_frame = self.update_physics_timer

    def post_gl_init(self):
        """Initialize OpenGL resources and simulation"""
        self.debug_draw = GLDebugDraw()
        self.simulation = TestbedSimulation(self.debug_draw)

    def render_simulation(self):
        """Draw the simulation in the window"""
        # Get window dimensions and position in screen coordinates
        pos = imgui.get_window_pos()
        size = imgui.get_window_size()
        io = imgui.get_io()
        # Ensure we have valid dimensions
        if size.x <= 0 or size.y <= 0:
            return

        # Convert ImGui coordinates to GL coordinates (flip Y)
        gl_y = io.display_size.y - (pos.y + size.y)

        # Set viewport to window region
        gl.glViewport(int(pos.x), int(gl_y), int(size.x), int(size.y))

        # Only handle scroll when mouse is over simulation window
        mouse_scroll = io.mouse_wheel
        if mouse_scroll != 0.0 and imgui.is_window_hovered():
            self.on_mouse_scroll(mouse_scroll)

        # Handle right mouse drag for panning
        if io.mouse_down[1] and imgui.is_window_hovered():
            self.on_right_drag(io.mouse_delta)

        # send key press events to current test
        self.key_press_events()

        # If a current test exists and the simulation window is hovered,
        # convert mouse coordinates to world coordinates and call test mouse events.
        if state.current_test_obj and imgui.is_window_hovered():
            mouse_pos = Vec2(io.mouse_pos.x, io.mouse_pos.y) - Vec2(pos.x, pos.y)
            world_pos = self.debug_draw.camera.convert_screen_to_world(mouse_pos)
            # Check left mouse button events.
            if io.mouse_clicked[0]:
                state.current_test_obj.on_mouse_down(world_pos)
            elif io.mouse_down[0]:
                delta = Vec2(io.mouse_delta.x, io.mouse_delta.y)
                state.current_test_obj.on_mouse_drag(world_pos, delta)
            if io.mouse_released[0]:
                state.current_test_obj.on_mouse_release(world_pos)

        self.debug_draw.camera.set_view(state.center, state.scale, size.x, size.y)

        if self.simulation is not None:
            # Draw simulation
            self.simulation.draw()

        # Reset viewport
        gl.glViewport(0, 0, int(io.display_size.x), int(io.display_size.y))

    def key_press_events(self):

        # Map of ImGui key codes to string identifiers
        key_map = {
            imgui.Key.space: "space",
            imgui.Key.left_arrow: "left",
            imgui.Key.right_arrow: "right",
            imgui.Key.up_arrow: "up",
            imgui.Key.down_arrow: "down",
            imgui.Key.escape: "escape",
            imgui.Key.enter: "enter",
            imgui.Key.tab: "tab",
            # Add letter keys
            **{
                getattr(imgui.Key, f"{chr(i)}"): chr(i)
                for i in range(ord("a"), ord("z") + 1)
            },
            # Add number keys
            **{getattr(imgui.Key, f"_{i}"): str(i) for i in range(10)},
        }

        # Check for key events
        if not hasattr(self, "_prev_keys_down"):
            self._prev_keys_down = set()

        # Check currently pressed keys
        # Home re-frames the current scenario, matching the C++ testbed. Handled
        # here rather than passed to the scenario, since it is a view control.
        if imgui.is_key_pressed(imgui.Key.home, repeat=False) and self.simulation:
            self.simulation.reset_view()

        for key_code, key_name in key_map.items():
            if imgui.is_key_pressed(key_code, repeat=False):
                if state.current_test_obj:
                    state.current_test_obj.on_key_down(key_name)
            if imgui.is_key_released(key_code):
                if state.current_test_obj:
                    state.current_test_obj.on_key_up(key_name)

    def update_physics_timer(self):
        if self.simulation is None:
            return
        now = time.perf_counter()
        elapsed = now - self.last_step_time
        target_interval = 1.0 / state.hertz

        if (
            not state.simulation_paused or state.step_number > 0
        ) and elapsed >= target_interval:
            if not state.simulation_paused:
                while elapsed >= target_interval:
                    self.simulation.update_physics()
                    elapsed -= target_interval
                    self.last_step_time += target_interval
            else:
                self.simulation.update_physics()
                self.last_step_time = now
                if state.step_number > 0:
                    state.step_number -= 1

    @staticmethod
    def _docking_split(initial_dock, new_dock, direction, ratio):
        """One pane of the docking layout."""
        split = hello_imgui.DockingSplit()
        split.initial_dock = initial_dock
        split.new_dock = new_dock
        split.direction = direction
        split.ratio = ratio
        return split

    @staticmethod
    def _dockable_window(label, dock_space_name, gui_function, **attributes):
        """One docked window, drawn by gui_function."""
        window = hello_imgui.DockableWindow()
        window.label = label
        window.dock_space_name = dock_space_name
        window.gui_function = gui_function
        for name, value in attributes.items():
            setattr(window, name, value)
        return window

    def create_layout(self):
        docking_params = hello_imgui.DockingParams()

        # A right-hand panel split top to bottom into Tests, the current test's
        # own UI, Controls, and Performance.
        docking_params.docking_splits = [
            self._docking_split("MainDockSpace", "RightPanel", imgui.Dir_.right, 0.2),
            self._docking_split("RightPanel", "RightPanel1", imgui.Dir_.down, 0.73),
            self._docking_split("RightPanel1", "RightPanel2", imgui.Dir_.down, 0.5),
            self._docking_split("RightPanel2", "RightPanel3", imgui.Dir_.down, 0.4),
        ]
        docking_params.dockable_windows = [
            self._dockable_window(
                "Simulation",
                "MainDockSpace",
                self.render_simulation,
                imgui_window_flags=imgui.WindowFlags_.no_background,
            ),
            self._dockable_window("Tests", "RightPanel1", self.show_test_list),
            self._dockable_window("Performance", "RightPanel3", self.show_stats),
            self._dockable_window("Controls", "RightPanel", self.show_controls),
            self.create_test_ui_window(),
        ]
        return docking_params

    def create_test_ui_window(self):
        """The panel a scenario fills with its own UI properties.

        Built separately because its title follows the selected scenario.
        """
        label = (
            state.current_test_cls.name
            if state.current_test_cls is not None
            else "Test UI"
        )
        return self._dockable_window(label, "RightPanel2", self.render_test_ui)

    def render_test_ui(self):
        # Only render if a test object exists.
        imgui.text(f"Test: {state.current_test_cls.name}")
        imgui.separator()
        # Iterate through UI elements defined in the current test.
        for name, elem in state.current_test_obj.ui_elements:
            if elem.type == "button":
                if imgui.button(elem.label):
                    v = getattr(state.current_test_obj, elem.name)
                    v = v or 1
                    setattr(state.current_test_obj, elem.name, v + 1)
            elif elem.type == "int":
                # Get current value from state if exists, default otherwise.
                current_val = elem.value
                imgui.set_next_item_width(50)
                changed, new_val = imgui.slider_int(
                    elem.label, current_val, elem.min_value, elem.max_value
                )
                if changed:
                    setattr(state.current_test_obj, elem.name, new_val)
            elif elem.type == "float":
                current_val = elem.value
                imgui.set_next_item_width(50)
                changed, new_val = imgui.slider_float(
                    elem.label,
                    current_val,
                    elem.min_value,
                    elem.max_value,
                    format="%.1f",
                )
                if changed:
                    setattr(state.current_test_obj, elem.name, new_val)
            elif elem.type == "select":
                current_val = elem.value
                current_item = elem.options.index(current_val)
                changed, new_val = imgui.combo(elem.label, current_item, elem.options)
                if changed:
                    setattr(
                        state.current_test_obj,
                        elem.name,
                        elem.options[new_val],
                    )
            elif elem.type == "bool":
                current_val = elem.value
                changed, new_val = imgui.checkbox(elem.label, current_val)
                if changed:
                    setattr(state.current_test_obj, elem.name, new_val)
            else:
                print(f"Unknown control type: {elem.control_type}")

    def show_controls(self):
        # Play/Pause button
        if imgui.button(
            icons_fontawesome_6.ICON_FA_PLAY
            if state.simulation_paused
            else icons_fontawesome_6.ICON_FA_PAUSE
        ):
            state.simulation_paused = not state.simulation_paused
        imgui.same_line()

        # Step button
        if imgui.button(icons_fontawesome_6.ICON_FA_FORWARD):
            if not state.simulation_paused:
                state.simulation_paused = True
            state.step_number += 1

        imgui.push_item_width(100)
        # Threads slider
        changed, state.threads = imgui.slider_int("Threads", state.threads, 1, 32)
        # Substeps slider
        changed, state.substeps = imgui.slider_int("Substeps", state.substeps, 1, 32)
        # Hertz slider
        _, state.hertz = imgui.slider_int("Hertz", state.hertz, 10, 240)
        imgui.pop_item_width()

        # Checkboxes
        _, state.enable_continuous = imgui.checkbox(
            "Continuous Collision", state.enable_continuous
        )
        _, state.enable_sleep = imgui.checkbox("Sleep", state.enable_sleep)

    def show_menus(self):
        # Not "View": hello_imgui owns a menu by that name (docking layout and
        # themes), and adding a second one puts two View menus side by side.
        if imgui.begin_menu("Camera"):
            if imgui.menu_item("Reset view", "Home", False)[0] and self.simulation:
                self.simulation.reset_view()
            imgui.end_menu()
        if imgui.begin_menu("Draw"):
            for key, value, display in state.show_dd.get_current():
                _, newvalue = imgui.menu_item(display, "", value)
                setattr(state.show_dd, key, newvalue)
            imgui.end_menu()

    def show_status(self):
        imgui.push_style_var(imgui.StyleVar_.item_spacing, (10, 1))
        for key, value, display in state.show_dd.get_current(primary_only=True):
            _, newvalue = imgui.checkbox(display, value)
            setattr(state.show_dd, key, newvalue)
            imgui.same_line()
        imgui.pop_style_var()

    def show_test_list(self):
        for category, tests in BaseTest.get_all_tests().items():
            if imgui.tree_node(category):
                for test_name, test_cls in tests.items():
                    if imgui.selectable(test_name, test_cls == state.current_test_cls)[
                        0
                    ]:
                        state.current_test_cls = test_cls
                        self.simulation.init_test()
                imgui.tree_pop()

    def show_stats(self):
        imgui.text("current (avg) [max] ms")
        imgui.separator()
        imgui.text(
            f"Physics: {state.perf.physics_ms:.2f} ({state.perf.physics_ms_avg:.2f}) [{state.perf.physics_ms_max:.2f}]"
        )
        imgui.text(
            f"Graphics: {state.perf.draw_ms:.1f} ({state.perf.draw_ms_avg:.1f}) [{state.perf.draw_ms_max:.1f}] ms"
        )

        profile, counters = state.perf.profile, state.perf.counters
        if profile is None or counters is None:
            return

        imgui.separator()
        # Box2D times itself, so this is the step without the binding around
        # it. Where it diverges from Physics above, the cost is on our side.
        imgui.text(f"Box2D step: {profile.step:.2f} ms")
        for name, milliseconds in profile.slowest(4):
            imgui.text(f"  {name.replace('_', ' ')}: {milliseconds:.2f}")

        imgui.separator()
        imgui.text(f"bodies {counters.body_count} ({state.perf.awake} awake)")
        imgui.text(f"shapes {counters.shape_count}  contacts {counters.contact_count}")
        imgui.text(f"joints {counters.joint_count}  islands {counters.island_count}")
        imgui.text(
            f"tree height {counters.tree_height} / static {counters.static_tree_height}"
        )
        imgui.text(f"memory {counters.byte_count / 1024:.0f} KiB")

    def on_mouse_scroll(self, ammount: float):
        """Handle mouse scroll for zooming"""
        # Scale factor per scroll unit
        scale_factor = 1.1
        if ammount > 0:
            scale_factor = 1 / scale_factor
        scale_factor = scale_factor ** abs(ammount)
        scale = state.scale * scale_factor
        # Clamp scale to reasonable values
        state.scale = max(0.02, min(scale, 100.0))

    def on_right_drag(self, delta):
        """Handle right mouse drag for panning the camera"""
        # Get current window size for scaling calculation
        size = imgui.get_window_size()

        screen_to_world = 2.0 * state.scale / size.y
        world_delta_x = delta.x * screen_to_world
        world_delta_y = -delta.y * screen_to_world

        state.center = Vec2(*state.center) - Vec2(world_delta_x, world_delta_y)

    def run(self):
        hello_imgui.run(self.runner_params)


def main():
    app = TestbedApp()
    app.run()


if __name__ == "__main__":
    main()
