Joint Module at a Glance
========================

This page provides a structured overview of the Box2D joint classes and the
definitions they are made from. A joint constrains how two bodies move
relative to each other:

- **Made by the world**: each kind has an ``add_*_joint`` method on the world,
  and ``world.add_joint()`` takes any of the definitions below; a joint is
  never constructed directly
- **Definitions are plain data**: a definition such as ``RevoluteJointDef``
  bundles everything one joint needs. The ``add_*_joint`` methods take its
  fields as keywords, build it, and pass it to ``world.add_joint()``
- **Anchors in either frame**: a definition takes ``local_anchor_a`` and
  ``local_anchor_b``, a point on each body in its own coordinates, or one
  world-space ``anchor`` converted to both
- **Owned by the world**: a joint lives until it, either of its bodies, or the
  world is destroyed, whether or not the caller kept it. ``body.joints`` hands
  back the same objects (:doc:`../guides/lifetime`)

:doc:`../guides/concepts` introduces joints, :doc:`../guides/events` the
events a joint under strain reports, and :doc:`../guides/character_movement`
the mover and pogo joints a character is built from.

===================  ===============================  ======================
Joint                Made by                          Definition
===================  ===============================  ======================
``DistanceJoint``    ``world.add_distance_joint()``   ``DistanceJointDef``
``FilterJoint``      ``world.add_filter_joint()``     ``FilterJointDef``
``MotorJoint``       ``world.add_motor_joint()``      ``MotorJointDef``
``MouseJoint``       ``world.add_mouse_joint()``      ``MouseJointDef``
``MoverJoint``       ``world.add_mover_joint()``      ``MoverJointDef``
``PogoJoint``        ``world.add_pogo_joint()``       ``PogoJointDef``
``PrismaticJoint``   ``world.add_prismatic_joint()``  ``PrismaticJointDef``
``RevoluteJoint``    ``world.add_revolute_joint()``   ``RevoluteJointDef``
``WeldJoint``        ``world.add_weld_joint()``       ``WeldJointDef``
``WheelJoint``       ``world.add_wheel_joint()``      ``WheelJointDef``
===================  ===============================  ======================

Joint
-----

The base of every joint. Every method and property raises ``DestroyedError``
once the joint has been destroyed.

Lifetime and Identity
^^^^^^^^^^^^^^^^^^^^^

* ``joint.destroy()`` - Destroy the joint, waking both its bodies
* ``joint.is_valid`` - Whether the joint is still live, i.e. has not been destroyed
* ``joint.world`` - The world the joint belongs to
* ``joint.user_data`` - Any Python object to keep with the joint
* ``joint.joint_type`` - Box2D's constant for the kind of joint (read-only)
* ``joint.body_a``, ``joint.body_b`` - The two bodies the joint connects

Attachment
^^^^^^^^^^

* ``joint.local_anchor_a``, ``joint.local_anchor_b`` - Get/set where the joint
  attaches to each body, in that body's coordinates
* ``joint.local_frame_a``, ``joint.local_frame_b`` - Get/set each attachment
  as a ``Transform``: the anchor, and the rotation the joint measures its
  angle or axis from
* ``joint.collide_connected`` - Get/set whether the two bodies still collide with each other

Solver
^^^^^^

* ``joint.constraint_tuning`` - Get/set how stiffly the joint is held, as
  ``(hertz, damping_ratio)``; (60.0, 2.0) by default, which looks rigid
* ``joint.constraint_force`` - The force the joint applied in the last step, as a ``Vec2`` (N)
* ``joint.constraint_torque`` - The torque the joint applied in the last step (N·m)
* ``joint.linear_separation`` - How far apart the joint's two anchors have drifted (m)
* ``joint.angular_separation`` - How far the joint has drifted in angle (rad)
* ``joint.wake_bodies()`` - Wake both bodies

Events
^^^^^^

A joint reports itself in ``world.get_joint_events()`` once its force or
torque passes a threshold, which is how a breakable construction finds the
joint about to give.

* ``joint.force_threshold`` - Get/set the force above which the joint reports an event (N)
* ``joint.torque_threshold`` - Get/set the torque above which the joint reports an event (N·m)

DistanceJoint
-------------

Keeps two anchor points a set distance apart, as a rod, a spring, or a rope.

