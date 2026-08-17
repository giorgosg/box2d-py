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
"""

from dataclasses import dataclass, fields
from typing import Optional

from .math import VectorLike


@dataclass
class JointDef:
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
    joint_class = None

    def resolved_anchors(self):
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

    def joint_arguments(self):
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


@dataclass
class FilterJointDef(JointDef):
    """Stops two bodies colliding without constraining them otherwise.

    Anchors and collide_connected are ignored: this joint has no geometry and
    exists precisely to prevent the collision the flag would re-enable.
    """

    def joint_arguments(self):
        return {"body_a": self.body_a, "body_b": self.body_b}


@dataclass
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


@dataclass
class RevoluteJointDef(JointDef):
    """Pins two bodies together at a point and lets them rotate about it.

    Attributes:
        lower_angle: Lower limit of rotation in radians.
        upper_angle: Upper limit of rotation in radians.
        enable_limit: Whether the angle limits are enforced.
        motor_speed: Desired motor speed in radians per second.
        max_motor_torque: Torque the motor may apply, in newton-metres.
        enable_motor: Whether the motor drives the joint.
        reference_angle: Angle between the bodies at which the joint rests.
        enable_spring: Whether a spring pulls the joint towards target_angle.
        hertz: Spring frequency.
        damping_ratio: Spring damping ratio.
        target_angle: The angle the spring pulls towards, in radians.
    """

    lower_angle: Optional[float] = None
    upper_angle: Optional[float] = None
    enable_limit: Optional[bool] = None
    motor_speed: Optional[float] = None
    max_motor_torque: Optional[float] = None
    enable_motor: Optional[bool] = None
    reference_angle: Optional[float] = None
    enable_spring: Optional[bool] = None
    hertz: Optional[float] = None
    damping_ratio: Optional[float] = None
    target_angle: Optional[float] = None


@dataclass
class PrismaticJointDef(JointDef):
    """Lets two bodies slide along one axis without rotating.

    Attributes:
        axis: The sliding axis, in body_a's local coordinates. Defaults to (1, 0).
        lower_limit: Lower translation limit.
        upper_limit: Upper translation limit.
        enable_limit: Whether the translation limits are enforced.
        motor_speed: Desired motor speed.
        max_motor_force: Force the motor may apply, in newtons.
        enable_motor: Whether the motor drives the joint.
        reference_angle: Not supported since Box2D 3.2, where the axis owns the
            joint frame's rotation. Passing it raises.
        enable_spring: Whether a spring pulls the joint toward its rest length.
        hertz: Spring frequency.
        damping_ratio: Spring damping ratio.
        target_translation: Where along the axis the spring pulls towards.
    """

    axis: VectorLike = (1, 0)
    lower_limit: Optional[float] = None
    upper_limit: Optional[float] = None
    enable_limit: Optional[bool] = None
    motor_speed: Optional[float] = None
    max_motor_force: Optional[float] = None
    enable_motor: Optional[bool] = None
    reference_angle: Optional[float] = None
    enable_spring: Optional[bool] = None
    hertz: Optional[float] = None
    damping_ratio: Optional[float] = None
    target_translation: Optional[float] = None


@dataclass
class WheelJointDef(JointDef):
    """A sliding axis with a spring, as between a chassis and a wheel.

    Attributes:
        axis: The suspension axis, in body_a's local coordinates. Defaults to (1, 0).
        enable_limit: Whether the translation limits are enforced.
        lower_translation: Lower translation limit.
        upper_translation: Upper translation limit.
        enable_motor: Whether the motor drives the joint.
        motor_speed: Desired motor speed in radians per second.
        max_motor_torque: Torque the motor may apply.
        enable_spring: Whether the suspension spring is active.
        spring_hertz: Spring frequency.
        spring_damping_ratio: Spring damping ratio.
    """

    axis: VectorLike = (1, 0)
    enable_limit: Optional[bool] = None
    lower_translation: Optional[float] = None
    upper_translation: Optional[float] = None
    enable_motor: Optional[bool] = None
    motor_speed: Optional[float] = None
    max_motor_torque: Optional[float] = None
    enable_spring: Optional[bool] = None
    spring_hertz: Optional[float] = None
    spring_damping_ratio: Optional[float] = None


@dataclass
class DistanceJointDef(JointDef):
    """Keeps two points a fixed distance apart, optionally springy.

    Attributes:
        length: The rest length between the anchors.
        min_length: Lower length limit.
        max_length: Upper length limit.
        enable_limit: Whether the length limits are enforced.
        enable_spring: Whether the joint behaves as a spring rather than a rod.
        hertz: Spring frequency.
        damping_ratio: Spring damping ratio.
        enable_motor: Whether the motor drives the length.
        motor_speed: Desired motor speed.
        max_motor_force: Force the motor may apply, in newtons.
        lower_spring_force: Most the spring may push, in newtons.
        upper_spring_force: Most the spring may pull. Clamping either at zero
            turns the spring into a rope or a strut.
    """

    length: Optional[float] = None
    min_length: Optional[float] = None
    max_length: Optional[float] = None
    enable_limit: Optional[bool] = None
    enable_spring: Optional[bool] = None
    hertz: Optional[float] = None
    damping_ratio: Optional[float] = None
    enable_motor: Optional[bool] = None
    motor_speed: Optional[float] = None
    max_motor_force: Optional[float] = None
    lower_spring_force: Optional[float] = None
    upper_spring_force: Optional[float] = None


@dataclass
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

    def joint_arguments(self):
        """The motor joint attaches at the bodies' origins, so it has no anchors."""
        arguments = super().joint_arguments()
        arguments.pop("local_anchor_a", None)
        arguments.pop("local_anchor_b", None)
        return arguments


@dataclass
class MouseJointDef:
    """Drags one body toward a moving world-space target.

    Unlike the other definitions this connects a single body to a point rather
    than two bodies together, so it does not share :class:`JointDef`'s fields.

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

    joint_class = None

    def joint_arguments(self):
        return {
            field.name: getattr(self, field.name)
            for field in fields(self)
            if getattr(self, field.name) is not None
        }


# Bound at import time rather than in each class body: jointdef must not import
# joint at module level, since joint imports math and world imports both.
def _bind_joint_classes():
    from . import joint

    for definition, name in (
        (FilterJointDef, "FilterJoint"),
        (WeldJointDef, "WeldJoint"),
        (RevoluteJointDef, "RevoluteJoint"),
        (PrismaticJointDef, "PrismaticJoint"),
        (WheelJointDef, "WheelJoint"),
        (DistanceJointDef, "DistanceJoint"),
        (MotorJointDef, "MotorJoint"),
        (MouseJointDef, "MouseJoint"),
    ):
        definition.joint_class = getattr(joint, name)


_bind_joint_classes()
