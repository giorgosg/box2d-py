Events
======

Box2D does not call back into the program when something happens during a
step. It records what happened -- shapes that began or stopped touching, hits,
sensor overlaps, bodies that moved, joints under strain -- and the program
reads the record once the step has returned, when it is free to change the
world in response. This page covers which events there are, how to ask for
them, and what they carry.

Reading events
--------------

Each kind has a getter on the world, and each getter describes the step that
has just finished. Reading does not consume the events, so asking twice
between steps gives the same answer, but the next step replaces them: read
them after every step, rather than every few.

=====================  ==============================================  ===============================================
Events                 Getter                                          Asked for by
=====================  ==============================================  ===============================================
Contact begin and end  :meth:`~box2d.world.World.get_contact_events`,  ``enable_contact_events`` on either shape
                       its ``begin`` and ``end``
Contact hits           :meth:`~box2d.world.World.get_contact_events`,  ``enable_hit_events`` on either shape
                       its ``hit``
Sensor begin and end   :meth:`~box2d.world.World.get_sensor_events`    ``is_sensor`` on the sensor, and
                                                                       ``enable_sensor_events`` on both shapes
Body moves             :meth:`~box2d.world.World.get_body_events`      nothing: every awake body
Joints under strain    :meth:`~box2d.world.World.get_joint_events`     a joint's ``force_threshold`` or
                                                                       ``torque_threshold``
=====================  ==============================================  ===============================================

The shape flags are keyword arguments wherever a shape is made, and properties
of the shape afterwards; ``body.enable_contact_events()`` and
``body.enable_hit_events()`` set them on every shape of a body. Contact and
hit events are off by default, since reporting every contact costs time.
``enable_sensor_events`` is the other way round: Box2D defaults it off, but
box2d-py defaults it on, so any shape is seen by a sensor unless it opts out.

Contacts beginning and ending
-----------------------------

A contact begins when two shapes start touching and ends when they stop. Each
event names the two shapes, ``shape_a`` and ``shape_b``, in no particular
order, and carries a :class:`~box2d.events.Contact`: a handle on the contact
itself, which compares equal across steps. So a contact can key a dictionary,
from its begin event until the end event with an equal handle.

A ball dropped with some bounce begins and ends a contact with the ground at
each bounce, until it comes to rest on it:

.. code-block:: python

    >>> from box2d import World
    >>> world = World()
    >>> ground = world.new_body().static().box(20, 1).build()
    >>> ball = (
    ...     world.new_body().dynamic().position(0, 4)
    ...     .circle(0.5, restitution=0.5, enable_contact_events=True).build()
    ... )
    >>> happened, touching = [], {}
    >>> for _ in range(240):
    ...     world.step(1 / 60, 4)
    ...     events = world.get_contact_events()
    ...     for event in events.begin:
    ...         happened.append("begin")
    ...         touching[event.contact] = (event.shape_a, event.shape_b)
    ...     for event in events.end:
    ...         happened.append("end")
    ...         del touching[event.contact]
    >>> happened
    ['begin', 'end', 'begin', 'end', 'begin']
    >>> [contact] = touching

Contact data
------------

While the contact lasts, its :attr:`~box2d.events.Contact.data` is a
:class:`~box2d.dataclasses.ContactData`: its two shapes and its manifold, the
contact points and the normal, which points from ``shape_a`` to ``shape_b``.
The same is available without events, by asking a body or a shape for its
``contact_data``:

.. code-block:: python

    >>> contact.is_valid
    True
    >>> data = contact.data
    >>> data.shape_a.body is ground, data.manifold.normal, len(data.manifold.points)
    (True, Vec2(0.0, 1.0), 1)
    >>> ball.contact_data[0].manifold.normal
    Vec2(0.0, 1.0)

Box2D can discard a contact at any step, so check
:attr:`~box2d.events.Contact.is_valid` before reading ``data``, which is None
once the contact is gone.

Destroyed shapes in events
--------------------------

Destroying a shape, or the body it is on, ends its contacts, and the end
events arrive after the next step. In those, and in any other event read after
the shape was destroyed, the destroyed shape is None:

.. code-block:: python

    >>> ball.destroy()
    >>> world.step(1 / 60, 4)
    >>> [(event.shape_a is ground.shapes[0], event.shape_b) for event in world.get_contact_events().end]
    [(True, None)]
    >>> contact.is_valid, contact.data
    (False, None)

So code that handles events checks a shape for None before using it.

Hits
----

