"""
Kinematic character movement.

A character controller usually does not want to be a dynamic body: it should
stop dead against a wall rather than bounce, climb a step without being tipped
over, and be moved by the player rather than by forces. Box2D 3.2 provides the
pieces for doing that yourself against the same collision data the solver uses.

The loop is: ask the world what a capsule would run into
(:meth:`.World.collide_mover`), work out the movement that satisfies all of
those at once (:func:`solve_planes`), and remove the parts of the velocity that
point into them (:func:`clip_vector`). :meth:`.World.cast_mover` is the
sweep-test counterpart, for questions like "how far can I fall before I land".

Nothing here moves anything. These are queries and geometry, so the character's
position is yours to keep and update.
"""

from dataclasses import dataclass
from typing import List

from ._box2d import ffi, lib
from .math import Vec2


@dataclass
class Plane:
    """A half-space: everything on the positive side of a line.

    Attributes:
        normal: Unit normal pointing out of the surface.
        offset: Signed distance from the origin along the normal.
    """

    normal: Vec2
    offset: float


@dataclass
class CollisionPlane:
    """One surface a mover is up against, and how hard it may push back.

    Attributes:
        plane: The surface itself.
        push_limit: How far this plane may push the mover, in metres. A large
            value makes it rigid; a small one lets the mover sink in, which is
            how soft or one-way surfaces are built.
        push: How far it actually pushed, filled in by :func:`solve_planes`.
        clip_velocity: Whether :func:`clip_vector` should remove velocity into
            this plane. False for soft planes, so the mover keeps its speed.
        shape: The shape this surface came from.
        point: Where the mover touched it.
    """

    plane: Plane
    push_limit: float = float("inf")
    push: float = 0.0
    clip_velocity: bool = True
    shape: "Shape" = None
    point: Vec2 = None

    @classmethod
    def _from_plane_result(cls, result, shape):
        return cls(
            plane=Plane(
                normal=Vec2(result.plane.normal.x, result.plane.normal.y),
                offset=result.plane.offset,
            ),
            point=Vec2(result.point.x, result.point.y),
            shape=shape,
        )

    def _to_b2(self, target):
        target.plane.normal = self.plane.normal.b2Vec2[0]
        target.plane.offset = self.plane.offset
        target.pushLimit = self.push_limit
        target.push = self.push
        target.clipVelocity = self.clip_velocity


@dataclass
class MoverResult:
    """What :func:`solve_planes` worked out.

    Attributes:
        translation: The movement that satisfies every plane. Add this to the
            mover's position.
        iterations: How many passes the solver took.
    """

    translation: Vec2
    iterations: int


def _pack_planes(planes):
    """Copy planes into a C array, keeping it alive for the caller."""
    array = ffi.new("b2CollisionPlane[]", max(len(planes), 1))
    for i, plane in enumerate(planes):
        plane._to_b2(array[i])
    return array


def solve_planes(target_delta, planes: List[CollisionPlane]) -> MoverResult:
    """Find the movement closest to the one asked for that clears every plane.

    Args:
        target_delta: The movement wanted, as a vector-like, ignoring obstacles.
        planes: What the mover is up against, from :meth:`.World.collide_mover`.

    Returns:
        MoverResult: The movement to actually apply. Each plane's ``push`` is
        updated in place, which is what :func:`clip_vector` then reads.

    Example:
        >>> world = World()
        >>> planes = world.collide_mover((0, 1), (0, 2), 0.5)
        >>> result = solve_planes((0.1, -0.2), planes)
    """
    array = _pack_planes(planes)
    result = lib.b2SolvePlanes(Vec2(target_delta).b2Vec2[0], array, len(planes))

    # The solver records how hard each plane pushed; carry that back so the
    # caller's planes can be handed straight to clip_vector.
    for i, plane in enumerate(planes):
        plane.push = array[i].push

    return MoverResult(
        translation=Vec2(result.translation.x, result.translation.y),
        iterations=result.iterationCount,
    )


def clip_vector(vector, planes: List[CollisionPlane]) -> Vec2:
    """Remove the parts of a vector that point into the given planes.

    Applied to velocity after :func:`solve_planes`, this is what stops a
    character accumulating speed into a wall it is already pressed against.
    Planes that did not push, or that set ``clip_velocity`` False, are ignored.

    Args:
        vector: The vector to clip, usually a velocity, as a vector-like.
        planes: The planes, after :func:`solve_planes` has filled in their push.

    Returns:
        Vec2: The clipped vector.
    """
    array = _pack_planes(planes)
    clipped = lib.b2ClipVector(Vec2(vector).b2Vec2[0], array, len(planes))
    return Vec2(clipped.x, clipped.y)
