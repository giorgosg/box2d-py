Body Module at a Glance
=======================

This page provides a structured overview of the Box2D Body class and the
builder that makes one. A body is a rigid frame with a position, a rotation
and a velocity, which carries the shapes that give it mass and something to
collide with:

- **Made by the world**: ``world.new_body()`` starts a ``BodyBuilder``, and
  ``world.add_body()`` makes a body in one call; a ``Body`` is never
  constructed directly. :doc:`../guides/concepts` sets out the two ways
- **Three types**: static bodies do not move, kinematic bodies move at the
  velocity they are given, and dynamic bodies are fully simulated
- **Properties, not getters**: position, velocity and the rest are read and
  assigned as attributes. Assigning a name the body does not have raises,
  rather than quietly setting nothing; ``user_data`` is there for your own
- **Owned by the world**: a body lives until it or its world is destroyed,
  whether or not the caller kept it, as :doc:`../guides/lifetime` explains

Body
----

A rigid body in a world. Every method and property raises ``DestroyedError``
once the body has been destroyed.

Lifetime and Identity
^^^^^^^^^^^^^^^^^^^^^

* ``body.destroy()`` - Destroy the body, with its shapes and every joint attached to it
* ``body.is_valid`` - Whether the body is still live, i.e. has not been destroyed
* ``body.world`` - The world the body belongs to
* ``body.user_data`` - Any Python object to keep with the body
* ``body.name`` - Get/set a name, which debug draw can show, or None. Box2D
  keeps its first 10 bytes of UTF-8; a longer name is cut at the last whole
  character that fits, with a warning when assigned
* ``body.get_next_body()`` - The body after this one in ``world.bodies``, or None

Type
^^^^

* ``body.type`` - Get/set the type: reads ``'static'``, ``'kinematic'`` or
  ``'dynamic'``, and takes a name or a ``BodyType``. Changing it rebuilds the
  body's contacts
* ``Body.types`` - The type names, mapped to Box2D's constants
* ``Body.resolve_type(body_type)`` - Box2D's constant for a type name or ``BodyType``
* ``body.enabled`` - Get/set whether the body takes part in the simulation at all

Position and Velocity
^^^^^^^^^^^^^^^^^^^^^

* ``body.position`` - Get/set the world position of the body origin; setting it teleports
* ``body.rotation`` - Get/set the rotation in radians, read back between -pi and pi
* ``body.transform`` - The position and rotation together, as a ``Transform`` (read-only)
* ``body.linear_velocity`` - Get/set the velocity of the centre of mass (m/s)
* ``body.angular_velocity`` - Get/set the angular velocity (rad/s)
* ``body.set_target_transform(position, rotation, dt, wake=True)`` - Set the
  velocities that bring a kinematic body to a pose in ``dt``; moving
  platforms use this rather than teleporting
* ``body.linear_damping`` - Get/set how quickly linear velocity dies away
* ``body.angular_damping`` - Get/set how quickly angular velocity dies away
* ``body.gravity_scale`` - Get/set how much of the world's gravity the body feels
* ``body.lock_x``, ``body.lock_y`` - Get/set whether translation along the world x or y axis is prevented
* ``body.lock_rotation`` - Get/set whether rotation is prevented

Forces and Impulses
^^^^^^^^^^^^^^^^^^^

Each takes world coordinates and wakes the body unless ``wake=False``.

* ``body.apply_force(force, point=None, wake=True)`` - Apply a force (N) at a
  world point, or at the centre of mass when ``point`` is None
* ``body.apply_torque(torque, wake=True)`` - Apply a torque (N·m)
* ``body.apply_linear_impulse(impulse, point=None, wake=True)`` - Change the
  velocity at once (N·s), at a world point or the centre of mass
* ``body.apply_angular_impulse(impulse, wake=True)`` - Change the angular velocity at once (kg·m²/s)
* ``body.clear_forces()`` - Discard forces and torques applied since the last step

Mass
^^^^

* ``body.mass`` - The mass in kilograms, from the shapes' areas and densities (read-only)
* ``body.rotational_inertia`` - The rotational inertia about the centre of mass (kg·m², read-only)
* ``body.local_center`` - The centre of mass in body coordinates
* ``body.world_center`` - The centre of mass in world coordinates
* ``body.mass_data`` - Get/set mass, centre and rotational inertia together,
  as a ``MassData``; setting it overrides what the shapes give
* ``body.update_mass_from_shapes()`` - Recompute the mass from the shapes, undoing a ``mass_data`` override

Shapes
^^^^^^

