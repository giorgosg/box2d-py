import math

from box2d import CollisionFilter, Color, Vec2, clip_vector, solve_planes

from .base_test import UI, BaseTest
from .dynamic_mover import DynamicMover
from .shared import parse_svg_path
from .tb_events import WALK_KEYS


class Mover(BaseTest, category="Character", name="Mover"):
    """A character that is not a body, moved with the mover queries.

    Each step the character asks the world which surfaces a capsule at its
    position is up against, works out the movement closest to the one it
    wants that clears all of them at once, and trims the parts of its
    velocity that point into them. No solver is involved, so nothing pushes
    it back or tips it over: it stops dead against the side of the ledge,
    stands on top once it has jumped up, and walks straight up the ramp. It
    turns green while it stands on something.

    Move with the left and right arrow keys, or A and D, and jump with space
    from the ground. Speed is how fast it walks and Jump Speed how fast a jump leaves
    the ground, both in m/s. Gravity is the character's own, in m/s^2: it is
    not a body, so the world's gravity never reaches it.
    """

    camera_center = (0, 5)
    camera_zoom = 16.0

    speed = UI.float(8.0, min=1.0, max=20.0)
    jump_speed = UI.float(10.0, min=1.0, max=30.0)
    gravity = UI.float(30.0, min=0.0, max=60.0)

    START = (-14, 2)
    #: The capsule: two centres 0.4 m above and below the position, and a
    #: 0.4 m radius round them, so 1.6 m tall.
    HALF_LENGTH = 0.4
    RADIUS = 0.4
    #: A surface whose normal points up at least this much is ground: slopes
    #: up to about 45 degrees. Box2D's movers use the same number.
    MIN_GROUND_NORMAL_Y = 0.7

    def setup(self):
        terrain = self.world.new_body().static()
        terrain.segment((-20, 0), (8.5, 0))  # ground, from wall to wall
        terrain.box(1, 6, offset=(9, 3))  # wall on the right
        terrain.box(6, 0.5, offset=(-8, 1))  # a ledge, low enough to jump onto
        terrain.box(5, 0.3, offset=(3, 0.9), angle=math.radians(20))  # a ramp up
        # A wall on the left too: without it the character walks off the end
        # of the ground and falls for ever.
        terrain.box(1, 6, offset=(-20.5, 3))
        terrain.build()

        # The character's own state. Nothing here is a Box2D body.
        self.position = Vec2(self.START)
        self.velocity = Vec2(0, 0)
        self.on_ground = False
        self.held = set()

    def capsule(self):
        """The character's capsule, as the world points of its two centres."""
        x, y = self.position
        return (x, y - self.HALF_LENGTH), (x, y + self.HALF_LENGTH)

    def after_step(self, dt):
        # One way at most, however many keys point that way.
        direction = sum({WALK_KEYS[key] for key in self.held})
        self.velocity = Vec2(
            direction * self.speed, self.velocity.y - self.gravity * dt
        )

        point1, point2 = self.capsule()
        planes = self.world.collide_mover(point1, point2, self.RADIUS)
        self.on_ground = any(
            plane.plane.normal.y > self.MIN_GROUND_NORMAL_Y for plane in planes
        )

        result = solve_planes(self.velocity * dt, planes)
        self.position = self.position + result.translation
        self.velocity = clip_vector(self.velocity, planes)

    def on_key_down(self, key):
        if key in WALK_KEYS:
            self.held.add(key)
        elif key == "space" and self.on_ground:
            self.velocity = Vec2(self.velocity.x, self.jump_speed)

    def on_key_up(self, key):
        self.held.discard(key)

    def debug_draw(self, debug_draw):
        colour = Color(80, 220, 120) if self.on_ground else Color(220, 180, 60)
        point1, point2 = self.capsule()
        debug_draw.draw_solid_capsule(Vec2(point1), Vec2(point2), self.RADIUS, colour)

    def status(self):
        where = "on the ground" if self.on_ground else "in the air"
        velocity = self.velocity
        return f"{where}   velocity ({velocity.x:.1f}, {velocity.y:.1f}) m/s"


