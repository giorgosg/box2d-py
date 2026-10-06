import math
import random
from itertools import product

from box2d import (
    CapsuleDef,
    CircleDef,
    Color,
    PolygonDef,
    SegmentDef,
    SurfaceMaterial,
    Vec2,
)

from .base_test import UI, BaseTest
from .shared import random_polygon


class RoundedShapes(BaseTest, category="Shapes", name="Rounded"):
    """A hundred random polygons with rounded corners, dropped into a box.

    Each is the hull of three to eight random points, given a rounding radius
    of 0.05 to 0.125. Box2D treats a rounded polygon as the polygon with a
    skin of that thickness all round, so its corners become arcs. That costs
    no extra vertices, and rounded corners do not snag on one another the way
    sharp ones can. Watch them tumble into a heap, or drag one through it.
    """

    def setup(self):
        (
            self.world.new_body()
            .static()
            .box(20, 2, offset=(0, -1))
            .box(2, 10, offset=(9, 5))
            .box(2, 10, offset=(-9, 5))
            .build()
        )

        for x, y in product(range(10), range(10)):
            polygon = random_polygon(0.5)
            (
                self.world.new_body()
                .dynamic()
                .position(-5 + x, 2 + y)
                .polygon(polygon.vertices, polygon.radius)
                .build()
            )


class Friction(BaseTest, category="Shapes", name="Friction"):
    """Five boxes slide down a zigzag of ramps, each less grippy than the last.

    The boxes have friction 0.75, 0.5, 0.35, 0.1 and 0. Box2D mixes two
    friction coefficients by their geometric mean, and the ramps have 0.2, so
    against a ramp the boxes have 0.39, 0.32, 0.26, 0.14 and 0. A box can
    rest on a ramp when that beats the ramp's gradient, tan(0.25) = 0.26. The
    first two stop on the top ramp. The third only just grips: it slides the
    length of the top ramp before friction has slowed it, drops off, and
    stops on the second. The last two run down every ramp, and the
    frictionless one slides off the end of the ground.
    """

    def setup(self):
        (
            self.world.new_body()
            .static()
            .segment((-40, 0), (40, 0), friction=0.2)
            .box(26.0, 0.5, offset=(-4.0, 22.0), angle=-0.25, friction=0.2)
            .box(0.5, 2.0, offset=(10.5, 19.0), friction=0.2)
            .box(26.0, 0.5, offset=(4.0, 14.0), angle=0.25, friction=0.2)
            .box(0.5, 2.0, offset=(-10.5, 11.0), friction=0.2)
            .box(26.0, 0.5, offset=(-4.0, 6.0), angle=-0.25, friction=0.2)
            .build()
        )

        for i, friction in enumerate([0.75, 0.5, 0.35, 0.1, 0.0]):
            (
                self.world.new_body()
                .dynamic()
                .position(-15.0 + 4.0 * i, 28.0)
                .box(1.0, 1.0, friction=friction, density=25.0)
                .build()
            )


class Restitution(BaseTest, category="Shapes", name="Restitution"):
    """Forty bodies dropped from the same height, from restitution 0 on the
    left to 1 on the right.

    A body bounces back to about restitution squared of the height it fell
    from, so the middle one, at 0.5, comes back up a quarter of the way and
    the last returns to where it started. It is only about: Box2D solves
    contacts speculatively, a little before the bodies touch, which makes
    restitution approximate.

    Shape rebuilds the scene with circles, boxes, random polygons or
    capsules. The polygons land on their corners and tumble, which scatters
    their bounces.
    """

    shape = UI.select("circle", ["circle", "box", "polygon", "capsule"])

    def setup(self):
        self.world.new_body().static().segment((-40, 0), (40, 0), restitution=0).build()

        count = 40
        for i in range(count):
            restitution = i / (count - 1)
            builder = self.world.new_body().dynamic().position(-(count - 1) + 2 * i, 40)
            if self.shape == "circle":
                builder.circle(0.5, restitution=restitution, density=1.0)
            elif self.shape == "box":
                builder.box(1.0, 1.0, restitution=restitution, density=1.0)
            elif self.shape == "polygon":
                polygon = random_polygon(0.5)
                builder.polygon(
                    polygon.vertices,
                    polygon.radius,
                    restitution=restitution,
                    density=1.0,
                )
            else:
                builder.capsule(
                    (0, -0.5),
                    (0, 0.5),
                    radius=0.5,
                    restitution=restitution,
                    density=1.0,
                )
            builder.build()

    @shape.callback
    def on_shape_change(self, key, value):
        self.rebuild()


