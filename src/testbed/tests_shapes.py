# test_shapes.py

from test_base import BaseTest
from itertools import product
from shared import create_random_polygon

class RoundedShapes(BaseTest, category="Shapes", name="Rounded"):
    def setup(self, world):
        body = (world.new_body().static()
                .box(40, 2, offset=(0, -1))
                .box(2, 10, offset=(19, 5))
                .box(2, 10, offset=(-19,5))
                .build())

        xcount, ycount = 10, 10
        xstart, ystart = -5, 2
        
        for x, y in product(range(xcount), range(ycount)):
            bb = (world.new_body().dynamic()
                  .position(xstart + x, ystart + y)
                  .create_random_polygon(0.5).build())
            


