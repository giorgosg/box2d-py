Body Module
===========

Physical entities in the simulation world.

.. automodule:: box2d.body
   :members: Body, BodyBuilder
   :special-members: __init__

Body Types
---------
.. autoclass:: Body
   :members:
   :undoc-members:

   .. rubric:: Dynamic vs Static

   - ``dynamic()`` - Responds to forces and moves
   - ``kinematic()`` - Moves but unaffected by forces
   - ``static()`` - Fixed position

Body Builder Pattern
--------------------
.. code-block:: python

   body = (
       world.new_body()
       .dynamic()
       .position(1.5, 3.0)
       .mass(10)
       .box_shape(width=2, height=1)
       .build()
   )

Key Methods
----------
.. autoclass:: Body
   :members:
   :exclude-members: __init__

   .. rubric:: Transformations

   - :py:meth:`~box2d.body.Body.position`
   - :py:meth:`~box2d.body.Body.rotation`
   - :py:meth:`~box2d.body.Body.velocity`

Example: Applying Forces
------------------------
.. code-block:: python

   # Apply impulse to center of mass
   body.apply_linear_impulse(Vec2(0, 200))

   # Apply angular torque
   body.apply_torque(50)