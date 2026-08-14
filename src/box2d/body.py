from box2d._box2d import lib, ffi
from .math import Vec2, Rot, Transform, VectorLike, AABB
from .shape import Box, Circle, Capsule, Segment, Polygon, Chain
from .joint import Joint
from .collision_filter import CollisionFilter
from typing import Sequence, List
from .material import SurfaceMaterial
from .dataclasses import MassData, ContactData, BodyDef
from .accessors import b2_bool, b2_float, b2_value
from .lifetime import IdRef, raw_id, is_live


class BodyBuilder:
    """Builder for creating Box2D bodies with chained configuration methods.

    Example:
        >>> body = world.new_body()
        >>> body.dynamic()
        >>> body.position(2, 3)
        >>> body.box(width=2, height=1)
        >>> body.circle(radius=0.5, center=(1, 0))
        >>> body = body.build()
    """

    def __init__(self, world):
        """Initialize the BodyBuilder with the world context.

        Args:
            world: The World instance where the body will be created.
        """
        self.world = world
        # Accumulated keyword arguments for World.add_body. The builder is sugar
        # over that call and holds no body state of its own.
        self._body_args = {}
        self._shape_defs = []

    @classmethod
    def extend(cls, func):
        """
        Decorator that adds a new method to the BodyBuilder class.

        When decorating a function with @BodyBuilder.extend, the function is attached as a new method
        to the BodyBuilder class. This enables you to extend the builder with custom configuration methods
        that can be chained with the built-in methods.

        Example::

            >>> @BodyBuilder.extend
            >>> def custom_shape(self, value):
            >>>     # Custom functionality
            >>>     return self

            >>> builder = world.new_body().custom_shape(10)

        Args:
            func (callable): A function to be added as a method to BodyBuilder. The function should accept
                             'self' as its first argument.

        Returns:
            callable: The unchanged original function.
        """
        setattr(cls, func.__name__, func)
        return func

    def dynamic(self):
        """Set the body type to dynamic.

        Dynamic bodies are affected by forces and impulses. Returns the builder instance.
        """
        self._body_args["body_type"] = "dynamic"
        return self

    def static(self):
        """Set the body type to static.

        Static bodies cannot move and are unaffected by forces. Returns the builder instance.
        """
        self._body_args["body_type"] = "static"
        return self

    def kinematic(self):
        """Set the body type to kinematic.

        Kinematic bodies are moved by setting their velocity. Returns the builder instance.
        """
        self._body_args["body_type"] = "kinematic"
        return self

    def lock_rotation(self, lock=True):
        """Prevent the body from rotating.

        Useful for objects like characters. Box2D 3.2 replaced the old
        fixed_rotation flag with independent locks; see also lock_x and lock_y.
        Args:
            lock: Boolean indicating whether rotation should be locked
        Returns:
            The builder instance
        """
        self._body_args["lock_rotation"] = lock
        return self

    def lock_x(self, lock=True):
        """Prevent the body from translating along the world x-axis.

        Args:
            lock: Boolean indicating whether x translation should be locked
        Returns:
            The builder instance
        """
        self._body_args["lock_x"] = lock
        return self

    def lock_y(self, lock=True):
        """Prevent the body from translating along the world y-axis.

        Args:
            lock: Boolean indicating whether y translation should be locked
        Returns:
            The builder instance
        """
        self._body_args["lock_y"] = lock
        return self

    def bullet(self, bullet=True):
        """Set whether the body is treated as a bullet.

        Bullet bodies perform continuous collision detection, suitable for fast-moving objects.
        Args:
            bullet: Boolean indicating whether to enable bullet behavior
        Returns:
            The builder instance
        """
        self._body_args["is_bullet"] = bullet
        return self

    def gravity_scale(self, scale):
        """Set the gravity scale for the body.

        Adjusts the effect of gravity on this body relative to the world gravity.
        Args:
            scale: Float value representing the gravity scale factor
        Returns:
            The builder instance
        """
        self._body_args["gravity_scale"] = scale
        return self

    def position(self, x, y: float = None):
        """Set the initial position of the body.

        Args:
            x: The position as a vector-like, or its x-coordinate when 'y' is given.
            y: The y-coordinate, when passing the coordinates separately.
        Returns:
            The builder instance

        Example:
            >>> builder = world.new_body().position(2, 3)
            >>> builder = world.new_body().position((2, 3))
        """
        self._body_args["position"] = Vec2(x, y)
        return self

    def rotation(self, rotation: float):
        """Set the initial rotation of the body.

        Args:
            rotation: The rotation in radians
        Returns:
            The builder instance
        """
        self._body_args["rotation"] = rotation
        return self

    def linear_velocity(self, x, y: float = None):
        """Set the initial linear velocity of the body.

        Args:
            x: The velocity as a vector-like, or its x-component when 'y' is given.
            y: The y-component, when passing the components separately.
        Returns:
            The builder instance
        """
        self._body_args["linear_velocity"] = Vec2(x, y)
        return self

    def angular_velocity(self, radians: float):
        """Set the initial angular velocity of the body.

        Args:
            radians: The angular velocity in radians per second
        Returns:
            The builder instance
        """
        self._body_args["angular_velocity"] = radians
        return self

    def linear_damping(self, damping: float):
        """Set the linear damping of the body.

        Damping reduces the linear velocity over time.
        Args:
            damping: Float value for linear damping
        Returns:
            The builder instance
        """
        self._body_args["linear_damping"] = damping
        return self

    def angular_damping(self, damping: float):
        """Set the angular damping of the body.

        Damping reduces the angular velocity over time.
        Args:
            damping: Float value for angular damping
        Returns:
            The builder instance
        """
        self._body_args["angular_damping"] = damping
        return self

    def enable_sleep(self, enable: bool):
        """Set whether the body is allowed to sleep.

        Sleeping bodies are skipped in simulations for performance optimization.
        Args:
            enable: Boolean indicating whether sleeping is enabled
        Returns:
            The builder instance
        """
        self._body_args["enable_sleep"] = enable
        return self

    def sleep_threshold(self, threshold: float):
        """Set the sleep threshold for the body.

        The minimum velocity below which the body will go to sleep.
        Args:
            threshold: Float value representing the sleep threshold
        Returns:
            The builder instance
        """
        self._body_args["sleep_threshold"] = threshold
        return self

    def box(
        self,
        width: float,
        height: float,
        radius=0.0,
        offset: VectorLike = (0, 0),
        angle=0.0,
        **shapedef_args,
    ):
        """Add a box shape to the body during construction.

        Args:
            width: Full width of the box.
            height: Full height of the box.
            radius: The radius of the rounded corners (default: 0.0).
            offset: The offset of the box from the body's position (default: (0, 0)).
            angle: The angle of the box (default: 0.0).
            **shapedef_args: Additional parameters for the shape definition.
        Returns:
            Self for method chaining.
        """
        self._shape_defs.append(
            {
                "type": "box",
                "params": (width, height),
                "kwargs": {
                    "radius": radius,
                    "offset": offset,
                    "angle": angle,
                    **shapedef_args,
                },
            }
        )
        return self

    def circle(
        self,
        radius: float,
        center: VectorLike = (0, 0),
        **shapedef_args,
    ):
        """Add a circle shape to the body during construction.

        Args:
            radius: Radius of the circle.
            center: Local center position (x, y).
            **shapedef_args: Additional parameters for the shape definition.
        Returns:
            Self for method chaining.
        """
        self._shape_defs.append(
            {
                "type": "circle",
                "params": (radius, center),
                "kwargs": {
                    **shapedef_args,
                },
            }
        )
        return self

    def capsule(
        self,
        point1: VectorLike,
        point2: VectorLike,
        radius: float,
        **shapedef_args,
    ):
        """Add a vertical capsule shape (cylinder with hemispherical ends).

        Args:
            point1: The first endpoint of the capsule.
            point2: The second endpoint of the capsule.
            radius: Radius of the hemispherical ends.
            **shapedef_args: Additional parameters for the shape definition.
        Returns:
            Self for method chaining.
        """
        self._shape_defs.append(
            {
                "type": "capsule",
                "params": (point1, point2, radius),
                "kwargs": {
                    **shapedef_args,
                },
            }
        )
        return self

    def polygon(
        self,
        vertices: Sequence[VectorLike],
        radius: float = 0.0,
        **shapedef_args,
    ):
        """Add a convex polygon shape.

        The given vertices are processed to compute their convex hull. An exception will be raised
        if the provided vertices do not form a valid convex polygon.

        Args:
            vertices: List of points that define the polygon shape.
            radius: The radius of the rounded corners (default: 0.0).
            **shapedef_args: Additional parameters for the shape definition.

        Returns:
            Self for method chaining.
        Raises:
            Exception: If the vertices cannot form a convex polygon.
        """
        self._shape_defs.append(
            {
                "type": "polygon",
                "params": (vertices,),
                "kwargs": {
                    "radius": radius,
                    **shapedef_args,
                },
            }
        )
        return self

    def segment(
        self,
        point1: VectorLike,
        point2: VectorLike,
        **shapedef_args,
    ):
        """Add a line segment shape with optional edge radius.

        Args:
            point1: The first endpoint, in local coordinates.
            point2: The second endpoint, in local coordinates.
            **shapedef_args: Additional parameters for the shape definition.
        Returns:
            Self for method chaining.
        """
        self._shape_defs.append(
            {
                "type": "segment",
                "params": (point1, point2),
                "kwargs": {
                    **shapedef_args,
                },
            }
        )
        return self

    def chain(
        self,
        vertices: Sequence[VectorLike],
        loop: bool = False,
        **chaindef_args,
    ):
        """Add a chain shape to the body during construction.

        Args:
            vertices: List of points that define the chain shape. Must contain at least 4 vertices.
            loop: Boolean indicating whether the chain should be closed (looped). Default is False.
            **chaindef_args: Additional parameters for the shape definition.
        Returns:
            Self for method chaining.
        """
        self._shape_defs.append(
            {
                "type": "chain",
                "params": (vertices,),
                "kwargs": {
                    "loop": loop,
                    **chaindef_args,
                },
            }
        )
        return self

    def build(self) -> "Body":
        """Finalize the body creation and attach configured shapes.

        Creates the body through :meth:`World.add_body` and attaches the shapes
        configured on this builder. The builder may be reused to create several
        bodies; each build produces an independent body.

        Returns:
            The newly created Body instance
        """
        body = self.world.add_body(**self._body_args)

        # Create shapes
        for shape_def in self._shape_defs:
            method = getattr(body, f'add_{shape_def["type"]}')
            method(*shape_def["params"], **shape_def["kwargs"])

        return body


