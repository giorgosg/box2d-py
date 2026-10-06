from .world import World, HAS_THREADS, HAS_AVX2, BOX2D_VERSION
from .math import Vec2, Rot, Transform, AABB, Mat22, ScaledTransform
from .body import Body, BodyBuilder
from .dataclasses import BodyType
from .shape import Box, Capsule, Chain, ChainSegment, Circle, Polygon, Segment, Shape
from .joint import (
    Joint,
    DistanceJoint,
    FilterJoint,
    MotorJoint,
    MouseJoint,
    MoverJoint,
    PogoJoint,
    PrismaticJoint,
    RevoluteJoint,
    WeldJoint,
    WheelJoint,
)
from .debug_draw import DebugDraw, Color
from .collision_filter import CollisionFilter, CollisionCategoryRegistry
from .events import (
    BodyMoveEvent,
    Contact,
    ContactBeginEvent,
    ContactEndEvent,
    ContactEvents,
    ContactHitEvent,
    JointEvent,
)
from .mover import (
    CollisionPlane,
    MoverResult,
    Plane,
    clip_vector,
    solve_planes,
)
from .query import MAX_PROXY_POINTS, ShapeProxy
from .diagnostics import Counters, Profile
from .jointdef import (
    JointDef,
    FilterJointDef,
    WeldJointDef,
    RevoluteJointDef,
    PrismaticJointDef,
    WheelJointDef,
    DistanceJointDef,
    MotorJointDef,
    MoverJointDef,
    PogoJointDef,
    MouseJointDef,
)
from .lifetime import DestroyedError
from ._checked import InvalidInputError

__all__ = [
    # world
    "World",
    "HAS_THREADS",
    "HAS_AVX2",
    "BOX2D_VERSION",
    # math
    "Vec2",
    "Rot",
    "Transform",
    "AABB",
    "Mat22",
    "ScaledTransform",
    # bodies and shapes
    "Body",
    "BodyBuilder",
    "BodyType",
    "Shape",
    "Box",
    "Capsule",
    "Chain",
    "ChainSegment",
    "Circle",
    "Polygon",
    "Segment",
    "CollisionFilter",
    "CollisionCategoryRegistry",
    # joints
    "Joint",
    "DistanceJoint",
    "FilterJoint",
    "MotorJoint",
    "MouseJoint",
    "MoverJoint",
    "PogoJoint",
    "PrismaticJoint",
    "RevoluteJoint",
    "WeldJoint",
    "WheelJoint",
    "JointDef",
    "DistanceJointDef",
    "FilterJointDef",
    "MotorJointDef",
    "MouseJointDef",
    "MoverJointDef",
    "PogoJointDef",
    "PrismaticJointDef",
    "RevoluteJointDef",
    "WeldJointDef",
    "WheelJointDef",
    # events
    "BodyMoveEvent",
    "Contact",
    "ContactBeginEvent",
    "ContactEndEvent",
    "ContactEvents",
    "ContactHitEvent",
    "JointEvent",
    # character movement
    "CollisionPlane",
    "MoverResult",
    "Plane",
    "clip_vector",
    "solve_planes",
    # queries, drawing, diagnostics
    "MAX_PROXY_POINTS",
    "ShapeProxy",
    "DebugDraw",
    "Color",
    "Counters",
    "Profile",
    # errors
    "DestroyedError",
    "InvalidInputError",
]
