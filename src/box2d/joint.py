# joint.py

from box2d._box2d import lib, ffi
from abc import ABC, abstractmethod
from .math import Vec2, Rot, Transform, VectorLike
from .accessors import b2_bool, b2_float, b2_value
from .lifetime import IdRef, raw_id, is_live


class Joint(ABC):
    """Base class for all physics joints connecting two rigid bodies.

    Manages the lifecycle and common properties of constraints between bodies,
    such as anchors and collision handling between connected bodies.
    """

    _joint_id = IdRef(lib.b2Joint_IsValid, "joint")

    def __init__(self, world, body_a, body_b, collide_connected=False):
        """Initialize a joint between two bodies.

        Args:
            world: The physics world where the joint exists
            body_a: First body to connect (must be movable/dynamic)
            body_b: Second body to connect (can be static or dynamic)
            collide_connected: Whether connected bodies should collide with each other
        """
        pass

    def _set_userdata(self):
        """Finalize joint creation in the physics simulation.

        Should be called after joint configuration is complete. Handles the
        internal connection between the joint definition and simulation.
        """
        self._joint_handle = ffi.new_handle(self)
        lib.b2Joint_SetUserData(self._joint_id, self._joint_handle)

    def destroy(self, wake_attached: bool = True):
        """Destroy the joint and remove it from the world.

        The joint raises :class:`DestroyedError` if used afterwards. Destroying
        twice is a no-op.

        Args:
            wake_attached: Wake the bodies this joint connected. Defaults to
                True so that releasing a constraint lets the bodies react to
                it; pass False to leave sleeping bodies asleep.
        """
        # Read past the validity check so destroy stays callable on a joint
        # Box2D has already reclaimed, e.g. one whose bodies went first.
        raw = raw_id(self, "_joint_id")
        if raw is not None and lib.b2Joint_IsValid(raw):
            lib.b2DestroyJoint(raw, bool(wake_attached))
        del self._joint_id

    @property
    def is_valid(self):
        """Check if the joint is currently active in the simulation.

        Returns:
            True if the joint still connects its bodies, False if it has been
            removed or destroyed
        """
        return is_live(self, "_joint_id", lib.b2Joint_IsValid)

    @property
    def body_a(self):
        """Get the first body connected by this joint.

        Returns:
            Body: The dynamic body that initiated the joint connection
        """
        return ffi.from_handle(
            lib.b2Body_GetUserData(lib.b2Joint_GetBodyA(self._joint_id))
        )

    @property
    def body_b(self):
        """Get the second body connected by this joint.

        Returns:
            Body: The partner body (can be static or dynamic)
        """
        return ffi.from_handle(
            lib.b2Body_GetUserData(lib.b2Joint_GetBodyB(self._joint_id))
        )

    @property
    def local_anchor_a(self):
        """Local connection point on the first body.

        Setting this moves where the joint attaches without rebuilding it,
        which is how a joint is retargeted at runtime. The frame's rotation is
        preserved; use :attr:`local_frame_a` to set both at once.

        Returns:
            Vec2: Position where the joint attaches to body_a in its local coordinates
        """
        vec = lib.b2Joint_GetLocalFrameA(self._joint_id).p
        return Vec2(vec.x, vec.y)

    @local_anchor_a.setter
    def local_anchor_a(self, value: VectorLike):
        frame = self.local_frame_a
        self.local_frame_a = Transform(Vec2(value), frame.q)

    @property
    def local_anchor_b(self):
        """Local connection point on the second body.

        Settable, like :attr:`local_anchor_a`.

        Returns:
            Vec2: Position where the joint attaches to body_b in its local coordinates
        """
        vec = lib.b2Joint_GetLocalFrameB(self._joint_id).p
        return Vec2(vec.x, vec.y)

    @local_anchor_b.setter
    def local_anchor_b(self, value: VectorLike):
        frame = self.local_frame_b
        self.local_frame_b = Transform(Vec2(value), frame.q)

    @property
    def local_frame_a(self) -> Transform:
        """The joint's frame on body_a: attachment point and orientation.

        The anchor alone positions a joint; the frame's rotation is what the
        joint measures its angle or axis against, so a revolute joint's zero
        angle and a prismatic joint's axis both come from here.
        """
        return Transform.from_b2Transform(lib.b2Joint_GetLocalFrameA(self._joint_id))

    @local_frame_a.setter
    def local_frame_a(self, value: Transform):
        lib.b2Joint_SetLocalFrameA(self._joint_id, value.b2Transform[0])

    @property
    def local_frame_b(self) -> Transform:
        """The joint's frame on body_b. See :attr:`local_frame_a`."""
        return Transform.from_b2Transform(lib.b2Joint_GetLocalFrameB(self._joint_id))

    @local_frame_b.setter
    def local_frame_b(self, value: Transform):
        lib.b2Joint_SetLocalFrameB(self._joint_id, value.b2Transform[0])

    @property
    def constraint_tuning(self) -> tuple:
        """How stiffly the solver enforces this joint, as ``(hertz, damping_ratio)``.

        Giving a joint a low stiffness makes it soft, so it can be pulled out
        of place and springs back -- the mechanism behind a suspension that
        yields under load.

        The scale is not monotonic: zero hertz means rigid, and so does a high
        value, with the softest behaviour in between. Measured on a hinge under
        a heavy weight, separation is 0.0002m at 0Hz, peaks near 0.02m around
        1-2Hz, and is back to 0.0001m by 60Hz. The default is (60.0, 2.0),
        which is stiff enough to look rigid.
        """
        hertz = ffi.new("float*")
        damping_ratio = ffi.new("float*")
        lib.b2Joint_GetConstraintTuning(self._joint_id, hertz, damping_ratio)
        return (hertz[0], damping_ratio[0])

    @constraint_tuning.setter
    def constraint_tuning(self, value):
        hertz, damping_ratio = value
        lib.b2Joint_SetConstraintTuning(
            self._joint_id, float(hertz), float(damping_ratio)
        )

    @property
    def constraint_force(self):
        """Current force exerted by the joint to maintain its constraint.

        Returns:
            Vec2: Constraint force vector in world coordinates
        """
        vec = lib.b2Joint_GetConstraintForce(self._joint_id)
        return Vec2(vec.x, vec.y)

    constraint_torque = b2_value(
        lib.b2Joint_GetConstraintTorque,
        doc="""Current torque exerted by the joint to maintain rotation constraints.
        
        Returns:
            float: Constraint torque value
        """,
    )
    collide_connected = b2_value(
        lib.b2Joint_GetCollideConnected,
        lib.b2Joint_SetCollideConnected,
        doc="""Check if connected bodies can collide with each other.
        
        Returns:
            bool: True if connected bodies can collide, False otherwise
        """,
    )

    joint_type = b2_value(
        lib.b2Joint_GetType,
        doc="The Box2D constant identifying which kind of joint this is.",
    )

    linear_separation = b2_value(
        lib.b2Joint_GetLinearSeparation,
        doc="""How far apart the joint's two frames have drifted, in metres.

        A perfectly satisfied joint reads zero; a large value means the solver
        is losing the constraint, which is what a breakable joint watches.
        """,
    )

    angular_separation = b2_value(
        lib.b2Joint_GetAngularSeparation,
        doc="The angular counterpart of linear_separation, in radians.",
    )

    force_threshold = b2_float(
        lib.b2Joint_GetForceThreshold,
        lib.b2Joint_SetForceThreshold,
        doc="""Get or set the force above which this joint reports an event.

        A joint reports nothing through World.get_joint_events until one of its
        thresholds is set, so this is how a breakable construction learns which
        of its joints is about to give. Defaults to infinity.
        """,
    )

    torque_threshold = b2_float(
        lib.b2Joint_GetTorqueThreshold,
        lib.b2Joint_SetTorqueThreshold,
        doc="""Get or set the torque above which this joint reports an event.

        The rotational counterpart of force_threshold. Defaults to infinity.
        """,
    )

    def wake_bodies(self):
        """Ensure connected bodies are active and responsive to movement.

        Useful when restarting dragging after bodies entered sleep state.
        """
        lib.b2Joint_WakeBodies(self._joint_id)


