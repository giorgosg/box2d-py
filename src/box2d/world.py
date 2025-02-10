# src/box3d/world.py

from ._box2d import lib, ffi
from .body import BodyBuilder, Body
from .joint import MouseJoint
from .math import Vec2, VectorLike, AABB
from .debug_draw import DebugDraw


class World:
    """2D physics world containing bodies, joints, and simulation parameters.

    Manages Box2D world state and provides body creation through a builder pattern.
    Wraps Box2D's b2World functionality with Pythonic interfaces.

    Example:
        >>> world = World(gravity=(0, -9.81))
        >>> body = world.new_body().dynamic().position(0, 5).box(1, 1).build()
        >>> for _ in range(60):
        ...     world.step(1/60, 4)
    """

    def __init__(self, gravity: VectorLike = (0, -10)):
        """Initialize physics world with specified gravity vector.

        Args:
            gravity: Initial gravitational acceleration (x,y) in m/s².

        Example:
            >>> world = World(gravity=(0, -9.8))
            >>> world.gravity
            Vec2(0.0, -9.8)
        """
        world_def = lib.b2DefaultWorldDef()
        world_def.gravity.x, world_def.gravity.y = gravity
        self._world_id = lib.b2CreateWorld(ffi.addressof(world_def))

        # Store default simulation parameters
        self._enable_sleep = world_def.enableSleep
        self._enable_continuous = world_def.enableContinuous
        self._restitution_threshold = world_def.restitutionThreshold
        self._hit_event_threshold = world_def.hitEventThreshold
        self._contact_hertz = world_def.contactHertz
        self._contact_damping_ratio = world_def.contactDampingRatio
        self._contact_push_velocity = world_def.contactPushMaxSpeed

        self._bodies = {}

    @property
    def gravity(self):
        """World gravity vector (m/s²).

        Example:
            >>> world = World()
            >>> world.gravity = (0, -9.81)
            >>> world.gravity
            Vec2(0.0, -9.81)
        """
        g = lib.b2World_GetGravity(self._world_id)
        return Vec2(g.x, g.y)

    @gravity.setter
    def gravity(self, value):
        """Set world gravity vector"""
        x, y = value
        vec = ffi.new("b2Vec2*", {"x": value[0], "y": value[1]})
        lib.b2World_SetGravity(self._world_id, vec[0])

    def step(self, time_step, substep_count=4):
        """Advance simulation by time step.

        Args:
            time_step: Time to simulate (seconds)
            substep_count: Number of solver iterations (default 4)
                           Higher values improve stability at cost of performance

        Example:
            >>> world = World()
            >>> world.step(1/60)  # Default 4 substeps
            >>> world.step(0.016, 6)  # Custom substep count
        """
        lib.b2World_Step(self._world_id, time_step, substep_count)

    def new_body(self):
        """Create BodyBuilder for constructing bodies. Entry point for body creation.

        Returns:
            BodyBuilder: Fluent interface for body configuration

        Example:
            >>> world = World()
            >>> builder = world.new_body()
            >>> body = builder.dynamic().position(2,3).circle(1).build()
        """
        return BodyBuilder(self)

    def add_mouse_joint(self, body, target, max_force=1000.0, damping_ratio=0.7):
        """Create a mouse joint for interactive dragging between bodies

        Args:
            body: Body to drag
            target: Initial target position in world coordinates
            max_force: Maximum constraint force (default 1000.0)
            damping_ratio: Response damping ratio (0-1, default 0.7)

        Example:
            >>> world = World()
            >>> box = world.new_body().dynamic().position(0,5).build()
            >>> mouse_joint = world.add_mouse_joint(box, (0,5))
        """
        if body._body_id not in self._bodies:
            raise ValueError("Bodies must belong to this world")
        return MouseJoint(self, body, target, max_force, damping_ratio)

    def _track_body(self, body: "Body"):
        """Internal method to track body references. Called automatically during body creation.

        Args:
            body: Body instance to register in the world
        """
        self._bodies[body._body_id] = body

    @property
    def bodies(self):
        """Get list of all active bodies in the world.

        Returns:
            list[Body]: Copies of registered body references

        Example:
            >>> world = World()
            >>> box = world.new_body().dynamic().build()
            >>> len(world.bodies)
            1
        """
        return list(self._bodies.values())

    def draw(self, debug_draw: DebugDraw):
        """Render world state using debug drawing interface.

        Args:
            debug_draw: Configured DebugDraw instance for visualization

        Example:
            >>> world = World()
            >>> debug_draw = DebugDraw()
            >>> world.draw(debug_draw)
        """
        lib.b2World_Draw(self._world_id, ffi.addressof(debug_draw._debug_draw))

    def query_aabb(self, aabb: AABB) -> list:
        """Find shapes overlapping axis-aligned bounding box.

        Args:
            aabb: Axis-aligned bounding box to query

        Returns:
            list: Shapes with overlapping fixtures

        Example:
            >>> world = World()
            >>> box = world.new_body().dynamic().position(0,0).box(1,1).build()
            >>> aabb = AABB(lower=(-1,-1), upper=(1,1))
            >>> overlaps = world.query_aabb(aabb)
            >>> len(overlaps) > 0
            True
        """
        results = []

        @ffi.callback("bool(b2ShapeId, void*)")
        def _overlap_callback(shape_id, _):
            shape = ffi.from_handle(lib.b2Shape_GetUserData(shape_id))
            results.append(shape)
            return True  # Continue querying

        # Use a default filter
        c_filter = lib.b2DefaultQueryFilter()

        lib.b2World_OverlapAABB(
            self._world_id,
            {
                "lowerBound": {"x": aabb.lower.x, "y": aabb.lower.y},
                "upperBound": {"x": aabb.upper.x, "y": aabb.upper.y},
            },
            {"categoryBits": 0x0001, "maskBits": 0xFFFF},
            _overlap_callback,
            ffi.NULL,
        )
        return results

    def destroy(self):
        """Destroy the world.

        Example:
            >>> world = World()
            >>> world.destroy()
        """
        if hasattr(self, "_world_id"):
            lib.b2DestroyWorld(self._world_id)
            del self._world_id

    def __del__(self):
        """Clean up world resources. Automatically called when instance is garbage collected.

        Destroys Box2D world instance.
        """
        self.destroy()

    @property
    def enable_sleep(self) -> bool:
        """Control whether bodies can enter sleep state to save computation.

        When enabled, inactive bodies will stop simulating until awakened.

        Example:
            >>> world = World()
            >>> world.enable_sleep = False  # Disable sleeping entirely
        """
        return self._enable_sleep

    @enable_sleep.setter
    def enable_sleep(self, value: bool):
        self._enable_sleep = bool(value)
        lib.b2World_EnableSleeping(self._world_id, self._enable_sleep)

    @property
    def enable_continuous(self) -> bool:
        """Toggle continuous collision detection for dynamic vs static bodies.

        Helps prevent fast-moving objects from tunneling through static geometry.

        Example:
            >>> world = World()
            >>> world.enable_continuous = False  # Disable CCD for static
        """
        return self._enable_continuous

    @enable_continuous.setter
    def enable_continuous(self, value: bool):
        self._enable_continuous = bool(value)
        lib.b2World_EnableContinuous(self._world_id, self._enable_continuous)

    @property
    def restitution_threshold(self) -> float:
        """Minimum collision speed for restitution effects (m/s).

        Collisions slower than this threshold will have zero restitution.

        Example:
            >>> world = World()
            >>> world.restitution_threshold = 2.0  # Only apply restitution above 2m/s
        """
        return self._restitution_threshold

    @restitution_threshold.setter
    def restitution_threshold(self, value: float):
        self._restitution_threshold = float(value)
        lib.b2World_SetRestitutionThreshold(self._world_id, self._restitution_threshold)

    @property
    def hit_event_threshold(self) -> float:
        """Minimum collision speed to trigger hit events (m/s).

        Collisions slower than this won't generate collision events.

        Example:
            >>> world = World()
            >>> world.hit_event_threshold = 0.5  # Get events for slower impacts
        """
        return self._hit_event_threshold

    @hit_event_threshold.setter
    def hit_event_threshold(self, value: float):
        self._hit_event_threshold = float(value)
        lib.b2World_SetHitEventThreshold(self._world_id, self._hit_event_threshold)

    @property
    def contact_hertz(self) -> float:
        """Contact constraint stiffness frequency (Hz).

        Higher values make contacts stiffer/more rigid.

        Example:
            >>> world = World()
            >>> world.contact_hertz = 30.0  # Softer contacts
        """
        return self._contact_hertz

    @contact_hertz.setter
    def contact_hertz(self, value: float):
        self._contact_hertz = float(value)
        lib.b2World_SetContactTuning(
            self._world_id,
            self._contact_hertz,
            self._contact_damping_ratio,
            self._contact_push_velocity,
        )

    @property
    def contact_damping_ratio(self) -> float:
        """Contact constraint damping ratio (0-1).

        1.0 = critical damping (fastest oscillation reduction)

        Example:
            >>> world = World()
            >>> world.contact_damping_ratio = 0.2  # Add some energy absorption
        """
        return self._contact_damping_ratio

    @contact_damping_ratio.setter
    def contact_damping_ratio(self, value: float):
        self._contact_damping_ratio = float(value)
        lib.b2World_SetContactTuning(
            self._world_id,
            self._contact_hertz,
            self._contact_damping_ratio,
            self._contact_push_velocity,
        )

    @property
    def contact_push_velocity(self) -> float:
        """Maximum velocity for pushing objects out of penetration (m/s).

        Limits how fast contacts can separate penetrating bodies.

        Example:
            >>> world = World()
            >>> world.contact_push_velocity = 2.0  # Allow faster separation
        """
        return self._contact_push_velocity

    @contact_push_velocity.setter
    def contact_push_velocity(self, value: float):
        self._contact_push_velocity = float(value)
        lib.b2World_SetContactTuning(
            self._world_id,
            self._contact_hertz,
            self._contact_damping_ratio,
            self._contact_push_velocity,
        )
