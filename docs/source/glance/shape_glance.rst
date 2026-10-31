Shape Module at a Glance
========================

This page provides a structured overview of the Box2D shape classes, the
definitions that describe them, and the surface materials they carry. A shape
gives a body its extent, its mass and something to collide with:

- **Attached to a body**: shapes are made by a body's ``add_*`` methods or
  the builder's shape methods, and move with it. Each kind's ``create``
  class method is what those call
- **Geometry plus a ShapeDef**: a shape is made from its geometry -- a
  radius, two points, a list of vertices -- and the ``ShapeDef`` fields, given
  as keywords: ``density``, ``friction``, ``is_sensor`` and the rest
- **Chains are apart**: a ``Chain`` is not a ``Shape``. It is a run of
  one-sided ``ChainSegment`` shapes for terrain, and it takes ``ChainDef``
  options rather than ``ShapeDef`` fields
- **Definitions are plain data**: ``CircleDef``, ``PolygonDef`` and the rest
  are dataclasses, which a shape's ``geometry`` reads and writes

:doc:`../guides/concepts` introduces shapes and their mass,
:doc:`../guides/queries` collision filters and the queries that find shapes,
and :doc:`../guides/events` the contact, hit and sensor events they report.

Shape
-----

The base of every shape but a chain: ``Circle``, ``Capsule``, ``Segment``,
``Polygon``, ``Box`` and ``ChainSegment``. Every method and property raises
``DestroyedError`` once the shape has been destroyed.

Lifetime and Identity
^^^^^^^^^^^^^^^^^^^^^

* ``shape.destroy(update_body_mass=True)`` - Remove the shape from its body;
  pass False when removing several, then call ``body.update_mass_from_shapes()``
* ``shape.is_valid`` - Whether the shape is still live, i.e. has not been destroyed
* ``shape.body`` - The body the shape is attached to
* ``shape.world`` - The world the shape belongs to
* ``shape.user_data`` - Any Python object to keep with the shape
* ``shape.shape_type`` - Box2D's constant for the kind of shape (read-only)
* ``shape.parent_chain`` - The chain this shape is a segment of, or None

Surface
^^^^^^^

* ``shape.friction`` - Get/set the friction coefficient, usually 0 to 1 (default 0.6)
* ``shape.restitution`` - Get/set the bounciness, usually 0 to 1 (default 0)
* ``shape.rolling_resistance`` - Get/set the rolling resistance, usually 0 to 1
* ``shape.tangent_speed`` - Get/set the speed the surface moves along itself, for conveyor belts (m/s)
* ``shape.user_material`` - Get/set the material id passed to the world's mixers; takes an id or a ``SurfaceMaterial``
* ``shape.surface_material`` - Get/set all of the above at once, as a ``SurfaceMaterial``

Mass
^^^^

* ``shape.density`` - Get/set the density (kg/m², default 1); setting it updates the body's mass
* ``shape.mass_data`` - The shape's own mass, centre and rotational inertia, as a ``MassData``

Collision
^^^^^^^^^

* ``shape.filter`` - Get/set the ``CollisionFilter`` deciding what the shape collides with
* ``shape.is_sensor`` - Whether the shape is a sensor, detecting overlap without colliding (read-only)

Events
^^^^^^

* ``shape.enable_contact_events`` - Get/set whether the shape reports touches beginning and ending
* ``shape.enable_hit_events`` - Get/set whether it reports hits above the world's ``hit_event_threshold``
* ``shape.enable_sensor_events`` - Get/set whether it takes part in sensor events (default False)
* ``shape.enable_pre_solve_events`` - Get/set whether the world's ``pre_solve`` callback runs for it
* ``shape.contact_data`` - The shape's touching contacts, as a list of ``ContactData``
* ``shape.contact_capacity`` - The most contacts ``contact_data`` can hold (read-only)
* ``shape.sensor_overlaps`` - For a sensor, the shapes overlapping it now; empty for any other shape
* ``shape.sensor_capacity`` - The most shapes ``sensor_overlaps`` can hold (read-only)

Geometry Queries
^^^^^^^^^^^^^^^^

