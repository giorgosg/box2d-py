import math
from typing import Union, Iterable, TypeAlias, Protocol, runtime_checkable, Iterator
from ._box2d import ffi, lib


@runtime_checkable
class VectorLike(Protocol):
    """
    A protocol representing a vector-like object.

    A vector-like object must:
      - Support indexing via __getitem__ (for indices 0 and 1) returning a float.
      - Be iterable, yielding floats.
      - Have a length of exactly 2.
    """

    # fmt: off
    def __getitem__(self, index: int) -> float: ...

    def __iter__(self) -> Iterator[float]: ...

    def __len__(self) -> int: ...
    # fmt: on


def ensure_two_elements(vec: VectorLike) -> None:
    """Raise a ValueError if 'vec' does not have exactly 2 elements."""
    if len(vec) != 2:
        raise ValueError(f"VectorLike must have exactly 2 elements, got {len(vec)}.")


def to_vec2(vec: VectorLike) -> "Vec2":
    """
    Convert a VectorLike object into a Vec2 instance, checking that it has exactly 2 elements.
    If 'vec' is already a Vec2, it is returned as is.
    """
    if isinstance(vec, Vec2):
        return vec
    ensure_two_elements(vec)
    return Vec2(vec[0], vec[1])


def format_num(n: float) -> str:
    """
    Format a float with 3 decimal places but trim trailing zeros.

    Args:
        n (float): The number to format.

    Returns:
        str: The formatted number as a string.
    """
    s = f"{n:.3f}".rstrip("0").rstrip(".")
    return f"{s}.0" if "." not in s else s


