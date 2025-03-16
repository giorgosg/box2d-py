"""
This module defines high-level shape objects for Box2D.
Each shape’s constructor accepts a body and a shape definition.
Each shape (except Chain) subclasses a common base that implements common properties.
Each shape also has a classmethod “create” that matches the signature from before.
Chain is now implemented as a separate class.
"""

from ._box2d import lib, ffi
from abc import ABC
from .math import Vec2, Transform, VectorLike
from .shapedef import (
    ShapeDef,
    CircleDef,
    CapsuleDef,
    SegmentDef,
    PolygonDef,
    ChainDef,
)
from .material import SurfaceMaterial


class Shape(ABC):
    """
    Base class for all non-chain shapes.
    It provides common properties like density, friction, restitution
    """

    def __init__(self, body: "Body"):
        self._body = body

    def _set_handle(self):
        """Set the handle for the shape."""
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

    def __init__(self, body: "Body", shapedef: ShapeDef, circledef: CircleDef):
        """
        Initialize a Circle shape from a body a ShapeDef and a CircleDef instance.
        """
        super().__init__(body)
        sd = shapedef.b2ShapeDef
        self._shape_id = lib.b2CreateCircleShape(
            body._body_id, ffi.addressof(sd), circledef.b2Circle
        )
        self._set_handle()

    @classmethod
    def create(
        cls,
        body,
        radius,
        center=(0, 0),
        **shapedef_kwargs,
    ):
        """
        Create and attach a circle shape to a body.
        The parameters are the same as the previous initializer.
        """
        circledef = CircleDef(radius, center)
        shapedef = ShapeDef(**shapedef_kwargs)
        return cls(body, shapedef, circledef)


class Capsule(Shape):
    """
    A capsule shape that can be attached to a body.
    """

    def __init__(self, body: "Body", shapedef: ShapeDef, capsuledef: CapsuleDef):
        """
        Initialize a Capsule shape from a body and a CapsuleDef instance.
        """
        super().__init__(body)
        sd = shapedef.b2ShapeDef
        self._shape_id = lib.b2CreateCapsuleShape(
            body._body_id, ffi.addressof(sd), capsuledef.b2Capsule
        )
        self._set_handle()

    @classmethod
    def create(
        cls,
        body,
        point1,
        point2,
        radius,
        **shapedef_kwargs,
    ):
        """
        Create and attach a capsule shape to a body.
        The parameters are the same as the previous initializer.
        """
        capsuledef = CapsuleDef(point1, point2, radius)
        shapedef = ShapeDef(**shapedef_kwargs)
        return cls(body, shapedef, capsuledef)


class Segment(Shape):
    """
    A line segment shape that can be attached to a body.
    """

    def __init__(self, body: "Body", shapedef: ShapeDef, segmentdef: SegmentDef):
        """
        Initialize a Segment shape from a body and a SegmentDef instance.
        """
        super().__init__(body)
        sd = shapedef.b2ShapeDef
        self._shape_id = lib.b2CreateSegmentShape(
            body._body_id, ffi.addressof(sd), segmentdef.b2Segment
        )
        self._set_handle()

    @classmethod
    def create(
        cls,
        body,
        point1,
        point2,
        **shapedef_kwargs,
    ):
        """
        Create and attach a segment shape to a body.
        The parameters are the same as the previous initializer.
        """
        segmentdef = SegmentDef(point1, point2)
        shapedef = ShapeDef(**shapedef_kwargs)
        return cls(body, shapedef, segmentdef)


class Polygon(Shape):
    """
    A convex polygon shape that can be attached to a body.
    """

    def __init__(self, body: "Body", shapedef: ShapeDef, polygondef: PolygonDef):
        """
        Initialize a Polygon shape from a body and a PolygonDef instance.
        """
        super().__init__(body)
        sd = shapedef.b2ShapeDef
        pd = polygondef.b2Polygon
        self._shape_id = lib.b2CreatePolygonShape(
            body._body_id,
            ffi.addressof(sd),
            ffi.addressof(pd),
        )
        self._set_handle()

    @classmethod
    def create(
        cls,
        body,
        vertices,
        radius=0.0,
        offset=(0, 0),
        angle=0.0,
        **shapedef_kwargs,
    ):
        """
        Create and attach a polygon shape to a body.
        The parameters are the same as the previous initializer.
        """
        polygondef = PolygonDef(
            vertices,
            radius=radius,
            offset=offset,
            rotation=angle,
        )
        shapedef = ShapeDef(
            **shapedef_kwargs,
        )
        b2sd = shapedef.b2ShapeDef
        return cls(body, shapedef, polygondef)


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
        **shapedef_kwargs,
    ):
        """
        Create and attach a box shape to a body.
        The parameters are the same as the previous initializer.
        """
        vertices = [
            (-width / 2, -height / 2),
            (width / 2, -height / 2),
            (width / 2, height / 2),
            (-width / 2, height / 2),
        ]
        return super().create(
            body,
            vertices,
            radius=radius,
            offset=offset,
            angle=angle,
            **shapedef_kwargs,
        )


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
        super().__init__(chain.body)
        self._set_handle()


class Chain:
    """
    A chain shape that can be attached to a body.
    Chain shapes are not a subclass of Shape and do not have the common shape methods
    because they are typically used for static boundaries and have no density/sensor properties.
    """

    def __init__(self, body: "Body", chaindef: ChainDef):
        self._body = body
        cd = chaindef.b2ChainDef
        self._shape_id = lib.b2CreateChain(body._body_id, ffi.addressof(cd))
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
        filter=None,
        materials=None,
        friction=None,
        restitution=None,
        rolling_resistance=None,
        tangent_speed=None,
        custom_color=None,
    ):
        """
        Create and attach a chain shape to a body.
        """
        if materials is None:
            materials = [
                SurfaceMaterial(
                    friction=friction,
                    restitution=restitution,
                    tangent_speed=tangent_speed,
                    rolling_resistance=rolling_resistance,
                    custom_color=custom_color,
                )
            ]
        shapedef = ChainDef(vertices, loop, filter=filter, materials=materials)
        return cls(body, shapedef)

    @property
    def body(self):
        """Return the body this chain is attached to."""
        return self._body