class MouseJoint(Joint):
    """Interactive joint for dragging bodies with mouse-like movement.

    Designed for smoothly pulling dynamic bodies to target positions,
    with spring-like behavior controls for realistic manipulation.

    Box2D 3.2 deleted b2MouseJoint. This keeps the same Python API by building
    what upstream's own samples now use for dragging: a kinematic proxy body at
    the target, joined to the dragged body by a motor joint with a linear
    spring. Moving the target moves the proxy, and the spring pulls the body
    after it. The proxy is destroyed along with the joint.
    """

    def __init__(
        self,
        world,
        body,
        target: VectorLike,
        max_force=1000.0,
        damping_ratio=0.7,
        hertz=5.0,
    ):
        """Create a drag-and-move joint for interactive manipulation.

        Args:
            world: The physics world where the joint exists
            body: Dynamic body to be dragged
            target: Initial world position (x,y) to pull toward
            max_force: Maximum force allowed for movement
            damping_ratio: Spring damping
            hertz: Spring stiffness in Hz
        """
        self.world = world
        self._body = body

        # The kinematic proxy the spring pulls towards. It must not sleep, or
        # dragging would stall once the proxy settles.
        target = Vec2(target)
        self._proxy = world.add_body(
            body_type="kinematic", position=target, enable_sleep=False
        )

        defn = lib.b2DefaultMotorJointDef()
        defn.base.bodyIdA = self._proxy._body_id
        defn.base.bodyIdB = body._body_id
        defn.base.localFrameB.p = body.get_local_point(target).b2Vec2[0]
        defn.base.collideConnected = False
        defn.linearHertz = hertz
        defn.linearDampingRatio = damping_ratio
        defn.maxSpringForce = max_force
        self._def = defn

        self._joint_id = lib.b2CreateMotorJoint(
            self.world._world_id, ffi.addressof(self._def)
        )
        self._set_userdata()
        self.wake_bodies()

    def destroy(self):
        """Destroy the joint and the kinematic proxy body backing it."""
        super().destroy()
        proxy = getattr(self, "_proxy", None)
        if proxy is not None:
            proxy.destroy()
            self._proxy = None

    @property
    def target(self):
        """Current target position to drag toward.

        Returns:
            Vec2: World coordinates of the drag target
        """
        return self._proxy.position

    @target.setter
    def target(self, value):
        """Update the position being dragged toward.

        Args:
            value (tuple/Vec2): New target position in world coordinates
        """
        self._proxy.position = Vec2(value)
        self.wake_bodies()

    max_force = b2_float(
        lib.b2MotorJoint_GetMaxSpringForce,
        lib.b2MotorJoint_SetMaxSpringForce,
        doc="Maximum pulling force available to move the body.",
    )
    damping_ratio = b2_float(
        lib.b2MotorJoint_GetLinearDampingRatio,
        lib.b2MotorJoint_SetLinearDampingRatio,
        doc="Spring damping controlling movement smoothness.",
    )
    hertz = b2_float(
        lib.b2MotorJoint_GetLinearHertz,
        lib.b2MotorJoint_SetLinearHertz,
        doc="Spring stiffness in Hz.",
    )


class FilterJoint(Joint):
    """Stops two specific bodies from colliding, and nothing else.

    Collision categories and masks work per shape and in groups, so they cannot
    say "these two bodies ignore each other" without also affecting everything
    sharing their category. A filter joint says exactly that and constrains
    nothing else: the bodies move independently, they simply pass through.

    Cheaper and simpler than a custom filter callback when the rule is a fixed
    pair rather than a computation.
    """

    def __init__(self, world, body_a, body_b, collide_connected=False):
        """Create a filter joint between two bodies.

        Args:
            world: The physics world where the joint exists
            body_a: First body
            body_b: Second body
            collide_connected: Ignored. A filter joint exists to stop these two
                colliding, so honouring this would defeat it.
        """
        self.world = world

        defn = lib.b2DefaultFilterJointDef()
        defn.base.bodyIdA = body_a._body_id
        defn.base.bodyIdB = body_b._body_id
        self._def = defn

        self._joint_id = lib.b2CreateFilterJoint(
            self.world._world_id, ffi.addressof(self._def)
        )
        self._set_userdata()


