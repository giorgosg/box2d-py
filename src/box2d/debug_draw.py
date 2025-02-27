# debug_draw.py
from ._box2d import ffi, lib
from .math import Vec2, Rot, Transform, AABB, Mat22


class Color:
    def __init__(self, hex_color: int):
        self._hex = hex_color
        self.r = (hex_color >> 16) & 0xFF
        self.g = (hex_color >> 8) & 0xFF
        self.b = hex_color & 0xFF
        self.a = 255  # Alpha not part of b2HexColor, default opaque

    @property
    def hex(self) -> int:
        return self._hex

    @property
    def as_float(self):
        """Return the RGBA color as a tuple of floats scaled 0 to 1."""
        return (self.r / 255, self.g / 255, self.b / 255, self.a / 255)

    def changed(self, r: int = None, g: int = None, b: int = None, a: int = None):
        """
        Return a new Color instance with the specified components changed.

        Args:
            r: New red component (0-255). If None, retains current value.
            g: New green component (0-255). If None, retains current value.
            b: New blue component (0-255). If None, retains current value.
            a: New alpha component (0-255). If None, retains current value.

        Returns:
            A new instance of Color with updated color components.
        """
        new_r = r if r is not None else self.r
        new_g = g if g is not None else self.g
        new_b = b if b is not None else self.b
        new_a = a if a is not None else self.a
        new_hex = (new_r << 16) | (new_g << 8) | new_b
        new_color = Color(new_hex)
        new_color.a = new_a  # Override alpha if changed
        return new_color

    def __iter__(self):
        return iter((self.r, self.g, self.b, self.a))

    def __repr__(self) -> str:
        return f"Color(r={self.r}, g={self.g}, b={self.b}, a={self.a})"

    def __eq__(self, other):
        """Check equality with another Color instance.

        Two Color objects are considered equal if their red, green, blue,
        and alpha components are all equal.
        """
        if not isinstance(other, Color):
            return NotImplemented
        return (
            self.r == other.r
            and self.g == other.g
            and self.b == other.b
            and self.a == other.a
        )

    def __hash__(self):
        """Return the hash based on the color's RGBA components."""
        return hash((self.r, self.g, self.b, self.a))


# Define callback wrappers with cffi.callback and conversion logic
@ffi.callback("void(b2Vec2*, int, b2HexColor, void*)")
def draw_polygon(vertices, count, color, context):
    instance = ffi.from_handle(context)
    py_vertices = [Vec2.from_b2Vec2(vertices[i]) for i in range(count)]
    instance.draw_polygon(py_vertices, Color(color))


@ffi.callback("void(b2Transform, b2Vec2*, int, float, b2HexColor, void*)")
def draw_solid_polygon(transform, vertices, count, radius, color, context):
    instance = ffi.from_handle(context)
    # py_transform = Transform.from_b2Transform(transform)
    # py_vertices = [Vec2.from_b2Vec2(vertices[i]) for i in range(count)]
    instance.draw_solid_polygon(transform, vertices, count, radius, color)


@ffi.callback("void(b2Vec2, float, b2HexColor, void*)")
def draw_circle(center, radius, color, context):
    instance = ffi.from_handle(context)
    py_center = Vec2.from_b2Vec2(center)
    instance.draw_circle(py_center, radius, Color(color))


@ffi.callback("void(b2Vec2, b2Vec2, b2HexColor, void*)")
def draw_segment(p1, p2, color, context):
    instance = ffi.from_handle(context)
    py_p1 = Vec2.from_b2Vec2(p1)
    py_p2 = Vec2.from_b2Vec2(p2)
    instance.draw_segment(py_p1, py_p2, Color(color))


@ffi.callback("void(b2Vec2, float, b2HexColor, void*)")
def draw_point(p, size, color, context):
    instance = ffi.from_handle(context)
    py_p = Vec2.from_b2Vec2(p)
    instance.draw_point(py_p, size, Color(color))


