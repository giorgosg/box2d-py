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

VectorLike
----------

.. py:class:: VectorLike

   Anything two floats can be read out of -- a :class:`Vec2`, a tuple, a list.
   Every argument that means a point or a direction takes one of these and
   passes it through :class:`Vec2`, rather than requiring one.

   Declared as ``Iterable[float]`` in ``box2d.math``. It is a type alias
   rather than a class, and is documented here because the signatures below
   are full of it.

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
