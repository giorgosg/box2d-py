"""
This module defines high-level shape objects for Box2D.
Each shape’s constructor now accepts a body and a shape definition.
Each shape (except Chain) subclasses a common base that implements common properties.
Each shape also has a classmethod “create” that matches the signature from before.
Chain is now implemented as a separate class.
"""

from ._box2d import lib, ffi
from abc import ABC
from .math import Vec2, Transform, VectorLike
from .shape_def import (
    CircleDef,
    CapsuleDef,
    SegmentDef,
    PolygonDef,
    BoxDef,
    ChainDef,
)


class Shape(ABC):
    """
    Base class for all non-chain shapes.
    Its constructor now accepts only a body and a shape definition.
    It provides common properties like density, friction, restitution, and a helper _finalize.
    """

    def __init__(self, body, shapedef):
        self._body = body

    def _finalize(self):
        """
        Finalize shape creation by setting the user data pointer.
        """
        self._handle = ffi.new_handle(self)
        lib.b2Shape_SetUserData(self._shape_id, self._handle)

    @property
    def density(self):
        """Get the mass density of the shape."""
        return lib.b2Shape_GetDensity(self._shape_id)

    @density.setter
    def density(self, value):
        """Set the mass density of the shape (and update the body mass)."""
        lib.b2Shape_SetDensity(self._shape_id, float(value), True)

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
        """Return the body to which this shape is attached."""
        return self._body


class Circle(Shape):
    """
    A circle shape that can be attached to a body.
    """

    def __init__(self, body, shapedef):
        """
        Initialize a Circle shape from a body and a CircleDef instance.
        """
        super().__init__(body, shapedef)
        self._shape_id = lib.b2CreateCircleShape(
            body._body_id, ffi.addressof(shapedef.shapedef), shapedef.circle
        )
        self._finalize()

    @classmethod
    def create(
        cls,
        body,
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
        Create and attach a circle shape to a body.
        The parameters are the same as the previous initializer.
        """
        shapedef = CircleDef(
            radius,
            center,
            density,
            friction,
            restitution,
            is_sensor,
            collision_filter,
            custom_color,
        )
        return cls(body, shapedef)


class Capsule(Shape):
    """
    A capsule shape that can be attached to a body.
    """

    def __init__(self, body, shapedef):
        """
        Initialize a Capsule shape from a body and a CapsuleDef instance.
        """
        super().__init__(body, shapedef)
        self._shape_id = lib.b2CreateCapsuleShape(
            body._body_id, ffi.addressof(shapedef.shapedef), shapedef.capsule
        )
        self._finalize()

    @classmethod
    def create(
        cls,
        body,
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
        Create and attach a capsule shape to a body.
        The parameters are the same as the previous initializer.
        """
        shapedef = CapsuleDef(
            point1,
            point2,
            radius,
            density,
            friction,
            restitution,
            is_sensor,
            collision_filter,
            custom_color=None,
        )
        return cls(body, shapedef)


class Segment(Shape):
    """
    A line segment shape that can be attached to a body.
    """

    def __init__(self, body, shapedef):
        """
        Initialize a Segment shape from a body and a SegmentDef instance.
        """
        super().__init__(body, shapedef)
        self._shape_id = lib.b2CreateSegmentShape(
            body._body_id, ffi.addressof(shapedef.shapedef), shapedef.segment
        )
        self._finalize()

    @classmethod
    def create(
        cls,
        body,
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
        Create and attach a segment shape to a body.
        The parameters are the same as the previous initializer.
        """
        shapedef = SegmentDef(
            point1,
            point2,
            density,
            friction,
            restitution,
            is_sensor,
            collision_filter,
            custom_color,
        )
        return cls(body, shapedef)


class Polygon(Shape):
    """
    A convex polygon shape that can be attached to a body.
    """

    def __init__(self, body, shapedef):
        """
        Initialize a Polygon shape from a body and a PolygonDef instance.
        """
        super().__init__(body, shapedef)
        # Note: shapedef.polygon is the geometry computed (via b2MakePolygon)
        self._shape_id = lib.b2CreatePolygonShape(
            body._body_id,
            ffi.addressof(shapedef.shapedef),
            ffi.addressof(shapedef.polygon),
        )
        self._finalize()

    @classmethod
    def create(
        cls,
        body,
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
        Create and attach a polygon shape to a body.
        The parameters are the same as the previous initializer.
        """
        shapedef = PolygonDef(
            vertices,
            radius,
            density,
            friction,
            restitution,
            is_sensor,
            collision_filter,
            custom_color,
        )
        return cls(body, shapedef)


class Box(Polygon):
    """
    A box (rectangle) shape that can be attached to a body.
    Inherits from Polygon since a box is a special case of a convex polygon.
    """

    @classmethod
    def create(
        cls,
        body,
        width,
        height,
        radius=0.0,
        offset=(0, 0),
        angle=0.0,
        density=None,
        friction=None,
        restitution=None,
        is_sensor=None,
        collision_filter=None,
        custom_color=None,
    ):
        """
        Create and attach a box shape to a body.
        The parameters are the same as the previous initializer.
        """
        shapedef = BoxDef(
            width,
            height,
            offset,
            radius,
            angle,
            density,
            friction,
            restitution,
            is_sensor,
            collision_filter,
            custom_color,
        )
        return cls(body, shapedef)


class ChainSegment(Shape):
    """
    A segment of a chain shape.
    Chain segments are created automatically by the Chain class and represent
    individual segments within a chain. Each segment has a reference to its parent chain.
    """

    def __init__(self, b2chainsegment, chain: "Chain"):
        """
        Initialize a chain segment with its parent chain and endpoints.

        Parameters:
        - b2chainsegment: The b2ChainSegment b2ShapeId
        - chain: The parent Chain object
        """
        self._shape_id = b2chainsegment
        self.parent_chain = chain
        super().__init__(chain.body, None)
        self._finalize()


class Chain:
    """
    A chain shape that can be attached to a body.
    Chain shapes are not a subclass of Shape and do not have the common shape methods
    because they are typically used for static boundaries and have no density/sensor properties.
    """

    def __init__(self, body, shapedef):
        self._body = body
        self._shape_id = lib.b2CreateChain(
            body._body_id, ffi.addressof(shapedef.shapedef)
        )
        segment_count = lib.b2Chain_GetSegmentCount(self._shape_id)
        segments = ffi.new("b2ShapeId[]", segment_count)
        lib.b2Chain_GetSegments(self._shape_id, segments, segment_count)
        self.segments = [ChainSegment(segments[i], self) for i in range(segment_count)]

    @classmethod
    def create(
        cls,
        body,
        vertices,
        loop=False,
        friction=None,
        restitution=None,
        collision_filter=None,
        custom_color=None,
    ):
        """
        Create and attach a chain shape to a body.
        """
        shapedef = ChainDef(
            vertices, loop, friction, restitution, collision_filter, custom_color
        )
        return cls(body, shapedef)

    @property
    def body(self):
        """Return the body this chain is attached to."""
        return self._body