class WeldJoint(Joint):
    """WeldJoint connects two bodies rigidly, fully constraining their relative
    translation and rotation while allowing for softness when spring parameters
    are configured.

    The weld joint "welds" two bodies together using provided local anchor points.
    These anchors are specified in each body's local coordinate system.

    Args:
        world: The physics world instance.
        body_a: The first body to be joined.
        body_b: The second body to be joined.
        local_anchor_a (tuple): Local coordinates (x, y) on body_a where the joint is attached.
        local_anchor_b (tuple): Local coordinates (x, y) on body_b where the joint is attached.
        collide_connected (bool, optional): If True, the connected bodies will collide.
        linear_hertz (float, optional): Linear spring stiffness in Hertz
        linear_damping_ratio (float, optional): Linear damping ratio
        angular_hertz (float, optional): Angular spring stiffness in Hertz
        angular_damping_ratio (float, optional): Angular damping ratio
        reference_angle (float, optional): The reference angle between the two bodies.
    """

    def __init__(
        self,
        world,
        body_a,
        body_b,
        local_anchor_a: VectorLike,
        local_anchor_b: VectorLike,
        collide_connected=False,
        linear_hertz=None,
        linear_damping_ratio=None,
        angular_hertz=None,
        angular_damping_ratio=None,
        reference_angle=None,
    ):
        self._local_anchor_a = Vec2(local_anchor_a)
        self._local_anchor_b = Vec2(local_anchor_b)
        self._linear_hertz = linear_hertz
        self._linear_damping_ratio = linear_damping_ratio
        self._angular_hertz = angular_hertz
        self._angular_damping_ratio = angular_damping_ratio
        self._reference_angle = reference_angle
        self.world = world
        defn = lib.b2DefaultWeldJointDef()
        defn.base.bodyIdA = body_a._body_id
        defn.base.bodyIdB = body_b._body_id
        defn.base.collideConnected = collide_connected

        # Use the provided local anchor points directly.
        defn.base.localFrameA.p = self._local_anchor_a.b2Vec2[0]
        defn.base.localFrameB.p = self._local_anchor_b.b2Vec2[0]
        if self._reference_angle is not None:
            # 3.2 removed referenceAngle; the reference orientation is now
            # carried by the rotation of the first local frame.
            defn.base.localFrameA.q = Rot(self._reference_angle).b2Rot[0]

        # Set the spring/damping parameters to allow for soft welding.
        if self._linear_hertz is not None:
            defn.linearHertz = self._linear_hertz
        if self._linear_damping_ratio is not None:
            defn.linearDampingRatio = self._linear_damping_ratio
        if self._angular_hertz is not None:
            defn.angularHertz = self._angular_hertz
        if self._angular_damping_ratio is not None:
            defn.angularDampingRatio = self._angular_damping_ratio
        self._def = defn
        self._joint_id = lib.b2CreateWeldJoint(
            self.world._world_id, ffi.addressof(self._def)
        )
        self._set_userdata()

    linear_hertz = b2_float(
        lib.b2WeldJoint_GetLinearHertz,
        lib.b2WeldJoint_SetLinearHertz,
        doc="The linear stiffness (in Hertz) of the weld joint spring.",
    )
    linear_damping_ratio = b2_float(
        lib.b2WeldJoint_GetLinearDampingRatio,
        lib.b2WeldJoint_SetLinearDampingRatio,
        doc="The linear damping ratio (non-dimensional) of the weld joint spring.",
    )
    angular_hertz = b2_float(
        lib.b2WeldJoint_GetAngularHertz,
        lib.b2WeldJoint_SetAngularHertz,
        doc="The angular stiffness (in Hertz) of the weld joint.",
    )
    angular_damping_ratio = b2_float(
        lib.b2WeldJoint_GetAngularDampingRatio,
        lib.b2WeldJoint_SetAngularDampingRatio,
        doc="The angular damping ratio (non-dimensional) of the weld joint.",
    )


