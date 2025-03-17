from dataclasses import dataclass
from typing import List, Optional, Union
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
