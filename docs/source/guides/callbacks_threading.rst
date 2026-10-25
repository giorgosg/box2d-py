Callbacks and threads
=====================

Most of what happens in a step is best read afterwards, from
:doc:`events`. A few decisions have to be made while the step is running:
whether two shapes may collide at all, whether a contact should hold this
step, how two surfaces' friction combines. For those the world takes
callbacks, which Box2D calls in the middle of the step, possibly on several
threads at once. This page covers the callbacks, what they may and may not do,
and stepping a world on more than one thread.

Setting a callback
------------------

Each callback is a property of the world: assign a function to set it, and
None to remove it. Box2D calls the first three only for shapes that ask for
them, so they cost nothing for the shapes that do not.

======================================================  ==================================================  ======================================
Callback                                                Called as                                           For shapes made with
======================================================  ==================================================  ======================================
:attr:`~box2d.world.World.custom_filter`                ``fn(shape_a, shape_b)``, returning a bool          ``enable_custom_filtering``, on either
:attr:`~box2d.world.World.pre_solve`                    ``fn(shape_a, shape_b, manifold)``                  ``enable_pre_solve_events``
:attr:`~box2d.world.World.pre_continuous`               ``fn(shape_a, shape_b, point, normal)``, a bool     ``enable_pre_solve_events``
:attr:`~box2d.world.World.friction_mixer`               ``fn(friction_a, material_a, friction_b,            every shape
                                                        material_b)``, returning a float
:attr:`~box2d.world.World.restitution_mixer`            ``fn(restitution_a, material_a, restitution_b,      every shape
                                                        material_b)``, returning a float
======================================================  ==================================================  ======================================

A callback that raises cannot pass the exception up through Box2D, so it is
printed, and the step carries on as if the callback were not there: the
collision allowed, the contact left as it was, the default mixing.

Custom filtering
----------------

:attr:`~box2d.world.World.custom_filter` decides, for a pair of shapes, what
categories and masks cannot: return False and the two do not collide. It is
consulted only when at least one of the two shapes has
``enable_custom_filtering``. Box2D's broad phase asks it about a pair of
shapes with no contact yet whose bounding boxes overlap, at the step one of
them moves into the other's; it asks again only as one of them moves on, and
not at all while a contact it allowed lasts. Continuous collision may also
ask it, before stopping a fast body at a shape. And a sensor asks it about
each shape overlapping it, where returning False hides the shape from the
sensor. Here a ghost falls through the ground:

.. code-block:: python

    >>> from box2d import World
    >>> world = World()
    >>> ground = world.new_body().static().box(20, 1).build()
    >>> ghost = (
    ...     world.new_body().dynamic().position(0, 3).user_data("ghost")
    ...     .circle(0.5, enable_custom_filtering=True).build()
    ... )
    >>> def solid(shape_a, shape_b):
    ...     return "ghost" not in (shape_a.body.user_data, shape_b.body.user_data)
    >>> world.custom_filter = solid
    >>> for _ in range(60):
    ...     world.step(1 / 60, 4)
    >>> ghost.position.y < 0
    True

Pre-solve and one-way platforms
-------------------------------

:attr:`~box2d.world.World.pre_solve` is called on each contact of a shape with
``enable_pre_solve_events``, every step, after Box2D has worked out its
:class:`~box2d.dataclasses.Manifold` and before the solver uses it. The
callback may change the manifold, and box2d-py writes it back: emptying its
``points`` disables the contact for that step. Box2D calls it only for awake
dynamic bodies, never for sensors, and the manifold's impulses are not reliable
at that point.

That is how a one-way platform is made: a contact with the platform holds only
when the other body is above it. The normal points from ``shape_a`` to
``shape_b``, so which way is up depends on which of the two is the platform.

A body fast enough to pass through the platform in one step needs
:attr:`~box2d.world.World.pre_continuous` as well. Continuous collision stops
such a body at the first surface it would pass through, before any contact
exists for pre-solve to see; ``pre_continuous`` is called then, and returning
False lets the body carry on through. Both are asked for by the same flag.

A ball thrown up from below rises through the platform, falls back onto it,
and stays there:

.. code-block:: python

    >>> platform = world.new_body().static().position(0, 3).box(4, 0.2).build()
    >>> ball = (
    ...     world.new_body().dynamic().position(0, 1).linear_velocity(0, 10)
    ...     .circle(0.25, enable_pre_solve_events=True).build()
    ... )
    >>> def from_above(shape_a, shape_b, normal):
    ...     if shape_a.body is platform:
    ...         return normal.y > 0
    ...     if shape_b.body is platform:
    ...         return normal.y < 0
    ...     return True
    >>> def one_way(shape_a, shape_b, manifold):
    ...     if not from_above(shape_a, shape_b, manifold.normal):
    ...         manifold.points.clear()
    >>> def let_through(shape_a, shape_b, point, normal):
    ...     return from_above(shape_a, shape_b, normal)
    >>> world.pre_solve = one_way
    >>> world.pre_continuous = let_through
    >>> heights = []
    >>> for _ in range(120):
    ...     world.step(1 / 60, 4)
    ...     heights.append(ball.position.y)
    >>> round(max(heights), 1), round(ball.position.y, 2)  # the top face is at y = 3.1
    (6.0, 3.35)

Mixing friction and restitution
-------------------------------