* ``distance.rest_length`` - Get/set the length held, or the spring's rest length (m)
* ``distance.current_length`` - The distance between the anchors now (m)
* ``distance.enable_spring`` - Get/set whether the joint is a spring rather than a rod
* ``distance.spring_hertz`` - Get/set the spring's frequency (Hz)
* ``distance.spring_damping_ratio`` - Get/set the spring's damping ratio
* ``distance.spring_force`` - The force the spring is exerting now (N)
* ``distance.lower_spring_force`` - Get/set the most the spring may pull, as a negative force; 0 makes a strut
* ``distance.upper_spring_force`` - Get/set the most the spring may push; 0 makes a rope
* ``distance.enable_limit`` - Get/set whether the length limits are enforced
* ``distance.lower_limit``, ``distance.upper_limit`` - Get/set the shortest and longest the joint may get (m)
* ``distance.set_limits(lower, upper)`` - Set both limits at once
* ``distance.enable_motor`` - Get/set whether the motor drives the length
* ``distance.target_motor_speed`` - Get/set the speed the motor drives the length towards (m/s)
* ``distance.max_motor_force`` - Get/set the most force the motor may apply (N)
* ``distance.current_motor_force`` - The force the motor applied in the last step (N)

FilterJoint
-----------

Stops two particular bodies colliding with each other, and constrains nothing
else. It has only the members every joint has.

MotorJoint
----------

Drives the motion of body_b relative to body_a, with a velocity drive and a
spring pulling body_b's origin towards body_a's. With zero velocity it acts as
friction, as for a top-down game.

* ``motor.linear_velocity`` - Get/set the relative velocity the drive aims for, as a ``Vec2`` (m/s)
* ``motor.angular_velocity`` - Get/set the relative angular velocity the drive aims for (rad/s)
* ``motor.max_velocity_force`` - Get/set the most force the velocity drive may apply (N)
* ``motor.max_velocity_torque`` - Get/set the most torque the velocity drive may apply (N·m)
* ``motor.linear_hertz`` - Get/set the linear spring's frequency; 0 turns it off
* ``motor.linear_damping_ratio`` - Get/set the linear spring's damping ratio
* ``motor.max_spring_force`` - Get/set the most force the linear spring may apply (N)
* ``motor.angular_hertz`` - Get/set the angular spring's frequency; 0 turns it off
* ``motor.angular_damping_ratio`` - Get/set the angular spring's damping ratio
* ``motor.max_spring_torque`` - Get/set the most torque the angular spring may apply (N·m)

MouseJoint
----------

Drags one body towards a target point that can move, as a mouse drags. It is
built from a motor joint and a kinematic proxy body at the target, so
``body_a`` is the proxy and ``body_b`` the dragged body, and the proxy is
listed in ``world.bodies`` while the joint exists.

* ``mouse.target`` - Get/set the world point the body is pulled towards; setting it wakes the body
* ``mouse.max_force`` - Get/set the most force the pull may apply (N)
* ``mouse.hertz`` - Get/set the pull's stiffness (Hz)
* ``mouse.damping_ratio`` - Get/set the pull's damping ratio
* ``mouse.destroy()`` - Destroy the joint and its proxy body

MoverJoint
----------

Drives a dynamic character, body_b, at a commanded velocity relative to body_a,
usually static.

* ``mover.linear_velocity`` - Get/set the velocity body_b is driven at, relative to body_a (m/s)
* ``mover.max_velocity_force`` - Get/set the most force on each axis, as a
  ``Vec2`` (N); an axis with no force is not driven

PogoJoint
---------

A spring holding a character, body_b, up off the ground it stands on, body_a.
It is meant to be made afresh each step, carrying the last one's ``impulse``
and ``current_speed`` over.

* ``pogo.rest_length`` - Get/set the length the spring settles at (m)
* ``pogo.spring_hertz`` - Get/set the spring's frequency (Hz)
* ``pogo.spring_damping_ratio`` - Get/set the spring's damping ratio
* ``pogo.current_length`` - The spring's length now (m)
* ``pogo.current_speed`` - The spring's internal velocity; the next pogo's ``velocity``
* ``pogo.impulse`` - The spring's internal impulse; the next pogo's ``impulse``

PrismaticJoint
--------------

