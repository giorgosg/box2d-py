"""
A jointed human figure, for ragdoll scenarios.

Eleven capsule bones hung off a hip, each pinned to its parent by a revolute
joint with an angle limit, a friction motor and an optional spring. That is
enough structure to fall convincingly: the limits stop limbs bending the wrong
way, the motors give joints something to work against so the figure does not
flail, and the spring pulls it back towards its rest pose.

Ported from Box2D's ``shared/human.c``. The C version writes each bone out in
full, eleven times over; here the measurements are a table and one loop builds
them, since the bones differ only in their numbers.

``set_scale`` resizes a figure in place, rewriting every shape and joint
frame, which is what the Scale Ragdoll scenario drags its slider on.
"""

import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional, Tuple

from box2d import CollisionFilter, RevoluteJointDef, Vec2
from box2d.shapedef import CapsuleDef, PolygonDef

if TYPE_CHECKING:  # only for the annotations below
    from box2d import Body, RevoluteJoint

# Box2D's own palette, so a colorized figure looks like the C++ samples.
SHIRT_COLOR = 0x48D1CC  # medium turquoise
PANT_COLOR = 0x1E90FF  # dodger blue
FOOT_COLOR = 0x8B4513  # saddle brown
SKIN_COLORS = (
    0xFFDEAD,
    0xFFFFE0,
    0xCD853F,
    0xD2B48C,
)  # navajo white, light yellow, peru, tan

#: Bones collide with the world (1) and with other humans (2), but a human's
#: own bones never collide with each other -- that is the negative group.
BONE_CATEGORY = 2
BONE_MASK = 1 | 2
#: Feet skip category 2, so a pile of ragdolls does not catch on each others' feet.
FOOT_MASK = 1


@dataclass(frozen=True)
class BoneDef:
    """One bone's measurements, as multiples of the figure's scale.

    Attributes:
        name: The bone's name, which debug draw can show.
        parent: The bone this one hangs from, or None for the root.
        y: Height of the body's origin above the spawn point.
        center1: Lower end of the capsule, relative to the body origin.
        center2: Upper end of the capsule.
        radius: Capsule radius.
        pivot_y: Height of the joint with the parent.
        limits: Lower and upper angle, in radians.
        friction_scale: How much of the figure's friction torque this joint
            gets. A head resists turning far less than a hip does.
        linear_damping: Damping on the body itself.
        color: Shirt, pant or skin.
        has_foot: Whether the foot polygon is attached to this bone.
    """

    name: str
    parent: Optional[str]
    y: float
    center1: Tuple[float, float]
    center2: Tuple[float, float]
    radius: float
    pivot_y: float = 0.0
    limits: Tuple[float, float] = (0.0, 0.0)
    friction_scale: float = 1.0
    linear_damping: float = 0.0
    color: str = "pant"
    has_foot: bool = False


PI = math.pi

