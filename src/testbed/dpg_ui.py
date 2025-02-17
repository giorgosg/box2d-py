import dearpygui.dearpygui as dpg
from .base_test import get_first_test, get_all_tests
from .debug_draw_dpg import DearpyguiDebugDraw
from .simulation_settings import settings
from box2d import ScaledTransform, Vec2


class TestbedUI:
    """
    Handles all UI layout, window creation, and widget callbacks.
    """

    def __init__(self):
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
            width=settings.width,
            height=settings.height,
        )
        # Items with a tag starting with settings_ are automatically updated when a settings value
        # with what follows in their tag is changed.
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
                dpg.add_text("Threads:")
                dpg.add_input_int(
                    tag="settings_threads",
                    default_value=settings.threads,
                    width=80,
                    callback=self.on_ui_settings_change,
                    max_value=32,
                    min_value=1,
                    min_clamped=True,
                    max_clamped=True,
                )
                dpg.add_text("Substeps:")
                dpg.add_slider_int(
                    tag="settings_substeps",
                    default_value=settings.substeps,
                    width=80,
                    min_value=1,
                    max_value=40,
                    drop_callback=self.on_ui_settings_change,
                )
                dpg.add_text("Hertz:")
                dpg.add_slider_int(
                    tag="settings_hertz",
                    label="",
                    default_value=settings.hertz,
                    min_value=5,
                    max_value=240,
                    width=80,
                    callback=self.on_ui_settings_change,
                )
                dpg.add_checkbox(
                    tag="settings_enable_continuous",
                    label="Continuous Collision",
                    default_value=settings.enable_continuous,
                    callback=self.on_ui_settings_change,
                )
                dpg.add_checkbox(
                    tag="settings_enable_sleep",
                    label="Sleep",
                    default_value=settings.enable_sleep,
                    callback=self.on_ui_settings_change,
                )

            # Create the main content group.
            with dpg.group(horizontal=True, tag="main_content"):
                self.simulation_canvas = dpg.add_drawlist(
                    tag="simulation_canvas",
                    width=100,  # temp values
                    height=100,
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
                    tag="settings_draw_shapes",
                    label="shapes",
                    default_value=settings.draw_shapes,
                    callback=self.on_ui_settings_change,
                )
                dpg.add_checkbox(
                    tag="settings_draw_aabbs",
                    label="aabbs",
                    default_value=settings.draw_aabbs,
                    callback=self.on_ui_settings_change,
                )
                dpg.add_checkbox(
                    tag="settings_draw_joints",
                    label="joints",
                    default_value=settings.draw_joints,
                    callback=self.on_ui_settings_change,
                )
                dpg.add_checkbox(
                    tag="settings_draw_contacts",
                    label="contacts",
                    default_value=settings.draw_contacts,
                    callback=self.on_ui_settings_change,
                )
                dpg.add_checkbox(
                    tag="settings_draw_contact_normals",
                    label="contact_normals",
                    default_value=settings.draw_contact_normals,
                    callback=self.on_ui_settings_change,
                )
                dpg.add_checkbox(
                    tag="settings_draw_contact_impulses",
                    label="contact_impulses",
                    default_value=settings.draw_contact_impulses,
                    callback=self.on_ui_settings_change,
                )
                dpg.add_checkbox(
                    tag="settings_draw_friction_impulses",
                    label="friction_impulses",
                    default_value=settings.draw_friction_impulses,
                    callback=self.on_ui_settings_change,
                )
                dpg.add_checkbox(
                    tag="settings_draw_mass",
                    label="mass",
                    default_value=settings.draw_mass,
                    callback=self.on_ui_settings_change,
                )
                dpg.add_checkbox(
                    tag="settings_draw_joint_extras",
                    label="joint_extras",
                    default_value=settings.draw_joint_extras,
                    callback=self.on_ui_settings_change,
                )

        dpg.set_viewport_resize_callback(self.on_viewport_resize)

        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window(self.main_window, True)

        self.input = TestbedInput(self.simulation_canvas)
        settings.subscribe(self.on_settings_changed)
        settings.subscribe(
            self.on_update_perf,
            "step_count",
            "physics_ms_avg",
            "physics_ms",
            "debug_draw_ms_avg",
            "debug_draw_ms",
        )
        # Update positions and sizes using the viewport's current dimensions.
        self.on_viewport_resize(None, None)
        settings.subscribe(self.build_test_ui, "current_test_obj")
        if settings.current_test_obj:
            self.build_test_ui(None, settings.current_test_obj)

    def build_tests_tree(self):
        self.test_selectable_ids = []
        if not settings.all_tests:
            return
        for category, tests in settings.all_tests.items():
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
            min_size=(ui_window_width, 30),
        ):
            self.test_ui_container = dpg.add_child_window(tag="test_ui_container")
        return self.test_ui_container

    def build_test_ui(self, key, test):
        """
        Build UI controls for a test based on its ui_elements descriptors.
        Supported controls: combo, button, checkbox.
        """
        self.create_test_ui_window(test)
        # Start with any UI elements defined by the test.
        ui_elements = []
        if hasattr(test, "ui_elements"):
            ui_elements.extend(test.ui_elements)
        # Also append default UI elements (e.g. reset button) from BaseTest.
        if hasattr(test, "get_default_ui_elements"):
            ui_elements.extend(test.get_default_ui_elements())

        # Helper function to create a callback wrapper that captures the callback and its user_data.
        def create_callback(element):
            if element.user_data is not None:

                def wrapped(sender, app_data):
                    return element.callback(element.key, app_data, element.user_data)

            else:

                def wrapped(sender, app_data):
                    return element.callback(element.key, app_data)

            return wrapped

        for element in ui_elements:
            callback_kwargs = {}
            if callable(element.callback):
                callback_kwargs["callback"] = create_callback(element)
            else:
                print(f"Element {element.label} has no callable callback.")

            if element.control_type == "combo":
                dpg.add_combo(
                    parent=self.test_ui_container,
                    label=element.label,
                    items=element.options,
                    default_value=element.default,
                    **callback_kwargs,
                )
            elif element.control_type == "button":
                dpg.add_button(
                    parent=self.test_ui_container,
                    label=element.label,
                    **callback_kwargs,
                )
            elif element.control_type == "checkbox":
                dpg.add_checkbox(
                    parent=self.test_ui_container,
                    label=element.label,
                    default_value=element.default,
                    **callback_kwargs,
                )
            elif element.control_type == "int_input":
                dpg.add_slider_int(
                    parent=self.test_ui_container,
                    label=element.label,
                    default_value=element.default,
                    min_value=element.min_value,
                    max_value=element.max_value,
                    **callback_kwargs,
                )
        # container_height = dpg.get_item_height("test_ui_container")
        new_height = len(ui_elements) * 25 + 45
        print(new_height)
        dpg.configure_item(
            "test_ui_window",
            height=new_height,
            pos=(10, settings.height - new_height - 50),
        )

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
        settings.width, settings.height = new_width, new_height

    # --- Callback wrappers ---
    def on_toggle_simulation(self, sender, app_data, user_data=None):
        settings.simulation_paused = not settings.simulation_paused
        new_label = "Play" if settings.simulation_paused else "Pause"
        dpg.set_item_label("sim_start_pause_button", new_label)

    def on_test_select(self, sender, app_data, user_data):
        for sid in self.test_selectable_ids:
            dpg.set_value(sid, False)
        dpg.set_value(sender, True)
        settings.current_test = user_data

    def on_step_simulation(self, sender, app_data, user_data=None):
        """
        Callback for the 'Step' button.
        If the simulation is running, pause it first.
        Then step the simulation for one physics update.
        """
        if not settings.simulation_paused:
            self.on_toggle_simulation(None, None)
        settings.step_number += 1

    def on_update_perf(self, key, value):
        # print(f"update perf: {key}: {value}")
        if key == "step_count":
            dpg.set_value("step_text", f"Step: {value}")
        if key == "debug_draw_ms_avg":
            dpg.set_value("draw_time_text", f"Draw: {value:.2f}")
        if key in ("physics_ms", "physics_ms_avg"):
            if settings.simulation_paused:
                phys = f"Physics: {settings.physics_ms:.2f} ms"
            else:
                phys = f"Physics: {settings.physics_ms_avg:.2f} ms (avg)"
            dpg.set_value("physics_time_text", phys)

    def on_ui_settings_change(self, sender, app_data, user_data=None):
        """
        Callback for when the user changes one of the ui settings that map
        to the settings controler.
        """
        sender_tag = dpg.get_item_info(sender).get("tag", sender)
        settings_key = sender_tag.removeprefix("settings_")
        setattr(settings, settings_key, dpg.get_value(sender))

    def on_settings_changed(self, key, new_value):
        """
        Callback for when a simulation setting is updated externally.
        This method updates the corresponding UI widget.
        """
        widget_tag = "settings_" + key
        if dpg.does_item_exist(widget_tag):
            dpg.set_value(widget_tag, new_value)


