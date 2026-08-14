"""
This module defines the ShapeDef class for configuring shapes in Box2D.
A shape definition is used to create shapes with specific properties.
"""

from dataclasses import dataclass, field
from typing import Optional, Any, Iterable, Sequence
from ._box2d import lib, ffi
from .material import SurfaceMaterial
from .collision_filter import CollisionFilter
from .math import Vec2, to_vec2, VectorLike, AABB, Rot
from .debug_draw import Color

_default_shape_def = lib.b2DefaultShapeDef()


@dataclass
class ShapeDef:
    """
    A shape definition is used to create shapes with specific properties.

    Shape definitions are temporary objects that bundle creation parameters
    for shapes. You can safely reuse shape definitions to create multiple shapes.
    Shapes are added to bodies after the body is created.

    Attributes:
        user_data: Application specific shape data. This is set to the shape object created.
        friction: The Coulomb (dry) friction coefficient, usually in the range [0,1]. default=0.6
        restitution: The coefficient of restitution (bounce), usually in the range [0,1]. default=0.0
        rolling_resistance: The rolling resistance coefficient, usually in the range [0,1]. default=0.0
        tangent_speed: The tangent speed for conveyor belt effects. default=0.0
        material: Material identifier or SurfaceMaterial object. default=0
        density: The density in kg/m^2. default=1.0
        filter: Collision filtering data as a CollisionFilter object
        custom_color: Custom debug draw color (optional hex color value)
        is_sensor: True if this shape is a sensor (generates events but no collision response). default=False
        enable_sensor_events: True if sensors may detect this shape. Box2D 3.1 made this
            opt-in and defaults it to False; box2d-py keeps it True so that sensors
            behave as they did before the 3.1 upgrade. default=True
        enable_contact_events: True to enable contact events for this shape. default=False
        enable_hit_events: True to enable hit events for this shape. default=False
        enable_pre_solve_events: True to enable pre-solve events (expensive). default=False
        invoke_contact_creation: True to force contact creation even for static bodies. default=False
        update_body_mass: True if the body should update mass properties when this shape is created. default=True
    """

    user_data: Optional[Any] = None
    friction: float = _default_shape_def.material.friction
    restitution: float = _default_shape_def.material.restitution
    rolling_resistance: float = _default_shape_def.material.rollingResistance
    tangent_speed: float = _default_shape_def.material.tangentSpeed
    material: SurfaceMaterial | int = _default_shape_def.material.userMaterialId
    density: float = _default_shape_def.density
    filter: Optional[CollisionFilter] = None
    custom_color: int = _default_shape_def.material.customColor
    is_sensor: bool = _default_shape_def.isSensor
    enable_sensor_events: bool = True
    enable_contact_events: bool = _default_shape_def.enableContactEvents
    enable_hit_events: bool = _default_shape_def.enableHitEvents
    enable_pre_solve_events: bool = _default_shape_def.enablePreSolveEvents
    invoke_contact_creation: bool = _default_shape_def.invokeContactCreation
    update_body_mass: bool = _default_shape_def.updateBodyMass

    @property
    def b2ShapeDef(self):
        """
        Creates and returns the C structure for this shape definition.

        Uses b2DefaultShapeDef() to get default values and only
        overrides properties that have been explicitly set.

        Returns:
            A b2ShapeDef C structure representing this shape definition
        """
        # Start with defaults
        shape_def = lib.b2DefaultShapeDef()

        # Override with any explicitly set values
        if self.user_data is not None:
            shape_def.userData = self.user_data

        shape_def.material.friction = self.friction
        shape_def.material.restitution = self.restitution
        shape_def.material.rollingResistance = self.rolling_resistance
        shape_def.material.tangentSpeed = self.tangent_speed

        # Handle material - either an int or SurfaceMaterial object
        if self.material is not None:
            if isinstance(self.material, SurfaceMaterial):
                shape_def.material.userMaterialId = self.material.material
                # Apply any material properties if the corresponding ShapeDef property is None
                if self.friction is None and self.material.friction is not None:
                    shape_def.material.friction = self.material.friction
                if self.restitution is None and self.material.restitution is not None:
                    shape_def.material.restitution = self.material.restitution
                if (
                    self.rolling_resistance is None
                    and self.material.rolling_resistance is not None
                ):
                    shape_def.material.rollingResistance = (
                        self.material.rolling_resistance
                    )
                if (
                    self.tangent_speed is None
                    and self.material.tangent_speed is not None
                ):
                    shape_def.material.tangentSpeed = self.material.tangent_speed
                if self.custom_color is None and self.material.custom_color is not None:
                    if isinstance(self.material.custom_color, int):
                        shape_def.material.customColor = self.material.custom_color
            else:
                shape_def.material.userMaterialId = self.material

        shape_def.density = self.density

        # Handle CollisionFilter
        if self.filter is not None:
            filter = self.filter.b2Filter[0]
            shape_def.filter.categoryBits = filter.categoryBits
            shape_def.filter.maskBits = filter.maskBits
            shape_def.filter.groupIndex = filter.groupIndex

        shape_def.material.customColor = self.custom_color
        shape_def.isSensor = self.is_sensor
        shape_def.enableSensorEvents = self.enable_sensor_events
        shape_def.enableContactEvents = self.enable_contact_events
        shape_def.enableHitEvents = self.enable_hit_events
        shape_def.enablePreSolveEvents = self.enable_pre_solve_events
        shape_def.invokeContactCreation = self.invoke_contact_creation
        shape_def.updateBodyMass = self.update_body_mass

        return shape_def


