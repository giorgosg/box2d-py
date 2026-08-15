from box2d import Vec2, CollisionFilter, Color
from .base_test import BaseTest, UI
from .human import Human
from .shared import donut
from box2d.material import SurfaceMaterial
from box2d import RevoluteJointDef


class FootSensor(BaseTest, category="Events", name="Foot Sensor"):
    def setup(self):
        ground = self.world.new_body().static()
        chain_points = [Vec2(x, 0) for x in range(10, -11, -1)]
        ground.chain(
            chain_points,
            loop=False,
            filter=CollisionFilter(category="ground", mask=["foot", "player"]),
        )
        ground = ground.build()

        player = self.world.new_body().dynamic().lock_rotation().position(0, 2)
        player = player.capsule(
            (0, -0.5),
            (0, 0.5),
            0.5,
            filter=CollisionFilter(category="player", mask=["ground"]),
        )
        player = player.box(
            1,
            0.5,
            offset=(0, -1),
            filter=CollisionFilter(category="foot", mask=["ground"]),
            is_sensor=True,
        )
        self.player = player.build()
        self.overlap_count = 0
        self.move = 0

    def on_key_down(self, key):
        if key == "a":
            self.move = -1
        elif key == "d":
            self.move = 1

    def on_key_up(self, key):
        if key in ("a", "d"):
            self.move = 0

    def after_step(self, dt):
        self.player.apply_force(self.move * Vec2(50, 0), (0, 0), True)
        sensorevents = self.world.get_sensor_events()
        self.overlap_count += len(sensorevents.begin) - len(sensorevents.end)

    def debug_draw(self, debug_draw):
        debug_draw.draw_string((5, 15), f"Overlap count: {self.overlap_count}")


class ContactEvents(BaseTest, category="Events", name="Contact"):
    """Boxes that light up while touching, and flash on a hard hit.

    Shapes report nothing by default, so both kinds of event are enabled here.
    Begin and end events maintain the touching set; hit events fire only above
    the world's hit threshold, so a gentle rest does not count.
    """

    camera_center = (0, 6)
    camera_zoom = 12.0

    hit_threshold = UI.float(1.0, min=0.0, max=20.0)

    def setup(self):

        self.world.hit_event_threshold = self.hit_threshold

        ground = self.world.new_body().static()
        ground.segment((-12, 0), (12, 0), enable_contact_events=True)
        ground.segment((-12, 0), (-12, 12), enable_contact_events=True)
        ground.segment((12, 0), (12, 12), enable_contact_events=True)
        self.ground = ground.build()
        self.ground.enable_hit_events()

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

        self.touching = set()
        self.flashes = {}
        self.hit_count = 0

    def after_step(self, dt):
        events = self.world.get_contact_events()

        for touch in events.begin:
            self.touching.add(id(touch.shape_a))
            self.touching.add(id(touch.shape_b))
        for touch in events.end:
            # A shape destroyed while touching still turns up here.
            for shape in (touch.shape_a, touch.shape_b):
                if shape is not None:
                    self.touching.discard(id(shape))

        # Fade the flashes from previous hits.
        self.flashes = {k: v - 1 for k, v in self.flashes.items() if v > 1}
        for hit in events.hit:
            self.hit_count += 1
            self.flashes[(hit.point.x, hit.point.y)] = 20

    @hit_threshold.callback
    def on_threshold_change(self, key, value):
        self.world.hit_event_threshold = value

    def debug_draw(self, debug_draw):
        for (x, y), life in self.flashes.items():
            debug_draw.draw_point((x, y), 4 + life, Color(255, 200, 0))
        debug_draw.draw_string(
            (-11, 11), f"touching: {len(self.touching)}   hits: {self.hit_count}"
        )


class BodyMoveEvents(BaseTest, category="Events", name="Body Move"):
    """Only the bodies that actually moved are reported each step.

    Box2D hands back a move event per moving body, which is cheaper than
    walking every body to refresh what you draw. As the pile settles the count
    falls to zero, and the sleeping bodies are marked as they drop out.
    """

    camera_center = (0, 6)
    camera_zoom = 14.0

    def setup(self):

        self.world.new_body().static().segment((-15, 0), (15, 0)).build()

        boxes = self.world.new_body().dynamic().box(0.8, 0.8, friction=0.6)
        for row in range(6):
            for column in range(6 - row):
                boxes.position(-3 + column + 0.5 * row, 0.5 + row).build()

        self.moved = 0
        self.asleep = 0

    def after_step(self, dt):
        events = self.world.get_body_events()
        self.moved = len(events)
        self.asleep += sum(1 for event in events if event.fell_asleep)

    def debug_draw(self, debug_draw):
        debug_draw.draw_string(
            (-13, 11),
            f"moving this step: {self.moved} of {len(self.world.bodies)}"
            f"   fell asleep: {self.asleep}",
        )


