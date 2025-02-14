from .base_test import BaseTest
import itertools


class BenchmarkCompound(BaseTest, category="Benchmark", name="Compound"):
    def setup(self):
        grid = 1.0
        rows, cols = 30, 30
        ground = self.world.new_body().static()

        ground_box_offsets = (
            (sign * grid * j, grid * i)
            for sign in (1, -1)
            for i in range(rows)
            for j in range(i, cols)
        )

        for offset in ground_box_offsets:
            ground.box(1.0, 1.0, offset=offset, friction=0.2)
        ground.build()

        count_x, count_y = 5, 5
        spacing_x, spacing_y = 3.0, 3.0
        start_x = -((count_x - 1) * spacing_x) / 2
        start_y = 50 - ((count_y - 1) * spacing_y) / 2

        fixture_positions = list(itertools.product([-1.0, 0.0, 1.0], repeat=2))

        # Create dynamic bodies in a grid layout.
        for row, col in itertools.product(range(count_y), range(count_x)):
            pos_x = start_x + col * spacing_x
            pos_y = start_y + row * spacing_y
            body_builder = self.world.new_body().dynamic().position(pos_x, pos_y)
            for offset in fixture_positions:
                body_builder.box(1.0, 1.0, offset=offset, density=1.0)
            body_builder.build()
