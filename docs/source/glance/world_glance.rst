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

* ``World(gravity=(0, -10), threads=1, capacity=None)`` - Create a world with specified gravity;
  ``capacity`` (a ``Capacity``, e.g. another world's ``max_capacity``) sets room aside up front
* ``world.destroy()`` - Destroy the world and every body, shape and joint in it
* ``world.is_valid`` - Whether the world is still live, i.e. has not been destroyed
* ``world.user_data`` - Any Python object to keep with the world

The world keeps what it contains: a body, shape or joint stays alive while it
does, whether or not the caller kept the object that created it, and anything
that hands it back -- ``body.joints``, a ray cast, an event -- returns that same
object. Events describe the step that finished, so they can name something
destroyed since: a sensor event gives None for a destroyed sensor or visitor,
and body and joint events leave such objects out. Destroying a body takes its
shapes and joints with it, a mouse joint's proxy body included; anything
destroyed raises ``DestroyedError`` if used. Nothing can be created or
destroyed from a callback during ``world.step()``, nor the world stepped again:
each raises ``RuntimeError`` then, so do it after the step.

Simulation Control
^^^^^^^^^^^^^^^^^^

* ``world.step(time_step, substep_count=4)`` - Advance simulation by specified time
* ``world.draw(debug_draw)`` - Render world using debug drawing interface
* ``world.explode(position, radius, impulse_per_length, falloff=None, mask=None)`` - Apply a radial impulse to the dynamic shapes within a radius

Body Management
^^^^^^^^^^^^^^^

* ``world.new_body()`` - Start building a new body
* ``world.add_body(body_type=None, position=None, ...)`` - Create a body directly, with ``BodyDef`` fields as keywords
* ``world.bodies`` - Get list of all bodies in world
* ``world.awake_body_count`` - How many bodies are awake; zero once a scene has come to rest
* ``world.bounds`` - The box containing every shape in the world

Joint Creation
^^^^^^^^^^^^^^

* ``world.add_joint(joint_def)`` - Create a joint from any definition in ``box2d.jointdef``; the methods below build one and call this
* ``world.add_distance_joint(body_a, body_b, ...)`` - Create a joint keeping bodies at a specific distance
* ``world.add_revolute_joint(body_a, body_b, ...)`` - Create a hinge-like rotational joint 
* ``world.add_prismatic_joint(body_a, body_b, ...)`` - Create a joint allowing sliding along an axis
* ``world.add_wheel_joint(body_a, body_b, ...)`` - Create a joint for vehicle suspension simulation
* ``world.add_weld_joint(body_a, body_b, ...)`` - Create a joint that rigidly connects bodies
* ``world.add_motor_joint(body_a, body_b, ...)`` - Create a joint to control relative motion
* ``world.add_mouse_joint(body, target, ...)`` - Create a joint for interactive object dragging
* ``world.add_filter_joint(body_a, body_b)`` - Stop two specific bodies colliding, and constrain nothing else
* ``world.add_mover_joint(body_a, body_b, ...)`` - Drive a character body at a commanded velocity
* ``world.add_pogo_joint(body_a, body_b, ...)`` - Hold a character up on a spring

Spatial Queries
^^^^^^^^^^^^^^^

* ``world.query_aabb(aabb, filter=None, max_results=None)`` - Find shapes in a specified AABB
* ``world.query_circle(position, radius, filter=None, max_results=None)`` - Find shapes in a circular area
* ``world.query_shape(proxy, filter=None, max_results=None)`` - Find shapes overlapping any region a ``ShapeProxy`` describes
* ``world.cast_ray(origin, translation, filter=None, first_hit_only=False)`` - Find shapes along a ray path
* ``world.cast_shape(proxy, translation, filter=None, first_hit_only=False)`` - Sweep a ``ShapeProxy`` and find what it runs into
* ``world.cast_mover(point1, point2, radius, translation, filter=None)`` - Sweep a character capsule; returns the fraction travelled
* ``world.collide_mover(point1, point2, radius, filter=None)`` - The surfaces a character capsule is up against, as collision planes

Events
^^^^^^

Each describes the step that just finished; the next step replaces it.

* ``world.get_contact_events()`` - Contacts that began, ended or hit (``ContactEvents``)
* ``world.get_sensor_events()`` - Sensor overlaps that began or ended (``SensorEvents``)
* ``world.get_body_events()`` - Bodies that moved (list of ``BodyMoveEvent``)
* ``world.get_joint_events()`` - Joints past their force or torque threshold (list of ``JointEvent``)

Callbacks
^^^^^^^^^

Each is a property: assign a function to set it, None to remove it.

* ``world.custom_filter`` - ``fn(shape_a, shape_b)``; return False to stop two shapes colliding
* ``world.pre_solve`` - ``fn(shape_a, shape_b, manifold)``, run on a contact just before it is solved
* ``world.pre_continuous`` - ``fn(shape_a, shape_b, point, normal)``; return False to let a fast body through
* ``world.friction_mixer`` - ``fn(friction_a, material_a, friction_b, material_b)`` returning the contact friction
* ``world.restitution_mixer`` - ``fn(restitution_a, material_a, restitution_b, material_b)`` returning the contact restitution

Simulation Parameters
^^^^^^^^^^^^^^^^^^^^^

* ``world.gravity`` - Get/set gravitational acceleration vector (m/s²)
* ``world.enable_sleeping`` - Toggle body sleeping for inactive objects
* ``world.enable_continuous`` - Toggle continuous collision detection
* ``world.contact_hertz`` - Get/set contact stiffness (Hz, default 30)
* ``world.contact_damping_ratio`` - Get/set contact bounciness (non-dimensional, default 10)
* ``world.contact_push_speed`` - Get/set the cap on overlap resolution speed (m/s, default 3)
* ``world.contact_recycle_distance`` - Get/set how far a contact may move and still be reused (m)
* ``world.restitution_threshold`` - Get/set minimum speed for restitution effects
* ``world.restitution_iterations`` - Get/set iterations of the restitution solver
* ``world.enable_restitution_propagation`` - Toggle passing a bounce fully through touching contacts
* ``world.enable_warm_starting`` - Toggle starting the solver from last step's impulses
* ``world.hit_event_threshold`` - Get/set minimum approach speed for hit events
* ``world.max_linear_speed`` - Get/set the speed cap applied to every body (m/s)

Threads
^^^^^^^

* ``world.threads`` - How many threads the world was created to step on (read-only)
* ``world.worker_count`` - Get/set how many pieces a step's work is split into

Diagnostics
^^^^^^^^^^^

* ``world.profile`` - Milliseconds spent in each phase of the last step (``Profile``)
* ``world.counters`` - Bodies, shapes, contacts and bytes as of the last step (``Counters``)
* ``world.max_capacity`` - The most the world has needed so far (``Capacity``, read-only);
  pass it to ``World(capacity=...)`` to help a new world for the same scene avoid allocating as it fills
* ``world.state_hash`` - A deterministic hash of the simulation state, for catching a desync
* ``world.dump_memory_stats()`` - Write Box2D's memory breakdown to ``box2d_memory.txt``
* ``world.rebuild_static_tree()`` - Rebuild the static broad-phase tree (Box2D marks it for testing)
* ``world.enable_sse2_fallback(value)`` - Use the SSE2 contact solver even with AVX2 (testing only)

Examples
^^^^^^^^

Creating a world with bodies:

.. code-block:: python

    from box2d import World

    # Create world with gravity pointing down
    world = World(gravity=(0, -9.8))

    # Create a ground body
    ground = world.new_body().static().position(0, -10).box(50, 1).build()
    
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
        lower_limit=-0.5,
        upper_limit=0.5
    )

