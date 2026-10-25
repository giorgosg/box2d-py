Queries
=======

Besides stepping, a world answers questions about where its shapes are: which
overlap a region, what a ray would hit, and where a moving shape would stop.
This page covers those queries, and the collision filters that decide both
which shapes collide with each other and which a query sees.

Every query takes and returns world coordinates, and works between steps:
during a step, which is when the world's callbacks run, Box2D answers every
query as if the world were empty, so an overlap query or a cast finds nothing
and :meth:`~box2d.world.World.cast_mover` reports a clear path, 1.0.

Overlap queries
---------------

:meth:`~box2d.world.World.query_circle` and
:meth:`~box2d.world.World.query_shape` return the shapes that overlap a
region. ``query_shape`` takes the region as a :class:`~box2d.query.ShapeProxy`,
which has a constructor for each kind: ``circle``, ``capsule``, ``segment``,
``point``, ``box`` and ``polygon``, the convex hull of up to eight points.

:meth:`~box2d.world.World.query_aabb` is the cheap one: it compares bounding
boxes only. Box2D keeps each shape's bounding box a little larger than the
shape, so it returns every shape that might overlap the box, including some
that do not. Here a small square sits off the edge of a ball, inside its
bounding box but clear of the ball itself:

.. code-block:: python

    >>> from box2d import AABB, ShapeProxy, World
    >>> world = World()
    >>> ball = world.new_body().dynamic().circle(0.5).build()
    >>> corner = AABB(lower=(0.4, 0.4), upper=(0.5, 0.5))
    >>> world.query_aabb(corner) == ball.shapes
    True
    >>> world.query_shape(ShapeProxy.box(0.1, 0.1, center=(0.45, 0.45)))
    []

So use ``query_aabb`` to narrow things down, and ``query_shape`` or
``query_circle`` when the answer has to be exact.

Each takes ``max_results``, and stops once it has found that many. Box2D keeps
static, kinematic and dynamic shapes in three separate trees and searches them
in that order, and each tree in an order of its own, which is not nearest
first. So a cap fills with static shapes before any others, and is for asking
whether there is anything, or capping the work, rather than for finding the
closest few. Here five static crates fill a cap of two, and the ball is left
out:

.. code-block:: python

    >>> crates = [world.new_body().position(x, 3).box(1, 1).build() for x in range(5)]
    >>> found = world.query_aabb(AABB(lower=(-10, -10), upper=(10, 10)), max_results=2)
    >>> [shape.body.type for shape in found]
    ['static', 'static']

Ray casts
---------

:meth:`~box2d.world.World.cast_ray` finds the shapes along a line segment. It
takes a start point and a translation -- the vector from the start to the end,
not the end itself -- and returns a
:class:`~box2d.world.RayCastResult` for each shape it crosses, nearest first.
Each has the ``shape``, the ``point`` where the ray enters it, the surface
``normal`` there, and the ``fraction`` of the translation travelled to reach
it:

.. code-block:: python

    >>> hits = world.cast_ray((-1, 3), (10, 0))
    >>> [hit.shape.body for hit in hits] == crates
    True
    >>> hits[0].point, hits[0].normal, round(hits[0].fraction, 2)
    (Vec2(-0.5, 3.0), Vec2(-1.0, 0.0), 0.05)

With ``first_hit_only=True`` it returns just the nearest hit, and Box2D does
less work to find it:

.. code-block:: python

    >>> [hit] = world.cast_ray((-1, 3), (10, 0), first_hit_only=True)
    >>> hit.shape.body is crates[0]
    True

The two differ over a ray that starts inside a shape. Without
``first_hit_only``, that shape is reported at fraction 0, with a zero normal,
as there is no surface there to take one from. With it, Box2D skips that shape,
and reports the nearest one the ray enters from outside:

.. code-block:: python

    >>> world.cast_ray((0, 3), (3, 0))[0].fraction
    0.0
    >>> world.cast_ray((0, 3), (3, 0), first_hit_only=True)[0].shape.body is crates[1]
    True

Shape casts
-----------