class RevoluteJoint(Joint):
    """
    RevoluteJoint connects two bodies at a pair of anchor points, allowing for
    relative rotation about a shared axis. Optionally, joint limits and a motor
    can be enabled.
    """

    def __init__(
        self,
        world,
        body_a,
        body_b,
        local_anchor_a: VectorLike,
        local_anchor_b: VectorLike,
        collide_connected=False,
        lower_angle=None,
        upper_angle=None,
        enable_limit=None,
        motor_speed=None,
        max_motor_torque=None,
        enable_motor=None,
        reference_angle=None,
        enable_spring=None,
        hertz=None,
        damping_ratio=None,
        target_angle=None,
    ):
        """
        Initialize a revolute joint with separate local anchor points for each body.

        Args:
            world: The physics world instance.
            body_a: The first body to connect.
            body_b: The second body to connect.
            local_anchor_a (tuple): The local (x, y) coordinates on body_a for the joint.
            local_anchor_b (tuple): The local (x, y) coordinates on body_b for the joint.
            collide_connected (bool, optional): If True, connected bodies will collide.
            lower_angle (float, optional): Lower joint limit in radians.
            upper_angle (float, optional): Upper joint limit in radians.
            enable_limit (bool, optional): Whether to enable joint limits.
            motor_speed (float, optional): Desired motor speed in radians/sec.
            max_motor_torque (float, optional): Maximum motor torque in newton-meters.
            enable_motor (bool, optional): Whether to enable the joint motor.
            reference_angle (float, optional): Reference angle between the two bodies.
            enable_spring (bool, optional): Whether a spring pulls the joint
                towards target_angle.
            hertz (float, optional): Spring frequency.
            damping_ratio (float, optional): Spring damping ratio.
            target_angle (float, optional): The angle the spring pulls towards.
        """
        self._localAnchorA = Vec2(local_anchor_a)
        self._localAnchorB = Vec2(local_anchor_b)
        self._lower_angle = lower_angle
        self._upper_angle = upper_angle
        self._enable_limit = enable_limit
        self._motor_speed = motor_speed
        self._max_motor_torque = max_motor_torque
        self._enable_motor = enable_motor
        self._reference_angle = reference_angle

        # Get a default revolute joint definition from Box2D.
        defn = lib.b2DefaultRevoluteJointDef()
        defn.base.bodyIdA = body_a._body_id
        defn.base.bodyIdB = body_b._body_id
        defn.base.collideConnected = collide_connected

        # Use the provided local anchors for each body.
        defn.base.localFrameA.p = self._localAnchorA.b2Vec2[0]
        defn.base.localFrameB.p = self._localAnchorB.b2Vec2[0]

        if self._reference_angle is not None:
            # 3.2 removed referenceAngle; the reference orientation is now
            # carried by the rotation of the first local frame.
            defn.base.localFrameA.q = Rot(self._reference_angle).b2Rot[0]

        # Configure joint limits.
        if self._lower_angle is not None:
            defn.lowerAngle = self._lower_angle
        if self._upper_angle is not None:
            defn.upperAngle = self._upper_angle
        if self._enable_limit is not None:
            defn.enableLimit = self._enable_limit

        # Configure motor parameters.
        if self._motor_speed is not None:
            defn.motorSpeed = self._motor_speed
        if self._max_motor_torque is not None:
            defn.maxMotorTorque = self._max_motor_torque
        if self._enable_motor is not None:
            defn.enableMotor = self._enable_motor

        # Spring parameters, which pull the joint back towards target_angle.
        if enable_spring is not None:
            defn.enableSpring = enable_spring
        if hertz is not None:
            defn.hertz = hertz
        if damping_ratio is not None:
            defn.dampingRatio = damping_ratio
        if target_angle is not None:
            defn.targetAngle = target_angle

        self._def = defn
        self.world = world
        self._joint_id = lib.b2CreateRevoluteJoint(
            self.world._world_id, ffi.addressof(self._def)
        )
        self._set_userdata()

    angle = b2_value(
        lib.b2RevoluteJoint_GetAngle,
        doc="Current joint angle in radians relative to the reference angle.",
    )
    motor_speed = b2_float(
        lib.b2RevoluteJoint_GetMotorSpeed,
        lib.b2RevoluteJoint_SetMotorSpeed,
        doc="Desired motor speed in radians per second.",
    )
    max_motor_torque = b2_float(
        lib.b2RevoluteJoint_GetMaxMotorTorque,
        lib.b2RevoluteJoint_SetMaxMotorTorque,
        doc="Maximum motor torque in newton-meters.",
    )
    lower_limit = b2_value(
        lib.b2RevoluteJoint_GetLowerLimit,
        doc="The lower joint limit in radians.",
    )
    upper_limit = b2_value(
        lib.b2RevoluteJoint_GetUpperLimit,
        doc="The upper joint limit in radians.",
    )

    def set_limits(self, lower, upper):
        """
        Set the joint limits in radians.

        Args:
            lower (float): Lower limit angle.
            upper (float): Upper limit angle.
        """
        lib.b2RevoluteJoint_SetLimits(self._joint_id, float(lower), float(upper))

    limit_enabled = b2_bool(
        lib.b2RevoluteJoint_IsLimitEnabled,
        lib.b2RevoluteJoint_EnableLimit,
        doc="Get or set whether the joint limit is enforced.",
    )
    motor_enabled = b2_bool(
        lib.b2RevoluteJoint_IsMotorEnabled,
        lib.b2RevoluteJoint_EnableMotor,
        doc="Get or set whether the motor drives the joint.",
    )
    motor_torque = b2_value(
        lib.b2RevoluteJoint_GetMotorTorque,
        doc="The torque the motor applied in the last step, in newton-metres.",
    )
    spring_enabled = b2_bool(
        lib.b2RevoluteJoint_IsSpringEnabled,
        lib.b2RevoluteJoint_EnableSpring,
        doc="Get or set whether the joint's angular spring is active.",
    )
    spring_hertz = b2_float(
        lib.b2RevoluteJoint_GetSpringHertz,
        lib.b2RevoluteJoint_SetSpringHertz,
        doc="Get or set the angular spring frequency in Hz.",
    )
    spring_damping_ratio = b2_float(
        lib.b2RevoluteJoint_GetSpringDampingRatio,
        lib.b2RevoluteJoint_SetSpringDampingRatio,
        doc="Get or set the angular spring damping ratio.",
    )
    target_angle = b2_float(
        lib.b2RevoluteJoint_GetTargetAngle,
        lib.b2RevoluteJoint_SetTargetAngle,
        doc="""Get or set the angle the spring pulls towards, in radians.
        
        New in Box2D 3.2, replacing the old reference angle as the way to say
        where the joint wants to rest.
        """,
    )


