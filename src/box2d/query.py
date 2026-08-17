"""
The shape used to ask the world a question.

Overlap and cast queries do not take a :class:`.Shape` -- a shape belongs to a
body and sits somewhere in the world, while a query is about a region you
describe on the spot. Box2D expresses that region as a point cloud with a
radius, which covers every case with one type: one point with a radius is a
circle, two points a capsule, four a box, and any point with a zero radius is
the polygon through them.

:class:`.ShapeProxy` is that region, with constructors for the shapes you
actually want rather than the point clouds behind them::

    world.query_shape(ShapeProxy.box(2, 1, center=(4, 0)))
    world.cast_shape(ShapeProxy.circle(0.5, center=(0, 10)), (0, -20))

The points are in world coordinates, the same as every other query here.
"""

import math
from dataclasses import dataclass, field
from typing import List

from ._box2d import ffi
from .math import Vec2, VectorLike

#: Box2D's B2_MAX_POLYGON_VERTICES. A proxy may not carry more points than this.
MAX_PROXY_POINTS = 8


@dataclass
class ShapeProxy:
    """A point cloud with a radius, describing a region to query.

    Prefer the constructors below to building one by hand.

    Attributes:
        points: The point cloud, in world coordinates. At least one, and no
            more than :data:`MAX_PROXY_POINTS`.
        radius: How far the region extends beyond the points. A radius around
            one point is a circle, around two a capsule.
    """

    points: List[Vec2] = field(default_factory=list)
    radius: float = 0.0

    def __post_init__(self):
        self.points = [Vec2(point) for point in self.points]
        if not self.points:
            raise ValueError("a shape proxy needs at least one point")
        if len(self.points) > MAX_PROXY_POINTS:
            raise ValueError(
                f"a shape proxy takes at most {MAX_PROXY_POINTS} points, "
                f"got {len(self.points)}"
            )

    @classmethod
    def circle(cls, radius: float, center: VectorLike = (0, 0)) -> "ShapeProxy":
        """A circle: one point with a radius."""
        return cls(points=[Vec2(center)], radius=radius)

    @classmethod
    def capsule(
        cls, center1: VectorLike, center2: VectorLike, radius: float
    ) -> "ShapeProxy":
        """A capsule: the region within ``radius`` of the segment between two points."""
        return cls(points=[Vec2(center1), Vec2(center2)], radius=radius)

    @classmethod
    def segment(cls, point1: VectorLike, point2: VectorLike) -> "ShapeProxy":
        """A segment: a capsule with no radius."""
        return cls(points=[Vec2(point1), Vec2(point2)], radius=0.0)

    @classmethod
    def point(cls, position: VectorLike) -> "ShapeProxy":
        """A single point, for asking what is exactly here."""
        return cls(points=[Vec2(position)], radius=0.0)

    @classmethod
    def box(
        cls,
        width: float,
        height: float,
        center: VectorLike = (0, 0),
        rotation: float = 0.0,
    ) -> "ShapeProxy":
        """A box of the given full width and height, centred on ``center``.

        Args:
            width: Full width, matching :meth:`.Body.add_box`.
            height: Full height.
            center: Where the box's centre sits, in world coordinates.
            rotation: Rotation about the centre, in radians.
        """
        half_width, half_height = width / 2, height / 2
        cosine, sine = math.cos(rotation), math.sin(rotation)
        center = Vec2(center)
        corners = [
            (-half_width, -half_height),
            (half_width, -half_height),
            (half_width, half_height),
            (-half_width, half_height),
        ]
        return cls(
            points=[
                Vec2(
                    center.x + x * cosine - y * sine,
                    center.y + x * sine + y * cosine,
                )
                for x, y in corners
            ]
        )

    @classmethod
    def polygon(cls, points, radius: float = 0.0) -> "ShapeProxy":
        """The convex hull of the given points, in world coordinates.

        Box2D computes the hull itself, so the points need not be in order,
        but points inside the hull are dropped rather than making it concave.
        """
        return cls(points=list(points), radius=radius)

    @property
    def b2ShapeProxy(self):
        """This proxy as a C struct, owned by the returned cdata."""
        proxy = ffi.new("b2ShapeProxy*")
        for index, point in enumerate(self.points):
            proxy.points[index] = point.b2Vec2[0]
        proxy.count = len(self.points)
        proxy.radius = self.radius
        return proxy
