"""
This module defines shape definition classes. These classes wrap the Box2D C
structure definitions for shapes so that they can be created, configured, and
later passed to the appropriate b2Create* functions when attaching them to
a body or used for other purposes.

Each class provides an __init__ method and a public variable (e.g. `shapedef`,
or geometry-specific attributes such as `circle`, `polygon`, etc.) which holds
the underlying C structure.
"""

from ._box2d import lib, ffi
from .math import Transform
from .collision_filter import CollisionFilter
import math


class ShapeDef:
    """
    Base shape definition.

    Wraps the common shape definition (b2ShapeDef) which contains properties like
    density, friction, restitution, sensor flag, and now collision filtering.
    collision_filter (CollisionFilter): Optional CollisionFilter instance.
    When provided, its C representation is copied to the underlying b2ShapeDef.filter.
    """

    def __init__(
        self,
        density=None,
        friction=None,
        restitution=None,
        is_sensor=None,
        collision_filter=None,
        custom_color=None,
    ):
        """
        Initialize a new ShapeDef.

        Parameters:
            density: The density of the shape.
            friction: The friction of the shape.
            restitution: The restitution (bounciness) of the shape.
            is_sensor: Flag to indicate if the shape is a sensor.
            collision_filter: An optional CollisionFilter instance.
            custom_color: Optional custom debug draw color (uint32_t).

        Example:
            >>> shape = ShapeDef(
            ...     density=1.0,
            ...     friction=0.5,
            ...     restitution=0.3,
            ...     is_sensor=False,
            ...     collision_filter=CollisionFilter(category="player", mask="enemy", group=0),
            ...     custom_color=0xFF00FF
            ... )
        """
        self.shapedef = lib.b2DefaultShapeDef()
        if density is not None:
            self.shapedef.density = density
        if friction is not None:
            self.shapedef.friction = friction
        if restitution is not None:
            self.shapedef.restitution = restitution
        if is_sensor is not None:
            self.shapedef.isSensor = is_sensor
        if collision_filter is not None:
            c_filter = collision_filter.b2Filter
            # Copy the filter bits into the b2ShapeDef.filter field.
            self.shapedef.filter.categoryBits = c_filter.categoryBits
            self.shapedef.filter.maskBits = c_filter.maskBits
            self.shapedef.filter.groupIndex = c_filter.groupIndex
        if custom_color is not None:
            self.shapedef.customColor = custom_color


class CircleDef(ShapeDef):
    """
    Circle shape definition.

    Creates a circle geometry (b2Circle) with a given radius and center position.
    """

    def __init__(
        self,
        radius,
        center=(0, 0),
        density=None,
        friction=None,
        restitution=None,
        is_sensor=None,
        collision_filter=None,
        custom_color=None,
    ):
        """
        Initialize a new CircleDef.

        Parameters:
            radius: The radius of the circle.
            center: A tuple representing the center coordinates.
            density: The density of the circle.
            friction: The friction of the circle.
            restitution: The restitution of the circle.
            is_sensor: Flag to indicate if the circle is a sensor.
            collision_filter: An optional CollisionFilter instance.
            custom_color: Optional custom debug draw color (uint32_t).

        Example:
            >>> circle = CircleDef(
            ...     radius=5.0,
            ...     center=(0, 0),
            ...     density=1.0,
            ...     friction=0.5,
            ...     restitution=0.3,
            ...     is_sensor=False,
            ...     collision_filter=CollisionFilter(category="player", mask="enemy", group=0),
            ...     custom_color=0xFF00FF
            ... )
        """
        super().__init__(
            density, friction, restitution, is_sensor, collision_filter, custom_color
        )
        self.circle = ffi.new("b2Circle*")
        self.circle.radius = radius
        self.circle.center.x, self.circle.center.y = center
        # The common shapedef is available via self.shapedef


class CapsuleDef(ShapeDef):
    """
    Capsule shape definition.

    Sets up a capsule geometry (b2Capsule) given two endpoints and a radius.
    """

    def __init__(
        self,
        point1,
        point2,
        radius,
        density=None,
        friction=None,
        restitution=None,
        is_sensor=None,
        collision_filter=None,
        custom_color=None,
    ):
        """
        Initialize a new CapsuleDef.

        Parameters:
            point1: The first endpoint as a tuple.
            point2: The second endpoint as a tuple.
            radius: The radius of the capsule.
            density: The density of the capsule.
            friction: The friction of the capsule.
            restitution: The restitution of the capsule.
            is_sensor: Flag to indicate if the capsule is a sensor.
            collision_filter: An optional CollisionFilter instance.
            custom_color: Optional custom debug draw color (uint32_t).

        Example:
            >>> capsule = CapsuleDef(
            ...     point1=(0, 0),
            ...     point2=(1, 1),
            ...     radius=2.0,
            ...     density=1.0,
            ...     friction=0.5,
            ...     restitution=0.3,
            ...     is_sensor=True,
            ...     collision_filter=CollisionFilter(category="enemy", mask="player", group=0)
            ... )
        """
        super().__init__(
            density, friction, restitution, is_sensor, collision_filter, custom_color
        )
        self.capsule = ffi.new("b2Capsule*")
        self.capsule.center1.x, self.capsule.center1.y = point1
        self.capsule.center2.x, self.capsule.center2.y = point2
        self.capsule.radius = radius