class PrismaticJoint(Joint):
    """
    A prismatic joint constrains two bodies to translate along a shared axis while
    preventing relative rotation. Also known as a slider joint.

    The prismatic joint is useful for things like:
    - Pistons and linear actuators
    - Moving platforms and elevators
    - Sliding doors and drawers
    - Any motion constrained to a line

    Features include:
    - Linear limits to restrict range of motion
    - Motor to drive relative motion
    - Spring to create soft constraints
    """

    def __init__(
        self,
        world,
        body_a,
        body_b,
        local_anchor_a: VectorLike,
        local_anchor_b: VectorLike,
        axis: VectorLike,
        collide_connected=False,
        lower_limit=None,
        upper_limit=None,
        enable_limit=None,
        motor_speed=None,
        max_motor_force=None,
        enable_motor=None,
        reference_angle=None,
        enable_spring=None,
        hertz=None,
        damping_ratio=None,
        target_translation=None,
    ):
        """Initialize a prismatic joint between two bodies.

        Args:
            world: The physics world instance
            body_a: First body to connect
            body_b: Second body to connect
            local_anchor_a (tuple): Local anchor point on body A (x,y)
            local_anchor_b (tuple): Local anchor point on body B (x,y)
            axis (tuple): The axis defining allowed translation (x,y) in body A's frame
            collide_connected (bool): Whether bodies can collide
            lower_limit (float): Lower translation limit
            upper_limit (float): Upper translation limit
            enable_limit (bool): Whether to enable joint limits
            motor_speed (float): Desired motor speed in meters/sec
            max_motor_force (float): Maximum motor force in N
            enable_motor (bool): Whether to enable the joint motor
            reference_angle (float): Reference angle between bodies
            enable_spring (bool): Enable spring behavior
            hertz (float): Spring oscillation frequency in Hz
            damping_ratio (float): Spring damping ratio
        """
        self._local_anchor_a = Vec2(local_anchor_a)
        self._local_anchor_b = Vec2(local_anchor_b)
        self._local_axis_a = Vec2(axis)
        self._lower_limit = lower_limit
        self._upper_limit = upper_limit
        self._enable_limit = enable_limit
        self._motor_speed = motor_speed
        self._max_motor_force = max_motor_force
        self._enable_motor = enable_motor
        self._reference_angle = reference_angle
        self._enable_spring = enable_spring
        self._hertz = hertz
        self._damping_ratio = damping_ratio
        self.world = world
        defn = lib.b2DefaultPrismaticJointDef()
        defn.base.bodyIdA = body_a._body_id
        defn.base.bodyIdB = body_b._body_id
        defn.base.collideConnected = collide_connected
        defn.base.localFrameA.p = self._local_anchor_a.b2Vec2[0]
        defn.base.localFrameB.p = self._local_anchor_b.b2Vec2[0]
        # 3.2 removed localAxisA: the axis is the rotation of the local frames.
        axis = self._local_axis_a
        axis_rotation = Rot.from_sincos(axis.y, axis.x).b2Rot[0]
        defn.base.localFrameA.q = axis_rotation
        defn.base.localFrameB.q = axis_rotation

        # reference_angle is deliberately not applied here. In 3.2 the frame
        # rotation carries the axis, and a prismatic joint has no orientation
        # left over to hold a separate reference angle. Setting it would
        # silently overwrite the axis and break the joint.
        if self._enable_limit is not None:
            defn.enableLimit = self._enable_limit
        if self._lower_limit is not None:
            defn.lowerTranslation = self._lower_limit
        if self._upper_limit is not None:
            defn.upperTranslation = self._upper_limit
        if self._enable_motor is not None:
            defn.enableMotor = self._enable_motor
        if self._motor_speed is not None:
            defn.motorSpeed = self._motor_speed
        if self._max_motor_force is not None:
            defn.maxMotorForce = self._max_motor_force
        if self._enable_spring is not None:
            defn.enableSpring = self._enable_spring
        if self._hertz is not None:
            defn.hertz = self._hertz
        if self._damping_ratio is not None:
            defn.dampingRatio = self._damping_ratio
        if target_translation is not None:
            defn.targetTranslation = target_translation

        self._def = defn

        self._joint_id = lib.b2CreatePrismaticJoint(
            self.world._world_id, ffi.addressof(self._def)
        )
        self._set_userdata()

    joint_translation = b2_value(
        lib.b2PrismaticJoint_GetTranslation,
        doc="Get the current joint translation.",
    )
    joint_speed = b2_value(
        lib.b2PrismaticJoint_GetSpeed,
        doc="Get the current joint linear speed.",
    )
    limit_enabled = b2_bool(
        lib.b2PrismaticJoint_IsLimitEnabled,
        lib.b2PrismaticJoint_EnableLimit,
        doc="Check if the joint limit is enabled.",
    )

    @property
    def lower_limit(self):
        """Get the lower joint limit."""
        return lib.b2PrismaticJoint_GetLowerLimit(self._joint_id)

    @lower_limit.setter
    def lower_limit(self, lower):
        """Set the lower joint limit."""
        upper_limit = self.upper_limit
        lib.b2PrismaticJoint_SetLimits(self._joint_id, float(lower), float(upper_limit))

    @property
    def upper_limit(self):
        """Get the upper joint limit."""
        return lib.b2PrismaticJoint_GetUpperLimit(self._joint_id)

    @upper_limit.setter
    def upper_limit(self, upper):
        """Set the upper joint limit."""
        lower_limit = self.lower_limit
        lib.b2PrismaticJoint_SetLimits(self._joint_id, float(lower_limit), float(upper))

    def set_limits(self, lower, upper):
        """Set the joint limits.

        Args:
            lower (float): Lower translation limit
            upper (float): Upper translation limit
        """
        lib.b2PrismaticJoint_SetLimits(self._joint_id, float(lower), float(upper))

    motor_enabled = b2_bool(
        lib.b2PrismaticJoint_IsMotorEnabled,
        lib.b2PrismaticJoint_EnableMotor,
        doc="Check if the joint motor is enabled.",
    )
    motor_speed = b2_float(
        lib.b2PrismaticJoint_GetMotorSpeed,
        lib.b2PrismaticJoint_SetMotorSpeed,
        doc="Get the motor speed in meters per second.",
    )
    max_motor_force = b2_float(
        lib.b2PrismaticJoint_GetMaxMotorForce,
        lib.b2PrismaticJoint_SetMaxMotorForce,
        doc="Get maximum motor force in Newtons.",
    )
    motor_force = b2_value(
        lib.b2PrismaticJoint_GetMotorForce,
        doc="Get the current motor force in Newtons.",
    )
    spring_enabled = b2_bool(
        lib.b2PrismaticJoint_IsSpringEnabled,
        lib.b2PrismaticJoint_EnableSpring,
        doc="Check if spring behavior is enabled.",
    )
    spring_hertz = b2_float(
        lib.b2PrismaticJoint_GetSpringHertz,
        lib.b2PrismaticJoint_SetSpringHertz,
        doc="Get spring frequency in Hertz.",
    )
    target_translation = b2_float(
        lib.b2PrismaticJoint_GetTargetTranslation,
        lib.b2PrismaticJoint_SetTargetTranslation,
        doc="""Where along the axis the spring pulls towards, in metres.

        Only meaningful with the spring enabled: the joint behaves as a
        linear servo, driving the translation towards this value at the
        stiffness set by spring_hertz.
        """,
    )

    spring_damping_ratio = b2_float(
        lib.b2PrismaticJoint_GetSpringDampingRatio,
        lib.b2PrismaticJoint_SetSpringDampingRatio,
        doc="Get spring damping ratio.",
    )


