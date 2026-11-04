"""
Joint definitions.

A joint definition bundles everything needed to create one joint, so that
adding a joint is one declarative object rather than a call with a dozen
keyword arguments. :meth:`.World.add_joint` takes any of these.

Every definition shares the fields in :class:`JointDef`: the two bodies, where
the joint attaches to each, and whether those bodies still collide. Anchors can
be given either as local points on each body, or as a single world-space
``anchor`` that is converted to both -- the common case when you know where the
pivot is but not each body's local frame.

Definitions have slots, so assigning a field one does not have -- a
misspelling, or a name from before a rename -- raises AttributeError
rather than being kept and never read.
"""

import math
from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Any, ClassVar, Optional, Type

from ._checked import lib
from .defdata import NON_NEGATIVE, ROUNDING, DefData, _f, _kinds, _short
from .math import Vec2, VectorLike

if TYPE_CHECKING:  # annotations only; these modules import this one
    from .body import Body
    from .joint import Joint


def _shortest_distance() -> float:
    """The lower limit a distance joint has until told otherwise."""
    from .joint import _distance_bounds

    return _distance_bounds()[0]


def _reference_angle(joint: "Joint") -> float:
    """The angle body_b rests at turned from body_a: what Box2D 3.2 keeps as
    the difference between the two local frames' rotations."""
    angle = joint.local_frame_a.q.angle - joint.local_frame_b.q.angle
    # A difference of two stored angles, so with both their roundings.
    return _short(math.remainder(angle, math.tau), ROUNDING)


def _axis(joint: "Joint") -> Vec2:
    """A sliding joint's axis, which Box2D 3.2 keeps as frame A's rotation."""
    rotation = joint.local_frame_a.q
    return Vec2(_short(rotation.c, ROUNDING), _short(rotation.s, ROUNDING))


@dataclass(slots=True, repr=False, eq=False)
class JointDef(DefData):
    """Fields common to every joint.

    Attributes:
        body_a: The first body to connect.
        body_b: The second body to connect.
        local_anchor_a: Attachment point in body_a's local coordinates.
            Defaults to the body's origin.
        local_anchor_b: Attachment point in body_b's local coordinates.
            Defaults to the body's origin.
        anchor: A world-space point converted into both local anchors. Give
            this or the local anchors, not both.
        collide_connected: Whether the two bodies keep colliding with each other.
    """

    body_a: "Body"
    body_b: "Body"
    local_anchor_a: Optional[VectorLike] = None
    local_anchor_b: Optional[VectorLike] = None
    anchor: Optional[VectorLike] = None
    collide_connected: bool = False

    #: The Joint subclass this definition builds. Set by each subclass.
    joint_class: ClassVar[Optional[Type["Joint"]]] = None

    def resolved_anchors(self) -> tuple[Optional[VectorLike], Optional[VectorLike]]:
        """Return the local anchors, converting a world anchor if one was given.

        Raises:
            ValueError: If both a world anchor and local anchors were given,
                since there is no sensible way to honour both.
        """
        if self.anchor is None:
            return self.local_anchor_a, self.local_anchor_b

        if self.local_anchor_a is not None or self.local_anchor_b is not None:
            raise ValueError(
                "Give either 'anchor' or the local anchors, not both: a world "
                "anchor already determines where the joint attaches to each body."
            )
        return (
            self.body_a.transform.inverse(self.anchor),
            self.body_b.transform.inverse(self.anchor),
        )

    def joint_arguments(self) -> dict[str, Any]:
        """The keyword arguments for this definition's joint class.

        'anchor' is resolved away here, so joints only ever see local anchors.
        """
        # A field left as None means "not specified", so it is omitted and the
        # joint's own default applies -- the same rule World.add_body follows.
        arguments = {
            field.name: getattr(self, field.name)
            for field in fields(self)
            if field.name != "anchor" and getattr(self, field.name) is not None
        }
        # An unspecified anchor means the body's own origin. Saying so here
        # keeps every joint class from having to decide separately.
        anchor_a, anchor_b = self.resolved_anchors()
        arguments["local_anchor_a"] = (0, 0) if anchor_a is None else anchor_a
        arguments["local_anchor_b"] = (0, 0) if anchor_b is None else anchor_b
        return arguments

    _table = {
        "body_a": _f("body", c="base.bodyIdA"),
        "body_b": _f("body", c="base.bodyIdB"),
        "local_anchor_a": _f("vec2", "m", default=(0, 0), c="base.localFrameA.p"),
        "local_anchor_b": _f("vec2", "m", default=(0, 0), c="base.localFrameB.p"),
        "collide_connected": _f("bool", c="base.collideConnected"),
    }

    def _written_values(self, full: bool) -> dict[str, Any]:
        # A world anchor is the local anchors said another way, and a
        # dictionary holds those.
        values = self._data_values(full)
        values["local_anchor_a"], values["local_anchor_b"] = self.resolved_anchors()
        return values


