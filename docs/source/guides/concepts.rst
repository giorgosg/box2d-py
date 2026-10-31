Concepts
========

This page sets out what the rest of the documentation takes for granted: what
a world, a body, a shape and a joint are, the units Box2D works in, how a
world is stepped and how bodies fall asleep, and the two ways box2d-py offers
of making things. Its examples carry on from one another, as on the other
pages.

The world
---------

A :class:`~box2d.world.World` is one simulation. It holds the bodies and
joints, steps them forward in time, and answers questions about where things
are. Worlds are independent of each other: nothing in one collides with or is
jointed to anything in another.

.. code-block:: python

    from box2d import World

    world = World(gravity=(0, -10))

Gravity is an acceleration, in metres per second squared, applied to every
dynamic body and scaled per body by its ``gravity_scale``. Box2D has no up
direction of its own: ``(0, -10)`` is what makes y point up.

Bodies
------

A body is a rigid frame with a position, a rotation and a velocity. It is one
of three types:

- **static** bodies do not move under simulation, and behave as if their mass
  were infinite. A body made without a type is static.
- **kinematic** bodies move at the velocity they are given, and nothing --
  gravity, forces, collisions -- changes it. They too behave as if infinitely
  massive. They suit moving platforms and anything else animated rather than
  simulated.
- **dynamic** bodies are fully simulated: gravity and forces accelerate them,
  and they collide with bodies of every type.

Only dynamic bodies collide with everything. A static or kinematic body
collides with dynamic bodies only, never with another static or kinematic one.

Here is one of each, stepped for a second. The platform has moved 2 m at the
2 m/s it was given, the crate has fallen about 5 m, and the floor has not
moved. Static and kinematic bodies have no mass, as Box2D stores it:

.. code-block:: python

    >>> floor = world.new_body().static().box(20, 1).build()
    >>> platform = (
    ...     world.new_body().kinematic().position(-5, 3).linear_velocity(2, 0)
    ...     .box(2, 0.2).build()
    ... )
    >>> crate = world.new_body().dynamic().position(5, 10).box(1, 1).build()
    >>> for _ in range(60):
    ...     world.step(1 / 60, 4)
    >>> floor.position, platform.position
    (Vec2(0.0, 0.0), Vec2(-3.0, 3.0))
    >>> round(crate.position.y, 1)
    5.0
    >>> [body.type for body in (floor, platform, crate)]
    ['static', 'kinematic', 'dynamic']
    >>> [round(body.mass, 3) for body in (floor, platform, crate)]
    [0.0, 0.0, 1.0]

Shapes
------

A shape gives a body its extent, its mass and something to collide with. A body
can carry any number of them. They move with it, never relative to each other,
and shapes on the same body never collide with each other.

The kinds are circles, capsules, convex polygons (a box is a polygon),
segments, and chains. A chain is a run of segments joined end to end, one-sided
and meant for static terrain; it is not a :class:`~box2d.shape.Shape` itself,
and its segments are.

A shape's mass is its area times its density, in kilograms per square metre,
which defaults to 1. A body's mass and centre of mass come from all of its
shapes. This cart is a 2 by 0.5 m box on two wheels of radius 0.25 m, so it
weighs 1 kg plus the two wheels' area:

.. code-block:: python

    >>> cart = (
    ...     world.new_body().dynamic().position(-8, 5)
    ...     .box(2, 0.5)
    ...     .circle(0.25, center=(-0.75, -0.5))
    ...     .circle(0.25, center=(0.75, -0.5))
    ...     .build()
    ... )
    >>> len(cart.shapes), round(cart.mass, 3)
    (3, 1.393)

A shape also has a surface: ``friction``, 0.6 by default, ``restitution``, or
bounciness, 0 by default, and ``rolling_resistance``. As in Box2D, these are
the fields of a :class:`~box2d.material.SurfaceMaterial`, the ``material`` of
the shape's :class:`~box2d.shapedef.ShapeDef`. Wherever a shape is made, its
``ShapeDef`` fields are keyword arguments, and so is each material field, on
its own: ``friction=0.2`` fills that field of the material, and overrides it
when a ``material=`` is given too. A shape made with ``is_sensor=True`` is a
sensor: it reports what overlaps it and never collides, as :doc:`events`
describes.

Joints
------

A joint constrains how two bodies move relative to each other: a revolute joint
pins them together at a point they both turn about, a weld joint holds them
rigidly, a prismatic joint lets them slide along one axis, and so on. One of
the two is often a static body, which fixes the other to the world. A joint
belongs to the world rather than to either body, and destroying either body
destroys it.

The two bodies a joint connects do not collide with each other, unless it was
made with ``collide_connected=True``. This door stands on a hinge at its foot,
where it meets the floor, and the two touch without colliding:

.. code-block:: python

    >>> door = world.new_body().dynamic().position(8, 2.5).box(0.2, 4).build()
    >>> hinge = world.add_revolute_joint(floor, door, anchor=(8, 0.5))
    >>> hinge.collide_connected
    False

The world has an ``add_*_joint`` method for each kind: distance, filter,
motor, mouse, mover, pogo, prismatic, revolute, weld and wheel.

Units
-----