Lets two bodies slide along one axis, fixed in body_a, without turning
relative to each other.

* ``prismatic.current_translation`` - How far along the axis the joint is now (m)
* ``prismatic.current_speed`` - How fast the joint is sliding now (m/s)
* ``prismatic.enable_limit`` - Get/set whether the translation limits are enforced
* ``prismatic.lower_limit``, ``prismatic.upper_limit`` - Get/set the translation limits (m)
* ``prismatic.set_limits(lower, upper)`` - Set both limits at once
* ``prismatic.enable_motor`` - Get/set whether the motor drives the joint
* ``prismatic.target_motor_speed`` - Get/set the speed the motor drives towards (m/s)
* ``prismatic.max_motor_force`` - Get/set the most force the motor may apply (N)
* ``prismatic.current_motor_force`` - The force the motor applied in the last step (N)
* ``prismatic.enable_spring`` - Get/set whether a spring pulls the joint towards ``target_translation``
* ``prismatic.target_translation`` - Get/set where along the axis the spring pulls towards (m)
* ``prismatic.spring_hertz`` - Get/set the spring's frequency (Hz)
* ``prismatic.spring_damping_ratio`` - Get/set the spring's damping ratio

RevoluteJoint
-------------

Pins two bodies together at a point they both turn about: a hinge.

* ``revolute.current_angle`` - The joint's angle now, between -pi and pi (rad)
* ``revolute.current_speed`` - How fast the joint is turning now (rad/s)
* ``revolute.enable_limit`` - Get/set whether the angle limits are enforced
* ``revolute.lower_limit``, ``revolute.upper_limit`` - Get/set the angle limits (rad)
* ``revolute.set_limits(lower, upper)`` - Set both limits at once
* ``revolute.enable_motor`` - Get/set whether the motor drives the joint
* ``revolute.target_motor_speed`` - Get/set the speed the motor drives towards (rad/s)
* ``revolute.max_motor_torque`` - Get/set the most torque the motor may apply (N·m)
* ``revolute.current_motor_torque`` - The torque the motor applied in the last step (N·m)
* ``revolute.enable_spring`` - Get/set whether a spring pulls the joint towards ``target_angle``
* ``revolute.target_angle`` - Get/set the angle the spring pulls towards (rad)
* ``revolute.spring_hertz`` - Get/set the spring's frequency (Hz)
* ``revolute.spring_damping_ratio`` - Get/set the spring's damping ratio

WeldJoint
---------

Holds two bodies rigidly together, or with some give when its springs are set.

* ``weld.linear_hertz`` - Get/set the stiffness of the linear give; 0 is rigid
* ``weld.linear_damping_ratio`` - Get/set the damping of the linear give
* ``weld.angular_hertz`` - Get/set the stiffness of the angular give; 0 is rigid
* ``weld.angular_damping_ratio`` - Get/set the damping of the angular give

WheelJoint
----------

A sliding axis with a spring, fixed in body_a, about which body_b turns
freely: a wheel on its suspension.

* ``wheel.enable_spring`` - Get/set whether the suspension spring is active
* ``wheel.spring_hertz`` - Get/set the suspension's frequency (Hz)
* ``wheel.spring_damping_ratio`` - Get/set the suspension's damping ratio
* ``wheel.enable_limit`` - Get/set whether the translation limits are enforced
* ``wheel.lower_limit``, ``wheel.upper_limit`` - Get/set the translation limits along the axis (m)
* ``wheel.set_limits(lower, upper)`` - Set both limits at once
* ``wheel.enable_motor`` - Get/set whether the motor spins the wheel
* ``wheel.target_motor_speed`` - Get/set the speed the motor spins the wheel towards (rad/s)
* ``wheel.max_motor_torque`` - Get/set the most torque the motor may apply (N·m)
* ``wheel.current_motor_torque`` - The torque the motor applied in the last step (N·m)

JointDef
--------

The fields every definition but ``MouseJointDef`` shares, before its own.
Definitions have slots, so assigning a field one does not have raises
``AttributeError``. A field left None takes Box2D's default.