class Vec2:
    """2D vector with Box2D math operations.

    .. glossary::
        :sorted:

        *vector-like*
            Any object that is indexable (with [0] and [1]), iterable (yielding
            floats), and of length 2 (tuples, lists, numpy arrays, other Vec2 instances, etc.)

    Features:
        - Component-wise operations
        - Tuple interoperability (+, -, etc.)
        - Rotation and projection operations
        - Factory methods for common vectors (Zero, Right, Left, etc.)

    Example:
        >>> v = Vec2(1, 2)
        >>> v.x
        1.0
    """

    __slots__ = ("_x", "_y")

    def __init__(self, x, y):
        """Initialize a 2D vector with the given components.

        Args:
            x (float): The x-component of the vector.
            y (float): The y-component of the vector.

        Returns:
            Vec2: A new instance of Vec2 with the specified components.
        """
        self._x = float(x)
        self._y = float(y)

    @property
    def x(self):
        """The x-component of the vector as a float."""
        return self._x

    @property
    def y(self):
        """The y-component of the vector as a float."""
        return self._y

    @classmethod
    def from_b2Vec2(cls, b2_vec):
        """Create from Box2D b2Vec2 structure.

        Example:
            >>> vec_c = ffi.new("b2Vec2*", (1.5, 2.5))
            >>> Vec2.from_b2Vec2(vec_c)
            Vec2(1.5, 2.5)
        """
        return cls(b2_vec.x, b2_vec.y)

    @property
    def b2Vec2(self):
        """Box2D b2Vec2 equivalent (managed by FFI).

        Example:
            >>> cv = Vec2(1.5, 2.5).b2Vec2
            >>> cv.x
            1.5
            >>> cv.y
            2.5
        """
        vec = ffi.new("b2Vec2*")
        vec.x = self.x
        vec.y = self.y
        return vec

    @classmethod
    def zero(cls):
        """Create a zero vector (0,0).

        Returns:
            Vec2: A zero vector instance.

        Example:
            >>> Vec2.zero()
            Vec2(0.0, 0.0)
        """
        return cls(0.0, 0.0)

    @classmethod
    def right(cls):
        """Create a right-pointing vector (1,0).

        Returns:
            Vec2: A right vector instance.

        Example:
            >>> Vec2.right()
            Vec2(1.0, 0.0)
        """
        return cls(1.0, 0.0)

    @classmethod
    def left(cls):
        """Create a left-pointing vector (-1,0).

        Returns:
            Vec2: A left vector instance.

        Example:
            >>> Vec2.left()
            Vec2(-1.0, 0.0)
        """
        return cls(-1.0, 0.0)

    @classmethod
    def up(cls):
        """Create an up-pointing vector (0,1).

        Returns:
            Vec2: An up vector instance.

        Example:
            >>> Vec2.up()
            Vec2(0.0, 1.0)
        """
        return cls(0.0, 1.0)

    @classmethod
    def down(cls):
        """Create a down-pointing vector (0,-1).

        Returns:
            Vec2: A down vector instance.

        Example:
            >>> Vec2.down()
            Vec2(0.0, -1.0)
        """
        return cls(0.0, -1.0)

    @classmethod
    def from_angle(cls, angle):
        """Create a unit vector from the given angle in radians.

        Args:
            angle (float): The angle in radians.

        Returns:
            Vec2: A unit vector instance.

        Example:
            >>> Vec2.from_angle(math.pi/2)
            Vec2(0.0, 1.0)
        """
        return cls(math.cos(angle), math.sin(angle))

    @property
    def is_finite(self):
        """Check if both components are finite numbers.

        Returns:
            bool: True if both components are finite, False otherwise.
        """
        return math.isfinite(self.x) and math.isfinite(self.y)

    def __getitem__(self, index):
        """Allow indexing to access vector components.

        Args:
            index (int): The index of the component to access (0 for x, 1 for y).

        Returns:
            float: The value of the component at the specified index.

        Raises:
            IndexError: If the index is out of range.

        Example:
            >>> v = Vec2(1.0, 2.0)
            >>> v[0]
            1.0
            >>> v[1]
            2.0
        """
        if index == 0:
            return self.x
        elif index == 1:
            return self.y
        raise IndexError("Index out of range. Must be 0 or 1.")

    def __len__(self):
        """Return the number of components in the vector.

        Returns:
            int: The number of components (always 2 for a 2D vector).
        """
        return 2

    def __iter__(self):
        """Allow tuple unpacking of the vector components.

        Yields:
            float: The x-component, followed by the y-component.

        Example:
            >>> x, y = Vec2(1.0, 2.0)
            >>> x
            1.0
            >>> y
            2.0
        """
        yield self.x
        yield self.y

    def __eq__(self, other: VectorLike) -> bool:
        """
        Check if this vector is equal to another vector or tuple.

        The parameter is first converted to a Vec2 using `to_vec2`. If conversion fails,
        the method returns False.
        """
        try:
            other_vec = to_vec2(other)
        except (TypeError, ValueError):
            return False
        return self.x == other_vec.x and self.y == other_vec.y

    def is_close(self, other: VectorLike, tolerance: float = 1e-6) -> bool:
        """
        Check if this vector is approximately equal to another vector-like object.

        The parameter is first converted via `to_vec2`.
        """
        try:
            other_vec = to_vec2(other)
        except (TypeError, ValueError):
            return False
        return (
            abs(self.x - other_vec.x) <= tolerance
            and abs(self.y - other_vec.y) <= tolerance
        )

    def __add__(self, other: VectorLike) -> "Vec2":
        """Return the component-wise addition of this vector and another."""
        other = to_vec2(other)
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: VectorLike) -> "Vec2":
        """Return the component-wise difference between this vector and another."""
        other = to_vec2(other)
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vec2":
        """Return the product of this vector and a scalar."""
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        return Vec2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> "Vec2":
        """Return the scalar multiplication from the left-hand side."""
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> "Vec2":
        """Return the vector divided by a scalar."""
        if scalar == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        return Vec2(self.x / scalar, self.y / scalar)

    def __neg__(self) -> "Vec2":
        """Return the negated vector."""
        return Vec2(-self.x, -self.y)

    def __repr__(self) -> str:
        """Return a string representation of the vector."""
        formatted_x, formatted_y = [format_num(v) for v in self]
        return f"Vec2({formatted_x}, {formatted_y})"

    def __hash__(self) -> int:
        """Return the hash value of the vector."""
        return hash((self.x, self.y))

    def __lt__(self, other: VectorLike) -> bool:
        """Return True if this vector is component-wise less than the other."""
        other = to_vec2(other)
        return self.x < other.x and self.y < other.y

    def __le__(self, other: VectorLike) -> bool:
        """Return True if this vector is component-wise less than or equal to the other."""
        other = to_vec2(other)
        return self.x <= other.x and self.y <= other.y

    def __ge__(self, other: VectorLike) -> bool:
        """Return True if this vector is component-wise greater than or equal to the other."""
        other = to_vec2(other)
        return self.x >= other.x and self.y >= other.y

    def __gt__(self, other: VectorLike) -> bool:
        """Return True if this vector is component-wise greater than the other."""
        other = to_vec2(other)
        return self.x > other.x and self.y > other.y

    def __bool__(self) -> bool:
        """Return True if the vector is non-zero."""
        return self.x != 0.0 or self.y != 0.0

    def __round__(self, ndigits: int = None) -> "Vec2":
        """
        Return a new Vec2 instance with each component rounded to the specified number of digits.

        Args:
            ndigits (int, optional): Number of digits to round to. If None, rounds to the nearest integer.

        Returns:
            Vec2: A new vector with rounded components.

        Example:
            >>> v = Vec2(1.23456, 7.89123)
            >>> round(v, 2)
            Vec2(1.23, 7.89)
        """
        return Vec2(round(self.x, ndigits), round(self.y, ndigits))

    @property
    def as_tuple(self) -> tuple[float, float]:
        """Return the vector as a tuple of floats.

        Returns:
            tuple: A tuple containing the x and y components of the vector.
        """
        return (self.x, self.y)

    @property
    def length(self) -> float:
        """The Euclidean length (magnitude) of the vector.

        Returns:
            float: The length of the vector.

        Example:
            >>> Vec2(3.0, 4.0).length
            5.0
        """
        return math.hypot(self.x, self.y)

    @property
    def length_squared(self) -> float:
        """The square of the Euclidean length of the vector.

        Returns:
            float: The squared length of the vector.

        Example:
            >>> Vec2(3.0, 4.0).length_squared
            25.0
        """
        return self.x**2 + self.y**2

    def dot(self, other: VectorLike) -> float:
        """Compute the dot product with another vector-like object."""
        other = to_vec2(other)
        return self.x * other.x + self.y * other.y

    def cross(self, other: VectorLike) -> float:
        """Compute the 2D cross product (a scalar) with another vector-like object."""
        other = to_vec2(other)
        return self.x * other.y - self.y * other.x

    def normalize(self) -> "Vec2":
        """Return a unit vector in the direction of this vector.

        Returns:
            Vec2: A unit vector if the length is non-zero; otherwise, a zero vector.

        Example:
            >>> Vec2(3.0, 4.0).normalize()
            Vec2(0.6, 0.8)
        """
        length = self.length
        if length == 0:
            return Vec2(0.0, 0.0)
        return Vec2(self.x / length, self.y / length)

    @property
    def angle(self) -> float:
        """Return the angle of the vector in radians.

        Returns:
            float: The angle in radians, computed using math.atan2(y, x).

        Example:
            >>> Vec2(1.0, 1.0).angle
            0.7853981633974483
        """
        return math.atan2(self.y, self.x)

    def project(self, other: VectorLike) -> "Vec2":
        """
        Project this vector onto another vector-like object.

        Raises:
            ValueError: If the other vector is the zero vector.
        """
        other = to_vec2(other)
        dot_product = self.dot(other)
        other_dot = other.dot(other)
        if other_dot == 0:
            raise ValueError("Cannot project onto the zero vector.")
        scalar = dot_product / other_dot
        return Vec2(scalar * other.x, scalar * other.y)

    def reject(self, other: VectorLike) -> "Vec2":
        """Return the component of this vector perpendicular to another vector-like object."""
        return self - self.project(other)

    def lerp(self, other: VectorLike, t: float) -> "Vec2":
        """
        Linearly interpolate between this vector and another vector-like object.

        Args:
            t (float): Interpolation factor (typically between 0 and 1).
        """
        other = to_vec2(other)
        return self + (other - self) * t

    def perpendicular(self, direction="right") -> "Vec2":
        """
        Return a perpendicular vector.

        Args:
            direction (str, optional): 'right' returns (y, -x), 'left' returns (-y, x).

        Raises:
            ValueError: If the direction is not 'left' or 'right'.
        """
        if direction == "right":
            return Vec2(self.y, -self.x)
        elif direction == "left":
            return Vec2(-self.y, self.x)
        else:
            raise ValueError("Direction must be 'left' or 'right'")

    def min(self, other: VectorLike) -> "Vec2":
        """Return the component-wise minimum comparing this vector and another."""
        other = to_vec2(other)
        return Vec2(min(self.x, other.x), min(self.y, other.y))

    def max(self, other: VectorLike) -> "Vec2":
        """Return the component-wise maximum comparing this vector and another."""
        other = to_vec2(other)
        return Vec2(max(self.x, other.x), max(self.y, other.y))

    def clamp(self, min_value: VectorLike, max_value: VectorLike) -> "Vec2":
        """
        Clamp this vector within a specified range.

        The inputs `min_value` and `max_value` are each converted to a Vec2.
        """
        return self.max(min_value).min(max_value)

    @property
    def heading(self) -> "Vec2":
        """Return the normalized (heading) vector."""
        return self.normalize()

    @property
    def inverse(self) -> "Vec2":
        """Return a new vector which is the component-wise inverse (negation)."""
        return -self

    def rotate(self, angle: float) -> "Vec2":
        """Rotate the vector by the given angle in radians."""
        new_x = self.x * math.cos(angle) - self.y * math.sin(angle)
        new_y = self.x * math.sin(angle) + self.y * math.cos(angle)
        return Vec2(new_x, new_y)

    def multiply_componentwise(self, other: VectorLike) -> "Vec2":
        """Multiply this vector with another vector-like object component-wise."""
        other = to_vec2(other)
        return Vec2(self.x * other.x, self.y * other.y)

    def cross_scalar(self, s: float, direction: str = "right") -> "Vec2":
        """
        Compute the cross product with a scalar following Box2D conventions.

        Args:
            s (float): The scalar multiplier.
            direction (str, optional): 'right' (default) or 'left'.
        """
        if direction == "right":
            return Vec2(s * self.y, -s * self.x)
        return Vec2(-s * self.y, s * self.x)

    def distance_to(self, other: VectorLike) -> float:
        """Calculate the Euclidean distance between this vector and another vector-like object."""
        other = to_vec2(other)
        return (self - other).length