class WheelJoint(Joint):
    """A wheel joint constrains a point on one body to translate along an axis fixed
    on another body. This is similar to a prismatic joint but with rotation.
    A rotational motor can be added to drive the relative rotation.
    This joint is designed for vehicle suspensions.
    """

    def __init__(
        self,
        world,
        body_a,
        body_b,
        local_anchor_a: VectorLike,
        local_anchor_b: VectorLike,
        axis: VectorLike,
        collide_connected=False,
        enable_limit=False,
        lower_translation=0.0,
        upper_translation=0.0,
        enable_motor=False,
        motor_speed=0.0,
        max_motor_torque=0.0,
        enable_spring=False,
        spring_hertz=0.0,
        spring_damping_ratio=0.0,
    ):
        """Initialize a wheel joint.

        Args:
            world: The physics world instance
            body_a: First body to connect
            body_b: Second body to connect
            local_anchor_a (tuple): Local anchor point on body A (x,y)
            local_anchor_b (tuple): Local anchor point on body B (x,y)
            axis (tuple): The axis defining translation in body A's frame (x,y)
            collide_connected (bool): Whether bodies can collide
            enable_limit (bool): Enable joint translation limits
            lower_translation (float): Lower translation limit
            upper_translation (float): Upper translation limit
            enable_motor (bool): Enable the joint motor
            motor_speed (float): Motor speed in radians/second
            max_motor_torque (float): Maximum motor torque in N-m
            enable_spring (bool): Enable spring behavior
            spring_hertz (float): Spring frequency in Hz
            spring_damping_ratio (float): Spring damping ratio
        """
        self._local_anchor_a = Vec2(local_anchor_a)
        self._local_anchor_b = Vec2(local_anchor_b)
        self._local_axis_a = Vec2(axis)
        self._enable_limit = enable_limit
        self._lower_translation = lower_translation
        self._upper_translation = upper_translation
        self._enable_motor = enable_motor
        self._motor_speed = motor_speed
        self._max_motor_torque = max_motor_torque
        self._enable_spring = enable_spring
        self._spring_hertz = spring_hertz
        self._spring_damping_ratio = spring_damping_ratio
        self.world = world

        defn = lib.b2DefaultWheelJointDef()
        defn.base.bodyIdA = body_a._body_id
        defn.base.bodyIdB = body_b._body_id
        defn.base.collideConnected = collide_connected
        defn.base.localFrameA.p = self._local_anchor_a.b2Vec2[0]
        defn.base.localFrameB.p = self._local_anchor_b.b2Vec2[0]
        # 3.2 removed localAxisA: the axis is the rotation of the local frames.
        axis = self._local_axis_a
        axis_rotation = Rot.from_sincos(axis.y, axis.x).b2Rot[0]
        defn.base.localFrameA.q = axis_rotation
        defn.base.localFrameB.q = axis_rotation
        defn.enableLimit = self._enable_limit
        defn.lowerTranslation = self._lower_translation
        defn.upperTranslation = self._upper_translation
        defn.enableMotor = self._enable_motor
        defn.motorSpeed = self._motor_speed
        defn.maxMotorTorque = self._max_motor_torque
        defn.enableSpring = self._enable_spring
        defn.hertz = self._spring_hertz
        defn.dampingRatio = self._spring_damping_ratio
        self._def = defn
        self._joint_id = lib.b2CreateWheelJoint(
            self.world._world_id, ffi.addressof(self._def)
        )
        self._set_userdata()

    spring_enabled = b2_bool(
        lib.b2WheelJoint_IsSpringEnabled,
        lib.b2WheelJoint_EnableSpring,
        doc="Check if spring behavior is enabled.",
    )
    spring_hertz = b2_float(
        lib.b2WheelJoint_GetSpringHertz,
        lib.b2WheelJoint_SetSpringHertz,
        doc="Get spring frequency in Hertz.",
    )
    spring_damping_ratio = b2_float(
        lib.b2WheelJoint_GetSpringDampingRatio,
        lib.b2WheelJoint_SetSpringDampingRatio,
        doc="Get spring damping ratio (non-dimensional).",
    )
    limit_enabled = b2_bool(
        lib.b2WheelJoint_IsLimitEnabled,
        lib.b2WheelJoint_EnableLimit,
        doc="Check if translation limits are enabled.",
    )
    lower_limit = b2_value(
        lib.b2WheelJoint_GetLowerLimit,
        doc="Get lower translation limit.",
    )
    upper_limit = b2_value(
        lib.b2WheelJoint_GetUpperLimit,
        doc="Get upper translation limit.",
    )

    def set_limits(self, lower, upper):
        """Set the translation limits.

        Args:
            lower (float): Lower translation limit
            upper (float): Upper translation limit
        """
        lib.b2WheelJoint_SetLimits(self._joint_id, float(lower), float(upper))

    motor_enabled = b2_bool(
        lib.b2WheelJoint_IsMotorEnabled,
        lib.b2WheelJoint_EnableMotor,
        doc="Check if joint motor is enabled.",
    )
    motor_speed = b2_float(
        lib.b2WheelJoint_GetMotorSpeed,
        lib.b2WheelJoint_SetMotorSpeed,
        doc="Get motor speed in radians per second.",
    )
    max_motor_torque = b2_float(
        lib.b2WheelJoint_GetMaxMotorTorque,
        lib.b2WheelJoint_SetMaxMotorTorque,
        doc="Get maximum motor torque in N-m.",
    )
    motor_torque = b2_value(
        lib.b2WheelJoint_GetMotorTorque,
        doc="Get current motor torque in N-m.",
    )