@dataclass(slots=True, repr=False, eq=False)
class FilterJointDef(JointDef):
    """Stops two bodies colliding without constraining them otherwise.

    Anchors and collide_connected are ignored: this joint has no geometry and
    exists precisely to prevent the collision the flag would re-enable.
    """

    def joint_arguments(self) -> dict[str, Any]:
        """Only the bodies: this joint has no anchors or other settings."""
        return {"body_a": self.body_a, "body_b": self.body_b}

    kind: ClassVar[Optional[str]] = "filter"
    _c_struct = "b2FilterJointDef"
    # It has no geometry, and the flag would undo what it is for.
    _table = {
        "local_anchor_a": None,
        "local_anchor_b": None,
        "collide_connected": None,
    }

    def _written_values(self, full: bool) -> dict[str, Any]:
        return self._data_values(full)


@dataclass(slots=True, repr=False, eq=False)
class WeldJointDef(JointDef):
    """Holds two bodies rigidly together, optionally with some give.

    Attributes:
        linear_hertz: Frequency of the linear softness; 0 welds rigidly.
        linear_damping_ratio: Damping of the linear softness.
        angular_hertz: Frequency of the angular softness; 0 welds rigidly.
        angular_damping_ratio: Damping of the angular softness.
        reference_angle: Angle between the bodies at which the joint rests.
    """

    linear_hertz: Optional[float] = None
    linear_damping_ratio: Optional[float] = None
    angular_hertz: Optional[float] = None
    angular_damping_ratio: Optional[float] = None
    reference_angle: Optional[float] = None

    kind: ClassVar[Optional[str]] = "weld"
    _c_struct = "b2WeldJointDef"
    _table = {
        "linear_hertz": _f("float", "Hz", NON_NEGATIVE, c="linearHertz"),
        "linear_damping_ratio": _f("float", range=NON_NEGATIVE, c="linearDampingRatio"),
        "angular_hertz": _f("float", "Hz", NON_NEGATIVE, c="angularHertz"),
        "angular_damping_ratio": _f(
            "float", range=NON_NEGATIVE, c="angularDampingRatio"
        ),
        "reference_angle": _f("angle", "rad", live=_reference_angle, default=0.0),
    }


@dataclass(slots=True, repr=False, eq=False)
class RevoluteJointDef(JointDef):
    """Pins two bodies together at a point and lets them rotate about it.

    Attributes:
        lower_limit: Lower limit of rotation in radians.
        upper_limit: Upper limit of rotation in radians.
        enable_limit: Whether the angle limits are enforced.
        target_motor_speed: The speed the motor drives towards, in radians per
            second.
        max_motor_torque: Torque the motor may apply, in newton-metres.
        enable_motor: Whether the motor drives the joint.
        reference_angle: Angle between the bodies at which the joint rests.
        enable_spring: Whether a spring pulls the joint towards target_angle.
        spring_hertz: Spring frequency.
        spring_damping_ratio: Spring damping ratio.
        target_angle: The angle the spring pulls towards, in radians.
    """

    lower_limit: Optional[float] = None
    upper_limit: Optional[float] = None
    enable_limit: Optional[bool] = None
    target_motor_speed: Optional[float] = None
    max_motor_torque: Optional[float] = None
    enable_motor: Optional[bool] = None
    reference_angle: Optional[float] = None
    enable_spring: Optional[bool] = None
    spring_hertz: Optional[float] = None
    spring_damping_ratio: Optional[float] = None
    target_angle: Optional[float] = None

    kind: ClassVar[Optional[str]] = "revolute"
    _c_struct = "b2RevoluteJointDef"
    _table = {
        "lower_limit": _f("float", "rad", c="lowerAngle"),
        "upper_limit": _f("float", "rad", c="upperAngle"),
        "enable_limit": _f("bool", c="enableLimit"),
        "target_motor_speed": _f("float", "rad/s", c="motorSpeed"),
        "max_motor_torque": _f("float", "N*m", NON_NEGATIVE, c="maxMotorTorque"),
        "enable_motor": _f("bool", c="enableMotor"),
        "reference_angle": _f("angle", "rad", live=_reference_angle, default=0.0),
        "enable_spring": _f("bool", c="enableSpring"),
        "spring_hertz": _f("float", "Hz", NON_NEGATIVE, c="hertz"),
        "spring_damping_ratio": _f("float", range=NON_NEGATIVE, c="dampingRatio"),
        "target_angle": _f("float", "rad", c="targetAngle"),
    }


