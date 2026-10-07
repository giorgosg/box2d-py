from box2d import CollisionFilter, Color, SurfaceMaterial

from .base_test import UI, BaseTest
from .human import Human
from .shared import donut


class FootSensor(BaseTest, category="Events", name="Foot Sensor"):
    """A sensor at a character's feet, telling it when it stands on something.

    The player is a capsule with a sensor box 1 m wide under it. A sensor
    detects overlap but never collides, so the box can reach a little below
    the capsule without holding it up, and collision filters let it see only
    the ground. Begin and end events from it keep a count of the ground
    shapes it overlaps: above zero, the player is standing on something.

    The ground is a chain of 1 m segments, so the foot straddles two almost
    everywhere; walk off either end and the count drops to zero. The dots
    mark the segments the sensor overlaps, read from sensor_overlaps: the
    same answer asked for on demand, rather than kept up to date from events.

    Move with the left and right arrow keys, or A and D as in Box2D's sample.
    """

    camera_center = (0, 3)
    camera_zoom = 7.5

    #: The push from a held key, in N, as in Box2D's sample.
    FORCE = 50.0

    def setup(self):
        # Chains opt in to sensor events like shapes do, and box2d-py
        # defaults that to on, so the foot can see this one.
        (
            self.world.new_body()
            .static()
            .chain(
                [(x, 0) for x in range(9, -10, -1)],
                filter=CollisionFilter(category="ground", mask=["foot", "player"]),
            )
            .build()
        )

        self.player = (
            self.world.new_body()
            .dynamic()
            .position(0, 2)
            .lock_rotation()
            .capsule(
                (0, -0.5),
                (0, 0.5),
                0.5,
                filter=CollisionFilter(category="player", mask=["ground"]),
            )
            .box(
                1,
                0.5,
                offset=(0, -1),
                is_sensor=True,
                filter=CollisionFilter(category="foot", mask=["ground"]),
            )
            .build()
        )
        self.foot = next(shape for shape in self.player.shapes if shape.is_sensor)

        self.overlaps = 0
        self.held = set()

    def on_key_down(self, key):
        self.held.add(key)

    def on_key_up(self, key):
        self.held.discard(key)

    def after_step(self, dt):
        # Holding both ways pushes both ways, and the player stands still.
        direction = bool(self.held & {"right", "d"}) - bool(self.held & {"left", "a"})
        self.player.apply_force((self.FORCE * direction, 0))

        events = self.world.get_sensor_events()
        self.overlaps += sum(1 for event in events.begin if event.sensor is self.foot)
        self.overlaps -= sum(1 for event in events.end if event.sensor is self.foot)

    def debug_draw(self, debug_draw):
        for shape in self.foot.sensor_overlaps:
            box = shape.aabb
            middle = ((box.lower.x + box.upper.x) / 2, (box.lower.y + box.upper.y) / 2)
            debug_draw.draw_point(middle, 10, Color(255, 255, 255))

    def status(self):
        where = "standing" if self.overlaps > 0 else "in the air"
        return f"foot overlaps {self.overlaps} ground segments: {where}"


