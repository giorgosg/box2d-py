"""
This module defines high-level shape objects for Box2D.
Each shape's constructor accepts a body and a shape definition.
Each shape (except Chain) subclasses a common base that implements common properties.
Each shape also has a classmethod "create" that matches the signature from before.
Chain is implemented as a separate class.
"""

from ._box2d import lib, ffi
from abc import ABC
from typing import List, Dict, Optional, Union, Any, Tuple, Iterable, Sequence
from .math import Vec2, Transform, VectorLike, AABB
from .shapedef import (
    ShapeDef,
    BoxDef,
    CircleDef,
    CapsuleDef,
    SegmentDef,
    PolygonDef,
    ChainDef,
)
from .material import SurfaceMaterial
from .collision_filter import CollisionFilter
from .dataclasses import MassData, CastResult, ManifoldPoint, Manifold, ContactData
from .accessors import b2_value
from .lifetime import IdRef, is_live, raw_id
from .accessors import b2_bool, b2_float, b2_value


class Shape(ABC):
    """
    Base class for all non-chain shapes.
    It provides common properties like density, friction, restitution
    """

    _shape_id = IdRef(lib.b2Shape_IsValid, "shape")

    def __init__(self, body: "Body"):
        self._body = body

    def _set_handle(self):
        """Set the handle for the shape."""
        self._handle = ffi.new_handle(self)
        lib.b2Shape_SetUserData(self._shape_id, self._handle)

    density = b2_float(
        lib.b2Shape_GetDensity,
        lib.b2Shape_SetDensity,
        extra_set_args=(True,),
        doc="""Get or set the mass density of the shape.

        Setting this updates the body's mass properties. Default is 1.0.
        """,
    )

    friction = b2_float(
        lib.b2Shape_GetFriction,
        lib.b2Shape_SetFriction,
        doc="""Get or set the Coulomb friction coefficient.

        Usually in the range [0,1], where 0 slides freely. Default is 0.6.
        """,
    )

    restitution = b2_float(
        lib.b2Shape_GetRestitution,
        lib.b2Shape_SetRestitution,
        doc="""Get or set the restitution, or bounciness.

        Usually in the range [0,1], where 0 does not bounce. Default is 0.0.
        """,
    )

    is_sensor = b2_bool(
        lib.b2Shape_IsSensor,
        doc="Whether this shape is a sensor, detecting overlap without colliding.",
    )

    @property
    def body(self) -> "Body":
        """Return the body to which this shape is attached."""
        body_id = lib.b2Shape_GetBody(self._shape_id)
        body_data = lib.b2Body_GetUserData(body_id)
        if body_data == ffi.NULL:
            raise ValueError("Body not found for shape")
        return ffi.from_handle(body_data)

    @property
    def material(self) -> int:
        """
        Get or set the shape material identifier.

        The material is used to customize friction, restitution, and other material properties
        through custom callbacks. When setting, you can use either a material ID (int)
        or a SurfaceMaterial object.
        """
        return lib.b2Shape_GetUserMaterial(self._shape_id)

    @material.setter
    def material(self, value: Union[int, SurfaceMaterial]) -> None:
        if hasattr(value, "material"):
            # If it's a SurfaceMaterial object
            lib.b2Shape_SetUserMaterial(self._shape_id, value.material)
        else:
            # If it's a material ID
            lib.b2Shape_SetUserMaterial(self._shape_id, int(value))

    @property
    def filter(self) -> CollisionFilter:
        """
        Get or set the shape collision filter.

        The collision filter determines which shapes can collide with each other
        based on category bits, mask bits, and group index.

        When setting a new filter, this operation is almost as expensive as recreating
        the shape and may cause contacts to be immediately destroyed. Contacts are not
        created until the next world step, and sensor overlap state is not updated until
        the next step.
        """
        b2filter = lib.b2Shape_GetFilter(self._shape_id)
        return CollisionFilter(
            category=b2filter.categoryBits,
            mask=b2filter.maskBits,
            group=b2filter.groupIndex,
        )

    @filter.setter
    def filter(self, value: CollisionFilter) -> None:
        lib.b2Shape_SetFilter(self._shape_id, value.b2Filter[0])

    enable_sensor_events = b2_bool(
        lib.b2Shape_AreSensorEventsEnabled,
        lib.b2Shape_EnableSensorEvents,
        doc="""Get or set whether sensors may detect this shape.

        Box2D 3.2 made this opt-in on the visiting shape. It was previously
        settable only when the shape was created.
        """,
    )
    enable_contact_events = b2_bool(
        lib.b2Shape_AreContactEventsEnabled,
        lib.b2Shape_EnableContactEvents,
        doc="""Get or set whether this shape reports begin and end touch events.\n\n        Ignored for sensors. Changing it at run time may lose events.
        """,
    )

    enable_pre_solve_events = b2_bool(
        lib.b2Shape_ArePreSolveEventsEnabled,
        lib.b2Shape_EnablePreSolveEvents,
        doc="""Get or set whether this shape reports pre-solve events.\n\n        Expensive, and called from worker threads. Dynamic bodies only.
        """,
    )

    enable_hit_events = b2_bool(
        lib.b2Shape_AreHitEventsEnabled,
        lib.b2Shape_EnableHitEvents,
        doc="""Get or set whether this shape reports hit events above the world's\n        hit threshold. Ignored for sensors.
        """,
    )

    shape_type = b2_value(
        lib.b2Shape_GetType,
        doc="""The kind of shape this is.

        One of Box2D's shape type constants: circle, capsule, segment or polygon.
        """,
    )

    @property
    def world(self) -> "World":
        """
        Get the world that owns this shape.

        Uses the user data handle to retrieve the World object.
        """
        world_id = lib.b2Shape_GetWorld(self._shape_id)
        world_data = lib.b2World_GetUserData(world_id)
        if world_data == ffi.NULL:
            raise ValueError("World not found for shape")
        return ffi.from_handle(world_data)

    @property
    def aabb(self) -> AABB:
        """
        Get the current world AABB of this shape.

        The AABB (Axis-Aligned Bounding Box) is the smallest rectangle
        that completely contains the shape in world coordinates.
        """
        b2aabb = lib.b2Shape_GetAABB(self._shape_id)
        return AABB.from_b2AABB(b2aabb)

    @property
    def mass_data(self) -> MassData:
        """
        Get the mass data for this shape.

        Returns a MassData object containing:
        - mass: The total mass of the shape
        - center: Center of mass position (Vec2)
        - rotational_inertia: Moment of inertia about the center of mass
        """
        md = lib.b2Shape_ComputeMassData(self._shape_id)
        return MassData.from_b2MassData(md)

    def is_valid(self) -> bool:
        """
        Shape identifier validation. Can be used to detect orphaned ids.

        Returns:
            True if the shape id is valid, False otherwise
        """
        return is_live(self, "_shape_id", lib.b2Shape_IsValid)

    def destroy(self, update_body_mass: bool = True) -> None:
        """Remove this shape from its body.

        The shape raises :class:`DestroyedError` if used afterwards. Destroying
        twice is a no-op.

        Args:
            update_body_mass: Recompute the body's mass from its remaining
                shapes. Pass False when removing several shapes at once and
                call body.apply_mass_from_shapes() when done.
        """
        raw = raw_id(self, "_shape_id")
        if raw is None:
            return
        if lib.b2Shape_IsValid(raw):
            lib.b2DestroyShape(raw, bool(update_body_mass))
        body = getattr(self, "_body", None)
        if body is not None and self in getattr(body, "_shapes", ()):
            body._shapes.remove(self)
        del self._shape_id

    @property
    def surface_material(self):
        """Get or set every surface property at once, as a SurfaceMaterial."""
        material = lib.b2Shape_GetSurfaceMaterial(self._shape_id)
        return SurfaceMaterial(
            material=material.userMaterialId,
            friction=material.friction,
            restitution=material.restitution,
            rolling_resistance=material.rollingResistance,
            tangent_speed=material.tangentSpeed,
            custom_color=material.customColor,
        )

    @surface_material.setter
    def surface_material(self, value: SurfaceMaterial) -> None:
        material = value.b2SurfaceMaterial
        lib.b2Shape_SetSurfaceMaterial(self._shape_id, ffi.addressof(material))

    def _set_material_field(self, field: str, value: float) -> None:
        """Change one surface property, leaving the rest of the material alone."""
        material = lib.b2Shape_GetSurfaceMaterial(self._shape_id)
        setattr(material, field, float(value))
        lib.b2Shape_SetSurfaceMaterial(self._shape_id, ffi.addressof(material))

    @property
    def tangent_speed(self) -> float:
        """Get or set the surface velocity, which drives conveyor belt effects."""
        return lib.b2Shape_GetSurfaceMaterial(self._shape_id).tangentSpeed

    @tangent_speed.setter
    def tangent_speed(self, value: float) -> None:
        self._set_material_field("tangentSpeed", value)

    @property
    def rolling_resistance(self) -> float:
        """Get or set the rolling resistance, usually in the range [0,1]."""
        return lib.b2Shape_GetSurfaceMaterial(self._shape_id).rollingResistance

    @rolling_resistance.setter
    def rolling_resistance(self, value: float) -> None:
        self._set_material_field("rollingResistance", value)

    def test_point(self, point: VectorLike) -> bool:
        """
        Test a point for overlap with this shape.

        Args:
            point: A Vec2 or tuple representing the world point to test

        Returns:
            True if the point is inside the shape, False otherwise
        """
        return lib.b2Shape_TestPoint(self._shape_id, Vec2(point).b2Vec2[0])

    def ray_cast(
        self, origin: VectorLike, translation: VectorLike
    ) -> Union[CastResult, None]:
        """
        Ray cast against this shape directly.

        Args:
            origin: The start point of the ray
            translation: The translation of the ray from the start point to the end point

        Returns:
            A RayCastResult object containing hit information
        """
        # 3.2 takes the origin and translation directly rather than a
        # b2RayCastInput, and always casts the full translation.
        output = lib.b2Shape_RayCast(
            self._shape_id, Vec2(origin).b2Vec2[0], Vec2(translation).b2Vec2[0]
        )
        return CastResult.from_b2CastOutput(output)

    contact_capacity = b2_value(
        lib.b2Shape_GetContactCapacity,
        doc="""Get the maximum capacity required for retrieving all the touching
        contacts on this shape.
        
        Returns:
            The required capacity for reading contact_data
        """,
    )

    @property
    def contact_data(self) -> List[ContactData]:
        """
        Get the touching contact data for this shape.

        Convenience property that automatically determines the capacity
        and returns all contact data as ContactData objects.
        """
        return self._read_contact_data()

    def _read_contact_data(self, capacity=None) -> List[ContactData]:
        """
        Get the touching contact data for this shape. The provided shape ID
        will be either shapeIdA or shapeIdB on the contact data.

        Note: Box2D uses speculative collision so some contact points may be separated.

        Args:
            capacity: Optional capacity for the contact data array.
                     If None, uses contact_capacity.

        Returns:
            A list of ContactData objects
        """
        if capacity is None:
            capacity = self.contact_capacity

        if capacity == 0:
            return []

        contact_data = ffi.new("b2ContactData[]", capacity)
        count = lib.b2Shape_GetContactData(self._shape_id, contact_data, capacity)

        result = [ContactData.from_b2ContactData(contact_data[i]) for i in range(count)]

        return result

    sensor_capacity = b2_value(
        lib.b2Shape_GetSensorCapacity,
        doc="""Get the maximum capacity required for retrieving all the overlapped
        shapes on a sensor shape. Returns 0 if this shape is not a sensor.
        
        Returns:
            The required capacity for reading sensor_overlaps
        """,
    )

    @property
    def sensor_overlaps(self) -> List["Shape"]:
        """
        Get all shapes that overlap with this sensor shape.

        Convenience property that automatically determines the capacity
        and returns all overlapping Shape objects.

        Returns an empty list if this shape is not a sensor.
        """
        return self._read_sensor_overlaps()

    def _read_sensor_overlaps(self, capacity=None) -> List["Shape"]:
        """
        Get the overlapped shapes for a sensor shape.

        Args:
            capacity: Optional capacity for the overlaps array.
                     If None, uses sensor_capacity.

        Returns:
            A list of Shape objects that overlap with this sensor.
            Returns an empty list if this shape is not a sensor.
        """
        if capacity is None:
            capacity = self.sensor_capacity

        if capacity == 0:
            return []

        overlaps = ffi.new("b2ShapeId[]", capacity)
        count = lib.b2Shape_GetSensorData(self._shape_id, overlaps, capacity)

        result = []
        for i in range(count):
            shape_id = overlaps[i]
            if lib.b2Shape_IsValid(shape_id):
                shape_data = lib.b2Shape_GetUserData(shape_id)
                if shape_data != ffi.NULL:
                    shape = ffi.from_handle(shape_data)
                    result.append(shape)

        return result

    def get_closest_point(self, target: VectorLike) -> Vec2:
        """
        Get the closest point on the shape to a target point.
        Target and result are in world space.

        Args:
            target: A Vec2 or tuple representing the target point

        Returns:
            A Vec2 representing the closest point on the shape
        """
        result = lib.b2Shape_GetClosestPoint(self._shape_id, Vec2(target).b2Vec2[0])
        return Vec2(result.x, result.y)


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

    @property
    def geometry(self) -> CircleDef:
        """
        Get or set this shape's geometry as a CircleDef.

        Setting geometry does not update the body's mass properties; call
        body.apply_mass_from_shapes() if you need them recomputed.
        """
        return CircleDef.from_b2Circle(lib.b2Shape_GetCircle(self._shape_id))

    @geometry.setter
    def geometry(self, circle_def: CircleDef) -> None:
        lib.b2Shape_SetCircle(self._shape_id, circle_def.b2Circle)

    @property
    def radius(self) -> float:
        """Get or set the radius of the circle."""
        return self.geometry.radius

    @radius.setter
    def radius(self, value: float) -> None:
        self.geometry = CircleDef(radius=float(value), center=self.geometry.center)

    @property
    def center(self) -> Vec2:
        """Get or set the circle's center, relative to the body origin."""
        return self.geometry.center

    @center.setter
    def center(self, value: VectorLike) -> None:
        self.geometry = CircleDef(radius=self.geometry.radius, center=Vec2(value))

    @classmethod
    def create(
        cls,
        body,
        radius,
        center: VectorLike = (0, 0),
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

    @property
    def geometry(self) -> CapsuleDef:
        """
        Get or set this shape's geometry as a CapsuleDef.

        Setting geometry does not update the body's mass properties; call
        body.apply_mass_from_shapes() if you need them recomputed.
        """
        return CapsuleDef.from_b2Capsule(lib.b2Shape_GetCapsule(self._shape_id))

    @geometry.setter
    def geometry(self, capsule_def: CapsuleDef) -> None:
        lib.b2Shape_SetCapsule(self._shape_id, capsule_def.b2Capsule)

    @property
    def point1(self) -> Vec2:
        """Get or set the first endpoint of the capsule's axis."""
        return self.geometry.vertex1

    @point1.setter
    def point1(self, value: VectorLike) -> None:
        current = self.geometry
        self.geometry = CapsuleDef(Vec2(value), current.vertex2, current.radius)

    @property
    def point2(self) -> Vec2:
        """Get or set the second endpoint of the capsule's axis."""
        return self.geometry.vertex2

    @point2.setter
    def point2(self, value: VectorLike) -> None:
        current = self.geometry
        self.geometry = CapsuleDef(current.vertex1, Vec2(value), current.radius)

    @property
    def radius(self) -> float:
        """Get or set the radius of the capsule's half-circles."""
        return self.geometry.radius

    @radius.setter
    def radius(self, value: float) -> None:
        current = self.geometry
        self.geometry = CapsuleDef(current.vertex1, current.vertex2, float(value))

    @classmethod
    def create(
        cls,
        body,
        point1: VectorLike,
        point2: VectorLike,
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

    @property
    def geometry(self) -> SegmentDef:
        """
        Get or set this shape's geometry as a SegmentDef.

        Setting geometry does not update the body's mass properties; call
        body.apply_mass_from_shapes() if you need them recomputed.
        """
        return SegmentDef.from_b2Segment(lib.b2Shape_GetSegment(self._shape_id))

    @geometry.setter
    def geometry(self, segment_def: SegmentDef) -> None:
        lib.b2Shape_SetSegment(self._shape_id, segment_def.b2Segment)

    @property
    def point1(self) -> Vec2:
        """Get or set the first endpoint of the segment."""
        return self.geometry.vertex1

    @point1.setter
    def point1(self, value: VectorLike) -> None:
        self.geometry = SegmentDef(Vec2(value), self.geometry.vertex2)

    @property
    def point2(self) -> Vec2:
        """Get or set the second endpoint of the segment."""
        return self.geometry.vertex2

    @point2.setter
    def point2(self, value: VectorLike) -> None:
        self.geometry = SegmentDef(self.geometry.vertex1, Vec2(value))

    @classmethod
    def create(
        cls,
        body,
        point1: VectorLike,
        point2: VectorLike,
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

    @property
    def geometry(self) -> PolygonDef:
        """
        Get or set this shape's geometry as a PolygonDef.

        Setting geometry does not update the body's mass properties; call
        body.apply_mass_from_shapes() if you need them recomputed.
        """
        return PolygonDef.from_b2Polygon(lib.b2Shape_GetPolygon(self._shape_id))

    @geometry.setter
    def geometry(self, polygon_def: PolygonDef) -> None:
        lib.b2Shape_SetPolygon(self._shape_id, ffi.addressof(polygon_def.b2Polygon))

    @property
    def vertices(self) -> List[Vec2]:
        """Get or set the polygon's vertices, in body-local coordinates."""
        return self.geometry.vertices

    @vertices.setter
    def vertices(self, value: Iterable[VectorLike]) -> None:
        self.geometry = PolygonDef(list(value), self.geometry.radius)

    @property
    def radius(self) -> float:
        """Get or set the radius of the polygon's rounded corners."""
        return self.geometry.radius

    @radius.setter
    def radius(self, value: float) -> None:
        self.geometry = PolygonDef(self.geometry.vertices, float(value))

    @classmethod
    def create(
        cls,
        body,
        vertices: Sequence[VectorLike],
        radius=0.0,
        offset: VectorLike = (0, 0),
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
        offset: VectorLike = (0, 0),
        angle=0.0,
        **shapedef_kwargs,
    ):
        """
        Create and attach a box shape to a body.
        The parameters are the same as the previous initializer.
        """
        # Built directly rather than through Polygon's hull, which has a
        # minimum feature size that very thin boxes fall below.
        boxdef = BoxDef(width, height, radius=radius, offset=offset, rotation=angle)
        shapedef = ShapeDef(**shapedef_kwargs)
        return cls(body, shapedef, boxdef)


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

    _chain_id = IdRef(lib.b2Chain_IsValid, "chain")

    def __init__(self, body: "Body", chaindef: ChainDef):
        self._body = body
        cd = chaindef.b2ChainDef
        self._chain_id = lib.b2CreateChain(body._body_id, ffi.addressof(cd))
        segment_count = lib.b2Chain_GetSegmentCount(self._chain_id)
        segments = ffi.new("b2ShapeId[]", segment_count)
        lib.b2Chain_GetSegments(self._chain_id, segments, segment_count)
        self.segments = [ChainSegment(segments[i], self) for i in range(segment_count)]

    @classmethod
    def create(
        cls,
        body,
        vertices: Sequence[VectorLike],
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

    def is_valid(self) -> bool:
        """
        Chain identifier validation. Can be used to detect orphaned ids.

        Returns:
            True if the chain id is valid, False otherwise
        """
        return is_live(self, "_chain_id", lib.b2Chain_IsValid)

    @property
    def world(self) -> "World":
        """
        Get the world that owns this chain.

        Returns:
            The World object that owns this chain
        """
        world_id = lib.b2Chain_GetWorld(self._chain_id)
        world_data = lib.b2World_GetUserData(world_id)
        if world_data == ffi.NULL:
            raise ValueError("World data is NULL")
        return ffi.from_handle(world_data)
