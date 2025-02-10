import time
import math
import dearpygui.dearpygui as dpg

from box2d import World, Vec2, ScaledTransform
from test_base import get_first_test, get_all_tests
from debug_draw_dpg import DearpyguiDebugDraw
import tests_sample
import tests_shapes


class TestbedConfig:
    WIDTH = 1024
    HEIGHT = 768
    CENTER = (WIDTH // 2, HEIGHT // 2)
    SCALE = 30  # pixels per meter (initial zoom)


class TestbedUI:
    """
    Handles all UI layout, window creation, and widget callbacks.
    """
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.width = coordinator.config.WIDTH
        self.height = coordinator.config.HEIGHT

        # Layout constants
        self.CONTROLS_HEIGHT = 40
        self.TOGGLES_HEIGHT = 35
        self.TEST_TREE_WIDTH = 160
        self.MARGIN = 20

        # UI object handles
        self.main_window = None
        self.canvas = None
        self.test_tree = None
        self.toggles_window = None
        self.test_ui_container = None
        self.selectable_ids = []
        self.debug_draw = None

    def initialize(self):
        dpg.create_context()
        dpg.configure_app(manual_callback_management=True)
        dpg.create_viewport(title="Box2D TestBed - DearPyGui", width=self.width, height=self.height)
        
        # Main window containing controls and main content.
        with dpg.window(label="TestBed", width=self.width, height=self.height,
                        no_scrollbar=True, tag="main_window") as self.main_window:
            # Top controls group.
            with dpg.group(horizontal=True, tag="controls_group"):
                dpg.add_button(label="Pause", tag="sim_start_pause_button",
                               callback=self.on_toggle_simulation)
                dpg.add_text("Substeps:")
                dpg.add_input_int(tag="substeps_input", label="", default_value=4, width=80,
                                  callback=self.on_physics_settings_change)
                dpg.add_text("Hertz:")
                dpg.add_input_int(tag="timestep_input", label="", default_value=60, width=80,
                                  callback=self.on_physics_settings_change)
                dpg.add_checkbox(tag="enable_continuous_checkbox",
                                 label="Continuous Collision",
                                 default_value=self.coordinator.sim.world.enable_continuous,
                                 callback=self.on_toggle_continuous)
                dpg.add_checkbox(tag="enable_sleep_checkbox",
                                 label="Sleep",
                                 default_value=self.coordinator.sim.world.enable_sleep,
                                 callback=self.on_toggle_sleep)
            
            # Calculate available height
            content_height = self.height - self.CONTROLS_HEIGHT - self.TOGGLES_HEIGHT

            # Main content area: simulation canvas and tests tree.
            with dpg.group(horizontal=True, tag="main_content"):
                canvas_width = self.width - self.TEST_TREE_WIDTH - self.MARGIN
                self.canvas = dpg.add_drawlist(tag="simulation_canvas", width=canvas_width, height=content_height)
                self.test_tree = dpg.add_child_window(tag="test_tree", width=self.TEST_TREE_WIDTH, height=content_height)
                self.build_tests_tree()

        # Initialize the debug draw so that its flags can be used
        # for the toggles window.
        self.debug_draw = DearpyguiDebugDraw(self.canvas)
        self.debug_draw.view_transform = self.coordinator.input.view_transform

        # Create the debug draw toggles window
        with dpg.window(
            label="Debug Draw Toggles",
            pos=(0, self.height - self.TOGGLES_HEIGHT),
            width=self.width,
            height=self.TOGGLES_HEIGHT,
            no_title_bar=True,
            no_move=True
        ) as self.toggles_window:
            with dpg.group(horizontal=True, horizontal_spacing=10):
                dpg.add_checkbox(label="shapes",
                                 default_value=self.debug_draw.draw_shapes,
                                 callback=self.on_toggle_debug_draw, user_data="draw_shapes")
                dpg.add_checkbox(label="aabbs",
                                 default_value=self.debug_draw.draw_aabbs,
                                 callback=self.on_toggle_debug_draw, user_data="draw_aabbs")
                dpg.add_checkbox(label="joints",
                                 default_value=self.debug_draw.draw_joints,
                                 callback=self.on_toggle_debug_draw, user_data="draw_joints")
                dpg.add_checkbox(label="contacts",
                                 default_value=self.debug_draw.draw_contacts,
                                 callback=self.on_toggle_debug_draw, user_data="draw_contacts")
                dpg.add_checkbox(label="contact_normals",
                                 default_value=self.debug_draw.draw_contact_normals,
                                 callback=self.on_toggle_debug_draw, user_data="draw_contact_normals")
                dpg.add_checkbox(label="contact_impulses",
                                 default_value=self.debug_draw.draw_contact_impulses,
                                 callback=self.on_toggle_debug_draw, user_data="draw_contact_impulses")
                dpg.add_checkbox(label="friction_impulses",
                                 default_value=self.debug_draw.draw_friction_impulses,
                                 callback=self.on_toggle_debug_draw, user_data="draw_friction_impulses")
                dpg.add_checkbox(label="mass",
                                 default_value=self.debug_draw.draw_mass,
                                 callback=self.on_toggle_debug_draw, user_data="draw_mass")
                dpg.add_checkbox(label="joint_extras",
                                 default_value=self.debug_draw.draw_joint_extras,
                                 callback=self.on_toggle_debug_draw, user_data="draw_joint_extras")

        # Register global mouse event handlers.
        with dpg.handler_registry():
            dpg.add_mouse_wheel_handler(callback=self.coordinator.input.on_mouse_scroll)
            dpg.add_mouse_down_handler(callback=self.coordinator.input.global_mouse_down_handler)
            dpg.add_mouse_drag_handler(callback=self.coordinator.input.global_mouse_drag_handler)
            dpg.add_mouse_release_handler(callback=self.coordinator.input.global_mouse_release_handler)

        dpg.set_viewport_resize_callback(self.on_viewport_resize)

        # Load a default test if one is available.
        default_test_cls = get_first_test()
        if default_test_cls is not None:
            self.coordinator.sim.load_test(default_test_cls)

        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window(self.main_window, True)

    def build_tests_tree(self):
        self.selectable_ids = []
        registry = get_all_tests()
        for category, tests in registry.items():
            with dpg.tree_node(label=category, default_open=False, parent=self.test_tree):
                for test_name, test_cls in tests.items():
                    selectable_id = dpg.add_selectable(label=test_name, callback=self.on_test_select, user_data=test_cls)
                    self.selectable_ids.append(selectable_id)

    def create_test_ui_window(self, test_cls):
        if dpg.does_item_exist("test_ui_window"):
            dpg.delete_item("test_ui_window")
        window_width = 220
        window_height = 150
        with dpg.window(label=f"{test_cls.category} - {test_cls.name}",
                        tag="test_ui_window",
                        pos=(10, dpg.get_viewport_height() - window_height - 50),
                        no_close=True,
                        width=window_width) as window:
            dpg.add_button(label="Reset Test", callback=self.on_reset_test)
            self.test_ui_container = dpg.add_child_window(tag="test_ui_container")
        return self.test_ui_container

    def clear_canvas(self):
        dpg.delete_item(self.canvas, children_only=True)
        canvas_width = dpg.get_item_width(self.canvas)
        canvas_height = dpg.get_item_height(self.canvas)
        dpg.draw_rectangle((0, 0),
                           (canvas_width, canvas_height),
                           fill=(60, 60, 60, 255),
                           color=(90, 90, 90, 255),
                           parent=self.canvas)

    def on_viewport_resize(self, sender, app_data):
        new_width, new_height = dpg.get_viewport_width(), dpg.get_viewport_height()
        content_height = new_height - self.CONTROLS_HEIGHT - self.TOGGLES_HEIGHT
        canvas_width = new_width - self.TEST_TREE_WIDTH - self.MARGIN
        dpg.configure_item(self.main_window, width=new_width, height=new_height)
        dpg.configure_item(self.canvas, width=canvas_width, height=content_height)
        dpg.configure_item(self.test_tree, width=self.TEST_TREE_WIDTH, height=content_height)
        new_center = (canvas_width // 2, content_height // 2)
        self.coordinator.input.set_view_center(new_center)
        dpg.configure_item(self.toggles_window,
                           pos=(0, new_height - self.TOGGLES_HEIGHT),
                           width=new_width,
                           height=self.TOGGLES_HEIGHT)

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
        for sid in self.selectable_ids:
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

    def update(self):
        self.debug_draw.view_transform = self.coordinator.input.view_transform


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
        self.substeps = 4  # default value matching the UI

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
        container = self.coordinator.ui.create_test_ui_window(test_cls)
        self.current_test = test_cls(self.world, self.coordinator.ui.debug_draw, container)
        self.current_test.setup()
        self.coordinator.reset_accumulator()

    def update_physics(self):
        """
        Update the world by stepping the physics simulation.
       """
        self.world.step(self.physics_dt, self.substeps)

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
            position=center,
            rotation=0,
            scale=(scale, -scale)
        )
        self.view_transform_inv = self.view_transform.inverse

    def on_mouse_scroll(self, sender, app_data):
        zoom_speed = 1.1
        current_zoom = abs(self.view_transform._scale.x)
        if app_data > 0:
            new_zoom = current_zoom * zoom_speed
        elif app_data < 0:
            new_zoom = current_zoom / zoom_speed
        else:
            new_zoom = current_zoom
        new_zoom = max(5, min(new_zoom, 200))
        self.view_transform.scale = Vec2(new_zoom, -new_zoom)
        self.view_transform_inv = self.view_transform.inverse

    def update_panning(self):
        if dpg.is_mouse_button_down(1):  # Right-click drag.
            current_mouse = dpg.get_mouse_pos()
            if self.last_mouse_pos is not None:
                dx = current_mouse[0] - self.last_mouse_pos[0]
                dy = current_mouse[1] - self.last_mouse_pos[1]
                new_x = self.view_transform.position.x + dx
                new_y = self.view_transform.position.y + dy
                self.view_transform.position = (new_x, new_y)
                self.view_transform_inv = self.view_transform.inverse
            self.last_mouse_pos = current_mouse
        else:
            self.last_mouse_pos = None

    def screen_to_world(self, pos):
        return self.view_transform.inverse(pos)

    def global_mouse_down_handler(self, sender, app_data):
        if not dpg.is_item_hovered(self.coordinator.ui.canvas):
            return
        if self.coordinator.sim.current_test and hasattr(self.coordinator.sim.current_test, "on_mouse_down"):
            pos = self.screen_to_world(dpg.get_drawing_mouse_pos())
            self.coordinator.sim.current_test.on_mouse_down(pos)

    def global_mouse_drag_handler(self, sender, app_data):
        if not dpg.is_item_hovered(self.coordinator.ui.canvas):
            return
        if self.coordinator.sim.current_test and hasattr(self.coordinator.sim.current_test, "on_mouse_drag"):
            pos = self.screen_to_world(dpg.get_drawing_mouse_pos())
            self.coordinator.sim.current_test.on_mouse_drag(pos, Vec2(0, 0))

    def global_mouse_release_handler(self, sender, app_data):
        if not dpg.is_item_hovered(self.coordinator.ui.canvas):
            return
        if self.coordinator.sim.current_test and hasattr(self.coordinator.sim.current_test, "on_mouse_release"):
            pos = self.screen_to_world(dpg.get_drawing_mouse_pos())
            self.coordinator.sim.current_test.on_mouse_release(pos)

    def set_view_center(self, new_center):
        self.view_transform.position = Vec2(*new_center)
        self.view_transform_inv = self.view_transform.inverse


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

            self.ui.clear_canvas()
            self.sim.draw()

            # Fixed timestep simulation update.
            if not self.sim.simulation_paused:
                while self.accumulator >= self.sim.physics_dt:
                    self.sim.update_physics()
                    self.accumulator -= self.sim.physics_dt

            dpg.render_dearpygui_frame()
            time.sleep(0.001)
        dpg.destroy_context()


if __name__ == "__main__":
    coordinator = TestbedCoordinator()
    coordinator.run()