class BreakableJoint(BaseTest, category="Events", name="Joint"):
    """A chain whose links break when pulled past their force threshold.

    A joint reports nothing until a threshold is set. Here every link reports
    above force_threshold, and the reported joints are destroyed, so the chain
    parts under the weight hung from its end.
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

    def debug_draw(self, debug_draw):
        debug_draw.draw_string(
            (-10, 4), f"links intact: {len(self.joints)}   broken: {self.broken}"
        )


class Platformer(BaseTest, category="Events", name="Platformer"):
    """One-way platforms, the classic use for a pre-solve callback.

    The player passes up through a platform but lands on top of it. Deciding
    that needs the contact normal, which only pre-solve has: it runs after the
    contact is found but before it is solved, and returning False drops it for
    this step.

    Move with the arrow keys, jump with space.
    """

    camera_center = (0, 6)
    camera_zoom = 12.0

    force = UI.float(25.0, min=0.0, max=50.0)
    jump_impulse = UI.float(25.0, min=0.0, max=50.0)

    def setup(self):

        self.world.new_body().static().segment((-20, 0), (20, 0)).build()

        # Both platforms let contacts through from below.
        self.world.new_body().static().position(-6, 6).box(
            4, 1, enable_pre_solve_events=True
        ).build()
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

        self.world.pre_solve = self.on_pre_solve
        self.held = set()
        self.dropped = 0

    def on_pre_solve(self, shape_a, shape_b, point, normal):
        """Keep the contact only when the player is above the platform.

        The normal points from shape_a to shape_b, so its sign tells us which
        side of the contact the player is on.
        """
        if shape_a is self.player_shape:
            sign = -1.0
        elif shape_b is self.player_shape:
            sign = 1.0
        else:
            return True

        if sign * normal.y > 0.95:
            return True
        self.dropped += 1
        return False

    def after_step(self, dt):
        # Bounce the moving platform between two walls.
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
        elif key == "space":
            self.player.apply_linear_impulse((0, self.jump_impulse))

    def on_key_up(self, key):
        self.held.discard(key)

    def debug_draw(self, debug_draw):
        debug_draw.draw_string(
            (-11, 11),
            f"arrows to move, space to jump   contacts dropped: {self.dropped}",
        )


class SensorFunnel(BaseTest, category="Events", name="Sensor Funnel"):
    """Ragdolls dropped through a funnel of spinning paddles, deleted at the bottom.

    A sensor across the outlet reports what reaches it, and each figure is
    removed when it does -- which is the point: the sensor is what tells you
    something arrived, without a collision response that would stop it.

    Destruction is deferred to the end of the step. A figure has eleven bodies
    and any of them can trip the sensor, so acting on the first event would
    destroy the rest while their events are still being read.
    """

    camera_center = (0, 0)
    camera_zoom = 25.0 * 1.333

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
        ground = self.world.add_body(position=(0, 0))
        ground.add_chain(
            self.FUNNEL, loop=True, materials=[SurfaceMaterial(friction=0.2)]
        )

        # Three paddles, turning opposite ways, to knock things about on the
        # way down rather than letting them drop straight through.
        sign = 1.0
        for level in range(3):
            y = 14.0 - level * 14.0
            paddle = self.world.add_body(body_type="dynamic", position=(0, y))
            paddle.add_box(12, 1, friction=0.1, restitution=1.0)
            self.world.add_joint(
                RevoluteJointDef(
                    ground,
                    paddle,
                    local_anchor_a=(0, y),
                    local_anchor_b=(0, 0),
                    enable_motor=True,
                    motor_speed=2.0 * sign,
                    max_motor_torque=200.0,
                )
            )
            sign = -sign

        self.sensor = ground.add_box(
            8, 2, offset=(0, -30.5), is_sensor=True, enable_sensor_events=True
        )

        self.elements = []
        self.side = -15.0
        self.wait = 0.0
        self.delivered = 0
        self.spawn()

    def spawn(self):
        if len(self.elements) >= self.MAX_ELEMENTS:
            return
        position = (self.side, 29.5)

        if self.shape == "human":
            element = Human(
                self.world,
                position,
                scale=2.0,
                friction_torque=0.05,
                hertz=6.0,
                damping_ratio=0.5,
                group_index=len(self.elements) + 1,
            )
            element.enable_sensor_events(True)
            bodies = [bone.body for bone in element.bones]
        else:
            bodies, _ = donut(self.world, position, radius=0.75)
            for body in bodies:
                for shape in body.shapes:
                    shape.enable_sensor_events = True
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
                if body.is_valid:
                    body.destroy()

    @shape.callback
    def on_shape_change(self, key, value):
        if hasattr(self, "elements"):
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

    def debug_draw(self, debug_draw):
        debug_draw.draw_string(
            (-15, 33),
            f"in the funnel: {len(self.elements)}   delivered: {self.delivered}",
            color=Color(255, 255, 255, 255),
        )
