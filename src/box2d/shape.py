# shape.py

from ._box2d import lib, ffi
from abc import ABC, abstractmethod
from .vec2 import Vec2

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



class Box(Shape):
    """A rectangular box shape that can be attached to a body."""
    def __init__(self, body, width, height, 
                 density=None, friction=None, restitution=None, is_sensor=None):
        """Create a box shape.
        
        Args:
            body: The Body instance to attach this shape to
            width: The width of the box
            height: The height of the box
            density: Mass density (kg/m²).
            friction: Friction coefficient.
            restitution: Bounciness (0-1).
            is_sensor: Whether this shape is a sensor.
        """
        super().__init__(body, density, friction, restitution, is_sensor)
        box_def = ffi.addressof(lib.b2MakeBox(width, height))
        self._shape_id = lib.b2CreatePolygonShape(body._body_id, ffi.addressof(self._shape_def), box_def)
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
    def __init__(self, body, vertices, density=None, friction=None, restitution=None, is_sensor=None):
        """Create a polygon shape.
        
        Args:
            body: The Body instance to attach this shape to
            vertices: List of vertices that define the polygon shape
            density: Mass density (kg/m²).
            friction: Friction coefficient.
            restitution: Bounciness (0-1).
            is_sensor: Whether this shape is a sensor.
        """

        super().__init__(body, density, friction, restitution, is_sensor)
        polygon_def = ffi.new("b2Polygon*")
        
        # Validate and convert vertices
        if len(vertices) < 3 or len(vertices) > 8:
            raise ValueError("Polygon must have 3-8 vertices")
            
        polygon_def.vertices = vertices
        polygon_def.count = len(vertices)
        
        self._shape_id = lib.b2CreatePolygonShape(body._body_id, ffi.addressof(self._shape_def), polygon_def)
        self._finalize()