* ``JointDef(body_a, body_b, local_anchor_a=None, local_anchor_b=None, anchor=None, collide_connected=False)`` - The shared fields, in order
* ``body_a``, ``body_b`` - The two bodies to connect
* ``local_anchor_a``, ``local_anchor_b`` - Where the joint attaches to each body, in its own coordinates; the origin if None
* ``anchor`` - A world point converted to both local anchors; give this or them, not both
* ``collide_connected`` - Whether the two bodies still collide with each other (default False)
* ``JointDef.joint_class`` - The joint class a definition makes
* ``joint_def.resolved_anchors()`` - The two local anchors, with ``anchor`` converted
* ``joint_def.joint_arguments()`` - The keywords ``world.add_joint()`` makes the joint with

DistanceJointDef
----------------

* ``DistanceJointDef(body_a, body_b, ...)`` - The shared fields, then these
* ``rest_length`` - The length to hold; the anchors' distance apart if None
* ``enable_spring`` - Make a spring rather than a rod
* ``spring_hertz``, ``spring_damping_ratio`` - The spring's frequency and damping ratio
* ``lower_spring_force``, ``upper_spring_force`` - The most the spring may pull and push
* ``enable_limit`` - Enforce the length limits
* ``lower_limit``, ``upper_limit`` - The shortest and longest the joint may get
* ``enable_motor`` - Drive the length with the motor
* ``target_motor_speed`` - The speed the motor drives towards (m/s)
* ``max_motor_force`` - The most force the motor may apply (N)

FilterJointDef
--------------

* ``FilterJointDef(body_a, body_b, ...)`` - Only the bodies are used; the
  anchors and ``collide_connected`` are ignored

MotorJointDef
-------------

The anchors are ignored: a motor joint works between the bodies' origins.

* ``MotorJointDef(body_a, body_b, ...)`` - The shared fields, then these
* ``linear_velocity``, ``angular_velocity`` - The relative velocities the drive aims for
* ``max_velocity_force``, ``max_velocity_torque`` - The most the velocity drive may apply
* ``linear_hertz``, ``linear_damping_ratio`` - The linear spring; 0 hertz turns it off
* ``max_spring_force`` - The most force the linear spring may apply
* ``angular_hertz``, ``angular_damping_ratio`` - The angular spring; 0 hertz turns it off
* ``max_spring_torque`` - The most torque the angular spring may apply

MouseJointDef
-------------

Connects one body to a point, so it has none of ``JointDef``'s fields.

* ``MouseJointDef(body, target, max_force=1000.0, damping_ratio=0.7, hertz=5.0)`` - A drag of ``body`` towards ``target``
* ``body`` - The body to drag
* ``target`` - The world point to pull it towards
* ``max_force`` - The most force the pull may apply (N)
* ``damping_ratio`` - The pull's damping ratio
* ``hertz`` - The pull's stiffness (Hz)
* ``MouseJointDef.joint_class`` - ``MouseJoint``
* ``mouse_def.joint_arguments()`` - The keywords ``world.add_joint()`` makes the joint with

MoverJointDef
-------------

The anchors are ignored: a mover joint drives velocity only.

* ``MoverJointDef(body_a, body_b, ...)`` - The shared fields, then these
* ``linear_velocity`` - The velocity to drive body_b at, relative to body_a
* ``max_velocity_force`` - The most force on each axis, as a vector-like

PogoJointDef
------------

body_a is the ground and body_b the character; ``local_anchor_a`` is where the
spring touches the ground, and ``local_anchor_b`` where it meets the character.

* ``PogoJointDef(body_a, body_b, ...)`` - The shared fields, then these
* ``normal`` - The ground normal at the contact, in world coordinates; straight up if None
* ``spring_hertz``, ``spring_damping_ratio`` - The spring's frequency and damping ratio
* ``rest_length`` - The length the spring settles at
* ``max_tension_force`` - How hard the spring may pull the character down; 0 while jumping
* ``max_compression_force`` - How hard the spring may push the character up
* ``impulse``, ``velocity`` - The last pogo's ``impulse`` and ``current_speed``, to carry on from

PrismaticJointDef
-----------------