Spatial queries:

.. code-block:: python

    # Find objects in an area
    overlapping_shapes = world.query_circle(position=(10, 5), radius=3)
    
    # Cast a ray and find intersections
    ray_hits = world.cast_ray(origin=(0, 0), translation=(10, 10))
    for hit in ray_hits:
        print(f"Hit at {hit.point}, normal: {hit.normal}")

RayCastResult
-------------

Contains information about a ray's intersection with a shape.

Properties
^^^^^^^^^^

* ``shape`` - The shape hit by the ray
* ``point`` - The hit point in world coordinates
* ``normal`` - Surface normal at hit point
* ``fraction`` - Fraction of ray length to hit point (0.0 to 1.0)

SensorEvent
-----------

Event generated when a sensor shape begins or ends overlap with another shape.

Properties
^^^^^^^^^^

* ``sensor`` - The sensor shape that triggered the event, or None if destroyed
* ``visitor`` - The shape that entered or left the sensor, or None if destroyed
* ``begin`` - True for beginning overlap, False for ending overlap

SensorEvents
------------

Collection of sensor events from a simulation step.

Properties
^^^^^^^^^^

* ``begin`` - List of sensor events for new overlaps
* ``end`` - List of sensor events for ended overlaps

Utility Functions
-----------------

* ``make_overlap_callback(results, max_results=None, *, world, errors=None)`` - Create callback for overlap queries in ``world``
* ``make_ray_cast_callback(results, *, world, errors=None)`` - Create callback for ray casting in ``world``