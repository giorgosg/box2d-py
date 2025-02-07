# src/box3d/world.py

from box2d._box2d import lib, ffi
from box2d.body import BodyBuilder
from box2d.vec2 import Vec2

class World:
    def __init__(self, gravity=(0, -10)):
        world_def = lib.b2DefaultWorldDef()
        world_def.gravity.x, world_def.gravity.y = gravity
        self._world_id = lib.b2CreateWorld(ffi.addressof(world_def))
        # Dictionary to store references to Python Body objects
        self._bodies = {}

    @property
    def gravity(self):
        """Get world gravity vector"""
        g = lib.b2World_GetGravity(self._world_id)
        return Vec2(g.x, g.y)

    @gravity.setter
    def gravity(self, value):
        """Set world gravity vector"""
        x, y = value
        vec = ffi.new("b2Vec2*", {'x': value[0], 'y': value[1]})
        lib.b2World_SetGravity(self._world_id, vec[0])

    def step(self, dt, velocity_iterations = 4):
        """Simulate one time step"""
        lib.b2World_Step(self._world_id, dt, velocity_iterations)

    def __del__(self):
        if hasattr(self, '_world_id'):
            lib.b2DestroyWorld(self._world_id)

    def new_body(self):
        """Entry point for body creation"""
        return BodyBuilder(self)
    def _track_body(self, body):
        """Store reference to a Body instance"""
        self._bodies[body._body_id] = body
        lib.b2Body_SetUserData(body._body_id, ffi.new_handle(body))

    def get_bodies(self):
        """Get list of all current bodies"""
        return list(self._bodies.values())

    def __del__(self):
        if hasattr(self, '_bodies'):
            # Clear body references
            self._bodies.clear()
        if hasattr(self, '_world_id'):
            lib.b2DestroyWorld(self._world_id)
