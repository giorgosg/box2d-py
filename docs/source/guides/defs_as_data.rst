Definitions as Data
===================

A definition says what an object is, and it can say so as plain data: a scene
file, a level editor's undo stack, a message between two processes. Every
definition turns into JSON-ready dictionaries and back, reads itself back from
a live object, describes its own fields, and prints as code.

To and from a dictionary
------------------------

:meth:`~box2d.defdata.DefData.to_dict` writes what differs from the defaults:

.. code-block:: python

    >>> import json
    >>> from box2d import BodyDef, World
    >>> body_def = BodyDef(type="dynamic", position=(1, 2), linear_damping=0.5)
    >>> body_def.to_dict()
    {'type': 'dynamic', 'position': [1.0, 2.0], 'linear_damping': 0.5}
    >>> text = json.dumps(body_def.to_dict())
    >>> BodyDef.from_dict(json.loads(text)) == body_def
    True

Points are ``[x, y]``, a rotation an angle in radians, a body type its name, a
filter its three integers and a material a dictionary of its own.
``user_data`` is left out: it is the application's, and may be anything.

:meth:`~box2d.defdata.DefData.from_dict` is strict, so a typing mistake in a
file does not quietly become a default:

.. code-block:: python

    >>> BodyDef.from_dict({"positon": [1, 2]})
    Traceback (most recent call last):
    ValueError: BodyDef has no field 'positon'; did you mean 'position'?

Shapes
^^^^^^

A shape's description is its geometry and its own settings, so a geometry
definition holds a :class:`~box2d.shapedef.ShapeDef` as its ``shape``, which
is for ``add_shape`` and dictionaries: a shape's ``geometry`` takes no notice
of it. Its
dictionary is flat, and carries a ``"kind"``, which
:func:`~box2d.defdata.def_from_dict` reads to make the right definition.
:meth:`~box2d.body.Body.add_shape` makes the shape from one:

.. code-block:: python

    >>> from box2d import CircleDef, ShapeDef, def_from_dict
    >>> circle = CircleDef(0.5, shape=ShapeDef(density=2.0))
    >>> circle.to_dict()
    {'kind': 'circle', 'radius': 0.5, 'density': 2.0}
    >>> world = World()
    >>> body = world.add_body(body_type="dynamic")
    >>> shape = body.add_shape(def_from_dict(circle.to_dict()))
    >>> shape.radius, shape.density
    (0.5, 2.0)

Joints
^^^^^^

A joint definition names its bodies, which a dictionary cannot hold. What
stands for a body in the data is yours to choose, so the library invents no
scene format: ``body_ref`` gives each body's reference, and ``resolve`` gives
the body back:

.. code-block:: python

    >>> from box2d import RevoluteJointDef
    >>> other = world.add_body(body_type="dynamic", position=(2, 0))
    >>> names = {"lid": body, "box": other}
    >>> name_of = {id(b): name for name, b in names.items()}
    >>> hinge = RevoluteJointDef(body, other, anchor=(1, 0), enable_motor=True)
    >>> data = hinge.to_dict(body_ref=lambda b: name_of[id(b)])
    >>> data["body_a"], data["local_anchor_b"]
    ('lid', [-1.0, 0.0])
    >>> again = def_from_dict(data, resolve=names.__getitem__)
    >>> world.add_joint(again).enable_motor
    True

A world ``anchor`` is written as the two local anchors it stands for.

What a missing field means
^^^^^^^^^^^^^^^^^^^^^^^^^^

A field left out means the default of whichever version reads the file, and
Box2D's defaults do change between versions. Two things guard against that:
:data:`~box2d.defdata.DEFAULTS_VERSION` names the set of defaults, for a file format to
write once at its top, and ``to_dict(full=True)`` writes every field, for
archives that must mean the same thing for good. In a full dictionary a field
worked out when the object is made, as a distance joint's rest length is, is
None.

Reading live objects back
-------------------------

:meth:`Body.to_def <box2d.body.Body.to_def>`,
:meth:`Shape.to_def <box2d.shape.Shape.to_def>`,
:meth:`Chain.to_def <box2d.shape.Chain.to_def>` and
:meth:`Joint.to_def <box2d.joint.Joint.to_def>` give the definition of
something already in the world, which is how to save a scene that has been
running:

.. code-block:: python

    >>> world.step(1 / 60, 4)
    >>> saved = other.to_def()
    >>> saved.to_dict()["type"], round(saved.position.x, 2)
    ('dynamic', 2.0)
    >>> shape.to_def().to_dict()
    {'kind': 'circle', 'radius': 0.5, 'density': 2.0}

Values come back as written: Box2D stores 0.7 in 32 bits, and reads it back as
0.699999988, but the definition says 0.7. Two definitions are equal when Box2D
would make the same thing of them, so a field left out equals its default.
:meth:`World.add_body_def <box2d.world.World.add_body_def>` makes a body from
what ``to_def()`` gave, and a joint comes back with ``world.add_joint``.
What is set on an object once made and is no part of a definition, such as a
joint's ``force_threshold``, is not read.

A few settings Box2D takes when an object is made and keeps no way to read,
and :meth:`~box2d.defdata.DefData.fields` marks each of them not ``readable``.
``to_def()`` leaves those at their defaults, whatever the object was made with:
``allow_fast_rotation`` on a body; ``enable_custom_filtering``,
``invoke_contact_creation`` and ``update_body_mass`` on a shape; and a pogo
joint's ``normal``, ``max_tension_force``, ``max_compression_force`` and
``velocity``. A polygon's vertices come back already placed, so its ``offset``
and ``rotation`` come back as None, and mean nothing further.

Describing the fields
---------------------

:meth:`~box2d.defdata.DefData.fields` says what a definition holds, which is
what an inspector or a file format's schema is generated from:

.. code-block:: python

    >>> from box2d import WheelJointDef
    >>> hertz = {f.name: f for f in WheelJointDef.fields()}["spring_hertz"]
    >>> hertz.type, hertz.default, hertz.unit, hertz.range, hertz.readable
    ('float', 1.0, 'Hz', (0.0, inf), True)

As code
-------

A definition's ``repr`` is code that makes an equal one, defaults left out, so
it is what to paste into a program:

.. code-block:: python

    >>> body_def
    BodyDef(type='dynamic', position=Vec2(1.0, 2.0), linear_damping=0.5)
    >>> CircleDef(0.5, shape=ShapeDef(density=2.0))
    CircleDef(radius=0.5, shape=ShapeDef(density=2.0))

A joint definition's repr names its bodies by their own repr, which is not
code; everything else in it is.