#: The figure, from the hip outwards. Parents are built before their children,
#: which the loop in Human.spawn relies on.
BONES: Tuple[BoneDef, ...] = (
    BoneDef("hip", None, 0.95, (0, -0.02), (0, 0.02), 0.095, color="pant"),
    BoneDef(
        "torso",
        "hip",
        1.2,
        (0, -0.135),
        (0, 0.135),
        0.09,
        pivot_y=1.0,
        limits=(-0.25 * PI, 0.0),
        friction_scale=0.5,
        color="shirt",
    ),
    BoneDef(
        "head",
        "torso",
        1.475,
        (0, -0.038),
        (0, 0.039),
        0.075,
        pivot_y=1.4,
        limits=(-0.3 * PI, 0.1 * PI),
        friction_scale=0.25,
        linear_damping=0.1,
        color="skin",
    ),
    BoneDef(
        "upper_left_leg",
        "hip",
        0.775,
        (0, -0.125),
        (0, 0.125),
        0.06,
        pivot_y=0.9,
        limits=(-0.05 * PI, 0.4 * PI),
        color="pant",
    ),
    BoneDef(
        "lower_left_leg",
        "upper_left_leg",
        0.475,
        (0, -0.155),
        (0, 0.125),
        0.045,
        pivot_y=0.625,
        limits=(-0.5 * PI, -0.02 * PI),
        friction_scale=0.5,
        color="pant",
        has_foot=True,
    ),
    BoneDef(
        "upper_right_leg",
        "hip",
        0.775,
        (0, -0.125),
        (0, 0.125),
        0.06,
        pivot_y=0.9,
        limits=(-0.05 * PI, 0.4 * PI),
        color="pant",
    ),
    BoneDef(
        "lower_right_leg",
        "upper_right_leg",
        0.475,
        (0, -0.155),
        (0, 0.125),
        0.045,
        pivot_y=0.625,
        limits=(-0.5 * PI, -0.02 * PI),
        friction_scale=0.5,
        color="pant",
        has_foot=True,
    ),
    BoneDef(
        "upper_left_arm",
        "torso",
        1.225,
        (0, -0.125),
        (0, 0.125),
        0.035,
        pivot_y=1.35,
        limits=(-0.1 * PI, 0.8 * PI),
        friction_scale=0.5,
        color="shirt",
    ),
    BoneDef(
        "lower_left_arm",
        "upper_left_arm",
        0.975,
        (0, -0.125),
        (0, 0.125),
        0.03,
        pivot_y=1.1,
        limits=(-0.2 * PI, 0.3 * PI),
        friction_scale=0.1,
        linear_damping=0.1,
        color="skin",
    ),
    BoneDef(
        "upper_right_arm",
        "torso",
        1.225,
        (0, -0.125),
        (0, 0.125),
        0.035,
        pivot_y=1.35,
        limits=(-0.1 * PI, 0.8 * PI),
        friction_scale=0.5,
        color="shirt",
    ),
    BoneDef(
        "lower_right_arm",
        "upper_right_arm",
        0.975,
        (0, -0.125),
        (0, 0.125),
        0.03,
        pivot_y=1.1,
        limits=(-0.2 * PI, 0.3 * PI),
        friction_scale=0.1,
        linear_damping=0.1,
        color="skin",
    ),
)

#: The foot, as a hull rather than a capsule, so it has a flat sole to stand on.
FOOT_POINTS = ((-0.03, -0.185), (0.11, -0.185), (0.11, -0.16), (-0.03, -0.14))
FOOT_RADIUS = 0.015


@dataclass
class Bone:
    """One built bone: its body, the joint to its parent, and its friction share."""

    name: str
    body: "Body"
    joint: Optional["RevoluteJoint"] = None
    friction_scale: float = 1.0