class Body:
    """Represents a rigid body in the 2D physics simulation.

    Bodies can be dynamic, kinematic, or static, and can have various forces,
    impulses, and constraints applied to them.
    """

    types = {
        "static": lib.b2_staticBody,
        "kinematic": lib.b2_kinematicBody,
        "dynamic": lib.b2_dynamicBody,
    }

    _body_id = IdRef(lib.b2Body_IsValid, "body")

    def __init__(self, world: "World", body_def: BodyDef):
        """
        Initialize a Body instance.

        Prefer :meth:`World.add_body`, which is the supported way to create a
        body. This constructor is the single point where a BodyDef becomes a
        live body, and everything else routes through it.

        Args:
            world: The World instance in which this body exists.
            body_def: The body definition used to create this body. It is not
                modified, so a definition may be reused to create many bodies.
        """
        self.world = world
        self._handle = ffi.new_handle(self)

        # Box2D's userData carries the handle that maps an id back to this
        # object, so the caller's own user_data lives on the Body instead.
        # Setting it on the definition would both overwrite the handle and
        # corrupt a definition the caller may want to reuse.
        self.user_data = body_def.user_data

        b2BodyDef = body_def.b2BodyDef
        b2BodyDef.userData = self._handle
        self._body_id = lib.b2CreateBody(self.world._world_id, ffi.addressof(b2BodyDef))
        self._shapes = []
        self._chains = []
        self.world._track_body(self)

    @property
    def shapes(self):
        """Get the shapes attached to this body."""
        return self._shapes

    @property
    def position(self):
        """Get the world position of the body."""
        pos = lib.b2Body_GetPosition(self._body_id)
        return Vec2(pos.x, pos.y)

    @position.setter
    def position(self, value: VectorLike):
        """Set the world position of the body."""
        rot = lib.b2Body_GetRotation(self._body_id)
        value = Vec2(value)
        lib.b2Body_SetTransform(self._body_id, value.b2Vec2[0], rot)

    @property
    def linear_velocity(self):
        """Get the linear velocity of the body."""
        vel = lib.b2Body_GetLinearVelocity(self._body_id)
        return Vec2(vel.x, vel.y)

    @linear_velocity.setter
    def linear_velocity(self, value: VectorLike):
        """Set the linear velocity of the body."""
        value = Vec2(value).b2Vec2[0]
        lib.b2Body_SetLinearVelocity(self._body_id, value)

    angular_velocity = b2_float(
        lib.b2Body_GetAngularVelocity,
        lib.b2Body_SetAngularVelocity,
        doc="Get angular velocity in radians/sec.",
    )
    linear_damping = b2_float(
        lib.b2Body_GetLinearDamping,
        lib.b2Body_SetLinearDamping,
        doc="Get the current linear damping value.",
    )
    angular_damping = b2_float(
        lib.b2Body_GetAngularDamping,
        lib.b2Body_SetAngularDamping,
        doc="Get the current angular damping value.",
    )
    sleep_threshold = b2_float(
        lib.b2Body_GetSleepThreshold,
        lib.b2Body_SetSleepThreshold,
        doc="Get the sleep threshold value.",
    )

    def _set_motion_lock(self, axis: str, value: bool) -> None:
        """Set one of the three motion locks, leaving the others alone."""
        locks = lib.b2Body_GetMotionLocks(self._body_id)
        setattr(locks, axis, bool(value))
        lib.b2Body_SetMotionLocks(self._body_id, locks)

    @property
    def lock_x(self) -> bool:
        """Get or set whether translation along the world x-axis is prevented."""
        return lib.b2Body_GetMotionLocks(self._body_id).linearX

    @lock_x.setter
    def lock_x(self, value: bool) -> None:
        self._set_motion_lock("linearX", value)

    @property
    def lock_y(self) -> bool:
        """Get or set whether translation along the world y-axis is prevented."""
        return lib.b2Body_GetMotionLocks(self._body_id).linearY

    @lock_y.setter
    def lock_y(self, value: bool) -> None:
        self._set_motion_lock("linearY", value)

    @property
    def lock_rotation(self) -> bool:
        """Get or set whether the body is prevented from rotating.

        Box2D 3.2 replaced the single fixed_rotation flag with three
        independent locks; this is the rotational one.
        """
        return lib.b2Body_GetMotionLocks(self._body_id).angularZ

    @lock_rotation.setter
    def lock_rotation(self, value: bool) -> None:
        self._set_motion_lock("angularZ", value)

    is_bullet = b2_bool(
        lib.b2Body_IsBullet,
        lib.b2Body_SetBullet,
        doc="Check if the body is treated as a bullet.",
    )
    gravity_scale = b2_value(
        lib.b2Body_GetGravityScale,
        lib.b2Body_SetGravityScale,
        doc="Get the gravity scale factor for this body.",
    )
    awake = b2_bool(
        lib.b2Body_IsAwake,
        lib.b2Body_SetAwake,
        doc="""Get the awake state of the body.
        
        Returns:
            bool: True if the body is awake, False otherwise.
        """,
    )

    @property
    def enabled(self):
        """Get whether the body is enabled.

        Returns:
            bool: True if the body is enabled, False otherwise.
        """
        return lib.b2Body_IsEnabled(self._body_id)

    @enabled.setter
    def enabled(self, value: bool):
        """Set whether the body is enabled.

        Args:
            value (bool): True to enable the body, False to disable it.
        """
        if value:
            lib.b2Body_Enable(self._body_id)
        else:
            lib.b2Body_Disable(self._body_id)

    @property
    def rotation(self):
        """Get the world rotation of the body in radians.

        Returns:
            float: The body's rotation angle in radians.
        """
        rot = lib.b2Body_GetRotation(self._body_id)
        return Rot.from_b2Rot(rot).angle_radians

    @rotation.setter
    def rotation(self, angle: float):
        """Set the world rotation of the body in radians.

        Args:
            angle (float): The new rotation angle in radians.
        """
        pos = lib.b2Body_GetPosition(self._body_id)
        rot = Rot(angle).b2Rot
        lib.b2Body_SetTransform(self._body_id, pos, rot[0])

    mass = b2_value(
        lib.b2Body_GetMass,
        doc="Get the mass of the body in kilograms",
    )
    rotational_inertia = b2_value(
        lib.b2Body_GetRotationalInertia,
        doc="Get the rotational inertia of the body.",
    )

    @property
    def transform(self) -> Transform:
        """Get the body Transform. You can use it to convert world coordinates to body coordinates."""
        b2transform = lib.b2Body_GetTransform(self._body_id)
        return Transform.from_b2Transform(b2transform)

    def enable_contact_events(self, enable: bool = True) -> None:
        """Turn contact events on or off for every shape on this body.

        Convenience for the common case of wanting begin and end touch events
        from a whole body rather than picking shapes individually.

        Args:
            enable: True to report contacts, False to stop.
        """
        lib.b2Body_EnableContactEvents(self._body_id, bool(enable))

    def enable_hit_events(self, enable: bool = True) -> None:
        """Turn hit events on or off for every shape on this body.

        Hits are reported only above the world's hit_event_threshold.

        Args:
            enable: True to report hits, False to stop.
        """
        lib.b2Body_EnableHitEvents(self._body_id, bool(enable))

    def apply_force(self, force: VectorLike, point: VectorLike = None, wake=True):
        """Apply a force at a world point.

        Args:
            force: The force vector as a vector-like.
            point: The application point as a vector-like. Defaults to the center of mass.
            wake: Boolean indicating whether to wake the body.
        """
        force = Vec2(force).b2Vec2[0]
        if point is None:
            lib.b2Body_ApplyForceToCenter(self._body_id, force, wake)
        else:
            lib.b2Body_ApplyForce(self._body_id, force, Vec2(point).b2Vec2[0], wake)

    def apply_torque(self, torque, wake=True):
        """Apply a torque to the body.

        Args:
            torque: Float value representing the torque.
            wake: Boolean indicating whether to wake the body.
        """
        lib.b2Body_ApplyTorque(self._body_id, torque, wake)

    def apply_linear_impulse(
        self, impulse: VectorLike, point: VectorLike = None, wake=True
    ):
        """Apply a linear impulse at a world point.

        Args:
            impulse: The impulse vector as a vector-like.
            point: The application point as a vector-like. Defaults to the center of mass.
            wake: Boolean indicating whether to wake the body.
        """
        impulse = Vec2(impulse).b2Vec2[0]
        if point is None:
            lib.b2Body_ApplyLinearImpulseToCenter(self._body_id, impulse, wake)
        else:
            lib.b2Body_ApplyLinearImpulse(
                self._body_id, impulse, Vec2(point).b2Vec2[0], wake
            )

    def add_box(
        self,
        width: float,
        height: float,
        radius: float = 0.0,
        offset: VectorLike = (0, 0),
        angle: float = 0.0,
        **shapedef_args,
    ):
        """Add a box shape to the body.

        Args:
            width: Full width of the box.
            height: Full height of the box.
            radius: The radius of the rounded corners (default: 0.0).
            offset: The offset of the box from the body's position (default: (0, 0)).
            angle: The rotation angle of the box in radians (default: 0.0).
            **shapedef_args: Additional parameters for the shape definition.

        Returns:
            The created box shape.
        """

        shape = Box.create(
            self,
            width,
            height,
            radius,
            offset,
            angle,
            **shapedef_args,
        )
        self._shapes.append(shape)
        return shape

    def add_circle(
        self,
        radius: float,
        center: VectorLike = (0, 0),
        **shapedef_args,
    ):
        """Add a circle shape to the body.

        Args:
            radius: Radius of the circle.
            center: Center of the circle (default: (0, 0)).
            **shapedef_args: Additional parameters for the shape definition.

        Returns:
            The created circle shape.
        """

        shape = Circle.create(
            self,
            radius,
            center,
            **shapedef_args,
        )
        self._shapes.append(shape)
        return shape

    def add_capsule(
        self,
        point1: VectorLike,
        point2: VectorLike,
        radius: float,
        **shapedef_args,
    ):
        """Add a capsule shape to the body.

        Args:
            point1: First endpoint of the capsule.
            point2: Second endpoint of the capsule.
            radius: Radius of the capsule.
            **shapedef_args: Additional parameters for the shape definition.

        Returns:
            The created capsule shape.
        """

        shape = Capsule.create(
            self,
            point1,
            point2,
            radius,
            **shapedef_args,
        )
        self._shapes.append(shape)
        return shape

    def add_polygon(
        self,
        vertices: Sequence[VectorLike],
        radius: float = 0.0,
        **shapedef_args,
    ):
        """Add a convex polygon shape to the body.

        Args:
            vertices: List of vertices defining the polygon.
            radius: Optional radius for rounded corners (default: 0.0).
            **shapedef_args: Additional parameters for the shape definition.

        Returns:
            The created polygon shape.
        """

        shape = Polygon.create(
            self,
            vertices,
            radius,
            **shapedef_args,
        )
        self._shapes.append(shape)
        return shape

    def add_segment(
        self,
        point1: VectorLike,
        point2: VectorLike,
        **shapedef_args,
    ):
        """Add a line segment shape to the body.

        Args:
            point1: Starting point of the segment.
            point2: Ending point of the segment.
            **shapedef_args: Additional parameters for the shape definition.

        Returns:
            The created segment shape.
        """

        shape = Segment.create(
            self,
            point1,
            point2,
            **shapedef_args,
        )
        self._shapes.append(shape)
        return shape

    def add_chain(
        self,
        vertices: Sequence[VectorLike],
        loop: bool = False,
        **chaindef_args,
    ):
        """Add a chain shape to the body.

        Args:
            vertices: List of vertices defining the chain (must contain at least 4 vertices).
            loop: Boolean indicating whether the chain should be closed (looped).
            **chaindef_args: Additional parameters for the `Chain` definition.

        Returns:
            The created chain shape.
        """
        chain = Chain.create(
            self,
            vertices,
            loop,
            **chaindef_args,
        )
        self._chains.append(chain)
        return chain

    def remove_shape(self, shape):
        """Remove a shape from the body."""
        if shape in self._shapes:
            lib.b2DestroyShape(shape._shape_id, True)  # Update body mass
            self._shapes.remove(shape)

    def is_sleep_enabled(self):
        """Check if the body is allowed to sleep."""
        return lib.b2Body_IsSleepEnabled(self._body_id)

    @property
    def is_valid(self) -> bool:
        """Whether this body is still live, i.e. has not been destroyed."""
        return is_live(self, "_body_id", lib.b2Body_IsValid)

    def destroy(self):
        """
        Destroy this body and remove it from the world.

        Destroying a body also destroys its shapes. The body and its shapes
        raise :class:`DestroyedError` if used afterwards. Destroying twice is a
        no-op.
        """
        # Read past the validity check: the id is needed to deregister the body
        # even once Box2D no longer recognises it (e.g. the world went first).
        raw = raw_id(self, "_body_id")
        if raw is None:
            return
        if lib.b2Body_IsValid(raw):
            lib.b2DestroyBody(raw)
        if hasattr(self.world, "_bodies"):
            self.world._bodies.pop(raw, None)
        del self._body_id

    def get_local_point(self, world_point: VectorLike) -> Vec2:
        """Convert a point from world space to local body space.

        Args:
            world_point: A point in world coordinates.

        Returns:
            The point in local body coordinates.
        """
        point = Vec2(world_point).b2Vec2[0]
        local_point = lib.b2Body_GetLocalPoint(self._body_id, point)
        return Vec2(local_point.x, local_point.y)

    def get_world_point(self, local_point: VectorLike) -> Vec2:
        """Convert a point from local body space to world space.

        Args:
            local_point: A point in local body coordinates.

        Returns:
            The point in world coordinates.
        """
        point = Vec2(local_point).b2Vec2
        world_point = lib.b2Body_GetWorldPoint(self._body_id, point[0])
        return Vec2.from_b2Vec2(world_point)

    def get_local_vector(self, world_vector: VectorLike) -> Vec2:
        """Convert a vector from world space to local body space.

        Args:
            world_vector: A vector in world coordinates.

        Returns:
            The vector in local body coordinates.
        """
        vector = Vec2(world_vector).b2Vec2
        local_vector = lib.b2Body_GetLocalVector(self._body_id, vector[0])
        return Vec2.from_b2Vec2(local_vector)

    def get_world_vector(self, local_vector: VectorLike) -> Vec2:
        """Convert a vector from local body space to world space.

        Args:
            local_vector: A vector in local body coordinates.

        Returns:
            The vector in world coordinates.
        """
        vector = Vec2(local_vector).b2Vec2
        world_vector = lib.b2Body_GetWorldVector(self._body_id, vector[0])
        return Vec2.from_b2Vec2(world_vector)

    def get_local_point_velocity(self, local_point: VectorLike) -> Vec2:
        """Get the velocity of a local point on the body.

        Args:
            local_point: A point in local body coordinates.

        Returns:
            The velocity of the point in world coordinates.
        """
        point = Vec2(local_point).b2Vec2
        velocity = lib.b2Body_GetLocalPointVelocity(self._body_id, point[0])
        return Vec2.from_b2Vec2(velocity)

    def get_world_point_velocity(self, world_point: VectorLike) -> Vec2:
        """Get the velocity of a world point if it were attached to the body.

        Args:
            world_point: A point in world coordinates.

        Returns:
            The velocity of the point in world coordinates.
        """
        point = Vec2(world_point).b2Vec2
        velocity = lib.b2Body_GetWorldPointVelocity(self._body_id, point[0])
        return Vec2.from_b2Vec2(velocity)

    def apply_angular_impulse(self, impulse: float, wake: bool = True):
        """Apply an angular impulse to the body.

        Args:
            impulse: The angular impulse in kg*m^2/s.
            wake: Whether to wake the body.
        """
        lib.b2Body_ApplyAngularImpulse(self._body_id, float(impulse), wake)

    @property
    def local_center_of_mass(self) -> Vec2:
        """Get the center of mass position in local space.

        Returns:
            Center of mass in local coordinates.
        """
        center = lib.b2Body_GetLocalCenter(self._body_id)
        return Vec2.from_b2Vec2(center)

    @property
    def world_center_of_mass(self) -> Vec2:
        """Get the center of mass position in world space.

        Returns:
            Center of mass in world coordinates.
        """
        center = lib.b2Body_GetWorldCenter(self._body_id)
        return Vec2.from_b2Vec2(center)

    @property
    def mass_data(self) -> MassData:
        """Get the complete mass data for the body.

        Returns:
            MassData object containing mass, center of mass, and rotational inertia.
        """
        b2_mass_data = lib.b2Body_GetMassData(self._body_id)
        return MassData.from_b2MassData(b2_mass_data)

    @mass_data.setter
    def mass_data(self, mass_data: MassData):
        """Override the body's mass properties.

        Args:
            mass_data: Mass data to apply to the body.
        """
        b2_mass_data = mass_data.b2MassData
        lib.b2Body_SetMassData(self._body_id, b2_mass_data[0])

    def apply_mass_from_shapes(self):
        """Update mass properties to the sum of the mass properties of the shapes.

        This normally doesn't need to be called unless you called set_mass_data()
        to override the mass and later want to reset the mass.
        """
        lib.b2Body_ApplyMassFromShapes(self._body_id)

    @property
    def aabb(self) -> AABB:
        """Get the AABB enclosing all shapes attached to the body.

        Returns:
            AABB object representing the axis-aligned bounding box.
        """
        b2_aabb = lib.b2Body_ComputeAABB(self._body_id)
        return AABB(
            Vec2.from_b2Vec2(b2_aabb.lowerBound),
            Vec2.from_b2Vec2(b2_aabb.upperBound),
        )

    joint_count = b2_value(
        lib.b2Body_GetJointCount,
        doc="""Get the number of joints attached to this body.
        
        Returns:
            The number of attached joints.
        """,
    )

    def _read_joints(self) -> List[Joint]:
        """Get the joints attached to this body.

        Returns:
            List of Joint objects attached to this body.
        """
        count = self.joint_count
        if count == 0:
            return []

        joint_ids = ffi.new("b2JointId[]", count)
        actual_count = lib.b2Body_GetJoints(self._body_id, joint_ids, count)

        joints = []
        for i in range(actual_count):
            joint_data = lib.b2Joint_GetUserData(joint_ids[i])
            if joint_data:
                joint = ffi.from_handle(joint_data)
                joints.append(joint)

        return joints

    @property
    def joints(self) -> List[Joint]:
        """Get all joints attached to this body.

        Returns:
            List of Joint objects attached to this body.
        """
        return self._read_joints()

    contact_capacity = b2_value(
        lib.b2Body_GetContactCapacity,
        doc="""Get the maximum capacity for contacts on this body.
        
        Returns:
            The maximum capacity for contacts.
        """,
    )

    def _read_contact_data(self) -> List[ContactData]:
        """Get contact data for all active contacts involving this body.

        Returns:
            List of ContactData objects for touching contacts.
        """
        capacity = self.contact_capacity
        if capacity == 0:
            return []

        contact_data_array = ffi.new("b2ContactData[]", capacity)
        count = lib.b2Body_GetContactData(self._body_id, contact_data_array, capacity)

        contacts = []
        for i in range(count):
            contacts.append(ContactData.from_b2ContactData(contact_data_array[i]))

        return contacts

    @property
    def contact_data(self) -> List[ContactData]:
        """Get all active contacts for this body.

        Returns:
            List of ContactData objects.
        """
        return self._read_contact_data()

    @property
    def name(self) -> str:
        """Get the name of the body.

        Returns:
            The name of the body, or None if no name is set.
        """
        name = lib.b2Body_GetName(self._body_id)
        if name == ffi.NULL:
            return None
        return ffi.string(name).decode("utf-8")

    @name.setter
    def name(self, value: str):
        """Set the name of the body.

        Args:
            value: The name to set for the body. Limited to 31 characters.
        """
        if value is None:
            lib.b2Body_SetName(self._body_id, ffi.NULL)
        else:
            if len(value) > 31:
                import warnings

                warnings.warn("Body name truncated to 31 characters")
                value = value[:31]
            lib.b2Body_SetName(self._body_id, value.encode("utf-8"))

    def get_next_body(self):
        """Get the next body in the world's body list.

        Returns:
            The next body in the world or None if this is the last body.
        """
        # Box2D 3.1 removed b2Body_GetNext along with the engine-side body
        # list, so this walks the world's own tracked bodies instead.
        bodies = self.world.bodies
        try:
            index = bodies.index(self)
        except ValueError:
            return None
        return bodies[index + 1] if index + 1 < len(bodies) else None

    @staticmethod
    def resolve_type(body_type) -> int:
        """Convert a body type to the Box2D constant.

        Args:
            body_type: A name -- 'static', 'kinematic' or 'dynamic' -- or a BodyType.

        Returns:
            The Box2D body type constant.

        Raises:
            ValueError: If the name is not a valid body type.
        """
        if isinstance(body_type, str):
            try:
                return Body.types[body_type]
            except KeyError:
                raise ValueError(
                    f"Invalid body type: {body_type!r}. "
                    f"Must be one of: {', '.join(sorted(Body.types))}."
                ) from None
        return int(body_type)

    @property
    def type(self) -> str:
        """Get or set the body type.

        Reads back as a name -- 'static', 'kinematic' or 'dynamic'. Accepts
        either a name or a BodyType when set.

        Changing type is not free: it destroys and recreates the body's
        contacts, and wakes both this body and anything touching it.
        """
        type_id = lib.b2Body_GetType(self._body_id)
        for name, value in Body.types.items():
            if value == type_id:
                return name

    @type.setter
    def type(self, body_type) -> None:
        lib.b2Body_SetType(self._body_id, Body.resolve_type(body_type))

    # TODO: currently is segfaults one of the tests. need to figure out why.
    # def __del__(self):
    # Attempt to clean up if destroy() wasn't explicitly called.
    # self.destroy()
