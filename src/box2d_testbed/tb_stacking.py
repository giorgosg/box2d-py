# tb_stacking.py

import math

from .base_test import BaseTest, UI
from box2d import Vec2


class CardHouse(BaseTest, category="Stacking", name="Card House"):
    """A house of cards built from very thin, high-friction boxes.

    The cards are 1mm thick, so this leans hard on the solver: any drift in
    contact handling collapses the structure.
    """

    camera_center = (0.75, 0.9)
    camera_zoom = 25.0 * 0.05

    rows = UI.int(5, min=1, max=8)

    def setup(self):

        self.world.new_body().static().position(0, -2).box(80, 4, friction=0.7).build()

        card_height = 0.2
        card_thickness = 0.001
        lean = math.radians(25)
        cards = (
            self.world.new_body()
            .dynamic()
            .box(2 * card_thickness, 2 * card_height, friction=0.7)
        )

        y = card_height - 0.02
        for row in range(self.rows, 0, -1):
            x = 0.175 * (self.rows - row)
            for i in range(row):
                # The flat card resting on top of the pair below it.
                if i != row - 1:
                    cards.position(x + 0.25, y + card_height - 0.015).rotation(
                        0.5 * math.pi
                    ).build()

                # The two leaning cards forming this cell.
                cards.position(x, y).rotation(-lean).build()
                x += 0.175
                cards.position(x, y).rotation(lean).build()
                x += 0.175

            y += card_height * 2.0 - 0.03

    @rows.callback
    def on_rows_change(self, key, value):
        for body in self.world.bodies:
            body.destroy()
        self.setup()


class Arch(BaseTest, category="Stacking", name="Arch"):
    """A masonry arch built from tapered voussoirs.

    Nothing holds the blocks together: the arch stands because each wedge is
    squeezed by its neighbours, so it is a good test of friction and of how the
    solver handles a long chain of contacts.
    """

    camera_center = (0, 8)
    camera_zoom = 25.0 * 0.35

    def setup(self):

        scale = 0.25
        # The two curves the voussoirs span between, inner and outer.
        inner = [
            (16.0, 0.0),
            (14.938037, 5.133601),
            (13.798717, 10.249281),
            (12.562530, 15.341070),
            (11.200410, 20.398565),
            (9.665212, 25.403699),
            (7.871799, 30.317934),
            (5.635200, 35.038207),
            (2.405938, 39.095541),
        ]
        outer = [
            (24.0, 0.0),
            (22.336195, 6.022998),
            (20.549369, 12.009644),
            (18.608546, 17.947032),
            (16.467693, 23.813679),
            (14.053250, 29.570794),
            (11.235510, 35.137758),
            (7.752568, 40.304507),
            (3.016932, 44.288916),
        ]
        inner = [Vec2(x * scale, y * scale) for x, y in inner]
        outer = [Vec2(x * scale, y * scale) for x, y in outer]

        self.world.new_body().static().segment(
            (-100, 0), (100, 0), friction=0.6
        ).build()

        def mirror(point):
            return Vec2(-point.x, point.y)

        # Each voussoir is a different polygon, so each needs its own body.
        # Reusing one builder would stack every previous polygon onto it, since
        # a builder accumulates the shapes configured on it.
        def add_block(vertices):
            block = self.world.add_body(body_type="dynamic")
            block.add_polygon(vertices=vertices, friction=0.6)

        for i in range(len(inner) - 1):
            # The right half, then its mirror image on the left.
            add_block([inner[i], outer[i], outer[i + 1], inner[i + 1]])
            add_block(
                [
                    mirror(outer[i]),
                    mirror(inner[i]),
                    mirror(inner[i + 1]),
                    mirror(outer[i + 1]),
                ]
            )

        # The keystone closing the top.
        add_block([inner[-1], outer[-1], mirror(outer[-1]), mirror(inner[-1])])

        # A short column resting on the keystone, to load the arch.
        for i in range(4):
            self.world.new_body().dynamic().position(
                0, 0.5 + outer[-1].y + 1.0 * i
            ).box(4, 1, friction=0.6).build()


