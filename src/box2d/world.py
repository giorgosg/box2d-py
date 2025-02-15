# src/box3d/world.py

from ._box2d import lib, ffi
from .body import BodyBuilder, Body
from .joint import MouseJoint, WeldJoint, RevoluteJoint
from .math import Vec2, VectorLike, AABB, Transform
from .debug_draw import DebugDraw
from .collision_filter import CollisionFilter
from .shape_def import CircleDef


def make_overlap_callback(results: list, max_results: int = None):
    """
    Create an overlap callback that appends detected shapes to the results
    list and stops querying when max_results is reached.

    Args:
        results: A list to collect overlapping shapes.
        max_results: Optional maximum number of shapes to collect. Once reached,
                     the callback returns False to stop further processing.

    Returns:
        A Box2D-compatible callback function.
    """

    @ffi.callback("bool(b2ShapeId, void*)")
    def overlap_callback(shape_id, _):
        shape = ffi.from_handle(lib.b2Shape_GetUserData(shape_id))
        results.append(shape)
        if max_results is not None and len(results) >= max_results:
            return False  # Stop querying further shapes
        return True  # Continue querying

    return overlap_callback


_WORLD_REGISTRY = {}


# src/box2d/world.py
@ffi.callback("void* (b2TaskCallback*, int, int, void*, void*)")
def _enqueue_task_callback(task, itemCount, minRange, taskContext, userContext):
    futures = []
    try:
        world_id = ffi.from_handle(userContext)
    except RuntimeError:
        return ffi.new_handle([])  # Handle already GC'd

    world_instance = _WORLD_REGISTRY.get(world_id)
    if world_instance is None:
        return ffi.new_handle([])

    n_workers = world_instance._threads

    # Calculate the work chunk per worker.
    # Use max(minRange, computed_chunk) to avoid scheduling tasks that are too small.
    computed_chunk = (itemCount + n_workers - 1) // n_workers
    chunk = max(minRange, computed_chunk)

    for worker in range(n_workers):
        start = worker * chunk
        end = min(start + chunk, itemCount)
        if start >= end:
            break

        def run_task(
            start=start, end=end, worker=worker, task=task, taskContext=taskContext
        ):
            task(start, end, worker, taskContext)

        future = world_instance._executor.submit(run_task)
        futures.append(future)

    # Create a handle for the futures list.
    handle = ffi.new_handle(futures)
    # Store the handle on the world instance to keep it alive until the task finishes.
    if not hasattr(world_instance, "_task_handles"):
        world_instance._task_handles = []
    world_instance._task_handles.append(handle)
    return handle