class ModifyGeometry(BaseTest, category="Shapes", name="Modify Geometry"):
    """A box resting on a kinematic platform whose shape is changed live.

    Scale gives the platform's shape new geometry in place, and the box on
    top is woken to move with it. Shape swaps the platform's shape for a
    circle, capsule, segment or polygon. Box2D can change a shape's kind in
    place too, but this binding's shapes are typed -- a Circle stays a
    Circle -- so a new kind is a new shape on the same body. The status line
    names the shape the platform has now.
    """

    camera_center = (0, 5)
    camera_zoom = 6.25

    shape = UI.select("circle", ["circle", "capsule", "segment", "polygon"])
    scale = UI.float(1.0, min=0.1, max=4.0)

    def setup(self):
        self.world.new_body().static().box(20, 2, offset=(0, -1)).build()
        self.world.new_body().dynamic().position(0, 4).box(2, 2).build()

        self.platform = self.world.new_body().kinematic().position(0, 1).build()
        self.platform_shape = self.platform.add_circle(radius=0.5)

    def geometry(self):
        """The selected shape at the selected scale, sized as in Box2D's sample."""
        scale = self.scale
        if self.shape == "circle":
            return CircleDef(radius=0.5 * scale)
        if self.shape == "capsule":
            return CapsuleDef((-0.5 * scale, 0), (0, 0.5 * scale), radius=0.5 * scale)
        if self.shape == "segment":
            return SegmentDef((-0.5 * scale, 0), (0.75 * scale, 0))
        half_width, half_height = 0.5 * scale, 0.75 * scale
        return PolygonDef(
            [
                (-half_width, -half_height),
                (half_width, -half_height),
                (half_width, half_height),
                (-half_width, half_height),
            ]
        )

    def add_shape(self, geometry):
        """Give the platform a new shape of whichever kind the geometry is."""
        if isinstance(geometry, CircleDef):
            return self.platform.add_circle(geometry.radius, geometry.center)
        if isinstance(geometry, CapsuleDef):
            return self.platform.add_capsule(
                geometry.vertex1, geometry.vertex2, geometry.radius
            )
        if isinstance(geometry, SegmentDef):
            return self.platform.add_segment(geometry.vertex1, geometry.vertex2)
        return self.platform.add_polygon(geometry.vertices)

    @shape.callback
    @scale.callback
    def on_change(self, key, value):
        geometry = self.geometry()
        if isinstance(self.platform_shape.geometry, type(geometry)):
            self.platform_shape.geometry = geometry
        else:
            self.platform_shape.destroy()
            self.platform_shape = self.add_shape(geometry)
        # New geometry leaves the body's mass as it was. A kinematic body has
        # no mass to update, but this is the call a dynamic one would need.
        self.platform.update_mass_from_shapes()

    def status(self):
        kind = type(self.platform_shape).__name__.lower()
        return f"platform: {kind}, scale {self.scale:.2f}"


class ConveyorBelt(BaseTest, category="Shapes", name="Conveyor Belt"):
    """A static platform whose surface runs like a belt, carrying boxes off
    the end.

    The platform's body never moves. Its shape's tangent speed tells the
    contact solver to treat the surface as though it slid along at that
    speed, so friction drags whatever rests on it -- to the right when the
    speed is positive. Tangent speed changes the running belt.
    """

    camera_center = (2, 7.5)
    camera_zoom = 12.0

    tangent_speed = UI.float(2.0, min=-10.0, max=10.0)

    def setup(self):
        self.world.new_body().static().segment((-20, 0), (20, 0)).build()

        # The belt can only pull as hard as friction allows, hence grippy.
        # Box2D reuses a contact that has barely moved without reading the
        # shapes' materials again, so a box at rest on the belt would never
        # see a new speed. Not recycling the belt's contacts makes them read
        # it every step.
        self.belt = (
            self.world.new_body()
            .static()
            .enable_contact_recycling(False)
            .position(-5, 5)
            .box(20, 0.5, radius=0.25, friction=0.8, tangent_speed=self.tangent_speed)
            .build()
        )

        box = self.world.new_body().dynamic().box(1, 1)
        for i in range(5):
            box.position(-10 + 2 * i, 7).build()

    @tangent_speed.callback
    def on_speed_change(self, key, value):
        for shape in self.belt.shapes:
            shape.tangent_speed = value
        # Boxes at rest on a still belt fall asleep, and would not notice.
        self.belt.wake_touching()