class Rot:
    """
    2D rotation represented by cosine and sine components.

    Provides common rotation operations and conversions.

    Features:
    - Angle conversions (radians/degrees)
    - Rotation composition via multiplication
    - Vector rotation via multiplication
    - Axis access (x_axis/y_axis properties)
    - Normalization and inversion

    Example:
        >>> deg_90 = Rot(math.pi/2)
        >>> v = Vec2(1, 0)
        >>> deg_90 * v
        Vec2(0.0, 1.0)
    """

    __slots__ = ("_s", "_c")  # sin/cos storage like Box2D

    def __init__(self, angle_radians=0.0):
        """
        Initialize from rotation angle in radians.

        Args:
            angle_radians (float): Initial angle in radians. Defaults to 0.0.

        Example:
            >>> r = Rot(math.pi/2)
            >>> r.c, r.s
            (6.123233995736766e-17, 1.0)
        """
        self._c = math.cos(angle_radians)
        self._s = math.sin(angle_radians)

    @property
    def c(self):
        """**Cosine** component of rotation (read-only).

        Example:
            >>> print(f"{Rot(math.pi/2).c:.1f}")
            0.0
        """
        return self._c

    @property
    def s(self):
        """**Sine** component of rotation (read-only).

        Example:
            >>> Rot(0).s
            0.0
        """
        return self._s

    @classmethod
    def from_b2Rot(cls, b2_rot):
        """Create a Rot instance from Box2D's b2Rot structure.

        Args:
            b2_rot: FFI pointer to b2Rot C struct

        Example:
            >>> rot_c = ffi.new("b2Rot*", (Rot(math.pi/2).c, Rot(math.pi/2).s))
            >>> Rot.from_b2Rot(rot_c).angle_degrees
            90.0
        """
        return cls.from_sincos(b2_rot.s, b2_rot.c)

    @property
    def b2Rot(self):
        """Box2D b2Rot equivalent (managed by FFI).

        Example:
            >>> rot = Rot(math.pi/4)
            >>> cr = rot.b2Rot
            >>> cr.s, cr.c
            (0.7071067690849304, 0.7071067690849304)
        """
        rot = ffi.new("b2Rot*")
        rot.s = self.s
        rot.c = self.c
        return rot

    @classmethod
    def from_sincos(cls, s: float, c: float) -> "Rot":
        """
        Create rotation directly from sine/cosine values.

        Args:
            s (float): Sine component
            c (float): Cosine component

        Returns:
            Rot: New unnormalized rotation

        Example:
            >>> r = Rot.from_sincos(0, 1)
            >>> r.angle_radians
            0.0
        """
        inst = cls(0)
        inst._s = s
        inst._c = c
        return inst

    @classmethod
    def from_degrees(cls, degrees: float) -> "Rot":
        """Create a Rot instance from an angle in degrees.

        Args:
            degrees (float): The angle in degrees.

        Returns:
            Rot: New rotation instance

        Example:
            >>> r = Rot.from_degrees(90)
            >>> r.angle_degrees
            90.0
        """
        return cls(math.radians(degrees))

    @property
    def angle_radians(self) -> float:
        """
        Rotation angle in radians [-π, π].

        Returns:
            float: Angle calculated via atan2(s, c)

        Example:
            >>> Rot(math.pi).angle_radians
            3.141592653589793
        """
        return math.atan2(self.s, self.c)

    @property
    def angle_degrees(self) -> float:
        """
        Rotation angle in degrees [-180, 180].

        Returns:
            float: Angle converted to degrees

        Example:
            >>> Rot(math.pi/2).angle_degrees
            90.0
        """
        return math.degrees(self.angle_radians)

    @property
    def x_axis(self) -> Vec2:
        """
        Get rotated X-axis (first column of rotation matrix).

        Returns:
            Vec2: Unit vector (c, s)

        Example:
            >>> Rot(0).x_axis
            Vec2(1.0, 0.0)
            >>> Rot(math.pi/2).x_axis
            Vec2(0.0, 1.0)
        """
        return Vec2(self.c, self.s)

    @property
    def y_axis(self) -> Vec2:
        """
        Get rotated Y-axis (second column of rotation matrix).

        Returns:
            Vec2: Unit vector (-s, c)

        Example:
            >>> Rot(0).y_axis
            Vec2(-0.0, 1.0)
            >>> Rot(math.pi/2).y_axis
            Vec2(-1.0, 0.0)
        """
        return Vec2(-self.s, self.c)

    @property
    def as_tuple(self) -> tuple[float, float]:
        """
        Return the rotation as a tuple of sine and cosine components.

        Returns: A tuple containing the sine and cosine components of the rotation.

        Example:
            >>> s, c = Rot(math.pi/2).as_tuple
            >>> s == 1.0
            True
            >>> round(c, 6) == 0.0
            True
        """
        return (self.s, self.c)

    def __mul__(self, other: Union["Vec2", "Rot", float]) -> Union["Vec2", "Rot"]:
        """
        Multiply the rotation with:
            - A vector: rotates the vector.
            - Another rotation: composes the rotations.
            - A float: produces a Vec2 in the direction of this rotation
              with a magnitude equal to the float.

        Args:
            other (Vec2 | Rot | float): The operand to multiply.

        Returns:
            Vec2 | Rot: If other is a Vec2, returns the rotated vector.
                        If other is a Rot, returns the composed rotation.
                        If other is a float (or int), returns a Vec2 representing
                        a unit vector rotated by this rotation and scaled by the float.

        Examples:
            >>> Rot(math.pi/2) * Vec2(1, 0)
            Vec2(0.0, 1.0)
            >>> r1 = Rot(math.pi/2)
            >>> r2 = Rot(math.pi/2)
            >>> (r1 * r2).angle_degrees
            180.0
            >>> Rot(math.pi/4) * 5
            Vec2(3.536, 3.536)
        """
        if isinstance(other, (int, float)):
            return Vec2(self.c * other, self.s * other)
        if isinstance(other, Vec2):
            return self.rotate_vector(other)
        if isinstance(other, Rot):
            # Rotation composition (b2Rot_Mul)
            return Rot.from_sincos(
                self.s * other.c + self.c * other.s, self.c * other.c - self.s * other.s
            )
        return NotImplemented

    def __rmul__(self, other: Union["Vec2", tuple, float]) -> "Vec2":
        """
        Handle multiplication when a vector, tuple, or float appears on the left-hand side.

        If the left operand is a vector or tuple, it rotates the vector.
        If the left operand is a float (or int), it returns a Vec2 in the direction of this rotation
        with its magnitude scaled by the float.

        Args:
            other (Vec2 | tuple | float): The left-hand operand.

        Returns:
            Vec2: The resulting rotated vector or scaled unit vector.

        Examples:
            >>> 5 * Rot(math.pi/4)
            Vec2(3.536, 3.536)
            >>> Vec2(1, 0) * Rot(math.pi/2)
            Vec2(0.0, 1.0)
        """
        if isinstance(other, (tuple, Vec2)):
            return self.rotate_vector(other)
        return self.__mul__(other)

    def __str__(self):
        """
        Human-readable string representation of rotation components.

        Returns:
            str: String in format 'Rot(c={c:.6f}, s={s:.6f})'

        Example:
            >>> print(Rot(math.pi))
            Rot(c=-1.000000, s=0.000000)
        """
        return f"Rot(c={self.c:.6f}, s={self.s:.6f})"

    def __repr__(self):
        """
        Precise string representation for recreation.

        Returns:
            str: Executable string constructor with angle precision

        Example:
            >>> repr(Rot(math.pi/2))
            'Rot(1.570796)'
        """
        return f"Rot({self.angle_radians:.6f})"

    def __eq__(self, other):
        """
        Exact component equality check between rotations.

        Args:
            other: Rotation to compare with

        Returns:
            bool: True if both c and s components match exactly

        Example:
            >>> Rot(1.0) == Rot(1.0)
            True
            >>> Rot(0.0) == Rot(1.0)
            False
        """
        if isinstance(other, Rot):
            return self.c == other.c and self.s == other.s
        return False

    def __hash__(self):
        """
        Hash value based on rotation components.

        Returns:
            int: Hash of (c, s) tuple

        Example:
            >>> hash(Rot(0.5)) == hash((math.cos(0.5), math.sin(0.5)))
            True
        """
        return hash((self.c, self.s))

    def normalize(self):
        """
        Create normalized rotation with unit-length components.

        Returns:
            Rot: New rotation with same direction but magnitude 1

        Note:
            Handles floating-point imprecision in rotation components

        Example:
            >>> r = Rot.from_sincos(2.0, 3.0).normalize() # Hypothetical non-normalized input
            >>> Vec2(r.c, r.s).length
            1.0
        """
        length = math.hypot(self.c, self.s)
        if length == 0:
            return Rot(0.0)
        c = self.c / length
        s = self.s / length
        return Rot(math.atan2(s, c))

    def __getstate__(self):
        """
        Get serialization state for pickling.

        Returns:
            float: Current angle in radians

        Note:
            Used internally by pickle module
        """
        return self.angle_radians

    def __setstate__(self, state):
        """
        Restore instance state from unpickled data.

        Args:
            state (float): Angle in radians to restore

        Note:
            Used internally by pickle module
        """
        self.__init__(state)

    @classmethod
    def identity(cls):
        """
        Create identity rotation (0 angle, no rotation).

        Returns:
            Rot: Identity rotation equivalent to Rot(0.0)

        Example:
            >>> Rot.identity().angle_degrees
            0.0
        """
        return cls(0.0)

    @classmethod
    def zero(cls):
        """
        Create zero rotation (synonym for Identity).

        Returns:
            Rot: Same as Identity rotation

        Example:
            >>> Rot.zero() == Rot.identity()
            True
        """
        return cls(0.0)

    @property
    def inverse(self):
        """
        Create inverse/opposite rotation.

        Returns:
            Rot: New rotation with negated angle

        Example:
            >>> Rot(math.pi/4).inverse.angle_degrees
            -45.0
        """
        return Rot(-self.angle_radians)

    def interpolate(self, other, t, ccw=True):
        """
        Linearly interpolate between two rotations with a forced direction.

        Args:
            other (Rot): The target rotation.
            t (float): Interpolation factor in the range [0.0, 1.0].
            ccw (bool, optional): If True (default), force counterclockwise interpolation.
                If False, force clockwise interpolation.

        Returns:
            Rot: A new rotation interpolated between self and other.

        Examples:
            >>> Rot(0).interpolate(Rot(math.pi/2), 0.5).angle_degrees
            45.0
            >>> Rot(0).interpolate(Rot(math.pi/2), 0.5, ccw=False).angle_degrees # Clockwise
            -135.0
        """
        a0 = self.angle_radians
        a1 = other.angle_radians

        if ccw:
            if a1 < a0:
                a1 += 2 * math.pi
        else:
            if a1 > a0:
                a1 -= 2 * math.pi

        diff = a1 - a0
        interpolated_angle = a0 + t * diff
        return Rot(interpolated_angle)

    def rotate_vector(self, v: VectorLike) -> Vec2:
        """
        Apply rotation to a vector.

        Args:
            v: Vector-like to rotate (supports any VectorLike input)

        Returns:
            Vec2: Rotated vector

        Example:
            >>> Rot(math.pi/2).rotate_vector(Vec2(1, 0))
            Vec2(0.0, 1.0)
        """
        v = Vec2(*v)
        x = self.c * v.x - self.s * v.y
        y = self.c * v.y + self.s * v.x
        return Vec2(x, y)

    def __call__(self, v: VectorLike) -> Vec2:
        """
        Functional interface for vector rotation.

        Args:
            v (Vec2): Vector to rotate

        Returns:
            Vec2: Rotated vector (same as rotate_vector)

        Example:
            >>> rot = Rot(math.pi)
            >>> rot(Vec2(1, 0))
            Vec2(-1.0, 0.0)
        """
        return self.rotate_vector(v)