* ``shape.bounds`` - The shape's ``AABB`` in world coordinates
* ``shape.test_point(point)`` - Whether a world point is inside the shape
* ``shape.get_closest_point(target)`` - The point on the shape closest to a world point
* ``shape.cast_ray(origin, translation)`` - Cast a ray at this shape alone; a ``CastResult``, or None for a miss

Forces
^^^^^^

* ``shape.apply_wind(wind, drag=1.0, lift=0.0, wake=True)`` - Push the shape
  with a wind (m/s), using the density of air; call it each step it blows

Circle
------

A circle, given by its radius and centre.

* ``Circle.create(body, radius, center=(0, 0), **shapedef_kwargs)`` - Make and attach one; ``body.add_circle()`` calls this
* ``circle.radius`` - Get/set the radius
* ``circle.center`` - Get/set the centre, in body coordinates
* ``circle.geometry`` - Get/set the geometry as a ``CircleDef``

Setting ``geometry``, or any property that changes it, here and on the kinds
below, leaves the body's mass as it was: call
``body.update_mass_from_shapes()`` afterwards for the mass to follow.

Capsule
-------

A segment rounded by a radius: two half-circles joined by straight sides.

* ``Capsule.create(body, point1, point2, radius, **shapedef_kwargs)`` - Make and attach one; ``body.add_capsule()`` calls this
* ``capsule.point1``, ``capsule.point2`` - Get/set the centres of the rounded ends, in body coordinates
* ``capsule.radius`` - Get/set the radius
* ``capsule.geometry`` - Get/set the geometry as a ``CapsuleDef``

Segment
-------

A line between two points, with no thickness.

* ``Segment.create(body, point1, point2, **shapedef_kwargs)`` - Make and attach one; ``body.add_segment()`` calls this
* ``segment.point1``, ``segment.point2`` - Get/set the ends, in body coordinates
* ``segment.geometry`` - Get/set the geometry as a ``SegmentDef``

Polygon
-------

A convex polygon of 3 to 8 vertices, optionally with rounded corners. Box2D
builds it from the convex hull of the points it is given, so they may come in
any order.

* ``Polygon.create(body, vertices, radius=0.0, offset=(0, 0), angle=0.0, **shapedef_kwargs)`` - Make and attach one;
  ``body.add_polygon()`` calls this. ``angle`` is ``PolygonDef``'s ``rotation``
* ``polygon.vertices`` - Get/set the vertices, in body coordinates
* ``polygon.radius`` - Get/set the radius of the rounded corners
* ``polygon.geometry`` - Get/set the geometry as a ``PolygonDef``

Box
---

A rectangle. It is a ``Polygon`` in every other way, but is built directly
rather than from a hull, so it can be thinner than Box2D's smallest polygon
feature.

* ``Box.create(body, width, height, radius=0.0, offset=(0, 0), angle=0.0, **shapedef_kwargs)`` - Make and attach one;
  ``body.add_box()`` calls this. ``angle`` is ``BoxDef``'s ``rotation``

Chain
-----

A run of one-sided segments joined end to end, open or closed into a loop, for
static terrain. Bodies slide across the joins without catching on them.

* ``Chain.create(body, vertices, loop=False, ghost1=None, ghost2=None, filter=None, materials=None, friction=None, restitution=None, rolling_resistance=None, tangent_speed=None, custom_color=None, user_data=None, enable_sensor_events=None)`` -
  Make and attach one; ``body.add_chain()`` calls this. ``friction`` and the
  rest make one material for the whole chain, when ``materials`` is not given
* ``chain.segments`` - The chain's ``ChainSegment`` shapes, in order
* ``chain.get_surface_material(segment_index=0)`` - A copy of one segment's ``SurfaceMaterial``
* ``chain.set_surface_material(material, segment_index=None)`` - Change one segment's material, or every segment's
* ``chain.destroy()`` - Remove the chain, and every segment of it, from its body
* ``chain.is_valid`` - Whether the chain is still live, i.e. has not been destroyed
* ``chain.body`` - The body the chain is attached to
* ``chain.world`` - The world the chain belongs to
* ``chain.user_data`` - Any Python object to keep with the chain

ChainSegment
------------

One segment of a chain: a ``Shape``, which ray casts, queries and events
report like any other, whose ``parent_chain`` is its chain.