class CustomFilter(BaseTest, category="Shapes", name="Custom Filter"):
    """A row of numbered boxes in which odd and even boxes ignore each other.

    Collision categories cannot say "these two particular shapes ignore each
    other", so the world's custom filter decides pair by pair instead. Box2D
    asks it only about shapes created with enable_custom_filtering.

    The boxes start side by side and simply land, so drag one into its
    neighbours: it passes through boxes of the other parity and shoves boxes
    of its own. Count rebuilds the row. The status line counts the times the
    filter has said no -- Box2D asks again about a rejected pair whenever
    either box moves, so it climbs while anything is moving.
    """

    camera_center = (0, 5)
    camera_zoom = 10.0

    count = UI.int(10, min=2, max=20)

    def setup(self):
        self.world.new_body().static().segment((-40, 0), (40, 0)).build()

        self.index_of = {}
        box = self.world.new_body().dynamic().box(2, 2, enable_custom_filtering=True)
        for i in range(self.count):
            body = box.position(-self.count + 2.0 * i, 5).build()
            self.index_of[body.shapes[0]] = i

        self.world.custom_filter = self.should_collide
        self.rejected = 0

    def should_collide(self, shape_a, shape_b):
        """Let a pair through unless one box is odd and the other even."""
        a = self.index_of.get(shape_a)
        b = self.index_of.get(shape_b)
        if a is None or b is None:
            return True  # the ground
        if (a & 1) != (b & 1):
            self.rejected += 1
            return False
        return True

    @count.callback
    def on_count_change(self, key, value):
        self.rebuild()

    def debug_draw(self, debug_draw):
        for shape, index in self.index_of.items():
            debug_draw.draw_string(shape.body.position, str(index))

    def status(self):
        return f"filter said no {self.rejected} times"


class Explosion(BaseTest, category="Shapes", name="Explosion"):
    """A ring of twelve planks around a blast, each held in place by a
    springy weld.

    Explode applies a radial impulse from the centre: in full out to Radius,
    fading to nothing over Falloff beyond it. The two circles mark those
    distances. The impulse is per metre of outline the blast can see, so
    which way a plank faces matters as much as how far away it is. The
    planks all lie level: the two beside the centre point straight at it,
    show it only their 0.2 m ends and barely move, while those above and
    below take it broadside and fly. A negative impulse pulls inward. The
    welds are springs, and pull the planks back to the ring for the next
    blast.
    """

    camera_center = (0, 0)
    camera_zoom = 14.0

    radius = UI.float(7.0, min=0.0, max=20.0)
    falloff = UI.float(3.0, min=0.0, max=20.0)
    impulse = UI.float(10.0, min=-20.0, max=50.0)
    detonate = UI.button("Explode")

    def setup(self):
        ground = self.world.new_body().static().build()

        ring_radius = 8.0
        plank = self.world.new_body().dynamic().gravity_scale(0).box(2, 0.2)
        for degrees in range(0, 360, 30):
            angle = math.radians(degrees)
            position = Vec2(
                ring_radius * math.cos(angle), ring_radius * math.sin(angle)
            )
            body = plank.position(position).build()
            self.world.add_weld_joint(
                ground,
                body,
                local_anchor_a=position,
                local_anchor_b=(0, 0),
                linear_hertz=0.5,
                linear_damping_ratio=0.7,
                angular_hertz=0.5,
                angular_damping_ratio=0.7,
            )

        self.blasts = 0

    @detonate.callback
    def on_detonate(self, key, value):
        self.world.explode(
            (0, 0),
            radius=self.radius,
            falloff=self.falloff,
            impulse_per_length=self.impulse,
        )
        self.blasts += 1

    def debug_draw(self, debug_draw):
        debug_draw.draw_circle((0, 0), self.radius, Color(255, 160, 0))
        debug_draw.draw_circle((0, 0), self.radius + self.falloff, Color(120, 90, 0))

    def status(self):
        return f"explosions: {self.blasts}"


