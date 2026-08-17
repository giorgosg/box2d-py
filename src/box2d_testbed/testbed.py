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
from box2d import HAS_THREADS
from .testbed_state import state
from .testbed_simulation import TestbedSimulation
from .base_test import BaseTest, format_view_declaration
from .scenario_console import Console
from .scenario_editor import ScenarioEditor
import os
import time
from .debug_draw_imgui import ImGuiDebugDraw
from box2d import Vec2


#: What the code panels are drawn in, and the size to load it at. Inconsolata
#: ships inside imgui_bundle's assets, so this needs nothing installed and is
#: there in a browser build too.
MONO_FONT = "fonts/Inconsolata-Medium.ttf"
MONO_FONT_SIZE = 16.0


class TestbedApp:
    def __init__(self):
        self.simulation = None
        self.runner_params = hello_imgui.RunnerParams()
        self.debug_draw = None
        self.simulation = None
        self.last_step_time = time.perf_counter()
        self.triangle_vao = None
        self.triangle_program = None
        # Loaded once there is a font atlas to load it into, which is after the
        # panels below have been built -- so they read it off the app each
        # frame rather than being handed it.
        self.mono_font = None
        self.editor = ScenarioEditor(self)
        self.console = Console(self)
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
        self.runner_params.callbacks.load_additional_fonts = self.load_fonts

    def load_fonts(self):
        """The default font, and a monospace one for the code panels.

        hello_imgui's own callback is called rather than replaced: it loads
        DroidSans with the FontAwesome icons merged in, and the play and step
        buttons in Controls are two of those icons.

        The editor and the console show code, and a proportional font makes a
        mess of it -- indentation that does not line up, and a text editor whose
        cursor lands between characters, since ImGuiColorTextEdit measures one
        glyph and assumes the rest match.
        """
        hello_imgui.imgui_default_settings.load_default_font_with_font_awesome_icons()
        self.mono_font = hello_imgui.load_font(MONO_FONT, MONO_FONT_SIZE)

    def post_gl_init(self):
        """Build the renderer and the simulation, once there is a GL context."""
        self.debug_draw = self.make_debug_draw()
        self.simulation = TestbedSimulation(self.debug_draw)

    @staticmethod
    def gl_module():
        """PyOpenGL, imported only when the GL renderer is in use.

        There is no PyOpenGL in a browser, and importing it fails outright
        rather than degrading, so the app must be able to load without it.
        """
        from OpenGL import GL

        return GL

    @staticmethod
    def debug_draw_class():
        """Which renderer class to draw with.

        BOX2D_TESTBED_RENDERER=imgui swaps the OpenGL renderer for the one
        that draws through imgui's draw list. The imgui renderer is the one
        that can run where there is no GL -- a browser, or hello_imgui's null
        backend -- so both exist while they are being compared.

        Kept apart from building one: a GLDebugDraw compiles shaders as it is
        constructed, so asking which renderer is wanted must not itself
        require a GL context.
        """
        choice = os.environ.get("BOX2D_TESTBED_RENDERER", "opengl").lower()
        if choice == "imgui":
            return ImGuiDebugDraw
        if choice in ("opengl", "gl", ""):
            # Imported here, not at module scope: it pulls in PyOpenGL, which
            # a browser does not have.
            from .debug_draw_gl import GLDebugDraw

            return GLDebugDraw
        raise SystemExit(f"unknown renderer {choice!r}; expected 'opengl' or 'imgui'")

    @classmethod
    def make_debug_draw(cls):
        """Build the chosen renderer. Needs a GL context for the GL one."""
        return cls.debug_draw_class()()

    def render_simulation(self):
        """Draw the simulation in the window"""
        # Get window dimensions and position in screen coordinates
        pos = imgui.get_window_pos()
        size = imgui.get_window_size()
        io = imgui.get_io()
        # Ensure we have valid dimensions
        if size.x <= 0 or size.y <= 0:
            return

        # The GL renderer draws into this window through a viewport; the
        # imgui one submits to the window's draw list and needs none.
        uses_gl = type(self.debug_draw).__name__ == "GLDebugDraw"
        if uses_gl:
            gl = self.gl_module()
            # Convert ImGui coordinates to GL coordinates (flip Y)
            gl_y = io.display_size.y - (pos.y + size.y)
            gl.glViewport(int(pos.x), int(gl_y), int(size.x), int(size.y))

        # Only handle scroll when mouse is over simulation window
        mouse_scroll = io.mouse_wheel
        if mouse_scroll != 0.0 and imgui.is_window_hovered():
            self.on_mouse_scroll(mouse_scroll)

        # Middle-drag pans the camera. Right-click is deliberately left
        # unbound so it is available for context menus or scenario-specific
        # interactions later.
        if io.mouse_down[2] and imgui.is_window_hovered():
            self.on_middle_drag(io.mouse_delta)

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

        if uses_gl:
            # Reset viewport
            self.gl_module().glViewport(
                0, 0, int(io.display_size.x), int(io.display_size.y)
            )

    def key_press_events(self):
        # Not while something is being typed. The editor and the console are
        # both text fields, and without this every letter reaching them also
        # reached the testbed: typing "pr" in the console paused the simulation
        # and restarted the scenario.
        if imgui.get_io().want_capture_keyboard:
            return

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

        # Global shortcuts, handled here rather than passed to the scenario:
        # these drive the testbed itself. They deliberately avoid the keys
        # scenarios use for their own controls (a, d, s, space and the arrows).
        for key, action in self.global_shortcuts().items():
            if imgui.is_key_pressed(key, repeat=False):
                action()

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

        # The saved layout is keyed by this name, and dock ids are positions in
        # the split tree -- so adding a split moves windows an older ini had
        # pinned elsewhere, which put the scenario's own panel in among the
        # simulation's tabs. A new name means a clean layout instead, leaving
        # whatever was saved under the old one alone. Change it when the set of
        # windows or splits below changes.
        docking_params.layout_name = "with-editor"

        # A right-hand panel split top to bottom into Tests, the current test's
        # own UI, Controls, and Performance, and a console along the bottom.
        docking_params.docking_splits = [
            self._docking_split("MainDockSpace", "RightPanel", imgui.Dir_.right, 0.2),
            self._docking_split("MainDockSpace", "BottomPanel", imgui.Dir_.down, 0.25),
            self._docking_split("RightPanel", "RightPanel1", imgui.Dir_.down, 0.73),
            self._docking_split("RightPanel1", "RightPanel2", imgui.Dir_.down, 0.5),
            self._docking_split("RightPanel2", "RightPanel3", imgui.Dir_.down, 0.4),
        ]
        docking_params.dockable_windows = [
            # The simulation is declared before the editor they share a dock
            # space with, which is what leaves it the tab in front: the testbed
            # should open showing physics, not source.
            self._dockable_window(
                "Simulation",
                "MainDockSpace",
                self.render_simulation,
                imgui_window_flags=imgui.WindowFlags_.no_background,
            ),
            # The editor is here rather than in the 20% strip on the right,
            # where no line of code fits.
            self._dockable_window("Editor", "MainDockSpace", self.editor.gui),
            self._dockable_window("Console", "BottomPanel", self.console.gui),
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
        if state.current_test_cls is None:
            return
        imgui.text(f"Test: {state.current_test_cls.name}")
        imgui.separator()

        # A scenario that failed to build has no controls to show, so its panel
        # shows why instead. This is the common view while editing one.
        if state.scenario_error:
            imgui.push_style_color(imgui.Col_.text, (1.0, 0.4, 0.4, 1.0))
            imgui.text_wrapped(state.scenario_error)
            imgui.pop_style_color()
            if state.current_test_obj is None:
                return
            imgui.separator()

        # Iterate through UI elements defined in the current test.
        previous_was_button = False
        for name, elem in state.current_test_obj.ui_elements:
            # Buttons declared next to each other share a row, so Reset and
            # Reset View sit side by side rather than stacked.
            is_button = elem.type == "button"
            if is_button and previous_was_button:
                imgui.same_line()
            previous_was_button = is_button

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

    def global_shortcuts(self):
        """Keyboard shortcuts for the testbed's own controls.

        Everything the control panel offers should be reachable from the
        keyboard, so a scenario can be driven without moving the mouse off it.
        """
        return {
            imgui.Key.p: self.toggle_pause,
            imgui.Key.o: self.step_once,
            imgui.Key.r: self.restart_test,
            imgui.Key.home: self.reset_view,
            imgui.Key.left_bracket: lambda: self.cycle_test(-1),
            imgui.Key.right_bracket: lambda: self.cycle_test(1),
        }

    def focus_editor(self):
        """Bring the editor tab up, since it shares a dock with the simulation."""
        self.runner_params.docking_params.focus_dockable_window("Editor")

    def toggle_pause(self):
        state.simulation_paused = not state.simulation_paused

    def step_once(self):
        """Advance one step, pausing first so it is a single step."""
        state.simulation_paused = True
        state.step_number += 1

    def restart_test(self):
        """Rebuild the current scenario, as the Reset button does."""
        if state.current_test_obj is not None:
            state.current_test_obj.on_reset("reset", None)

    def reset_view(self):
        if self.simulation is not None:
            self.simulation.reset_view()

    def cycle_test(self, step: int):
        """Move to the next or previous scenario, wrapping at the ends."""
        ordered = [
            test_cls
            for tests in BaseTest.get_all_tests().values()
            for test_cls in tests.values()
        ]
        if not ordered:
            return
        try:
            index = ordered.index(state.current_test_cls)
        except ValueError:
            index = 0
        state.current_test_cls = ordered[(index + step) % len(ordered)]
        if self.simulation is not None:
            self.simulation.init_test()

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
        # Threads slider. A build without the task scheduler cannot go above
        # one, and asking raises, so the control does not offer it.
        if HAS_THREADS:
            changed, state.threads = imgui.slider_int("Threads", state.threads, 1, 32)
        else:
            imgui.text_disabled("Threads: 1 (this build has no scheduler)")
        # Substeps slider
        changed, state.substeps = imgui.slider_int("Substeps", state.substeps, 1, 32)
        # Hertz slider
        _, state.hertz = imgui.slider_int("Hertz", state.hertz, 10, 240)

        _, state.maximum_linear_speed = imgui.slider_float(
            "Max speed", state.maximum_linear_speed, 10.0, 1000.0, format="%.0f"
        )
        _, state.contact_recycle_distance = imgui.slider_float(
            "Recycle dist", state.contact_recycle_distance, 0.0, 0.5, format="%.3f"
        )
        imgui.pop_item_width()

        # Checkboxes
        _, state.enable_continuous = imgui.checkbox(
            "Continuous Collision", state.enable_continuous
        )
        _, state.enable_sleep = imgui.checkbox("Sleep", state.enable_sleep)
        _, state.enable_warm_starting = imgui.checkbox(
            "Warm starting", state.enable_warm_starting
        )
        imgui.set_item_tooltip(
            "Start the solver from last step's impulses.\n"
            "Turning it off costs stability and buys nothing; it is here to see that."
        )
        _, state.enable_speculative = imgui.checkbox(
            "Speculative contacts", state.enable_speculative
        )

        imgui.separator()
        imgui.text_disabled("P pause   O step   R reset   Home view   [ ] prev/next")

    def show_menus(self):
        if imgui.begin_menu("Scenario"):
            if imgui.menu_item("New", "", False)[0]:
                self.editor.new()
                self.focus_editor()
            if imgui.menu_item("Edit the running one", "", False)[0]:
                self.editor.open_current_scenario()
                self.focus_editor()
            if imgui.menu_item("Save", "Ctrl+S", False)[0]:
                self.editor.save()
            imgui.separator()
            imgui.text_disabled(str(self.editor.user_store.path))
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

        # Live, so it is readable while panning, and next to a button that
        # copies it as source: frame a scenario by hand, paste, keep it.
        # Right-justified, so it holds its place as the toggles change width.
        center = Vec2(state.center)
        label = f"view ({center.x:.2f}, {center.y:.2f}) z{state.scale:.2f}"

        style = imgui.get_style()
        # SmallButton keeps the horizontal frame padding and drops the vertical.
        copy_width = imgui.calc_text_size("Copy").x + 2.0 * style.frame_padding.x
        needed = imgui.calc_text_size(label).x + style.item_spacing.x + copy_width
        imgui.same_line(imgui.get_window_width() - needed - style.window_padding.x)

        imgui.text_disabled(label)
        imgui.same_line()
        if imgui.small_button("Copy"):
            imgui.set_clipboard_text(format_view_declaration(state.center, state.scale))
        imgui.set_item_tooltip(
            "Copy camera_center and camera_zoom for the current view,\n"
            "ready to paste into the scenario class."
        )
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

    def on_middle_drag(self, delta):
        """Handle middle mouse drag for panning the camera."""
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
