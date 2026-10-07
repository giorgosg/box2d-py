import math

from box2d import Vec2

from .base_test import UI, BaseTest


class CardHouse(BaseTest, category="Stacking", name="Card House"):
    """A house of cards, held up by nothing but friction.

    Each row is a line of pairs of cards leaning together, with a card laid
    flat across the tops of neighbouring pairs for the next row to stand on.
    The cards are 2 mm thick, less than the half centimetre Box2D lets
    touching shapes overlap, and only friction stops them sliding, so the
    contacts have to hold exactly. The house settles within a second and
    stands. How well the solver holds it depends on its sub-steps: at 4, the
    default in Box2D's own samples rather than the testbed's 20, a taller
    house is on the edge and may fall.

    Rows sets how many rows the house has, rebuilding it.
    """

    # Frames the tallest house Rows allows, eight rows and 3 m high.
    camera_center = (1.3, 1.5)
    camera_zoom = 1.7

    #: A card's height and thickness, in m.
    CARD_HEIGHT = 0.4
    CARD_THICKNESS = 0.002
    #: How far each card of a pair leans from the vertical.
    LEAN = math.radians(25)
    #: The cards' friction, and the floor's. Box2D's value: at its 4 sub-steps
    #: a step the house needs all of it, and at the testbed's 20 it stands down
    #: to 0.5.
    FRICTION = 0.7

    rows = UI.int(5, min=1, max=8)

    def setup(self):
        (
            self.world.new_body()
            .static()
            .position(0, -2)
            .box(80, 4, friction=self.FRICTION)
            .build()
        )

        cards = (
            self.world.new_body()
            .dynamic()
            .box(self.CARD_THICKNESS, self.CARD_HEIGHT, friction=self.FRICTION)
        )

        # Box2D's layout, which it took from PEEL. A card leaning 25 degrees
        # has its centre 0.18 m up, and stands 0.175 m from the card before it,
        # so the two of a pair meet at the top. Each row is 0.37 m above the
        # last, which puts its feet on the flat cards, and starts half a pair
        # further in.
        half_height = self.CARD_HEIGHT / 2
        spacing = 0.175
        y = half_height - 0.02
        for row in range(self.rows, 0, -1):
            x = spacing * (self.rows - row)
            for i in range(row):
                # The flat card across the tops of this pair and the next.
                if i != row - 1:
                    cards.position(x + 0.25, y + half_height - 0.015).rotation(
                        0.5 * math.pi
                    ).build()

                cards.position(x, y).rotation(-self.LEAN).build()
                x += spacing
                cards.position(x, y).rotation(self.LEAN).build()
                x += spacing

            y += self.CARD_HEIGHT - 0.03

    @rows.callback
    def on_rows_change(self, key, value):
        self.rebuild()


