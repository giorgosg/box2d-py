# test_shapes.py

from test_base import BaseTest
from itertools import product
from shared import create_random_polygon

class RoundedShapes(BaseTest, category="Shapes", name="Rounded"):
    def setup(self):
        body = (self.world.new_body().static()
                .box(40, 2, offset=(0, -1))
                .box(2, 10, offset=(19, 5))
                .box(2, 10, offset=(-19, 5))
                .build())

        xcount, ycount = 10, 10
        xstart, ystart = -5, 2
        
        for x, y in product(range(xcount), range(ycount)):
            bb = (self.world.new_body().dynamic()
                  .position(xstart + x, ystart + y)
                  .create_random_polygon(0.5)
                  .build())


class Friction(BaseTest, category="Shapes", name="Friction"):
    def setup(self):
        # Create a static ground body.
        ground = self.world.new_body().static()
        ground.segment((-40, 0), (40, 0), friction=0.2)
        ground.box(26.0, 0.5, offset=(-4.0, 22.0), angle=-0.25, friction=0.2)
        ground.box(0.5, 2.0, offset=(10.5, 19.0), angle=0.0, friction=0.2)
        ground.box(26.0, 0.5, offset=(4.0, 14.0), angle=0.25, friction=0.2)
        ground.box(0.5, 2.0, offset=(-10.5, 11.0), angle=0.0, friction=0.2)
        ground.box(26.0, 0.5, offset=(-4.0, 6.0), angle=-0.25, friction=0.2)
        ground.build()

        # Create dynamic bodies.
        friction_values = [0.75, 0.5, 0.35, 0.1, 0.0]
        for i, f in enumerate(friction_values):
            x = -15.0 + 4.0 * i
            y = 28.0
            self.world.new_body().dynamic().position(x, y)\
                .box(1.0, 1.0, friction=f, density=25.0).build()