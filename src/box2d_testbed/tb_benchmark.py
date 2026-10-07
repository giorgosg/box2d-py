import itertools
import math

from box2d import Rot, Vec2

from .base_test import UI, BaseTest


class Compound(BaseTest, category="Benchmark", name="Compound"):
    """Bodies of nine boxes each, dropped into a valley made of boxes.

    A body with several shapes is a compound: it moves as one, but each of
    its shapes is in the broad-phase and collides on its own. So every box
    here costs what a separate body would in finding contacts, and the
    valley, a staircase of 1 m boxes on a single static body, is a few
    hundred shapes more. The bodies fall about 40 m, land a little under 3 s
    in, and pile up in the bottom of the valley, asleep 5 to 8 s in.

    Count sets how many bodies there are, Count by Count, and sizes the
    valley to match. It rebuilds the scene.
    """

    camera_center = (0, 27)
    camera_zoom = 28.5

    #: The valley's friction. The pile ends up much the same at the 0.6 the
    #: bodies have, Box2D's default.
    GROUND_FRICTION = 0.2

    count = UI.int(3, min=2, max=10)

    @count.callback
    def on_count_change(self, key, value):
        self.rebuild()

    def setup(self):
        # Row i of each side of the valley starts i boxes out from the middle,
        # so its floor is one box and its sides rise a box a step.
        size = self.count * 3 + 5
        ground = self.world.new_body().static()
        for sign in (1, -1):
            for row in range(size):
                for column in range(row, size):
                    ground.box(
                        1.0,
                        1.0,
                        offset=(sign * column, row),
                        friction=self.GROUND_FRICTION,
                    )
        ground.build()

        # Three boxes by three, touching.
        compound = self.world.new_body().dynamic()
        for offset in itertools.product((-1.0, 0.0, 1.0), repeat=2):
            compound.box(1.0, 1.0, offset=offset)

        # Count by Count of them, 3 m apart, centred 50 m up.
        spacing = 3.0
        first_x = -((self.count - 1) * spacing) / 2
        first_y = 50 - ((self.count - 1) * spacing) / 2
        for row, column in itertools.product(range(self.count), repeat=2):
            compound.position(
                first_x + column * spacing, first_y + row * spacing
            ).build()


def pyramid(world, base_count, base_position):
    """Build a pyramid of 1 m boxes, ``base_count`` wide at the bottom.

    The bottom row stands on ``base_position``, and runs half a box further
    to the right of it than to the left.
    """
    boxes = world.new_body().dynamic().box(1, 1)
    top = base_position + Vec2(0, base_count + 0.5)
    # Row r from the top has r boxes, each resting on two of the row below.
    for row in range(1, base_count + 1):
        for column in range(row):
            boxes.position(*(top - Vec2(column - row / 2, row))).build()


class Pyramid(BaseTest, category="Benchmark", name="Pyramid"):
    """A pyramid of boxes, the classic stacking benchmark.

    Each box rests on two below it, so the whole pyramid is one island the
    solver has to settle together every step: 210 boxes at the default, n (n
    + 1) / 2 for a base of n. It settles within a second, and then falls
    asleep, after which it costs next to nothing. Untick Sleep in the
    testbed's settings to keep it awake and measure the solve, as Box2D's
    own benchmark does; the Performance panel has the timings.

    Base Count sets how many boxes wide the bottom row is, rebuilding the
    pyramid.
    """

    camera_center = (0, 10)
    camera_zoom = 12.0

    base_count = UI.int(20, min=5, max=100)

    @base_count.callback
    def on_count_change(self, key, value):
        self.rebuild()

    def setup(self):
        self.world.new_body().static().position(0, -10).box(200, 20).build()
        pyramid(self.world, self.base_count, Vec2(0, 0))


class ManyPyramids(BaseTest, category="Benchmark", name="Many Pyramids"):
    """A grid of small pyramids, each on its own shelf.

    Fifty-five boxes a pyramid, and none touches another: each is an island
    of its own, so this measures many small islands where Pyramid measures
    one large one. They settle and fall asleep within a second. Untick Sleep
    in the testbed's settings to keep them awake, as Box2D's own benchmark
    does.

    Grid sets how many pyramids there are, Grid by Grid, rebuilding them.
    """

    camera_center = (0, 27)
    camera_zoom = 30.0

    #: How many boxes wide each pyramid is at the bottom.
    PYRAMID_BASE = 10

    grid = UI.int(5, min=2, max=10)

    @grid.callback
    def on_grid_change(self, key, value):
        self.rebuild()

    def setup(self):
        # A pyramid and a box's gap beside it, across and up: the shelves are
        # a pyramid's height and a box apart.
        spacing = self.PYRAMID_BASE + 1
        width = spacing * self.grid
        ground = self.world.new_body().static()
        for row in range(self.grid):
            ground.segment((-width / 2, row * spacing), (width / 2, row * spacing))
        ground.build()

        first_x = -self.grid / 2 * spacing + self.PYRAMID_BASE / 2
        for column in range(self.grid):
            for row in range(self.grid):
                pyramid(
                    self.world,
                    self.PYRAMID_BASE,
                    Vec2(first_x + spacing * column, row * spacing),
                )