class Transform:
    """Represents a 2D transformation combining position and rotation.

    Features:
    - Apply transformations to points (rotate then translate)
    - Calculate inverse transformations
    - Compatible with Box2D's b2Transform structure

    Example:
        >>> t = Transform(Vec2(2, 3), Rot(math.pi/2))
        >>> t(Vec2(1, 0))  # Rotate then translate
        Vec2(2.0, 4.0)
    """

    __slots__ = ("p", "q")

    def __init__(
        self, position: VectorLike = Vec2(0, 0), rotation: Union[float, Rot] = Rot(0)
    ):
        """
        Initialize transformation with position and rotation.

        Args:
            position VectorLike: Translation component
            rotation (Rot | float): Rotation component (accepts angle in radians)

        Example:
            >>> Transform((1, 2), math.pi)
            Transform(p=Vec2(1.0, 2.0), q=Rot(3.141593))
        """
        self.p = position if isinstance(position, Vec2) else Vec2(*position)
        self.q = rotation if isinstance(rotation, Rot) else Rot(rotation)

    @classmethod
    def from_b2Transform(cls, b2_transform):
        """Create Transform from Box2D's b2Transform structure.

        Args:
            b2_transform: FFI pointer to b2Transform C struct

        Example:
            >>> tf_c = ffi.new("b2Transform*", ((1,2), Rot(math.pi/2).b2Rot[0]))
            >>> Transform.from_b2Transform(tf_c)
            Transform(p=Vec2(1.0, 2.0), q=Rot(1.570796))
        """
        p = Vec2.from_b2Vec2(b2_transform.p)
        q = Rot.from_b2Rot(b2_transform.q)
        return cls(p, q)

    @property
    def b2Transform(self):
        """Box2D b2Transform equivalent (managed by FFI).

        Example:
            >>> tf = Transform(Vec2(1,2), Rot(math.pi))
            >>> ct = tf.b2Transform
            >>> ct.p.x, ct.p.y
            (1.0, 2.0)
        """
        transform = ffi.new("b2Transform*")
        transform.p = self.p.b2Vec2[0]
        transform.q = self.q.b2Rot[0]
        return transform

    def __call__(self, point: VectorLike) -> Vec2:
        """
        Apply transformation to a point (rotate then translate).

        Args:
            point (Vec2 | Iterable): Point to transform

        Returns:
            Vec2: Transformed point

        Example:
            >>> Transform(Vec2(1, 1), Rot(0))(Vec2(2, 3))
            Vec2(3.0, 4.0)
        """
        if not isinstance(point, Vec2):
            point = Vec2(*point)
        return self.q * point + self.p

    @property
    def rotation(self) -> Rot:
        """
        Get the rotation component of the transform.

        Returns:
            Rot: Current rotation component
        """
        return self.q

    @property
    def position(self) -> Vec2:
        """
        Get the position component of the transform.
        """
        return self.p

    @property
    def inverse(self) -> "Transform":
        """
        Calculate inverse transformation.

        Returns:
            Transform: Inverse that reverses this transformation

        Note:
            The inverse transform satisfies: t.inverted()(t(p)) == p

        Example:
            >>> t = Transform(Vec2(2, 3), Rot(math.pi/2))
            >>> t_inv = t.inverse
            >>> t_inv(t(Vec2(1, 0)))  # Should return original point
            Vec2(1.0, 0.0)
        """
        inv_rot = Rot.from_sincos(-self.q.s, self.q.c)
        return Transform(inv_rot * (-self.p), inv_rot)

    def __repr__(self):
        """
        Machine-readable representation of the transform.

        Returns:
            str: String that can recreate the transform

        Example:
            >>> repr(Transform(Vec2(1, 2), Rot(0.5)))
            'Transform(p=Vec2(1.0, 2.0), q=Rot(0.500000))'
        """
        return f"Transform(p={self.p!r}, q={self.q!r})"

    def __mul__(self, other: Union["Transform", "ScaledTransform"]) -> "Transform":
        """
        Compose two transformations.

        Args:
            other (Transform): Transformation to compose with

        Returns:
            Transform: Composed transformation
        """
        if isinstance(other, Transform):
            return Transform(self.p + self.q * other.p, self.q * other.q)
        elif isinstance(other, ScaledTransform):
            # Convert base transform to scaled transform and compose
            return ScaledTransform.from_transform(self) * other
        return NotImplemented


