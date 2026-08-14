from dataclasses import dataclass
from typing import List, Optional, Union
from enum import IntEnum
from .math import Vec2, Rot, Transform
from ._box2d import lib, ffi


@dataclass
class MassData:
    """
    Mass data for a shape.

    Attributes:
        mass: The mass of the shape in kg.
        center: Center of mass relative to the shape's origin (Vec2).
        rotational_inertia: Moment of inertia about the center of mass.
    """

    mass: float
    center: Vec2
    rotational_inertia: float

    @classmethod
    def from_b2MassData(cls, mass_data):
        return cls(
            mass=mass_data.mass,
            center=Vec2.from_b2Vec2(mass_data.center),
            rotational_inertia=mass_data.rotationalInertia,
        )

    @property
    def b2MassData(self):
        mass_data = ffi.new("b2MassData*")
        mass_data.mass = self.mass
        mass_data.center = self.center.b2Vec2
        mass_data.rotationalInertia = self.rotational_inertia
        return mass_data


@dataclass
class CastResult:
    """
    Result of a ray cast operation.

    Attributes:
        point: Hit point in world coordinates (Vec2).
        normal: Surface normal at the hit point (Vec2).
        fraction: Fraction of the ray length where the hit occurred.
        iterations: Number of iterations used in the calculation.
    """

    point: Optional[Vec2] = None
    normal: Optional[Vec2] = None
    fraction: Optional[float] = None
    iterations: Optional[int] = None

    @classmethod
    def from_b2CastOutput(cls, output):
        if output.hit:
            return cls(
                point=Vec2.from_b2Vec2(output.point),
                normal=Vec2.from_b2Vec2(output.normal),
                fraction=output.fraction,
                iterations=output.iterations,
            )
        else:
            return None


@dataclass
class ManifoldPoint:
    """
    A contact point belonging to a contact manifold.

    Attributes:
        point: Location of the contact point in world space.
        anchor_a: Location of the contact point relative to shape A's origin.
        anchor_b: Location of the contact point relative to shape B's origin.
        separation: Separation of the contact point, negative if penetrating.
        normal_impulse: Impulse along the manifold normal vector.
        tangent_impulse: Friction impulse.
        max_normal_impulse: Maximum normal impulse applied during sub-stepping.
        normal_velocity: Relative normal velocity pre-solve. Negative means shapes approaching.
        id: Uniquely identifies a contact point between two shapes.
        persisted: True if the contact point existed in the previous step.
    """

    point: Vec2
    anchor_a: Vec2
    anchor_b: Vec2
    separation: float
    normal_impulse: float
    tangent_impulse: float
    max_normal_impulse: float
    normal_velocity: float
    id: int
    persisted: bool

    @classmethod
    def from_b2ManifoldPoint(cls, manifold_point):
        return cls(
            point=Vec2.from_b2Vec2(manifold_point.point),
            anchor_a=Vec2.from_b2Vec2(manifold_point.anchorA),
            anchor_b=Vec2.from_b2Vec2(manifold_point.anchorB),
            separation=manifold_point.separation,
            normal_impulse=manifold_point.normalImpulse,
            tangent_impulse=manifold_point.tangentImpulse,
            max_normal_impulse=manifold_point.maxNormalImpulse,
            normal_velocity=manifold_point.normalVelocity,
            id=manifold_point.id,
            persisted=manifold_point.persisted,
        )


@dataclass
class Manifold:
    """
    A contact manifold describing contact points between colliding shapes.

    Attributes:
        normal: The unit normal vector in world space, points from shape A to shape B.
        rolling_impulse: Angular impulse applied for rolling resistance.
        points: List of ManifoldPoint objects, up to two points in 2D.
    """

    normal: Vec2
    rolling_impulse: float
    points: List[ManifoldPoint]

    @classmethod
    def from_b2Manifold(cls, manifold):
        normal = (Vec2.from_b2Vec2(manifold.normal),)
        rolling_impulse = manifold.rollingImpulse
        points = [
            ManifoldPoint.from_b2ManifoldPoint(manifold.points[i])
            for i in range(manifold.pointCount)
        ]
        return cls(normal=normal, rolling_impulse=rolling_impulse, points=points)


