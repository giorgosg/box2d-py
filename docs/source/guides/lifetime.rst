Object lifetime
===============

Box2D owns the bodies, shapes and joints it simulates, and box2d-py's objects
are handles on them. This page covers who keeps what alive, what destroying
something takes with it, what happens to a handle once its object is gone,
and the errors box2d-py raises when something is used wrongly.

The world keeps what it contains
--------------------------------

A body, shape or joint stays alive for as long as its world has it, whether or
not the code that made it kept the object it was given. These crates are made
without keeping them:

.. code-block:: python

    from box2d import World

    world = World()
    ground = world.new_body().static().box(20, 1).build()
    for x in (-2, 0, 2):
        world.new_body().dynamic().position(x, 3).box(1, 1).build()

Anything that hands a body, shape or joint back -- ``world.bodies``,
``body.shapes``, ``body.joints``, a query, an event -- hands back that same
object, not a new one. So whatever was set on it is still there, including
``user_data``, which every body, shape and joint has for the application's own
use:

.. code-block:: python

    >>> len(world.bodies)
    4
    >>> [hit] = world.cast_ray((0, 10), (0, -20), first_hit_only=True)
    >>> crate = hit.shape.body
    >>> crate.user_data = "the middle crate"
    >>> world.cast_ray((0, 10), (0, -20), first_hit_only=True)[0].shape.body.user_data
    'the middle crate'
    >>> crate.shapes[0] is hit.shape
    True
    >>> hinge = world.add_revolute_joint(ground, crate, anchor=(0, 0.5))
    >>> crate.joints[0] is hinge
    True

Destroying things
-----------------

``destroy()`` removes a body, shape, chain or joint from its world. What
belongs to it goes too: destroying a body destroys its shapes and chains and
every joint attached to it, which wakes the bodies at the other ends.
Destroying a shape updates its body's mass, unless ``update_body_mass=False``
is passed to save the work when removing several, and destroying a joint wakes
both its bodies. Destroying something a second time does nothing.

:meth:`~box2d.world.World.destroy` destroys the world and everything in it,
which is much faster than destroying its contents one by one.

Using what has been destroyed
-----------------------------

A handle whose object has been destroyed -- by its own ``destroy()``, or with
its body or its world -- raises :exc:`~box2d.lifetime.DestroyedError`, a
:class:`RuntimeError`, when it is used. ``is_valid`` asks without raising:

.. code-block:: python

    >>> crate.destroy()
    >>> len(world.bodies), hit.shape.is_valid, hinge.is_valid
    (3, False, False)
    >>> crate.destroy()
    >>> hinge.current_angle
    Traceback (most recent call last):
      ...
    box2d.lifetime.DestroyedError: This joint has been destroyed and can no longer be used.

``user_data`` is the exception: it stays readable, since it is the
application's and not Box2D's.

Objects outliving their world
-----------------------------

The same goes for everything a destroyed world held. The handles keep working
as Python objects, and every use of one that needs Box2D raises:

.. code-block:: python

    >>> left = world.cast_ray((-2, 10), (0, -20), first_hit_only=True)[0].shape.body
    >>> world.destroy()
    >>> world.is_valid, left.is_valid, ground.is_valid
    (False, False, False)
    >>> left.position
    Traceback (most recent call last):
      ...
    box2d.lifetime.DestroyedError: This body has been destroyed and can no longer be used.

A world is also destroyed when Python collects it. But each body refers to its
world, and a world to its bodies, so a world with anything in it is collected
only when Python's cycle collector next runs, and not at all while the
application holds one of its bodies, shapes or joints. Box2D has room for 128
worlds at a time, so call ``destroy()`` on a world once it is finished with
rather than leaving it to the garbage collector.

Not during a step
-----------------

Nothing can be created or destroyed while the world is stepping, which is when
Box2D calls the world's callbacks: :attr:`~box2d.world.World.custom_filter`,
:attr:`~box2d.world.World.pre_solve` and the others. Box2D would ignore a
destroy then and fail a create, so box2d-py raises :class:`RuntimeError`
instead, as it does for a step from inside a step:

.. code-block:: python

    >>> world = World()
    >>> ground = world.new_body().static().box(20, 1).build()
    >>> crate = (
    ...     world.new_body().dynamic().position(0, 0.95)
    ...     .box(1, 1, enable_custom_filtering=True).build()
    ... )
    >>> refused = []
    >>> def destroy_on_contact(shape_a, shape_b):
    ...     try:
    ...         crate.destroy()
    ...     except RuntimeError as error:
    ...         refused.append(str(error))
    ...     return True
    >>> world.custom_filter = destroy_on_contact
    >>> world.step(1 / 60, 4)
    >>> refused
    ['cannot destroy a body during a world callback; destroy it after the step']
    >>> crate.is_valid
    True

The way to react to something that happens during a step is to note it, and
act once ``step()`` has returned. :doc:`events` are made for that, being read
after the step: here, each crate that lands is removed.

.. code-block:: python

    >>> world.custom_filter = None
    >>> crates = [
    ...     world.new_body().dynamic().position(x, 3)
    ...     .box(1, 1, enable_contact_events=True).build()
    ...     for x in (-3, 3)
    ... ]
    >>> for _ in range(60):
    ...     world.step(1 / 60, 4)
    ...     landed = {
    ...         shape.body
    ...         for event in world.get_contact_events().begin
    ...         for shape in (event.shape_a, event.shape_b)
    ...         if shape.body.type == "dynamic"
    ...     }
    ...     for body in landed:
    ...         body.destroy()
    >>> [crate.is_valid for crate in crates]
    [False, False]

Invalid input
-------------

Box2D checks the arguments it is given. One it rejects raises
:exc:`~box2d.InvalidInputError` from the call that passed it, naming the Box2D
function and the check that failed, and the world is left as it was:

.. code-block:: python

    >>> import math
    >>> box = world.new_body().dynamic().position(0, 5).box(1, 1).build()
    >>> box.linear_velocity = (math.nan, 0)
    Traceback (most recent call last):
      ...
    box2d.InvalidInputError: b2Body_SetLinearVelocity rejected its input: b2IsValidVec2( linearVelocity )
    >>> box.linear_velocity
    Vec2(0.0, 0.0)

``InvalidInputError`` is a :class:`ValueError`. Some arguments are checked in
Python before Box2D sees them, and raise a plain :class:`ValueError`, so
catching :class:`ValueError` covers a bad value either way:

.. code-block:: python

    >>> world.add_body(body_type="dynamc")
    Traceback (most recent call last):
      ...
    ValueError: Invalid body type: 'dynamc'. Must be one of: dynamic, kinematic, static.

Logging
-------

Box2D's other messages are warnings rather than errors, and go to the
:mod:`logging` logger named ``box2d``: a body whose velocity has become
infinite or not a number, for instance, is reported as ``unstable`` followed
by its name. With no logging configured, Python prints warnings to standard
error. ``logging.getLogger("box2d")`` is the logger to configure to send them
elsewhere or silence them.