:meth:`~box2d.world.World.cast_shape` sweeps a :class:`~box2d.query.ShapeProxy`
along a translation and reports what it runs into, as a ray cast does for a
point. It answers the questions a ray cannot, such as whether a body of some
size fits through a gap, or where a box dropped from here would land. This
1 m box, dropped from 10 m, would fall 9 m before landing on the ground's top
face, at y = 0.5:

.. code-block:: python

    >>> world.destroy()
    >>> world = World()
    >>> ground = world.new_body().static().box(20, 1).build()
    >>> [hit] = world.cast_shape(ShapeProxy.box(1, 1, center=(5, 10)), (0, -20))
    >>> round(hit.fraction * 20, 1), round(hit.point.y, 2), hit.normal
    (9.0, 0.5, Vec2(0.0, 1.0))

The results are as for ``cast_ray``, nearest first, and ``first_hit_only``
keeps only the first. A shape the proxy overlaps at its starting position is
reported at fraction 0, with a zero normal.

Collision filters
-----------------

A shape's :class:`~box2d.collision_filter.CollisionFilter` decides what it
collides with. It has a ``category``, the bits for what the shape is, and a
``mask``, the bits for what it collides with. Two shapes collide only when each
one's category is in the other's mask. Both are 64-bit, and
:attr:`~box2d.collision_filter.CollisionFilter.ALL` is every bit set. A shape
made without a filter has category ``0x1`` and mask ``ALL``, so it collides
with every shape whose mask includes ``0x1``.

A filter can name its categories rather than give bits, through a
:class:`~box2d.collision_filter.CollisionCategoryRegistry`, which gives each
name the next free bit, lowest first. Without one, names go to a registry
shared by the whole program, which makes up a new category for any name it has
not seen, so a misspelt name quietly becomes a category of its own. A registry
of the program's own, made with the default ``auto_create=False``, accepts
only the names defined on it:

.. code-block:: python

    >>> from box2d import CollisionCategoryRegistry, CollisionFilter
    >>> categories = CollisionCategoryRegistry()
    >>> [categories.define(name) for name in ("scenery", "player", "debris")]
    [1, 2, 4]
    >>> CollisionFilter("debirs", registry=categories)
    Traceback (most recent call last):
      ...
    ValueError: Category 'debirs' is not defined.

Defined first, ``scenery`` has the default category, ``0x1``, so shapes made
without a filter are scenery. Debris that collides with the scenery and with
nothing else is given its own category and a mask of scenery alone:

.. code-block:: python

    >>> debris = CollisionFilter("debris", mask="scenery", registry=categories)
    >>> debris
    CollisionFilter(category=0x4, mask=0x1, group=0)
    >>> rubble = world.new_body().dynamic().position(0, 1).box(1, 1, filter=debris).build()

A filter is given as ``filter=`` wherever a shape is made, and can be changed
afterwards through the shape's ``filter`` property, which Box2D says costs
almost as much as making the shape again.

The ``group`` overrides the bits for shapes that share it: two shapes in the
same positive group always collide, and two in the same negative group never
do. Giving every part of a ragdoll the same negative group stops it colliding
with itself, while it still collides with everything else.

Filters in queries
------------------

Every query and cast takes a ``filter`` too, a
:class:`~box2d.collision_filter.CollisionFilter` that is matched against each
shape's in the same way, both ways round: the query sees a shape when the
shape's category is in the query's mask and the query's category is in the
shape's mask. The group plays no part.

The default, ``CollisionFilter()``, has category ``0x1`` and mask ``ALL``, so
it sees every shape whose mask includes ``0x1``. That is every shape made
without a filter, but not one whose mask leaves ``0x1`` out. Given a shape's
own filter, a query sees what that shape would collide with. A ray cast down
with the default filter finds the rubble and the ground beneath it, and one
with a player's filter finds only the ground, as debris does not collide with
the player:

.. code-block:: python

    >>> down = ((0, 5), (0, -10))
    >>> [hit.shape.body is rubble for hit in world.cast_ray(*down)]
    [True, False]
    >>> player = CollisionFilter("player", mask=["scenery", "player"], registry=categories)
    >>> [hit.shape.body is ground for hit in world.cast_ray(*down, filter=player)]
    [True]