class ScaledTransform:
    """A 2D transformation supporting scaling, rotation, and translation.

    Designed for visualization purposes - does not affect Box2D physics calculations.
    Applies transformations in the order: Scale → Rotate → Translate.

    Attributes:
        position (Vec2): Translation component of the transform
        rotation (Rot): Rotation component of the transform
        scale (Vec2): Scaling factors (x, y). Defaults to (1, 1)

    Example:
        >>> t = ScaledTransform(position=(10, 20), rotation=math.pi/2, scale=2)
        >>> t(Vec2(1, 0))  # Scale first, then rotate, then translate
        Vec2(10.0, 22.0)
    """

    __slots__ = ("_position", "_rotation", "_scale", "_matrix", "_inv_matrix")

    def __init__(
        self,
        position: VectorLike = Vec2(0, 0),
        rotation: Union[float, Rot] = Rot(0),
        scale: Union[float, VectorLike] = Vec2(1, 1),
    ):
        """Initialize a scaled transform.

        Args:
            position: Translation offset as Vec2 or tuple. Defaults to (0, 0)
            rotation: Rotation angle (radians) or Rot instance. Defaults to 0
            scale: Scaling factors as Vec2, tuple, or single number for uniform scaling.
                Defaults to (1, 1)

        Note:
            If a single number is provided for scale, it will create uniform scaling
            in both x and y axes.

        Example:
            >>> # Various initialization styles:
            >>> t1 = ScaledTransform()  # Identity transform
            >>> t2 = ScaledTransform(scale=2)  # Uniform scaling
            >>> t3 = ScaledTransform(scale=(1.5, 0.5))  # Non-uniform scaling
        """
        self._position = position if isinstance(position, Vec2) else Vec2(*position)
        self._rotation = rotation if isinstance(rotation, Rot) else Rot(rotation)

        # Handle different scale input types
        if isinstance(scale, (int, float)):
            self._scale = Vec2(scale, scale)
        else:
            self._scale = scale if isinstance(scale, Vec2) else Vec2(*scale)
        self._recalc_matrix()
        self._inv_matrix = None

    def _recalc_matrix(self):
        """
        Recalculate the transformation matrix and store it.

        For demonstration, let's assume our matrix is a 2x3 matrix stored as a tuple:
            (m00, m01, m02, m10, m11, m12)
        where the transformation is applied as:
            newX = m00*x + m01*y + m02
            newY = m10*x + m11*y + m12
        """
        r = self._rotation
        s = self._scale
        t = self._position

        # Construct the combined matrix: Scale → Rotate → Translate.
        m00 = r.c * s.x
        m01 = -r.s * s.y
        m02 = t.x
        m10 = r.s * s.x
        m11 = r.c * s.y
        m12 = t.y

        self._matrix = (m00, m01, m02, m10, m11, m12)

    def __call__(self, point: VectorLike) -> Vec2:
        """Apply the transformation to a point.

        Transformation order:
        1. Scale the point
        2. Apply rotation
        3. Apply translation

        Args:
            point: Vector-like input to transform

        Returns:
            Vec2: Transformed point in world coordinates

        Example:
            >>> t = ScaledTransform(position=(5, 0), rotation=math.pi, scale=2)
            >>> t((1, 1))  # (1*2, 1*2) → rotated 180° → + (5, 0)
            Vec2(3.0, -2.0)
        """
        # point = Vec2(*point)
        ## Apply scaling first
        # scaled = point.multiply_componentwise(self.scale)
        ## Then apply rotation and translation
        # return self.rotation * scaled + self.position

        m00, m01, m02, m10, m11, m12 = self._matrix
        x, y = Vec2(*point)
        new_x = m00 * x + m01 * y + m02
        new_y = m10 * x + m11 * y + m12
        return Vec2(new_x, new_y)

    @property
    def position(self) -> Vec2:
        """Get/set the translation component of the transform.

        Accepts:
            VectorLike: Any tuple/list/Vec2 convertible to Vec2

        Example:
            >>> t = ScaledTransform()
            >>> t.position = (5, 2)
            >>> t.position
            Vec2(5.0, 2.0)
        """
        return self._position

    @position.setter
    def position(self, value: VectorLike):
        self._position = value if isinstance(value, Vec2) else Vec2(*value)
        self._recalc_matrix()
        self._inv_matrix = None

    @property
    def rotation(self) -> Rot:
        """Get/set the rotation component.

        Accepts:
            float: Angle in radians
            Rot: Direct rotation instance

        Example:
            >>> t = ScaledTransform()
            >>> t.rotation = math.pi/2  # Set from angle
            >>> t.rotation = Rot(0)     # Set directly
        """
        return self._rotation

    @rotation.setter
    def rotation(self, value: Union[float, Rot]):
        self._rotation = value if isinstance(value, Rot) else Rot(value)
        self._recalc_matrix()
        self._inv_matrix = None

    @property
    def scale(self) -> Vec2:
        """Get/set the scaling factors.

        Accepts:
            float: Uniform scaling for both axes
            VectorLike: Separate x/y scaling factors

        Example:
            >>> t = ScaledTransform()
            >>> t.scale = 2.5      # Uniform scaling
            >>> t.scale = (1, 0.5) # Non-uniform
        """
        return self._scale

    @scale.setter
    def scale(self, value: Union[float, VectorLike]):
        if isinstance(value, (int, float)):
            self._scale = Vec2(value, value)
        else:
            self._scale = value if isinstance(value, Vec2) else Vec2(*value)
        self._recalc_matrix()
        self._inv_matrix = None

    @classmethod
    def from_transform(
        cls, transform: Transform, scale: Union[float, VectorLike] = 1.0
    ) -> "ScaledTransform":
        """Create a ScaledTransform from a base Transform and optional scaling.

        Args:
            transform: Base Transform containing position and rotation
            scale: Scaling factor(s). Defaults to 1.0 (no scaling)

        Example:
            >>> base = Transform(Vec2(2,3), Rot(math.pi/2))
            >>> st = ScaledTransform.from_transform(base, scale=2)
            >>> st.position == base.position
            True
            >>> st.rotation == base.rotation
            True
        """
        if isinstance(scale, (int, float)):
            scale_vec = Vec2(scale, scale)
        else:
            scale_vec = Vec2(*scale)

        return cls(transform.position, transform.rotation, scale_vec)

    @property
    def inverse(self) -> "ScaledTransform":
        """Calculate inverse transformation that reverses this transformation.

        Returns:
            ScaledTransform: Inverse that satisfies inverse(t(p)) == p

        Note:
            Handles non-uniform scaling and rotation correctly
            Will raise ValueError if any scale component is zero

        Example:
            >>> t = ScaledTransform(Vec2(2,3), Rot(math.pi/2), scale=2)
            >>> t_inv = t.inverse
            >>> t_inv(t(Vec2(1, 0)))  # Should return original point
            Vec2(1.0, 0.0)
        """
        if self._inv_matrix is not None:
            return self._inv_matrix

        inv_scale = Vec2(1 / self.scale.x, 1 / self.scale.y)
        inv_rotation = self.rotation.inverse

        # Calculate inverse position: -(inv_rotation * position) * inv_scale
        inv_position = (inv_rotation * (-self.position)).multiply_componentwise(
            inv_scale
        )

        self._inv_matrix = ScaledTransform(
            position=inv_position, rotation=inv_rotation, scale=inv_scale
        )
        return self._inv_matrix

    def __mul__(self, other: Union["ScaledTransform", Transform]) -> "ScaledTransform":
        """
        Compose transformations, handling both ScaledTransform and base Transform.

        The composition is defined so that (self * other)(x) = self(other(x)).
        This means the linear (scale/rotation) part of self will act on the other's
        translation. In particular, if you convert a Transform to a ScaledTransform
        with an identity scale and then compose it with a ScaledTransform that has
        nontrivial scaling, the translation from the Transform will be multiplied
        by those scale factors.

        Args:
            other (ScaledTransform|Transform): Transformation to compose.

        Returns:
            ScaledTransform: New composite transformation.

        Examples:
            >>> tf = Transform((1, 0), Rot(math.pi/2))
            >>> st = ScaledTransform(scale=2)
            >>> # When composed in the order below, the translation (1, 0) is scaled to (2, 0)
            >>> tf * st
            ScaledTransform(position=Vec2(1.0, 0.0), rotation=Rot(1.570796), scale=Vec2(2.0, 2.0))
            >>> st * tf
            ScaledTransform(position=Vec2(2.0, 0.0), rotation=Rot(1.570796), scale=Vec2(2.0, 2.0))
        """
        # If the other transform is a plain Transform, convert it to a ScaledTransform
        if isinstance(other, Transform):
            other = ScaledTransform.from_transform(other)
        elif not isinstance(other, ScaledTransform):
            return NotImplemented

        # Compose transformations in the order: (self ∘ other)(x) = self(other(x))
        combined_scale = self.scale.multiply_componentwise(other.scale)
        combined_rotation = self.rotation * other.rotation
        # Note: other.position is "pre-scaled" by self.scale.
        combined_position = self.position + self.rotation.rotate_vector(
            self.scale.multiply_componentwise(other.position)
        )

        return ScaledTransform(
            position=combined_position, rotation=combined_rotation, scale=combined_scale
        )

    def __eq__(self, other: object) -> bool:
        """Check equality with both ScaledTransform and base Transform.

        Args:
            other: Transformation to compare (ScaledTransform/Transform)

        Returns:
            bool: True if components match exactly. For Transform comparisons,
                checks if scale is (1,1) and other components match.

        Example:
            >>> st = ScaledTransform(scale=1)
            >>> tf = Transform()
            >>> st == tf  # True when scale is identity
            True
        """
        if isinstance(other, Transform):
            return (
                self.position == other.position
                and self.rotation == other.rotation
                and self.scale == (1, 1)
            )
        if isinstance(other, ScaledTransform):
            return (
                self.position == other.position
                and self.rotation == other.rotation
                and self.scale == other.scale
            )
        return False

    def __repr__(self) -> str:
        """Machine-readable representation of the transform.

        Returns:
            str: String that can recreate the transform via eval()

        Example:
            >>> t = ScaledTransform(Vec2(1,2), Rot(0.5), (2,3))
            >>> repr(t)
            'ScaledTransform(position=Vec2(1.0, 2.0), rotation=Rot(0.500000), scale=Vec2(2.0, 3.0))'
        """
        return (
            f"ScaledTransform(position={self.position!r}, "
            f"rotation={self.rotation!r}, scale={self.scale!r})"
        )