@dataclass
class CircleDef:
    """
    Definition for a circle shape.

    A circle is defined by its position relative to the body origin and its radius.

    Attributes:
        center: Position of the circle's center relative to the body origin
        radius: The radius of the circle
    """

    radius: float
    center: VectorLike = Vec2(0, 0)

    def __post_init__(self):
        """Convert center to Vec2 if it wasn't already"""
        self.center = to_vec2(self.center)
        super().__post_init__() if hasattr(super(), "__post_init__") else None

    @property
    def b2Circle(self):
        """
        Creates and returns the C structure for this circle.

        Returns:
            A b2Circle C structure representing this circle
        """
        circle = ffi.new("b2Circle*")
        circle.center = self.center.b2Vec2[0]
        circle.radius = self.radius
        return circle

    @classmethod
    def from_b2Circle(cls, circle):
        """
        Creates a CircleDef from a b2Circle C structure.

        Args:
            circle: A b2Circle C structure

        Returns:
            A CircleDef instance with properties from the b2Circle
        """
        return cls(radius=circle.radius, center=Vec2.from_b2Vec2(circle.center))


@dataclass
class CapsuleDef:
    """
    Definition for a capsule shape.

    A capsule is a line segment with half-circles at each end. It is defined by
    two points (the centers of the half-circles) and a radius.

    Attributes:
        vertex1: The first endpoint of the capsule's axis
        vertex2: The second endpoint of the capsule's axis
        radius: The radius of the capsule's half-circles
    """

    vertex1: VectorLike
    vertex2: VectorLike
    radius: float

    def __post_init__(self):
        """Convert vertices to Vec2 if they weren't already"""
        self.vertex1 = to_vec2(self.vertex1)
        self.vertex2 = to_vec2(self.vertex2)
        super().__post_init__() if hasattr(super(), "__post_init__") else None

    @property
    def b2Capsule(self):
        """
        Creates and returns the C structure for this capsule.

        Returns:
            A b2Capsule C structure representing this capsule
        """
        capsule = ffi.new("b2Capsule*")
        capsule.center1 = self.vertex1.b2Vec2[0]
        capsule.center2 = self.vertex2.b2Vec2[0]
        capsule.radius = self.radius
        return capsule

    @classmethod
    def from_b2Capsule(cls, capsule):
        """
        Creates a CapsuleDef from a b2Capsule C structure.

        Args:
            capsule: A b2Capsule C structure

        Returns:
            A CapsuleDef instance with properties from the b2Capsule
        """
        return cls(
            vertex1=Vec2.from_b2Vec2(capsule.center1),
            vertex2=Vec2.from_b2Vec2(capsule.center2),
            radius=capsule.radius,
        )


