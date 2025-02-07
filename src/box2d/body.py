from box2d._box2d import lib, ffi
from box2d.vec2 import Vec2

class BodyBuilder:
    def __init__(self, world):
        self.world = world
        self._def = lib.b2DefaultBodyDef()
        self._shapes = []

    def dynamic(self):
        self._def.type = lib.b2_dynamicBody
        return self

    def position(self, x: float, y: float):
        self._def.position.x = x
        self._def.position.y = y
        return self

    def add_box(self, width: float, height: float, density=1.0):
        """Add box shape to body"""
        shape_def = lib.b2DefaultShapeDef()
        shape_def.density = density

        box = ffi.addressof(lib.b2MakeBox(width, height))
        self._shapes.append((lib.b2CreatePolygonShape, box, shape_def))
        return self

    def add_circle(self, radius: float, center=(0,0), density=1.0):
        """Add circle shape to body"""
        shape_def = lib.b2DefaultShapeDef()
        shape_def.density = density

        circle = ffi.new("b2Circle*")
        circle.radius = radius
        circle.center.x, circle.center.y = center
        self._shapes.append((lib.b2CreateCircleShape, circle, shape_def))
        return self

    def build(self):
        """Finalize body creation"""
        body_id = lib.b2CreateBody(self.world._world_id, ffi.addressof(self._def))

        # Attach shapes
        for cfunc, shape, shape_def in self._shapes:
            cfunc(
                body_id,
                ffi.addressof(shape_def),
                shape
            )
        return Body(body_id)


class Body():
    def __init__(self, body_id):
        self._body_id = body_id

    @property
    def position(self):
        """Get body position as (x, y) tuple"""
        pos = lib.b2Body_GetPosition(self._body_id)
        return Vec2(pos.x, pos.y)

    @position.setter
    def position(self, value):
        """Set body position from (x, y) tuple"""
        x, y = value
        # Get current rotation since SetTransform needs both position and rotation
        rot = lib.b2Body_GetRotation(self._body_id)

        # Create position vector
        pos = ffi.new("b2Vec2 *", {'x': x, 'y': y})
        lib.b2Body_SetTransform(self._body_id, pos, rot)

    @property
    def linear_velocity(self):
        """Get linear velocity as (vx, vy) tuple"""
        vel = lib.b2Body_GetLinearVelocity(self._body_id)
        return Vec2(vel.x, vel.y)

    @linear_velocity.setter
    def linear_velocity(self, value):
        """Set linear velocity from (vx, vy) tuple"""
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
    def type(self):
        """Get body type as string"""
        body_type = lib.b2Body_GetType(self._body_id)
        if body_type == lib.b2_dynamicBody:
            return "dynamic"
        elif body_type == lib.b2_kinematicBody:
            return "kinematic"
        else:
            return "static"

    def create_box(self, dimensions=None, **kwargs):
        box = Box(self, dimensions, **kwargs)
        return self