@dataclass(slots=True, repr=False, eq=False)
class PrismaticJointDef(JointDef):
    """Lets two bodies slide along one axis without rotating.

    Attributes:
        axis: The sliding axis, in body_a's local coordinates. Defaults to (1, 0).
        lower_limit: Lower translation limit.
        upper_limit: Upper translation limit.
        enable_limit: Whether the translation limits are enforced.
        target_motor_speed: The speed the motor drives towards.
        max_motor_force: Force the motor may apply, in newtons.
        enable_motor: Whether the motor drives the joint.
        reference_angle: The angle body_b is held at relative to body_a,
            body_b's angle less body_a's, in radians. Defaults to 0, which
            turns the bodies to the same angle.
        enable_spring: Whether a spring pulls the joint toward its rest length.
        spring_hertz: Spring frequency.
        spring_damping_ratio: Spring damping ratio.
        target_translation: Where along the axis the spring pulls towards.
    """

    axis: VectorLike = (1, 0)
    lower_limit: Optional[float] = None
    upper_limit: Optional[float] = None
    enable_limit: Optional[bool] = None
    target_motor_speed: Optional[float] = None
    max_motor_force: Optional[float] = None
    enable_motor: Optional[bool] = None
    reference_angle: Optional[float] = None
    enable_spring: Optional[bool] = None
    spring_hertz: Optional[float] = None
    spring_damping_ratio: Optional[float] = None
    target_translation: Optional[float] = None

    kind: ClassVar[Optional[str]] = "prismatic"
    _c_struct = "b2PrismaticJointDef"
    _table = {
        "axis": _f("vec2", live=_axis),
        "lower_limit": _f("float", "m", c="lowerTranslation"),
        "upper_limit": _f("float", "m", c="upperTranslation"),
        "enable_limit": _f("bool", c="enableLimit"),
        "target_motor_speed": _f("float", "m/s", c="motorSpeed"),
        "max_motor_force": _f("float", "N", NON_NEGATIVE, c="maxMotorForce"),
        "enable_motor": _f("bool", c="enableMotor"),
        "reference_angle": _f("angle", "rad", live=_reference_angle, default=0.0),
        "enable_spring": _f("bool", c="enableSpring"),
        "spring_hertz": _f("float", "Hz", NON_NEGATIVE, c="hertz"),
        "spring_damping_ratio": _f("float", range=NON_NEGATIVE, c="dampingRatio"),
        "target_translation": _f("float", "m", c="targetTranslation"),
    }


@dataclass(slots=True, repr=False, eq=False)
class WheelJointDef(JointDef):
    """A sliding axis with a spring, as between a chassis and a wheel.

    A field left None takes Box2D's default: the spring is on, at 1 Hz and a
    damping ratio of 0.7, and the limit and motor are off. With the spring
    turned off, or at 0 Hz, nothing but the limits holds the wheel along the
    axis.

    Attributes:
        axis: The suspension axis, in body_a's local coordinates. Defaults to (1, 0).
        enable_limit: Whether the translation limits are enforced.
        lower_limit: Lower translation limit.
        upper_limit: Upper translation limit.
        enable_motor: Whether the motor drives the joint.
        target_motor_speed: The speed the motor drives towards, in radians per
            second.
        max_motor_torque: Torque the motor may apply.
        enable_spring: Whether the suspension spring is active. On by default.
        spring_hertz: Spring frequency. 1 Hz by default.
        spring_damping_ratio: Spring damping ratio. 0.7 by default.
    """

    axis: VectorLike = (1, 0)
    enable_limit: Optional[bool] = None
    lower_limit: Optional[float] = None
    upper_limit: Optional[float] = None
    enable_motor: Optional[bool] = None
    target_motor_speed: Optional[float] = None
    max_motor_torque: Optional[float] = None
    enable_spring: Optional[bool] = None
    spring_hertz: Optional[float] = None
    spring_damping_ratio: Optional[float] = None

    kind: ClassVar[Optional[str]] = "wheel"
    _c_struct = "b2WheelJointDef"
    _table = {
        "axis": _f("vec2", live=_axis),
        "enable_limit": _f("bool", c="enableLimit"),
        "lower_limit": _f("float", "m", c="lowerTranslation"),
        "upper_limit": _f("float", "m", c="upperTranslation"),
        "enable_motor": _f("bool", c="enableMotor"),
        "target_motor_speed": _f("float", "rad/s", c="motorSpeed"),
        "max_motor_torque": _f("float", "N*m", NON_NEGATIVE, c="maxMotorTorque"),
        "enable_spring": _f("bool", c="enableSpring"),
        "spring_hertz": _f("float", "Hz", NON_NEGATIVE, c="hertz"),
        "spring_damping_ratio": _f("float", range=NON_NEGATIVE, c="dampingRatio"),
    }


