# test_shapes.py

from .base_test import BaseTest, UI
from itertools import product
import math
import random

# imported for the side effect of extending BodyBuilder with the method
from .shared import create_random_polygon  # noqa: F401
from box2d import Vec2, Color
from box2d.shape import Circle, Capsule, Segment, Polygon
from box2d.shapedef import CapsuleDef, SegmentDef, PolygonDef


class RoundedShapes(BaseTest, category="Shapes", name="Rounded"):
    def setup(self):
        (
            self.world.new_body()
            .static()
            .box(20, 2, offset=(0, -1))
            .box(2, 10, offset=(9, 5))
            .box(2, 10, offset=(-9, 5))
            .build()
        )

        xcount, ycount = 10, 10
        xstart, ystart = -5, 2

        for x, y in product(range(xcount), range(ycount)):
            (
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
    shape = UI.select("circle", ["circle", "box", "polygon", "capsule"])

    def setup(self):
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
        shape = self.shape
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

    @shape.callback
    def on_shape_change(self, key, new_value):
        for body in self.world.bodies:
            body.destroy()
        self.setup()


class ModifyGeometry(BaseTest, category="Shapes", name="Modify Geometry"):
    """Reshape a live shape in place.

    The kinematic platform's shape is swapped between geometry types and
    rescaled without recreating the body, using the shape's geometry
    properties. The body's mass has to be recomputed afterwards.
    """

    shape = UI.select("circle", ["circle", "capsule", "segment", "polygon"])
    scale = UI.float(1.0, min=0.1, max=4.0)

    def setup(self):
        self.app_state.center = Vec2(0, 5)
        self.app_state.zoom = 25.0 * 0.25

        self.world.new_body().static().box(20, 2, offset=(0, -1)).build()
        self.world.new_body().dynamic().position(0, 4).box(2, 2).build()

        self.platform = self.world.new_body().kinematic().position(0, 1).build()
        self.shape_obj = self.platform.add_circle(radius=0.5)

    def update_shape(self):
        """Replace the platform's geometry with the currently selected shape."""
        body = self.shape_obj.body
        scale = self.scale

        # A shape cannot change type in place, so swap the object when needed
        # and only touch the geometry when the type already matches.
        if self.shape == "circle" and isinstance(self.shape_obj, Circle):
            self.shape_obj.radius = 0.5 * scale
        elif self.shape == "capsule" and isinstance(self.shape_obj, Capsule):
            self.shape_obj.geometry = CapsuleDef(
                (-0.5 * scale, 0), (0, 0.5 * scale), 0.5 * scale
            )
        elif self.shape == "segment" and isinstance(self.shape_obj, Segment):
            self.shape_obj.geometry = SegmentDef((-0.5 * scale, 0), (0.75 * scale, 0))
        elif self.shape == "polygon" and isinstance(self.shape_obj, Polygon):
            self.shape_obj.geometry = PolygonDef(
                [
                    (-0.5 * scale, -0.75 * scale),
                    (0.5 * scale, -0.75 * scale),
                    (0.5 * scale, 0.75 * scale),
                    (-0.5 * scale, 0.75 * scale),
                ]
            )
        else:
            self.shape_obj = self._recreate(body, scale)

        body.apply_mass_from_shapes()

    def _recreate(self, body, scale):
        """Attach a fresh shape of the selected type, dropping the old one."""
        self.shape_obj.destroy()
        if self.shape == "circle":
            return body.add_circle(radius=0.5 * scale)
        if self.shape == "capsule":
            return body.add_capsule(
                point1=(-0.5 * scale, 0), point2=(0, 0.5 * scale), radius=0.5 * scale
            )
        if self.shape == "segment":
            return body.add_segment(point1=(-0.5 * scale, 0), point2=(0.75 * scale, 0))
        half_w, half_h = 0.5 * scale, 0.75 * scale
        return body.add_polygon(
            vertices=[
                (-half_w, -half_h),
                (half_w, -half_h),
                (half_w, half_h),
                (-half_w, half_h),
            ]
        )

    @shape.callback
    @scale.callback
    def on_change(self, key, value):
        self.update_shape()

    def debug_draw(self, debug_draw):
        debug_draw.draw_string(
            (-5, 8), f"{type(self.shape_obj).__name__.lower()}, scale {self.scale:.2f}"
        )


class ConveyorBelt(BaseTest, category="Shapes", name="Conveyor Belt"):
    """A surface whose tangent speed drags whatever rests on it sideways."""

    tangent_speed = UI.float(2.0, min=-10.0, max=10.0)

    def setup(self):
        self.app_state.center = Vec2(2, 7.5)
        self.app_state.zoom = 12.0

        self.world.new_body().static().segment((-20, 0), (20, 0)).build()

        self.belt = (
            self.world.new_body()
            .static()
            .position(-5, 5)
            .box(20, 0.5, radius=0.25, friction=0.8, tangent_speed=self.tangent_speed)
            .build()
        )

        boxes = self.world.new_body().dynamic().box(1, 1)
        for i in range(5):
            boxes.position(-10 + 2 * i, 7).build()

    @tangent_speed.callback
    def on_speed_change(self, key, value):
        for shape in self.belt.shapes:
            shape.tangent_speed = value


class CustomFilter(BaseTest, category="Shapes", name="Custom Filter"):
    """Odd and even boxes pass through each other.

    Collision categories cannot express "these two particular shapes ignore
    each other", so the world's custom filter decides per pair instead. It is
    consulted only for shapes created with enable_custom_filtering.
    """

    count = UI.int(10, min=2, max=20)

    def setup(self):
        self.app_state.center = Vec2(0, 5)
        self.app_state.zoom = 10.0

        self.world.new_body().static().segment((-40, 0), (40, 0)).build()

        self.index_of = {}
        boxes = self.world.new_body().dynamic().box(2, 2, enable_custom_filtering=True)
        for i in range(self.count):
            body = boxes.position(-self.count + 2.0 * i, 5).build()
            self.index_of[body.shapes[0]] = i

        self.world.custom_filter = self.should_collide
        self.rejected = 0

    def should_collide(self, shape_a, shape_b):
        """Let a pair through when their indices differ in parity."""
        a = self.index_of.get(shape_a)
        b = self.index_of.get(shape_b)
        if a is None or b is None:
            return True  # anything against the ground still collides
        if (a & 1) != (b & 1):
            self.rejected += 1
            return False
        return True

    @count.callback
    def on_count_change(self, key, value):
        self.world.custom_filter = None
        for body in self.world.bodies:
            body.destroy()
        self.setup()

    def debug_draw(self, debug_draw):
        for shape, index in self.index_of.items():
            if shape.is_valid():
                debug_draw.draw_string(shape.body.position, str(index))
        debug_draw.draw_string((-9, 9), f"odd/even pairs rejected: {self.rejected}")


class Explosion(BaseTest, category="Shapes", name="Explosion"):
    """A ring of soft-welded planks blown outward by a radial impulse.

    Each plank is held to the ground by a springy weld joint, so the blast
    scatters them and the springs pull them back, which makes the falloff
    easy to see: planks near the edge barely move.
    """

    radius = UI.float(7.0, min=0.0, max=20.0)
    falloff = UI.float(3.0, min=0.0, max=20.0)
    impulse = UI.float(10.0, min=-20.0, max=50.0)
    detonate = UI.button("Explode")

    def setup(self):
        self.app_state.center = Vec2(0, 0)
        self.app_state.zoom = 14.0

        ground = self.world.new_body().static().build()

        ring_radius = 8.0
        planks = self.world.new_body().dynamic().gravity_scale(0).box(2, 0.2)
        for degrees in range(0, 360, 30):
            angle = math.radians(degrees)
            position = Vec2(
                ring_radius * math.cos(angle), ring_radius * math.sin(angle)
            )
            plank = planks.position(position).build()
            # A soft weld, so the plank springs back after being thrown.
            self.world.add_weld_joint(
                ground,
                plank,
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
        # Show where the blast reaches, and where it fades out.
        steps = 48
        for name, r in (
            ("radius", self.radius),
            ("falloff", self.radius + self.falloff),
        ):
            if r <= 0:
                continue
            colour = Color(255, 160, 0) if name == "radius" else Color(120, 90, 0)
            previous = None
            for i in range(steps + 1):
                angle = 2 * math.pi * i / steps
                point = Vec2(r * math.cos(angle), r * math.sin(angle))
                if previous is not None:
                    debug_draw.draw_segment(previous, point, colour)
                previous = point
        debug_draw.draw_string((-12, 12), f"explosions: {self.blasts}")


class Wind(BaseTest, category="Shapes", name="Wind"):
    """A hanging chain blown about by a gusting wind.

    Wind is applied per shape rather than per body, because how much a shape
    catches depends on how much of it the wind can see. The gust is the steady
    direction plus a slowly wandering noise, so the chain flutters instead of
    simply leaning.
    """

    wind_x = UI.float(10.0, min=-20.0, max=20.0)
    wind_y = UI.float(0.0, min=-20.0, max=20.0)
    drag = UI.float(0.5, min=0.0, max=1.0)
    lift = UI.float(0.5, min=0.0, max=4.0)
    links = UI.int(12, min=1, max=30)

    def setup(self):
        self.app_state.center = Vec2(0, -4)
        self.app_state.zoom = 14.0

        ground = self.world.new_body().static().build()

        radius = 0.5
        previous = ground
        anchor = Vec2(0, 0)
        self.shapes = []
        planks = self.world.new_body().dynamic().box(0.2, 2 * radius, density=1.0)
        for i in range(self.links):
            link = planks.position(0, -radius - 2 * radius * i).build()
            self.world.add_revolute_joint(
                previous,
                link,
                local_anchor_a=(0, 0) if previous is ground else (0, -radius),
                local_anchor_b=(0, radius),
            )
            self.shapes.append(link.shapes[0])
            previous = link

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
            if shape.is_valid():
                shape.apply_wind(self.gust, drag=self.drag, lift=self.lift)

        # Wander the noise slowly so the gust is never quite steady.
        target = Vec2(random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3))
        self.noise = self.noise + (target - self.noise) * 0.05

    @links.callback
    def on_links_change(self, key, value):
        for body in self.world.bodies:
            body.destroy()
        self.setup()

    def debug_draw(self, debug_draw):
        debug_draw.draw_segment((0, 0), self.gust * 0.2, Color(255, 0, 255))
        debug_draw.draw_string((-12, 4), f"wind {self.gust.x:.1f}, {self.gust.y:.1f}")
