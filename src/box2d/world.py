# src/box3d/world.py

from ._box2d import lib, ffi
from .body import BodyBuilder
from .math import Vec2
from .debug_draw import DebugDraw
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

    def step(self, time_step, substep_count = 4):
        """Simulate one time step"""
        lib.b2World_Step(self._world_id, time_step, substep_count)

    def new_body(self):
        """Entry point for body creation"""
        return BodyBuilder(self)

    def _track_body(self, body):
        """Store reference to a Body instance"""
        self._bodies[body._body_id] = body

    def get_bodies(self):
        """Get list of all current bodies"""
        return list(self._bodies.values())

    def draw(self, debug_draw: DebugDraw):
        """Draw the world"""
        lib.b2World_Draw(self._world_id, ffi.addressof(debug_draw._debug_draw))

    def query_aabb(self, aabb) -> list:
        """Query all shapes overlapping the given AABB region"""
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
            {"lowerBound": {"x": aabb.lower.x, "y": aabb.lower.y},
             "upperBound": {"x": aabb.upper.x, "y": aabb.upper.y}}, 
            {"categoryBits": 0x0001, "maskBits": 0xFFFF},
            _overlap_callback, 
            ffi.NULL
        )
        return results

    def __del__(self):
        if hasattr(self, '_bodies'):
            # Clear body references
            self._bodies.clear()
        if hasattr(self, '_world_id'):
            lib.b2DestroyWorld(self._world_id)
