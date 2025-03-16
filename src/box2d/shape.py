"""
This module defines high-level shape objects for Box2D.
Each shape's constructor accepts a body and a shape definition.
Each shape (except Chain) subclasses a common base that implements common properties.
Each shape also has a classmethod "create" that matches the signature from before.
Chain is implemented as a separate class.
"""

from ._box2d import lib, ffi
from abc import ABC
from typing import List, Dict, Optional, Union, Any, Tuple
from .math import Vec2, Transform, VectorLike, AABB, to_vec2
from .shapedef import (
    ShapeDef,
    CircleDef,
    CapsuleDef,
    SegmentDef,
    PolygonDef,
    ChainDef,
)
from .material import SurfaceMaterial
from .collision_filter import CollisionFilter
from .dataclasses import MassData, RayCastResult, ManifoldPoint, Manifold, ContactData


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
    def density(self) -> float:
        """
        Get or set the mass density of the shape.

        When setting, the body mass properties are automatically updated if update_body_mass is True.
        Default density is 1.0.
        """
        return lib.b2Shape_GetDensity(self._shape_id)

    @density.setter
    def density(self, value: float) -> None:
        lib.b2Shape_SetDensity(self._shape_id, float(value), True)

    @property
    def friction(self) -> float:
        """
        Get or set the friction coefficient of the shape.

        Friction is used to make objects slide realistically along surfaces.
        Usually in the range [0,1] where 0 is frictionless and 1 is high friction.
        Default friction is 0.6.
        """
        return lib.b2Shape_GetFriction(self._shape_id)

    @friction.setter
    def friction(self, value: float) -> None:
        lib.b2Shape_SetFriction(self._shape_id, float(value))

    @property
    def restitution(self) -> float:
        """
        Get or set the restitution (bounciness) of the shape.

        Restitution determines how bouncy a shape is during collisions.
        Usually in the range [0,1] where 0 means no bounce and 1 is perfect bounce.
        Default restitution is 0.0.
        """
        return lib.b2Shape_GetRestitution(self._shape_id)

    @restitution.setter
    def restitution(self, value: float) -> None:
        lib.b2Shape_SetRestitution(self._shape_id, float(value))

    @property
    def is_sensor(self) -> bool:
        """Check if this shape is a sensor."""
        return lib.b2Shape_IsSensor(self._shape_id)

    @property
    def body(self) -> "Body":
        """Return the body to which this shape is attached."""
        body_id = lib.b2Shape_GetBody(self._shape_id)
        body_data = lib.b2Body_GetUserData(body_id)
        if body_data == ffi.NULL:
            return None
        return ffi.from_handle(body_data)

    @property
    def material(self) -> int:
        """
        Get or set the shape material identifier.

        The material is used to customize friction, restitution, and other material properties
        through custom callbacks. When setting, you can use either a material ID (int)
        or a SurfaceMaterial object.
        """
        return lib.b2Shape_GetMaterial(self._shape_id)

    @material.setter
    def material(self, value: Union[int, SurfaceMaterial]) -> None:
        if hasattr(value, "material"):
            # If it's a SurfaceMaterial object
            lib.b2Shape_SetMaterial(self._shape_id, value.material)
        else:
            # If it's a material ID
            lib.b2Shape_SetMaterial(self._shape_id, int(value))

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

    @property
    def enable_contact_events(self) -> bool:
        """
        Get or set whether contact events are enabled for this shape.

        Contact events notify when shapes begin or end touching.
        Only applies to kinematic and dynamic bodies and is ignored for sensors.

        Warning: Changing this at run-time may lead to lost begin/end events.
        """
        return lib.b2Shape_AreContactEventsEnabled(self._shape_id)

    @enable_contact_events.setter
    def enable_contact_events(self, flag: bool) -> None:
        lib.b2Shape_EnableContactEvents(self._shape_id, bool(flag))

    @property
    def enable_pre_solve_events(self) -> bool:
        """
        Get or set whether pre-solve events are enabled for this shape.

        Pre-solve events allow modifying contact properties before collision response.
        These are expensive and must be carefully handled due to multithreading.
        Only applies to dynamic bodies and is ignored for sensors.
        """
        return lib.b2Shape_ArePreSolveEventsEnabled(self._shape_id)

    @enable_pre_solve_events.setter
    def enable_pre_solve_events(self, flag: bool) -> None:
        lib.b2Shape_EnablePreSolveEvents(self._shape_id, bool(flag))

    @property
    def enable_hit_events(self) -> bool:
        """
        Get or set whether hit events are enabled for this shape.

        Hit events notify when shapes collide with sufficient velocity.
        This setting is ignored for sensors.
        """
        return lib.b2Shape_AreHitEventsEnabled(self._shape_id)

    @enable_hit_events.setter
    def enable_hit_events(self, flag: bool) -> None:
        lib.b2Shape_EnableHitEvents(self._shape_id, bool(flag))

    @property
    def shape_type(self) -> int:
        """
        Get the type of this shape.

        Returns an integer constant indicating whether this is a circle,
        polygon, capsule, segment, or other shape type.
        """
        return lib.b2Shape_GetType(self._shape_id)

    @property
    def world(self) -> "World":
        """
        Get the world that owns this shape.

        Uses the user data handle to retrieve the World object.
        """
        world_id = lib.b2Shape_GetWorld(self._shape_id)
        world_data = lib.b2World_GetUserData(world_id)
        if world_data == ffi.NULL:
            return None
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
        md = lib.b2Shape_GetMassData(self._shape_id)
        return MassData(
            mass=md.mass,
            center=Vec2(md.center.x, md.center.y),
            rotational_inertia=md.rotationalInertia,
        )

    def is_valid(self) -> bool:
        """
        Shape identifier validation. Can be used to detect orphaned ids.

        Returns:
            True if the shape id is valid, False otherwise
        """
        return lib.b2Shape_IsValid(self._shape_id)

    def test_point(self, point: VectorLike) -> bool:
        """
        Test a point for overlap with this shape.

        Args:
            point: A Vec2 or tuple representing the world point to test

        Returns:
            True if the point is inside the shape, False otherwise
        """
        return lib.b2Shape_TestPoint(self._shape_id, to_vec2(point).b2Vec2[0])

    def ray_cast(
        self, origin: VectorLike, translation: VectorLike
    ) -> Union[RayCastResult, None]:
        """
        Ray cast against this shape directly.

        Args:
            origin: The start point of the ray
            translation: The translation of the ray from the start point to the end point

        Returns:
            A RayCastResult object containing hit information
        """
        input = ffi.new("b2RayCastInput*")
        input.origin = to_vec2(origin).b2Vec2[0]
        input.translation = to_vec2(translation).b2Vec2[0]
        input.maxFraction = 1.0

        output = lib.b2Shape_RayCast(self._shape_id, input)
        if output.hit:
            return RayCastResult(
                point=Vec2(output.point.x, output.point.y),
                normal=Vec2(output.normal.x, output.normal.y),
                fraction=output.fraction,
                iterations=output.iterations,
            )
        else:
            return None

    def get_contact_capacity(self) -> int:
        """
        Get the maximum capacity required for retrieving all the touching
        contacts on this shape.

        Returns:
            The required capacity for get_contact_data
        """
        return lib.b2Shape_GetContactCapacity(self._shape_id)

    @property
    def contact_data(self) -> List[ContactData]:
        """
        Get the touching contact data for this shape.

        Convenience property that automatically determines the capacity
        and returns all contact data as ContactData objects.
        """
        return self.get_contact_data()

    def get_contact_data(self, capacity: Optional[int] = None) -> List[ContactData]:
        """
        Get the touching contact data for this shape. The provided shape ID
        will be either shapeIdA or shapeIdB on the contact data.

        Note: Box2D uses speculative collision so some contact points may be separated.

        Args:
            capacity: Optional capacity for the contact data array.
                     If None, will use get_contact_capacity().

        Returns:
            A list of ContactData objects
        """
        if capacity is None:
            capacity = self.get_contact_capacity()

        if capacity == 0:
            return []

        contact_data = ffi.new("b2ContactData[]", capacity)
        count = lib.b2Shape_GetContactData(self._shape_id, contact_data, capacity)

        result = []
        for i in range(count):
            data = contact_data[i]

            # Get the shapes from the IDs
            shape_a_data = lib.b2Shape_GetUserData(data.shapeIdA)
            shape_b_data = lib.b2Shape_GetUserData(data.shapeIdB)

            shape_a = (
                None if shape_a_data == ffi.NULL else ffi.from_handle(shape_a_data)
            )
            shape_b = (
                None if shape_b_data == ffi.NULL else ffi.from_handle(shape_b_data)
            )

            # Convert manifold points
            manifold_points = []
            for j in range(data.manifold.pointCount):
                mp = data.manifold.points[j]
                manifold_points.append(
                    ManifoldPoint(
                        point=Vec2(mp.point.x, mp.point.y),
                        anchor_a=Vec2(mp.anchorA.x, mp.anchorA.y),
                        anchor_b=Vec2(mp.anchorB.x, mp.anchorB.y),
                        separation=mp.separation,
                        normal_impulse=mp.normalImpulse,
                        tangent_impulse=mp.tangentImpulse,
                        max_normal_impulse=mp.maxNormalImpulse,
                        normal_velocity=mp.normalVelocity,
                        id=mp.id,
                        persisted=mp.persisted,
                    )
                )

            # Create manifold
            manifold = Manifold(
                normal=Vec2(data.manifold.normal.x, data.manifold.normal.y),
                rolling_impulse=data.manifold.rollingImpulse,
                points=manifold_points,
            )

            # Create contact data
            contact = ContactData(shape_a=shape_a, shape_b=shape_b, manifold=manifold)

            result.append(contact)

        return result

    def get_sensor_capacity(self) -> int:
        """
        Get the maximum capacity required for retrieving all the overlapped
        shapes on a sensor shape. Returns 0 if this shape is not a sensor.

        Returns:
            The required capacity for get_sensor_overlaps
        """
        return lib.b2Shape_GetSensorCapacity(self._shape_id)

    @property
    def sensor_overlaps(self) -> List["Shape"]:
        """
        Get all shapes that overlap with this sensor shape.

        Convenience property that automatically determines the capacity
        and returns all overlapping Shape objects.

        Returns an empty list if this shape is not a sensor.
        """
        return self.get_sensor_overlaps()

    def get_sensor_overlaps(self, capacity: Optional[int] = None) -> List["Shape"]:
        """
        Get the overlapped shapes for a sensor shape.

        Args:
            capacity: Optional capacity for the overlaps array.
                     If None, will use get_sensor_capacity().

        Returns:
            A list of Shape objects that overlap with this sensor.
            Returns an empty list if this shape is not a sensor.
        """
        if capacity is None:
            capacity = self.get_sensor_capacity()

        if capacity == 0:
            return []

        overlaps = ffi.new("b2ShapeId[]", capacity)
        count = lib.b2Shape_GetSensorOverlaps(self._shape_id, overlaps, capacity)

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
        result = lib.b2Shape_GetClosestPoint(self._shape_id, to_vec2(target).b2Vec2[0])
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