class BouncingBoxes(BaseTest, category="Events", name="Contact"):
    """Six bouncy boxes dropped into a walled pit, lit while they touch.

    Contact events are opt-in, and Box2D reports a contact if either of its
    shapes asked, so only the boxes do. Begin and end events say when a
    contact starts and stops touching, and the scene keeps the contacts
    touching now: a box is lit while it is in one, and the status line
    counts the shapes that are. Hit events are a separate opt-in, for
    contacts that begin at speed: one fires only when the shapes close faster
    than the world's hit threshold, so a box settling gently makes none. Each
    hit flashes where it landed.

    Hit Threshold sets that speed, in m/s.
    """

    camera_center = (0, 6)
    camera_zoom = 12.0

    hit_threshold = UI.float(1.0, min=0.0, max=20.0)

    def setup(self):
        self.world.hit_event_threshold = self.hit_threshold

        (
            self.world.new_body()
            .static()
            .segment((-12, 0), (12, 0))
            .segment((-12, 0), (-12, 12))
            .segment((12, 0), (12, 12))
            .build()
        )

        boxes = (
            self.world.new_body()
            .dynamic()
            .box(
                1,
                1,
                restitution=0.6,
                enable_contact_events=True,
                enable_hit_events=True,
            )
        )
        for i in range(6):
            boxes.position(-5 + 2 * i, 6 + 1.5 * i).build()

        # Touching contacts and their shapes. A shape can be in several at
        # once -- the ground holds up every box -- so it stops touching when
        # its last contact ends, not its first.
        self.contacts = {}
        self.flashes = {}
        self.hit_count = 0

    def after_step(self, dt):
        events = self.world.get_contact_events()

        for touch in events.begin:
            self.contacts[touch.contact] = (touch.shape_a, touch.shape_b)
        for touch in events.end:
            self.contacts.pop(touch.contact, None)

        # Each flash lasts twenty steps, fading as it goes.
        self.flashes = {k: v - 1 for k, v in self.flashes.items() if v > 1}
        for hit in events.hit:
            self.hit_count += 1
            self.flashes[(hit.point.x, hit.point.y)] = 20

    @property
    def touching(self):
        """The shapes in a touching contact."""
        return {shape for pair in self.contacts.values() for shape in pair}

    @hit_threshold.callback
    def on_threshold_change(self, key, value):
        self.world.hit_event_threshold = value

    def debug_draw(self, debug_draw):
        for shape in self.touching:
            if shape.body.type == "dynamic":
                debug_draw.draw_polygon(
                    shape.body.transform, shape.vertices, Color(80, 220, 120)
                )
        for (x, y), life in self.flashes.items():
            debug_draw.draw_point((x, y), 4 + life, Color(255, 200, 0))

    def status(self):
        return f"touching: {len(self.touching)}   hits: {self.hit_count}"


class SettlingPyramid(BaseTest, category="Events", name="Body Move"):
    """A pyramid of boxes, and the move events Box2D reports for it.

    After each step Box2D hands back a move event for every body the step
    moved -- every awake body -- with its new transform. That is cheaper than
    walking every body to refresh what you draw, since a body at rest costs
    nothing. The pyramid settles within a couple of seconds, Box2D puts it to
    sleep, and the count drops to zero. The last event a body gets says it
    fell asleep, and any event after that means it woke, which is how the
    scene counts the boxes asleep. Drag a box to wake the pile and watch it
    settle again.
    """

    camera_center = (0, 6)
    camera_zoom = 14.0

    def setup(self):
        self.world.new_body().static().segment((-15, 0), (15, 0)).build()

        builder = self.world.new_body().dynamic().box(0.8, 0.8, friction=0.6)
        self.boxes = {
            builder.position(-3 + column + 0.5 * row, 0.5 + row).build()
            for row in range(6)
            for column in range(6 - row)
        }

        self.moved = 0
        self.sleeping = set()

    def after_step(self, dt):
        # Only the pile: dragging a box adds the kinematic body the mouse
        # joint pulls from, and that moves too.
        events = [
            event for event in self.world.get_body_events() if event.body in self.boxes
        ]
        self.moved = len(events)
        for event in events:
            if event.fell_asleep:
                self.sleeping.add(event.body)
            else:
                self.sleeping.discard(event.body)

    @property
    def asleep(self):
        """How many boxes are asleep now."""
        return len(self.sleeping)

    def status(self):
        return (
            f"moving this step: {self.moved} of {len(self.boxes)} boxes"
            f"   asleep: {self.asleep}"
        )


