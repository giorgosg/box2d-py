import random
import time
import dearpygui.dearpygui as dpg

from box2d import World, Vec2, ScaledTransform
from test_base import get_first_test, get_all_tests  # Default and tests tree.
from debug_draw_dpg import DearpyguiDebugDraw
import tests_sample
import tests_shapes

# Global configuration for the viewport.
WIDTH, HEIGHT = 1024, 768
CENTER = (WIDTH // 2, HEIGHT // 2)
SCALE = 30  # pixels per meter (initial zoom)

class TestBedDPG:
    def __init__(self, width=WIDTH, height=HEIGHT):
        self.width = width
        self.height = height
        self.last_mouse_pos = None  # For panning via mouse drag.

        # Layout constants for our UI.
        self.TEST_TREE_WIDTH = 160
        self.CONTROLS_HEIGHT = 40   # estimated height for top controls
        self.TOGGLES_HEIGHT = 40    # estimated height for the toggles window
        self.MARGIN = 20            # margin between canvas and test tree

        # Set up the physics world with gravity.
        self.world = World(gravity=(0, -10))
        # NEW: initialize the pending test flag.
        self.pending_test_cls = None
        self.current_test = None  # Active test instance.
        self.mouse_joint = None  # Active mouse joint, if any.

        # Maintain a view transform (panning/zooming)
        self.view_transform = ScaledTransform(
            position=CENTER,
            rotation=0,
            scale=(SCALE, -SCALE)
        )
        self.view_transform_inv = self.view_transform.inverse  # Cached inverse

        # Set up the Dear PyGui context, viewport and main UI window.
        dpg.create_context()
        dpg.create_viewport(title="Box2D TestBed - DearPyGui", width=self.width, height=self.height)

        # Create the main window.
        with dpg.window(label="TestBed", width=self.width, height=self.height, no_scrollbar=True, tag="main_window") as self.main_window:
            # Top controls.
            with dpg.group(horizontal=True, tag="controls_group"):
                dpg.add_text("Substeps:")
                dpg.add_input_int(tag="substeps_input", label="", default_value=4, width=100)
                dpg.add_text("Hertz:")
                dpg.add_input_int(tag="timestep_input", label="", default_value=60, width=100)
                dpg.add_button(label="Create Random Circle", callback=lambda: self.create_random_circle())
            
            # Calculate available height for our main content (the simulation canvas and test tree).
            content_height = self.height - self.CONTROLS_HEIGHT - self.TOGGLES_HEIGHT

            # Main content area: a horizontal split between the simulation canvas and the tests tree.
            with dpg.group(horizontal=True, tag="main_content"):
                canvas_width = self.width - self.TEST_TREE_WIDTH - self.MARGIN
                self.canvas = dpg.add_drawlist(tag="simulation_canvas",
                                               width=canvas_width,
                                               height=content_height)
                self.test_tree = dpg.add_child_window(tag="test_tree",
                                                      width=self.TEST_TREE_WIDTH,
                                                      height=content_height)
                # Build the tests tree on the right.
                self.build_tests_tree()

        # Initialize the debug draw AFTER the canvas is created.
        self.debug_draw = DearpyguiDebugDraw(self.canvas)
        self.debug_draw.view_transform = self.view_transform

        # Create a separate window for toggle buttons.
        with dpg.window(label="Debug Draw Toggles", pos=(0, self.height - 50), 
                        width=self.width, height=50, no_title_bar=True, no_move=True) as self.toggles_window:
            with dpg.group(horizontal=True, horizontal_spacing=10):
                dpg.add_checkbox(label="shapes", default_value=self.debug_draw.draw_shapes,
                                 callback=self._toggle_debug_draw, user_data="draw_shapes")
                dpg.add_checkbox(label="aabbs", default_value=self.debug_draw.draw_aabbs,
                                 callback=self._toggle_debug_draw, user_data="draw_aabbs")
                dpg.add_checkbox(label="joints", default_value=self.debug_draw.draw_joints,
                                 callback=self._toggle_debug_draw, user_data="draw_joints")
                dpg.add_checkbox(label="contacts", default_value=self.debug_draw.draw_contacts,
                                 callback=self._toggle_debug_draw, user_data="draw_contacts")
                dpg.add_checkbox(label="contact_normals", default_value=self.debug_draw.draw_contact_normals,
                                 callback=self._toggle_debug_draw, user_data="draw_contact_normals")
                dpg.add_checkbox(label="contact_impulses", default_value=self.debug_draw.draw_contact_impulses,
                                 callback=self._toggle_debug_draw, user_data="draw_contact_impulses")
                dpg.add_checkbox(label="friction_impulses", default_value=self.debug_draw.draw_friction_impulses,
                                 callback=self._toggle_debug_draw, user_data="draw_friction_impulses")
                dpg.add_checkbox(label="mass", default_value=self.debug_draw.draw_mass,
                                 callback=self._toggle_debug_draw, user_data="draw_mass")
                dpg.add_checkbox(label="joint_extras", default_value=self.debug_draw.draw_joint_extras,
                                 callback=self._toggle_debug_draw, user_data="draw_joint_extras")

        # Register global mouse event handlers.
        with dpg.handler_registry():
            dpg.add_mouse_wheel_handler(callback=self.on_mouse_scroll)
            dpg.add_mouse_down_handler(callback=self.global_mouse_down_handler)
            dpg.add_mouse_drag_handler(callback=self.global_mouse_drag_handler)
            dpg.add_mouse_release_handler(callback=self.global_mouse_release_handler)

        self.on_viewport_resize(None, None)  # Set initial sizes.

        # Auto-load a default test (e.g. the first registered one).
        default_test_cls = get_first_test()
        if default_test_cls is not None:
            self.load_test(default_test_cls)

    def build_tests_tree(self):
        """
        Build a tree widget inside the test_tree child window.
        """
        self.selectable_ids = [] 
        registry = get_all_tests()
        for category, tests in registry.items():
            with dpg.tree_node(label=category, default_open=False, parent=self.test_tree):
                for test_name, test_cls in tests.items():
                    selectable_id = dpg.add_selectable(
                        label=test_name,
                        callback=self.select_test_callback,
                        user_data=test_cls
                    )
                    self.selectable_ids.append(selectable_id)

    def select_test_callback(self, sender, app_data, user_data):
        """
        Callback when a test is clicked in the tests tree.
        Loads the selected test.
        """
        # Deselect all test selectables.
        for sid in self.selectable_ids:
            dpg.set_value(sid, False)
    
        # Mark the currently clicked selectable as selected.
        dpg.set_value(sender, True)
        
        # Load the corresponding test.
        self.load_test(user_data)

    def load_test(self, test_cls):
        """
        Loads (restarts) the simulation with the given test.
        """
        self.pending_test_cls = test_cls
        print(f"Test switch requested: {test_cls.__name__}")

    def _toggle_debug_draw(self, sender, app_data, user_data):
        """
        Toggle callback for updating DebugDraw properties.
        """
        new_value = dpg.get_value(sender)
        setattr(self.debug_draw, user_data, new_value)

    def on_mouse_scroll(self, sender, app_data):
        """
        Update the zoom level when the mouse wheel is scrolled.
        """
        zoom_speed = 1.1
        current_zoom = abs(self.view_transform._scale.x)
        if app_data > 0:
            new_zoom = current_zoom * zoom_speed
        elif app_data < 0:
            new_zoom = current_zoom / zoom_speed
        else:
            new_zoom = current_zoom

        # Clamp the zoom level.
        new_zoom = max(5, min(new_zoom, 200))
        self.view_transform.scale = Vec2(new_zoom, -new_zoom)
        self.view_transform_inv = self.view_transform.inverse

    def create_random_circle(self):
        x = random.uniform(-10, 10)
        y = random.uniform(10, 20)
        radius = random.uniform(0.5, 1.5)
        self.world.new_body().dynamic().position(x, y).circle(radius).build()

    def update_physics(self, dt):
        """
        Update the physics simulation using a fixed time step.
        """
        substeps = dpg.get_value("substeps_input")
        self.world.step(dt, substeps)

    def screen_to_world(self, pos):
        """
        Convert a screen coordinate to a Box2D world coordinate using
        the cached inverse of the view transform.
        """
        return self.view_transform_inv(pos)

    def global_mouse_down_handler(self, sender, app_data):
        """
        Global mouse down handler that checks if the canvas is hovered.
        """
        if not dpg.is_item_hovered(self.canvas):
            return
        if self.current_test is not None:
            pos = self.screen_to_world(dpg.get_drawing_mouse_pos())
            self.current_test.on_mouse_down(pos)

    def global_mouse_drag_handler(self, sender, app_data):
        """
        Global mouse drag handler that checks if the canvas is hovered.
        """
        if not dpg.is_item_hovered(self.canvas):
            return
        if self.current_test is not None:
            pos = self.screen_to_world(dpg.get_drawing_mouse_pos())
            # Here, we assume a zero relative motion; tests can override this behavior if needed.
            from box2d import Vec2
            self.current_test.on_mouse_drag(pos, Vec2(0, 0))

    def global_mouse_release_handler(self, sender, app_data):
        """
        Global mouse release handler that checks if the canvas is hovered.
        """
        if not dpg.is_item_hovered(self.canvas):
            return
        if self.current_test is not None:
            pos = self.screen_to_world(dpg.get_drawing_mouse_pos())
            self.current_test.on_mouse_release(pos)

    def update_panning(self):
        """
        Update the view transformation based on mouse dragging.
        """
        if dpg.is_mouse_button_down(1):  # Assumes right-click drag.
            current_mouse = dpg.get_mouse_pos()
            if self.last_mouse_pos is not None:
                dx = current_mouse[0] - self.last_mouse_pos[0]
                dy = current_mouse[1] - self.last_mouse_pos[1]
                new_pos = (self.view_transform.position.x + dx,
                           self.view_transform.position.y + dy)
                self.view_transform.position = new_pos
                self.view_transform_inv = self.view_transform.inverse
            self.last_mouse_pos = current_mouse
        else:
            self.last_mouse_pos = None

        self.debug_draw.view_transform = self.view_transform

    def on_viewport_resize(self, sender, app_data):
        """
        Callback when the viewport is resized.
        Updates the main window, canvas, test tree, view transform, and toggle elements.
        """
        new_width, new_height = dpg.get_viewport_width(), dpg.get_viewport_height()
        content_height = new_height - self.CONTROLS_HEIGHT - self.TOGGLES_HEIGHT
        canvas_width = new_width - self.TEST_TREE_WIDTH - self.MARGIN
        dpg.configure_item(self.main_window, width=new_width, height=new_height)
        dpg.configure_item(self.canvas, width=canvas_width, height=content_height)
        dpg.configure_item(self.test_tree, width=self.TEST_TREE_WIDTH, height=content_height)
        
        new_center = (canvas_width // 2, content_height // 2)
        self.view_transform.position = Vec2(*new_center)
        self.view_transform_inv = self.view_transform.inverse
        
        dpg.configure_item(self.toggles_window,
                           pos=(0, new_height - self.TOGGLES_HEIGHT),
                           width=new_width,
                           height=self.TOGGLES_HEIGHT)

    def run(self):
        """
        Main loop:
        - Applies any pending test switches.
        - Updates UI (and panning controls) each iteration.
        - Updates the physics simulation when enough time has accumulated.
        """
        dpg.setup_dearpygui()
        dpg.set_viewport_resize_callback(self.on_viewport_resize)
        dpg.show_viewport()
        dpg.set_primary_window(self.main_window, True)

        prev_time = time.perf_counter()
        accumulator = 0.0

        while dpg.is_dearpygui_running():
            # Process any pending test switch before simulation update.
            if self.pending_test_cls is not None:
                if self.world is not None:
                    self.world.destroy()
                self.world = World(gravity=(0, -10))
                self.current_test = self.pending_test_cls(self.world, self.debug_draw, None)
                self.current_test.setup()
                print(f"Loaded test: {self.pending_test_cls.__name__}")
                self.pending_test_cls = None
                accumulator = 0.0  # Reset physics accumulator

            current_time = time.perf_counter()
            elapsed = current_time - prev_time
            prev_time = current_time
            accumulator += elapsed

            # Update panning (UI interactions).
            self.update_panning()

            # Clear the canvas before drawing.
            dpg.delete_item(self.canvas, children_only=True)
            canvas_width = dpg.get_item_width(self.canvas)
            canvas_height = dpg.get_item_height(self.canvas)
            dpg.draw_rectangle((0, 0), (canvas_width, canvas_height),
                               fill=(60, 60, 60, 255),
                               color=(90, 90, 90, 255),
                               parent=self.canvas)
            # Draw the simulation state.
            self.world.draw(self.debug_draw)
            dpg.render_dearpygui_frame()

            # Determine physics update interval.
            timestep_hz = dpg.get_value("timestep_input")
            if timestep_hz <= 0:
                timestep_hz = 60.0
            physics_dt = 1.0 / timestep_hz

            while accumulator >= physics_dt:
                self.update_physics(physics_dt)
                accumulator -= physics_dt

            time.sleep(0.001)

        dpg.destroy_context()

if __name__ == "__main__":
    testbed = TestBedDPG()
    testbed.run()