@dataclass(slots=True, repr=False, eq=False)
class DistanceJointDef(JointDef):
    """Keeps two points a fixed distance apart, optionally springy.

    Attributes:
        rest_length: The rest length between the anchors. If None, how far
            apart the anchors are in the world when the joint is made, so it
            holds the bodies where they are. This is box2d-py's default, not
            Box2D's, which is 1 m wherever the anchors are and so pulls bodies
            set out at any other distance together, or apart, on the first
            step.
        lower_limit: Lower length limit.
        upper_limit: Upper length limit.
        enable_limit: Whether the length limits are enforced.
        enable_spring: Whether the joint behaves as a spring rather than a rod.
        spring_hertz: Spring frequency.
        spring_damping_ratio: Spring damping ratio.
        enable_motor: Whether the motor drives the length.
        target_motor_speed: The speed the motor drives towards.
        max_motor_force: Force the motor may apply, in newtons.
        lower_spring_force: Most the spring may pull, as a negative force in
            newtons. At zero it only pushes, like a strut.
        upper_spring_force: Most the spring may push. At zero it only pulls,
            like a rope.
    """

    rest_length: Optional[float] = None
    lower_limit: Optional[float] = None
    upper_limit: Optional[float] = None
    enable_limit: Optional[bool] = None
    enable_spring: Optional[bool] = None
    spring_hertz: Optional[float] = None
    spring_damping_ratio: Optional[float] = None
    enable_motor: Optional[bool] = None
    target_motor_speed: Optional[float] = None
    max_motor_force: Optional[float] = None
    lower_spring_force: Optional[float] = None
    upper_spring_force: Optional[float] = None

    kind: ClassVar[Optional[str]] = "distance"
    _c_struct = "b2DistanceJointDef"
    _table = {
        # Left out, the distance between the anchors when the joint is made.
        "rest_length": _f("float", "m", NON_NEGATIVE, default=None, c="length"),
        # Box2D's is 0, but it holds a distance joint's lengths to its slop.
        "lower_limit": _f(
            "float", "m", NON_NEGATIVE, default=_shortest_distance, c="minLength"
        ),
        "upper_limit": _f("float", "m", NON_NEGATIVE, c="maxLength"),
        "enable_limit": _f("bool", c="enableLimit"),
        "enable_spring": _f("bool", c="enableSpring"),
        "spring_hertz": _f("float", "Hz", NON_NEGATIVE, c="hertz"),
        "spring_damping_ratio": _f("float", range=NON_NEGATIVE, c="dampingRatio"),
        "enable_motor": _f("bool", c="enableMotor"),
        "target_motor_speed": _f("float", "m/s", c="motorSpeed"),
        "max_motor_force": _f("float", "N", NON_NEGATIVE, c="maxMotorForce"),
        "lower_spring_force": _f("float", "N", c="lowerSpringForce"),
        "upper_spring_force": _f("float", "N", c="upperSpringForce"),
    }