@dataclass
class SegmentDef:
    """
    Definition for a segment (line) shape.

    A segment is a line segment defined by two points. Unlike a capsule,
    a segment has no thickness.

    Attributes:
        vertex1: The first endpoint of the segment
        vertex2: The second endpoint of the segment
    """

    vertex1: VectorLike
    vertex2: VectorLike

    def __post_init__(self):
        """Convert vertices to Vec2 if they weren't already"""
        self.vertex1 = to_vec2(self.vertex1)
        self.vertex2 = to_vec2(self.vertex2)
        super().__post_init__() if hasattr(super(), "__post_init__") else None

    @property
    def b2Segment(self):
        """
        Creates and returns the C structure for this segment.

        Returns:
            A b2Segment C structure representing this segment
        """
        segment = ffi.new("b2Segment*")
        segment.point1 = self.vertex1.b2Vec2[0]
        segment.point2 = self.vertex2.b2Vec2[0]
        return segment

    @classmethod
    def from_b2Segment(cls, segment):
        """
        Creates a SegmentDef from a b2Segment C structure.

        Args:
            segment: A b2Segment C structure

        Returns:
            A SegmentDef instance with properties from the b2Segment
        """
        return cls(
            vertex1=Vec2.from_b2Vec2(segment.point1),
            vertex2=Vec2.from_b2Vec2(segment.point2),
        )


def _compute_hull(vertices: Sequence[VectorLike]):
    """
    Compute the convex hull of a set of points. Returns an empty hull if it fails.
    Some failure cases:
        - all points very close together
        - all points on a line
        - less than 3 points
        - more than B2_MAX_POLYGON_VERTICES points
        This welds close points and removes collinear points.
    """
    count = len(vertices)
    if count < 3 or count > 8:
        raise ValueError("Polygon must have at least 3 vertices and at most 8 vertices")
    b2_points = ffi.new("b2Vec2[]", count)
    for i, vertex in enumerate(vertices):
        b2_points[i].x, b2_points[i].y = to_vec2(vertex)
    hull = lib.b2ComputeHull(b2_points, count)
    return hull


@dataclass
class PolygonDef:
    """
    Definition for a polygon shape.

    A polygon is a convex polygon defined by a list of vertices.
    The vertices must define a convex polygon in counter-clockwise order.

    Attributes:
        vertices: List of points defining the polygon vertices
        radius: Rounding radius for the polygon corners (optional)
        offset: Local position of the polygon relative to the body origin (optional)
        rotation: Local rotation of the polygon relative to the body (optional)
    """

    vertices: Iterable[VectorLike]
    radius: Optional[float] = None
    offset: Optional[VectorLike] = None
    rotation: Optional[float | Rot] = None

    def __post_init__(self):
        """Convert all vertices to Vec2 objects"""
        self.vertices = [to_vec2(v) for v in self.vertices]
        super().__post_init__() if hasattr(super(), "__post_init__") else None

    @property
    def b2Polygon(self):
        """
        Creates and returns the C structure for this polygon.

        Returns:
            A b2Polygon C structure representing this polygon
        """
        count = len(self.vertices)
        if count < 3:
            raise ValueError("Polygon must have at least 3 vertices")

        if count > 8:  # B2_MAX_POLYGON_VERTICES
            raise ValueError(f"Polygon has too many vertices: {count}, maximum is 8")

        hull = _compute_hull(self.vertices)
        if hull.count == 0:
            raise ValueError("Failed to compute convex hull of polygon vertices")

        radius = self.radius if self.radius is not None else 0.0
        offset = to_vec2(self.offset) if self.offset is not None else Vec2(0, 0)
        rotation = self.rotation if self.rotation is not None else Rot(0.0)
        if not isinstance(rotation, Rot):
            rotation = Rot(rotation)
        polygon = lib.b2MakeOffsetRoundedPolygon(
            ffi.addressof(hull), offset.b2Vec2[0], rotation.b2Rot[0], radius
        )
        return polygon

    @classmethod
    def from_b2Polygon(cls, polygon):
        """
        Creates a PolygonDef from a b2Polygon C structure.

        Args:
            polygon: A b2Polygon C structure

        Returns:
            A PolygonDef instance with properties from the b2Polygon
        """
        vertices = []
        for i in range(polygon.count):
            vertices.append(Vec2.from_b2Vec2(polygon.vertices[i]))

        return cls(vertices=vertices, radius=polygon.radius)