# Collision categories for the dynamic mover scene, as in Box2D's samples.
STATIC_BIT = 0x0001  # the default category, so the terrain needs no filter
MOVER_BIT = 0x0002
DYNAMIC_BIT = 0x0004

# The two stretches of terrain, drawn in Inkscape and kept as SVG paths.
TERRAIN_WEST = (
    "M -34.395834,201.08333 H 293.68751 v -47.625 h -2.64584 l -10.58333,7.9375 "
    "-13.22916,7.9375 -13.24648,5.29167 -31.73269,7.9375 -21.16667,2.64583 "
    "-23.8125,13.22919 -15.875,2e-5 0,-6.61461 -17.19792,2e-5 v 2.64582 h "
    "-17.19791 v -1.32292 h -3.96875 v -1.32292 h -3.96875 v -1.32292 h -3.96875 "
    "v -1.32291 h -3.96875 v -1.32292 h -3.96875 v -1.32292 h -3.96875 v -1.32291 "
    "h -3.968754 v -1.32292 h -3.96875 v -1.32292 h -3.968751 v -1.32291 h "
    "-3.96875 v -1.32292 h -3.96875 v -1.32292 h -3.96875 v -1.32291 h -3.96875 "
    "v -1.32292 h -3.96875 v -1.32292 h -3.968751 v -1.32291 h -3.96875 l "
    "-2e-6,-1.32294 H 52.916669 L 39.6875,177.27083 h -5.291667 l "
    "-7.937499,5.29167 H 15.875001 l -47.625002,-50.27083 v -26.45834 h "
    "-2.645834 l 10e-7,95.25"
)
TERRAIN_EAST = (
    "M 2.6458333,201.08333 H 399.52085 v -23.8125 h -23.8125 l 21.16667,18.52084 "
    "-232.83335,-1e-5 -0.0575,2.64584 h -5.29166 v -2.64583 l -7.86855,-1e-5 "
    "-0.0114,-2.64583 h -2.64583 l -2.64583,2.64584 h -7.9375 l -2.64584,2.64583 "
    "-2.58891,-2.64584 -10.64031,2e-5 v -2.64583 l -7.9375,0 v -2.64584 l "
    "-7.9375,0 v -2.64583 l -7.9375,0 v -2.64583 l -7.9375,0 v -2.64583 l "
    "-7.937501,-1e-5 v -2.64584 l -7.9375,1e-5 v -2.64583 l -7.937501,-2e-5 V "
    "174.625 l -7.937501,1e-5 v -2.64584 l -5.291669,0 -7.9375,-2.64584 "
    "-7.9375,-2.64583 -5.291667,-5.29167 H 21.166667 L 13.229167,158.75 "
    "5.2916668,153.45833 H 2.6458334 l -10e-8,47.625"
)


