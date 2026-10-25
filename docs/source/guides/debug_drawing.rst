Debug drawing
=============

Box2D can describe a world as a stream of simple drawing calls -- polygons,
circles, capsules, segments, points, text -- for a renderer to turn into
pixels. It is meant for seeing what the simulation is doing, not for a
finished game's graphics, and it is how the testbed draws. This page covers
writing a renderer, which call Box2D makes for what, and the flags that choose
what is drawn.

Writing a renderer
------------------

A renderer is a subclass of :class:`~box2d.debug_draw.DebugDraw` that
overrides the methods it can draw. Every method does nothing unless
overridden, so a renderer can start with only the shapes.
:meth:`~box2d.world.World.draw` then calls those methods for everything the
renderer's flags ask for. Call it between steps: during a step, Box2D draws
nothing.

Coordinates are in metres, in world space, and turning them into screen
pixels is the renderer's job. Polygons and solid circles come with a
:class:`~box2d.math.Transform` and their points relative to it, so applying
the transform to a point gives its world position; the other calls give world
positions directly.

This renderer only records what it is asked to draw:

.. code-block:: python

    from box2d import DebugDraw, World


    class Recorder(DebugDraw):
        def __init__(self):
            super().__init__()
            self.drawn = []

        def draw_solid_polygon(self, transform, vertices, radius, color):
            self.drawn.append(("polygon", [transform(v) for v in vertices]))

        def draw_solid_circle(self, transform, center, radius, color):
            self.drawn.append(("circle", transform(center), radius))

        def draw_solid_capsule(self, p1, p2, radius, color):
            self.drawn.append(("capsule", p1, p2, radius))

        def draw_segment(self, p1, p2, color):
            self.drawn.append(("segment", p1, p2))

        def draw_transform(self, transform):
            self.drawn.append(("transform", transform.p))

        def draw_string(self, p, s, color):
            self.drawn.append(("string", s.strip()))

Here it draws a box, a circle, a capsule and a segment:

.. code-block:: python

    >>> world = World()
    >>> ground = world.new_body().static().segment((-5, 0), (5, 0)).build()
    >>> crate = world.new_body().dynamic().position(0, 2).box(2, 1).build()
    >>> ball = world.new_body().dynamic().position(3, 2).circle(0.5).build()
    >>> pill = world.new_body().dynamic().position(-3, 2).capsule((-0.5, 0), (0.5, 0), 0.25).build()
    >>> recorder = Recorder()
    >>> world.draw(recorder)
    >>> for call in sorted(recorder.drawn):
    ...     print(*call)
    capsule Vec2(-3.5, 2.0) Vec2(-2.5, 2.0) 0.25
    circle Vec2(3.0, 2.0) 0.5
    polygon [Vec2(-1.0, 1.5), Vec2(1.0, 1.5), Vec2(1.0, 2.5), Vec2(-1.0, 2.5)]
    segment Vec2(-5.0, 0.0) Vec2(5.0, 0.0)

Box2D draws in no particular order, and an exception raised in one of these
methods is printed rather than raised, after which drawing carries on.

What Box2D calls for what
-------------------------

======================================================  ===================================================
Method                                                  What Box2D draws with it
======================================================  ===================================================
:meth:`~box2d.debug_draw.DebugDraw.draw_solid_polygon`  polygons and boxes, with their rounding ``radius``
:meth:`~box2d.debug_draw.DebugDraw.draw_solid_circle`   circles
:meth:`~box2d.debug_draw.DebugDraw.draw_solid_capsule`  capsules; there is no capsule outline
:meth:`~box2d.debug_draw.DebugDraw.draw_segment`        segments and chain segments, and lines for joints,
                                                        contact normals and forces, and chain normals
:meth:`~box2d.debug_draw.DebugDraw.draw_point`          the end of each chain segment, contact points, and
                                                        joint anchors
:meth:`~box2d.debug_draw.DebugDraw.draw_polygon`        the frames of weld joints
:meth:`~box2d.debug_draw.DebugDraw.draw_circle`         revolute joints
:meth:`~box2d.debug_draw.DebugDraw.draw_bounds`         bounding boxes and islands
:meth:`~box2d.debug_draw.DebugDraw.draw_transform`      the frame at each dynamic body's centre of mass
:meth:`~box2d.debug_draw.DebugDraw.draw_string`         body names, masses, contact separations and forces,
                                                        contact feature ids, and some joint values
======================================================  ===================================================

A point's ``size`` is Box2D's suggestion, between 4 and 10, which its own
samples draw in pixels whatever the zoom.

Choosing what is drawn
----------------------

Each kind of thing has a flag on the renderer. Only
:attr:`~box2d.debug_draw.DebugDraw.draw_shapes` is on by default; the others,
documented with :class:`~box2d.debug_draw.DebugDraw`, include
``draw_joints``, ``draw_aabbs``, ``draw_contacts``, ``draw_contact_normals``,
``draw_contact_impulses``, ``draw_mass``, ``draw_body_names`` and
``draw_islands``. Here the shapes are turned off and ``draw_mass`` on, which
draws a frame, a short line and the mass at each dynamic body's centre of
mass:

.. code-block:: python

    >>> recorder = Recorder()
    >>> recorder.draw_shapes = False
    >>> recorder.draw_mass = True
    >>> world.draw(recorder)
    >>> sorted(call[0] for call in recorder.drawn).count("transform")
    3
    >>> sorted(call[1] for call in recorder.drawn if call[0] == "string")
    ['0.70', '0.79', '2.00']

The bounding boxes ``draw_aabbs`` shows are the slightly enlarged ones Box2D
keeps for each shape, not the shape's exact extent.

:attr:`~box2d.debug_draw.DebugDraw.drawing_bounds` limits drawing to a region
of the world. Box2D finds the shapes in it with its own tree, so setting it to
the visible area skips everything off screen before any method is called. It
starts as the whole world.

.. code-block:: python

    >>> from box2d import AABB
    >>> recorder = Recorder()
    >>> recorder.drawing_bounds = AABB(lower=(2, 1), upper=(4, 3))
    >>> world.draw(recorder)
    >>> recorder.drawn
    [('circle', Vec2(3.0, 2.0), 0.5)]

Colours
-------

Each method gets a :class:`~box2d.debug_draw.Color`, with 0-255 ``r``, ``g``,
``b`` and ``a`` components; ``as_float`` gives them from 0 to 1. Box2D's
colours are always opaque. It colours a shape by the state of its body:
static shapes pale green, kinematic royal blue, awake dynamic pink, sleeping
dynamic grey, and sensors wheat, with others for disabled, fast, bullet and
speed-capped bodies. A shape made with ``custom_color``, a ``0xRRGGBB``
integer, is drawn in that colour instead:

.. code-block:: python

    >>> class Colours(DebugDraw):
    ...     def __init__(self):
    ...         super().__init__()
    ...         self.colours = {}
    ...     def draw_solid_circle(self, transform, center, radius, color):
    ...         self.colours[radius] = hex(color.hex)
    >>> marked = world.new_body().dynamic().position(6, 2).circle(0.75, custom_color=0x00FF00).build()
    >>> colours = Colours()
    >>> world.draw(colours)
    >>> colours.colours[0.5], colours.colours[0.75]  # the ball, pink, and the marked circle
    ('0xffc0cb', '0xff00')