class Wind(BaseTest, category="Shapes", name="Wind"):
    """A chain of planks hanging from a pin, blown about by a gusting wind.

    Box2D applies wind shape by shape, from how much of the shape the wind
    can see and how fast the shape already moves through the air, so a plank
    broadside on catches far more than one edge on. Drag is how much the
    shape's own motion counts against the wind; lift pushes across the wind,
    which is what makes the chain flutter rather than simply stream out. The
    gust is the wind's direction plus a slowly wandering noise, scaled to its
    speed, and the magenta line from the pin shows it. Links rebuilds the
    chain.
    """

    camera_center = (0, -4)
    camera_zoom = 14.0

    wind_x = UI.float(10.0, min=-20.0, max=20.0)
    wind_y = UI.float(0.0, min=-20.0, max=20.0)
    drag = UI.float(0.5, min=0.0, max=1.0)
    lift = UI.float(0.5, min=0.0, max=4.0)
    links = UI.int(12, min=1, max=30)

    def setup(self):
        ground = self.world.new_body().static().build()

        radius = 0.5
        previous = ground
        self.shapes = []
        link = self.world.new_body().dynamic().box(0.2, 2 * radius, density=1.0)
        for i in range(self.links):
            body = link.position(0, -radius - 2 * radius * i).build()
            self.world.add_revolute_joint(
                previous,
                body,
                local_anchor_a=(0, 0) if previous is ground else (0, -radius),
                local_anchor_b=(0, radius),
            )
            self.shapes.append(body.shapes[0])
            previous = body

        self.noise = Vec2(0, 0)
        self.gust = Vec2(0, 0)

    def after_step(self, dt):
        wind = Vec2(self.wind_x, self.wind_y)
        speed = wind.length
        if speed > 0:
            direction = wind * (1.0 / speed)
            self.gust = (direction + self.noise) * speed
        else:
            self.gust = Vec2(0, 0)

        for shape in self.shapes:
            shape.apply_wind(self.gust, drag=self.drag, lift=self.lift)

        # Wander the noise slowly so the gust is never quite steady.
        target = Vec2(random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3))
        self.noise = self.noise + (target - self.noise) * 0.05

    @links.callback
    def on_links_change(self, key, value):
        self.rebuild()

    def debug_draw(self, debug_draw):
        debug_draw.draw_segment((0, 0), self.gust * 0.2, Color(255, 0, 255))

    def status(self):
        return f"gust ({self.gust.x:.1f}, {self.gust.y:.1f}) m/s"


class RollingResistance(BaseTest, category="Shapes", name="Rolling Resistance"):
    """Twenty wheels set rolling along twenty lanes, each lane up with more
    rolling resistance than the one below.

    A wheel rolling without slipping loses nothing to friction, since its
    contact point does not slide, so on its own it would roll forever, as
    the bottom one does. Rolling resistance is a torque at the contact
    against the two shapes turning relative to each other, up to the
    coefficient times the radius times the contact force: a limit like
    friction's, but on turning rather than sliding. It slows the spin, and
    friction slows the wheel with it, so each lane up stops sooner; the top
    wheel stops in about two seconds. Box2D scales it by the shapes' radius,
    so it only acts on circles, capsules and rounded polygons.

    Resistance Scale is how much resistance each lane adds. Lane tilt raises
    the right end of every lane, in metres: uphill every wheel stops, and
    those with too little resistance to hold on the slope roll back; downhill
    only the lanes whose resistance outweighs the slope can stop theirs.
    Both rebuild the scene. The status line counts the wheels stopped.
    """

    camera_center = (5, 20)
    camera_zoom = 27.5

    resistance_scale = UI.float(0.02, min=0.0, max=0.2)
    lift = UI.float(0.0, min=-10.0, max=10.0, label="Lane tilt")

    def setup(self):
        self.wheels = []
        for i in range(20):
            y = 2.0 * i
            self.world.new_body().static().segment(
                (-40, y), (40, y + self.lift)
            ).build()

            # Spinning at the rate that rolls it at 5 m/s, so it starts out
            # rolling rather than skidding.
            wheel = (
                self.world.new_body()
                .dynamic()
                .position(-39.5, y + 0.75)
                .angular_velocity(-10.0)
                .linear_velocity(5.0, 0.0)
                .circle(radius=0.5, rolling_resistance=self.resistance_scale * i)
                .build()
            )
            self.wheels.append(wheel)

    @resistance_scale.callback
    @lift.callback
    def on_change(self, key, value):
        self.rebuild()

    def status(self):
        stopped = sum(1 for w in self.wheels if abs(w.linear_velocity.x) < 0.1)
        return f"wheels stopped: {stopped} of {len(self.wheels)}"


