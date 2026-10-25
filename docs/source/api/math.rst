Math Module
===========

.. automodule:: box2d.math
   :noindex:

The Math module provides essential types for 2D physics calculations in Box2D. It includes 
vectors, transformations, rotations, matrices, and bounding boxes that form the foundation
of the physics engine.

Key design principles of the Math module:

* **Mostly immutable objects**: Vec2, Rot, Transform and AABB cannot be changed in place, and
  operations return new instances rather than modifying existing ones. Mat22 and
  ScaledTransform can be changed in place.
* **Pythonic interfaces**: Classes support Python operators, iteration protocols and unpacking
* **Robust calculations**: Handles edge cases safely with proper numerical handling
* **Box2D integration**: Vec2, Rot, Transform, AABB and Mat22 convert to and from Box2D's
  native C types. ScaledTransform has no Box2D counterpart.

VectorLike
----------

.. py:class:: VectorLike

   Anything two floats can be read out of -- a :class:`Vec2`, a tuple, a list.
   Every argument that means a point or a direction takes one of these and
   passes it through :class:`Vec2`, rather than requiring one.

   Declared as ``Iterable[float]`` in ``box2d.math``. It is a type alias
   rather than a class, so signatures show it expanded, as
   ``Iterable[float]``; parameter descriptions that name ``VectorLike`` link
   here.

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
---------

.. autoclass:: box2d.Transform
   :members:
   :special-members: __init__

ScaledTransform
---------------

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
-----------------

.. autofunction:: box2d.math.format_num