class TestbedInput:
    """
    Handles mouse, viewport, and coordinate transforms.
    """

    def __init__(self, simulation_canvas):
        self.simulation_canvas = simulation_canvas
        self.last_mouse_pos = None
        self.last_drag_pos = None
        self.update_transform()
        settings.subscribe(self.update_transform, "center", "scale", "width", "height")
        # Register global mouse event handlers.
        with dpg.handler_registry():
            dpg.add_mouse_wheel_handler(callback=self.on_mouse_scroll)
            dpg.add_mouse_click_handler(
                callback=self.global_mouse_down_handler, button=dpg.mvMouseButton_Left
            )
            dpg.add_mouse_drag_handler(
                callback=self.global_mouse_drag_handler, button=dpg.mvMouseButton_Left
            )
            dpg.add_mouse_release_handler(
                callback=self.global_mouse_release_handler,
                button=dpg.mvMouseButton_Left,
            )
            dpg.add_mouse_drag_handler(
                button=dpg.mvMouseButton_Right, callback=self.update_panning
            )
            dpg.add_mouse_release_handler(
                callback=self.stop_panning, button=dpg.mvMouseButton_Right
            )

    def update_transform(self, key=None, value=None):
        canvas_width = dpg.get_item_width(self.simulation_canvas)
        canvas_height = dpg.get_item_height(self.simulation_canvas)
        canvas = Vec2(canvas_width, canvas_height) / 2
        s = settings.scale
        p = Vec2(*settings.center)
        self.view_transform = ScaledTransform(
            position=Vec2(canvas.x - p.x * s, canvas.y + p.y * s),
            rotation=0,
            scale=(settings.scale, -settings.scale),
        )

    def on_mouse_scroll(self, sender, app_data):
        # Only zoom if the mouse is over the simulation canvas.
        if not dpg.is_item_hovered(self.simulation_canvas):
            return
        zoom_speed = 1.1
        current_zoom = settings.scale
        if app_data > 0:
            new_zoom = current_zoom * zoom_speed
        elif app_data < 0:
            new_zoom = current_zoom / zoom_speed
        else:
            new_zoom = current_zoom
        new_zoom = max(5, min(new_zoom, 200))
        settings.scale = new_zoom

    def update_panning(self, sender, app_data):
        if not dpg.is_item_hovered(self.simulation_canvas):
            self.last_drag_pos = None
            return

        current_mouse_pos = dpg.get_mouse_pos()
        if self.last_drag_pos is None:
            self.last_drag_pos = current_mouse_pos
            return

        dx = current_mouse_pos[0] - self.last_drag_pos[0]
        dy = current_mouse_pos[1] - self.last_drag_pos[1]

        # Update last_right_mouse_pos for the next callback.
        self.last_drag_pos = current_mouse_pos

        world_dx = dx / settings.scale
        world_dy = -dy / settings.scale

        settings.center = Vec2(
            settings.center[0] - world_dx,
            settings.center[1] - world_dy,
        )

    def stop_panning(self, sender, app_data):
        self.last_drag_pos = None

    # What's up with that offset needed....?
    def global_mouse_down_handler(self, sender, app_data):
        if not dpg.is_item_hovered(self.simulation_canvas):
            return
        canvas_min = dpg.get_item_pos(self.simulation_canvas)
        mouse_pos = dpg.get_mouse_pos()
        local_mouse = Vec2(*mouse_pos) - canvas_min - (7, 10)
        pos = self.view_transform.inverse(local_mouse)
        settings.current_test_obj.on_mouse_down(pos)

    def global_mouse_drag_handler(self, sender, app_data):
        if not dpg.is_item_hovered(self.simulation_canvas):
            return
        canvas_min = dpg.get_item_pos(self.simulation_canvas)
        mouse_pos = dpg.get_mouse_pos()
        local_mouse = Vec2(*mouse_pos) - canvas_min - (7, 10)
        pos = self.view_transform.inverse(local_mouse)
        settings.current_test_obj.on_mouse_drag(pos, Vec2(0, 0))

    def global_mouse_release_handler(self, sender, app_data):
        # if not dpg.is_item_hovered(self.simulation_canvas):
        #    return
        canvas_min = dpg.get_item_pos(self.simulation_canvas)
        mouse_pos = dpg.get_mouse_pos()
        local_mouse = Vec2(*mouse_pos) - canvas_min - (7, 10)
        pos = self.view_transform.inverse(local_mouse)
        settings.current_test_obj.on_mouse_release(pos)
