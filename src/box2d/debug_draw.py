# debug_draw.py
from ._box2d import ffi, lib
from .math import Vec2, Rot, Transform, AABB, Mat22


class Color:
    def __init__(self, r: int, g: int, b: int, a: int = 0xFF):
        self.r, self.g, self.b, self.a = r, g, b, a
        self.hexcolor = None

    @classmethod
    def from_b2HexColor(cls, hex_color: int):
        r = (hex_color >> 16) & 0xFF
        g = (hex_color >> 8) & 0xFF
        b = hex_color & 0xFF
        a = 0xFF  # Alpha not part of b2HexColor, default opaque
        color = cls(r, g, b, a)
        return color

    @property
    def b2HexColor(self) -> int:
        hexcolor = (self.r << 16) | (self.g << 8) | self.b
        return hexcolor

    hex = b2HexColor

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
        new_color = Color(new_r, new_g, new_b, new_a)
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
@ffi.callback("void(b2Transform, b2Vec2*, int, b2HexColor, void*)")
def draw_polygon(transform, vertices: list[Vec2], count, color, context):
    instance = ffi.from_handle(context)
    py_transform = Transform.from_b2Transform(transform)
    py_vertices = [Vec2.from_b2Vec2(vertices[i]) for i in range(count)]
    instance.draw_polygon(py_transform, py_vertices, Color.from_b2HexColor(color))


@ffi.callback("void(b2Transform, b2Vec2*, int, float, b2HexColor, void*)")
def draw_solid_polygon(transform, vertices: list[Vec2], count, radius, color, context):
    instance = ffi.from_handle(context)
    py_transform = Transform.from_b2Transform(transform)
    py_vertices = [Vec2.from_b2Vec2(vertices[i]) for i in range(count)]
    instance.draw_solid_polygon(
        py_transform, py_vertices, radius, Color.from_b2HexColor(color)
    )


@ffi.callback("void(b2Vec2, float, b2HexColor, void*)")
def draw_circle(center: Vec2, radius, color, context):
    instance = ffi.from_handle(context)
    py_center = Vec2.from_b2Vec2(center)
    instance.draw_circle(py_center, radius, Color.from_b2HexColor(color))


@ffi.callback("void(b2Vec2, b2Vec2, b2HexColor, void*)")
def draw_segment(p1, p2, color, context):
    instance = ffi.from_handle(context)
    py_p1 = Vec2.from_b2Vec2(p1)
    py_p2 = Vec2.from_b2Vec2(p2)
    instance.draw_segment(py_p1, py_p2, Color.from_b2HexColor(color))


@ffi.callback("void(b2Vec2, float, b2HexColor, void*)")
def draw_point(p, size, color, context):
    instance = ffi.from_handle(context)
    py_p = Vec2.from_b2Vec2(p)
    instance.draw_point(py_p, size, Color.from_b2HexColor(color))


@ffi.callback("void(b2AABB, b2HexColor, void*)")
def draw_bounds(aabb, color, context):
    instance = ffi.from_handle(context)
    py_aabb = AABB(
        lower=Vec2(aabb.lowerBound.x, aabb.lowerBound.y),
        upper=Vec2(aabb.upperBound.x, aabb.upperBound.y),
    )
    instance.draw_bounds(py_aabb, Color.from_b2HexColor(color))


@ffi.callback("void(b2Vec2, const char*, b2HexColor, void*)")
def draw_string(p, s, color, context):
    instance = ffi.from_handle(context)
    py_p = Vec2.from_b2Vec2(p)
    py_str = ffi.string(s).decode("utf-8")
    instance.draw_string(py_p, py_str, Color.from_b2HexColor(color))


@ffi.callback("void(b2Vec2, b2Vec2, float, b2HexColor, void*)")
def draw_solid_capsule(p1, p2, radius, color, context):
    instance = ffi.from_handle(context)
    py_p1 = Vec2.from_b2Vec2(p1)
    py_p2 = Vec2.from_b2Vec2(p2)
    instance.draw_solid_capsule(py_p1, py_p2, radius, Color.from_b2HexColor(color))


@ffi.callback("void(b2Transform, b2Vec2, float, b2HexColor, void*)")
def draw_solid_circle(transform, center: Vec2, radius, color, context):
    instance = ffi.from_handle(context)
    py_transform = Transform.from_b2Transform(transform)
    py_center = Vec2.from_b2Vec2(center)
    instance.draw_solid_circle(
        py_transform, py_center, radius, Color.from_b2HexColor(color)
    )


@ffi.callback("void(b2Transform, void*)")
def draw_transform(transform, context):
    instance = ffi.from_handle(context)
    py_transform = Transform.from_b2Transform(transform)
    instance.draw_transform(py_transform)


