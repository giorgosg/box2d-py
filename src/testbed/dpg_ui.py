import dearpygui.dearpygui as dpg
from base_test import get_first_test, get_all_tests
from debug_draw_dpg import DearpyguiDebugDraw


class TestbedUI:
    """
    Handles all UI layout, window creation, and widget callbacks.
    """

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.viewport_width = coordinator.config.WIDTH
        self.viewport_height = coordinator.config.HEIGHT

        # Layout constants
        self.controls_height = 40
        self.toggles_height = 35
        self.sidebar_width = 160
        self.margin = 20

        # Constants for the stats window (bottom-right above toggles)
        self.stats_height = 50
        self.stats_margin = 5
        self.stats_bottom_offset = 35

        # UI object handles
        self.main_window = None
        self.simulation_canvas = None
        self.tests_tree = None
        self.debug_toggles_panel = None
        self.test_ui_container = None
        self.test_selectable_ids = []
        self.debug_draw = None

    def initialize(self):
        dpg.create_context()
        dpg.configure_app(manual_callback_management=True)
        dpg.create_viewport(
            title="Box2D TestBed - DearPyGui",
            width=self.viewport_width,
            height=self.viewport_height,
        )

        with dpg.window(
            label="TestBed", tag="main_window", no_scrollbar=True
        ) as self.main_window:
            # Top controls group.
            with dpg.group(horizontal=True, tag="controls_group"):
                dpg.add_button(
                    label="Pause",
                    tag="sim_start_pause_button",
                    callback=self.on_toggle_simulation,
                )
                dpg.add_button(
                    label="Step",
                    tag="sim_step_button",
                    callback=self.on_step_simulation,
                )
                dpg.add_text("Substeps:")
                dpg.add_input_int(
                    tag="substeps_input",
                    label="",
                    default_value=4,
                    width=80,
                    callback=self.on_physics_settings_change,
                )
                dpg.add_text("Hertz:")
                dpg.add_input_int(
                    tag="timestep_input",
                    label="",
                    default_value=60,
                    width=80,
                    callback=self.on_physics_settings_change,
                )
                dpg.add_checkbox(
                    tag="enable_continuous_checkbox",
                    label="Continuous Collision",
                    default_value=self.coordinator.sim.world.enable_continuous,
                    callback=self.on_toggle_continuous,
                )
                dpg.add_checkbox(
                    tag="enable_sleep_checkbox",
                    label="Sleep",
                    default_value=self.coordinator.sim.world.enable_sleep,
                    callback=self.on_toggle_sleep,
                )

            # Create the main content group.
            with dpg.group(horizontal=True, tag="main_content"):
                self.simulation_canvas = dpg.add_drawlist(
                    tag="simulation_canvas",
                    width=self.viewport_width,
                    height=self.viewport_height,
                )
                self.tests_tree = dpg.add_child_window(tag="tests_tree")
                self.build_tests_tree()

        # Stats window (without fixed position/size; will be set on viewport resize).
        with dpg.window(
            label="",
            tag="stats_window",
            no_title_bar=True,
            no_move=True,
            no_resize=True,
            no_scrollbar=True,
            min_size=(0, 0),
        ):
            dpg.add_text("Step: 0", tag="step_text")
            dpg.add_text("Physics: 0.0 ms", tag="physics_time_text")
            dpg.add_text("Draw: 0.0 ms", tag="draw_time_text")

        # Initialize the debug draw.
        self.debug_draw = DearpyguiDebugDraw(self.simulation_canvas)
        self.debug_draw.view_transform = self.coordinator.input.view_transform

        # Debug draw toggles window.
        with dpg.window(
            label="Debug Draw Toggles",
            tag="debug_toggles_panel",
            no_title_bar=True,
            no_move=True,
            no_resize=True,
            min_size=(0, 0),
        ) as self.debug_toggles_panel:
            with dpg.group(horizontal=True, horizontal_spacing=10):
                dpg.add_checkbox(
                    label="shapes",
                    default_value=self.debug_draw.draw_shapes,
                    callback=self.on_toggle_debug_draw,
                    user_data="draw_shapes",
                )
                dpg.add_checkbox(
                    label="aabbs",
                    default_value=self.debug_draw.draw_aabbs,
                    callback=self.on_toggle_debug_draw,
                    user_data="draw_aabbs",
                )
                dpg.add_checkbox(
                    label="joints",
                    default_value=self.debug_draw.draw_joints,
                    callback=self.on_toggle_debug_draw,
                    user_data="draw_joints",
                )
                dpg.add_checkbox(
                    label="contacts",
                    default_value=self.debug_draw.draw_contacts,
                    callback=self.on_toggle_debug_draw,
                    user_data="draw_contacts",
                )
                dpg.add_checkbox(
                    label="contact_normals",
                    default_value=self.debug_draw.draw_contact_normals,
                    callback=self.on_toggle_debug_draw,
                    user_data="draw_contact_normals",
                )
                dpg.add_checkbox(
                    label="contact_impulses",
                    default_value=self.debug_draw.draw_contact_impulses,
                    callback=self.on_toggle_debug_draw,
                    user_data="draw_contact_impulses",
                )
                dpg.add_checkbox(
                    label="friction_impulses",
                    default_value=self.debug_draw.draw_friction_impulses,
                    callback=self.on_toggle_debug_draw,
                    user_data="draw_friction_impulses",
                )
                dpg.add_checkbox(
                    label="mass",
                    default_value=self.debug_draw.draw_mass,
                    callback=self.on_toggle_debug_draw,
                    user_data="draw_mass",
                )
                dpg.add_checkbox(
                    label="joint_extras",
                    default_value=self.debug_draw.draw_joint_extras,
                    callback=self.on_toggle_debug_draw,
                    user_data="draw_joint_extras",
                )

        # Register global mouse event handlers.
        with dpg.handler_registry():
            dpg.add_mouse_wheel_handler(callback=self.coordinator.input.on_mouse_scroll)
            dpg.add_mouse_down_handler(
                callback=self.coordinator.input.global_mouse_down_handler
            )
            dpg.add_mouse_drag_handler(
                callback=self.coordinator.input.global_mouse_drag_handler
            )
            dpg.add_mouse_release_handler(
                callback=self.coordinator.input.global_mouse_release_handler
            )

        dpg.set_viewport_resize_callback(self.on_viewport_resize)

        default_test_cls = get_first_test()
        if default_test_cls is not None:
            self.coordinator.sim.load_test(default_test_cls)

        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window(self.main_window, True)

        # Update positions and sizes using the viewport's current dimensions.
        self.on_viewport_resize(None, None)

    def build_tests_tree(self):
        self.test_selectable_ids = []
        tests_registry = get_all_tests()
        for category, tests in tests_registry.items():
            with dpg.tree_node(
                label=category, default_open=False, parent=self.tests_tree
            ):
                for test_name, test_cls in tests.items():
                    selectable_id = dpg.add_selectable(
                        label=test_name,
                        callback=self.on_test_select,
                        user_data=test_cls,
                    )
                    self.test_selectable_ids.append(selectable_id)

    def create_test_ui_window(self, test_cls):
        if dpg.does_item_exist("test_ui_window"):
            dpg.delete_item("test_ui_window")
        ui_window_width = 220
        ui_window_height = 150
        with dpg.window(
            label=f"{test_cls.category} - {test_cls.name}",
            tag="test_ui_window",
            pos=(10, dpg.get_viewport_height() - ui_window_height - 50),
            no_close=True,
            width=ui_window_width,
        ):
            dpg.add_button(label="Reset Test", callback=self.on_reset_test)
            self.test_ui_container = dpg.add_child_window(tag="test_ui_container")
        return self.test_ui_container

    def on_viewport_resize(self, sender, app_data):
        new_width, new_height = dpg.get_viewport_width(), dpg.get_viewport_height()
        content_height = new_height - self.controls_height - self.toggles_height
        canvas_width = new_width - self.sidebar_width - self.margin

        dpg.configure_item(self.main_window, width=new_width, height=new_height)
        dpg.configure_item(
            self.simulation_canvas, width=canvas_width, height=content_height
        )

        # Adjust the tests tree height to account for the stats window margin and bottom offset.
        tests_tree_height = content_height - (
            self.stats_height + self.stats_margin + self.stats_bottom_offset
        )
        dpg.configure_item(
            self.tests_tree, width=self.sidebar_width, height=tests_tree_height
        )

        new_view_center = (canvas_width // 2, content_height // 2)
        self.coordinator.input.set_view_center(new_view_center)
        dpg.configure_item(
            self.debug_toggles_panel,
            pos=(0, new_height - self.toggles_height),
            width=new_width,
            height=self.toggles_height,
        )
        # Set the stats window to be the same width as the tests tree.
        if dpg.does_item_exist("stats_window"):
            dpg.configure_item("stats_window", width=self.sidebar_width)
            dpg.configure_item(
                "stats_window",
                pos=(
                    new_width - self.sidebar_width - self.stats_margin,
                    new_height
                    - self.toggles_height
                    - self.stats_height
                    - self.stats_margin
                    - self.stats_bottom_offset,
                ),
            )

    # --- Callback wrappers ---
    def on_toggle_simulation(self, sender, app_data, user_data=None):
        new_label = self.coordinator.sim.toggle_simulation(sender, app_data)
        dpg.set_item_label(sender, new_label)

    def on_toggle_continuous(self, sender, app_data, user_data=None):
        self.coordinator.sim.toggle_continuous(sender, app_data)

    def on_toggle_sleep(self, sender, app_data, user_data=None):
        self.coordinator.sim.toggle_sleep(sender, app_data)

    def on_toggle_debug_draw(self, sender, app_data, user_data):
        new_value = dpg.get_value(sender)
        setattr(self.debug_draw, user_data, new_value)

    def on_test_select(self, sender, app_data, user_data):
        for sid in self.test_selectable_ids:
            dpg.set_value(sid, False)
        dpg.set_value(sender, True)
        self.coordinator.sim.load_test(user_data)

    def on_reset_test(self, sender, app_data, user_data=None):
        self.coordinator.sim.reset_current_test()

    def on_physics_settings_change(self, sender, app_data, user_data=None):
        """
        Callback executed when the timestep or substeps setting is changed.
        It propagates the new values to the simulation.
        """
        self.coordinator.sim.update_settings()

    def on_step_simulation(self, sender, app_data, user_data=None):
        """
        Callback for the 'Step' button.
        If the simulation is running, pause it first.
        Then step the simulation for one physics update.
        """
        if not self.coordinator.sim.simulation_paused:
            # If not paused, pause the simulation.
            new_label = self.coordinator.sim.toggle_simulation(
                "sim_start_pause_button", app_data
            )
            dpg.set_item_label("sim_start_pause_button", new_label)
        # Step the simulation for one physics update.
        self.coordinator.sim.update_physics()
        # Update the step counter in the UI.
        dpg.set_value("step_text", f"Step: {self.coordinator.sim.step_counter}")

    def update(self):
        self.debug_draw.view_transform = self.coordinator.input.view_transform
