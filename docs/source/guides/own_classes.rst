Your Own Classes
================

A game usually wants more on its objects than Box2D keeps: a ball's score, a
bumper's colour, what a sensor is for. ``user_data`` can hold any of that, but
a world can do better and make its objects your own classes. A ball found by a
contact event, a query or ``body.shapes`` is then a ``Ball``, with your methods
on it, and nothing has to be looked up on the way. A world also reports each
object it makes and destroys, which is how a program keeps a list of its own
in step with the world's.

Choosing the classes
--------------------

A world's class map names, for any class the library makes, a subclass of it
to make instead:

.. code-block:: python

    >>> from box2d import Body, Circle, World
    >>> class Ball(Body):
    ...     def kick(self):
    ...         self.apply_linear_impulse((1, 0))
    >>> world = World(classes={Body: Ball})
    >>> ball = world.add_body(body_type="dynamic")
    >>> type(ball).__name__
    'Ball'
    >>> ball.kick()

The map applies wherever the world makes that class: ``add_body``, the
builder, every ``add_*`` on a body, every ``add_*_joint``, and anything Box2D
hands back afterwards, since that is the object the world made. A subclass of
World sets it once for every world of its kind, and ``World(classes=...)``
adds to it for one world:

.. code-block:: python

    >>> class BallCircle(Circle):
    ...     pass
    >>> class Game(World):
    ...     classes = {Body: Ball}
    >>> game = Game(classes={Circle: BallCircle})
    >>> circle = game.add_body().add_circle(radius=1)
    >>> type(circle).__name__, type(circle.body).__name__
    ('BallCircle', 'Ball')
    >>> game.class_for(Body).__name__
    'Ball'

A few rules hold the map to what the world makes:

- **Each kind is mapped on its own.** Circle, Polygon, Box, Capsule, Segment,
  Chain, ChainSegment and each joint kind are separate keys. Mapping Polygon
  leaves boxes alone, though a Box is a Polygon, and a Box cannot stand in for
  a Polygon, since boxes are made differently. A chain's segments, which
  Box2D makes, follow the ChainSegment entry.
- **A mouse joint's proxy is a body,** and so of the class mapped for Body.
- **A bad map fails when the world is made.** A key the world never makes
  raises ``ValueError``; a value that is not a subclass of its key raises
  ``TypeError``.
- **A subclass keeps the constructor's arguments.** An ``__init__`` of its own
  passes everything on to ``super().__init__`` and sets its own attributes
  after. Attributes are its to add: only the library's own classes refuse
  names they do not define.

The same extras on every kind
-----------------------------

To give every shape, or every joint, the same methods, write them once as a
mixin and let :func:`~box2d.world.classes_with` make a subclass of each kind:

.. code-block:: python

    >>> from box2d import Shape, classes_with
    >>> class Glowing:
    ...     glow = 0.0
    ...     def light_up(self):
    ...         self.glow = 1.0
    >>> world = World(classes=classes_with(Glowing, Shape))
    >>> box = world.add_body().add_box(1, 1)
    >>> box.light_up()
    >>> type(box).__name__, box.glow
    ('GlowingBox', 1.0)

It makes each class once and hands the same ones back on every call, so a map
built with it can be merged with others: ``{**classes_with(Glowing, Shape),
Body: Ball}``.

Hearing of what is made and destroyed
-------------------------------------

:meth:`~box2d.world.World.object_created` and
:meth:`~box2d.world.World.object_destroyed` do nothing until a subclass
overrides them:

.. code-block:: python

    >>> class Watched(World):
    ...     def object_created(self, obj):
    ...         print("made", type(obj).__name__)
    ...     def object_destroyed(self, obj, cause):
    ...         print("lost", type(obj).__name__, "with", type(cause).__name__)
    >>> world = Watched()
    >>> body = world.new_body().dynamic().circle(0.5).build()
    made Body
    made Circle
    >>> other = world.add_body(body_type="dynamic", position=(2, 0))
    made Body
    >>> joint = world.add_distance_joint(body, other)
    made DistanceJoint
    >>> body.destroy()
    lost DistanceJoint with Body
    lost Circle with Body
    lost Body with Body

What they promise:

- **Made means usable.** ``object_created`` runs once the object is fully made,
  its class's own ``__init__`` included, in the order things are made: a body
  before the shapes added to it, a chain before its segments.
- **Everything that goes is reported, children first.** Destroying a body takes
  its joints, chains and shapes with it, a chain its segments, a mouse joint
  its proxy body, the world everything; each is reported before its parent, so
  a shape can still reach its body. ``cause`` is the object whose ``destroy()``
  started it, or the world.
- **Reported while still readable.** ``object_destroyed`` runs before Box2D lets
  go of anything, so the object's last position or force is there to read.
- **A failing report does not stop a destroy.** If ``object_destroyed`` raises,
  every object is still reported and destroyed, and the first exception is
  raised after. One from ``object_created`` reaches the caller once everything
  made has been reported, and the objects stay made.
- **Only what the world and bodies make.** An object made by calling its class,
  or a shape class's ``create``, is reported neither made nor destroyed. A
  world garbage collected without ``destroy()`` reports nothing.
- **Once each.** Destroying something again from inside ``object_destroyed``,
  even what is already going, does nothing; adding a shape or joint to a body
  that is going raises ``RuntimeError``.
- **A mouse joint's proxy body is reported** like any other body, just before
  the joint. It is the joint's ``body_a``, and goes with it.

The world's own teardown names the world as the cause, which is how to skip
it when it is only noise:

.. code-block:: python

    >>> world.destroy()
    lost Body with Watched

Telling a type checker
----------------------

The world's methods are annotated with the library's classes, so to a type
checker ``add_body()`` returns a Body even when the class map makes it a Ball.
A World subclass that says otherwise, once, puts that right for every caller:

.. code-block:: python

    >>> from typing import Any, cast
    >>> class Pinball(World):
    ...     classes = {Body: Ball}
    ...     def add_body(self, *args: Any, **kwargs: Any) -> Ball:
    ...         return cast(Ball, super().add_body(*args, **kwargs))
    >>> table = Pinball()
    >>> table.add_body(body_type="dynamic").kick()

The ``cast`` is needed: the base method's annotation says Body, and only the
class map knows better.