@dataclass
class ContactData:
    """
    Data about a contact between two shapes.

    Attributes:
        shape_a: The first shape in the contact.
        shape_b: The second shape in the contact.
        manifold: The contact manifold describing the collision.
        enabled: Whether the contact is enabled.
        touching: Whether the shapes are touching.
    """

    shape_a: "Shape"
    shape_b: "Shape"
    manifold: Manifold

    @classmethod
    def from_b2ContactData(cls, contact_data):
        shape_a_data = lib.b2Shape_GetUserData(contact_data.shapeIdA)
        shape_b_data = lib.b2Shape_GetUserData(contact_data.shapeIdB)
        if shape_a_data is None or shape_b_data is None:
            raise ValueError("Shape data not found in contact data")

        manifold = Manifold.from_b2Manifold(contact_data.manifold)

        return cls(
            shape_a=ffi.from_handle(shape_a_data),
            shape_b=ffi.from_handle(shape_b_data),
            manifold=manifold,
        )


class BodyType(IntEnum):
    """
    Enum for body types: static (0), kinematic (1), or dynamic (2).
    """

    STATIC = lib.b2_staticBody
    KINEMATIC = lib.b2_kinematicBody
    DYNAMIC = lib.b2_dynamicBody


_default_body_def = lib.b2DefaultBodyDef()


@dataclass
class BodyDef:
    """
    A body definition holds all the data needed to construct a rigid body.

    You can safely re-use body definitions. Shapes are added to a body after construction.

    Attributes:
        type: The body type: static (0), kinematic (1), or dynamic (2).
        position: The initial world position of the body (Vec2).
        rotation: The initial world rotation of the body (Rot).
        linear_velocity: The initial linear velocity of the body's origin.
        angular_velocity: The initial angular velocity of the body in radians per second.
        linear_damping: Linear damping reduces linear velocity. Can be > 1.
        angular_damping: Angular damping reduces angular velocity. Can be > 1.
        gravity_scale: Scale the gravity applied to this body. Non-dimensional.
        sleep_threshold: Sleep speed threshold, default is 0.05 meters per second.
        name: Optional body name for debugging (up to 31 characters).
        user_data: Application specific body data.
        enable_sleep: Set to false if this body should never fall asleep.
        is_awake: Is this body initially awake or sleeping?
        fixed_rotation: Should this body be prevented from rotating?
        is_bullet: Treat this body as high speed object for continuous collision detection.
        is_enabled: Used to disable a body. A disabled body doesn't move or collide.
        allow_fast_rotation: Bypass rotational speed limits. For circular objects like wheels.
    """

    type: int = _default_body_def.type
    position: Vec2 = Vec2.from_b2Vec2(_default_body_def.position)
    rotation: Rot = Rot.from_b2Rot(_default_body_def.rotation)
    linear_velocity: Vec2 = Vec2.from_b2Vec2(_default_body_def.linearVelocity)
    angular_velocity: float = _default_body_def.angularVelocity
    linear_damping: float = _default_body_def.linearDamping
    angular_damping: float = _default_body_def.angularDamping
    gravity_scale: float = _default_body_def.gravityScale
    sleep_threshold: float = _default_body_def.sleepThreshold
    name: Optional[str] = None
    user_data: Optional[object] = None
    enable_sleep: bool = _default_body_def.enableSleep
    is_awake: bool = _default_body_def.isAwake
    fixed_rotation: bool = _default_body_def.fixedRotation
    is_bullet: bool = _default_body_def.isBullet
    is_enabled: bool = _default_body_def.isEnabled
    allow_fast_rotation: bool = _default_body_def.allowFastRotation

    @property
    def b2BodyDef(self):
        """
        Creates and returns the C structure for this body definition.

        Uses b2DefaultBodyDef() to get default values and only
        overrides properties that have been explicitly set.

        Returns:
            A b2BodyDef C structure representing this body definition
        """
        # Start with defaults
        body_def = lib.b2DefaultBodyDef()

        # Override with any explicitly set values
        body_def.type = self.type
        body_def.position = self.position.b2Vec2[0]
        body_def.rotation = self.rotation.b2Rot[0]
        body_def.linearVelocity = self.linear_velocity.b2Vec2[0]
        body_def.angularVelocity = self.angular_velocity
        body_def.linearDamping = self.linear_damping
        body_def.angularDamping = self.angular_damping
        body_def.gravityScale = self.gravity_scale
        body_def.sleepThreshold = self.sleep_threshold

        if self.name is not None:
            # Need to keep a reference to the C string
            self._name_string = ffi.new("char[]", self.name.encode("utf-8"))
            body_def.name = self._name_string

        if self.user_data is not None:
            body_def.userData = self.user_data

        body_def.enableSleep = self.enable_sleep
        body_def.isAwake = self.is_awake
        body_def.fixedRotation = self.fixed_rotation
        body_def.isBullet = self.is_bullet
        body_def.isEnabled = self.is_enabled
        body_def.allowFastRotation = self.allow_fast_rotation

        return body_def
