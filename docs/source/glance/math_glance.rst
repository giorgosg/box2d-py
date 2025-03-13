Math Module at a Glance
=======================

.. automodule:: box2d.math
   :noindex:

This page provides a structured overview of the Box2D math classes. The math module is designed with several key principles:

- **Immutable objects**: Most classes (Vec2, Rot, Transform, AABB) are immutable - operations return new instances rather than modifying existing ones
- **Vector-like compatibility**: Functions accepting vector arguments can take any iterable with 2 floats (tuples, lists, Vec2, etc.)
- **Pythonic interfaces**: Classes support Python protocols like operators, iteration, and unpacking
- **Box2D integration**: All classes provide seamless conversion to and from Box2D's native types

Vec2
----

An immutable 2D vector class representing points and vectors in 2D space. Supports Python unpacking and can be used anywhere a sequence of 2 floats is expected.

Creation
^^^^^^^^

* ``Vec2(x, y)`` - Create a vector with given components
* ``Vec2.zero()`` - Create a zero vector (0,0)
* ``Vec2.up()`` - Unit vector pointing up (0,1)
* ``Vec2.down()`` - Unit vector pointing down (0,-1)
* ``Vec2.left()`` - Unit vector pointing left (-1,0)
* ``Vec2.right()`` - Unit vector pointing right (1,0)
* ``Vec2.from_angle(angle)`` - Create a unit vector from an angle
* ``Vec2.from_b2Vec2(b2_vec)`` - Create from Box2D's native vector

Properties
^^^^^^^^^^

* ``x, y`` - Component access
* ``as_tuple`` - Get components as tuple (x, y)
* ``length`` - Get vector magnitude
* ``length_squared`` - Get squared magnitude (faster)
* ``angle`` - Get angle in radians
* ``normalized`` - Get unit vector in same direction
* ``inverse`` - Get vector with negated components (-x, -y)
* ``b2Vec2`` - Get Box2D's native vector equivalent
* ``is_finite`` - Check if vector has finite components

Vector Operations
^^^^^^^^^^^^^^^^^

* ``v1 + v2`` - Vector addition
* ``v1 - v2`` - Vector subtraction
* ``v1 * scalar`` - Scalar multiplication
* ``v1 / scalar`` - Scalar division
* ``-v`` - Negation
* ``x, y = vec`` - Unpacking into components
* ``tuple(vec)`` - Convert to tuple
* ``list(vec)`` - Convert to list
* ``normalize()`` - Normalize vector in-place
* ``dot(other)`` - Dot product
* ``cross(other)`` - Cross product (scalar result)
* ``cross_scalar(s, direction)`` - Cross product with scalar
* ``perpendicular(direction)`` - Get perpendicular vector
* ``rotate(angle)`` - Rotate vector by angle
* ``lerp(other, t)`` - Linear interpolation
* ``project(other)`` - Project onto another vector
* ``reject(other)`` - Reject component from another vector
* ``distance_to(other)`` - Distance between vectors

Utility Methods
^^^^^^^^^^^^^^^

* ``is_close(other, tolerance)`` - Check if vectors are close
* ``min(other)`` - Component-wise minimum
* ``max(other)`` - Component-wise maximum
* ``clamp(min_value, max_value)`` - Clamp components to range
* ``multiply_componentwise(other)`` - Component-wise multiplication

Rot
---

Immutable representation of 2D rotation using sine/cosine components for efficient calculations. All rotation operations create new instances rather than modifying existing ones.

Creation
^^^^^^^^

* ``Rot(angle)`` - Create from angle in radians
* ``Rot.identity()`` - Create identity (zero) rotation
* ``Rot.zero()`` - Alias for identity
* ``Rot.from_degrees(degrees)`` - Create from angle in degrees
* ``Rot.from_sincos(s, c)`` - Create from sine and cosine values
* ``Rot.from_b2Rot(b2_rot)`` - Create from Box2D's native rotation

Properties
^^^^^^^^^^

* ``s, c`` - Sine and cosine components
* ``angle`` - Rotation angle in radians
* ``angle_radians`` - Alias for angle
* ``angle_degrees`` - Rotation angle in degrees
* ``as_tuple`` - Get components as tuple (s, c)
* ``b2Rot`` - Get Box2D's native rotation equivalent
* ``x_axis`` - Get rotated X axis as Vec2
* ``y_axis`` - Get rotated Y axis as Vec2
* ``inverse`` - Get inverse rotation

