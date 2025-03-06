# joint.py

from box2d._box2d import lib, ffi
from abc import ABC, abstractmethod
from .math import Vec2


class Joint(ABC):
    """Base class for all physics joints connecting two rigid bodies.

    Manages the lifecycle and common properties of constraints between bodies,
    such as anchors and collision handling between connected bodies.
    """

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

    def destroy(self):
        """Destroy the joint and remove it from the world."""
        if self._joint_id and lib.b2Joint_IsValid(self._joint_id):
            lib.b2DestroyJoint(self._joint_id)
        self._joint_id = None

    @property
    def is_valid(self):
        """Check if the joint is currently active in the simulation.

        Returns:
            True if the joint still connects its bodies, False if it has been
            removed or destroyed
        """
        return lib.b2Joint_IsValid(self._joint_id)

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
    def anchor_a(self):
        """Local connection point on the first body.

        Returns:
            Vec2: Position where the joint attaches to body_a in its local coordinates
        """
        vec = lib.b2Joint_GetLocalAnchorA(self._joint_id)
        return Vec2(vec.x, vec.y)

    @property
    def anchor_b(self):
        """Local connection point on the second body.

        Returns:
            Vec2: Position where the joint attaches to body_b in its local coordinates
        """
        vec = lib.b2Joint_GetLocalAnchorB(self._joint_id)
        return Vec2(vec.x, vec.y)

    @property
    def constraint_force(self):
        """Current force exerted by the joint to maintain its constraint.

        Returns:
            Vec2: Constraint force vector in world coordinates
        """
        vec = lib.b2Joint_GetConstraintForce(self._joint_id)
        return Vec2(vec.x, vec.y)

    @property
    def constraint_torque(self):
        """Current torque exerted by the joint to maintain rotation constraints.

        Returns:
            float: Constraint torque value
        """
        return lib.b2Joint_GetConstraintTorque(self._joint_id)

    @property
    def collide_connected(self) -> bool:
        """Check if connected bodies can collide with each other.

        Returns:
            bool: True if connected bodies can collide, False otherwise
        """
        return lib.b2Joint_GetCollideConnected(self._joint_id)

    @collide_connected.setter
    def collide_connected(self, collide: bool):
        """Control whether connected bodies can collide with each other.

        Args:
            collide: True to enable collisions between bodies, False to disable
        """
        lib.b2Joint_SetCollideConnected(self._joint_id, collide)

    def wake_bodies(self):
        """Ensure connected bodies are active and responsive to movement.

        Useful when restarting dragging after bodies entered sleep state.
        """
        lib.b2Joint_WakeBodies(self._joint_id)


