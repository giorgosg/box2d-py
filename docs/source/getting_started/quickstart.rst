Quickstart
==========

This page builds a small scene and works through what most programs do with
one: step it, read where things are, join two bodies, cast a ray, and hear
about collisions. Each block carries on from the ones before it, so they can
be pasted into a Python prompt in order.

A world
-------

A :class:`~box2d.world.World` holds everything that is simulated. Gravity is
an acceleration in metres per second squared, and points down the y axis:

.. code-block:: python

    from box2d import World

    world = World(gravity=(0, -10))

Ground and falling boxes
------------------------

A body has a position and a velocity; its shapes give it extent, mass and
something to collide with. :meth:`~box2d.world.World.new_body` starts a
builder that sets both, and ``build()`` creates the body in the world.

The ground is a static body, which never moves. A box is given its full width
and height, centred on the body's position, so this one is 40 m wide with its
top surface at y = 0.5:

.. code-block:: python

    ground = world.new_body().static().position(0, 0).box(40, 1).build()

Dynamic bodies move under gravity and collide. Three 1 m boxes, held 4 m up:

.. code-block:: python

    boxes = [
        world.new_body().dynamic().position(x, 4).box(1, 1).build()
        for x in (-3, 0, 3)
    ]

Stepping
--------

:meth:`~box2d.world.World.step` advances the world by a time step, in
seconds. Use the same step every time, typically 1/60 of a second, rather
than the time a frame happened to take: Box2D is tuned for a fixed step, and
a varying one makes the simulation jittery. The second argument is the
number of substeps, which trade speed for accuracy; 4 is the usual choice.

.. code-block:: python

    for _ in range(90):
        world.step(1 / 60, 4)

Reading positions
-----------------

A body's ``position`` is its origin in world coordinates, a
:class:`~box2d.math.Vec2`, and ``rotation`` is its angle in radians. After a
second and a half, the boxes have landed: each centre is half a metre above
the ground's top surface.

.. code-block:: python

    >>> [round(box.position.y, 2) for box in boxes]
    [1.0, 1.0, 1.0]
    >>> abs(boxes[0].rotation) < 0.01  # landed flat
    True

A body that has been still for a moment is put to sleep, and costs nothing to
step until something touches it:

.. code-block:: python

    >>> boxes[0].awake
    False

Units
-----

Box2D works in metres, kilograms and seconds, and in radians for angles.
Its tolerances are tuned for moving objects between about 0.1 and 10 metres;
much smaller or larger than that and stacks jitter and objects pass through
each other. Static bodies can be larger, as the 40 m ground is. So size a
scene in metres, not pixels: a 64-pixel sprite is better simulated as a
1 m body and scaled for drawing than simulated as a 64 m one.

Density is in kilograms per square metre, and defaults to 1. Angles given
in degrees convert with :func:`math.radians`; this ramp is tilted by 20
degrees:

.. code-block:: python

    import math

    ramp = (
        world.new_body()
        .static()
        .position(-10, 2)
        .rotation(math.radians(20))
        .box(6, 0.2)
        .build()
    )

Adding a shape later
--------------------

A body does not need its shapes at the start. ``add_box``, ``add_circle`` and
the other ``add_*`` methods attach one to a body that already exists, and its
mass follows the shapes it has:

.. code-block:: python

    >>> ball = world.new_body().dynamic().position(-3, 8).build()
    >>> ball.mass
    0.0
    >>> circle = ball.add_circle(radius=0.5, enable_contact_events=True)
    >>> round(ball.mass, 3)  # the circle's area, at a density of 1
    0.785

``enable_contact_events`` is for `Contact events`_, below.

A joint
-------

A joint constrains how two bodies move relative to each other. A revolute
joint pins them together at a point they both turn about; here it hangs a
small weight 2 m from a pivot on the ground body, as a pendulum. ``anchor``
is the pivot in world coordinates:

.. code-block:: python

    pivot = (6, 6)
    weight = world.new_body().dynamic().position(8, 6).circle(0.25).build()
    hinge = world.add_revolute_joint(ground, weight, anchor=pivot)

    for _ in range(30):
        world.step(1 / 60, 4)

Half a second later, the weight has swung down and is still 2 m from the
pivot:

.. code-block:: python

    >>> round((weight.position - pivot).length, 2)
    2.0
    >>> hinge.current_angle < 0  # it has turned clockwise
    True

The other joints -- distance, prismatic, wheel, weld, motor and more -- are
made the same way, with ``world.add_distance_joint`` and so on.

A ray cast
----------

:meth:`~box2d.world.World.cast_ray` finds the shapes along a line segment,
given as a start point and a translation from it. This one points straight
down through the right-hand box. With ``first_hit_only=True`` it returns just
the closest hit:

.. code-block:: python

    >>> [hit] = world.cast_ray((3, 10), (0, -20), first_hit_only=True)
    >>> hit.shape.body is boxes[2]
    True
    >>> hit.point
    Vec2(3.0, 1.5)
    >>> hit.normal
    Vec2(0.0, 1.0)

Without it, every shape along the ray is returned, nearest first: here, the
box and then the ground beneath it.

.. code-block:: python

    >>> [hit.shape.body for hit in world.cast_ray((3, 10), (0, -20))] == [boxes[2], ground]
    True

Contact events
--------------

After each step, :meth:`~box2d.world.World.get_contact_events` lists the
contacts that began, ended or hit hard during it. Box2D only reports contacts
for shapes that ask, so a shape opts in with ``enable_contact_events=True``,
as the ball's circle did above; one of the two shapes opting in is enough.
Box2D leaves it off by default because reporting every contact costs time.

The events describe the last step only, and the next step replaces them, so
read them after every step. Dropped from 8 m, the ball lands on the left-hand
box:

.. code-block:: python

    >>> began = []
    >>> for _ in range(120):
    ...     world.step(1 / 60, 4)
    ...     began += world.get_contact_events().begin
    >>> first = began[0]
    >>> {first.shape_a.body, first.shape_b.body} == {ball, boxes[0]}
    True

Hits, which carry the speed of impact, need ``enable_hit_events`` instead.

When something goes wrong
-------------------------

Box2D checks what it is given. An argument it rejects raises
:class:`~box2d.InvalidInputError`, a :class:`ValueError`, from the call that
passed it, naming the Box2D function and the check that failed. The world is
left as it was:

.. code-block:: python

    >>> ball.add_circle(radius=0.5, density=-1)
    Traceback (most recent call last):
      ...
    box2d.InvalidInputError: b2CreateCircleShape rejected its input: b2IsValidFloat( def->density ) && def->density >= 0.0f (in b2CreateShape)

Destroying a body destroys its shapes and joints with it. Anything destroyed,
directly or that way, raises :class:`~box2d.lifetime.DestroyedError`, a
:class:`RuntimeError`, when it is used again:

.. code-block:: python

    >>> ball.destroy()
    >>> ball.position
    Traceback (most recent call last):
      ...
    box2d.lifetime.DestroyedError: This body has been destroyed and can no longer be used.
    >>> circle.is_valid
    False

The testbed
-----------

The ``testbed`` extra, described in :doc:`install`, adds ``box2d-testbed``:
a window of scenarios, each showing one part of Box2D -- stacking, shapes,
joints, events, continuous collision, character movement -- running live with
its controls in a side panel.

.. code-block:: bash

    box2d-testbed

The scenarios are written with this same API, so they double as examples of
it. Each one's source opens in the testbed's own editor, where it can be
changed and run again without a restart, or forked into a scenario of your
own. The project's
`README <https://github.com/giorgosg/box2d-py#running-the-testbed>`_
covers its keys, writing scenarios, and the console it has on the running
simulation.

Where next
----------

The overviews, starting with :doc:`../glance/world_glance`, list what each
module offers, and the API reference documents every class and function in
full.