class Arch(BaseTest, category="Stacking", name="Arch"):
    """A masonry arch of seventeen blocks, loaded with a column of four more.

    Nothing holds the blocks together: each wedge is squeezed between its
    neighbours, and friction alone stops them sliding. A long chain of
    contacts, every one of which has to hold, is hard on the solver. The
    keystone sinks nearly 30 cm under the load, and then the arch stands,
    asleep a little over a second in.
    """

    camera_center = (0, 8)
    camera_zoom = 8.75

    #: The inner and outer curves of the arch's right half, from the base up,
    #: before scaling. Each block spans two neighbouring points of each, and
    #: the left half mirrors the right. Box2D's numbers.
    INNER = [
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
    OUTER = [
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
    #: Scales the curves to an arch 12 m across and 11 m high.
    SCALE = 0.25
    #: Every surface's friction. At 0.5 the blocks slide and the arch falls.
    FRICTION = 0.6

    def setup(self):
        inner = [Vec2(x * self.SCALE, y * self.SCALE) for x, y in self.INNER]
        outer = [Vec2(x * self.SCALE, y * self.SCALE) for x, y in self.OUTER]

        (
            self.world.new_body()
            .static()
            .segment((-100, 0), (100, 0), friction=self.FRICTION)
            .build()
        )

        def mirror(point):
            return Vec2(-point.x, point.y)

        # A new builder for each block: a builder keeps every shape added to
        # it, and each block is a different polygon.
        def add_block(vertices):
            (
                self.world.new_body()
                .dynamic()
                .polygon(vertices, friction=self.FRICTION)
                .build()
            )

        for i in range(len(inner) - 1):
            # A block of the right half, then its mirror image on the left.
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

        # The load: a column standing on the keystone.
        load = self.world.new_body().dynamic().box(4, 1, friction=self.FRICTION)
        for i in range(4):
            load.position(0, 0.5 + outer[-1].y + 1.0 * i).build()


class DoubleDomino(BaseTest, category="Stacking", name="Double Domino"):
    """A row of dominoes that falls twice.

    A small push topples the first domino. They are 1 m tall and stand 1 m
    apart, so each falls onto the next and comes to rest leaning on it, and
    the lean runs down the row in about eight seconds. When it reaches
    the end, the last domino has nothing to lean on and falls flat, and the
    row collapses back the other way, each domino dropping flat in turn.

    Count sets how many dominoes there are, and Nudge the push given to the
    first, in N s. Both rebuild the row.
    """

    camera_center = (0, 4)
    camera_zoom = 6.25

    #: Every domino's friction, against the floor and the others.
    FRICTION = 0.6

    count = UI.int(15, min=2, max=60)
    nudge = UI.float(0.2, min=0.0, max=2.0)

    def setup(self):
        self.world.new_body().static().position(0, -1).box(200, 2).build()

        dominoes = (
            self.world.new_body().dynamic().box(0.25, 1.0, friction=self.FRICTION)
        )
        x = -0.5 * self.count
        for i in range(self.count):
            domino = dominoes.position(x, 0.5).build()
            if i == 0:
                # At the top, where it gives the most turn for the push.
                domino.apply_linear_impulse((self.nudge, 0), (x, 1.0))
            x += 1.0

    @count.callback
    @nudge.callback
    def on_change(self, key, value):
        self.rebuild()


class VerticalStack(BaseTest, category="Stacking", name="Vertical Stack"):
    """Columns of boxes, and a ball fired through them at 400 m/s.

    The ball covers 6.7 m a step, more than a column and the gap to the
    next, so checking for overlap after each step would miss the boxes
    altogether. Box2D sweeps every fast body's path between steps against
    static bodies, but only a bullet's against dynamic ones too. So a bullet
    hits the first column, and a ball that is not one passes every column
    and stops only at the wall.

    Fire fires the ball, replacing the last one, and Bullet decides whether
    the next one is a bullet. Columns and Rows set the size of the stacks,
    rebuilding them.
    """

    camera_center = (-7, 9)
    camera_zoom = 14.0

    #: The boxes' friction, against the ground and each other.
    BOX_FRICTION = 0.3
    #: Where the ball is fired from: just past the end of the ground, level
    #: with the fifth row.
    BALL_START = (-31, 5)
    #: The ball's speed, in m/s: Box2D's maximum linear speed, the fastest it
    #: lets anything go.
    BALL_SPEED = 400.0
    #: The ball's radius, in m, and density, four times the boxes', so it
    #: carries enough to knock a column about.
    BALL_RADIUS = 0.25
    BALL_DENSITY = 4.0

    columns = UI.int(5, min=1, max=10)
    rows = UI.int(12, min=1, max=30)
    bullet = UI.bool(True)
    fire = UI.button("Fire")

    def setup(self):
        (
            self.world.new_body()
            .static()
            .segment((-30, 0), (30, 0))
            .segment((10, 0), (10, 20))
            .build()
        )

        boxes = self.world.new_body().dynamic().box(1, 1, friction=self.BOX_FRICTION)
        # Alternate rows sit 2 cm either side, so that a column is not
        # perfectly aligned, and 1 cm apart, so that each box drops onto the
        # one below.
        offsets = (-0.02, 0.02)
        for column in range(self.columns):
            x = -12.0 + 3.0 * column
            for row in range(self.rows):
                boxes.position(x + offsets[row % 2], 0.5 + 1.01 * row).build()

        self.ball = None

    @fire.callback
    def on_fire(self, key, value):
        if self.ball is not None:
            self.ball.destroy()
        self.ball = (
            self.world.new_body()
            .dynamic()
            .bullet(self.bullet)
            .position(self.BALL_START)
            .linear_velocity(self.BALL_SPEED, 0)
            .circle(radius=self.BALL_RADIUS, density=self.BALL_DENSITY)
            .build()
        )

    @columns.callback
    @rows.callback
    def on_change(self, key, value):
        self.rebuild()


class Cliff(BaseTest, category="Stacking", name="Cliff"):
    """Bodies sent sliding off the ends of three ledges.

    The ledges are a segment, a box and a capsule, and each has a capsule, a
    box and a circle on it, all sent towards the same end: the capsule and
    the box slide, almost without friction, and the circle rolls. Watch each
    leave its ledge. It should tip over the edge and drop to the ground,
    without catching on the corner or floating on past it.

    Mirror sends them all the other way, rebuilding the scene.
    """

    camera_center = (0, 5)
    camera_zoom = 12.5

    #: How fast each kind of body is sent towards the end of its ledge, in
    #: m/s, and its friction. The capsules and boxes all but slide, so they
    #: reach the edge however far back they start; the circles roll, and need
    #: some grip to. Box2D's values.
    CAPSULE_SPEED = 2.0
    BOX_SPEED = 2.5
    CIRCLE_SPEED = 1.5
    SLIDING_FRICTION = 0.01
    CIRCLE_FRICTION = 0.2

    mirror = UI.bool(False)

    def setup(self):
        (
            self.world.new_body()
            .static()
            .box(200, 2, offset=(0, -1))
            .segment((-14, 4), (-8, 4))
            .box(6, 1, offset=(0, 4))
            .capsule((8.5, 4), (13.5, 4), radius=0.5)
            .build()
        )
        # Where each ledge's middle is, and how high its top.
        ledges = ((-11.0, 4.0), (0.0, 4.5), (11.0, 4.5))

        # Each capsule starts 2 m towards the end it is sent to, each box in
        # the middle and each circle 2 m the other way.
        sign = -1.0 if self.mirror else 1.0
        capsule = (
            self.world.new_body()
            .dynamic()
            .linear_velocity(self.CAPSULE_SPEED * sign, 0)
            .capsule((-0.25, 0), (0.25, 0), radius=0.25, friction=self.SLIDING_FRICTION)
        )
        for middle, top in ledges:
            capsule.position(middle + 2.0 * sign, top + 0.25).build()

        box = (
            self.world.new_body()
            .dynamic()
            .linear_velocity(self.BOX_SPEED * sign, 0)
            .box(1, 1, friction=self.SLIDING_FRICTION)
        )
        for middle, top in ledges:
            box.position(middle, top + 0.5).build()

        circle = (
            self.world.new_body()
            .dynamic()
            .linear_velocity(self.CIRCLE_SPEED * sign, 0)
            .circle(0.5, friction=self.CIRCLE_FRICTION)
        )
        for middle, top in ledges:
            circle.position(middle - 2.0 * sign, top + 0.5).build()

    @mirror.callback
    def on_mirror(self, key, value):
        self.rebuild()

    def status(self):
        bodies = [body for body in self.world.bodies if body.type == "dynamic"]
        fallen = sum(1 for body in bodies if body.position.y < 2)
        return f"on the ground: {fallen} of {len(bodies)}"


class Confined(BaseTest, category="Stacking", name="Confined"):
    """Six hundred and twenty-five weightless circles, in a box too small to
    hold them.

    They start in a grid, overlapping their neighbours, and even packed as
    tightly as circles go they would need two fifths more room than the box
    has, so they can never all be clear of each other. With gravity off there is
    no floor to settle onto either. Box2D pushes overlapping shapes apart no
    faster than the world's contact push velocity, 3 m/s, so the overlap
    turns into a gentle shove rather than speed that would make the pile
    jitter or burst: it comes to rest, overlaps and all, and falls asleep a
    little over a second in.

    Grid sets how many circles there are, Grid by Grid, rebuilding the box.
    """

    camera_center = (0, 10)
    camera_zoom = 12.5

    grid = UI.int(25, min=5, max=30)

    def setup(self):
        walls = self.world.new_body().static()
        for start, end in (
            ((-10.5, 0), (10.5, 0)),
            ((-10.5, 0), (-10.5, 20.5)),
            ((10.5, 0), (10.5, 20.5)),
            ((-10.5, 20.5), (10.5, 20.5)),
        ):
            walls.capsule(start, end, radius=0.5)
        walls.build()

        circles = self.world.new_body().dynamic().gravity_scale(0.0).circle(radius=0.5)
        for column in range(self.grid):
            for row in range(self.grid):
                circles.position(
                    -8.75 + column * 18.0 / self.grid,
                    1.5 + row * 18.0 / self.grid,
                ).build()

    @grid.callback
    def on_grid_change(self, key, value):
        self.rebuild()


class CapsuleStack(BaseTest, category="Stacking", name="Capsule Stack"):
    """Twenty capsules lying flat, dropped onto one another.

    They start a quarter of a metre apart, so the top of the stack falls 5 m
    before it settles. Two capsules side by side touch along a line, which
    Box2D holds with a contact point at each end of it, and the stack comes
    to rest a couple of centimetres off the vertical and falls asleep within
    a few seconds.

    Rolling Resistance is the setting Box2D's sample suggests for stacking
    stability. This stack stands without it, and with it takes longer to come
    to rest. Count sets how many capsules there are. Both rebuild the stack.
    """

    camera_center = (0, 7)
    camera_zoom = 8.5

    count = UI.int(20, min=2, max=30)
    rolling_resistance = UI.float(0.0, min=0.0, max=0.3)

    def setup(self):
        self.world.new_body().static().position(0, -1).box(20, 2).build()

        radius = 0.25
        capsules = (
            self.world.new_body()
            .dynamic()
            .capsule(
                (-4.0 * radius, 0),
                (4.0 * radius, 0),
                radius=radius,
                rolling_resistance=self.rolling_resistance,
            )
        )
        y = 2.0 * radius
        for _ in range(self.count):
            capsules.position(0, y).build()
            y += 3.0 * radius

    @count.callback
    @rolling_resistance.callback
    def on_change(self, key, value):
        self.rebuild()


class TiltedStack(BaseTest, category="Stacking", name="Tilted Stack"):
    """Columns of rounded boxes, each box set a little to the right of the one
    below, so the columns lean.

    Whether a column stands is statics. The n boxes resting on any box have
    their centre of mass (n + 1) / 2 times the lean out from its middle, and
    they topple once that is past the edge of its flat top, 0.45 m out. At the
    defaults the nine on the bottom box are 1 m out, so every column topples,
    about 1.7 s in.

    The solver gets close to that answer, and closer the shorter the column.
    Five rows stand at 0.175 m and fall at 0.18, where statics puts the
    limit. Ten rows, which statics holds up to 0.09 m, stand at 0.08 and fall
    at 0.085, and twenty, held up to 0.045 m, already fall at 0.03.

    Rows and Columns set the size of the stacks, and Lean per row how far
    each box is set over, in m. All three rebuild the stacks.
    """

    camera_center = (9, 5)
    camera_zoom = 12.0

    #: How far the corners of the boxes are rounded, in m. It takes 5 cm off
    #: each side of the flat a box can rest on.
    ROUNDING = 0.05
    #: The boxes' friction, against the ground and each other.
    FRICTION = 0.3

    rows = UI.int(10, min=2, max=20)
    columns = UI.int(4, min=1, max=8)
    lean = UI.float(0.2, min=0.0, max=0.5, label="Lean per row")

    def setup(self):
        self.world.new_body().static().position(0, -1).box(2000, 2).build()

        # 1 m across, but the rounding leaves a flat top and bottom 0.9 m wide,
        # which is what a box can rest on.
        boxes = (
            self.world.new_body()
            .dynamic()
            .box(0.9, 0.9, radius=self.ROUNDING, friction=self.FRICTION)
        )
        spacing = 5.0
        first_x = -0.5 * spacing * (self.columns - 1.0)
        for column in range(self.columns):
            x = first_x + column * spacing
            for row in range(self.rows):
                boxes.position(x + self.lean * row, 0.5 + 1.0 * row).build()

    @rows.callback
    @columns.callback
    @lean.callback
    def on_change(self, key, value):
        self.rebuild()