class MouseJoint(Joint):
    """Interactive joint for dragging bodies with mouse-like movement.

    Designed for smoothly pulling dynamic bodies to target positions,
    with spring-like behavior controls for realistic manipulation.
    """

    def __init__(
        self, world, body, target, max_force=1000.0, damping_ratio=0.7, hertz=5.0
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

        self._target = Vec2(*target)
        self._max_force = max_force
        self._damping_ratio = damping_ratio
        self._hertz = hertz
        self.world = world
        defn = lib.b2DefaultMouseJointDef()
        defn.bodyIdA = body._body_id
        defn.bodyIdB = body._body_id
        defn.target = self._target.b2Vec2[0]
        defn.maxForce = self._max_force
        defn.dampingRatio = self._damping_ratio
        defn.collideConnected = False
        defn.hertz = self._hertz
        self._def = defn
        self._joint_id = lib.b2CreateMouseJoint(
            self.world._world_id, ffi.addressof(self._def)
        )
        self._set_userdata()
        self.wake_bodies()

    @property
    def target(self):
        """Current target position to drag toward.

        Returns:
            Vec2: World coordinates of the drag target
        """
        return Vec2.from_b2Vec2(lib.b2MouseJoint_GetTarget(self._joint_id))

    @target.setter
    def target(self, value):
        """Update the position being dragged toward.

        Args:
            value (tuple/Vec2): New target position in world coordinates
        """
        vec = ffi.new("b2Vec2*", {"x": value[0], "y": value[1]})
        lib.b2MouseJoint_SetTarget(self._joint_id, vec[0])

    @property
    def max_force(self):
        """Maximum pulling force available to move the body."""
        return lib.b2MouseJoint_GetMaxForce(self._joint_id)

    @max_force.setter
    def max_force(self, value):
        """Adjust maximum pulling force."""
        lib.b2MouseJoint_SetMaxForce(self._joint_id, float(value))

    @property
    def damping_ratio(self):
        """Spring damping controlling movement smoothness."""
        return lib.b2MouseJoint_GetSpringDampingRatio(self._joint_id)

    @damping_ratio.setter
    def damping_ratio(self, value):
        """Set how quickly movement stabilizes at target."""
        lib.b2MouseJoint_SetSpringDampingRatio(self._joint_id, float(value))


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
        local_anchor_a,
        local_anchor_b,
        collide_connected=False,
        linear_hertz=None,
        linear_damping_ratio=None,
        angular_hertz=None,
        angular_damping_ratio=None,
        reference_angle=None,
    ):
        self._local_anchor_a = Vec2(*local_anchor_a)
        self._local_anchor_b = Vec2(*local_anchor_b)
        self._linear_hertz = linear_hertz
        self._linear_damping_ratio = linear_damping_ratio
        self._angular_hertz = angular_hertz
        self._angular_damping_ratio = angular_damping_ratio
        self._reference_angle = reference_angle
        self.world = world
        defn = lib.b2DefaultWeldJointDef()
        defn.bodyIdA = body_a._body_id
        defn.bodyIdB = body_b._body_id
        defn.collideConnected = collide_connected

        # Use the provided local anchor points directly.
        defn.localAnchorA = self._local_anchor_a.b2Vec2[0]
        defn.localAnchorB = self._local_anchor_b.b2Vec2[0]
        if self._reference_angle is not None:
            defn.referenceAngle = self._reference_angle

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

    @property
    def linear_hertz(self):
        """The linear stiffness (in Hertz) of the weld joint spring."""
        return lib.b2WeldJoint_GetLinearHertz(self._joint_id)

    @linear_hertz.setter
    def linear_hertz(self, value):
        lib.b2WeldJoint_SetLinearHertz(self._joint_id, float(value))

    @property
    def linear_damping_ratio(self):
        """The linear damping ratio (non-dimensional) of the weld joint spring."""
        return lib.b2WeldJoint_GetLinearDampingRatio(self._joint_id)

    @linear_damping_ratio.setter
    def linear_damping_ratio(self, value):
        lib.b2WeldJoint_SetLinearDampingRatio(self._joint_id, float(value))

    @property
    def angular_hertz(self):
        """The angular stiffness (in Hertz) of the weld joint."""
        return lib.b2WeldJoint_GetAngularHertz(self._joint_id)

    @angular_hertz.setter
    def angular_hertz(self, value):
        lib.b2WeldJoint_SetAngularHertz(self._joint_id, float(value))

    @property
    def angular_damping_ratio(self):
        """The angular damping ratio (non-dimensional) of the weld joint."""
        return lib.b2WeldJoint_GetAngularDampingRatio(self._joint_id)

    @angular_damping_ratio.setter
    def angular_damping_ratio(self, value):
        lib.b2WeldJoint_SetAngularDampingRatio(self._joint_id, float(value))


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
        anchor_a,
        anchor_b,
        collide_connected=False,
        lower_angle=None,
        upper_angle=None,
        enable_limit=None,
        motor_speed=None,
        max_motor_torque=None,
        enable_motor=None,
        reference_angle=None,
    ):
        """
        Initialize a revolute joint with separate local anchor points for each body.

        Args:
            world: The physics world instance.
            body_a: The first body to connect.
            body_b: The second body to connect.
            anchor_a (tuple): The local (x, y) coordinates on body_a for the joint.
            anchor_b (tuple): The local (x, y) coordinates on body_b for the joint.
            collide_connected (bool, optional): If True, connected bodies will collide.
            lower_angle (float, optional): Lower joint limit in radians.
            upper_angle (float, optional): Upper joint limit in radians.
            enable_limit (bool, optional): Whether to enable joint limits.
            motor_speed (float, optional): Desired motor speed in radians/sec.
            max_motor_torque (float, optional): Maximum motor torque in newton-meters.
            enable_motor (bool, optional): Whether to enable the joint motor.
            reference_angle (float, optional): Reference angle between the two bodies.
        """
        self._localAnchorA = Vec2(*anchor_a)
        self._localAnchorB = Vec2(*anchor_b)
        self._lower_angle = lower_angle
        self._upper_angle = upper_angle
        self._enable_limit = enable_limit
        self._motor_speed = motor_speed
        self._max_motor_torque = max_motor_torque
        self._enable_motor = enable_motor
        self._reference_angle = reference_angle

        # Get a default revolute joint definition from Box2D.
        defn = lib.b2DefaultRevoluteJointDef()
        defn.bodyIdA = body_a._body_id
        defn.bodyIdB = body_b._body_id
        defn.collideConnected = collide_connected

        # Use the provided local anchors for each body.
        defn.localAnchorA = self._localAnchorA.b2Vec2[0]
        defn.localAnchorB = self._localAnchorB.b2Vec2[0]

        if self._reference_angle is not None:
            defn.referenceAngle = self._reference_angle

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

        self._def = defn
        self.world = world
        self._joint_id = lib.b2CreateRevoluteJoint(
            self.world._world_id, ffi.addressof(self._def)
        )
        self._set_userdata()

    @property
    def angle(self):
        """Current joint angle in radians relative to the reference angle."""
        return lib.b2RevoluteJoint_GetAngle(self._joint_id)

    @property
    def motor_speed(self):
        """Desired motor speed in radians per second."""
        return lib.b2RevoluteJoint_GetMotorSpeed(self._joint_id)

    @motor_speed.setter
    def motor_speed(self, value):
        lib.b2RevoluteJoint_SetMotorSpeed(self._joint_id, float(value))

    @property
    def max_motor_torque(self):
        """Maximum motor torque in newton-meters."""
        return lib.b2RevoluteJoint_GetMaxMotorTorque(self._joint_id)

    @max_motor_torque.setter
    def max_motor_torque(self, value):
        lib.b2RevoluteJoint_SetMaxMotorTorque(self._joint_id, float(value))

    @property
    def lower_limit(self):
        """The lower joint limit in radians."""
        return lib.b2RevoluteJoint_GetLowerLimit(self._joint_id)

    @property
    def upper_limit(self):
        """The upper joint limit in radians."""
        return lib.b2RevoluteJoint_GetUpperLimit(self._joint_id)

    def set_limits(self, lower, upper):
        """
        Set the joint limits in radians.

        Args:
            lower (float): Lower limit angle.
            upper (float): Upper limit angle.
        """
        lib.b2RevoluteJoint_SetLimits(self._joint_id, float(lower), float(upper))


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
        anchor_a,
        anchor_b,
        axis,
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
    ):
        """Initialize a prismatic joint between two bodies.

        Args:
            world: The physics world instance
            body_a: First body to connect
            body_b: Second body to connect
            anchor_a (tuple): Local anchor point on body A (x,y)
            anchor_b (tuple): Local anchor point on body B (x,y)
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
        self._local_anchor_a = Vec2(*anchor_a)
        self._local_anchor_b = Vec2(*anchor_b)
        self._local_axis_a = Vec2(*axis)
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
        defn.bodyIdA = body_a._body_id
        defn.bodyIdB = body_b._body_id
        defn.collideConnected = collide_connected
        defn.localAnchorA = self._local_anchor_a.b2Vec2[0]
        defn.localAnchorB = self._local_anchor_b.b2Vec2[0]
        defn.localAxisA = self._local_axis_a.b2Vec2[0]

        if self._reference_angle is not None:
            defn.referenceAngle = self._reference_angle
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

        self._def = defn

        self._joint_id = lib.b2CreatePrismaticJoint(
            self.world._world_id, ffi.addressof(self._def)
        )
        self._set_userdata()

    @property
    def joint_translation(self):
        """Get the current joint translation."""
        return lib.b2PrismaticJoint_GetJointTranslation(self._joint_id)

    @property
    def joint_speed(self):
        """Get the current joint linear speed."""
        return lib.b2PrismaticJoint_GetJointSpeed(self._joint_id)

    @property
    def limit_enabled(self):
        """Check if the joint limit is enabled."""
        return lib.b2PrismaticJoint_IsLimitEnabled(self._joint_id)

    @limit_enabled.setter
    def limit_enabled(self, enable):
        """Enable/disable the joint limit.

        Args:
            enable (bool): True to enable limits, False to disable
        """
        lib.b2PrismaticJoint_EnableLimit(self._joint_id, enable)

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

    @property
    def motor_enabled(self):
        """Check if the joint motor is enabled."""
        return lib.b2PrismaticJoint_IsMotorEnabled(self._joint_id)

    @motor_enabled.setter
    def motor_enabled(self, enable):
        """Enable/disable the joint motor.

        Args:
            enable (bool): True to enable motor, False to disable
        """
        lib.b2PrismaticJoint_EnableMotor(self._joint_id, enable)

    @property
    def motor_speed(self):
        """Get the motor speed in meters per second."""
        return lib.b2PrismaticJoint_GetMotorSpeed(self._joint_id)

    @motor_speed.setter
    def motor_speed(self, speed):
        """Set the motor speed.

        Args:
            speed (float): Desired speed in meters per second
        """
        lib.b2PrismaticJoint_SetMotorSpeed(self._joint_id, float(speed))

    @property
    def max_motor_force(self):
        """Get maximum motor force in Newtons."""
        return lib.b2PrismaticJoint_GetMaxMotorForce(self._joint_id)

    @max_motor_force.setter
    def max_motor_force(self, force):
        """Set the maximum motor force.

        Args:
            force (float): Maximum force in Newtons
        """
        lib.b2PrismaticJoint_SetMaxMotorForce(self._joint_id, float(force))

    @property
    def motor_force(self):
        """Get the current motor force in Newtons."""
        return lib.b2PrismaticJoint_GetMotorForce(self._joint_id)

    @property
    def spring_enabled(self):
        """Check if spring behavior is enabled."""
        return lib.b2PrismaticJoint_IsSpringEnabled(self._joint_id)

    @spring_enabled.setter
    def spring_enabled(self, enable):
        """Enable/disable spring behavior.

        Args:
            enable (bool): True to enable spring, False to disable
        """
        lib.b2PrismaticJoint_EnableSpring(self._joint_id, enable)

    @property
    def spring_hertz(self):
        """Get spring frequency in Hertz."""
        return lib.b2PrismaticJoint_GetSpringHertz(self._joint_id)

    @spring_hertz.setter
    def spring_hertz(self, hertz):
        """Set spring oscillation frequency.

        Args:
            hertz (float): Frequency in Hertz (cycles/sec)
        """
        lib.b2PrismaticJoint_SetSpringHertz(self._joint_id, float(hertz))

    @property
    def spring_damping_ratio(self):
        """Get spring damping ratio."""
        return lib.b2PrismaticJoint_GetSpringDampingRatio(self._joint_id)

    @spring_damping_ratio.setter
    def spring_damping_ratio(self, damping):
        """Set spring damping ratio.

        Args:
            damping (float): Damping ratio.
        """
        lib.b2PrismaticJoint_SetSpringDampingRatio(self._joint_id, float(damping))


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
        anchor_a,
        anchor_b,
        axis,
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
            anchor_a (tuple): Local anchor point on body A (x,y)
            anchor_b (tuple): Local anchor point on body B (x,y)
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
        self._local_anchor_a = Vec2(*anchor_a)
        self._local_anchor_b = Vec2(*anchor_b)
        self._local_axis_a = Vec2(*axis)
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
        defn.bodyIdA = body_a._body_id
        defn.bodyIdB = body_b._body_id
        defn.collideConnected = collide_connected
        defn.localAnchorA = self._local_anchor_a.b2Vec2[0]
        defn.localAnchorB = self._local_anchor_b.b2Vec2[0]
        defn.localAxisA = self._local_axis_a.b2Vec2[0]
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

    @property
    def spring_enabled(self):
        """Check if spring behavior is enabled."""
        return lib.b2WheelJoint_IsSpringEnabled(self._joint_id)

    @spring_enabled.setter
    def spring_enabled(self, enable):
        """Enable/disable spring behavior.

        Args:
            enable (bool): True to enable spring, False to disable
        """
        lib.b2WheelJoint_EnableSpring(self._joint_id, enable)

    @property
    def spring_hertz(self):
        """Get spring frequency in Hertz."""
        return lib.b2WheelJoint_GetSpringHertz(self._joint_id)

    @spring_hertz.setter
    def spring_hertz(self, hertz):
        """Set spring frequency.

        Args:
            hertz (float): Frequency in Hz
        """
        lib.b2WheelJoint_SetSpringHertz(self._joint_id, float(hertz))

    @property
    def spring_damping_ratio(self):
        """Get spring damping ratio (non-dimensional)."""
        return lib.b2WheelJoint_GetSpringDampingRatio(self._joint_id)

    @spring_damping_ratio.setter
    def spring_damping_ratio(self, damping):
        """Set spring damping ratio.

        Args:
            damping (float): Damping ratio (non-dimensional)
        """
        lib.b2WheelJoint_SetSpringDampingRatio(self._joint_id, float(damping))

    @property
    def limit_enabled(self):
        """Check if translation limits are enabled."""
        return lib.b2WheelJoint_IsLimitEnabled(self._joint_id)

    @limit_enabled.setter
    def limit_enabled(self, enable):
        """Enable/disable translation limits.

        Args:
            enable (bool): True to enable limits, False to disable
        """
        lib.b2WheelJoint_EnableLimit(self._joint_id, enable)

    @property
    def lower_limit(self):
        """Get lower translation limit."""
        return lib.b2WheelJoint_GetLowerLimit(self._joint_id)

    @property
    def upper_limit(self):
        """Get upper translation limit."""
        return lib.b2WheelJoint_GetUpperLimit(self._joint_id)

    def set_limits(self, lower, upper):
        """Set the translation limits.

        Args:
            lower (float): Lower translation limit
            upper (float): Upper translation limit
        """
        lib.b2WheelJoint_SetLimits(self._joint_id, float(lower), float(upper))

    @property
    def motor_enabled(self):
        """Check if joint motor is enabled."""
        return lib.b2WheelJoint_IsMotorEnabled(self._joint_id)

    @motor_enabled.setter
    def motor_enabled(self, enable):
        """Enable/disable the joint motor.

        Args:
            enable (bool): True to enable motor, False to disable
        """
        lib.b2WheelJoint_EnableMotor(self._joint_id, enable)

    @property
    def motor_speed(self):
        """Get motor speed in radians per second."""
        return lib.b2WheelJoint_GetMotorSpeed(self._joint_id)

    @motor_speed.setter
    def motor_speed(self, speed):
        """Set motor speed.

        Args:
            speed (float): Speed in radians per second
        """
        lib.b2WheelJoint_SetMotorSpeed(self._joint_id, float(speed))

    @property
    def max_motor_torque(self):
        """Get maximum motor torque in N-m."""
        return lib.b2WheelJoint_GetMaxMotorTorque(self._joint_id)

    @max_motor_torque.setter
    def max_motor_torque(self, torque):
        """Set maximum motor torque.

        Args:
            torque (float): Maximum torque in N-m
        """
        lib.b2WheelJoint_SetMaxMotorTorque(self._joint_id, float(torque))

    @property
    def motor_torque(self):
        """Get current motor torque in N-m."""
        return lib.b2WheelJoint_GetMotorTorque(self._joint_id)


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
        anchor_a,
        anchor_b,
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
    ):
        """Initialize a distance joint between two bodies.

        Args:
            world: The physics world instance
            body_a: First body to connect
            body_b: Second body to connect
            anchor_a (tuple): Local anchor point on body A (x,y)
            anchor_b (tuple): Local anchor point on body B (x,y)
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
        self._local_anchor_a = Vec2(*anchor_a)
        self._local_anchor_b = Vec2(*anchor_b)
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
        defn.bodyIdA = body_a._body_id
        defn.bodyIdB = body_b._body_id
        defn.collideConnected = collide_connected
        defn.localAnchorA = self._local_anchor_a.b2Vec2[0]
        defn.localAnchorB = self._local_anchor_b.b2Vec2[0]

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
        self._joint_id = lib.b2CreateDistanceJoint(
            self.world._world_id, ffi.addressof(self._def)
        )
        self._set_userdata()

    @property
    def length(self):
        """Get the rest length of the joint."""
        return lib.b2DistanceJoint_GetLength(self._joint_id)

    @length.setter
    def length(self, value):
        """Set the rest length of the joint.

        Args:
            value (float): New rest length
        """
        lib.b2DistanceJoint_SetLength(self._joint_id, float(value))

    @property
    def current_length(self):
        """Get the current distance between anchor points."""
        return lib.b2DistanceJoint_GetCurrentLength(self._joint_id)

    @property
    def spring_enabled(self):
        """Check if spring behavior is enabled."""
        return lib.b2DistanceJoint_IsSpringEnabled(self._joint_id)

    @spring_enabled.setter
    def spring_enabled(self, enable):
        """Enable/disable spring behavior.

        Args:
            enable (bool): True to enable spring, False for rigid behavior
        """
        lib.b2DistanceJoint_EnableSpring(self._joint_id, enable)

    @property
    def spring_hertz(self):
        """Get spring frequency in Hertz."""
        return lib.b2DistanceJoint_GetSpringHertz(self._joint_id)

    @spring_hertz.setter
    def spring_hertz(self, hertz):
        """Set spring frequency in Hertz.

        Args:
            hertz (float): Oscillation frequency in Hz
        """
        lib.b2DistanceJoint_SetSpringHertz(self._joint_id, float(hertz))

    @property
    def spring_damping_ratio(self):
        """Get spring damping ratio."""
        return lib.b2DistanceJoint_GetSpringDampingRatio(self._joint_id)

    @spring_damping_ratio.setter
    def spring_damping_ratio(self, damping):
        """Set spring damping ratio.

        Args:
            damping (float): Damping ratio [0,1]
        """
        lib.b2DistanceJoint_SetSpringDampingRatio(self._joint_id, float(damping))

    @property
    def limit_enabled(self):
        """Check if length limits are enabled."""
        return lib.b2DistanceJoint_IsLimitEnabled(self._joint_id)

    @limit_enabled.setter
    def limit_enabled(self, enable):
        """Enable/disable length limits.

        Args:
            enable (bool): True to enable limits, False to disable
        """
        lib.b2DistanceJoint_EnableLimit(self._joint_id, enable)

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

    @property
    def motor_enabled(self):
        """Check if the joint motor is enabled."""
        return lib.b2DistanceJoint_IsMotorEnabled(self._joint_id)

    @motor_enabled.setter
    def motor_enabled(self, enable):
        """Enable/disable the joint motor.

        Args:
            enable (bool): True to enable motor, False to disable
        """
        lib.b2DistanceJoint_EnableMotor(self._joint_id, enable)

    @property
    def motor_speed(self):
        """Get motor speed in meters per second."""
        return lib.b2DistanceJoint_GetMotorSpeed(self._joint_id)

    @motor_speed.setter
    def motor_speed(self, speed):
        """Set motor speed.

        Args:
            speed (float): Desired speed in meters per second
        """
        lib.b2DistanceJoint_SetMotorSpeed(self._joint_id, float(speed))

    @property
    def max_motor_force(self):
        """Get maximum motor force in Newtons."""
        return lib.b2DistanceJoint_GetMaxMotorForce(self._joint_id)

    @max_motor_force.setter
    def max_motor_force(self, force):
        """Set maximum motor force.

        Args:
            force (float): Maximum force in Newtons
        """
        lib.b2DistanceJoint_SetMaxMotorForce(self._joint_id, float(force))

    @property
    def motor_force(self):
        """Get current motor force in Newtons."""
        return lib.b2DistanceJoint_GetMotorForce(self._joint_id)