* ``segment.destroy(update_body_mass=True)`` - Always raises ``TypeError``:
  a segment cannot leave its chain, so destroy the chain instead

ShapeDef
--------

The settings every shape but a chain is made with. Each field is also a
keyword to ``body.add_box()``, ``Circle.create()`` and the other shape-making
calls, which make the ``ShapeDef`` from them.

Surface
^^^^^^^

* ``friction`` - The friction coefficient (default 0.6)
* ``restitution`` - The bounciness (default 0)
* ``rolling_resistance`` - The rolling resistance (default 0)
* ``tangent_speed`` - The conveyor speed along the surface (default 0)
* ``material`` - A user material id, or a ``SurfaceMaterial`` whose id is
  used; its friction and the rest are not (default 0)
* ``custom_color`` - A colour for debug draw, as a hex int or ``Color``; 0 for the default colours

Mass
^^^^

* ``density`` - The density, in kg/m² (default 1)
* ``update_body_mass`` - Whether adding the shape updates the body's mass (default True)

Collision
^^^^^^^^^

* ``filter`` - The ``CollisionFilter``, or None to collide with everything
* ``is_sensor`` - Make a sensor, which reports overlaps and never collides (default False)
* ``enable_custom_filtering`` - Ask the world's ``custom_filter`` about this shape's contacts (default False)
* ``invoke_contact_creation`` - On a static body, look for contacts with existing shapes at the next step (default True)

Events
^^^^^^

* ``enable_contact_events`` - Report touches beginning and ending (default False)
* ``enable_hit_events`` - Report hits (default False)
* ``enable_sensor_events`` - Take part in sensor events, which a sensor and a shape both have to (default False)
* ``enable_pre_solve_events`` - Run the world's ``pre_solve`` callback for this shape (default False)

Other
^^^^^

* ``user_data`` - Any Python object, kept as the shape's ``user_data``
* ``shape_def.b2ShapeDef`` - The Box2D structure, with Box2D's defaults for anything not set

CircleDef
---------

* ``CircleDef(radius, center=(0, 0))`` - A circle's geometry
* ``radius`` - The radius
* ``center`` - The centre, in body coordinates, as a ``Vec2``
* ``circle_def.b2Circle`` - The Box2D structure
* ``CircleDef.from_b2Circle(circle)`` - Read one back from Box2D's structure

CapsuleDef
----------

* ``CapsuleDef(vertex1, vertex2, radius)`` - A capsule's geometry
* ``vertex1``, ``vertex2`` - The centres of the rounded ends, in body coordinates
* ``radius`` - The radius
* ``capsule_def.b2Capsule`` - The Box2D structure
* ``CapsuleDef.from_b2Capsule(capsule)`` - Read one back from Box2D's structure

SegmentDef
----------

* ``SegmentDef(vertex1, vertex2)`` - A segment's geometry
* ``vertex1``, ``vertex2`` - The ends, in body coordinates
* ``segment_def.b2Segment`` - The Box2D structure
* ``SegmentDef.from_b2Segment(segment)`` - Read one back from Box2D's structure

PolygonDef
----------

* ``PolygonDef(vertices, radius=None, offset=None, rotation=None)`` - A polygon's geometry; None is no rounding, offset or rotation
* ``vertices`` - The points whose convex hull is the polygon, 3 to 8 of them
* ``radius`` - The radius of the rounded corners
* ``offset`` - Where the polygon sits, relative to the body origin
* ``rotation`` - The polygon's rotation relative to the body, in radians or as a ``Rot``
* ``polygon_def.is_valid`` - Whether Box2D can build a polygon from this; adding one that is not raises ``ValueError``
* ``polygon_def.b2Polygon`` - The Box2D structure, made from the hull
* ``PolygonDef.from_b2Polygon(polygon)`` - Read one back from Box2D's structure

BoxDef
------

Importable from ``box2d.shapedef``.

* ``BoxDef(width, height, radius=0.0, offset=(0, 0), rotation=None)`` - A box's geometry
* ``width``, ``height`` - The full width and height
* ``radius`` - The radius of the rounded corners
* ``offset`` - Where the box's centre sits, relative to the body origin
* ``rotation`` - The box's rotation relative to the body, in radians or as a ``Rot``
* ``box_def.b2Polygon`` - The Box2D structure, a ``b2Polygon``

