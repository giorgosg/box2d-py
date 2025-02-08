import math
import random
import time
import dearpygui.dearpygui as dpg

from box2d import World, Vec2, ScaledTransform
from test_base import get_first_test  # Test registration and sample test.
from debug_draw_dpg import DearpyguiDebugDraw

# Global configuration for the viewport.
WIDTH, HEIGHT = 800, 600
CENTER = (WIDTH // 2, HEIGHT // 2)
SCALE = 30  # pixels per meter (initial zoom)

class TestBedDPG:
    def __init__(self, width=WIDTH, height=HEIGHT):
        self.width = width
        self.height = height
        self.last_mouse_pos = None  # Used for panning via mouse drag.

        # Set up the physics world with gravity.
        self.world = World(gravity=(0, -10))

        # Maintain a view transform (panning/zooming)
        self.view_transform = ScaledTransform(
            position=CENTER,
            rotation=0,
            scale=(SCALE, -SCALE)
        )

        # Set up the Dear PyGui context, viewport and UI.
        dpg.create_context()
        dpg.create_viewport(title="Box2D TestBed - DearPyGui", width=self.width, height=self.height)

        with dpg.window(label="TestBed", width=self.width, height=self.height, no_scrollbar=True) as self.main_window:
            # Place controls on top.
            with dpg.group(horizontal=True):
                dpg.add_text("Substeps:")
                dpg.add_input_int(tag="substeps_input", label="", default_value=4, width=100)
                dpg.add_text("Hertz:")
                dpg.add_input_float(tag="timestep_input", label="", default_value=60.0, width=100)
                dpg.add_button(label="Create Random Circle", callback=lambda: self.create_random_circle())
            # Create a drawing canvas for simulation rendering.
            self.canvas = dpg.add_drawlist(width=self.width, height=self.height)

        # Register the mouse wheel handler to handle zoom changes.
        with dpg.handler_registry():
            dpg.add_mouse_wheel_handler(callback=self.on_mouse_scroll)

        # Set up our debug draw (which uses the canvas).
        self.debug_draw = DearpyguiDebugDraw(self.canvas)
        self.debug_draw.view_transform = self.view_transform

        self.on_viewport_resize(None, None)
        # Create the simulation objects using the first registered test.
        self.test = get_first_test()
        self.test().setup(self.world)

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

    def update_panning(self):
        """
        Independently update the view transformation based on panning input,
        so that the UI and panning remain responsive.
        """
        if dpg.is_mouse_button_down(1):  # Assumes right-click drag.
            current_mouse = dpg.get_mouse_pos()
            if self.last_mouse_pos is not None:
                dx = current_mouse[0] - self.last_mouse_pos[0]
                dy = current_mouse[1] - self.last_mouse_pos[1]
                new_pos = (self.view_transform.position.x + dx,
                           self.view_transform.position.y + dy)
                self.view_transform.position = new_pos
                self.view_transform._recalc_matrix()
            self.last_mouse_pos = current_mouse
        else:
            self.last_mouse_pos = None

        self.debug_draw.view_transform = self.view_transform

    def on_viewport_resize(self, sender, app_data):
        """
        Callback when the viewport is resized, ensuring our window and canvas update accordingly.
        """
        new_width, new_height = dpg.get_viewport_width(), dpg.get_viewport_height()
        canvas_height = new_height - 40  # Adjust appropriately.
        canvas_width = new_width - 16    # Adjust appropriately.
        dpg.configure_item(self.main_window, width=new_width, height=new_height)
        dpg.configure_item(self.canvas, width=canvas_width, height=canvas_height)
        new_center = (new_width // 2, new_height // 2)
        self.view_transform.position = Vec2(*new_center)

    def run(self):
        """
        Main loop:
        - The UI (and panning controls) are updated every iteration.
        - Physics is updated only when enough time has accumulated, as determined
          by the "Timestep (Hz)" value.
        This decouples the UI refresh rate from the simulation update rate.
        """
        dpg.setup_dearpygui()
        dpg.set_viewport_resize_callback(self.on_viewport_resize)
        dpg.show_viewport()
        dpg.set_primary_window(self.main_window, True)

        prev_time = time.perf_counter()
        accumulator = 0.0

        while dpg.is_dearpygui_running():
            current_time = time.perf_counter()
            elapsed = current_time - prev_time
            prev_time = current_time
            accumulator += elapsed

            # Update panning (UI interactions) every frame.
            self.update_panning()

            # Update the UI (clear canvas, draw current simulation state).
            dpg.delete_item(self.canvas, children_only=True)
            self.world.draw(self.debug_draw)
            dpg.render_dearpygui_frame()

            # Determine desired physics update interval based on UI control.
            timestep_hz = dpg.get_value("timestep_input")
            if timestep_hz <= 0:
                timestep_hz = 60.0
            physics_dt = 1.0 / timestep_hz

            # Run physics updates if enough time has accumulated.
            while accumulator >= physics_dt:
                self.update_physics(physics_dt)
                accumulator -= physics_dt

            # Yield a bit to prevent 100% CPU usage.
            time.sleep(0.001)

        dpg.destroy_context()


if __name__ == "__main__":
    testbed = TestBedDPG()
    testbed.run()