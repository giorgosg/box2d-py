# shape.py

from ._box2d import lib, ffi
from abc import ABC, abstractmethod
from .math import Vec2, Transform

class Shape(ABC):
    """Base class for all shapes. Provides common functionality for all shape types."""
    def __init__(self, body, density=None, friction=None, restitution=None, is_sensor=None):
        """Initialize a shape with material properties.
        
        Args:
            body: The Body instance this shape will be attached to
            density: Mass density (kg/m²).
            friction: Friction coefficient.
            restitution: Bounciness (0-1).
            is_sensor: Whether this shape is a sensor.
        """
        self._shape_def = lib.b2DefaultShapeDef()
        self._body = body
        if density is not None:
            self._shape_def.density = density
        if friction is not None:
            self._shape_def.friction = friction
        if restitution is not None:
            self._shape_def.restitution = restitution
        if is_sensor is not None:
            self._shape_def.isSensor = is_sensor

    def _finalize(self):
        """Finalize shape creation and set up user data."""
        del self._shape_def
        self._handle = ffi.new_handle(self)
        lib.b2Shape_SetUserData(self._shape_id, self._handle)

    @property
    def density(self):
        """Get the mass density of the shape."""
        return lib.b2Shape_GetDensity(self._shape_id)
    
    @density.setter
    def density(self, value):
        """Set the mass density of the shape."""
        lib.b2Shape_SetDensity(self._shape_id, float(value), True) # updates the bodies mass
    
    @property
    def friction(self):
        """Get the friction coefficient of the shape."""
        return lib.b2Shape_GetFriction(self._shape_id)
    
    @friction.setter
    def friction(self, value):
        """Set the friction coefficient of the shape."""
        lib.b2Shape_SetFriction(self._shape_id, float(value))
    
    @property
    def restitution(self):
        """Get the restitution (bounciness) of the shape."""
        return lib.b2Shape_GetRestitution(self._shape_id)
    
    @restitution.setter
    def restitution(self, value):
        """Set the restitution (bounciness) of the shape."""
        lib.b2Shape_SetRestitution(self._shape_id, float(value))
    
    @property
    def is_sensor(self):
        """Check if this shape is a sensor."""
        return lib.b2Shape_IsSensor(self._shape_id)

    @property
    def body(self):
        """Get the body this shape is attached to."""
        return self._body

class Circle(Shape):
    """A circle shape that can be attached to a body."""
    def __init__(self, body, radius, center=(0,0), 
                 density=None, friction=None, restitution=None, is_sensor=None):
        """Create a circle shape.
        
        Args:
            body: The Body instance to attach this shape to
            radius: The radius of the circle
            center: The center point of the circle (default: (0,0))
            density: Mass density (kg/m²).
            friction: Friction coefficient.
            restitution: Bounciness (0-1).
            is_sensor: Whether this shape is a sensor.
        """
        super().__init__(body, density, friction, restitution, is_sensor)
        circle_def = ffi.new("b2Circle*")
        circle_def.radius = radius
        circle_def.center.x, circle_def.center.y = center
        self._shape_id = lib.b2CreateCircleShape(body._body_id, 
                                                 ffi.addressof(self._shape_def), 
                                                 circle_def)
        self._finalize()

class Capsule(Shape):
    """A capsule shape that can be attached to a body."""
    def __init__(self, body, point1, point2, radius, 
                 density=None, friction=None, restitution=None, is_sensor=None):
        """Create a capsule shape.
        
        Args:
            body: The Body instance to attach this shape to
            point1: The first endpoint of the capsule
            point2: The second endpoint of the capsule
            radius: The radius of the capsule
            density: Mass density (kg/m²).
            friction: Friction coefficient.
            restitution: Bounciness (0-1).
            is_sensor: Whether this shape is a sensor.
        """

        super().__init__(body, density, friction, restitution, is_sensor)
        capsule_def = ffi.new("b2Capsule*")
        capsule_def.center1.x, capsule_def.center1.y = point1
        capsule_def.center2.x, capsule_def.center2.y = point2
        capsule_def.radius = radius
        self._shape_id = lib.b2CreateCapsuleShape(body._body_id, ffi.addressof(self._shape_def), capsule_def)
        self._finalize()