class AABB:
    """Axis-Aligned Bounding Box (AABB) for 2D spatial queries.

    Features:
    - Immutable design (all operations return new instances)
    - Y-up coordinate system compatibility
    - Merge operations with other AABBs/points
    - Intersection calculations
    - Validity and containment checks

    Example:
        >>> box = AABB((0, 0), (2, 3))
        >>> box.center
        Vec2(1.0, 1.5)
    """

    __slots__ = ("_lower", "_upper")

    def __init__(
        self,
        lower: VectorLike = Vec2(math.inf, math.inf),
        upper: VectorLike = Vec2(-math.inf, -math.inf),
    ):
        """
        Initialize AABB with lower and upper bounds.

        Args:
            lower (VectorLike): Minimum coordinates (x1, y1)
            upper (VectorLike): Maximum coordinates (x2, y2)

        Note:
            Default creates invalid AABB, use from_points for valid initialization

        Example:
            >>> AABB((0, 0), (2, 2))
            AABB(lower=Vec2(0.0, 0.0), upper=Vec2(2.0, 2.0))
        """
        self._lower = Vec2(*lower)
        self._upper = Vec2(*upper)

    @property
    def lower(self) -> Vec2:
        """
        Minimum boundary point (read-only).

        Returns:
            Vec2: Copy of lower bounds vector

        Example:
            >>> AABB((1,2), (3,4)).lower
            Vec2(1.0, 2.0)
        """
        return self._lower

    @property
    def upper(self) -> Vec2:
        """
        Maximum boundary point (read-only).

        Returns:
            Vec2: Copy of upper bounds vector

        Example:
            >>> AABB((1,2), (3,4)).upper
            Vec2(3.0, 4.0)
        """
        return self._upper

    @classmethod
    def from_b2AABB(cls, b2_aabb):
        """Create AABB from Box2D's b2AABB structure.

        Args:
            b2_aabb: FFI pointer to b2AABB C struct

        Example:
            >>> aabb_c = ffi.new("b2AABB*", ((0,0), (2,3)))
            >>> AABB.from_b2AABB(aabb_c)
            AABB(lower=Vec2(0.0, 0.0), upper=Vec2(2.0, 3.0))
        """
        lower = Vec2.from_b2Vec2(b2_aabb.lowerBound)
        upper = Vec2.from_b2Vec2(b2_aabb.upperBound)
        return cls(lower, upper)

    @property
    def b2AABB(self):
        """Box2D b2AABB equivalent (managed by FFI).

        Example:
            >>> aabb = AABB((1,2), (3,4))
            >>> ca = aabb.b2AABB
            >>> ca.lowerBound.x, ca.upperBound.y
            (1.0, 4.0)
        """
        aabb = ffi.new("b2AABB*")
        aabb.lowerBound = self.lower.b2Vec2[0]
        aabb.upperBound = self.upper.b2Vec2[0]
        return aabb

    def merge(self, other: Union["AABB", VectorLike]) -> "AABB":
        """
        Create new AABB encompassing this and another AABB/point.

        Args:
            other: AABB or point to include

        Returns:
            AABB: Expanded bounding box

        Example:
            >>> AABB((0,0), (1,1)).merge(AABB((2,2), (3,3)))
            AABB(lower=Vec2(0.0, 0.0), upper=Vec2(3.0, 3.0))
        """
        if isinstance(other, AABB):
            new_lower = Vec2.min(self.lower, other.lower)
            new_upper = Vec2.max(self.upper, other.upper)
        else:  # Treat as point
            point = Vec2(*other)
            new_lower = Vec2.min(self.lower, point)
            new_upper = Vec2.max(self.upper, point)
        return AABB(new_lower, new_upper)

    def __or__(self, other: Union["AABB", VectorLike]) -> "AABB":
        """
        Union operator equivalent to merge().

        Example:
            >>> AABB((0,0), (1,1)) | (2,2)
            AABB(lower=Vec2(0.0, 0.0), upper=Vec2(2.0, 2.0))
        """
        return self.merge(other)

    @classmethod
    def from_points(cls, points: Iterable[VectorLike]) -> "AABB":
        """
        Construct minimal AABB containing all given points.

        Args:
            points: Collection of Vec2 or coordinate tuples

        Returns:
            AABB: Bounding box containing all points

        Example:
            >>> AABB.from_points([(0,1), (2,3), (-1,5)])
            AABB(lower=Vec2(-1.0, 1.0), upper=Vec2(2.0, 5.0))
        """
        aabb = cls(points[0], points[0])
        for point in points:
            aabb = aabb.merge(point)  # Returns new AABB each iteration
        return aabb

    @property
    def is_valid(self):
        """
        Check if AABB represents a valid bounded region.

        Returns:
            bool: True if lower <= upper and all coordinates finite

        Example:
            >>> AABB((0,0), (1,1)).is_valid
            True
            >>> AABB((1,1), (0,0)).is_valid
            False
        """
        return (
            self.lower.x <= self.upper.x
            and self.lower.y <= self.upper.y
            and self.lower.is_finite
            and self.upper.is_finite
        )

    @property
    def center(self):
        """
        Calculate geometric center of AABB.

        Returns:
            Vec2: Center point coordinates

        Example:
            >>> AABB((0,0), (2,2)).center
            Vec2(1.0, 1.0)
        """
        return (self.lower + self.upper) * 0.5

    @property
    def half_size(self):
        """
        Get half dimensions from center to edges.

        Returns:
            Vec2: (width/2, height/2) vector

        Example:
            >>> AABB((0,0), (2,4)).half_size
            Vec2(1.0, 2.0)
        """
        return (self.upper - self.lower) * 0.5

    def contains(self, other: Union["AABB", VectorLike]) -> bool:
        """
        Check if another AABB or point is fully contained within this one.

        Args:
            other: AABB or point to test containment

        Returns:
            bool: True if other AABB or point is completely inside

        Example:
            >>> AABB((0,0), (5,5)).contains(AABB((1,1), (3,3)))
            True
            >>> AABB((0,0), (5,5)).contains((3,3))
            True
        """
        if isinstance(other, AABB):
            return (self.lower <= other.lower) and (self.upper >= other.upper)
        else:  # Treat as point
            other = Vec2(*other)
            return (self.lower <= other) and (self.upper >= other)

    def __contains__(self, other: Union["AABB", VectorLike]) -> bool:
        """
        Check if another AABB or point is fully contained within this one.

        Args:
            other: AABB or point to test containment

        Returns:
            bool: True if other AABB or point is completely inside

        Example:
            >>> AABB((1,1), (3,3)) in AABB((0,0), (5,5))
            True
            >>> (0, 3) in AABB((0,0), (5,5))
            True
        """
        return self.contains(other)

    def overlaps(self, other: "AABB") -> bool:
        """
        Check if another AABB overlaps with this one.

        Args:
            other: AABB to test overlap

        Returns:
            bool: True if AABBs overlap

        Example:
            >>> AABB((0,0), (2,2)).overlaps(AABB((1,1), (3,3)))
            True
        """
        if isinstance(other, AABB):
            return (self & other).is_valid
        else:
            raise TypeError(
                f"Unsupported operand type(s) for &: 'AABB' and '{type(other)}'"
            )

    def __and__(self, other: "AABB") -> "AABB":
        """
        Calculate intersection region with another AABB.

        Returns:
            AABB: Overlapping region (may be invalid if no overlap)

        Example:
            >>> AABB((0,0), (2,2)) & AABB((1,1), (3,3))
            AABB(lower=Vec2(1.0, 1.0), upper=Vec2(2.0, 2.0))
        """
        return AABB(
            lower=(max(self.lower.x, other.lower.x), max(self.lower.y, other.lower.y)),
            upper=(min(self.upper.x, other.upper.x), min(self.upper.y, other.upper.y)),
        )

    @property
    def width(self) -> float:
        """
        Calculate horizontal span of the AABB.

        Returns:
            float: Difference between upper and lower x-coordinates

        Example:
            >>> AABB((1, 2), (4, 5)).width
            3.0
        """
        return self.upper.x - self.lower.x

    @property
    def height(self) -> float:
        """
        Calculate vertical span of the AABB.

        Returns:
            float: Difference between upper and lower y-coordinates

        Example:
            >>> AABB((1, 2), (3, 5)).height
            3.0
        """
        return self.upper.y - self.lower.y

    def __repr__(self):
        """
        Machine-readable representation of the AABB.

        Returns:
            str: String that can recreate the AABB

        Example:
            >>> repr(AABB((1, 2), (3, 4)))
            'AABB(lower=Vec2(1.0, 2.0), upper=Vec2(3.0, 4.0))'
        """
        return f"AABB(lower={self.lower}, upper={self.upper})"

    def __eq__(self, other):
        """
        Exact bounds equality check.

        Args:
            other: AABB to compare

        Returns:
            bool: True if both lower and upper bounds match exactly

        Example:
            >>> AABB((1,1), (2,2)) == AABB((1,1), (2,2))
            True
            >>> AABB((0,0), (1,1)) == AABB((0,0), (2,2))
            False
        """
        return self.lower == other.lower and self.upper == other.upper

    def __bool__(self) -> bool:
        """
        Boolean conversion equivalent to validity check.

        Returns:
            bool: True if AABB is valid (non-degenerate and finite)

        Example:
            >>> bool(AABB((0,0), (1,1)))
            True
            >>> bool(AABB((1,1), (0,0)))
            False
        """
        return self.is_valid

    def expanded(self, margin: float) -> "AABB":
        """
        Create uniformly expanded/contracted AABB.

        Args:
            margin: Expansion amount (positive expands, negative contracts)

        Returns:
            AABB: New AABB expanded on all sides

        Example:
            >>> AABB((0,0), (2,2)).expanded(1)
            AABB(lower=Vec2(-1.0, -1.0), upper=Vec2(3.0, 3.0))
        """
        margin = Vec2(margin, margin)
        return AABB(self.lower - margin, self.upper + margin)

    def translated(self, offset: VectorLike) -> "AABB":
        """
        Create translated AABB by given offset.

        Args:
            offset: Translation vector (Vec2 or tuple/list)

        Returns:
            AABB: Shifted AABB

        Example:
            >>> AABB((0,0), (2,2)).translated((1, -1))
            AABB(lower=Vec2(1.0, -1.0), upper=Vec2(3.0, 1.0))
        """
        off = Vec2(*offset)
        return AABB(self.lower + off, self.upper + off)