A hit event reports two shapes coming together faster than the world's
:attr:`~box2d.world.World.hit_event_threshold`, 1 m/s by default, with the
point and normal of the impact and the ``approach_speed``. It is the event for
a sound or a spark on impact, since it says how hard:

.. code-block:: python

    >>> rock = world.new_body().dynamic().position(0, 5).circle(0.5, enable_hit_events=True).build()
    >>> hits = []
    >>> for _ in range(60):
    ...     world.step(1 / 60, 4)
    ...     hits += world.get_contact_events().hit
    >>> [round(hit.approach_speed, 1) for hit in hits]
    [9.0]
    >>> hits[0].normal
    Vec2(0.0, 1.0)

Sensors
-------

A sensor shape, made with ``is_sensor=True``, never collides. Instead it
reports shapes that begin or stop overlapping it, as
:meth:`~box2d.world.World.get_sensor_events` returns them: each event names
the ``sensor`` and the ``visitor``. A sensor may sit on a body of any type,
including a static one, and never reports shapes on its own body. Box2D works
out sensor overlaps at the end of the step, from where the shapes ended up.
Since Box2D 3.2 it also sweeps fast shapes against static sensors, and
bullets against every sensor not on a bullet, so a shape that crosses a
sensor within a single step is still reported: it begins, and ends at the
next step.

A visitor is reported only if it also has ``enable_sensor_events``, so a shape
made with it off passes through unseen. Here a ghost and a rock fall into a
sensor, and only the rock is reported:

.. code-block:: python

    >>> world.destroy()
    >>> world = World()
    >>> zone = world.new_body().static().position(0, 2).box(4, 2, is_sensor=True).build()
    >>> ghost = (
    ...     world.new_body().dynamic().position(-1, 6)
    ...     .circle(0.25, enable_sensor_events=False).build()
    ... )
    >>> rock = world.new_body().dynamic().position(1, 6).circle(0.25).build()
    >>> entered = []
    >>> for _ in range(60):
    ...     world.step(1 / 60, 4)
    ...     entered += [event.visitor.body for event in world.get_sensor_events().begin]
    >>> entered == [rock]
    True

A sensor's ``sensor_overlaps`` lists what is inside it at the moment, without
events. Destroying a shape inside a sensor ends its overlap, with the
destroyed shape None, as in contact events:

.. code-block:: python

    >>> zone.shapes[0].sensor_overlaps == rock.shapes
    True
    >>> rock.destroy()
    >>> world.step(1 / 60, 4)
    >>> [(event.sensor is zone.shapes[0], event.visitor) for event in world.get_sensor_events().end]
    [(True, None)]

Body moves
----------

:meth:`~box2d.world.World.get_body_events` lists each body the step
simulated, which is every body that is awake and not static, with its new
``transform``. A sleeping body is left out, so updating what is drawn from it
is cheaper than reading every body after every step. ``fell_asleep`` is True on a body's last event before it
sleeps, so whatever follows that body can stop too:

.. code-block:: python

    >>> world.destroy()
    >>> world = World()
    >>> ground = world.new_body().static().box(20, 1).build()
    >>> crate = world.new_body().dynamic().position(0, 3).box(1, 1).build()
    >>> moves = []
    >>> for _ in range(120):
    ...     world.step(1 / 60, 4)
    ...     moves += world.get_body_events()
    >>> all(move.body is crate for move in moves)
    True
    >>> moves[-1].fell_asleep, crate.awake, round(moves[-1].transform.p.y, 2)
    (True, False, 1.0)

Box2D reports what the simulation moved: moving a body by setting its
position is not reported as a move.

Joints under strain
-------------------

A joint reports an event for each step in which the force it applies exceeds
its ``force_threshold``, or its torque its ``torque_threshold``. Both default
to the largest 32-bit float, so a joint reports nothing until one is set. This is how
a breakable joint is made: read the events after the step, and destroy the
joints that report. A weight of about 0.79 kg hangs from this hinge, pulling
with about 7.9 N, and the hinge breaks at 5 N:

.. code-block:: python

    >>> ceiling = world.new_body().static().position(5, 10).build()
    >>> weight = world.new_body().dynamic().position(5, 8).circle(0.5).build()
    >>> hinge = world.add_revolute_joint(ceiling, weight, anchor=(5, 10))
    >>> hinge.force_threshold = 5.0
    >>> world.step(1 / 60, 4)
    >>> for event in world.get_joint_events():
    ...     event.joint.destroy()
    >>> hinge.is_valid
    False

A joint destroyed since the step, on its own or with one of its bodies, is left
out of the joint events, as a destroyed body is left out of the body events.
