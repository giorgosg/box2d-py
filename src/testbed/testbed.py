import pyglet
from box2d import World, Vec2, DebugDraw, Body

class PygletDebugDraw(DebugDraw):
    def __init__(self, batch=None):
        super().__init__()
        self.batch = batch or pyglet.graphics.Batch()
        self.shapes = []
        
    def _draw_polygon(self, vertices, count, color):
        vertices = [(vertices[i].x, vertices[i].y) for i in range(count)]
        self.shapes.append(pyglet.shapes.Line(*vertices, color=self._b2color(color), 
                                           closed=True, batch=self.batch))
        
    def _draw_solid_polygon(self, transform, vertices, count, radius, color):
        verts = [self._transform_point(transform, vertices[i]) for i in range(count)]
        self.shapes.append(pyglet.shapes.Polygon(*verts, color=self._b2color(color), 
                                              batch=self.batch))
    
    def _transform_point(self, transform, point):
        x = transform.q.c * point.x - transform.q.s * point.y + transform.p.x
        y = transform.q.s * point.x + transform.q.c * point.y + transform.p.y
        return (x * 50, y * 50)
    
    def _b2color(self, color):
        return (color.r, color.g, color.b, color.a)

class TestbedApp:
    def __init__(self):
        self.world = World(gravity=(0, -10))
        self.window = pyglet.window.Window(1280, 720, vsync=False)
        self.batch = pyglet.graphics.Batch()
        self.debug_draw = PygletDebugDraw(self.batch)
        
        # Setup debug draw flags
        self.debug_draw.draw_shapes = True
        self.debug_draw.draw_joints = True
        
        # Test setup
        self._create_test_scene()
        
    def _create_test_scene(self):
        # Create ground
        ground = self.world.new_body().static().position(0, 0).build()
        ground.add_box(50, 1)
        
        # Create dynamic box
        body = self.world.new_body().dynamic().position(0, 5).build()
        body.add_box(1, 1, density=1, friction=0.3)

    def run(self):
        self._setup_handlers()
        pyglet.clock.schedule_interval(self._update, 1/60)
        pyglet.app.run()

    def _setup_handlers(self):
        @self.window.event
        def on_draw():
            self.window.clear()
            self.debug_draw.shapes.clear()
            self.world.draw(self.debug_draw)
            self.batch.draw()
            
    def _update(self, dt):
        self.world.step(dt, 6)
        
    def screen_to_world(self, pos):
        # Convert screen coordinates to physics world coordinates
        return Vec2(
            (pos[0] - self.window.width/2) / 50,
            (self.window.height/2 - pos[1]) / 50
        )

if __name__ == "__main__":
    app = TestbedApp()
    app.run()