class BreakableChain(BaseTest, category="Events", name="Joint"):
    """A chain that comes apart when pulled harder than its links can take.

    A joint reports nothing until it is given a force or torque threshold.
    Each link here reports when the force holding it together passes
    Threshold, and every joint reported is destroyed after the step.

    The chain starts out level, pinned at its left end, and swings down
    carrying a 314 kg weight that outweighs the links six to one. So every
    link pulls with nearly the weight's whole force, and at the default
    2000 N they all pass the threshold in the same step, three quarters of a
    second in: the chain falls apart at once. Raise Threshold and it survives
    the first swing to whip about, and the links nearest the pin, which hold
    the most, give first -- at 10000 N the top three break 1.6 s in and the
    rest falls away. Threshold also changes the links still whole.
    """

    camera_center = (0, -4)
    camera_zoom = 12.0

    threshold = UI.float(2000.0, min=100.0, max=20000.0)

    def setup(self):
        ground = self.world.new_body().static().build()

        links = (
            self.world.new_body()
            .dynamic()
            .capsule((-0.4, 0), (0.4, 0), radius=0.15, density=20.0)
        )
        previous = ground
        self.joints = []
        for i in range(8):
            link = links.position(1.0 + i, 0).build()
            joint = self.world.add_revolute_joint(previous, link, anchor=(0.5 + i, 0))
            joint.force_threshold = self.threshold
            self.joints.append(joint)
            previous = link

        weight = (
            self.world.new_body()
            .dynamic()
            .position(9.5, 0)
            .circle(radius=1.0, density=100.0)
            .build()
        )
        joint = self.world.add_revolute_joint(previous, weight, anchor=(8.5, 0))
        joint.force_threshold = self.threshold
        self.joints.append(joint)

        self.broken = 0

    def after_step(self, dt):
        for event in self.world.get_joint_events():
            joint = event.joint
            if joint in self.joints:
                self.joints.remove(joint)
                joint.destroy()
                self.broken += 1

    @threshold.callback
    def on_threshold_change(self, key, value):
        for joint in self.joints:
            joint.force_threshold = value

    def status(self):
        return f"links intact: {len(self.joints)}   broken: {self.broken}"