@dataclass(slots=True, repr=False, eq=False)
class MotorJointDef(JointDef):
    """Drives the relative motion of two bodies.

    Box2D 3.2 rewrote this joint around velocities and springs. To pull a body
    toward a world point, use :class:`.MouseJointDef` instead.

    Attributes:
        linear_velocity: Desired relative linear velocity.
        angular_velocity: Desired relative angular velocity in radians/second.
        max_velocity_force: Force cap for the linear velocity drive.
        max_velocity_torque: Torque cap for the angular velocity drive.
        linear_hertz: Linear spring frequency; 0 disables the spring.
        linear_damping_ratio: Linear spring damping ratio.
        max_spring_force: Force cap for the linear spring.
        angular_hertz: Angular spring frequency; 0 disables the spring.
        angular_damping_ratio: Angular spring damping ratio.
        max_spring_torque: Torque cap for the angular spring.
    """

    linear_velocity: Optional[VectorLike] = None
    angular_velocity: Optional[float] = None
    max_velocity_force: Optional[float] = None
    max_velocity_torque: Optional[float] = None
    linear_hertz: Optional[float] = None
    linear_damping_ratio: Optional[float] = None
    max_spring_force: Optional[float] = None
    angular_hertz: Optional[float] = None
    angular_damping_ratio: Optional[float] = None
    max_spring_torque: Optional[float] = None

    def joint_arguments(self) -> dict[str, Any]:
        """The motor joint attaches at the bodies' origins, so it has no anchors."""
        # super() with arguments: slots=True makes a new class that a bare
        # super() in a method of the old one cannot see before Python 3.14.
        arguments = super(MotorJointDef, self).joint_arguments()
        arguments.pop("local_anchor_a", None)
        arguments.pop("local_anchor_b", None)
        return arguments

    kind: ClassVar[Optional[str]] = "motor"
    _c_struct = "b2MotorJointDef"
    _table = {
        "linear_velocity": _f("vec2", "m/s", c="linearVelocity"),
        "angular_velocity": _f("float", "rad/s", c="angularVelocity"),
        "max_velocity_force": _f("float", "N", NON_NEGATIVE, c="maxVelocityForce"),
        "max_velocity_torque": _f("float", "N*m", NON_NEGATIVE, c="maxVelocityTorque"),
        "linear_hertz": _f("float", "Hz", NON_NEGATIVE, c="linearHertz"),
        "linear_damping_ratio": _f("float", range=NON_NEGATIVE, c="linearDampingRatio"),
        "max_spring_force": _f("float", "N", NON_NEGATIVE, c="maxSpringForce"),
        "angular_hertz": _f("float", "Hz", NON_NEGATIVE, c="angularHertz"),
        "angular_damping_ratio": _f(
            "float", range=NON_NEGATIVE, c="angularDampingRatio"
        ),
        "max_spring_torque": _f("float", "N*m", NON_NEGATIVE, c="maxSpringTorque"),
    }


@dataclass(slots=True, repr=False, eq=False)
class MoverJointDef(JointDef):
    """Drives a dynamic character body at a commanded velocity.

    See :class:`.MoverJoint`. body_a is the reference, usually static, and
    body_b the character.

    Attributes:
        linear_velocity: Desired velocity of body_b relative to body_a.
        max_velocity_force: Force cap for each axis, as a vector-like. An axis
            with zero force is not driven.
    """

    linear_velocity: Optional[VectorLike] = None
    max_velocity_force: Optional[VectorLike] = None

    def joint_arguments(self) -> dict[str, Any]:
        """The mover joint drives velocity only, so it has no anchors."""
        # super() with arguments: slots=True makes a new class that a bare
        # super() in a method of the old one cannot see before Python 3.14.
        arguments = super(MoverJointDef, self).joint_arguments()
        arguments.pop("local_anchor_a", None)
        arguments.pop("local_anchor_b", None)
        return arguments

    kind: ClassVar[Optional[str]] = "mover"
    _c_struct = "b2MoverJointDef"
    _table = {
        "linear_velocity": _f("vec2", "m/s", c="linearVelocity"),
        "max_velocity_force": _f("vec2", "N", c="maxVelocityForce"),
    }


