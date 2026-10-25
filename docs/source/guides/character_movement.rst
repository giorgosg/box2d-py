Character movement
==================

A player's character usually should not behave like a crate. It should stop
dead against a wall rather than bounce, walk up a step without tipping over,
and go where the controls say rather than where the forces take it. Box2D
offers two toolkits for this rather than a finished controller, since games
want different things of one: a geometric mover, which is not a body at all,
and a dynamic mover, a body driven by two joints made for it. This page builds
a small version of each. The testbed's Character scenarios, Mover and Dynamic
Mover, run fuller ones.

Box2D suggests the geometric mover for networked games that need rollback, and
for games that do not want the character to push things about; and the dynamic
mover for games that want it to, which is harder to network.

A geometric mover
-----------------

A geometric mover is a capsule whose position and velocity the program keeps
itself. Nothing in the world knows it is there: bodies do not collide with it,
and gravity does not reach it. Each step, it asks the world which surfaces the
capsule is up against, works out the movement that comes closest to the one
wanted while clearing all of them, and trims its velocity so as not to keep
pushing into them. Three functions do that:

- :meth:`~box2d.world.World.collide_mover` returns the surfaces a capsule
  touches or overlaps, as :class:`~box2d.mover.CollisionPlane` objects, each
  with the shape it came from;
- :func:`~box2d.mover.solve_planes` finds the movement closest to the one
  asked for that satisfies every plane, and returns it as the
  ``translation`` of a :class:`~box2d.mover.MoverResult`;
- :func:`~box2d.mover.clip_vector` removes the parts of the velocity that
  point into the planes that pushed.

Here a capsule 1.6 m tall -- two centres 0.4 m above and below its position,
and a 0.4 m radius round them -- drops onto the ground, then walks right into a
wall:

.. code-block:: python

    from box2d import Vec2, World, clip_vector, solve_planes

    world = World()
    terrain = (
        world.new_body().static()
        .segment((-10, 0), (10, 0))  # the ground
        .box(1, 4, offset=(5, 2))  # a wall, its left face at x = 4.5
        .build()
    )

    HALF_LENGTH, RADIUS = 0.4, 0.4
    GRAVITY = 30.0  # the character's own, in m/s^2
    TIME_STEP = 1 / 60


    class Walker:
        def __init__(self, position):
            self.position = Vec2(position)
            self.velocity = Vec2(0, 0)
            self.on_ground = False

        def capsule(self):
            x, y = self.position
            return (x, y - HALF_LENGTH), (x, y + HALF_LENGTH)

        def update(self, walk_speed):
            self.velocity = Vec2(walk_speed, self.velocity.y - GRAVITY * TIME_STEP)
            planes = world.collide_mover(*self.capsule(), RADIUS)
            # A surface facing up more steeply than 45 degrees is ground.
            self.on_ground = any(plane.plane.normal.y > 0.7 for plane in planes)
            result = solve_planes(self.velocity * TIME_STEP, planes)
            self.position += result.translation
            self.velocity = clip_vector(self.velocity, planes)

It lands with the bottom of its capsule on the ground, 0.8 m below its
position, and stops against the wall with its side on the wall's face:

.. code-block:: python

    >>> walker = Walker((0, 3))
    >>> for _ in range(60):
    ...     walker.update(0)
    >>> round(walker.position.y, 1), walker.on_ground, walker.velocity
    (0.8, True, Vec2(0.0, 0.0))
    >>> for _ in range(120):
    ...     walker.update(4)
    >>> round(walker.position.x, 1), walker.velocity
    (4.1, Vec2(0.0, 0.0))

The capsule is not stepped by the world, so ``update`` runs once per step, and
the world's ``step`` moves only the bodies around it. A jump is a velocity set
while ``on_ground``.

Each plane carries a ``push_limit``, how far it may push the mover, which is
unlimited unless changed, and ``clip_velocity``. Lowering the first between
:meth:`~box2d.world.World.collide_mover` and
:func:`~box2d.mover.solve_planes` makes a surface soft, so the mover can
push into it, as into another character, and setting the second to False
keeps the mover's speed through it. Each plane's ``shape`` says which surface
it is, for deciding that, or for leaving planes out altogether.

