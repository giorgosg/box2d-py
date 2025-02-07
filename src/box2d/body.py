from box2d._box2d import lib, ffi
from .vec2 import Vec2
from .shape import Box, Circle

class BodyBuilder:
    def __init__(self, world):
        self.world = world
        self._def = lib.b2DefaultBodyDef()
        self._shapes = []

    def dynamic(self):
        self._def.type = lib.b2_dynamicBody
        return self

    def static(self):
        self._def.type = lib.b2_staticBody
        return self

    def kinematic(self):
        self._def.type = lib.b2_kinematicBody
        return self

    def position(self, x: float, y: float):
        self._def.position.x = x
        self._def.position.y = y
        return self

    def linear_velocity(self, x: float, y: float):
        self._def.linearVelocity.x = x
        self._def.linearVelocity.y = y
        return self

    def angular_velocity(self, radians: float):
        self._def.angularVelocity = radians
        return self

    def enable_sleep(self, enable: bool):
        self._def.enableSleep = enable
        return self

    def build(self):
        """Finalize body creation"""
        body_id = lib.b2CreateBody(self.world._world_id, ffi.addressof(self._def))

        body = Body(body_id)
        # Track the body in the world
        self.world._track_body(body)
        return body


class Body():
    def __init__(self, body_id):
        self._body_id = body_id
        lib.b2Body_SetUserData(body_id, ffi.new_handle(self))
        self._shapes = []
        
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

        lib.b2Body_SetTransform(self._body_id, value, rot)

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

    def add_box(self, width: float, height: float, density=None, friction=None):
        shape = Box(self, width, height, density, friction)
        self._shapes.append(shape)
        return self

    def add_circle(self, radius: float, center=(0,0), density=None, friction=None):
        shape = Circle(self, radius, center, density, friction)
        self._shapes.append(shape)
        return self

    def is_sleep_enabled(self):
        """Check if the body is allowed to sleep"""
        return lib.b2Body_IsSleepEnabled(self._body_id)