class Segment(Shape):
    """A line segment shape that can be attached to a body."""
    def __init__(self, body, point1, point2, density=None, friction=None, restitution=None, is_sensor=None):
        """Create a segment shape.
        
        Args:
            body: The Body instance to attach this shape to
            point1: The first endpoint of the segment
            point2: The second endpoint of the segment
            density: Mass density (kg/m²).
            friction: Friction coefficient.
            restitution: Bounciness (0-1).
            is_sensor: Whether this shape is a sensor.
        """

        super().__init__(body, density, friction, restitution, is_sensor)
        segment_def = ffi.new("b2Segment*")
        segment_def.point1.x, segment_def.point1.y = point1
        segment_def.point2.x, segment_def.point2.y = point2
        self._shape_id = lib.b2CreateSegmentShape(body._body_id, ffi.addressof(self._shape_def), segment_def)
        self._finalize()

class Polygon(Shape):
    """A convex polygon shape that can be attached to a body."""
    def __init__(self, body, vertices, radius=0.0, density=None, friction=None, restitution=None, is_sensor=None):
        """Create a polygon shape.
        
        Args:
            body: The Body instance to attach this shape to
            vertices: List of vertices that define the polygon shape
            radius: The radius of the rounded corners (default: 0.0)
            density: Mass density (kg/m²).
            friction: Friction coefficient.
            restitution: Bounciness (0-1).
            is_sensor: Whether this shape is a sensor.
        """

        super().__init__(body, density, friction, restitution, is_sensor)
        
        # Convert vertices to b2Vec2 array
        point_count = len(vertices)
        if point_count < 3 or point_count > 8:
            raise ValueError("Polygon must have 3-8 vertices")

        points = ffi.new("b2Vec2[]", point_count)
        for i, v in enumerate(vertices):
            points[i].x, points[i].y = v

        # Compute convex hull
        hull = lib.b2ComputeHull(points, point_count)
        if hull.count == 0:
            raise ValueError("Failed to compute convex hull from vertices")

        # Create rounded polygon from hull
        polygon_def = lib.b2MakePolygon(ffi.addressof(hull), radius)

        self._handle = ffi.addressof(self._shape_def)
        self._shape_id = lib.b2CreatePolygonShape(body._body_id,
                                                  self._handle,
                                                  ffi.addressof(polygon_def))
        self._finalize()

class Box(Polygon):
    """A rectangular box shape that can be attached to a body, with support for offset positioning and rotation."""
    
    def __init__(self, body, width, height, radius=0.0, offset=(0,0), angle=0.0, 
                 density=None, friction=None, restitution=None, is_sensor=None):
        """Create a box shape with optional offset and rotation.
        
        Args:
            body: Body to attach this shape to
            width: Total width of the box
            height: Total height of the box
            radius: Radius for rounded corners (default: 0)
            offset: Center offset from body position (Vec2/tuple)
            angle: Rotation angle in radians (default: 0)
            density: Mass density
            friction: Friction coefficient
            restitution: Bounciness
            is_sensor: Sensor flag
        """
        hw = width / 2 - radius
        hh = height / 2 - radius
        base_vertices = [
            (-hw, -hh),
            (hw, -hh),
            (hw, hh),
            (-hw, hh)
        ]
        
        transform = Transform(position=offset, rotation=angle)
        transformed_vertices = [transform(v) for v in base_vertices]

        super().__init__(
            body=body,
            vertices=transformed_vertices,
            radius=radius,
            density=density,
            friction=friction,
            restitution=restitution,
            is_sensor=is_sensor
        )

