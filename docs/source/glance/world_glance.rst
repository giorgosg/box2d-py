World Module at a Glance
========================

.. automodule:: box2d.world
   :noindex:

This page provides a structured overview of the Box2D World class and related components. The World class serves as the foundation of any Box2D simulation:

- **Central coordinator**: Manages all bodies, joints, and performs collision detection and physics simulation
- **Body factory**: Creates bodies through a builder pattern
- **Joint factory**: Creates joints between bodies with various constraints
- **Query system**: Provides spatial queries (ray casts, overlap tests) for game logic
- **Stepping control**: Manages time advancement and solver parameters

World
-----

The central class representing a complete physics simulation. Contains bodies, joints, and handles all collision detection and physics calculations.

Creation and Destruction
^^^^^^^^^^^^^^^^^^^^^^^^

* ``World(gravity=(0, -10), threads=1)`` - Create a world with specified gravity
* ``world.destroy()`` - Clean up all resources

Simulation Control
^^^^^^^^^^^^^^^^^^

* ``world.step(time_step, substep_count=4)`` - Advance simulation by specified time
* ``world.draw(debug_draw)`` - Render world using debug drawing interface

Body Management
^^^^^^^^^^^^^^^

* ``world.new_body()`` - Start building a new body
* ``world.bodies`` - Get list of all bodies in world

Joint Creation
^^^^^^^^^^^^^

* ``world.add_distance_joint(body_a, body_b, ...)`` - Create a joint keeping bodies at a specific distance
* ``world.add_revolute_joint(body_a, body_b, ...)`` - Create a hinge-like rotational joint 
* ``world.add_prismatic_joint(body_a, body_b, ...)`` - Create a joint allowing sliding along an axis
* ``world.add_wheel_joint(body_a, body_b, ...)`` - Create a joint for vehicle suspension simulation
* ``world.add_weld_joint(body_a, body_b, ...)`` - Create a joint that rigidly connects bodies
* ``world.add_motor_joint(body_a, body_b, ...)`` - Create a joint to control relative motion
* ``world.add_mouse_joint(body, target, ...)`` - Create a joint for interactive object dragging

Spatial Queries
^^^^^^^^^^^^^^

* ``world.query_aabb(aabb, collision_filter=None, max_results=None)`` - Find shapes in a specified AABB
* ``world.query_circle(position, radius, collision_filter=None, max_results=None)`` - Find shapes in a circular area
* ``world.ray_cast(origin, translation, collision_filter=None, first_hit_only=False)`` - Find shapes along a ray path
* ``world.get_sensor_events()`` - Get sensor overlap events from last simulation step

Simulation Parameters
^^^^^^^^^^^^^^^^^^^

* ``world.gravity`` - Get/set gravitational acceleration vector (m/s²)
* ``world.enable_sleep`` - Toggle body sleeping for inactive objects
* ``world.enable_continuous`` - Toggle continuous collision detection
* ``world.contact_hertz`` - Get/set contact stiffness frequency
* ``world.contact_damping_ratio`` - Get/set contact damping ratio
* ``world.contact_push_velocity`` - Get/set max velocity for penetration resolution
* ``world.restitution_threshold`` - Get/set minimum speed for restitution effects
* ``world.hit_event_threshold`` - Get/set minimum collision speed for hit events

Examples
^^^^^^^^

Creating a world with bodies:

.. code-block:: python

    # Create world with gravity pointing down
    world = World(gravity=(0, -9.8))
    
    # Create a ground body
    ground = world.new_body().position(0, -10).box(50, 1).build()
    
    # Create a dynamic box
    box = world.new_body().dynamic().position(0, 5).box(1, 1).build()
    
    # Run simulation
    for i in range(60):
        world.step(1/60)
        print(f"Box position: {box.position}")

Adding joints:

.. code-block:: python

    # Create a revolute joint (hinge)
    pendulum = world.new_body().dynamic().position(0, 5).circle(1).build()
    joint = world.add_revolute_joint(
        ground, pendulum, 
        anchor=(0, 10),
        enable_limit=True,
        lower_angle=-0.5,
        upper_angle=0.5
    )

Spatial queries:

.. code-block:: python

    # Find objects in an area
    overlapping_shapes = world.query_circle(position=(10, 5), radius=3)
    
    # Cast a ray and find intersections
    ray_hits = world.ray_cast(origin=(0, 0), translation=(10, 10))
    for hit in ray_hits:
        print(f"Hit at {hit.point}, normal: {hit.normal}")

RayCastResult
------------

Contains information about a ray's intersection with a shape.

Properties
^^^^^^^^^

* ``shape`` - The shape hit by the ray
* ``point`` - The hit point in world coordinates
* ``normal`` - Surface normal at hit point
* ``fraction`` - Fraction of ray length to hit point (0.0 to 1.0)

SensorEvent
----------

Event generated when a sensor shape begins or ends overlap with another shape.

Properties
^^^^^^^^^

* ``sensor`` - The sensor shape that triggered the event
* ``visitor`` - The shape that entered or left the sensor
* ``begin`` - True for beginning overlap, False for ending overlap

SensorEvents
-----------

Collection of sensor events from a simulation step.

Properties
^^^^^^^^^

* ``begin`` - List of sensor events for new overlaps
* ``end`` - List of sensor events for ended overlaps

Utility Functions
---------------

* ``make_overlap_callback(results, max_results=None)`` - Create callback for overlap queries
* ``make_ray_cast_callback(results)`` - Create callback for ray casting