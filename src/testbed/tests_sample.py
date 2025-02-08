import random
from test_base import BaseTest

class BenchmarkRainTest(BaseTest, category="Benchmark", name="Rain Test"):
    """
    A benchmark test that spawns many falling circle bodies (raindrops) to stress the physics simulation.
    
    Inspired by the BenchmarkRain sample in the C++ testbed, this test creates a large ground
    and then a number of random dynamic circles that fall under gravity.
    """
    def setup(self, world):
        # Create a large static ground body.
        world.new_body().static().position(0, -10).box(50, 10).build()
        
        num_drops = 150  # Number of raindrop bodies to create.
        for i in range(num_drops):
            x = random.uniform(-20, 20)
            y = random.uniform(10, 50)
            radius = random.uniform(0.1, 0.3)
            world.new_body().dynamic().position(x, y).circle(radius).build()


class PyramidTest(BaseTest, category="Performance", name="Pyramid Test"):
    """
    A test that builds a pyramid of boxes to demonstrate stacking and collision resolution.
    
    Inspired by the pyramid tests from the C++ testbed (e.g. in sample_bodies.cpp), this test creates
    a ground and then stacks a pyramid of dynamic box bodies.
    """
    def setup(self, world):
        # Create a static ground body.
        world.new_body().static().position(0, -10).box(50, 10).build()

        rows = 10
        box_half_size = 0.5  # Each box will be 1x1 (if box() takes half-dimensions).

        for i in range(rows):
            # In row i, we create (rows - i) boxes.
            count = rows - i
            # Center the row around x = 0.
            start_x = -count * box_half_size
            # Place rows so that the bottom row is just above the ground,
            # and each subsequent row is 1 unit higher, with a small spacing.
            y = box_half_size + i * (box_half_size * 2 + 0.01)
            for j in range(count):
                x = start_x + j * (box_half_size * 2)
                world.new_body().dynamic().position(x, y).box(box_half_size, box_half_size).build() 