class DistanceJoint(Joint):
    """A distance joint constrains two points on two bodies to maintain a constant distance.

    A distance joint connects two points on two bodies with a massless rod or a spring.
    The distance can be static (like a rod) or behave like a spring that can stretch.
    When spring is enabled, it can optionally have a motor to actively change its length.

    Features:
    - Optional spring behavior with configurable stiffness and damping
    - Optional length limits to restrict stretching
    - Optional motor to actively change the distance
    """

    def __init__(
        self,
        world,
        body_a,
        body_b,
        local_anchor_a: VectorLike,
        local_anchor_b: VectorLike,
        collide_connected=False,
        length=None,
        min_length=None,
        max_length=None,
        enable_limit=False,
        enable_spring=False,
        hertz=None,
        damping_ratio=None,
        enable_motor=False,
        motor_speed=None,
        max_motor_force=None,
        lower_spring_force=None,
        upper_spring_force=None,
    ):
        """Initialize a distance joint between two bodies.

        Args:
            world: The physics world instance
            body_a: First body to connect
            body_b: Second body to connect
            local_anchor_a (tuple): Local anchor point on body A (x,y)
            local_anchor_b (tuple): Local anchor point on body B (x,y)
            collide_connected (bool): Whether bodies can collide
            length (float): Rest length. Calculated from anchors if None.
            min_length (float): Minimum allowed length when using limits
            max_length (float): Maximum allowed length when using limits
            enable_limit (bool): Whether to enable length limits
            enable_spring (bool): Enable spring behavior
            hertz (float): Spring oscillation frequency in Hz when enabled
            damping_ratio (float): Spring damping ratio [0,1] when enabled
            enable_motor (bool): Enable the joint motor
            motor_speed (float): Desired motor speed in meters/second
            max_motor_force (float): Maximum motor force in Newtons
        """
        self._local_anchor_a = Vec2(local_anchor_a)
        self._local_anchor_b = Vec2(local_anchor_b)
        self._length = length
        self._min_length = min_length
        self._max_length = max_length
        self._enable_limit = enable_limit
        self._enable_spring = enable_spring
        self._hertz = hertz
        self._damping_ratio = damping_ratio
        self._enable_motor = enable_motor
        self._motor_speed = motor_speed
        self._max_motor_force = max_motor_force
        self.world = world

        defn = lib.b2DefaultDistanceJointDef()
        defn.base.bodyIdA = body_a._body_id
        defn.base.bodyIdB = body_b._body_id
        defn.base.collideConnected = collide_connected
        defn.base.localFrameA.p = self._local_anchor_a.b2Vec2[0]
        defn.base.localFrameB.p = self._local_anchor_b.b2Vec2[0]

        if self._length is not None:
            defn.length = self._length
        if self._min_length is not None:
            defn.minLength = self._min_length
        if self._max_length is not None:
            defn.maxLength = self._max_length

        defn.enableLimit = self._enable_limit
        defn.enableSpring = self._enable_spring
        if self._hertz is not None:
            defn.hertz = self._hertz
        if self._damping_ratio is not None:
            defn.dampingRatio = self._damping_ratio
        defn.enableMotor = self._enable_motor
        if self._motor_speed is not None:
            defn.motorSpeed = self._motor_speed
        if self._max_motor_force is not None:
            defn.maxMotorForce = self._max_motor_force

        self._def = defn
        # Clamping the spring's force range is what turns it into a rope or a
        # strut; unbounded in both directions by default.
        if lower_spring_force is not None:
            defn.lowerSpringForce = lower_spring_force
        if upper_spring_force is not None:
            defn.upperSpringForce = upper_spring_force

        self._joint_id = lib.b2CreateDistanceJoint(
            self.world._world_id, ffi.addressof(self._def)
        )
        self._set_userdata()

    length = b2_float(
        lib.b2DistanceJoint_GetLength,
        lib.b2DistanceJoint_SetLength,
        doc="Get the rest length of the joint.",
    )
    current_length = b2_value(
        lib.b2DistanceJoint_GetCurrentLength,
        doc="Get the current distance between anchor points.",
    )
    spring_enabled = b2_bool(
        lib.b2DistanceJoint_IsSpringEnabled,
        lib.b2DistanceJoint_EnableSpring,
        doc="Check if spring behavior is enabled.",
    )
    spring_hertz = b2_float(
        lib.b2DistanceJoint_GetSpringHertz,
        lib.b2DistanceJoint_SetSpringHertz,
        doc="Get spring frequency in Hertz.",
    )
    spring_damping_ratio = b2_float(
        lib.b2DistanceJoint_GetSpringDampingRatio,
        lib.b2DistanceJoint_SetSpringDampingRatio,
        doc="Get spring damping ratio.",
    )
    limit_enabled = b2_bool(
        lib.b2DistanceJoint_IsLimitEnabled,
        lib.b2DistanceJoint_EnableLimit,
        doc="Check if length limits are enabled.",
    )

    @property
    def spring_force_range(self) -> tuple:
        """How hard the spring may pull and push, as ``(lower, upper)`` newtons.

        Clamping the range is what turns a spring into a rope or a strut: a
        lower bound of zero can only push, an upper bound of zero can only
        pull. The default range is unbounded in both directions.
        """
        lower = ffi.new("float*")
        upper = ffi.new("float*")
        lib.b2DistanceJoint_GetSpringForceRange(self._joint_id, lower, upper)
        return (lower[0], upper[0])

    @spring_force_range.setter
    def spring_force_range(self, value):
        lower, upper = value
        lib.b2DistanceJoint_SetSpringForceRange(
            self._joint_id, float(lower), float(upper)
        )

    @property
    def min_length(self):
        """Get the minimum allowed length."""
        return lib.b2DistanceJoint_GetMinLength(self._joint_id)

    @min_length.setter
    def min_length(self, value):
        """Set the minimum allowed length.

        Args:
            value (float): New minimum length
        """
        self.set_length_range(float(value), self.max_length)

    @property
    def max_length(self):
        """Get the maximum allowed length."""
        return lib.b2DistanceJoint_GetMaxLength(self._joint_id)

    @max_length.setter
    def max_length(self, value):
        """Set the maximum allowed length.

        Args:
            value (float): New maximum length
        """
        self.set_length_range(self.min_length, float(value))

    def set_length_range(self, min_length, max_length):
        """Set the allowed length range.

        Args:
            min_length (float): Minimum allowed length
            max_length (float): Maximum allowed length
        """
        lib.b2DistanceJoint_SetLengthRange(
            self._joint_id, float(min_length), float(max_length)
        )

    motor_enabled = b2_bool(
        lib.b2DistanceJoint_IsMotorEnabled,
        lib.b2DistanceJoint_EnableMotor,
        doc="Check if the joint motor is enabled.",
    )
    motor_speed = b2_float(
        lib.b2DistanceJoint_GetMotorSpeed,
        lib.b2DistanceJoint_SetMotorSpeed,
        doc="Get motor speed in meters per second.",
    )
    max_motor_force = b2_float(
        lib.b2DistanceJoint_GetMaxMotorForce,
        lib.b2DistanceJoint_SetMaxMotorForce,
        doc="Get maximum motor force in Newtons.",
    )
    motor_force = b2_value(
        lib.b2DistanceJoint_GetMotorForce,
        doc="Get current motor force in Newtons.",
    )