class SegmentDef(ShapeDef):
    """
    Segment (line) shape definition.

    Creates a segment geometry (b2Segment) defined by two endpoints.
    """

    def __init__(
        self,
        point1,
        point2,
        density=None,
        friction=None,
        restitution=None,
        is_sensor=None,
        collision_filter=None,
        custom_color=None,
    ):
        """
        Initialize a new SegmentDef.

        Parameters:
            point1: The first endpoint as a tuple.
            point2: The second endpoint as a tuple.
            density: The density of the segment.
            friction: The friction of the segment.
            restitution: The restitution of the segment.
            is_sensor: Flag to indicate if the segment is a sensor.
            collision_filter: An optional CollisionFilter instance.
            custom_color: Optional custom debug draw color (uint32_t).

        Example:
            >>> segment = SegmentDef(
            ...     point1=(0, 0),
            ...     point2=(1, 1),
            ...     density=1.0,
            ...     friction=0.5,
            ...     restitution=0.3,
            ...     is_sensor=False,
            ...     collision_filter=CollisionFilter(category="player", mask="enemy", group=0)
            ... )
        """
        super().__init__(
            density, friction, restitution, is_sensor, collision_filter, custom_color
        )
        self.segment = ffi.new("b2Segment*")
        self.segment.point1.x, self.segment.point1.y = point1
        self.segment.point2.x, self.segment.point2.y = point2


class PolygonDef(ShapeDef):
    """
    Convex polygon shape definition.

    Accepts a list of vertices and an optional radius for rounded corners.
    It computes the convex hull and then creates the polygon geometry using
    b2MakePolygon.
    """

    def __init__(
        self,
        vertices,
        radius=0.0,
        density=None,
        friction=None,
        restitution=None,
        is_sensor=None,
        collision_filter=None,
        custom_color=None,
    ):
        """
        Initialize a new PolygonDef.

        Parameters:
            vertices: A list of vertices (tuples) for the polygon.
            radius: Optional radius for rounded corners.
            density: The density of the polygon.
            friction: The friction of the polygon.
            restitution: The restitution of the polygon.
            is_sensor: Flag to indicate if the polygon is a sensor.
            collision_filter: An optional CollisionFilter instance.
            custom_color: Optional custom debug draw color (uint32_t).

        Example:
            >>> polygon = PolygonDef(
            ...     vertices=[(0, 0), (1, 0), (0, 1)],
            ...     radius=0.1,
            ...     density=1.0,
            ...     friction=0.3,
            ...     restitution=0.2,
            ...     is_sensor=False,
            ...     collision_filter=CollisionFilter(category="ally", mask="enemy", group=0)
            ... )
        """
        super().__init__(
            density, friction, restitution, is_sensor, collision_filter, custom_color
        )
        point_count = len(vertices)
        if point_count < 3 or point_count > 8:
            raise ValueError("Polygon must have 3-8 vertices")
        # Create an array of vertices as b2Vec2's
        points = ffi.new("b2Vec2[]", point_count)
        for i, v in enumerate(vertices):
            points[i].x, points[i].y = v
        hull = lib.b2ComputeHull(points, point_count)
        if hull.count == 0:
            raise ValueError("Failed to compute convex hull from vertices")
        polygon_geom = lib.b2MakePolygon(ffi.addressof(hull), radius)
        self.polygon = polygon_geom


class ChainDef:
    """
    Chain shape definition.

    Unlike the typical shapes, a chain shape is defined by a list of vertices
    (at least four) and a loop flag. Note: Chain shapes generally have no density
    and cannot be sensors.

    The resulting C structure is that of a chain definition (b2ChainDef) and is
    stored in the `shapedef` attribute.
    """

    def __init__(
        self,
        vertices,
        loop=False,
        friction=None,
        restitution=None,
        collision_filter=None,
        custom_color=None,
    ):
        """
        Initialize a new ChainDef.

        Parameters:
            vertices: A list of vertices (tuples) for the chain; at least four are required.
            loop: Boolean indicating if the chain forms a loop.
            friction: The friction of the chain.
            restitution: The restitution of the chain.
            collision_filter: An optional CollisionFilter instance.
            custom_color: Optional custom debug draw color (uint32_t).

        Example:
            >>> chain = ChainDef(
            ...     vertices=[(0, 0), (1, 0), (1, 1), (0, 1)],
            ...     loop=True,
            ...     friction=0.2,
            ...     restitution=0.4,
            ...     collision_filter=CollisionFilter(category="chain", mask="enemy", group=0),
            ...     custom_color=0xFF00FF,
            ... )
        """
        if len(vertices) < 4:
            raise ValueError(
                f"Chain shape requires at least 4 vertices; received {len(vertices)}."
            )
        point_count = len(vertices)
        points = ffi.new("b2Vec2[]", point_count)
        self._points = points
        for i, v in enumerate(vertices):
            points[i].x, points[i].y = v
        chain_def = lib.b2DefaultChainDef()
        chain_def.points = points
        chain_def.count = point_count
        chain_def.isLoop = loop
        if friction is not None:
            chain_def.friction = friction
        if restitution is not None:
            chain_def.restitution = restitution
        if collision_filter is not None:
            c_filter = collision_filter.b2Filter
            chain_def.filter.categoryBits = c_filter.categoryBits
            chain_def.filter.maskBits = c_filter.maskBits
            chain_def.filter.groupIndex = c_filter.groupIndex
        if custom_color is not None:
            chain_def.customColor = custom_color
        self.shapedef = chain_def


