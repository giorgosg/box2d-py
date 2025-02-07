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
            with dpg.group(horizontal=True):
                dpg.add_button(label="Create Random Circle", callback=lambda: self.create_random_circle())
                dpg.add_button(label="Quit", callback=lambda: dpg.stop_dearpygui())
            # Create a drawing canvas where the simulation will be rendered.
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
        Positive app_data zooms in, negative zooms out.
        """
        zoom_speed = 1.1
        current_zoom = abs(self.view_transform._scale.x)
        if app_data > 0:
            new_zoom = current_zoom * zoom_speed
        elif app_data < 0:
            new_zoom = current_zoom / zoom_speed
        else:
            new_zoom = current_zoom

        # Optionally, clamp the zoom level
        new_zoom = max(5, min(new_zoom, 200))
        self.view_transform.scale = Vec2(new_zoom, -new_zoom)

    def create_random_circle(self):
        x = random.uniform(-10, 10)
        y = random.uniform(10, 20)
        radius = random.uniform(0.5, 1.5)
        self.world.new_body().dynamic().position(x, y).circle(radius).build()

    def update(self, dt):
        """
        Update the simulation for the given time step.
        Also handles panning via right–click dragging.
        """
        self.world.step(dt, 4)

        # Panning: if the right mouse button is pressed, update the transform.
        if dpg.is_mouse_button_down(1):  # Assumes right-click.
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

        # Ensure the debug draw uses the updated view transformation.
        self.debug_draw.view_transform = self.view_transform

    def on_viewport_resize(self, sender, app_data):
        """
        Callback when the viewport (OS-level window) is resized.
        """
        # Get the client area's width and height.
        new_width, new_height = dpg.get_viewport_width(), dpg.get_viewport_height()
        canvas_height = new_height - 40 # there must be a better way to do this
        canvas_width = new_width - 16   # ...
        dpg.configure_item(self.main_window, width=new_width, height=new_height)
        dpg.configure_item(self.canvas, width=canvas_width, height=canvas_height)
        new_center = (new_width // 2, new_height // 2)
        # Update the view transform to be centered according to the new client size.
        self.view_transform.position = Vec2(*new_center)

    def run(self):
        """
        Main loop: repeatedly step the simulation and refresh the render.
        """
        dpg.setup_dearpygui()
        # Register the viewport resize callback so our main window and canvas stay in sync.
        dpg.set_viewport_resize_callback(self.on_viewport_resize)
        dpg.show_viewport()
        # Set the main window as the primary, so it fills the entire viewport.
        dpg.set_primary_window(self.main_window, True)
        previous_time = time.perf_counter()
        while dpg.is_dearpygui_running():
            current_time = time.perf_counter()
            dt = current_time - previous_time
            previous_time = current_time
            # Here we use a fixed time step (1/60 s) for physics stepping.
            self.update(1.0 / 60.0)
            # Clear the canvas from the previous frame.
            dpg.delete_item(self.canvas, children_only=True)
            # Ask the world to draw itself using our debug draw.
            self.world.draw(self.debug_draw)
            dpg.render_dearpygui_frame()
        dpg.destroy_context()


if __name__ == "__main__":
    testbed = TestBedDPG()
    testbed.run()