class OffsetShapes(BaseTest, category="Shapes", name="Offset"):
    """A small stack whose shapes all sit metres from their bodies' origins.

    A shape's geometry is in body-local coordinates, so it need not sit on
    the origin. Here a block, a capsule lying on it and a box dropped on top
    are each offset from their body's origin, marked by the axes drawn
    there. Box2D puts a body's centre of mass at its shapes' centroid, so the
    stack settles level, as it would with the shapes centred. Getting the
    mass and rotation right for offset shapes is easy to break, which is
    what this exercises.
    """

    camera_center = (2, 8)
    camera_zoom = 13.75

    def setup(self):
        (
            self.world.new_body()
            .static()
            .position(-1, 1)
            .box(2, 2, offset=(10, -2), angle=0.5 * math.pi)
            .build()
        )
        (
            self.world.new_body()
            .dynamic()
            .position(13.5, -0.75)
            .capsule((-5, 1), (-4, 1), radius=0.25)
            .build()
        )
        (
            self.world.new_body()
            .dynamic()
            .box(1.5, 1.0, offset=(9, 2), angle=0.5 * math.pi)
            .build()
        )

    def debug_draw(self, debug_draw):
        for body in self.world.bodies:
            debug_draw.draw_transform(body.transform)


class ChainMaterials(BaseTest, category="Shapes", name="Chain Materials"):
    """One chain, three surfaces: a steep grippy slope, an icy middle stretch
    and a grippy flat.

    A chain takes a material per segment, when it is made or later, so the
    same ground can be grippy in one stretch and slippery in the next. The
    box slides down the slope, which is too steep to hold it at any setting,
    across the ice, and stops on the flat. Raise Icy friction and boxes stop
    on the middle stretch instead. Drop a box drops another; the newest
    twelve are kept. Each stretch is labelled with its friction.
    """

    # Framed by hand: the whole ramp, not just the one box on it.
    camera_center = (0.0, 9.0)
    camera_zoom = 14.0

    icy_friction = UI.float(0.0, min=0.0, max=1.0)
    grippy_friction = UI.float(0.9, min=0.0, max=1.0)
    drop = UI.button("Drop a box")

    # A downhill run in three stretches. Wound right-to-left: a chain collides
    # on one side only, and this is the order that puts the solid side up.
    POINTS = [(22, 0), (8, 0), (-6, 2), (-20, 16)]
    # Where the slope would carry on past each end.
    GHOST1 = (30, 4)
    GHOST2 = (-30, 24)
    ICY = 1

    def setup(self):
        # Box2D reuses a contact that has barely moved without reading the
        # materials again, so a box at rest would never feel a new friction.
        # Not recycling the ground's contacts makes them read it every step.
        ground = (
            self.world.new_body()
            .static()
            .enable_contact_recycling(False)
            .chain(
                self.POINTS,
                ghost1=self.GHOST1,
                ghost2=self.GHOST2,
                materials=[self.material(i) for i in range(len(self.POINTS) - 1)],
            )
            .build()
        )
        self.chain = ground.chains[0]
        self.boxes = []
        self.drop_box()

    def material(self, index):
        """The surface of one stretch of the chain."""
        friction = self.icy_friction if index == self.ICY else self.grippy_friction
        return SurfaceMaterial(friction=friction)

    @icy_friction.callback
    @grippy_friction.callback
    def on_friction_change(self, key, value):
        for index in range(len(self.chain.segments)):
            self.chain.set_surface_material(self.material(index), index)
        # A box that has come to rest is asleep, and would not notice.
        self.chain.body.wake_touching()

    @drop.callback
    def on_drop(self, key, value):
        self.drop_box()

    def drop_box(self):
        # Above the uphill end of the ground; anything dropped past either end
        # falls straight past it.
        box = (
            self.world.new_body()
            .dynamic()
            .position(-16, 18)
            .box(1.2, 1.2, friction=0.3)
            .build()
        )
        self.boxes.append(box)
        # Keep the scene from growing without bound as the button is pressed.
        while len(self.boxes) > 12:
            self.boxes.pop(0).destroy()

    def debug_draw(self, debug_draw):
        for index, segment in enumerate(self.chain.segments):
            label = "icy" if index == self.ICY else "grippy"
            midpoint = (Vec2(self.POINTS[index]) + Vec2(self.POINTS[index + 1])) / 2
            debug_draw.draw_string(
                midpoint + Vec2(0, 1), f"{label} {segment.friction:.2f}"
            )