:meth:`~box2d.world.World.cast_mover` is the sweep to go with them: it moves
the capsule along a translation and returns the fraction of it travelled
before hitting something, 1.0 if nothing. It is built for movers, and lets a
capsule already touching a surface slide along it rather than stop. Here, how
far the walker could fall from 3 m up before landing:

.. code-block:: python

    >>> fraction = world.cast_mover((-3, 2.6), (-3, 3.4), RADIUS, (0, -5))
    >>> round(fraction * 5, 1)
    2.2

Both mover queries take a :class:`~box2d.collision_filter.CollisionFilter`, as
the other queries do, to choose which shapes count, as :doc:`queries`
describes.

A dynamic mover
---------------

A dynamic mover is an ordinary dynamic body, usually a capsule with its
rotation locked, so it collides with and pushes everything else and is pushed
back. Two joints move it:

- a :class:`~box2d.joint.MoverJoint`, between a static body and the
  character, drives it toward a velocity with at most a given force, set
  separately for x and y. A force on x alone lets the player steer while
  gravity and jumps keep the y axis;
- a :class:`~box2d.joint.PogoJoint` is a spring along a ray cast down from the
  character, which holds it off the ground. Its capsule never touches the
  floor, so it rides over steps and bumps without catching on them.

The pogo is meant to be made again every step, where the ray lands that step,
so the character can stand on a moving platform as readily as on the ground.
Each new pogo starts from the old one's ``impulse`` and ``current_speed``, so
the spring carries on rather than starting over. Box2D pools joints, so making
and destroying one a step costs little.

.. code-block:: python

    world = World()
    ground = world.new_body().static().box(40, 1, offset=(0, -0.5)).build()
    anchor = world.new_body().static().build()
    FOOT = (0, -0.5)  # the capsule's lower centre, in the body's frame
    REST_LENGTH = 0.9

    character = (
        world.new_body().dynamic().position(0, 2).lock_rotation().enable_sleep(False)
        # The joints do the moving, and friction would fight them.
        .capsule(FOOT, (0, 0.5), 0.3, friction=0.0)
        .build()
    )
    mover = world.add_mover_joint(
        anchor, character, max_velocity_force=(70, 0), collide_connected=True
    )


    class Pogo:
        def __init__(self):
            self.joint = None
            self.impulse = self.speed = 0.0

        def update(self):
            if self.joint is not None:
                self.impulse = self.joint.impulse
                self.speed = self.joint.current_speed
                self.joint.destroy()
                self.joint = None
            foot = character.get_world_point(FOOT)
            hits = world.cast_ray(foot, (0, -2 * REST_LENGTH), first_hit_only=True)
            if not hits:
                self.impulse = self.speed = 0.0
                return
            hit = hits[0]
            surface = hit.shape.body
            weight = character.mass * world.gravity.length
            self.joint = world.add_pogo_joint(
                surface,
                character,
                local_anchor_a=surface.get_local_point(hit.point),
                local_anchor_b=FOOT,
                normal=hit.normal,
                rest_length=REST_LENGTH,
                spring_hertz=5.0,
                spring_damping_ratio=0.8,
                max_compression_force=100 * weight,
                max_tension_force=100 * weight,
                impulse=self.impulse,
                velocity=self.speed,
                collide_connected=True,
            )


    pogo = Pogo()

Each step, the pogo is rebuilt and the mover given the velocity wanted. The
character settles with its foot at the pogo's rest length above the ground,
and walks at the speed it is given:

.. code-block:: python

    >>> for _ in range(120):
    ...     pogo.update()
    ...     mover.linear_velocity = (0, 0)
    ...     world.step(1 / 60, 4)
    >>> round(character.position.y, 2), round(pogo.joint.current_length, 2)
    (1.4, 0.9)
    >>> for _ in range(60):
    ...     pogo.update()
    ...     mover.linear_velocity = (3, 0)
    ...     world.step(1 / 60, 4)
    >>> round(character.linear_velocity.x, 2), round(character.position.y, 2)
    (3.0, 1.4)

A full controller adds acceleration and friction, a smaller force budget in
the air, a jump that sets ``max_tension_force`` to zero so the spring does not
pull the character back down, and a check of the ground's slope. The testbed's
`dynamic_mover.py
<https://github.com/giorgosg/box2d-py/blob/main/src/box2d_testbed/dynamic_mover.py>`_
is a port of Box2D's own, written to be copied and changed.