Each ``add_*`` method attaches one shape and returns it. The keywords after
the geometry are ``ShapeDef`` fields -- ``density``, ``is_sensor``,
``material`` and the rest -- and the fields of its ``SurfaceMaterial``, such
as ``friction``, or, for a chain, ``ChainDef`` options; see
:doc:`shape_glance`.

* ``body.add_box(width, height, radius=0.0, offset=(0, 0), angle=0.0, **shapedef_args)`` - Attach a ``Box``, rounded by ``radius``
* ``body.add_circle(radius, center=(0, 0), **shapedef_args)`` - Attach a ``Circle``
* ``body.add_capsule(point1, point2, radius, **shapedef_args)`` - Attach a ``Capsule`` between two local points
* ``body.add_polygon(vertices, radius=0.0, **shapedef_args)`` - Attach a ``Polygon``, the convex hull of 3 to 8 points
* ``body.add_segment(point1, point2, **shapedef_args)`` - Attach a ``Segment``, a line with no thickness
* ``body.add_chain(vertices, loop=False, **chaindef_args)`` - Attach a ``Chain`` of one-sided segments, for terrain
* ``body.remove_shape(shape)`` - Destroy one of the body's shapes, the same as ``shape.destroy()``
* ``body.shapes`` - The shapes attached, as a list; chain segments are listed by their chain instead
* ``body.chains`` - The chains attached, as a list
* ``body.bounds`` - The world ``AABB`` around all the body's shapes

Converting Coordinates
^^^^^^^^^^^^^^^^^^^^^^

* ``body.get_world_point(local_point)`` - A point in body coordinates, in world coordinates
* ``body.get_local_point(world_point)`` - A point in world coordinates, in body coordinates
* ``body.get_world_vector(local_vector)`` - A direction in body coordinates, rotated into the world
* ``body.get_local_vector(world_vector)`` - A direction in world coordinates, rotated into the body
* ``body.get_world_point_velocity(world_point)`` - The velocity of a world point moving with the body
* ``body.get_local_point_velocity(local_point)`` - The velocity of a body point, in world coordinates

Sleeping
^^^^^^^^

* ``body.awake`` - Get/set whether the body is awake; a sleeping body costs nothing to step
* ``body.enable_sleeping`` - Get/set whether the body may fall asleep
* ``body.sleep_threshold`` - Get/set the speed below which it may fall asleep (m/s, default 0.05)
* ``body.wake_touching()`` - Wake every body touching this one, after moving it by hand

Contacts and Joints
^^^^^^^^^^^^^^^^^^^

* ``body.contact_data`` - The body's touching contacts, as a list of ``ContactData``
* ``body.contact_capacity`` - The most contacts ``contact_data`` can hold (read-only)
* ``body.enable_contact_events(enable=True)`` - Turn begin and end touch
  events on or off for every shape on the body (:doc:`../guides/events`)
* ``body.enable_hit_events(enable=True)`` - Turn hit events on or off for every shape on the body
* ``body.enable_contact_recycling`` - Get/set whether the body's contacts may
  be reused between steps; Box2D suggests turning it off for characters
* ``body.joints`` - The joints attached, as a list
* ``body.joint_count`` - How many joints are attached (read-only)

Continuous Collision
^^^^^^^^^^^^^^^^^^^^

Box2D sweeps a fast body against static shapes so it cannot pass through them.

* ``body.is_bullet`` - Get/set whether the body is swept against kinematic
  and dynamic bodies too, but not other bullets, for something small and fast
* ``body.safety_factor`` - Get/set how far the body may move in a step, as a
  fraction of its ``min_extent``, before it is swept (default 0.5)
* ``body.min_extent`` - The least distance from the centre of mass to the edge of the shapes
* ``body.max_extent`` - The greatest distance from the centre of mass to the edge of the shapes
* ``body.max_extent_from_origin`` - The greatest distance from the body origin to the edge of the shapes

BodyBuilder
-----------

Builds a body in one expression. ``world.new_body()`` starts one; each method
sets one thing and returns the builder, and ``build()`` makes the body by
calling ``world.add_body()`` with the settings, then the body's ``add_*``
method for each shape, with the same arguments. A builder can be kept and
built from again: each ``build()`` makes a new body.

Type
^^^^

* ``builder.dynamic()`` - Make a dynamic body: simulated, moved by gravity, forces and collisions
* ``builder.static()`` - Make a static body, which never moves; the default
* ``builder.kinematic()`` - Make a kinematic body, which moves only at the velocity it is given

Placement and Motion
^^^^^^^^^^^^^^^^^^^^