class Spinner(BaseTest, category="Benchmark", name="Spinner"):
    """A long bar driven round inside a ring, churning a heap of small shapes.

    The bar is turned by a motor at 5 rad/s and sweeps the bottom half of the
    ring, flinging capsules, circles and boxes about, so contacts keep
    starting and ending and nothing ever settles. The ring is a single
    looped chain, which only collides on its inner side.

    Body Count sets how many shapes are dropped in, rebuilding the scene.
    """

    camera_center = (0, 0)
    camera_zoom = 42.0

    #: The ring's radius, in m, and how many points make it.
    RING_RADIUS = 40.0
    RING_POINTS = 200
    #: The ring's friction, and the bar's: the bar has none, so it pushes the
    #: pieces round rather than dragging them. Box2D's values.
    RING_FRICTION = 0.1
    BAR_FRICTION = 0.0
    #: How fast the motor turns the bar, in rad/s, and the most torque it may
    #: use to, in N m.
    MOTOR_SPEED = 5.0
    MAX_MOTOR_TORQUE = 50000.0
    #: The pieces' material: light, a little bouncy, and slippery. Box2D's
    #: values.
    PIECE_FRICTION = 0.1
    PIECE_RESTITUTION = 0.1
    PIECE_DENSITY = 0.25

    body_count = UI.int(500, min=100, max=3000)

    @body_count.callback
    def on_change(self, key, value):
        self.rebuild()

    def setup(self):
        # Wound clockwise, so the chain's solid side faces in.
        top = Vec2(0, self.RING_RADIUS)
        ring = [
            Rot(-2 * math.pi / self.RING_POINTS * i)(top)
            for i in range(self.RING_POINTS)
        ]
        ground = (
            self.world.new_body()
            .static()
            .chain(ring, loop=True, friction=self.RING_FRICTION)
            .build()
        )

        # The bar is 40 m long and turns about its middle, 20 m below the
        # ring's centre, so its ends sweep the bottom of the ring. A motor does
        # not keep a body awake: stalled by the heap for half a second, the bar
        # would fall asleep with it, and the motor would not wake it again.
        bar = (
            self.world.new_body()
            .dynamic()
            .enable_sleep(False)
            .box(0.8, 40, radius=0.2, friction=self.BAR_FRICTION)
            .position(0, -20)
            .build()
        )
        self.world.add_revolute_joint(
            ground,
            bar,
            anchor=bar.position,
            enable_motor=True,
            motor_speed=self.MOTOR_SPEED,
            max_motor_torque=self.MAX_MOTOR_TORQUE,
        )

        material = {
            "friction": self.PIECE_FRICTION,
            "restitution": self.PIECE_RESTITUTION,
            "density": self.PIECE_DENSITY,
        }
        pieces = (
            self.world.new_body()
            .dynamic()
            .capsule((-0.25, 0), (0.25, 0), radius=0.25, **material),
            self.world.new_body().dynamic().circle(0.35, **material),
            self.world.new_body().dynamic().box(0.7, 0.7, **material),
        )

        # Rows 1 m apart, of 49 pieces 1 m apart, taking the three kinds in
        # turn.
        x, y = -24, 2
        for i in range(self.body_count):
            pieces[i % 3].position(x, y).build()
            x += 1.0
            if x > 24.0:
                x = -24.0
                y += 1.0


class Tumbler(BaseTest, category="Benchmark", name="Tumbler"):
    """A spinning drum 20 m across, fed a quarter-metre box every step.

    The drum is a kinematic body: it turns at the speed it is given, however
    hard the boxes push back, as if driven by a motor of unlimited torque.
    The boxes tumble against its walls and each other, so contacts keep
    starting and ending, and none of them ever rests for long enough to fall
    asleep.

    Speed is how fast the drum turns, in degrees a second, and takes effect
    at once. Max Bodies is how many boxes are fed in; raising it feeds more,
    lowering it stops the feed.
    """

    # Takes in the drum's corners as it turns.
    camera_center = (0, 0)
    camera_zoom = 16.0

    #: How many places across the middle the boxes are fed in at.
    FEED_PLACES = 16

    angular_speed = UI.float(25.0, min=-100.0, max=100.0, label="Speed (deg/s)")
    max_bodies = UI.int(400, min=10, max=2000)

    def setup(self):
        # Box2D's drum: 1 m walls round a space 19 m square, which 2000 of the
        # boxes would fill only a third of.
        self.drum = (
            self.world.new_body()
            .kinematic()
            .angular_velocity(math.radians(self.angular_speed))
            .box(1.0, 20.0, offset=(10.0, 0.0))
            .box(1.0, 20.0, offset=(-10.0, 0.0))
            .box(20.0, 1.0, offset=(0.0, 10.0))
            .box(20.0, 1.0, offset=(0.0, -10.0))
            .build()
        )

        self.boxes = self.world.new_body().dynamic().box(0.25, 0.25)
        self.count = 0

    def after_step(self, dt):
        if self.count < self.max_bodies:
            # Sixteen places half a metre apart across the middle, taken in
            # turn. By the time one comes round again, 16 steps on, the box
            # fed there has fallen a third of a metre, clear of it.
            place = self.count % self.FEED_PLACES
            x = 0.5 * (place - (self.FEED_PLACES - 1) / 2)
            self.boxes.position(x, 0).build()
            self.count += 1

    @angular_speed.callback
    def on_speed_change(self, key, value):
        self.drum.angular_velocity = math.radians(value)

    def status(self):
        return f"boxes: {self.count}"