class Platformer(BaseTest, category="Events", name="Platformer"):
    """One-way platforms, the classic use for a pre-solve callback.

    The player passes up through a platform but lands on top of it. Deciding
    that needs the contact normal, which pre-solve sees after the contact is
    found and before it is solved. Emptying the manifold's points there drops
    the contact for that step; the callback's return value is ignored.

    The callback only reads its arguments and edits the manifold. Box2D
    calls it in the middle of the step, and with more than one thread on the
    world, from its worker threads, several at once. Python's lock keeps
    that from crashing, but not from losing updates: ``count += 1`` reads
    and then writes, and another thread can write in between. So anything
    the scene wants to know is worked out after the step instead, on the
    main thread -- here, what the player is standing on, from the contacts
    that survived pre-solve.

    Move with the left and right arrow keys, and jump with space from
    anything you stand on. Force is the push the arrows give, in N, and Jump
    Impulse the kick space gives, in N s.
    """

    camera_center = (0, 6)
    camera_zoom = 12.0

    force = UI.float(25.0, min=0.0, max=50.0)
    jump_impulse = UI.float(25.0, min=0.0, max=50.0)

    def setup(self):
        ground = self.world.new_body().static().segment((-20, 0), (20, 0)).build()

        # Both platforms let contacts through from below.
        platform = (
            self.world.new_body()
            .static()
            .position(-6, 6)
            .box(4, 1, enable_pre_solve_events=True)
            .build()
        )
        self.moving_platform = (
            self.world.new_body()
            .kinematic()
            .position(0, 6)
            .linear_velocity(2, 0)
            .box(6, 1, enable_pre_solve_events=True)
            .build()
        )

        self.player = (
            self.world.new_body()
            .dynamic()
            .position(0, 1)
            .lock_rotation()
            .linear_damping(0.5)
            .capsule((0, 0), (0, 1), radius=0.5, friction=0.1)
            .build()
        )
        self.player_shape = self.player.shapes[0]
        self.surfaces = {
            ground: "the ground",
            platform: "the platform",
            self.moving_platform: "the moving platform",
        }

        self.world.pre_solve = self.on_pre_solve
        self.world.pre_continuous = self.on_pre_continuous
        self.held = set()
        self.standing_on = None

    def on_pre_solve(self, shape_a, shape_b, manifold):
        """Drop the contact unless the player is on top of the platform."""
        if not self.player_is_above(shape_a, shape_b, manifold.normal):
            manifold.points.clear()

    def on_pre_continuous(self, shape_a, shape_b, point, normal):
        """The same rule, for a player moving fast enough to tunnel."""
        return self.player_is_above(shape_a, shape_b, normal)

    def player_is_above(self, shape_a, shape_b, normal):
        """True unless this is the player meeting a platform from below or
        the side.

        The normal points from shape_a to shape_b, so its sign tells us which
        side of the contact the player is on.
        """
        if shape_a is self.player_shape:
            sign = -1.0
        elif shape_b is self.player_shape:
            sign = 1.0
        else:
            return True

        return sign * normal.y > 0.95

    def after_step(self, dt):
        self.standing_on = self.support()

        # Turn the moving platform round at either end of its run.
        if self.moving_platform.position.x > 8:
            self.moving_platform.linear_velocity = (-2, 0)
        elif self.moving_platform.position.x < -8:
            self.moving_platform.linear_velocity = (2, 0)

        if "left" in self.held:
            self.player.apply_force((-self.force, 0))
        if "right" in self.held:
            self.player.apply_force((self.force, 0))

    def on_key_down(self, key):
        if key in ("left", "right"):
            self.held.add(key)
        elif key == "space" and self.standing_on is not None:
            self.player.apply_linear_impulse((0, self.jump_impulse))

    def on_key_up(self, key):
        self.held.discard(key)

    def support(self):
        """The body the player is standing on, or None in the air.

        Only touching contacts are listed, and a contact pre-solve dropped
        is not touching, so a platform the player is passing up through
        never shows here. Those contacts were found before the step moved
        the player, though, so for one step after a jump they still hold
        the ground it left; a player on its way up is not standing, as in
        Box2D's sample.
        """
        if self.player.linear_velocity.y > 0.01:
            return None
        for contact in self.player.contact_data:
            if contact.shape_b is self.player_shape:
                other, up = contact.shape_a, contact.manifold.normal.y
            else:
                other, up = contact.shape_b, -contact.manifold.normal.y
            # Something to stand on is underneath, not beside the player.
            if up > 0.7:
                return other.body
        return None

    def status(self):
        if self.standing_on is None:
            return "in the air"
        return f"standing on {self.surfaces[self.standing_on]}"