@ffi.callback("void(b2Vec2, const char*, b2HexColor, void*)")
def draw_string(p, s, color, context):
    instance = ffi.from_handle(context)
    py_p = Vec2.from_b2Vec2(p)
    py_str = ffi.string(s).decode("utf-8")
    instance.draw_string(py_p, py_str, Color(color))


@ffi.callback("void(b2Vec2, b2Vec2, float, b2HexColor, void*)")
def draw_solid_capsule(p1, p2, radius, color, context):
    instance = ffi.from_handle(context)
    py_p1 = Vec2.from_b2Vec2(p1)
    py_p2 = Vec2.from_b2Vec2(p2)
    instance.draw_solid_capsule(py_p1, py_p2, radius, Color(color))


@ffi.callback("void(b2Transform, float, b2HexColor, void*)")
def draw_solid_circle(transform, radius, color, context):
    instance = ffi.from_handle(context)
    instance.draw_solid_circle(transform, radius, color)


@ffi.callback("void(b2Transform, void*)")
def draw_transform(transform, context):
    instance = ffi.from_handle(context)
    py_transform = Transform.from_b2Transform(transform)
    instance.draw_transform(py_transform)


class DebugDraw:
    """Abstract base class for custom debug rendering of Box2D simulations.

    Subclass this and override methods to implement debug visualization of:
    - Shape outlines and solids
    - Joints, AABBs, contact points
    - Physics metrics like mass centers and impulses

    Set boolean flags (draw_shapes, draw_aabbs etc.) to control which elements are rendered.
    Uses Box2D's b2DebugDraw callbacks internally.

    Example:
        class MyDebugDraw(DebugDraw):
            def _draw_polygon(self, vertices, color):
                # Implement polygon drawing with your graphics API

    """

    def __init__(self):
        # Create a C b2DebugDraw instance
        self._debug_draw = lib.b2DefaultDebugDraw()
        # Assign context handle to retrieve instance in callbacks
        self._debug_draw.context = ffi.new_handle(self)

        # Assign decorated callbacks
        self._debug_draw.DrawPolygon = draw_polygon
        self._debug_draw.DrawSolidPolygon = draw_solid_polygon
        self._debug_draw.DrawCircle = draw_circle
        self._debug_draw.DrawSegment = draw_segment
        self._debug_draw.DrawPoint = draw_point
        self._debug_draw.DrawString = draw_string
        self._debug_draw.DrawSolidCapsule = draw_solid_capsule
        self._debug_draw.DrawSolidCircle = draw_solid_circle
        self._debug_draw.DrawTransform = draw_transform

        # Store a handle to this Python object for context
        self._context_handle = ffi.new_handle(self)
        self._debug_draw.context = self._context_handle

    @property
    def draw_shapes(self):
        return bool(self._debug_draw.drawShapes)

    @draw_shapes.setter
    def draw_shapes(self, value: bool):
        self._debug_draw.drawShapes = bool(value)

    @property
    def draw_aabbs(self):
        return bool(self._debug_draw.drawAABBs)

    @draw_aabbs.setter
    def draw_aabbs(self, value: bool):
        self._debug_draw.drawAABBs = bool(value)

    @property
    def draw_joints(self):
        return bool(self._debug_draw.drawJoints)

    @draw_joints.setter
    def draw_joints(self, value: bool):
        self._debug_draw.drawJoints = bool(value)

    @property
    def draw_contacts(self):
        return bool(self._debug_draw.drawContacts)

    @draw_contacts.setter
    def draw_contacts(self, value: bool):
        self._debug_draw.drawContacts = bool(value)

    @property
    def draw_contact_normals(self):
        return bool(self._debug_draw.drawContactNormals)

    @draw_contact_normals.setter
    def draw_contact_normals(self, value: bool):
        self._debug_draw.drawContactNormals = bool(value)

    @property
    def draw_contact_impulses(self):
        return bool(self._debug_draw.drawContactImpulses)

    @draw_contact_impulses.setter
    def draw_contact_impulses(self, value: bool):
        self._debug_draw.drawContactImpulses = bool(value)

    @property
    def draw_friction_impulses(self):
        return bool(self._debug_draw.drawFrictionImpulses)

    @draw_friction_impulses.setter
    def draw_friction_impulses(self, value: bool):
        self._debug_draw.drawFrictionImpulses = bool(value)

    @property
    def draw_mass(self):
        return bool(self._debug_draw.drawMass)

    @draw_mass.setter
    def draw_mass(self, value: bool):
        self._debug_draw.drawMass = bool(value)

    @property
    def draw_joint_extras(self):
        return bool(self._debug_draw.drawJointExtras)

    @draw_joint_extras.setter
    def draw_joint_extras(self, value: bool):
        self._debug_draw.drawJointExtras = bool(value)

    # Internal callback handlers (override these in subclasses)
    def draw_polygon(self, vertices: list[Vec2], color: Color):
        """Draw wireframe polygon outlines (AABBs and shape outlines when draw_aabbs/shapes enabled).


        Args:
            vertices: Polygon vertex coordinates in Counter-Clockwise order
            color: RGB color with alpha
        """
        pass  # Override in subclass

    def draw_solid_polygon(
        self, transform: Transform, vertices: list[Vec2], radius: float, color: Color
    ):
        """Draw filled convex polygons with optional rounded corners (triggered by draw_shapes flag).

        Args:
            transform: Position and rotation of the polygon
            vertices: Polygon vertices in CCW order
            radius: Radius for rounded corners (0 for sharp edges)
            color: Fill color with transparency
        """
        pass

    def draw_circle(self, center: Vec2, radius: float, color: Color):
        """Callback for drawing circle outlines.

        Args:
            center: World position of circle center
            radius: Radius in meters
            color: RGB color of the outline
        """
        pass

    def draw_segment(self, p1: Vec2, p2: Vec2, color: Color):
        """Draw line segments for joints/contact normals (requires draw_joints or draw_contact_normals).

        Args:
            p1: Starting point in world coordinates
            p2: Ending point in world coordinates
            color: Color of the line segment
        """

        pass

    def draw_point(self, p: Vec2, size: float, color: Color):
        """Visualize contact points (draw_contacts) or mass centers (draw_mass).

        Args:
            position: World coordinates of the point
            size: Diameter to render the point (screen pixels or meters)
            color: RGB color of the point

        Note:
            Used for contact points when draw_contacts flag is True
        """
        pass

    def draw_string(self, p: Vec2, s: str, color: Color):
        """Render debug text for impulse values (draw_contact_impulses/draw_friction_impulses).

        Args:
            p: World position where text should be anchored
            s: Text string to display
            color: Color of the text

        Note:
            Coordinate system depends on your renderer's text handling
        """
        pass

    def draw_capsule(self, p1: Vec2, p2: Vec2, radius: float, color: Color):
        """Callback for drawing capsule outlines (line segment with radius).

        Args:
            p1: First endpoint of the capsule's centerline
            p2: Second endpoint of the capsule's centerline
            radius: Radius of the capsule (extends beyond endpoints)
            color: Outline color

        Note:
            Used for character controllers or rounded collision shapes
        """
        pass

    def draw_solid_capsule(self, p1: Vec2, p2: Vec2, radius: float, color: Color):
        """Draw filled capsule shapes (triggered by draw_shapes for capsule fixtures).

        Args:
            p1: First endpoint of the capsule's axis
            p2: Second endpoint of the capsule's axis
            radius: Radial thickness of the capsule
            color: Fill color with transparency

        Note:
            Rendered as two half-circles connected by a rectangle
        """
        pass

    def draw_solid_circle(self, transform: Transform, radius: float, color: Color):
        """Draw filled circles with orientation marker (used for circular fixtures when draw_shapes enabled).

        Args:
            transform: Center position and rotation (rotation affects orientation line)
            radius: Circle radius in world units
            color: Fill color with alpha channel
        """
        pass

    def draw_transform(self, transform: Transform):
        """Visualize coordinate frames for joint anchors (requires draw_joint_extras flag).

        Args:
            transform: Contains position and rotation matrix
            color: Base color for the axes (often overridden)
        """
        pass