@dataclass
class ChainDef:
    """
    Definition for a chain shape.

    A chain shape is defined by a sequence of points that form line segments.
    Chain shapes are designed to eliminate "ghost" collisions with some limitations:
    - chains are one-sided
    - chains have a counter-clockwise winding order
    - chains can be either a loop or open
    - a chain must have at least 4 points
    - chains should not self-intersect

    Attributes:
        vertices: A sequence of points defining the chain's vertices
        is_loop: True if the chain is closed by connecting the first and last points
        materials: Optional list of SurfaceMaterial objects for each segment
        filter: Collision filtering data as a CollisionFilter object
        user_data: Application specific data
        enable_sensor_events: True if sensors may detect this chain. See ShapeDef
            for why this defaults to True rather than Box2D's False. default=True
    """

    vertices: Sequence[VectorLike]
    is_loop: bool = False
    materials: Sequence[SurfaceMaterial] = None
    filter: Optional[CollisionFilter] = None
    user_data: Optional[Any] = None
    enable_sensor_events: bool = True

    def __post_init__(self):
        """Convert all vertices to Vec2 objects"""
        # Convert vertices to Vec2
        self.vertices = [to_vec2(v) for v in self.vertices]

        # Validate vertices
        count = len(self.vertices)
        if count < 4:
            raise ValueError("Chain must have at least 4 vertices")

        # Validate materials if provided
        if self.materials is not None and len(self.materials) > 1:
            if len(self.materials) != (count if not self.is_loop else count + 1):
                raise ValueError(
                    "Number of materials must match the number of segments"
                )

        super().__post_init__() if hasattr(super(), "__post_init__") else None

    @property
    def b2ChainDef(self):
        """
        Creates and returns the C structure for this chain definition.

        Returns:
            A b2ChainDef C structure representing this chain definition
        """
        # Get the count of vertices
        count = len(self.vertices)

        # Create a new chain definition
        chain_def = lib.b2DefaultChainDef()

        # Set user data if provided
        if self.user_data is not None:
            chain_def.userData = self.user_data

        # Create an array for the vertices
        b2_vertices = ffi.new("b2Vec2[]", count)
        for i, vertex in enumerate(self.vertices):
            b2_vertices[i] = vertex.b2Vec2[0]
        self.b2_vertices = b2_vertices

        chain_def.points = b2_vertices
        chain_def.count = count
        chain_def.isLoop = self.is_loop
        chain_def.enableSensorEvents = self.enable_sensor_events

        # Handle materials
        if self.materials is not None:
            material_count = len(self.materials)
            materials = ffi.new("b2SurfaceMaterial[]", material_count)
            self.b2_materials = materials

            for i, mat in enumerate(self.materials):
                materials[i].friction = (
                    mat.friction
                    if mat.friction is not None
                    else lib.b2DefaultSurfaceMaterial().friction
                )
                materials[i].restitution = (
                    mat.restitution
                    if mat.restitution is not None
                    else lib.b2DefaultSurfaceMaterial().restitution
                )
                materials[i].rollingResistance = (
                    mat.rolling_resistance
                    if mat.rolling_resistance is not None
                    else lib.b2DefaultSurfaceMaterial().rollingResistance
                )
                materials[i].tangentSpeed = (
                    mat.tangent_speed
                    if mat.tangent_speed is not None
                    else lib.b2DefaultSurfaceMaterial().tangentSpeed
                )
                materials[i].userMaterialId = mat.material

                if mat.custom_color is not None:
                    if isinstance(mat.custom_color, int):
                        materials[i].customColor = mat.custom_color
                    elif isinstance(mat.custom_color, Color):
                        materials[i].customColor = mat.custom_color.b2HexColor
            chain_def.materials = materials
            chain_def.materialCount = material_count

        # Handle filter
        if self.filter is not None:
            chain_def.filter = self.filter.b2Filter[0]
        else:
            chain_def.filter = lib.b2DefaultFilter()

        # Set internal value to mark as valid
        chain_def.internalValue = 1

        return chain_def
