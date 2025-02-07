from box2d._box2d import lib as _b2d
from box2d._box2d import ffi

class Shape:
    CIRCLE= _b2d.b2_circleShape
    CAPSULE= _b2d.b2_capsuleShape
    SEGMENT= _b2d.b2_segmentShape

class Box(Shape):
    def __init__(self, body, dimensions, density=None, friction=None):
        shapedef = _b2d.b2DefaultShapeDef()
        if density is not None:
            shapedef.density = density
        if friction is not None:
            shapedef.friction = friction
        box = _b2d.b2MakeBox(*dimensions)
