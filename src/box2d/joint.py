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
        self.world = world
        self._joint_id = None
        self._def = self._create_joint_def(body_a, body_b, collide_connected)
        self._create_joint()

    @abstractmethod
    def _create_joint_def(self, body_a, body_b, collide_connected):
        """Define joint configuration parameters (implemented by subclasses).

        Used internally to set up specific joint types with their required
        connection points and physical constraints.
        """
        pass

    def _create_joint(self):
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

    def __del__(self):
        """Safely remove the joint from the physics simulation when destroyed.

        Automatically cleans up the joint connection between bodies if it
        still exists in the world.
        """
        self.destroy()

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
    def reaction_force(self):
        """Current force exerted by the joint to maintain its constraint.

        Returns:
            Vec2: Constraint force vector in world coordinates
        """
        vec = lib.b2Joint_GetConstraintForce(self._joint_id)
        return Vec2(vec.x, vec.y)

    @property
    def reaction_torque(self):
        """Current torque exerted by the joint to maintain rotation constraints.

        Returns:
            float: Constraint torque value
        """
        return lib.b2Joint_GetConstraintTorque(self._joint_id)

    def set_collide_connected(self, collide: bool):
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
            body: Dynamic body to be dragged (automatically wakes up)
            target: Initial world position (x,y) to pull toward (defines anchor point)
            max_force: Maximum force allowed for movement (scales with body mass)
            damping_ratio: Spring damping (0=oscillatory, 1=critically damped)
            hertz: Spring stiffness in Hz (higher = stiffer movement)
        """

        self._target = Vec2(*target)
        self._max_force = max_force
        self._damping_ratio = damping_ratio
        self._hertz = hertz
        super().__init__(world, body, body)
        self.wake_bodies()

    def _create_joint_def(self, body_a, body_b, collide_connected):
        """Configure internal joint parameters (automatically called)."""
        defn = lib.b2DefaultMouseJointDef()
        defn.bodyIdA = body_a._body_id
        defn.bodyIdB = body_b._body_id
        defn.target = self._target.b2Vec2[0]
        defn.maxForce = self._max_force
        defn.dampingRatio = self._damping_ratio
        defn.collideConnected = False
        defn.hertz = self._hertz
        return defn

    def _create_joint(self):
        """Finalize joint creation in physics simulation (internal use)."""
        self._joint_id = lib.b2CreateMouseJoint(
            self.world._world_id, ffi.addressof(self._def)
        )
        super()._create_joint()

    def destroy(self):
        """Destroy the joint and remove it from the world."""
        super().destroy()

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
        """Maximum pulling force available to move the body.

        Returns:
            float: Current force limit (higher values = stronger pulls)
        """
        return lib.b2MouseJoint_GetMaxForce(self._joint_id)

    @max_force.setter
    def max_force(self, value):
        """Adjust maximum pulling force.

        Args:
            value: New force limit (must be positive)
        """
        lib.b2MouseJoint_SetMaxForce(self._joint_id, float(value))

    @property
    def damping_ratio(self):
        """Spring damping controlling movement smoothness.

        Returns:
            float: 0-1 value where 1=critically damped (no overshooting)
        """
        return lib.b2MouseJoint_GetSpringDampingRatio(self._joint_id)

    @damping_ratio.setter
    def damping_ratio(self, value):
        """Set how quickly movement stabilizes at target.

        Args:
            value: 0=no damping (springy), 1=immediate stabilization
        """
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
        collide_connected (bool, optional): If True, the connected bodies will collide. Defaults to False.
        linear_hertz (float, optional): Linear spring stiffness in Hertz (0 means rigid). Defaults to 0.
        linear_damping_ratio (float, optional): Linear damping ratio (non-dimensional). Defaults to 0.
        angular_hertz (float, optional): Angular spring stiffness in Hertz (0 means rigid). Defaults to 0.
        angular_damping_ratio (float, optional): Angular damping ratio (non-dimensional). Defaults to 0.
        reference_angle (float, optional): The reference angle between the two bodies. Defaults to 0.
    """

    def __init__(
        self,
        world,
        body_a,
        body_b,
        local_anchor_a,
        local_anchor_b,
        collide_connected=False,
        linear_hertz=0,
        linear_damping_ratio=0,
        angular_hertz=0,
        angular_damping_ratio=0,
        reference_angle=0,
    ):
        self._local_anchor_a = Vec2(*local_anchor_a)
        self._local_anchor_b = Vec2(*local_anchor_b)
        self._linear_hertz = linear_hertz
        self._linear_damping_ratio = linear_damping_ratio
        self._angular_hertz = angular_hertz
        self._angular_damping_ratio = angular_damping_ratio
        self._reference_angle = reference_angle
        super().__init__(world, body_a, body_b, collide_connected)

    def _create_joint_def(self, body_a, body_b, collide_connected):
        # Get a default weld joint definition from Box2D.
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

        return defn

    def _create_joint(self):
        # Create the weld joint using the corresponding lib function.
        self._joint_id = lib.b2CreateWeldJoint(
            self.world._world_id, ffi.addressof(self._def)
        )
        super()._create_joint()

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
        super().__init__(world, body_a, body_b, collide_connected)

    def _create_joint_def(self, body_a, body_b, collide_connected):
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

        return defn

    def _create_joint(self):
        # Create the joint in the Box2D world using the revolute joint creation function.
        self._joint_id = lib.b2CreateRevoluteJoint(
            self.world._world_id, ffi.addressof(self._def)
        )
        super()._create_joint()

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
