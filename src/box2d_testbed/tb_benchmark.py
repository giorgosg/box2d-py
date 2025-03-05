from .base_test import BaseTest, UI
import itertools
import math
from box2d import World, Vec2, Rot


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


def pyramid(world: World, base_count: int, box_size: float, base_position: Vec2):
    bb = world.new_body().dynamic().box(box_size, box_size)
    top_pos = base_position + Vec2(0, box_size / 2 + base_count * box_size)
    box_positions = (
        top_pos - Vec2(col * box_size - row * box_size / 2, row * box_size)
        for row in range(base_count + 1)
        for col in range(row)
    )
    bodies = [bb.position(*pos).build() for pos in box_positions]
    return bodies


class PyramidTest(BaseTest, category="Benchmark", name="Pyramid Test"):
    base_count = UI.int(20, min=5, max=100)

    @base_count.callback
    def on_count_change(self, key, value):
        self.on_reset(key, value)

    def setup(self):
        # Create a static ground body.
        self.world.new_body().static().position(0, -10).box(200, 20).build()
        self.boxes = pyramid(self.world, self.base_count, 1, Vec2(0, 0))


class ManyPyramids(BaseTest, category="Benchmark", name="Many Pyramids"):
    gridcount = UI.int(5, min=2, max=10)

    @gridcount.callback
    def on_grid_change(self, key, value):
        self.on_reset(key, value)

    def setup(self):
        pyramid_base = 10
        ground = self.world.new_body().static()
        ground_width = (pyramid_base + 1) * self.gridcount
        segments = [
            (
                Vec2(-ground_width / 2, y * (pyramid_base + 1)),
                Vec2(ground_width / 2, y * (pyramid_base + 1)),
            )
            for y in range(self.gridcount)
        ]
        for s in segments:
            ground.segment(s[0], s[1])
        ground = ground.build()
        xstart = -self.gridcount / 2 * (pyramid_base + 1) + pyramid_base / 2
        pyramids = [
            pyramid(
                self.world,
                pyramid_base,
                1,
                Vec2(xstart + (pyramid_base + 1) * x, y * (pyramid_base + 1)),
            )
            for x in range(self.gridcount)
            for y in range(self.gridcount)
        ]


class Spinner(BaseTest, category="Benchmark", name="Spinner"):
    body_count = UI.int(500, min=100, max=3000)

    @body_count.callback
    def on_change(self, key, value):
        self.on_reset(key, value)

    def setup(self):
        pcount = 200
        rotations = [Rot(-2 * math.pi / pcount * i) for i in range(pcount)]
        p = Vec2(0, 40)
        chain_points = [r(p) for r in rotations]
        ground = (
            self.world.new_body().chain(chain_points, loop=True, friction=0.1).build()
        )
        self.ground = ground
        spinner = (
            self.world.new_body()
            .dynamic()
            .enable_sleep(False)
            .box(0.8, 40, radius=0.2, friction=0.0)
            .position(0, -20)
            .build()
        )
        self.spinner = spinner

        spinner_j = self.world.add_revolute_joint(
            ground,
            spinner,
            anchor=spinner.position,
            enable_motor=True,
            motor_speed=5,
            max_motor_torque=50000,
        )
        shapeargs = {"friction": 0.1, "restitution": 0.1, "density": 0.25}
        capsule = (
            self.world.new_body()
            .dynamic()
            .capsule((-0.25, 0), (0.25, 0), 0.25, **shapeargs)
        )
        circle = self.world.new_body().dynamic().circle(0.35, **shapeargs)
        box = self.world.new_body().dynamic().box(0.7, 0.7, **shapeargs)

        x, y = -24, 2
        for i in range(self.body_count):
            remainder = i % 3
            if remainder == 0:
                capsule.position(x, y).build()
            elif remainder == 1:
                circle.position(x, y).build()
            elif remainder == 2:
                box.position(x, y).build()

            x += 1.0
            if x > 24.0:
                x = -24.0
                y += 1.0