class SensorFunnel(BaseTest, category="Events", name="Sensor Funnel"):
    """Ragdolls dropped through a funnel of spinning paddles, deleted at the
    bottom.

    A sensor across the outlet reports what reaches it, and each figure is
    removed when it does -- which is the point: the sensor is what tells you
    something arrived, without a collision response that would stop it. A
    sensor only sees shapes that allow it with enable_sensor_events, which
    box2d-py defaults to True; Box2D itself defaults it to False.

    Destruction is deferred until the events have all been read. A figure
    has eleven bodies and any of them can trip the sensor, so destroying it
    on the first event would leave the rest of its events naming shapes that
    no longer exist.

    Shape empties the funnel and drops ragdolls or soft donuts instead.
    """

    camera_center = (0, 0)
    camera_zoom = 33.3

    shape = UI.select("human", ["human", "donut"])

    MAX_ELEMENTS = 32
    SPAWN_INTERVAL = 0.5

    # The funnel, as a closed chain: three ledges either side above a narrow
    # outlet, taken from the C++ sample.
    FUNNEL = [
        (-16.867, 31.089),
        (16.867, 31.089),
        (16.867, 17.198),
        (8.268, 11.906),
        (16.867, 11.906),
        (16.867, -0.661),
        (8.268, -5.953),
        (16.867, -5.953),
        (16.867, -13.229),
        (3.638, -23.151),
        (3.638, -31.089),
        (-3.638, -31.089),
        (-3.638, -23.151),
        (-16.867, -13.229),
        (-16.867, -5.953),
        (-8.268, -5.953),
        (-16.867, -0.661),
        (-16.867, 11.906),
        (-8.268, 11.906),
        (-16.867, 17.198),
    ]

    def setup(self):
        ground = (
            self.world.new_body()
            .static()
            .chain(self.FUNNEL, loop=True, materials=[SurfaceMaterial(friction=0.2)])
            .box(8, 2, offset=(0, -30.5), is_sensor=True)
            .build()
        )

        # Three paddles, turning opposite ways, to knock things about on the
        # way down rather than letting them drop straight through.
        sign = 1.0
        for level in range(3):
            y = 14.0 - level * 14.0
            paddle = (
                self.world.new_body()
                .dynamic()
                .position(0, y)
                .box(12, 1, friction=0.1, restitution=1.0)
                .build()
            )
            self.world.add_revolute_joint(
                ground,
                paddle,
                anchor=(0, y),
                enable_motor=True,
                motor_speed=2.0 * sign,
                max_motor_torque=200.0,
            )
            sign = -sign

        self.elements = []
        self.spawned = 0
        self.side = -15.0
        self.wait = self.SPAWN_INTERVAL
        self.delivered = 0
        self.spawn()

    def spawn(self):
        if len(self.elements) >= self.MAX_ELEMENTS:
            return
        position = (self.side, 29.5)
        self.spawned += 1

        if self.shape == "human":
            element = Human(
                self.world,
                position,
                scale=2.0,
                friction_torque=0.05,
                hertz=6.0,
                damping_ratio=0.5,
                # A figure's bones share a negative group, so they pass
                # through one another. Two figures sharing one would pass
                # through each other too, so every figure gets its own.
                group_index=self.spawned,
            )
            bodies = [bone.body for bone in element.bones]
        else:
            bodies, _ = donut(self.world, position, radius=0.75)
            element = bodies

        # Every body points back at what it belongs to, so a sensor event on
        # any one of them identifies the whole thing.
        for body in bodies:
            body.user_data = element

        self.elements.append(element)
        self.side = -self.side

    def clear(self):
        for element in self.elements:
            self.remove(element)
        self.elements = []

    def remove(self, element):
        if isinstance(element, Human):
            element.destroy()
        else:
            for body in element:
                body.destroy()
        # A body takes its joints with it, the mouse joint included when the
        # figure was being dragged; the drag ends there.
        if self.mouse_joint is not None and not self.mouse_joint.is_valid:
            self.mouse_joint = None

    @shape.callback
    def on_shape_change(self, key, value):
        # Only the figures go: the funnel keeps turning, as in Box2D's sample.
        self.clear()
        self.spawn()

    def after_step(self, dt):
        self.wait -= dt
        if self.wait <= 0.0:
            self.spawn()
            self.wait = self.SPAWN_INTERVAL

        # Collect first, destroy after: one figure trips the sensor with
        # several bodies, and destroying it mid-loop would invalidate the
        # shapes the remaining events still refer to.
        arrived = []
        for event in self.world.get_sensor_events().begin:
            element = event.visitor.body.user_data
            if element is not None and element not in arrived:
                arrived.append(element)

        for element in arrived:
            if element in self.elements:
                self.elements.remove(element)
                self.remove(element)
                self.delivered += 1

    def status(self):
        return f"in the funnel: {len(self.elements)}   delivered: {self.delivered}"