Box2D works in metres, kilograms and seconds, so forces are in newtons, and
angles are in radians. Its tolerances are tuned for moving shapes between
about 0.1 and 10 metres; much smaller or larger than that, stacks jitter and
objects pass through each other. Static shapes can be longer, up to about 50 m;
a longer floor is better split over several static bodies. So size a scene in
metres, not pixels, and scale it for drawing.

Positions are 32-bit floats, which lose precision far from the origin. Box2D
advises keeping a world within about 16 km.

A rotation is given in radians and read back between -pi and pi, so a body
made at 200 degrees reads -160:

.. code-block:: python

    >>> import math
    >>> sign = world.new_body().position(0, 20).rotation(math.radians(200)).build()
    >>> round(math.degrees(sign.rotation), 1)
    -160.0

Stepping
--------

:meth:`~box2d.world.World.step` advances the world by a time step, in seconds,
divided into substeps. Give it the same time step every time: a time step
that varies gives results that vary with it, which Box2D warns makes a
simulation hard to debug, so the step should not follow the frame rate.
1/60 s gives a good simulation, and Box2D advises nothing longer than 1/30 s.
The substeps trade speed for accuracy. Four is Box2D's recommendation and the default;
more help long chains of joints, which stretch less.

A game's frames do not take a fixed time, so the usual loop keeps an
accumulator: each frame adds the time it took, the world is stepped once for
every whole time step the accumulator holds, and what is left over carries to
the next frame.

.. code-block:: python

    TIME_STEP = 1 / 60


    class Clock:
        """Steps a world in fixed steps, however long each frame takes."""

        def __init__(self, world):
            self.world = world
            self.accumulator = 0.0

        def advance(self, elapsed):
            """Step for a frame that took ``elapsed`` seconds; return the step count."""
            # Capped, so that one long stall -- a breakpoint, a dragged
            # window -- does not demand hundreds of steps at once.
            self.accumulator += min(elapsed, 0.25)
            steps = 0
            while self.accumulator >= TIME_STEP:
                self.world.step(TIME_STEP, 4)
                self.accumulator -= TIME_STEP
                steps += 1
            return steps

Frames of 16, 16, 40 and 2 ms take this many steps of 1/60 s:

.. code-block:: python

    >>> clock = Clock(world)
    >>> [clock.advance(elapsed) for elapsed in (0.016, 0.016, 0.040, 0.002)]
    [0, 1, 3, 0]

What is left over, ``clock.accumulator / TIME_STEP`` as a fraction of a step,
is how far the frame has got towards the next step: enough to draw each body
part way between its last two positions, if the drawing should be smoother
than the steps.

Sleeping
--------

Simulating a body that is not moving is wasted work, so Box2D puts it to sleep.
Bodies touching each other or connected by joints form an island, and an
island sleeps once every body in it has moved slower than its
``sleep_threshold``, 0.05 m/s by default, for half a second. A sleeping body
costs nothing to step. It wakes when something awake touches it, when a joint
or contact on it is destroyed, when a force or impulse is applied to it, when
it is given a velocity other than zero, or when ``awake`` is set to True.

Stopped, the platform falls asleep with everything else, and
:attr:`~box2d.world.World.awake_body_count` falls to zero:

.. code-block:: python

    >>> platform.linear_velocity = (0, 0)
    >>> for _ in range(120):
    ...     world.step(1 / 60, 4)
    >>> crate.awake, world.awake_body_count
    (False, 0)
    >>> crate.apply_linear_impulse((0, 5))
    >>> crate.awake, world.awake_body_count
    (True, 1)

A body moved by hand does not wake what rests on it: after moving a static or
kinematic body by setting its position, call its ``wake_touching()``. Sleep
can be turned off for one body, with ``enable_sleeping``, or for the whole
world, with :attr:`~box2d.world.World.enable_sleeping`.

The builder and the add methods
-------------------------------

There are two ways to make a body. :meth:`~box2d.world.World.new_body` starts a
:class:`~box2d.body.BodyBuilder`, whose methods each set one thing and return
the builder, and whose ``build()`` makes the body.
:meth:`~box2d.world.World.add_body` makes a body in one call, taking the same
settings as keywords, after which ``add_box``, ``add_circle`` and the other
``add_*`` methods attach shapes to it one at a time. The builder is a
convenience over the second way: ``build()`` calls ``add_body``, then the
``add_*`` method for each shape it was given, with the same arguments.

So these two bodies are the same, made each way:

.. code-block:: python

    >>> built = world.new_body().dynamic().position(-2, 8).box(1, 1, friction=0.2).build()
    >>> added = world.add_body(body_type="dynamic", position=(2, 8))
    >>> box = added.add_box(1, 1, friction=0.2)
    >>> built.mass == added.mass, built.shapes[0].friction == box.friction
    (True, True)

The builder reads as one expression, and can be kept and built from again:
each ``build()`` makes a new body, with whatever the builder holds at that
moment.

.. code-block:: python

    >>> template = world.new_body().dynamic().box(0.5, 0.5)
    >>> crates = [template.position(x, 12).build() for x in (-1, 0, 1)]
    >>> [(crate.position.x, len(crate.shapes)) for crate in crates]
    [(-1.0, 1), (0.0, 1), (1.0, 1)]

The ``add_*`` methods return the shape they made, where the builder returns
only the body, and they add a shape to a body that already exists. Joints have
no builder: they are made with the ``add_*_joint`` methods, or with
:meth:`~box2d.world.World.add_joint` from a definition in
:mod:`box2d.jointdef`.