class _DrawFlag:
    """One of Box2D's debug-draw flags, as a property on the owning DebugDraw.

    Args:
        field: The b2DebugDraw struct field this flag lives in.
        doc: What turning it on shows.
    """

    def __init__(self, field, doc):
        self._field = field
        self.__doc__ = doc

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return bool(getattr(instance._debug_draw, self._field))

    def __set__(self, instance, value):
        setattr(instance._debug_draw, self._field, bool(value))


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
        self._debug_draw.DrawPolygonFcn = draw_polygon
        self._debug_draw.DrawSolidPolygonFcn = draw_solid_polygon
        self._debug_draw.DrawCircleFcn = draw_circle
        self._debug_draw.DrawLineFcn = draw_segment
        self._debug_draw.DrawPointFcn = draw_point
        self._debug_draw.DrawStringFcn = draw_string
        self._debug_draw.DrawSolidCapsuleFcn = draw_solid_capsule
        self._debug_draw.DrawSolidCircleFcn = draw_solid_circle
        self._debug_draw.DrawTransformFcn = draw_transform
        self._debug_draw.DrawBoundsFcn = draw_bounds

        # Store a handle to this Python object for context
        self._context_handle = ffi.new_handle(self)
        self._debug_draw.context = self._context_handle

    # Box2D's fifteen debug-draw flags. Each is a plain bool on the C struct,
    # so a descriptor declares them rather than fifteen copies of the same
    # property pair. Python names differ from the C ones where Box2D's own
    # wording changed (drawBounds is the AABB flag; forces were impulses).
    draw_shapes = _DrawFlag("drawShapes", "Shape outlines and fills.")
    draw_aabbs = _DrawFlag("drawBounds", "Each shape's axis-aligned bounding box.")
    draw_joints = _DrawFlag("drawJoints", "Joint connections and anchors.")
    draw_joint_extras = _DrawFlag(
        "drawJointExtras", "Joint limits, motors and reference angles."
    )
    draw_contacts = _DrawFlag("drawContacts", "Contact points between touching shapes.")
    draw_contact_normals = _DrawFlag(
        "drawContactNormals", "The normal at each contact point."
    )
    draw_contact_impulses = _DrawFlag(
        "drawContactForces", "How hard each contact is pushing."
    )
    draw_friction_impulses = _DrawFlag(
        "drawFrictionForces", "The friction impulse at each contact."
    )
    draw_mass = _DrawFlag("drawMass", "Each body's centre of mass and its frame.")
    draw_contact_features = _DrawFlag(
        "drawContactFeatures",
        """The feature ids identifying each contact point.

        A contact point keeps its id between steps while it persists, which is
        what lets the solver carry impulses over. Seeing the ids flicker means
        the contact is being rebuilt rather than reused.
        """,
    )
    draw_islands = _DrawFlag(
        "drawIslands",
        """The bounding box of each simulation island.

        An island is a group of bodies solved together. Two piles that touch
        merge into one island and are solved as a unit, which is why one heavy
        stack can slow down a scene that looks otherwise idle.
        """,
    )
    draw_graph_colors = _DrawFlag(
        "drawGraphColors",
        """Constraints coloured by their solver graph colour.

        Constraints sharing a colour touch no common body, so they are solved
        in parallel. This is the visual form of Counters.color_counts: an even
        spread of colours parallelises, everything in one colour does not.
        """,
    )
    draw_body_names = _DrawFlag(
        "drawBodyNames", "The name given to each body, for picking one out of a crowd."
    )
    draw_chain_normals = _DrawFlag(
        "drawChainNormals",
        """The outward normal of each chain segment.

        A chain collides on one side only, decided by its winding order, and
        this shows which side that is -- the quickest way to find a chain
        things fall straight through.
        """,
    )
    draw_anchor_a = _DrawFlag(
        "drawAnchorA", "Each joint's anchor frame on body A rather than both."
    )

    # Internal callback handlers (override these in subclasses)
    def draw_polygon(self, transform: Transform, vertices: list[Vec2], color: Color):
        """Draw wireframe polygon outlines (AABBs and shape outlines when draw_bounds/shapes enabled).

        Box2D 3.2 added the transform argument; the vertices are in local space.

        Args:
            transform: Position and rotation the vertices are relative to
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

    @property
    def drawing_bounds(self) -> AABB:
        """The region worth drawing, in world coordinates.

        b2World_Draw queries the broad-phase tree with this rather than
        walking every shape, so setting it to the visible region culls
        everything off screen in C, before a single callback fires.

        It defaults to the whole float range, which means no culling at all.
        On a scene of 7000 bodies, narrowing it to a 40x40 view took a draw
        from 57ms to 6.7ms, and a 10x10 view to 0.6ms -- the cost follows
        what is visible instead of what exists.
        """
        aabb = self._debug_draw.drawingBounds
        return AABB(
            lower=Vec2(aabb.lowerBound.x, aabb.lowerBound.y),
            upper=Vec2(aabb.upperBound.x, aabb.upperBound.y),
        )

    @drawing_bounds.setter
    def drawing_bounds(self, aabb: AABB):
        bounds = self._debug_draw.drawingBounds
        bounds.lowerBound.x, bounds.lowerBound.y = aabb.lower.x, aabb.lower.y
        bounds.upperBound.x, bounds.upperBound.y = aabb.upper.x, aabb.upper.y

    def draw_bounds(self, aabb: "AABB", color: Color):
        """Callback for drawing a shape's bounding box, enabled by draw_aabbs.

        Box2D 3.2 gave bounds their own callback rather than routing them
        through draw_polygon. Leaving it unset is silent rather than fatal,
        because b2DefaultDebugDraw installs a stub -- so the AABB toggle did
        nothing at all until this was bound.

        Args:
            aabb: The box, in world coordinates
            color: Line color
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

    def draw_solid_circle(
        self, transform: Transform, center: Vec2, radius: float, color: Color
    ):
        """Draw filled circles with orientation marker (used for circular fixtures when draw_shapes enabled).

        Box2D 3.2 added the center argument, which is relative to the transform.

        Args:
            transform: Position and rotation (rotation affects orientation line)
            center: Circle center relative to the transform
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