class Human:
    """A jointed figure that falls like a body rather than a box.

    Example:
        >>> human = Human(world, (0, 10))
        >>> human.set_joint_friction_torque(0.5)
        >>> human.apply_random_angular_impulse(10.0)
    """

    def __init__(
        self,
        world,
        position,
        scale: float = 1.0,
        friction_torque: float = 0.05,
        hertz: float = 0.0,
        damping_ratio: float = 0.0,
        group_index: int = 1,
        colorize: bool = True,
        user_data=None,
    ):
        """Build a figure standing at the given position.

        Args:
            world: The world to build in.
            position: Where the feet land, as a vector-like.
            scale: Overall size. 1.0 is roughly two metres tall.
            friction_torque: How hard the joints resist being moved. Zero
                gives a limp figure, higher values a stiff one.
            hertz: Spring frequency pulling joints back to their rest pose.
                Zero disables the springs.
            damping_ratio: Damping for that spring.
            group_index: Figures with different group indices collide with each
                other; a figure never collides with itself. Also picks the skin
                colour, so a crowd is not all one shade.
            colorize: Whether to give bones shirt, trouser and skin colours.
            user_data: Attached to every bone's body.
        """
        self.world = world
        self.scale = scale
        #: The size the figure was built at, which set_scale measures from.
        self.original_scale = scale
        self.friction_torque = friction_torque
        self.bones: List[Bone] = []
        self._by_name = {}
        self.spawn(position, group_index, hertz, damping_ratio, colorize, user_data)

    # --- construction -------------------------------------------------------

    def spawn(self, position, group_index, hertz, damping_ratio, colorize, user_data):
        """Build the bones and the joints between them."""
        position = Vec2(position)
        scale = self.scale
        max_torque = self.friction_torque * scale
        skin_color = SKIN_COLORS[group_index % len(SKIN_COLORS)]
        colors = {"shirt": SHIRT_COLOR, "pant": PANT_COLOR, "skin": skin_color}

        # A negative group index makes a figure's own bones pass through each
        # other, which is what stops it fighting itself as it folds up.
        body_filter = CollisionFilter(
            category=BONE_CATEGORY, mask=BONE_MASK, group=-group_index
        )
        foot_filter = CollisionFilter(
            category=BONE_CATEGORY, mask=FOOT_MASK, group=-group_index
        )

        for definition in BONES:
            body = self.world.add_body(
                body_type="dynamic",
                position=position + Vec2(0.0, definition.y * scale),
                linear_damping=definition.linear_damping,
                sleep_threshold=0.1,
                name=definition.name,
                user_data=user_data,
            )
            body.add_capsule(
                Vec2(definition.center1) * scale,
                Vec2(definition.center2) * scale,
                radius=definition.radius * scale,
                friction=0.2,
                filter=body_filter,
                custom_color=colors[definition.color] if colorize else None,
            )
            if definition.has_foot:
                body.add_polygon(
                    [Vec2(point) * scale for point in FOOT_POINTS],
                    radius=FOOT_RADIUS * scale,
                    # A slippery, flat sole; feet also skip other ragdolls.
                    friction=0.05,
                    filter=foot_filter,
                    custom_color=FOOT_COLOR if colorize else None,
                )

            bone = Bone(definition.name, body, friction_scale=definition.friction_scale)

            if definition.parent is not None:
                parent = self._by_name[definition.parent].body
                pivot = position + Vec2(0.0, definition.pivot_y * scale)
                lower, upper = definition.limits
                bone.joint = self.world.add_joint(
                    RevoluteJointDef(
                        parent,
                        body,
                        local_anchor_a=parent.get_local_point(pivot),
                        local_anchor_b=body.get_local_point(pivot),
                        enable_limit=True,
                        lower_angle=lower,
                        upper_angle=upper,
                        enable_motor=True,
                        max_motor_torque=definition.friction_scale * max_torque,
                        enable_spring=hertz > 0.0,
                        hertz=hertz,
                        damping_ratio=damping_ratio,
                    )
                )

            self.bones.append(bone)
            self._by_name[definition.name] = bone

    def destroy(self):
        """Remove the figure from the world.

        Joints go first: destroying a body takes its joints with it, and
        Box2D would then be handed ids it has already reclaimed.
        """
        for bone in self.bones:
            if bone.joint is not None and bone.joint.is_valid:
                bone.joint.destroy()
        for bone in self.bones:
            if bone.body.is_valid:
                bone.body.destroy()
        self.bones = []
        self._by_name = {}

    # --- parts --------------------------------------------------------------

    def bone(self, name: str) -> Bone:
        """One bone by name, e.g. ``human.bone("head")``."""
        return self._by_name[name]

    @property
    def torso(self):
        return self._by_name["torso"].body

    @property
    def head(self):
        return self._by_name["head"].body

    @property
    def hip(self):
        return self._by_name["hip"].body

    @property
    def joints(self):
        """Every joint, which is every bone but the root."""
        return [bone.joint for bone in self.bones if bone.joint is not None]

    # --- driving it ---------------------------------------------------------

    def set_velocity(self, velocity):
        """Move the whole figure at once, without disturbing its pose."""
        for bone in self.bones:
            bone.body.linear_velocity = velocity

    def apply_random_angular_impulse(self, magnitude: float):
        """Spin the torso by a random amount, to tip a standing figure over."""
        self.torso.apply_angular_impulse(random.uniform(-magnitude, magnitude), True)

    def set_joint_friction_torque(self, torque: float):
        """How hard the joints resist being moved.

        Zero switches the motors off, which is the difference between a body
        that folds under its own weight and one that holds a pose.
        """
        for bone in self.bones:
            if bone.joint is None:
                continue
            if torque == 0.0:
                bone.joint.motor_enabled = False
            else:
                bone.joint.motor_enabled = True
                bone.joint.max_motor_torque = self.scale * bone.friction_scale * torque

    def set_joint_spring_hertz(self, hertz: float):
        """Spring frequency pulling joints back towards their rest pose."""
        for bone in self.bones:
            if bone.joint is None:
                continue
            if hertz == 0.0:
                bone.joint.spring_enabled = False
            else:
                bone.joint.spring_enabled = True
                bone.joint.spring_hertz = hertz

    def set_joint_damping_ratio(self, damping_ratio: float):
        """Damping for the joint springs."""
        for bone in self.bones:
            if bone.joint is not None:
                bone.joint.spring_damping_ratio = damping_ratio

    def set_scale(self, scale: float):
        """Resize the figure in place, keeping its pose.

        Everything moves relative to the hip: the other bones' positions, the
        joint frames between them, and the shapes themselves. The hip stays
        put, so a figure grows about its middle rather than drifting.

        Joint friction is scaled by the cube of the size change rather than
        matching it. Torque would go with the fourth power of length from mass
        and leverage alone, but gravity pulls harder on the heavier figure
        too, and the cube is what Box2D's own helper settles on.

        Args:
            scale: The new size. Must be positive.

        Raises:
            ValueError: If the scale is not positive.
        """
        if scale <= 0.0:
            raise ValueError(f"scale must be positive, got {scale}")

        # Checked before anything moves. The foot is a hull, and below roughly
        # half size its features fall under Box2D's minimum and the hull
        # cannot be built -- which would otherwise leave the figure partly
        # resized, with the bones that were reached the new size and the rest
        # the old one.
        self._check_scale_is_buildable(scale)

        ratio = scale / self.scale
        original_ratio = scale / self.original_scale
        friction_torque = (original_ratio**3) * self.friction_torque
        origin = self.hip.position

        for index, bone in enumerate(self.bones):
            if index > 0:
                # Setting position keeps the body's rotation, which is what
                # preserves the pose while the figure resizes around the hip.
                offset = (bone.body.position - origin) * ratio
                bone.body.position = origin + offset

                bone.joint.local_anchor_a = bone.joint.local_anchor_a * ratio
                bone.joint.local_anchor_b = bone.joint.local_anchor_b * ratio
                bone.joint.max_motor_torque = bone.friction_scale * friction_torque

            for shape in bone.body.shapes:
                geometry = shape.geometry
                if isinstance(geometry, CapsuleDef):
                    shape.geometry = CapsuleDef(
                        vertex1=Vec2(geometry.vertex1) * ratio,
                        vertex2=Vec2(geometry.vertex2) * ratio,
                        radius=geometry.radius * ratio,
                    )
                elif isinstance(geometry, PolygonDef):
                    shape.geometry = PolygonDef(
                        vertices=[Vec2(point) * ratio for point in geometry.vertices],
                        radius=geometry.radius * ratio,
                    )

            # The shapes changed size, so the body's mass has to be recomputed
            # from them or it keeps the old figure's inertia.
            bone.body.apply_mass_from_shapes()

        self.scale = scale

    def _check_scale_is_buildable(self, scale: float):
        """Raise if the foot would be too small to form a hull at this scale.

        Tried rather than calculated: the limit is Box2D's, and asking it is
        more honest than hard-coding a number that its next version changes.
        """
        try:
            PolygonDef(
                vertices=[Vec2(point) * scale for point in FOOT_POINTS],
                radius=FOOT_RADIUS * scale,
            ).b2Polygon
        except ValueError as error:
            raise ValueError(
                f"a figure cannot be built at scale {scale}: its feet fall below "
                f"Box2D's minimum polygon size. Roughly 0.5 is the smallest that "
                f"works."
            ) from error

    def enable_sensor_events(self, enable: bool = True):
        """Let sensors detect this figure's bones."""
        for bone in self.bones:
            for shape in bone.body.shapes:
                shape.enable_sensor_events = enable
