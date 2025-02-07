# shape.py

from ._box2d import lib, ffi
from abc import ABC, abstractmethod
from .vec2 import Vec2

class Shape(ABC):
    def __init__(self, body, density=None, friction=None):
        self._shape_def = lib.b2DefaultShapeDef()
        self._body = body
        if density is not None:
            self._shape_def.density = density
        if friction is not None:
            self._shape_def.friction = friction

    def _finalize(self):
        del self._shape_def
        lib.b2Shape_SetUserData(self._shape_id, ffi.new_handle(self))

class Circle(Shape):
    def __init__(self, body, radius, center=(0,0), density=None, friction=None):
        super().__init__(body, density, friction)
        circle_def = ffi.new("b2Circle*")
        circle_def.radius = radius
        circle_def.center.x, circle_def.center.y = center
        self._shape_id = lib.b2CreateCircleShape(body._body_id, ffi.addressof(self._shape_def), circle_def)
        self._finalize()

class Box(Shape):
    def __init__(self, body, width, height, density=None, friction=None):
        super().__init__(body, density, friction)
        box_def = ffi.addressof(lib.b2MakeBox(width, height))
        self._shape_id = lib.b2CreatePolygonShape(body._body_id, ffi.addressof(self._shape_def), box_def)
        self._finalize()