class MotorJoint(Joint):
    """Drives the relative motion between two bodies.

    Box2D 3.2 rewrote this joint. It no longer takes a target offset and a
    correction factor; it drives a relative *velocity* capped by a maximum
    force, optionally with a spring pulling the bodies toward the joint's rest
    configuration. For the old "pull a body toward a world point" behaviour,
    use :class:`MouseJoint`, which is built on this joint.

    Features:
    - Drive a relative linear and angular velocity
    - Separate force and torque caps for the velocity drive
    - Optional linear and angular springs with their own force caps
    """

    def __init__(
        self,
        world,
        body_a,
        body_b,
        linear_velocity: VectorLike = None,
        angular_velocity=None,
        max_velocity_force=None,
        max_velocity_torque=None,
        linear_hertz=None,
        linear_damping_ratio=None,
        max_spring_force=None,
        angular_hertz=None,
        angular_damping_ratio=None,
        max_spring_torque=None,
        collide_connected=False,
    ):
        """Initialize a motor joint.

        Args:
            world: The physics world instance
            body_a: First body to connect
            body_b: Second body to connect
            linear_velocity (vector-like): Desired relative linear velocity
            angular_velocity (float): Desired relative angular velocity, rad/s
            max_velocity_force (float): Force cap for the linear velocity drive
            max_velocity_torque (float): Torque cap for the angular velocity drive
            linear_hertz (float): Linear spring frequency; 0 disables the spring
            linear_damping_ratio (float): Linear spring damping ratio
            max_spring_force (float): Force cap for the linear spring
            angular_hertz (float): Angular spring frequency; 0 disables the spring
            angular_damping_ratio (float): Angular spring damping ratio
            max_spring_torque (float): Torque cap for the angular spring
            collide_connected (bool): Whether connected bodies can collide
        """
        self.world = world

        defn = lib.b2DefaultMotorJointDef()
        defn.base.bodyIdA = body_a._body_id
        defn.base.bodyIdB = body_b._body_id
        defn.base.collideConnected = collide_connected
        if linear_velocity is not None:
            defn.linearVelocity = Vec2(linear_velocity).b2Vec2[0]
        if angular_velocity is not None:
            defn.angularVelocity = angular_velocity
        if max_velocity_force is not None:
            defn.maxVelocityForce = max_velocity_force
        if max_velocity_torque is not None:
            defn.maxVelocityTorque = max_velocity_torque
        if linear_hertz is not None:
            defn.linearHertz = linear_hertz
        if linear_damping_ratio is not None:
            defn.linearDampingRatio = linear_damping_ratio
        if max_spring_force is not None:
            defn.maxSpringForce = max_spring_force
        if angular_hertz is not None:
            defn.angularHertz = angular_hertz
        if angular_damping_ratio is not None:
            defn.angularDampingRatio = angular_damping_ratio
        if max_spring_torque is not None:
            defn.maxSpringTorque = max_spring_torque

        self._def = defn
        self._joint_id = lib.b2CreateMotorJoint(
            self.world._world_id, ffi.addressof(self._def)
        )
        self._set_userdata()

    @property
    def linear_velocity(self):
        """Get or set the desired relative linear velocity."""
        return Vec2.from_b2Vec2(lib.b2MotorJoint_GetLinearVelocity(self._joint_id))

    @linear_velocity.setter
    def linear_velocity(self, value):
        lib.b2MotorJoint_SetLinearVelocity(self._joint_id, Vec2(value).b2Vec2[0])

    angular_velocity = b2_float(
        lib.b2MotorJoint_GetAngularVelocity,
        lib.b2MotorJoint_SetAngularVelocity,
        doc="Get or set the desired relative angular velocity in radians per second.",
    )
    max_velocity_force = b2_float(
        lib.b2MotorJoint_GetMaxVelocityForce,
        lib.b2MotorJoint_SetMaxVelocityForce,
        doc="Get or set the force cap for the linear velocity drive.",
    )
    max_velocity_torque = b2_float(
        lib.b2MotorJoint_GetMaxVelocityTorque,
        lib.b2MotorJoint_SetMaxVelocityTorque,
        doc="Get or set the torque cap for the angular velocity drive.",
    )
    linear_hertz = b2_float(
        lib.b2MotorJoint_GetLinearHertz,
        lib.b2MotorJoint_SetLinearHertz,
        doc="Get or set the linear spring frequency. Zero disables the spring.",
    )
    linear_damping_ratio = b2_float(
        lib.b2MotorJoint_GetLinearDampingRatio,
        lib.b2MotorJoint_SetLinearDampingRatio,
        doc="Get or set the linear spring damping ratio.",
    )
    max_spring_force = b2_float(
        lib.b2MotorJoint_GetMaxSpringForce,
        lib.b2MotorJoint_SetMaxSpringForce,
        doc="Get or set the force cap for the linear spring.",
    )
    angular_hertz = b2_float(
        lib.b2MotorJoint_GetAngularHertz,
        lib.b2MotorJoint_SetAngularHertz,
        doc="Get or set the angular spring frequency. Zero disables the spring.",
    )
    angular_damping_ratio = b2_float(
        lib.b2MotorJoint_GetAngularDampingRatio,
        lib.b2MotorJoint_SetAngularDampingRatio,
        doc="Get or set the angular spring damping ratio.",
    )
    max_spring_torque = b2_float(
        lib.b2MotorJoint_GetMaxSpringTorque,
        lib.b2MotorJoint_SetMaxSpringTorque,
        doc="Get or set the torque cap for the angular spring.",
    )
