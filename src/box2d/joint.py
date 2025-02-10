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

        # Auto-create static body for joint anchor
        self._ground_body = world.new_body().static().position(0, 0).build()
        self._target = Vec2(*target)
        self._max_force = max_force
        self._damping_ratio = damping_ratio
        self._hertz = hertz
        super().__init__(world, self._ground_body, body)
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