@ffi.callback("void (void*, void*)")
def _finish_task_callback(userTask, userContext):
    try:
        world_id = ffi.from_handle(userContext)
    except RuntimeError:
        return  # Handle already garbage collected

    try:
        futures = ffi.from_handle(userTask)
    except RuntimeError:
        return  # Futures list was GC'd

    if world_id not in _WORLD_REGISTRY:
        return  # World destroyed, skip processing

    world_instance = _WORLD_REGISTRY.get(world_id)
    # Remove the handle from the stored list now that we are finishing.
    if (
        hasattr(world_instance, "_task_handles")
        and userTask in world_instance._task_handles
    ):
        world_instance._task_handles.remove(userTask)

    for future in futures:
        try:
            future.result()
        except Exception:
            pass


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

    def __init__(self, gravity: VectorLike = (0, -10), threads: int = 1):
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
        self._threads = threads
        if threads > 1:
            import concurrent.futures

            self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=threads)
            world_def.workerCount = threads
            world_def.enqueueTask = _enqueue_task_callback
            world_def.finishTask = _finish_task_callback
            self._user_task_ctx = ffi.new_handle(id(self))
            _WORLD_REGISTRY[id(self)] = self
            world_def.userTaskContext = self._user_task_ctx
        else:
            self._executor = None

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

    def add_mouse_joint(
        self, body, target, max_force=1000.0, damping_ratio=0.7
    ) -> MouseJoint:
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

    def add_weld_joint(
        self,
        body_a,
        body_b,
        local_anchor_a=None,
        local_anchor_b=None,
        anchor=None,
        collide_connected=False,
        linear_hertz=None,
        linear_damping_ratio=None,
        angular_hertz=None,
        angular_damping_ratio=None,
    ) -> WeldJoint:
        """Create a weld joint that rigidly connects two bodies.

        Args:
            body_a: The first body to connect (must belong to this world)
            body_b: The second body to connect (must belong to this world)
            local_anchor_a (tuple): Local coordinates (x, y) on body_a where the joint attaches.
            local_anchor_b (tuple): Local coordinates (x, y) on body_b where the joint attaches.
            anchor: World coordinates (x, y) where the joint attaches. (Used without local anchors)
            collide_connected (bool, optional): If True, the connected bodies will collide.
            linear_hertz (float, optional): Linear spring stiffness in Hertz (0 means rigid).
            linear_damping_ratio (float, optional): Linear damping ratio (non-dimensional).
            angular_hertz (float, optional): Angular spring stiffness in Hertz (0 means rigid).
            angular_damping_ratio (float, optional): Angular damping ratio (non-dimensional).
            reference_angle (float, optional): The body_b angle minus body_a angle in the reference state (radians)

        Returns:
            WeldJoint: The created weld joint connecting the two bodies.

        Example:
            >>> world = World()
            >>> body_a = world.new_body().dynamic().position(0, 0).build()
            >>> body_b = world.new_body().dynamic().position(1, 1).build()
            >>> weld_joint = world.add_weld_joint(body_a, body_b, anchor=(0.5, 0.5))
        """
        if (body_a._body_id not in self._bodies) or (
            body_b._body_id not in self._bodies
        ):
            raise ValueError("Both bodies must belong to this world")
        if anchor is not None:
            if local_anchor_a is not None or local_anchor_b is not None:
                raise ValueError(
                    "You can't set local anchors when setting a world anchor"
                )
            local_anchor_a = body_a.transform.inverse(anchor)
            local_anchor_b = body_b.transform.inverse(anchor)
        return WeldJoint(
            self,
            body_a,
            body_b,
            local_anchor_a,
            local_anchor_b,
            collide_connected,
            linear_hertz,
            linear_damping_ratio,
            angular_hertz,
            angular_damping_ratio,
        )

    def add_revolute_joint(
        self,
        body_a,
        body_b,
        local_anchor_a=None,
        local_anchor_b=None,
        anchor=None,
        collide_connected=False,
        lower_angle=None,
        upper_angle=None,
        enable_limit=None,
        motor_speed=None,
        max_motor_torque=None,
        enable_motor=None,
        reference_angle=None,
    ) -> RevoluteJoint:
        """
        Create a revolute joint connecting two bodies, allowing relative rotation about an anchor point.

        Args:
            body_a: The first body to connect (must belong to this world).
            body_b: The second body to connect (must belong to this world).
            local_anchor_a (tuple): Local coordinates (x, y) on body_a for the joint.
            local_anchor_b (tuple): Local coordinates (x, y) on body_b for the joint.
            collide_connected (bool, optional): Whether the connected bodies should collide with each other.
                                                  Defaults to False.
            lower_angle (float, optional): Lower joint limit in radians. Defaults to 0.0.
            upper_angle (float, optional): Upper joint limit in radians. Defaults to 0.0.
            enable_limit (bool, optional): Enable joint limits if True. Defaults to False.
            motor_speed (float, optional): Desired motor speed in radians per second. Defaults to 0.0.
            max_motor_torque (float, optional): Maximum motor torque in newton-meters. Defaults to 0.0.
            enable_motor (bool, optional): Enable the joint motor if True. Defaults to False.
            reference_angle (float, optional): Reference angle between the two bodies. Defaults to 0.0.

        Returns:
            RevoluteJoint: The created revolute joint connecting body_a and body_b.

        Example:
            >>> world = World()
            >>> body_a = world.new_body().dynamic().position(0, 0).build()
            >>> body_b = world.new_body().dynamic().position(1, 0).build()
            >>> revolute_joint = world.add_revolute_joint(
            ...     body_a, body_b, (0, 0), (0, 0),
            ...     collide_connected=False,
            ...     enable_limit=True,
            ...     lower_angle=-0.5,
            ...     upper_angle=0.5
            ... )
        """
        if (body_a._body_id not in self._bodies) or (
            body_b._body_id not in self._bodies
        ):
            raise ValueError("Both bodies must belong to this world")
        if anchor is not None:
            if local_anchor_a is not None or local_anchor_b is not None:
                raise ValueError(
                    "You can't set local anchors when setting a world anchor"
                )
            local_anchor_a = body_a.transform.inverse(anchor)
            local_anchor_b = body_b.transform.inverse(anchor)
        return RevoluteJoint(
            self,
            body_a,
            body_b,
            local_anchor_a,
            local_anchor_b,
            collide_connected,
            lower_angle,
            upper_angle,
            enable_limit,
            motor_speed,
            max_motor_torque,
            enable_motor,
            reference_angle,
        )

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

    def query_aabb(
        self,
        aabb: AABB,
        collision_filter: "CollisionFilter" = None,
        max_results: int = None,
    ) -> list:
        """Find shapes overlapping an axis-aligned bounding box using an optional collision filter.

        Args:
            aabb: Axis-aligned bounding box to query.
            collision_filter: Optional CollisionFilter instance for filtering.
                          If None, a default CollisionFilter is used.
            max_results: Optional maximum number of shapes to return.
                     The callback will return False when this limit is reached.

        Returns:
            list: Shapes with overlapping fixtures.

        Example:
            >>> world = World()
            >>> box = world.new_body().dynamic().position(0, 0).box(1, 1).build()
            >>> aabb = AABB(lower=Vec2(-1, -1), upper=Vec2(1, 1))
            >>> overlaps = world.query_aabb(aabb, collision_filter=CollisionFilter(), max_results=10)
            >>> len(overlaps) <= 10
            True
        """

        if collision_filter is None:
            collision_filter = CollisionFilter()

        results = []
        overlap_callback = make_overlap_callback(results, max_results)

        # Convert the CollisionFilter to a Box2D c_filter.
        c_filter = collision_filter.b2QueryFilter
        filter_dict = {
            "categoryBits": c_filter.categoryBits,
            "maskBits": c_filter.maskBits,
        }

        lib.b2World_OverlapAABB(
            self._world_id,
            aabb.b2AABB[0],
            c_filter[0],
            overlap_callback,
            ffi.NULL,
        )
        return results

    def query_circle(
        self,
        position: VectorLike,
        radius: float,
        collision_filter: "CollisionFilter" = None,
        max_results: int = None,
    ) -> list:
        """Find shapes overlapping a circle.

        Args:
            position: Center of the query circle in world coordinates.
            radius: Radius of the query circle.
            collision_filter: Optional CollisionFilter instance for filtering.
                              If None, a default CollisionFilter is used.
            max_results: Optional maximum number of shapes to return.
                         The callback will return False when this limit is reached.

        Returns:
            list: Shapes with overlapping fixtures.

        Example:
            >>> world = World()
            >>> # Create a body with a circle fixture
            >>> box = world.new_body().dynamic().circle(1).build()
            >>> overlaps = world.query_circle((0, 0), 1.5, collision_filter=CollisionFilter(), max_results=10)
            >>> len(overlaps) <= 10
            True
        """
        if collision_filter is None:
            collision_filter = CollisionFilter()

        results = []
        overlap_callback = make_overlap_callback(results, max_results)

        circle = CircleDef(radius).circle
        transform = Transform(position=position).b2Transform
        c_filter = collision_filter.b2QueryFilter

        lib.b2World_OverlapCircle(
            self._world_id,
            circle,
            transform[0],
            c_filter[0],
            overlap_callback,
            ffi.NULL,
        )
        return results

    def destroy(self):
        """Destroy the world.

        Example:
            >>> world = World()
            >>> world.destroy()
        """
        if hasattr(self, "_executor") and self._executor is not None:
            print("shutting down tasks")
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._executor = None

        if hasattr(self, "_user_task_ctx"):
            _WORLD_REGISTRY.pop(id(self), None)

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
