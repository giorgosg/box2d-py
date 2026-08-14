from box2d import Vec2, CollisionFilter, Color
from .base_test import BaseTest, UI


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

    hit_threshold = UI.float(1.0, min=0.0, max=20.0)

    def setup(self):
        self.app_state.center = Vec2(0, 6)
        self.app_state.zoom = 12.0

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

    def setup(self):
        self.app_state.center = Vec2(0, 6)
        self.app_state.zoom = 14.0

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

    threshold = UI.float(2000.0, min=100.0, max=20000.0)

    def setup(self):
        self.app_state.center = Vec2(0, -4)
        self.app_state.zoom = 12.0

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

    force = UI.float(25.0, min=0.0, max=50.0)
    jump_impulse = UI.float(25.0, min=0.0, max=50.0)

    def setup(self):
        self.app_state.center = Vec2(0, 6)
        self.app_state.zoom = 12.0

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
