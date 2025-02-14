# test_shapes.py

from base_test import BaseTest, UIElement
from itertools import product
from shared import create_random_polygon


class RoundedShapes(BaseTest, category="Shapes", name="Rounded"):
    def setup(self):
        body = (
            self.world.new_body()
            .static()
            .box(40, 2, offset=(0, -1))
            .box(2, 10, offset=(19, 5))
            .box(2, 10, offset=(-19, 5))
            .build()
        )

        xcount, ycount = 10, 10
        xstart, ystart = -5, 2

        for x, y in product(range(xcount), range(ycount)):
            bb = (
                self.world.new_body()
                .dynamic()
                .position(xstart + x, ystart + y)
                .create_random_polygon(0.5)
                .build()
            )


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
            self.world.new_body().dynamic().position(x, y).box(
                1.0, 1.0, friction=f, density=25.0
            ).build()


class Restitution(BaseTest, category="Shapes", name="Restitution"):
    def setup(self, shape="circle"):
        ground = (
            self.world.new_body().static().segment((-40, 0), (40, 0), restitution=0)
        )
        ground.build()

        e_count = 40
        dr = 1.0 / (e_count - 1)
        dx = 2.0

        x_list = [-1.0 * (e_count - 1) + i * dx for i in range(e_count)]
        restitution_list = [i * dr for i in range(e_count)]
        y_position = 40.0

        for x, r in zip(x_list, restitution_list):
            builder = self.world.new_body().dynamic().position(x, y_position)
            if shape == "circle":
                builder.circle(radius=0.5, center=(0, 0), restitution=r, density=1.0)
            elif shape == "box":
                builder.box(1.0, 1.0, restitution=r, density=1.0)
            elif shape == "polygon":
                builder.create_random_polygon(0.5, restitution=r, density=1.0)
            elif shape == "capsule":
                builder.capsule(
                    (0, -0.5), (0, 0.5), radius=0.5, restitution=r, density=1.0
                )
            else:
                builder.circle(radius=0.5, center=(0, 0), restitution=r, density=1.0)
            builder.build()

    def init_ui(self):
        super().init_ui()
        self.current_shape = "circle"
        self.ui_elements += [
            UIElement(
                control_type="combo",
                key="shape_selector",
                label="Shape",
                default="circle",
                options=["circle", "box", "polygon", "capsule"],
                callback=self.on_shape_change,
            )
        ]

    def on_shape_change(self, new_value):
        self.current_shape = new_value
        # First, clear all existing bodies in the world.
        for body in self.world.bodies:
            body.destroy()

        self.setup(self.current_shape)
