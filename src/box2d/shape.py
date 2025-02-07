# shape.py

from ._box2d import lib, ffi
from abc import ABC, abstractmethod
from .vec2 import Vec2

class Shape(ABC):
    def __init__(self, body, density=None, friction=None, restitution=None, is_sensor=None):
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
        del self._shape_def
        lib.b2Shape_SetUserData(self._shape_id, ffi.new_handle(self))

class Circle(Shape):
    def __init__(self, body, radius, center=(0,0), density=None, friction=None, restitution=None, is_sensor=None):
        super().__init__(body, density, friction, restitution, is_sensor)
        circle_def = ffi.new("b2Circle*")
        circle_def.radius = radius
        circle_def.center.x, circle_def.center.y = center
        self._shape_id = lib.b2CreateCircleShape(body._body_id, ffi.addressof(self._shape_def), circle_def)
        self._finalize()

class Box(Shape):
    def __init__(self, body, width, height, density=None, friction=None, restitution=None, is_sensor=None):
        super().__init__(body, density, friction, restitution, is_sensor)
        box_def = ffi.addressof(lib.b2MakeBox(width, height))
        self._shape_id = lib.b2CreatePolygonShape(body._body_id, ffi.addressof(self._shape_def), box_def)
        self._finalize()

class Capsule(Shape):
    def __init__(self, body, point1, point2, radius, density=None, friction=None, restitution=None, is_sensor=None):
        super().__init__(body, density, friction, restitution, is_sensor)
        capsule_def = ffi.new("b2Capsule*")
        capsule_def.center1.x, capsule_def.center1.y = point1
        capsule_def.center2.x, capsule_def.center2.y = point2
        capsule_def.radius = radius
        self._shape_id = lib.b2CreateCapsuleShape(body._body_id, ffi.addressof(self._shape_def), capsule_def)
        self._finalize()

class Segment(Shape):
    def __init__(self, body, point1, point2, density=None, friction=None, restitution=None, is_sensor=None):
        super().__init__(body, density, friction, restitution, is_sensor)
        segment_def = ffi.new("b2Segment*")
        segment_def.point1.x, segment_def.point1.y = point1
        segment_def.point2.x, segment_def.point2.y = point2
        self._shape_id = lib.b2CreateSegmentShape(body._body_id, ffi.addressof(self._shape_def), segment_def)
        self._finalize()

class Polygon(Shape):
    def __init__(self, body, vertices, density=None, friction=None, restitution=None, is_sensor=None):
        super().__init__(body, density, friction, restitution, is_sensor)
        polygon_def = ffi.new("b2Polygon*")
        
        # Validate and convert vertices
        if len(vertices) < 3 or len(vertices) > 8:
            raise ValueError("Polygon must have 3-8 vertices")
            
        polygon_def.vertices = vertices
        polygon_def.count = len(vertices)
        
        self._shape_id = lib.b2CreatePolygonShape(body._body_id, ffi.addressof(self._shape_def), polygon_def)
        self._finalize()