class MotorJoint(Joint):
    """A motor joint is used to control the relative motion between two bodies.

    The motor joint is used to drive the relative transform between two bodies.
    It takes a relative position and rotation and applies the forces and torques
    needed to achieve that relative transform over time.

    A typical usage is to control the movement of a dynamic body with respect
    to the ground.

    Features:
    - Control relative linear position between bodies
    - Control relative angular position between bodies
    - Maximum force and torque limits
    - Position correction factor for stability
    """

    def __init__(
        self,
        world,
        body_a,
        body_b,
        linear_offset=None,
        angular_offset=None,
        max_force=None,
        max_torque=None,
        correction_factor=None,
        collide_connected=False,
    ):
        """Initialize a motor joint.

        Args:
            world: The physics world instance
            body_a: First body to connect
            body_b: Second body to connect
            linear_offset (tuple): Position of bodyB minus bodyA, in bodyA's frame
            angular_offset (float): Angle of bodyB minus bodyA in radians
            max_force (float): Maximum force in Newtons
            max_torque (float): Maximum torque in Newton-meters
            correction_factor (float): Position correction factor in range [0,1]
            collide_connected (bool): Whether connected bodies can collide
        """
        self._linear_offset = linear_offset
        self._angular_offset = angular_offset
        self._max_force = max_force
        self._max_torque = max_torque
        self._correction_factor = correction_factor
        self.world = world

        defn = lib.b2DefaultMotorJointDef()
        defn.bodyIdA = body_a._body_id
        defn.bodyIdB = body_b._body_id
        defn.collideConnected = collide_connected
        if linear_offset is not None:
            defn.linearOffset = Vec2(*self._linear_offset).b2Vec2[0]
        if angular_offset is not None:
            defn.angularOffset = self._angular_offset
        if max_force is not None:
            defn.maxForce = self._max_force
        if max_torque is not None:
            defn.maxTorque = self._max_torque
        if correction_factor is not None:
            defn.correctionFactor = self._correction_factor

        self._def = defn
        self._joint_id = lib.b2CreateMotorJoint(
            self.world._world_id, ffi.addressof(self._def)
        )
        self._set_userdata()

    @property
    def linear_offset(self):
        """Get the target linear offset in bodyA's frame."""
        return Vec2.from_b2Vec2(lib.b2MotorJoint_GetLinearOffset(self._joint_id))

    @linear_offset.setter
    def linear_offset(self, offset):
        """Set the target linear offset in bodyA's frame.

        Args:
            offset (tuple/Vec2): Target position of bodyB in bodyA frame
        """
        vec = Vec2(*offset)
        lib.b2MotorJoint_SetLinearOffset(self._joint_id, vec.b2Vec2[0])

    @property
    def angular_offset(self):
        """Get the target angular offset in radians."""
        return lib.b2MotorJoint_GetAngularOffset(self._joint_id)

    @angular_offset.setter
    def angular_offset(self, angle):
        """Set the target angular offset.

        Args:
            angle (float): Target angle in radians
        """
        lib.b2MotorJoint_SetAngularOffset(self._joint_id, float(angle))

    @property
    def max_force(self):
        """Get maximum force in Newtons."""
        return lib.b2MotorJoint_GetMaxForce(self._joint_id)

    @max_force.setter
    def max_force(self, force):
        """Set the maximum force in Newtons.

        Args:
            force (float): Maximum force value
        """
        lib.b2MotorJoint_SetMaxForce(self._joint_id, float(force))

    @property
    def max_torque(self):
        """Get maximum torque in Newton-meters."""
        return lib.b2MotorJoint_GetMaxTorque(self._joint_id)

    @max_torque.setter
    def max_torque(self, torque):
        """Set the maximum torque in Newton-meters.

        Args:
            torque (float): Maximum torque value
        """
        lib.b2MotorJoint_SetMaxTorque(self._joint_id, float(torque))

    @property
    def correction_factor(self):
        """Get position correction factor [0,1]."""
        return lib.b2MotorJoint_GetCorrectionFactor(self._joint_id)

    @correction_factor.setter
    def correction_factor(self, factor):
        """Set the position correction factor.

        Args:
            factor (float): Correction factor in range [0,1]
        """
        lib.b2MotorJoint_SetCorrectionFactor(self._joint_id, float(factor))