* ``PrismaticJointDef(body_a, body_b, ...)`` - The shared fields, then these
* ``axis`` - The sliding axis, in body_a's coordinates (default (1, 0))
* ``reference_angle`` - body_b's angle less body_a's, held fixed (default 0)
* ``enable_limit`` - Enforce the translation limits
* ``lower_limit``, ``upper_limit`` - The translation limits
* ``enable_motor`` - Drive the joint with the motor
* ``target_motor_speed`` - The speed the motor drives towards (m/s)
* ``max_motor_force`` - The most force the motor may apply (N)
* ``enable_spring`` - Pull the joint towards ``target_translation`` with a spring
* ``target_translation`` - Where along the axis the spring pulls towards
* ``spring_hertz``, ``spring_damping_ratio`` - The spring's frequency and damping ratio

RevoluteJointDef
----------------

* ``RevoluteJointDef(body_a, body_b, ...)`` - The shared fields, then these
* ``reference_angle`` - The angle between the bodies at which the joint reads zero
* ``enable_limit`` - Enforce the angle limits
* ``lower_limit``, ``upper_limit`` - The angle limits (rad)
* ``enable_motor`` - Drive the joint with the motor
* ``target_motor_speed`` - The speed the motor drives towards (rad/s)
* ``max_motor_torque`` - The most torque the motor may apply (N·m)
* ``enable_spring`` - Pull the joint towards ``target_angle`` with a spring
* ``target_angle`` - The angle the spring pulls towards (rad)
* ``spring_hertz``, ``spring_damping_ratio`` - The spring's frequency and damping ratio

WeldJointDef
------------

* ``WeldJointDef(body_a, body_b, ...)`` - The shared fields, then these
* ``reference_angle`` - The angle between the bodies at which the joint rests
* ``linear_hertz``, ``linear_damping_ratio`` - The linear give; 0 hertz is rigid
* ``angular_hertz``, ``angular_damping_ratio`` - The angular give; 0 hertz is rigid

WheelJointDef
-------------

* ``WheelJointDef(body_a, body_b, ...)`` - The shared fields, then these
* ``axis`` - The suspension axis, in body_a's coordinates (default (1, 0))
* ``enable_spring`` - Make the suspension springy
* ``spring_hertz``, ``spring_damping_ratio`` - The suspension's frequency and damping ratio
* ``enable_limit`` - Enforce the translation limits
* ``lower_limit``, ``upper_limit`` - The translation limits along the axis
* ``enable_motor`` - Spin the wheel with the motor
* ``target_motor_speed`` - The speed the motor spins it towards (rad/s)
* ``max_motor_torque`` - The most torque the motor may apply (N·m)

Examples
--------

A pendulum on a hinge, and a wheel on a sprung axle:

.. code-block:: python

    from box2d import World

    world = World(gravity=(0, -10))
    ground = world.new_body().static().box(40, 1).build()

    # A hinge at a world point, with a limit on how far it swings
    bob = world.new_body().dynamic().position(3, 8).circle(0.5).build()
    hinge = world.add_revolute_joint(
        ground, bob, anchor=(0, 8),
        enable_limit=True, lower_limit=-1.0, upper_limit=1.0,
    )

    # A car body on a wheel, sprung along the vertical axis and driven by a motor
    car = world.new_body().dynamic().position(-5, 2).box(2, 0.5).build()
    tyre = world.new_body().dynamic().position(-5.5, 1.3).circle(0.4, friction=0.9).build()
    axle = world.add_wheel_joint(
        car, tyre, anchor=tyre.position, axis=(0, 1),
        enable_spring=True, spring_hertz=4, spring_damping_ratio=0.7,
        enable_motor=True, target_motor_speed=-5, max_motor_torque=20,
    )

    for _ in range(120):
        world.step(1 / 60, 4)
    print(f"hinge at {hinge.current_angle:.2f} rad, car at x = {car.position.x:.1f}")

The same hinge from a definition, and a joint's settings read and changed
once it is made:

.. code-block:: python

    >>> from box2d import RevoluteJointDef
    >>> door = world.new_body().dynamic().position(8, 3).box(0.2, 4).build()
    >>> definition = RevoluteJointDef(ground, door, anchor=(8, 1))
    >>> door_hinge = world.add_joint(definition)
    >>> door_hinge.body_b is door, door_hinge in door.joints
    (True, True)
    >>> door_hinge.local_anchor_b
    Vec2(0.0, -2.0)
    >>> door_hinge.enable_motor = True
    >>> door_hinge.target_motor_speed = 1.5
    >>> round(door_hinge.target_motor_speed, 2)
    1.5