class DoubleDomino(BaseTest, category="Stacking", name="Double Domino"):
    """A row of dominoes toppled by a nudge to the first one."""

    camera_center = (0, 4)
    camera_zoom = 25.0 * 0.25

    count = UI.int(15, min=2, max=60)
    nudge = UI.float(0.2, min=0.0, max=2.0)

    def setup(self):

        self.world.new_body().static().position(0, -1).box(200, 2).build()

        dominoes = self.world.new_body().dynamic().box(0.25, 1.0, friction=0.6)
        x = -0.5 * self.count
        for i in range(self.count):
            domino = dominoes.position(x, 0.5).build()
            if i == 0:
                # Topple the first one; the rest is up to the solver.
                domino.apply_linear_impulse((self.nudge, 0), (x, 1.0))
            x += 1.0

    @count.callback
    @nudge.callback
    def on_change(self, key, value):
        for body in self.world.bodies:
            body.destroy()
        self.setup()


class VerticalStack(BaseTest, category="Stacking", name="Vertical Stack"):
    """Columns of boxes, and a bullet to knock them over.

    The bullet is fired fast enough that continuous collision detection decides
    whether it passes through the stack or hits it.
    """

    camera_center = (-7, 9)
    camera_zoom = 14.0

    columns = UI.int(5, min=1, max=10)
    rows = UI.int(12, min=1, max=30)
    fire = UI.button("Fire bullet")

    def setup(self):

        ground = self.world.new_body().static()
        ground.segment((-30, 0), (30, 0))
        ground.segment((10, 0), (10, 20))
        ground.build()

        boxes = self.world.new_body().dynamic().box(1, 1, density=1.0, friction=0.3)
        offsets = (-0.02, 0.02)
        for column in range(self.columns):
            x = -12.0 + 3.0 * column
            for row in range(self.rows):
                # A slight alternating offset stops the columns being perfectly
                # aligned, which is both more realistic and harder to solve.
                boxes.position(x + offsets[row % 2], 0.5 + 1.01 * row).build()

        self.bullet = None

    @fire.callback
    def on_fire(self, key, value):
        if self.bullet is not None:
            self.bullet.destroy()
        self.bullet = (
            self.world.new_body()
            .dynamic()
            .bullet()
            .position(-31, 5)
            .linear_velocity(400, 0)
            .circle(radius=0.25, density=4.0)
            .build()
        )

    @columns.callback
    @rows.callback
    def on_change(self, key, value):
        self.bullet = None
        for body in self.world.bodies:
            body.destroy()
        self.setup()


class Cliff(BaseTest, category="Stacking", name="Cliff"):
    """Bodies teetering on the edges of three different ledges.

    Whether a body topples depends on where its centre of mass falls relative
    to the edge it is on, so this is a compact test of mass properties: a
    capsule, a rounded box and a plain box each hanging off a flat ledge, a
    segment and a rounded one.
    """

    camera_center = (0, 5)
    camera_zoom = 25.0 * 0.5

    flip = UI.bool(False, label="Mirror")

    def setup(self):

        ground = self.world.new_body().static()
        ground.box(200, 2, offset=(0, -1))
        ground.segment((-14, 4), (-8, 4))
        ground.box(6, 1, offset=(0, 4))
        ground.capsule((8.5, 4), (13.5, 4), radius=0.5)
        ground.build()

        sign = -1.0 if self.flip else 1.0
        offset = 0.0 if self.flip else 0.0

        # Three bodies per ledge, each hanging further over the edge.
        for base_x, ledge in ((-11.0, "segment"), (0.0, "box"), (11.0, "capsule")):
            for i, overhang in enumerate((0.0, 0.6, 1.2)):
                x = base_x + sign * (overhang - 1.0 + i * 0.1)
                body = self.world.new_body().dynamic().position(x, 4.9)
                if i == 0:
                    body.capsule((-0.25, 0), (0.25, 0), radius=0.25)
                elif i == 1:
                    body.box(1.0, 0.5, radius=0.1)
                else:
                    body.box(1.0, 0.5)
                body.build()

    @flip.callback
    def on_flip(self, key, value):
        for body in self.world.bodies:
            body.destroy()
        self.setup()

    def debug_draw(self, debug_draw):
        fallen = sum(
            1 for b in self.world.bodies if b.type == "dynamic" and b.position.y < 2
        )
        debug_draw.draw_string((-14, 10), f"toppled off: {fallen}")
