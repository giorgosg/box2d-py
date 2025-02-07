World Module
============

The core physics simulation container.

.. automodule:: box2d.world
   :members: World
   :special-members: __init__

Main Interface
--------------
.. autoclass:: World
   :members:
   :undoc-members:

   .. rubric:: Essential Methods

   - :py:meth:`~box2d.world.World.gravity` - Get/set global gravity vector
   - :py:meth:`~box2d.world.World.new_body` - Create a body builder
   - :py:meth:`~box2d.world.World.step` - Advance simulation by time step

Example Usage
-------------
Creating a world with gravity:

.. code-block:: python

   from box2d import World, Vec2

   # Create world with downward gravity
   world = World(gravity=Vec2(0, -9.81))

   # Simulation step
   world.step(time_step=1/60, velocity_iters=6, position_iters=2)

Spatial Queries
---------------
.. automethod:: box2d.world.World.query_aabb