class DynamicMoverScene(BaseTest, category="Character", name="Dynamic Mover"):
    """A character that is a dynamic body, driven by a mover and a pogo joint.

    Unlike the Mover scenario's character this one is a real body: it knocks
    the balls and boxes about and is knocked back, rides the elevator and
    walks the swinging bridge. A mover joint drives it towards the speed it
    wants, and a pogo joint -- a spring along a ray cast down from the
    capsule -- holds it up off the ground, so it glides up steps it would
    otherwise catch on. The grey line is that ray, its dot plum where it
    found ground, and the line from the character is its velocity, orange
    while it stands on the ground.

    The elevator is one-way: jump up through it from below and land on top.
    Its pre-solve callback only reads the contact and empties the manifold,
    since nothing may be created or destroyed from inside a step.

    Move with A and D or the arrow keys, and jump with space; held in the
    air, space jumps on landing. The sliders tune the controller as it runs,
    over the ranges Box2D's sample gives them. Max Speed is the walking
    speed and Jump Speed how fast a jump leaves the ground, both in m/s, and
    Accelerate is how many times Max Speed the character gains per second,
    Air Steer the share of that it keeps in the air. On the ground, Friction
    takes off that many times its speed per second, or times Stop Speed when
    it is slower than that, and below Min Speed it stops dead. Gravity Scale
    multiplies the world's gravity for the character alone. Pogo Hertz and
    Pogo Damping tune the spring holding it up, and Lock Camera keeps the
    view on it.
    """

    # On the character, where Lock Camera keeps the view from the first step.
    camera_center = (0.0, 9.0)
    camera_zoom = 10.0

    jump_speed = UI.float(7.0, min=0.0, max=40.0)
    min_speed = UI.float(0.1, min=0.0, max=1.0)
    max_speed = UI.float(6.0, min=0.0, max=20.0)
    stop_speed = UI.float(3.0, min=0.0, max=10.0)
    accelerate = UI.float(20.0, min=0.0, max=100.0)
    friction = UI.float(8.0, min=0.0, max=10.0)
    gravity_scale = UI.float(1.5, min=0.0, max=4.0)
    air_steer = UI.float(0.5, min=0.0, max=1.0)
    pogo_hertz = UI.float(5.0, min=0.0, max=30.0)
    pogo_damping = UI.float(0.8, min=0.0, max=4.0)
    lock_camera = UI.bool(True)

    START = (0, 8)
    #: The elevator rides up and down, 4 m either side of this point, once
    #: every 2 pi seconds.
    ELEVATOR_BASE = Vec2(112.0, 10.0)
    ELEVATOR_AMPLITUDE = 4.0

    def setup(self):
        self.mover = DynamicMover(
            self.world,
            position=self.START,
            filter=CollisionFilter(category=MOVER_BIT, mask=STATIC_BIT | DYNAMIC_BIT),
            enable_pre_solve_events=True,
        )

        west = (
            self.world.new_body()
            .static()
            .name("terrain")
            .chain(
                parse_svg_path(TERRAIN_WEST, offset=(-50, -200), scale=0.2), loop=True
            )
            .build()
        )
        east = (
            self.world.new_body()
            .static()
            .position(98, 0)
            .chain(parse_svg_path(TERRAIN_EAST, offset=(0, -200), scale=0.2), loop=True)
            .build()
        )

        self.build_bridge(west, east)
        self.build_props(east)

        self.time = 0.0
        self.jump_pending = False
        self.held = set()

        # The elevator lets the character through from below. Pre-continuous
        # covers it arriving fast enough for continuous collision to catch it
        # before pre-solve ever sees a contact.
        self.world.pre_solve = self.on_pre_solve
        self.world.pre_continuous = self.on_pre_continuous

    def build_bridge(self, west, east):
        """Fifty planks on sprung hinges, slung between the two stretches."""
        # Box2D's numbers: the gap runs from x = 48.7 to 98.7 at height 9.2.
        x_base, y_base, count = 48.7, 9.2, 50
        hinge = dict(
            enable_motor=True,
            max_motor_torque=10.0,
            enable_spring=True,
            spring_hertz=3.0,
            spring_damping_ratio=0.8,
        )
        plank = self.world.new_body().dynamic().angular_damping(0.2).box(1.1, 0.25)
        previous = west
        for i in range(count):
            body = plank.position(x_base + 0.5 + i, y_base).build()
            self.world.add_revolute_joint(
                previous, body, anchor=(x_base + i, y_base), **hinge
            )
            previous = body
        self.world.add_revolute_joint(
            previous, east, anchor=(x_base + count, y_base), **hinge
        )

    def build_props(self, east):
        """Things to bump into: bouncy balls, a stack, an elevator, a paddle."""
        props = CollisionFilter(category=DYNAMIC_BIT)

        ball = (
            self.world.new_body()
            .dynamic()
            .circle(0.25, filter=props, restitution=0.7, rolling_resistance=0.2)
        )
        for i in range(5):
            ball.position(7, 7 + 0.5 * i).build()

        self.elevator = (
            self.world.new_body()
            .kinematic()
            .position(self.ELEVATOR_BASE - (0, self.ELEVATOR_AMPLITUDE))
            .box(4.0, 0.2, filter=props)
            .build()
        )

        box = self.world.new_body().dynamic().box(0.5, 0.5, filter=props)
        for i in range(10):
            box.position(140, (2 * i + 1) * 0.25 + 1).build()

        # A paddle turned round its top by a motor. It sweeps through the
        # floor, which it is jointed to: a joint's two bodies do not collide.
        paddle = self.world.new_body().dynamic().position(160, 4).box(0.2, 8.0).build()
        self.world.add_revolute_joint(
            east,
            paddle,
            anchor=(160, 8),
            enable_motor=True,
            motor_speed=1.0,
            max_motor_torque=500.0,
        )

    # --- one-way elevator --------------------------------------------------

    def blocks(self, shape_a, shape_b, normal):
        """False for the character meeting the elevator from below.

        The normal points from shape_a to shape_b, so whether it points up or
        down depends on which of the two is the elevator.
        """
        body_a, body_b = shape_a.body, shape_b.body
        mover = self.mover.body
        if body_a is self.elevator and body_b is mover:
            return normal.y >= 0
        if body_a is mover and body_b is self.elevator:
            return normal.y <= 0
        return True

    def on_pre_solve(self, shape_a, shape_b, manifold):
        if not self.blocks(shape_a, shape_b, manifold.normal):
            manifold.points.clear()

    def on_pre_continuous(self, shape_a, shape_b, point, normal):
        return self.blocks(shape_a, shape_b, normal)

    # --- per step ------------------------------------------------------------

    def after_step(self, dt):
        self.time += dt
        height = self.ELEVATOR_AMPLITUDE * math.cos(self.time + math.pi)
        self.elevator.set_target_transform(
            (self.ELEVATOR_BASE.x, self.ELEVATOR_BASE.y + height), 0.0, dt
        )

        self.apply_settings()

        # One way at most, however many keys point that way.
        throttle = float(sum({WALK_KEYS[key] for key in self.held}))

        # A jump pressed in the air waits for the ground, as upstream's does,
        # but each press jumps only once.
        if self.jump_pending and self.mover.jump():
            self.jump_pending = False

        self.mover.update(dt, throttle)

        if self.lock_camera:
            center = Vec2(self.app_state.center)
            self.app_state.center = Vec2(self.mover.position.x, center.y)

    def apply_settings(self):
        """Hand the sliders to the controller, which reads them every update."""
        mover = self.mover
        mover.jump_speed = self.jump_speed
        mover.min_speed = self.min_speed
        mover.max_speed = self.max_speed
        mover.stop_speed = self.stop_speed
        mover.accelerate = self.accelerate
        mover.friction = self.friction
        mover.air_steer = self.air_steer
        mover.pogo_hertz = self.pogo_hertz
        mover.pogo_damping_ratio = self.pogo_damping
        mover.gravity_scale = self.gravity_scale

    def on_key_down(self, key):
        if key == "space":
            self.jump_pending = True
        elif key in WALK_KEYS:
            self.held.add(key)

    def on_key_up(self, key):
        if key == "space":
            self.jump_pending = False
        else:
            self.held.discard(key)

    def debug_draw(self, debug_draw):
        mover = self.mover
        reach = mover.pogo_origin + mover.pogo_translation * mover.pogo_fraction
        debug_draw.draw_segment(mover.pogo_origin, reach, Color(128, 128, 128))
        hit_colour = Color(221, 160, 221) if mover.cast else Color(128, 128, 128)
        debug_draw.draw_point(reach, 10.0, hit_colour)

        position = mover.position
        colour = Color(255, 165, 0) if mover.on_ground else Color(127, 255, 212)
        debug_draw.draw_segment(position, position + mover.velocity, colour)

    def status(self):
        mover = self.mover
        normal_y = mover.cast.normal.y if mover.cast else 0.0
        return [
            f"velocity ({mover.velocity.x:.2f}, {mover.velocity.y:.2f}) m/s",
            f"pogo length {mover.pogo_length:.2f}/{mover.pogo_rest_length:.2f} m, "
            f"impulse {mover.pogo_impulse:.3f}",
            f"on ground {mover.on_ground}, walkable {mover.walkable} "
            f"(normal y {normal_y:.2f}), jumping {mover.jumping}",
        ]
