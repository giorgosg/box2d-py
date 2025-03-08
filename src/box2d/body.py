from box2d._box2d import lib, ffi
from .math import Vec2, Rot, Transform, VectorLike, to_vec2
from .shape import Box, Circle, Capsule, Segment, Polygon, Chain
from .shape_def import PolygonDef
from .collision_filter import CollisionFilter


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
        self._def = lib.b2DefaultBodyDef()
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
        self._def.type = lib.b2_dynamicBody
        return self

    def static(self):
        """Set the body type to static.

        Static bodies cannot move and are unaffected by forces. Returns the builder instance.
        """
        self._def.type = lib.b2_staticBody
        return self

    def kinematic(self):
        """Set the body type to kinematic.

        Kinematic bodies are moved by setting their velocity. Returns the builder instance.
        """
        self._def.type = lib.b2_kinematicBody
        return self

    def fixed_rotation(self, fixed=True):
        """Set whether the body has fixed rotation.

        Fixed rotation bodies will not rotate. Useful for objects like characters.
        Args:
            fixed: Boolean indicating whether rotation should be fixed
        Returns:
            The builder instance
        """
        self._def.fixedRotation = fixed
        return self

    def bullet(self, bullet=True):
        """Set whether the body is treated as a bullet.

        Bullet bodies perform continuous collision detection, suitable for fast-moving objects.
        Args:
            bullet: Boolean indicating whether to enable bullet behavior
        Returns:
            The builder instance
        """
        self._def.isBullet = bullet
        return self

    def gravity_scale(self, scale):
        """Set the gravity scale for the body.

        Adjusts the effect of gravity on this body relative to the world gravity.
        Args:
            scale: Float value representing the gravity scale factor
        Returns:
            The builder instance
        """
        self._def.gravityScale = scale
        return self

    def position(self, x: float, y: float):
        """Set the initial position of the body.

        Args:
            x: The x-coordinate of the body's position
            y: The y-coordinate of the body's position
        Returns:
            The builder instance
        """
        self._def.position.x = x
        self._def.position.y = y
        return self

    def rotation(self, rotation: float):
        """Set the initial rotation of the body.

        Args:
            rotation: The rotation in radians
        Returns:
            The builder instance
        """
        self._def.rotation = Rot(rotation).b2Rot[0]
        return self

    def linear_velocity(self, x: float, y: float):
        """Set the initial linear velocity of the body.

        Args:
            x: The x-component of the velocity
            y: The y-component of the velocity
        Returns:
            The builder instance
        """
        self._def.linearVelocity.x = x
        self._def.linearVelocity.y = y
        return self

    def angular_velocity(self, radians: float):
        """Set the initial angular velocity of the body.

        Args:
            radians: The angular velocity in radians per second
        Returns:
            The builder instance
        """
        self._def.angularVelocity = radians
        return self

    def linear_damping(self, damping: float):
        """Set the linear damping of the body.

        Damping reduces the linear velocity over time.
        Args:
            damping: Float value for linear damping
        Returns:
            The builder instance
        """
        self._def.linearDamping = damping
        return self

    def angular_damping(self, damping: float):
        """Set the angular damping of the body.

        Damping reduces the angular velocity over time.
        Args:
            damping: Float value for angular damping
        Returns:
            The builder instance
        """
        self._def.angularDamping = damping
        return self

    def enable_sleep(self, enable: bool):
        """Set whether the body is allowed to sleep.

        Sleeping bodies are skipped in simulations for performance optimization.
        Args:
            enable: Boolean indicating whether sleeping is enabled
        Returns:
            The builder instance
        """
        self._def.enableSleep = enable
        return self

    def sleep_threshold(self, threshold: float):
        """Set the sleep threshold for the body.

        The minimum velocity below which the body will go to sleep.
        Args:
            threshold: Float value representing the sleep threshold
        Returns:
            The builder instance
        """
        self._def.sleepThreshold = threshold
        return self

    def box(
        self,
        width: float,
        height: float,
        radius=0.0,
        offset=(0, 0),
        angle=0.0,
        density: float = 1.0,
        friction: float = 0.2,
        restitution: float = 0.0,
        is_sensor: bool = False,
        collision_filter: CollisionFilter = None,
    ):
        """Add a box shape to the body during construction.

        Args:
            width: Full width of the box.
            height: Full height of the box.
            radius: The radius of the rounded corners (default: 0.0).
            offset: The offset of the box from the body's position (default: (0, 0)).
            angle: The angle of the box (default: 0.0).
            density: Mass density (kg/m²).
            friction: Friction coefficient (0-1).
            restitution: Bounciness (0-1).
            is_sensor: True for sensor shape (no collision response).
            collision_filter: Optional CollisionFilter instance for collision filtering.
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
                    "density": density,
                    "friction": friction,
                    "restitution": restitution,
                    "is_sensor": is_sensor,
                    "collision_filter": collision_filter,
                },
            }
        )
        return self

    def circle(
        self,
        radius: float,
        center: tuple = (0, 0),
        density: float = 1.0,
        friction: float = 0.2,
        restitution: float = 0.0,
        is_sensor: bool = False,
        collision_filter: CollisionFilter = None,
    ):
        """Add a circle shape to the body during construction.

        Args:
            radius: Radius of the circle.
            center: Local center position (x, y).
            density: Mass density (kg/m²).
            friction: Friction coefficient (0-1).
            restitution: Bounciness (0-1).
            is_sensor: True for sensor shape.
            collision_filter: Optional CollisionFilter instance for collision filtering.
        Returns:
            Self for method chaining.
        """
        self._shape_defs.append(
            {
                "type": "circle",
                "params": (radius, center),
                "kwargs": {
                    "density": density,
                    "friction": friction,
                    "restitution": restitution,
                    "is_sensor": is_sensor,
                    "collision_filter": collision_filter,
                },
            }
        )
        return self

    def capsule(
        self,
        point1: tuple,
        point2: tuple,
        radius: float,
        density: float = 1.0,
        friction: float = 0.2,
        restitution: float = 0.0,
        is_sensor: bool = False,
        collision_filter: CollisionFilter = None,
    ):
        """Add a vertical capsule shape (cylinder with hemispherical ends).

        Args:
            point1: The first endpoint of the capsule.
            point2: The second endpoint of the capsule.
            radius: Radius of the hemispherical ends.
            density: Mass density (kg/m²).
            friction: Friction coefficient (0-1).
            restitution: Bounciness (0-1).
            is_sensor: True for sensor shape.
            collision_filter: Optional CollisionFilter instance for collision filtering.
        Returns:
            Self for method chaining.
        """
        self._shape_defs.append(
            {
                "type": "capsule",
                "params": (point1, point2, radius),
                "kwargs": {
                    "density": density,
                    "friction": friction,
                    "restitution": restitution,
                    "is_sensor": is_sensor,
                    "collision_filter": collision_filter,
                },
            }
        )
        return self

    def polygon(
        self,
        vertices: list[tuple],
        radius: float = 0.0,
        density: float = 1.0,
        friction: float = 0.2,
        restitution: float = 0.0,
        is_sensor: bool = False,
        collision_filter: CollisionFilter = None,
    ):
        """Add a convex polygon shape.

        The given vertices are processed to compute their convex hull. An exception will be raised
        if the provided vertices do not form a valid convex polygon.

        Args:
            vertices: List of points that define the polygon shape.
            radius: The radius of the rounded corners (default: 0.0).
            density: Mass density (kg/m²).
            friction: Friction coefficient (0-1).
            restitution: Bounciness (0-1).
            is_sensor: True for sensor shape.
            collision_filter: Optional CollisionFilter instance for collision filtering.
        Returns:
            Self for method chaining.
        Raises:
            Exception: If the vertices cannot form a convex polygon.
        """
        # Validate convexity (this will raise an exception if the polygon is not convex)
        PolygonDef(vertices)
        self._shape_defs.append(
            {
                "type": "polygon",
                "params": (vertices,),
                "kwargs": {
                    "radius": radius,
                    "density": density,
                    "friction": friction,
                    "restitution": restitution,
                    "is_sensor": is_sensor,
                    "collision_filter": collision_filter,
                },
            }
        )
        return self

    def segment(
        self,
        start: tuple,
        end: tuple,
        density: float = 0.0,
        friction: float = 0.2,
        restitution: float = 0.0,
        is_sensor: bool = False,
        collision_filter: CollisionFilter = None,
    ):
        """Add a line segment shape with optional edge radius.

        Args:
            start: Starting point (x, y) in local coordinates.
            end: Ending point (x, y) in local coordinates.
            density: Typically 0 for static segments.
            friction: Friction coefficient (0-1).
            restitution: Bounciness (0-1).
            is_sensor: True for sensor shape.
            collision_filter: Optional CollisionFilter instance for collision filtering.
        Returns:
            Self for method chaining.
        """
        self._shape_defs.append(
            {
                "type": "segment",
                "params": (start, end),
                "kwargs": {
                    "density": density,
                    "friction": friction,
                    "restitution": restitution,
                    "is_sensor": is_sensor,
                    "collision_filter": collision_filter,
                },
            }
        )
        return self

    def chain(
        self,
        vertices: list[tuple],
        loop: bool = False,
        friction: float = 0.2,
        restitution: float = 0.0,
        collision_filter: CollisionFilter = None,
    ):
        """Add a chain shape to the body during construction.

        Args:
            vertices: List of points that define the chain shape. Must contain at least 4 vertices.
            loop: Boolean indicating whether the chain should be closed (looped). Default is False.
            friction: Friction coefficient (0-1).
            restitution: Bounciness (0-1).
            collision_filter: Optional CollisionFilter instance for collision filtering.
        Returns:
            Self for method chaining.
        """
        self._shape_defs.append(
            {
                "type": "chain",
                "params": (vertices,),
                "kwargs": {
                    "loop": loop,
                    "friction": friction,
                    "restitution": restitution,
                    "collision_filter": collision_filter,
                },
            }
        )
        return self

    def build(self) -> "Body":
        """Finalize the body creation and attach configured shapes.

        Creates and configures the body in the world using the specified properties.
        Returns:
            The newly created Body instance
        """
        body = Body(self.world, self._def)

        # Apply additional properties after creation
        if self._def.fixedRotation:
            lib.b2Body_SetFixedRotation(body._body_id, True)
        if self._def.isBullet:
            lib.b2Body_SetBullet(body._body_id, True)
        lib.b2Body_SetGravityScale(body._body_id, self._def.gravityScale)

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

    def __init__(self, world, body_def):
        """
        Initialize a Body instance.

        Args:
            world: The World instance in which this body exists.
            body_def: The body definition used to create this body.
        """
        self.world = world
        self.body_def = body_def
        self._body_id = lib.b2CreateBody(
            self.world._world_id, ffi.addressof(self.body_def)
        )
        self._handle = ffi.addressof(self._body_id)
        lib.b2Body_SetUserData(self._body_id, self._handle)
        self._shapes = []
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
        value = to_vec2(value)
        lib.b2Body_SetTransform(self._body_id, value.b2Vec2[0], rot)

    @property
    def linear_velocity(self):
        """Get the linear velocity of the body."""
        vel = lib.b2Body_GetLinearVelocity(self._body_id)
        return Vec2(vel.x, vel.y)

    @linear_velocity.setter
    def linear_velocity(self, value: VectorLike):
        """Set the linear velocity of the body."""
        value = to_vec2(value).b2Vec2[0]
        lib.b2Body_SetLinearVelocity(self._body_id, value)

    @property
    def angular_velocity(self):
        """Get angular velocity in radians/sec."""
        return lib.b2Body_GetAngularVelocity(self._body_id)

    @angular_velocity.setter
    def angular_velocity(self, value):
        """Set angular velocity in radians/sec."""
        lib.b2Body_SetAngularVelocity(self._body_id, float(value))

    @property
    def linear_damping(self):
        """Get the current linear damping value."""
        return lib.b2Body_GetLinearDamping(self._body_id)

    @linear_damping.setter
    def linear_damping(self, value: float):
        """Set the linear damping value."""
        lib.b2Body_SetLinearDamping(self._body_id, float(value))

    @property
    def angular_damping(self):
        """Get the current angular damping value."""
        return lib.b2Body_GetAngularDamping(self._body_id)

    @angular_damping.setter
    def angular_damping(self, value: float):
        """Set the angular damping value."""
        lib.b2Body_SetAngularDamping(self._body_id, float(value))

    @property
    def sleep_threshold(self):
        """Get the sleep threshold value."""
        return lib.b2Body_GetSleepThreshold(self._body_id)

    @sleep_threshold.setter
    def sleep_threshold(self, value: float):
        """Set the sleep threshold value."""
        lib.b2Body_SetSleepThreshold(self._body_id, float(value))

    @property
    def type(self):
        """Get the body type as a string ('dynamic', 'kinematic', or 'static')."""
        body_type = lib.b2Body_GetType(self._body_id)
        if body_type == lib.b2_dynamicBody:
            return "dynamic"
        elif body_type == lib.b2_kinematicBody:
            return "kinematic"
        else:
            return "static"

    @property
    def fixed_rotation(self):
        """Check if the body has fixed rotation."""
        return lib.b2Body_IsFixedRotation(self._body_id)

    @fixed_rotation.setter
    def fixed_rotation(self, value):
        """Set whether the body has fixed rotation."""
        lib.b2Body_SetFixedRotation(self._body_id, value)

    @property
    def is_bullet(self):
        """Check if the body is treated as a bullet."""
        return lib.b2Body_IsBullet(self._body_id)

    @is_bullet.setter
    def is_bullet(self, value):
        """Set whether the body is treated as a bullet."""
        lib.b2Body_SetBullet(self._body_id, value)

    @property
    def gravity_scale(self):
        """Get the gravity scale factor for this body."""
        return lib.b2Body_GetGravityScale(self._body_id)

    @gravity_scale.setter
    def gravity_scale(self, value):
        """Set the gravity scale factor for this body."""
        lib.b2Body_SetGravityScale(self._body_id, value)

    @property
    def awake(self):
        """Get the awake state of the body.

        Returns:
            bool: True if the body is awake, False otherwise.
        """
        return lib.b2Body_IsAwake(self._body_id)

    @awake.setter
    def awake(self, value: bool):
        """Set the awake state of the body.

        Args:
            value (bool): True to wake the body, False to put the body to sleep.
        """
        lib.b2Body_SetAwake(self._body_id, value)

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

    @property
    def mass(self):
        """Get the mass of the body in kilograms"""
        return lib.b2Body_GetMass(self._body_id)

    @property
    def rotational_inertia(self):
        """Get the rotational inertia of the body."""
        return lib.b2Body_GetRotationalInertia(self._body_id)

    @property
    def transform(self) -> Transform:
        """Get the body Transform. You can use it to convert world coordinates to body coordinates."""
        b2transform = lib.b2Body_GetTransform(self._body_id)
        return Transform.from_b2Transform(b2transform)

    def apply_force(self, force, point=None, wake=True):
        """Apply a force at a world point.

        Args:
            force: Tuple representing the force vector (Fx, Fy).
            point: Tuple representing the application point (x, y). Defaults to center.
            wake: Boolean indicating whether to wake the body.
        """
        x, y = force
        if point is None:
            lib.b2Body_ApplyForceToCenter(self._body_id, (x, y), wake)
        else:
            fx, fy = point
            lib.b2Body_ApplyForce(self._body_id, (x, y), (fx, fy), wake)

    def apply_torque(self, torque, wake=True):
        """Apply a torque to the body.

        Args:
            torque: Float value representing the torque.
            wake: Boolean indicating whether to wake the body.
        """
        lib.b2Body_ApplyTorque(self._body_id, torque, wake)

    def apply_linear_impulse(self, impulse, point=None, wake=True):
        """Apply a linear impulse at a world point.

        Args:
            impulse: Tuple representing the impulse vector (Ix, Iy).
            point: Tuple representing the application point (x, y). Defaults to center.
            wake: Boolean indicating whether to wake the body.
        """
        x, y = impulse
        if point is None:
            lib.b2Body_ApplyLinearImpulseToCenter(self._body_id, (x, y), wake)
        else:
            fx, fy = point
            lib.b2Body_ApplyLinearImpulse(self._body_id, (x, y), (fx, fy), wake)

    def add_box(
        self,
        width: float,
        height: float,
        radius: float = 0.0,
        offset: tuple = (0, 0),
        angle: float = 0.0,
        density: float = None,
        friction: float = None,
        restitution: float = None,
        is_sensor: bool = None,
        collision_filter=None,
        custom_color=None,
    ):
        """Add a box shape to the body.

        Args:
            width: Full width of the box.
            height: Full height of the box.
            radius: The radius of the rounded corners (default: 0.0).
            offset: The offset of the box from the body's position (default: (0, 0)).
            angle: The rotation angle of the box in radians (default: 0.0).
            density: Mass density of the shape.
            friction: Friction coefficient.
            restitution: Bounciness.
            is_sensor: Flag indicating whether the shape is a sensor.
            collision_filter: Optional CollisionFilter instance for collision filtering.
            custom_color: Optional custom debug draw color (uint32_t).

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
            density,
            friction,
            restitution,
            is_sensor,
            collision_filter,
            custom_color,
        )
        self._shapes.append(shape)
        return shape

    def add_circle(
        self,
        radius: float,
        center: tuple = (0, 0),
        density: float = None,
        friction: float = None,
        restitution: float = None,
        is_sensor: bool = None,
        collision_filter=None,
        custom_color=None,
    ):
        """Add a circle shape to the body.

        Args:
            radius: Radius of the circle.
            center: Center of the circle (default: (0, 0)).
            density: Mass density of the shape.
            friction: Friction coefficient.
            restitution: Bounciness.
            is_sensor: Flag indicating whether the shape is a sensor.
            collision_filter: Optional CollisionFilter instance for collision filtering.
            custom_color: Optional custom debug draw color (uint32_t).

        Returns:
            The created circle shape.
        """
        shape = Circle.create(
            self,
            radius,
            center,
            density,
            friction,
            restitution,
            is_sensor,
            collision_filter,
            custom_color,
        )
        self._shapes.append(shape)
        return shape

    def add_capsule(
        self,
        point1: tuple,
        point2: tuple,
        radius: float,
        density: float = None,
        friction: float = None,
        restitution: float = None,
        is_sensor: bool = None,
        collision_filter=None,
        custom_color=None,
    ):
        """Add a capsule shape to the body.

        Args:
            point1: First endpoint of the capsule.
            point2: Second endpoint of the capsule.
            radius: Radius of the capsule.
            density: Mass density of the shape.
            friction: Friction coefficient.
            restitution: Bounciness.
            is_sensor: Flag indicating whether the shape is a sensor.
            collision_filter: Optional CollisionFilter instance for collision filtering.
            custom_color: Optional custom debug draw color (uint32_t).

        Returns:
            The created capsule shape.
        """
        shape = Capsule.create(
            self,
            point1,
            point2,
            radius,
            density,
            friction,
            restitution,
            is_sensor,
            collision_filter,
            custom_color,
        )
        self._shapes.append(shape)
        return shape

    def add_polygon(
        self,
        vertices: list[tuple],
        radius: float = 0.0,
        density: float = None,
        friction: float = None,
        restitution: float = None,
        is_sensor: bool = None,
        collision_filter=None,
        custom_color=None,
    ):
        """Add a convex polygon shape to the body.

        Args:
            vertices: List of vertices defining the polygon.
            radius: Optional radius for rounded corners (default: 0.0).
            density: Mass density of the shape.
            friction: Friction coefficient.
            restitution: Bounciness.
            is_sensor: Flag indicating whether the shape is a sensor.
            collision_filter: Optional CollisionFilter instance for collision filtering.
            custom_color: Optional custom debug draw color (uint32_t).

        Returns:
            The created polygon shape.
        """
        shape = Polygon.create(
            self,
            vertices,
            radius,
            density,
            friction,
            restitution,
            is_sensor,
            collision_filter,
            custom_color,
        )
        self._shapes.append(shape)
        return shape

    def add_segment(
        self,
        point1: tuple,
        point2: tuple,
        density: float = None,
        friction: float = None,
        restitution: float = None,
        is_sensor: bool = None,
        collision_filter=None,
        custom_color=None,
    ):
        """Add a line segment shape to the body.

        Args:
            point1: Starting point of the segment.
            point2: Ending point of the segment.
            density: Mass density of the shape.
            friction: Friction coefficient.
            restitution: Bounciness.
            is_sensor: Flag indicating whether the shape is a sensor.
            collision_filter: Optional CollisionFilter instance for collision filtering.
            custom_color: Optional custom debug draw color (uint32_t).

        Returns:
            The created segment shape.
        """
        shape = Segment.create(
            self,
            point1,
            point2,
            density,
            friction,
            restitution,
            is_sensor,
            collision_filter,
            custom_color,
        )
        self._shapes.append(shape)
        return shape

    def add_chain(
        self,
        vertices: list[tuple],
        loop: bool = False,
        friction: float = None,
        restitution: float = None,
        collision_filter=None,
        custom_color=None,
    ):
        """Add a chain shape to the body.

        Args:
            vertices: List of vertices defining the chain (must contain at least 4 vertices).
            loop: Boolean indicating whether the chain should be closed (looped).
            friction: Friction coefficient.
            restitution: Bounciness.
            collision_filter: Optional CollisionFilter instance for collision filtering.
            custom_color: Optional custom debug draw color (uint32_t).

        Returns:
            The created chain shape.
        """
        shape = Chain.create(
            self, vertices, loop, friction, restitution, collision_filter, custom_color
        )
        self._shapes.append(shape)
        return shape

    def remove_shape(self, shape):
        """Remove a shape from the body."""
        if shape in self._shapes:
            lib.b2DestroyShape(shape._shape_id, True)  # Update body mass
            self._shapes.remove(shape)

    def is_sleep_enabled(self):
        """Check if the body is allowed to sleep."""
        return lib.b2Body_IsSleepEnabled(self._body_id)

    def destroy(self):
        """
        Destroy this body and remove it from the world.
        """
        if getattr(self, "_body_id", None) is None:
            return
        lib.b2DestroyBody(self._body_id)
        if hasattr(self.world, "_bodies"):
            self.world._bodies.pop(self._body_id, None)
        self._body_id = None

    # TODO: currently is segfaults one of the tests. need to figure out why.
    # def __del__(self):
    # Attempt to clean up if destroy() wasn't explicitly called.
    # self.destroy()
