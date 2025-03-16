from dataclasses import dataclass
from typing import List, Optional, Union
from .math import Vec2, Rot, Transform


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


@dataclass
class RayCastResult:
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
