from box2d._box2d import lib, ffi
from .math import Vec2
from .shape import Box, Circle, Capsule, Segment, Polygon, convex_hull

class BodyBuilder:
    """Builder for creating Box2D bodies with chained configuration methods.
    
    Example:
        >>> body = world.new_body()
        >>> body.dynamic()
        >>> body.position(2, 3)
        >>> body.box(half_x=1, half_y=0.5)
        >>> body.circle(radius=0.5, offset=(1, 0))
        >>> body = body.build()
    """
    def __init__(self, world):
        """Initialize the BodyBuilder with the world context.
        
        Args:
            world: The World instance where the body will be created
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

    def fixed_rotation(self, fixed):
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

    def box(self, width: float, height: float, radius=0.0, offset=(0,0), angle=0.0,
           density: float = 1.0, friction: float = 0.2, 
           restitution: float = 0.0, is_sensor: bool = False):
        """Add a box shape to the body during construction.
        
        Args:
            width: Full width of the box
            height: Full height of the box
            radius: The radius of the rounded corners (default: 0.0)
            offset: The offset of the box from the body's position (default: (0,0))
            angle: The angle of the box (default: 0.0)
            density: Mass density (kg/m²)
            friction: Friction coefficient (0-1)
            restitution: Bounciness (0-1)
            is_sensor: True for sensor shape (no collision response)
        Returns:
            self for method chaining
        """
        self._shape_defs.append({
            'type': 'box',
            'params': (width, height),
            'kwargs': {
                'radius': radius,
                'offset': offset,
                'angle': angle,
                'density': density,
                'friction': friction,
                'restitution': restitution,
                'is_sensor': is_sensor
            }
        })
        return self

    def circle(self, radius: float, center: tuple = (0,0),
              density: float = 1.0, friction: float = 0.2,
              restitution: float = 0.0, is_sensor: bool = False):
        """Add a circle shape to the body during construction.
        
        Args:
            radius: Radius of the circle
            center: Local center position (x,y)
            density: Mass density (kg/m²)
            friction: Friction coefficient (0-1)
            restitution: Bounciness (0-1)
            is_sensor: True for sensor shape
        Returns:
            self for method chaining
        """
        self._shape_defs.append({
            'type': 'circle', 
            'params': (radius, center),
            'kwargs': {
                'density': density,
                'friction': friction,
                'restitution': restitution,
                'is_sensor': is_sensor
            }
        })
        return self

    def capsule(self, point1: tuple, point2: tuple, radius: float,
                density: float = 1.0, friction: float = 0.2, 
                restitution: float = 0.0, is_sensor: bool = False):
        """Add a vertical capsule shape (cylinder with hemispherical ends).
        
        Args:
            point1: The first endpoint of the capsule
            point2: The second endpoint of the capsule
            radius: Radius of the hemispherical ends
            density: Mass density (kg/m²)
            friction: Friction coefficient (0-1)
            restitution: Bounciness (0-1)
            is_sensor: True for sensor shape
        """
        self._shape_defs.append({
            'type': 'capsule',
            'params': (point1, point2, radius),
            'kwargs': {
                'density': density,
                'friction': friction,
                'restitution': restitution,
                'is_sensor': is_sensor
            }
        })
        return self

    def polygon(self, vertices: list[tuple], radius: float = 0.0,
               density: float = 1.0, friction: float = 0.2,
               restitution: float = 0.0, is_sensor: bool = False):
        """Add a convex polygon shape.

        The given vertices are processed to compute their convex hull. An exception will be raised
        if the provided vertices do not form a valid convex polygon.
        
        Args:
            vertices: List of points that define the polygon shape
            radius: The radius of the rounded corners (default: 0.0)
            density: Mass density (kg/m²)
            friction: Friction coefficient (0-1)
            restitution: Bounciness (0-1)
            is_sensor: True for sensor shape

        Raises:
            Exception: If the vertices cannot form a convex polygon.
        """
        # Compute the convex hull of the polygon so an exception is raised
        # at the function call if the points do not form a convex polygon.
        vertices = convex_hull(vertices)
        self._shape_defs.append({
            'type': 'polygon',
            'params': (vertices,),
            'kwargs': {
                'radius': radius,
                'density': density,
                'friction': friction,
                'restitution': restitution,
                'is_sensor': is_sensor
            }
        })
        return self

    def segment(self, start: tuple, end: tuple, 
               density: float = 0.0,
               friction: float = 0.2, restitution: float = 0.0, 
               is_sensor: bool = False):
        """Add a line segment shape with optional edge radius.
        
        Args:
            start: Starting point (x,y) in local coordinates
            end: Ending point (x,y) in local coordinates
            density: Typically 0 for static segments
            friction: Friction coefficient (0-1)
            restitution: Bounciness (0-1)
            is_sensor: True for sensor shape
        """
        self._shape_defs.append({
            'type': 'segment',
            'params': (start, end),
            'kwargs': {
                'density': density,
                'friction': friction,
                'restitution': restitution,
                'is_sensor': is_sensor
            }
        })
        return self

    def build(self) -> 'Body':
        """Finalize the body creation and attach configured shapes.
        
        Creates and configures the body in the world using the specified properties.
        Returns:
            The newly created Body instance
        """
        body_id = lib.b2CreateBody(self.world._world_id, ffi.addressof(self._def))
        body = Body(body_id)
        
        # Track the body in the world
        self.world._track_body(body)
        
        # Apply additional properties after creation
        if self._def.fixedRotation:
            lib.b2Body_SetFixedRotation(body._body_id, True)
        if self._def.isBullet:
            lib.b2Body_SetBullet(body._body_id, True)
        lib.b2Body_SetGravityScale(body._body_id, self._def.gravityScale)

        # Create shapes
        for shape_def in self._shape_defs:
            method = getattr(body, f'add_{shape_def["type"]}')
            method(*shape_def['params'], **shape_def['kwargs'])
       
        return body


class Body():
    """Represents a rigid body in the 2D physics simulation.
    
    Bodies can be dynamic, kinematic, or static, and can have various forces,
    impulses, and constraints applied to them.
    """
    def __init__(self, body_id):
        """Initialize a Body instance.
        
        Args:
            body_id: The unique identifier for this body in the physics simulation
        """
        self._body_id = body_id
        self._handle = ffi.addressof(self._body_id)
        lib.b2Body_SetUserData(body_id, self._handle)
        self._shapes = []

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
    def position(self, value):
        """Set the world position of the body."""
        # Get current rotation since SetTransform needs both position and rotation
        rot = lib.b2Body_GetRotation(self._body_id)

        lib.b2Body_SetTransform(self._body_id, value, rot)

    @property
    def linear_velocity(self):
        """Get the linear velocity of the body."""
        vel = lib.b2Body_GetLinearVelocity(self._body_id)
        return Vec2(vel.x, vel.y)

    @linear_velocity.setter
    def linear_velocity(self, value):
        """Set the linear velocity of the body."""
        x, y = value
        vec = ffi.new("b2Vec2 *", {'x': x, 'y': y})
        lib.b2Body_SetLinearVelocity(self._body_id, vec[0])

    @property
    def angular_velocity(self):
        """Get angular velocity in radians/sec"""
        return lib.b2Body_GetAngularVelocity(self._body_id)

    @angular_velocity.setter
    def angular_velocity(self, value):
        """Set angular velocity in radians/sec"""
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

    def apply_force(self, force, point=None, wake=True):
        """Apply a force at a world point.
        
        Args:
            force: Tuple representing the force vector (Fx, Fy)
            point: Tuple representing the application point (x, y)
            wake: Boolean indicating whether to wake the body if it's sleeping
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
            torque: Float value representing the torque to apply
            wake: Boolean indicating whether to wake the body if it's sleeping
        """
        lib.b2Body_ApplyTorque(self._body_id, torque, wake)

    def apply_linear_impulse(self, impulse, point=None, wake=True):
        """Apply a linear impulse at a world point.
        
        Args:
            impulse: Tuple representing the impulse vector (Ix, Iy)
            point: Tuple representing the application point (x, y)
            wake: Boolean indicating whether to wake the body if it's sleeping
        """
        x, y = impulse
        if point is None:
            lib.b2Body_ApplyLinearImpulseToCenter(self._body_id, (x, y), wake)
        else:
            fx, fy = point
            lib.b2Body_ApplyLinearImpulse(self._body_id, (x, y), (fx, fy), wake)

    def add_box(self, width: float, height: float, radius=0.0, offset=(0,0), angle=0.0,
                density=None, friction=None, restitution=None, is_sensor=None):
        """Add a box shape to the body.
        
        Args:
            width: The width of the box
            height: The height of the box
            radius: The radius of the rounded corners (default: 0.0)
            offset: The offset of the box from the body's position (default: (0,0))
            angle: The angle of the box (default: 0.0)
            density: Mass density (kg/m²).
            friction: Friction coefficient.
            restitution: Bounciness (0-1).
            is_sensor: Whether this shape is a sensor.
        """
        shape = Box(self, width=width, height=height, radius=radius, offset=offset, angle=angle, 
                    density=density, friction=friction, restitution=restitution, 
                    is_sensor=is_sensor)
        self._shapes.append(shape)
        return shape

    def add_circle(self, radius: float, center=(0,0), 
                   density=None, friction=None, restitution=None, is_sensor=None):
        """Add a circle shape to the body.
        
        Args:
            radius: The radius of the circle
            center: The center point of the circle (default: (0,0))
            density: Mass density (kg/m²).
            friction: Friction coefficient.
            restitution: Bounciness (0-1).
            is_sensor: Whether this shape is a sensor.
        """
        shape = Circle(self, radius, center, density, friction, restitution, is_sensor)
        self._shapes.append(shape)
        return shape

    def add_capsule(self, point1, point2, radius, 
                    density=None, friction=None, restitution=None, is_sensor=None):
        """Add a capsule shape to the body.
        
        Args:
            point1: The first endpoint of the capsule
            point2: The second endpoint of the capsule
            radius: The radius of the capsule
            density: Mass density (kg/m²).
            friction: Friction coefficient.
            restitution: Bounciness (0-1).
            is_sensor: Whether this shape is a sensor.
        """
        shape = Capsule(self, point1, point2, radius, density, friction, restitution, is_sensor)
        self._shapes.append(shape)
        return shape

    def add_polygon(self, vertices, radius=0.0,
                    density=None, friction=None, restitution=None, is_sensor=None):
        """Add a polygon shape to the body.
        
        Args:
            vertices: List of points that define the polygon shape
            radius: The radius of the rounded corners (default: 0.0)
            density: Mass density (kg/m²).
            friction: Friction coefficient.
            restitution: Bounciness (0-1).
            is_sensor: Whether this shape is a sensor.
        """
        shape = Polygon(self, vertices, radius, density, friction, restitution, is_sensor)
        self._shapes.append(shape)
        return shape

    def add_segment(self, point1, point2, 
                    density=None, friction=None, restitution=None, is_sensor=None):
        """Add a segment shape to the body.
        
        Args:
            point1: The first endpoint of the segment
            point2: The second endpoint of the segment
            density: Mass density (kg/m²).
            friction: Friction coefficient.
            restitution: Bounciness (0-1).
            is_sensor: Whether this shape is a sensor.
        """
        shape = Segment(self, point1, point2, density, friction, restitution, is_sensor)
        self._shapes.append(shape)
        return shape

    def remove_shape(self, shape):
        """Remove a shape from the body."""
        if shape in self._shapes:
            lib.b2DestroyShape(shape._shape_id, True)  # Update body mass
            self._shapes.remove(shape)


    def is_sleep_enabled(self):
        """Check if the body is allowed to sleep"""
        return lib.b2Body_IsSleepEnabled(self._body_id)