class BoxDef(PolygonDef):
    """
    Box shape definition.

    Defines a box shape given a full width and height along with an offset,
    a corner radius for rounded corners, and a rotation angle.

    This class uses the Transform class to calculate the rotated and translated
    vertices and then creates a convex polygon shape. It inherits from PolygonDef.
    """

    def __init__(
        self,
        width: float,
        height: float,
        offset: tuple = (0, 0),
        radius: float = 0.0,
        angle: float = 0.0,
        density=None,
        friction=None,
        restitution=None,
        is_sensor=None,
        collision_filter=None,
        custom_color=None,
    ):
        """
        Initialize a new BoxDef.

        Parameters:
            width: The full width of the box.
            height: The full height of the box.
            offset: A tuple representing the offset position.
            radius: The corner radius for rounded corners.
            angle: The rotation angle in radians.
            density: The density of the box.
            friction: The friction of the box.
            restitution: The restitution of the box.
            is_sensor: Flag to indicate if the box is a sensor.
            collision_filter: An optional CollisionFilter instance.
            custom_color: Optional custom debug draw color (uint32_t).

        Example:
            >>> box = BoxDef(
            ...     width=10,
            ...     height=5,
            ...     offset=(2, 3),
            ...     radius=0.5,
            ...     angle=0.785,
            ...     density=1.0,
            ...     friction=0.5,
            ...     restitution=0.3,
            ...     is_sensor=False,
            ...     collision_filter=CollisionFilter(category="box", mask="enemy", group=0)
            ... )
        """
        # Adjust half dimensions to account for the corner radius.
        hw = width / 2.0 - radius
        hh = height / 2.0 - radius
        # Define the four base vertices (centered at the origin).
        base_vertices = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
        # Create a transform that applies both the offset and the rotation.
        transform = Transform(position=offset, rotation=angle)
        # Apply the transform to each vertex.
        transformed_vertices = [transform(v) for v in base_vertices]
        # Call the PolygonDef initializer to compute the convex hull and
        # create the polygon geometry.
        super().__init__(
            vertices=transformed_vertices,
            radius=radius,
            density=density,
            friction=friction,
            restitution=restitution,
            is_sensor=is_sensor,
            collision_filter=collision_filter,
            custom_color=custom_color,
        )
        # Optionally alias the created polygon for clarity.
        self.box = self.polygon


class ChainSegmentDef(ShapeDef):
    """
    Chain segment shape definition.

    Defines a single segment intended for use in chain structures.
    """

    def __init__(
        self,
        start: tuple,
        end: tuple,
        density: float = None,
        friction: float = None,
        restitution: float = None,
        is_sensor: bool = None,
        collision_filter=None,
        custom_color=None,
    ):
        """
        Initialize a new ChainSegmentDef.

        Parameters:
            start: The starting point of the segment as a tuple.
            end: The ending point of the segment as a tuple.
            density: The density of the segment.
            friction: The friction of the segment.
            restitution: The restitution of the segment.
            is_sensor: Flag to indicate if the segment is a sensor.
            collision_filter: An optional CollisionFilter instance.
            custom_color: Optional custom debug draw color (uint32_t).

        Example:
            >>> chain_segment = ChainSegmentDef(
            ...     start=(0, 0),
            ...     end=(2, 2),
            ...     density=1.0,
            ...     friction=0.5,
            ...     restitution=0.3,
            ...     is_sensor=False,
            ...     collision_filter=CollisionFilter(category="chain_seg", mask="enemy", group=0)
            ... )
        """
        super().__init__(
            density, friction, restitution, is_sensor, collision_filter, custom_color
        )
        self.chainsegment = ffi.new("b2ChainSegment*")
        self.chainsegment.segment.point1.x, self.chainsegment.segment.point1.y = start
        self.chainsegment.segment.point2.x, self.chainsegment.segment.point2.y = end
