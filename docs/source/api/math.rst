Math Module
===========

.. automodule:: box2d.math
   :noindex:

The Math module provides essential types for 2D physics calculations in Box2D. It includes 
vectors, transformations, rotations, matrices, and bounding boxes that form the foundation
of the physics engine.

Key design principles of the Math module:

* **Immutable objects**: Operations return new instances rather than modifying existing ones
* **Pythonic interfaces**: Classes support Python operators, iteration protocols and unpacking
* **Robust calculations**: Handles edge cases safely with proper numerical handling
* **Box2D integration**: All classes provide conversion to and from Box2D's native C++ types

Vec2
----

.. autoclass:: box2d.Vec2
   :members:
   :special-members: __init__
   
Rot
---

.. autoclass:: box2d.Rot
   :members:
   :special-members: __init__

Transform
--------

.. autoclass:: box2d.Transform
   :members:
   :special-members: __init__

ScaledTransform
--------------

.. autoclass:: box2d.ScaledTransform
   :members:
   :special-members: __init__

AABB
----

.. autoclass:: box2d.AABB
   :members:
   :special-members: __init__

Mat22
-----

.. autoclass:: box2d.Mat22
   :members:
   :special-members: __init__

Utility Functions
---------------

.. autofunction:: box2d.math.to_vec2
.. autofunction:: box2d.math.format_num