ChainDef
--------

* ``ChainDef(vertices, is_loop=False, ghost1=None, ghost2=None, materials=None, filter=None, user_data=None, enable_sensor_events=False)`` -
  A chain's points and options. An open chain needs 2 points, a loop 3
* ``vertices`` - The chain's points, in order; each is a real vertex
* ``is_loop`` - Whether the last point joins back to the first
* ``ghost1``, ``ghost2`` - Points beyond each end of an open chain, saying
  where the surface carries on; they default to carrying the end segments straight on
* ``materials`` - One ``SurfaceMaterial`` for the whole chain, or one per segment
* ``filter`` - The ``CollisionFilter`` for every segment
* ``user_data`` - Any Python object, kept as the chain's ``user_data``
* ``enable_sensor_events`` - Whether the segments take part in sensor events (default False)
* ``chain_def.segment_count`` - How many segments the chain will have
* ``chain_def.b2ChainDef`` - The Box2D structure

SurfaceMaterial
---------------

A surface's properties in one object, for a shape's ``surface_material``, a
chain's ``materials``, and the world's friction and restitution mixers
(:doc:`../guides/callbacks_threading`). A field left None takes Box2D's
default.

* ``SurfaceMaterial(user_material=<new id>, friction=None, restitution=None, rolling_resistance=None, tangent_speed=None, custom_color=None)`` -
  A material; each gets a new ``user_material`` id unless given one
* ``user_material`` - The id the mixers are passed, to tell materials apart
* ``friction`` - The friction coefficient
* ``restitution`` - The bounciness
* ``rolling_resistance`` - The rolling resistance
* ``tangent_speed`` - The conveyor speed along the surface
* ``custom_color`` - A colour for debug draw, as a hex int or ``Color``
* ``SurfaceMaterial.default()`` - A material with Box2D's default values, and a new id
* ``SurfaceMaterial.get_by_id(material_id)`` - The live material with this id, or None
* ``SurfaceMaterial.clear_registry()`` - Forget every material ``get_by_id`` knows
* ``material.b2SurfaceMaterial`` - The Box2D structure
* ``SurfaceMaterial.from_b2SurfaceMaterial(material)`` - Read one back from Box2D's structure, keeping its id

Examples
--------

Shapes of each kind on one body, with their settings:

.. code-block:: python

    from box2d import World

    world = World(gravity=(0, -10))
    ground = world.new_body().static().box(40, 1).build()

    body = world.new_body().dynamic().position(0, 5).build()
    hull = body.add_box(2, 0.5, density=2, friction=0.3)
    wheel = body.add_circle(0.4, center=(0.8, -0.4), restitution=0.2)
    nose = body.add_polygon([(1, 0.25), (1.6, 0), (1, -0.25)])
    mast = body.add_capsule((0, 0.25), (0, 1.5), 0.1, density=0.5)
    # A sensor has mass like any other shape, unless its density is zero
    sensor = body.add_circle(2, is_sensor=True, density=0)

    for _ in range(60):
        world.step(1 / 60, 4)
    print(len(body.shapes), "shapes, mass", round(body.mass, 2))

A shape's properties can be read and changed once it is made:

.. code-block:: python

    >>> round(wheel.radius, 2), wheel.center
    (0.4, Vec2(0.8, -0.4))
    >>> wheel.friction = 0.9
    >>> round(wheel.friction, 2)
    0.9
    >>> wheel.test_point(wheel.body.get_world_point((0.8, -0.4)))
    True
    >>> sensor.is_sensor, hull.is_sensor
    (True, False)

A chain for terrain, with an icy stretch in the middle:

.. code-block:: python

    from box2d import SurfaceMaterial

    hills = world.new_body().static().position(0, -4).build()
    chain = hills.add_chain([(-20, 0), (-10, 2), (0, 0), (10, 2), (20, 0)])
    ice = SurfaceMaterial(friction=0.02)
    chain.set_surface_material(ice, segment_index=2)
    print(len(chain.segments), "segments;", round(chain.get_surface_material(2).friction, 2))