* ``builder.position(x, y=None)`` - The starting position, as a vector-like or two numbers
* ``builder.rotation(rotation)`` - The starting rotation, in radians
* ``builder.linear_velocity(x, y=None)`` - The starting velocity, as a vector-like or two numbers
* ``builder.angular_velocity(radians)`` - The starting angular velocity (rad/s)
* ``builder.linear_damping(damping)`` - How quickly linear velocity dies away
* ``builder.angular_damping(damping)`` - How quickly angular velocity dies away
* ``builder.gravity_scale(scale)`` - How much of the world's gravity the body feels
* ``builder.lock_x(lock=True)``, ``builder.lock_y(lock=True)`` - Prevent translation along the world x or y axis
* ``builder.lock_rotation(lock=True)`` - Prevent rotation

Simulation
^^^^^^^^^^

* ``builder.awake(awake=True)`` - False to build the body asleep, at rest until something touches it
* ``builder.enabled(enabled=True)`` - False to build the body disabled, out of the simulation
* ``builder.enable_sleep(enable)`` - Whether the body may fall asleep
* ``builder.sleep_threshold(threshold)`` - The speed below which it may fall asleep (m/s)
* ``builder.bullet(bullet=True)`` - Sweep the body against kinematic and dynamic bodies too, but not other bullets
* ``builder.safety_factor(factor)`` - The continuous collision safety factor; see ``body.safety_factor``
* ``builder.allow_fast_rotation(allow=True)`` - Lift Box2D's cap on rotation speed, for wheels and other round things
* ``builder.enable_contact_recycling(enable=True)`` - Whether the body's contacts may be reused between steps

Identity
^^^^^^^^

* ``builder.name(name)`` - A name, which debug draw can show; Box2D keeps its first 10 bytes of UTF-8
* ``builder.user_data(data)`` - Any Python object to keep with the body

Shapes
^^^^^^

Each takes the same arguments as the body's matching ``add_*`` method.

* ``builder.box(width, height, radius=0.0, offset=(0, 0), angle=0.0, **shapedef_args)`` - Add a box
* ``builder.circle(radius, center=(0, 0), **shapedef_args)`` - Add a circle
* ``builder.capsule(point1, point2, radius, **shapedef_args)`` - Add a capsule
* ``builder.polygon(vertices, radius=0.0, **shapedef_args)`` - Add a convex polygon
* ``builder.segment(point1, point2, **shapedef_args)`` - Add a segment
* ``builder.chain(vertices, loop=False, **chaindef_args)`` - Add a chain

Building
^^^^^^^^

* ``builder.build()`` - Make the body, with its shapes, and return it
* ``builder.world`` - The world the builder makes bodies in
* ``BodyBuilder.extend(func)`` - Decorator adding ``func`` to every builder as a
  method, which should return the builder so calls still chain

Examples
--------

Making bodies both ways, then pushing one:

.. code-block:: python

    from box2d import World

    world = World(gravity=(0, -10))
    ground = world.new_body().static().box(40, 1).build()

    # A crate from the builder, and a ball from add_body and add_circle
    crate = (
        world.new_body().dynamic().position(-2, 4)
        .box(1, 1, density=2, friction=0.4)
        .build()
    )
    ball = world.add_body(body_type="dynamic", position=(2, 6))
    ball.add_circle(0.5, restitution=0.6)

    # Shove the crate sideways at its top edge, so it tips as it slides
    crate.apply_linear_impulse((3, 0), point=crate.get_world_point((0, 0.5)))
    for _ in range(120):
        world.step(1 / 60, 4)
    print(f"crate at {crate.position}, turned {crate.rotation:.2f} rad")

A body's mass comes from its shapes, and its coordinate conversions follow it
as it moves:

.. code-block:: python

    >>> wheel = world.new_body().dynamic().position(10, 5).circle(0.5).build()
    >>> round(wheel.mass, 3)
    0.785
    >>> wheel.get_world_point((0.5, 0))
    Vec2(10.5, 5.0)
    >>> spoke = wheel.add_box(0.8, 0.1, density=0)
    >>> len(wheel.shapes), round(wheel.mass, 3)
    (2, 0.785)

A kinematic platform driven along a path with ``set_target_transform``:

.. code-block:: python

    platform = world.new_body().kinematic().position(-5, 3).box(3, 0.2).build()
    for step in range(60):
        x = -5 + (step + 1) * 0.1
        platform.set_target_transform((x, 3), 0.0, 1 / 60)
        world.step(1 / 60, 4)
    print(platform.position)  # about (1, 3)
