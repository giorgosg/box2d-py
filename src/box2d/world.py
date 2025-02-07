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
        # Dictionary to store references to Python Body objects
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
        vec = ffi.new("b2Vec2*", {'x': value[0], 'y': value[1]})
        lib.b2World_SetGravity(self._world_id, vec[0])

    def step(self, time_step, substep_count = 4):
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

    def _track_body(self, body: 'Body'):
        """Internal method to track body references. Called automatically during body creation.
    
        Args:
            body: Body instance to register in the world
        """
        self._bodies[body._body_id] = body

    def get_bodies(self):
        """Get list of all active bodies in the world.
    
        Returns:
            list[Body]: Copies of registered body references
        
        Example:
            >>> world = World()
            >>> box = world.new_body().dynamic().build()
            >>> len(world.get_bodies())
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
            {"lowerBound": {"x": aabb.lower.x, "y": aabb.lower.y},
             "upperBound": {"x": aabb.upper.x, "y": aabb.upper.y}}, 
            {"categoryBits": 0x0001, "maskBits": 0xFFFF},
            _overlap_callback, 
            ffi.NULL
        )
        return results

    def __del__(self):
        """Clean up world resources. Automatically called when instance is garbage collected.
    
        Destroys Box2D world instance.
        """
        if hasattr(self, '_world_id'):
            lib.b2DestroyWorld(self._world_id)