class Mat22:
    """A 2x2 matrix for linear transformations.

    Features:
        - Column-major storage
        - Matrix-vector/matrix multiplication
        - Matrix inversion and transpose
        - Rotation/identity matrix creation
        - Accepts various input formats (tuples, lists, Vec2s)

    Example:
        >>> Mat22(1, 2, 3, 4)
        Mat22(Vec2(1.0, 2.0), Vec2(3.0, 4.0))
    """

    __slots__ = ("cx", "cy")

    def __init__(self, *args: Union[float, VectorLike]):
        """
        Initialize matrix from multiple formats.

        Args:
            *args: Supported formats:
                - 4 scalars (a, b, c, d) => ::

                  [[a b]
                   [c d]]

                - 2 column vectors
                - Single iterable with 4 elements

        Example:
            >>> Mat22(1, 2, 3, 4)  # Scalar components
            Mat22(Vec2(1.0, 2.0), Vec2(3.0, 4.0))
            >>> Mat22(Vec2(1,2), Vec2(3,4))  # Column vectors
            Mat22(Vec2(1.0, 2.0), Vec2(3.0, 4.0))
        """
        if len(args) == 4:  # Scalar components
            self.cx = Vec2(args[0], args[1])
            self.cy = Vec2(args[2], args[3])
        elif len(args) == 2:  # Two column vectors
            self.cx = Vec2(*args[0])
            self.cy = Vec2(*args[1])
        elif len(args) == 1 and len(args[0]) == 4:  # Flat list
            self.cx = Vec2(args[0][0], args[0][1])
            self.cy = Vec2(args[0][2], args[0][3])
        else:
            raise ValueError("Invalid arguments for Mat22")

    @classmethod
    def from_b2Mat22(cls, b2_mat22):
        """Create Mat22 from Box2D's b2Mat22 structure.

        Args:
            b2_mat22: FFI pointer to b2Mat22 C struct

        Example:
            >>> mat_c = ffi.new("b2Mat22*", ((1,2), (3,4)))
            >>> Mat22.from_b2Mat22(mat_c)
            Mat22(Vec2(1.0, 2.0), Vec2(3.0, 4.0))
        """
        cx = Vec2.from_b2Vec2(b2_mat22.cx)
        cy = Vec2.from_b2Vec2(b2_mat22.cy)
        return cls(cx, cy)

    @property
    def b2Mat22(self):
        """Box2D b2Mat22 equivalent (managed by FFI).

        Example:
            >>> mat = Mat22(1,2,3,4)
            >>> cm = mat.b2Mat22
            >>> cm.cx.x, cm.cy.y
            (1.0, 4.0)
        """
        mat = ffi.new("b2Mat22*")
        mat.cx = self.cx.b2Vec2[0]
        mat.cy = self.cy.b2Vec2[0]
        return mat

    @classmethod
    def identity(cls) -> "Mat22":
        """
        Create identity matrix (no transformation).

        Returns:
            Mat22: [[1 0]
                    [0 1]]

        Example:
            >>> Mat22.identity()
            Mat22(Vec2(1.0, 0.0), Vec2(0.0, 1.0))
        """
        return cls(1, 0, 0, 1)

    @classmethod
    def from_angle(cls, angle: float) -> "Mat22":
        """
        Create rotation matrix from angle.

        Args:
            angle (float): Rotation angle in radians

        Returns:
            Mat22: Rotation matrix

        Example:
            >>> Mat22.from_angle(math.pi/2)
            Mat22(Vec2(0.0, 1.0), Vec2(-1.0, 0.0))
        """
        c = math.cos(angle)
        s = math.sin(angle)
        return cls(c, s, -s, c)

    @classmethod
    def from_columns(cls, col1: VectorLike, col2: VectorLike) -> "Mat22":
        """
        Create matrix from column vectors.

        Args:
            col1: First column vector
            col2: Second column vector

        Returns:
            Mat22: Column-based matrix

        Example:
            >>> Mat22.from_columns((1,2), (3,4))
            Mat22(Vec2(1.0, 2.0), Vec2(3.0, 4.0))
        """

        return cls(col1, col2)

    @classmethod
    def from_rows(cls, row1: VectorLike, row2: VectorLike) -> "Mat22":
        """
        Create matrix from row vectors (transposed).

        Args:
            row1: First row vector
            row2: Second row vector

        Returns:
            Mat22: Row-based matrix

        Example:
            >>> Mat22.from_rows((1,3), (2,4))
            Mat22(Vec2(1.0, 2.0), Vec2(3.0, 4.0))
        """
        return cls(row1[0], row2[0], row1[1], row2[1])

    def __mul__(self, other: Union[VectorLike, "Mat22"]) -> Union["Vec2", "Mat22"]:
        """
        Matrix multiplication with vector or matrix.

        Args:
            other: Vec2 or Mat22 to multiply

        Returns:
            Vec2|Mat22: Transformation result

        Example - Vector multiplication:
            >>> Mat22(1,2,3,4) * Vec2(1,1)
            Vec2(4.0, 6.0)

        Example - Matrix multiplication:
            >>> Mat22(1,2,3,4) * Mat22(5,6,7,8)
            Mat22(Vec2(23.0, 34.0), Vec2(31.0, 46.0))
        """
        if isinstance(other, Mat22):
            return Mat22(self * other.cx, self * other.cy)
        other_vec = Vec2(*other)
        return Vec2(
            self.cx.x * other.x + self.cy.x * other.y,
            self.cx.y * other.x + self.cy.y * other.y,
        )

    def transpose(self) -> "Mat22":
        """
        Create transposed matrix (swap rows and columns).

        Returns:
            Mat22: Transposed matrix

        Example:
            >>> Mat22(1,2,3,4).transpose()
            Mat22(Vec2(1.0, 3.0), Vec2(2.0, 4.0))
        """
        return Mat22(self.cx.x, self.cy.x, self.cx.y, self.cy.y)

    @property
    def inverse(self) -> "Mat22":
        """
        Calculate inverse matrix if possible.

        Returns:
            Mat22: Inverse or identity matrix if singular

        Example:
            >>> Mat22(1,1,0,1).inverse
            Mat22(Vec2(1.0, -1.0), Vec2(-0.0, 1.0))

        Note:
            Returns identity matrix for singular matrices (det ≈ 0)
        """
        det = self.determinant
        if abs(det) < 1e-8:
            return Mat22.identity()

        inv_det = 1.0 / det
        return Mat22(
            inv_det * self.cy.y,
            -inv_det * self.cx.y,
            -inv_det * self.cy.x,
            inv_det * self.cx.x,
        )

    def solve(self, b: VectorLike) -> "Vec2":
        """
        Solve the linear system A * x = b.

        Args:
            b: Right-hand side vector (Vec2 or tuple/list)

        Returns:
            Vec2: Solution vector x if matrix is invertible

        Note:
            Returns zero vector if matrix is singular (det ≈ 0)

        Example:
            >>> m = Mat22(2, 0, 0, 2)  # Scales by 2
            >>> m.solve(Vec2(4, 6))     # Should divide by 2
            Vec2(2.0, 3.0)
            >>> singular = Mat22(1, 1, 1, 1)
            >>> singular.solve((1, 1))  # Returns zero for singular matrix
            Vec2(0.0, 0.0)
        """
        det = self.determinant
        if abs(det) < 1e-8:
            return Vec2.zero()

        inv_det = 1.0 / det
        return Vec2(
            inv_det * (self.cy.y * b.x - self.cy.x * b.y),
            inv_det * (-self.cx.y * b.x + self.cx.x * b.y),
        )

    @property
    def determinant(self) -> float:
        """
        Matrix determinant (scalar value indicating invertibility).

        Calculated as: (cx.x * cy.y) - (cy.x * cx.y)

        Returns:
            float: Determinant value

        Example:
            >>> Mat22(1, 0, 0, 1).determinant
            1.0
        """
        return self.cx.x * self.cy.y - self.cy.x * self.cx.y

    @property
    def columns(self) -> tuple["Vec2", "Vec2"]:
        """
        Matrix column vectors as a tuple.

        Returns:
            (Vec2, Vec2): First and second column vectors

        Example:
            >>> Mat22(1, 2, 3, 4).columns
            (Vec2(1.0, 2.0), Vec2(3.0, 4.0))
        """
        return (self.cx, self.cy)

    @property
    def rows(self) -> tuple["Vec2", "Vec2"]:
        """
        Matrix row vectors as a tuple.

        Returns:
            (Vec2, Vec2): First and second row vectors

        Example:
            >>> Mat22(1, 2, 3, 4).rows
            (Vec2(1.0, 3.0), Vec2(2.0, 4.0))
        """
        return (Vec2(self.cx.x, self.cy.x), Vec2(self.cx.y, self.cy.y))

    def __repr__(self) -> str:
        """Clear string representation with precision handling"""
        return f"Mat22({self.cx}, {self.cy})"

    def __eq__(self, other: object) -> bool:
        """
        Exact matrix equality check.

        Args:
            other: Matrix to compare

        Returns:
            bool: True if all components match exactly

        Example:
            >>> Mat22(1,2,3,4) == Mat22(1,2,3,4)
            True
            >>> Mat22(1,2,3,4) == Mat22(1,2,3,5)
            False
        """
        if not isinstance(other, Mat22):
            return False
        return self.cx == other.cx and self.cy == other.cy
