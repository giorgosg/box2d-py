from .base_test import BaseTest, UI
import itertools


class BenchmarkCompound(BaseTest, category="Benchmark", name="Compound"):
    count = UI.int(3, max=10, min=2)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @count.callback
    def on_count_change(self, key, value):
        for body in self.world.bodies:
            body.destroy()
        self.setup()

    def setup(self):
        grid = 1.0
        rows, cols = self.count * 3 + 5, self.count * 3 + 5
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

        count_x, count_y = self.count, self.count
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