@dataclass(slots=True, repr=False, eq=False)
class PogoJointDef(JointDef):
    """A spring holding a character up off the ground. See :class:`.PogoJoint`.

    body_a is the ground and body_b the character. local_anchor_a is where the
    spring touches the ground and local_anchor_b where it meets the character.

    Attributes:
        normal: The ground normal at the contact, in world coordinates.
            Defaults to straight up, (0, 1). This is box2d-py's default, not
            Box2D's: Box2D's is (0, 0), along which the spring pushes nowhere,
            so the joint would do nothing, and box2d-py refuses a zero normal.
        spring_hertz: Spring frequency.
        spring_damping_ratio: Spring damping ratio.
        rest_length: Length the spring settles at.
        max_tension_force: How hard the spring may pull the character down.
        max_compression_force: How hard the spring may push the character up.
        impulse: Starting impulse, from the previous step's pogo.
        velocity: Starting spring velocity, from the previous step's pogo.
    """

    normal: Optional[VectorLike] = None
    spring_hertz: Optional[float] = None
    spring_damping_ratio: Optional[float] = None
    rest_length: Optional[float] = None
    max_tension_force: Optional[float] = None
    max_compression_force: Optional[float] = None
    impulse: Optional[float] = None
    velocity: Optional[float] = None

    kind: ClassVar[Optional[str]] = "pogo"
    # Box2D has no functions reading these back but the impulse.
    _c_struct = "b2PogoJointDef"
    _table = {
        "normal": _f("vec2", live=None, default=(0, 1), c="normal"),
        "spring_hertz": _f("float", "Hz", NON_NEGATIVE, c="hertz"),
        "spring_damping_ratio": _f("float", range=NON_NEGATIVE, c="dampingRatio"),
        "rest_length": _f("float", "m", NON_NEGATIVE, c="restLength"),
        "max_tension_force": _f(
            "float",
            "N",
            NON_NEGATIVE,
            live=None,
            default=lambda: lib.b2DefaultPogoJointDef().maxTensionForce,
            c="maxTensionForce",
        ),
        "max_compression_force": _f(
            "float",
            "N",
            NON_NEGATIVE,
            live=None,
            default=lambda: lib.b2DefaultPogoJointDef().maxCompressionForce,
            c="maxCompressionForce",
        ),
        "impulse": _f("float", "N*s", c="impulse"),
        "velocity": _f(
            "float",
            "m/s",
            live=None,
            default=lambda: lib.b2DefaultPogoJointDef().velocity,
            c="velocity",
        ),
    }


@dataclass(slots=True, repr=False, eq=False)
class MouseJointDef(DefData):
    """Drags one body toward a moving world-space target.

    Unlike the other definitions this connects a single body to a point rather
    than two bodies together, so it does not share :class:`JointDef`'s fields.

    The joint it makes adds a kinematic proxy body to the world; see
    :class:`.MouseJoint`. Box2D 3.2 has no mouse joint, and so no default
    definition for one: these defaults are box2d-py's own.

    Attributes:
        body: The body to drag.
        target: The world position to pull toward.
        max_force: Maximum force available to move the body.
        damping_ratio: Spring damping ratio.
        hertz: Spring frequency, controlling how stiffly the body follows.
    """

    body: "Body"
    target: VectorLike
    max_force: float = 1000.0
    damping_ratio: float = 0.7
    hertz: float = 5.0

    joint_class: ClassVar[Optional[Type["Joint"]]] = None

    def joint_arguments(self) -> dict[str, Any]:
        """Every field that is set; a mouse joint has no anchors to resolve."""
        return {
            field.name: getattr(self, field.name)
            for field in fields(self)
            if getattr(self, field.name) is not None
        }

    kind: ClassVar[Optional[str]] = "mouse"
    _table = {
        # The joint's body_a is its proxy, and body_b the body dragged.
        "body": _f("body", live="body_b"),
        "target": _f("vec2", "m"),
        "max_force": _f("float", "N", NON_NEGATIVE),
        "damping_ratio": _f("float", range=NON_NEGATIVE),
        "hertz": _f("float", "Hz", NON_NEGATIVE),
    }


def _definition_for(joint_class: type) -> Any:
    """The definition class that makes ``joint_class``, or a base of it."""
    for klass in joint_class.__mro__:
        for definition in _kinds.values():
            if getattr(definition, "joint_class", None) is klass:
                return definition
    raise TypeError(f"{joint_class.__name__} has no definition")


# Bound at import time rather than in each class body: jointdef must not import
# joint at module level, since joint imports math and world imports both.
def _bind_joint_classes() -> None:
    from . import joint

    for definition, name in (
        (FilterJointDef, "FilterJoint"),
        (WeldJointDef, "WeldJoint"),
        (RevoluteJointDef, "RevoluteJoint"),
        (PrismaticJointDef, "PrismaticJoint"),
        (WheelJointDef, "WheelJoint"),
        (DistanceJointDef, "DistanceJoint"),
        (MotorJointDef, "MotorJoint"),
        (MoverJointDef, "MoverJoint"),
        (PogoJointDef, "PogoJoint"),
        (MouseJointDef, "MouseJoint"),
    ):
        definition.joint_class = getattr(joint, name)


_bind_joint_classes()