A contact's friction and restitution come from its two shapes'. By default
Box2D takes the geometric mean of the frictions, ``sqrt(friction_a *
friction_b)``, and the larger of the restitutions.
:attr:`~box2d.world.World.friction_mixer` and
:attr:`~box2d.world.World.restitution_mixer` replace those rules, given each
shape's value and its material: the integer it was made with as
``material=``, 0 by default, or the id of the
:class:`~box2d.material.SurfaceMaterial` given there. A material is what makes
a rule like "nothing grips ice" possible:

.. code-block:: python

    >>> import math
    >>> ICE = 1
    >>> def friction(friction_a, material_a, friction_b, material_b):
    ...     if ICE in (material_a, material_b):
    ...         return 0.0
    ...     return math.sqrt(friction_a * friction_b)
    >>> world.destroy()
    >>> world = World()
    >>> ground = world.new_body().static().box(20, 1).build()
    >>> crate = world.new_body().dynamic().position(-5, 1).linear_velocity(3, 0).box(1, 1).build()
    >>> puck = (
    ...     world.new_body().dynamic().position(0, 1).linear_velocity(3, 0)
    ...     .box(1, 1, material=ICE).build()
    ... )
    >>> world.friction_mixer = friction
    >>> for _ in range(60):
    ...     world.step(1 / 60, 4)
    >>> round(crate.linear_velocity.x, 2), round(puck.linear_velocity.x, 2)
    (0.0, 3.0)

Box2D calls the mixers from its worker threads with no other context, and asks
that they touch neither Box2D nor the application's state: they should
compute their answer from their four arguments and nothing else.

What a callback may do
----------------------

A callback runs while Box2D is in the middle of the step, with the world
locked, and Box2D's own advice is not to change the world from one. So a
callback should look, decide and return, and leave every change to after
:meth:`~box2d.world.World.step` returns, as :doc:`lifetime` describes.

box2d-py enforces the clearest cases: creating or destroying anything, or
stepping the world, raises :class:`RuntimeError` inside a callback. The rest it
does not stop, and Box2D's answer varies. Some setters are ignored while the
world is locked, others take effect part way through the solve, and every
query answers as if the world were empty: overlaps and casts find nothing, and
``cast_mover`` reports a clear path, 1.0:

.. code-block:: python

    >>> box = (
    ...     world.new_body().dynamic().position(5, 0.95)
    ...     .box(1, 1, enable_custom_filtering=True).build()
    ... )
    >>> seen = {}
    >>> def meddle(shape_a, shape_b):
    ...     crate.gravity_scale = 0.0
    ...     seen["gravity_scale"] = crate.gravity_scale
    ...     seen["hits"] = world.cast_ray((-5, 10), (0, -20))
    ...     return True
    >>> world.custom_filter = meddle
    >>> world.step(1 / 60, 4)
    >>> seen
    {'gravity_scale': 1.0, 'hits': []}
    >>> world.custom_filter = None

Threads
-------

A world steps on one thread unless it is made with more:
``World(threads=4)`` gives it a pool of its own, which counts the thread that
calls :meth:`~box2d.world.World.step` as one of the four and is stopped when
the world is destroyed. Worlds do not share threads. Box2D does best on
performance cores that share one L3 cache, and notes that efficiency cores and
hyper-threading add little and can even slow it down.

:data:`~box2d.world.HAS_THREADS` says whether this build can use threads at
all. It is False under WebAssembly, where Box2D is built without them, and
asking for more than one thread there raises :class:`RuntimeError`. So a
program meant to run everywhere asks conditionally:

.. code-block:: python

    from box2d import HAS_THREADS

    threads = 4 if HAS_THREADS else 1

:attr:`~box2d.world.World.threads` is fixed for the world's life.
:attr:`~box2d.world.World.worker_count`, the number of pieces Box2D splits a
step's work into, starts equal to it and can be changed, but the pool keeps
the size it was made with.

Callbacks on worker threads
---------------------------

With more than one thread, Box2D calls the callbacks from whichever of its
threads is doing the work, the calling thread among them, and Box2D's header
asks that each be thread-safe. In Python each call takes the GIL, so no two
run at the same moment. They do run in an order that changes from one run to
the next, though, so a callback that records what it sees records it in a
different order each time, and one whose answer depends on what earlier calls
saw is not deterministic. Taking the GIL also serialises the callbacks, so a
step that calls many of them gains less from extra threads.

Determinism
-----------

Box2D is designed to be deterministic: given the same world, built in the same
order, and the same steps, it produces the same result whatever the number of
threads, and, Box2D says, across platforms. :attr:`~box2d.world.World.state_hash`
is a hash of the simulation's state, so two worlds that are meant to agree,
such as two peers in a networked game, can check that they do. Here the same
pile settles identically on one thread and on four:

.. code-block:: python

    >>> def pile(threads):
    ...     world = World(threads=threads)
    ...     world.new_body().static().box(40, 1).build()
    ...     for i in range(6):
    ...         for j in range(6):
    ...             world.new_body().dynamic().position(i * 1.01 - 3, j * 1.01 + 1).box(1, 1).build()
    ...     for _ in range(60):
    ...         world.step(1 / 60, 4)
    ...     state_hash = world.state_hash
    ...     world.destroy()
    ...     return state_hash
    >>> pile(1) == pile(threads)
    True

Box2D's determinism covers what Box2D computes. A callback whose answers
depend on the order it is called in, or on anything outside its arguments,
can still make two runs differ.