Rotation Operations
^^^^^^^^^^^^^^^^^^^

* ``r1 * r2`` - Compose rotations
* ``r * v`` - Rotate vector
* ``rotate_vector(v)`` - Rotate vector (alternative syntax)
* ``normalize()`` - Normalize rotation components
* ``interpolate(other, t, ccw)`` - Interpolate between rotations

Transform
---------

Immutable transformation combining position and rotation. Performs rotation followed by translation when applied to points.

Creation
^^^^^^^^

* ``Transform(position, rotation)`` - Create with position and rotation (accepts any vector-like object and angle/Rot)
* ``Transform.from_b2Transform(b2_transform)`` - Create from Box2D's native transform

Properties
^^^^^^^^^^

* ``position`` - Translation vector (Vec2)
* ``rotation`` - Rotation component (Rot)
* ``inverse`` - Get inverse transformation
* ``b2Transform`` - Get Box2D's native transform equivalent

Operations
^^^^^^^^^^

* ``t(point)`` - Apply transform to point (calling the transform)
* ``t * point`` - Apply transform to point (multiplication syntax)
* ``t1 * t2`` - Compose transforms

ScaledTransform
---------------

Extended transform with scaling support, primarily for visualization purposes. Applies transformations in the order: Scale → Rotate → Translate.

Creation
^^^^^^^^

* ``ScaledTransform(position, rotation, scale)`` - Create with position, rotation and scale
* ``ScaledTransform.from_transform(transform, scale)`` - Create from Transform and scale

Properties
^^^^^^^^^^

* ``position`` - Translation vector
* ``rotation`` - Rotation component
* ``scale`` - Scale vector (x and y scale)
* ``inverse`` - Get inverse transformation

Operations
^^^^^^^^^^

* ``st(point)`` - Apply scaled transform to point (calling the transform)
* ``st * point`` - Apply scaled transform to point (multiplication syntax)

Mat22
-----

A 2x2 matrix for linear transformations. Used for rotations, scaling, and linear systems.

Creation
^^^^^^^^

* ``Mat22(*args)`` - Create from components
* ``Mat22.identity()`` - Create identity matrix
* ``Mat22.from_angle(angle)`` - Create rotation matrix
* ``Mat22.from_columns(col1, col2)`` - Create from column vectors
* ``Mat22.from_rows(row1, row2)`` - Create from row vectors
* ``Mat22.from_b2Mat22(b2_mat22)`` - Create from Box2D's native matrix

Properties
^^^^^^^^^^

* ``columns`` - Get column vectors tuple
* ``rows`` - Get row vectors tuple
* ``determinant`` - Get matrix determinant
* ``inverse`` - Get inverse matrix
* ``b2Mat22`` - Get Box2D's native matrix equivalent

Operations
^^^^^^^^^^

* ``m * v`` - Apply matrix to vector
* ``m1 * m2`` - Matrix multiplication
* ``transpose()`` - Get transposed matrix
* ``solve(b)`` - Solve linear system A*x = b

AABB
----

Immutable Axis-Aligned Bounding Box for collision detection and spatial queries. Used extensively in the physics engine for broadphase collision detection.

Creation
^^^^^^^^

* ``AABB(lower, upper)`` - Create with lower and upper bounds (accepts any vector-like objects)
* ``AABB.from_points(points)`` - Create from collection of points
* ``AABB.from_b2AABB(b2_aabb)`` - Create from Box2D's native AABB

Properties
^^^^^^^^^^

* ``lower`` - Lower bound (minimum point)
* ``upper`` - Upper bound (maximum point)
* ``center`` - Center point
* ``half_size`` - Half dimensions
* ``width`` - Width (x-span)
* ``height`` - Height (y-span)
* ``is_valid`` - Check if upper ≥ lower
* ``b2AABB`` - Get Box2D's native AABB equivalent

Operations
^^^^^^^^^^

* ``contains(other)`` - Check if contains AABB or point
* ``overlaps(other)`` - Check if overlaps with another AABB
* ``merge(other)`` - Create union with AABB or point
* ``expanded(margin)`` - Create expanded/contracted AABB
* ``translated(offset)`` - Create translated AABB

