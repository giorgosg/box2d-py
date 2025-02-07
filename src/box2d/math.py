import math
from typing import Union, Iterable, TypeAlias
from ._box2d import ffi, lib

VectorLike: TypeAlias = Union[
    tuple[float, float],
    list[float],
    Iterable[float]
]


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
            Any indexable with [0]/[1] access (tuples, lists,  
            numpy arrays, other Vec2 instances, etc.)

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
    __slots__ = ('_x', '_y')

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
        """Check if this vector is equal to another vector or tuple.

        Args:
            other: The :term:`vector-like` to compare with.

        Returns:
            bool: True if the vectors are equal, False otherwise.

        Example:
            >>> Vec2(1.0, 2.0) == (1.0, 2.0)
            True
        """
        if isinstance(other, Vec2):
            return self.x == other.x and self.y == other.y
        return tuple(self) == tuple(other)

    def __add__(self, other: VectorLike) -> 'Vec2':
        """Return the sum of this vector and another vector or tuple.

        Args:
            other: The :term:`vector-like` to add.

        Returns:
            Vec2: A new vector where each component is the sum of the corresponding components.

        Example:
            >>> Vec2(1.0, 2.0) + (3.0, 4.0)
            Vec2(4.0, 6.0)
        """
        return Vec2(self.x + other[0], self.y + other[1])

    def __sub__(self, other: VectorLike) -> 'Vec2':
        """Return the difference between this vector and another vector or tuple.

        Args:
            other: The :term:`vector-like` to subtract.

        Returns:
            Vec2: A new vector where each component is the difference of the corresponding components.

        Example:
            >>> Vec2(3, 4) - (1, 2)
            Vec2(2.0, 2.0)
        """
        return Vec2(self.x - other[0], self.y - other[1])

    def __mul__(self, scalar: float) -> 'Vec2':
        """Return the product of this vector and a scalar.

        Args:
            scalar (float): The scalar to multiply by.

        Returns:
            Vec2: A new vector where each component is multiplied by the scalar.

        Example:
            >>> Vec2(1.0, 2.0) * 2.0
            Vec2(2.0, 4.0)
        """
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        return Vec2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> 'Vec2':
        """Return the product of a scalar and this vector.

        Args:
            scalar (float): The scalar to multiply by.

        Returns:
            Vec2: A new vector where each component is multiplied by the scalar.

        Example:
            >>> 2.0 * Vec2(1.0, 2.0)
            Vec2(2.0, 4.0)
        """
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> 'Vec2':
        """Return the quotient of this vector divided by a scalar.

        Args:
            scalar (float): The scalar to divide by.

        Returns:
            Vec2: A new vector where each component is divided by the scalar.

        Raises:
            ZeroDivisionError: If the scalar is zero.

        Example:
            >>> Vec2(2.0, 4.0) / 2.0
            Vec2(1.0, 2.0)
        """
        if scalar == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        return Vec2(self.x / scalar, self.y / scalar)

    def __neg__(self) -> 'Vec2':
        """Return the negation of this vector.

        Returns:
            Vec2: A new vector with both components negated.

        Example:
            >>> -Vec2(1.0, 2.0)
            Vec2(-1.0, -2.0)
        """
        return Vec2(-self.x, -self.y)

    def __repr__(self) -> str:
        """Return a string representation of the vector.

        Returns:
            str: A string in the format 'Vec2(x, y)'.

        Example:
            >>> repr(Vec2(1.0, 2.0))
            'Vec2(1.0, 2.0)'
        """
        formatted_x, formatted_y = [format_num(v) for v in self]
        return f"Vec2({formatted_x}, {formatted_y})"

    def __hash__(self) -> int:
        """Return the hash value of the vector.

        Returns:
            int: The hash value based on the vector's components.
        """
        return hash((self.x, self.y))

    def __lt__(self, other: VectorLike) -> bool:
        """Check if this vector is less than another vector or tuple.

        Args:
            other: The :term:`vector-like` to compare with.

        Returns:
            bool: True if both components of this vector are less than the corresponding components of the other vector.

        Example:
            >>> Vec2(1.0, 2.0) < (2.0, 3.0)
            True
        """
        other = Vec2(*other)
        return self.x < other.x and self.y < other.y
    
    def __le__(self, other: VectorLike) -> bool:
        """Check if this vector is less than or equal to another vector or tuple.

        Args:
            other: The :term:`vector-like` to compare with.

        Returns:
            bool: True if both components of this vector are less than or equal to the corresponding components of the other vector.

        Example:
            >>> Vec2(1.0, 2.0) <= (2.0, 3.0)
            True
        """
        other = Vec2(*other)
        return self.x <= other.x and self.y <= other.y
    
    def __ge__(self, other: VectorLike) -> bool:
        """Check if this vector is greater than or equal to another vector or tuple.

        Args:
            other: The :term:`vector-like` to compare with.

        Returns:
            bool: True if both components of this vector are greater than or equal to the corresponding components of the other vector.

        Example:
            >>> Vec2(2.0, 3.0) >= (1.0, 2.0)
            True
        """
        other = Vec2(*other)
        return self.x >= other.x and self.y >= other.y
    
    def __gt__(self, other: VectorLike) -> bool:
        """Check if this vector is greater than another vector or tuple.

        Args:
            other: The :term:`vector-like` to compare with.

        Returns:
            bool: True if both components of this vector are greater than the corresponding components of the other vector.

        Example:
            >>> Vec2(2.0, 3.0) > (1.0, 2.0)
            True
        """
        other = Vec2(*other)
        return self.x > other.x and self.y > other.y

    def __bool__(self) -> bool:
        """Return True if the vector is not zero.

        Returns:
            bool: True if the vector is not zero, False otherwise.
        """
        return self.x != 0.0 or self.y != 0.0

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
        return self.x ** 2 + self.y ** 2

    def dot(self, other: VectorLike) -> float:
        """Compute the dot product of this vector and another vector or tuple.

        Args:
            other: The :term:`vector-like` to compute the dot product with.

        Returns:
            float: The dot product of the two vectors.

        Example:
            >>> Vec2(1.0, 2.0).dot((3.0, 4.0))
            11.0
        """
        other = Vec2(*other)
        return self.x * other.x + self.y * other.y

    def cross(self, other: VectorLike) -> float:
        """Compute the cross product of this vector and another vector or tuple.

        Args:
            other: The :term:`vector-like` to compute the cross product with.

        Returns:
            float: The cross product result, which is a scalar value.

        Note:
            In 2D, the cross product gives the z-component of the 3D cross product,
            which can be used to determine the direction of rotation relative to the other vector.

        Example:
            >>> Vec2(1.0, 0.0).cross((0.0, 1.0))
            1.0
        """
        other = Vec2(*other)
        return self.x * other.y - self.y * other.x

    def normalize(self):
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
    def angle(self):
        """The angle of the vector in radians.

        Returns:
            float: The angle in radians, computed using math.atan2(y, x).

        Example:
            >>> Vec2(1.0, 1.0).angle
            0.7853981633974483
        """
        return math.atan2(self.y, self.x)

    def project(self, other):
        """Project this vector onto another vector or tuple.

        Args:
            other: The :term:`vector-like` to project onto.

        Returns:
            Vec2: The projection of this vector onto the other vector.

        Raises:
            ValueError: If the other vector is the zero vector.

        Example:
            >>> Vec2(1.0, 0.0).project((0.0, 1.0))
            Vec2(0.0, 0.0)
        """
        other = Vec2(*other)
        dot_product = self.dot(other)
        other_dot = other.dot(other)
        if other_dot == 0:
            raise ValueError("Cannot project onto the zero vector.")
        scalar = dot_product / other_dot
        return Vec2(scalar * other.x, scalar * other.y)

    def reject(self, other):
        """Return the component of this vector perpendicular to another vector.

        Args:
            other: The :term:`vector-like` to reject from.

        Returns:
            Vec2: The component of this vector that is perpendicular to the other vector.

        Example:
            >>> Vec2(3.0, 0.0).reject((0.0, 1.0))
            Vec2(3.0, 0.0)
        """
        return self - self.project(other)

    def lerp(self, other, t):
        """Linearly interpolate between this vector and another vector or tuple.

        Args:
            other: The :term:`vector-like` to interpolate to.
            t (float): The interpolation factor, typically in [0, 1].

        Returns:
            Vec2: The interpolated vector.

        Example:
            >>> Vec2(0.0, 0.0).lerp((1.0, 1.0), 0.5)
            Vec2(0.5, 0.5)
        """
        other = Vec2(*other)
        return self + (other - self) * t

    def perpendicular(self, direction="right"):
        """Return a perpendicular vector.

        Args:
            direction (str, optional): The direction of the perpendicular vector.
                'right' or 'left'. Defaults to 'right'.

        Returns:
            Vec2: A perpendicular vector.

        Raises:
            ValueError: If the direction is not 'left' or 'right'.

        Example:
            >>> Vec2(1.0, 0.0).perpendicular('right')
            Vec2(0.0, -1.0)
        """
        if direction == "right":
            return Vec2(self.y, -self.x)
        elif direction == "left":
            return Vec2(-self.y, self.x)
        else:
            raise ValueError("Direction must be 'left' or 'right'")

    def min(self, other):
        """Return the component-wise minimum of this vector and another vector or tuple.

        Args:
            other: The :term:`vector-like` to compare.

        Returns:
            Vec2: A new vector where each component is the minimum of the corresponding components.

        Example:
            >>> Vec2(1.0, 2.0).min((3.0, 4.0))
            Vec2(1.0, 2.0)
        """
        other = Vec2(*other)
        return Vec2(min(self.x, other.x), min(self.y, other.y))

    def max(self, other):
        """Return the component-wise maximum of this vector and another vector or tuple.

        Args:
            other: The :term:`vector-like` to compare.

        Returns:
            Vec2: A new vector where each component is the maximum of the corresponding components.

        Example:
            >>> Vec2(1.0, 2.0).max((3.0, 4.0))
            Vec2(3.0, 4.0)
        """
        other = Vec2(*other)
        return Vec2(max(self.x, other.x), max(self.y, other.y))

    def clamp(self, min_value, max_value):
        """Clamp this vector within the specified range.

        Args:
            min_value: The :term:`vector-like` to compare.
            max_value: The :term:`vector-like` to compare.

        Returns:
            Vec2: A new vector where each component is clamped within the specified range.

        Example:
            >>> Vec2(0.5, 1.5).clamp((0.0, 0.0), (1.0, 1.0))
            Vec2(0.5, 1.0)
        """
        return self.max(min_value).min(max_value)

    @property
    def heading(self):
        """The normalized vector representing the direction.

        Returns:
            Vec2: The normalized vector.

        Example:
            >>> Vec2(3.0, 4.0).heading
            Vec2(0.6, 0.8)
        """
        return self.normalize()

    @property
    def inverse(self):
        """Return a new vector with both components inverted.

        Returns:
            Vec2: A new vector with components (-x, -y).

        Example:
            >>> Vec2(1.0, 2.0).inverse
            Vec2(-1.0, -2.0)
        """
        return -self

    def rotate(self, angle):
        """Rotate the vector by the given angle in radians.

        Args:
            angle (float): The angle in radians to rotate by.

        Returns:
            Vec2: The rotated vector.

        Example:
            >>> Vec2(1.0, 0.0).rotate(math.pi / 2)
            Vec2(0.0, 1.0)
        """
        new_x = self.x * math.cos(angle) - self.y * math.sin(angle)
        new_y = self.x * math.sin(angle) + self.y * math.cos(angle)
        return Vec2(new_x, new_y)
   
    def multiply_componentwise(self, other) -> 'Vec2':
        """Component-wise multiplication with another vector or tuple.

        Args:
            other: The :term:`vector-like` to multiply component-wise.

        Returns:
            Vec2: A new vector where each component is the product of the corresponding components.

        Example:
            >>> Vec2(2.0, 3.0).multiply_componentwise((3.0, 4.0))
            Vec2(6.0, 12.0)
        """
        other = Vec2(*other)
        return Vec2(self.x * other.x, self.y * other.y)

    def cross_scalar(self, s: float, direction: str = 'right') -> 'Vec2':
        """Cross product with a scalar, following Box2D conventions.

        Args:
            s (float): The scalar value.
            direction (str, optional): The direction of the cross product, either 'right' or 'left'. Defaults to 'right'.

        Returns:
            Vec2: The result of the cross product with the scalar.

        Example:
            >>> Vec2(3.0, 4.0).cross_scalar(2)
            Vec2(8.0, -6.0)
        """
        if direction == 'right':
            return Vec2(s * self.y, -s * self.x)
        return Vec2(-s * self.y, s * self.x)

    def distance_to(self, other) -> float:
        """Calculate the distance between this vector and another vector or tuple.

        Args:
            other: The :term:`vector-like` to measure the distance to.

        Returns:
            float: The Euclidean distance between the two vectors.

        Example:
            >>> Vec2(0.0, 0.0).distance_to((3.0, 4.0))
            5.0
        """
        other = Vec2(*other)
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
    __slots__ = ('_s', '_c')  # sin/cos storage like Box2D

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
    def from_sincos(cls, s: float, c: float) -> 'Rot':
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
    def from_degrees(cls, degrees: float) -> 'Rot':
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

    def __mul__(self, other: Union['Vec2', 'Rot']) -> Union['Vec2', 'Rot']:
        """
        Rotate vector or combine rotations.

        Args:
            other (Vec2|Rot): Vector to rotate or rotation to compose

        Returns:
            Vec2|Rot: Rotated vector or combined rotation

        Example - Vector rotation:
            >>> Rot(math.pi/2) * Vec2(1, 0)
            Vec2(0.0, 1.0)

        Example - Rotation composition:
            >>> r1 = Rot(math.pi/2)
            >>> r2 = Rot(math.pi/2)
            >>> (r1 * r2).angle_degrees
            180.0
        """
        if isinstance(other, Vec2):
            return self.rotate_vector(other)
        if isinstance(other, Rot):
            # Rotation composition (b2Rot_Mul)
            return Rot.from_sincos(
                self.s * other.c + self.c * other.s,
                self.c * other.c - self.s * other.s
            )
        return NotImplemented

    def __rmul__(self, other):
        """
        Handle vector * rotation syntax.

        Args:
            other (Vec2|tuple): Vector to rotate

        Returns:
            Vec2: Rotated vector

        Example:
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

    def inverse(self):
        """
        Create inverse/opposite rotation.

        Returns:
            Rot: New rotation with negated angle

        Example:
            >>> Rot(math.pi/4).inverse().angle_degrees
            -45.0
        """
        return Rot(-self.angle_radians)

    def interpolate(self, other, t):
        """
        Linear interpolation between two rotations.

        Args:
            other (Rot): Target rotation
            t (float): Interpolation factor [0.0, 1.0]

        Returns:
            Rot: Interpolated rotation

        Example:
            >>> Rot(0).interpolate(Rot(math.pi), 0.5).angle_degrees
            90.0
        """
        angle = self.angle_radians + t * (other.angle_radians - self.angle_radians)
        return Rot(angle)

    def rotate_vector(self, v):
        """
        Apply rotation to a vector.

        Args:
            v (Vec2): Vector to rotate

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

    def __call__(self, v):
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
    
    __slots__ = ('p', 'q')
    
    def __init__(self, 
                position: VectorLike = Vec2(0, 0), 
                rotation: Union[float, Rot] = Rot(0)):
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
        return self.q * point + self.p

    @property
    def inverse(self) -> 'Transform':
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
    
    def __mul__(self, other: 'Transform') -> 'Transform':
        """
        Compose two transformations.

        Args:
            other (Transform): Transformation to compose with

        Returns:
            Transform: Composed transformation
       """
        if isinstance(other, Transform):
            return Transform(self.p + self.q * other.p, self.q * other.q)
        else:
            raise TypeError(f"Unsupported operand type(s) for *: 'Transform' and '{type(other)}'")

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
   
    __slots__ = ('_lower', '_upper')
    
    def __init__(self, lower=(math.inf, math.inf), upper=(-math.inf, -math.inf)):
        """
        Initialize AABB with lower and upper bounds.

        Args:
            lower (Iterable): Minimum coordinates (x1, y1)
            upper (Iterable): Maximum coordinates (x2, y2)

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

    def merge(self, other: Union['AABB', VectorLike]) -> 'AABB':
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

    def __or__(self, other: Union['AABB', VectorLike]) -> 'AABB':
        """
        Union operator equivalent to merge().

        Example:
            >>> AABB((0,0), (1,1)) | (2,2)
            AABB(lower=Vec2(0.0, 0.0), upper=Vec2(2.0, 2.0))
        """
        return self.merge(other)

    @classmethod
    def from_points(cls, points: Iterable[VectorLike]) -> 'AABB':
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
        return (self.lower.x <= self.upper.x and 
                self.lower.y <= self.upper.y and
                self.lower.is_finite and 
                self.upper.is_finite)
    
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
    
    def contains(self, other: Union['AABB', VectorLike]) -> bool:
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

    def __contains__(self, other: Union['AABB', VectorLike]) -> bool:
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

    def overlaps(self, other: 'AABB') -> bool:
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
            raise TypeError(f"Unsupported operand type(s) for &: 'AABB' and '{type(other)}'")

    def __and__(self, other: 'AABB') -> 'AABB':
        """
        Calculate intersection region with another AABB.

        Returns:
            AABB: Overlapping region (may be invalid if no overlap)

        Example:
            >>> AABB((0,0), (2,2)) & AABB((1,1), (3,3))
            AABB(lower=Vec2(1.0, 1.0), upper=Vec2(2.0, 2.0))
        """
        return AABB(
            lower=(max(self.lower.x, other.lower.x), 
                   max(self.lower.y, other.lower.y)),
            upper=(min(self.upper.x, other.upper.x), 
                   min(self.upper.y, other.upper.y))
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

    def expanded(self, margin: float) -> 'AABB':
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

    def translated(self, offset: Union[Vec2, Iterable]) -> 'AABB':
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
    """A 2x2 matrix for linear transformations, compatible with Box2D's b2Mat22.
    
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

    __slots__ = ('cx', 'cy')

    def __init__(self, *args: Union[float, VectorLike]):
        """
        Initialize matrix from multiple formats.

        Args:
            *args: Supported formats:
                - 4 scalars (a, b, c, d) => [[a c]
                                             [b d]]
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
    def identity(cls) -> 'Mat22':
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
    def from_angle(cls, angle: float) -> 'Mat22':
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
    def from_columns(cls, col1: VectorLike, col2: VectorLike) -> 'Mat22':
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
    def from_rows(cls, row1: VectorLike, row2: VectorLike) -> 'Mat22':
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

    def __mul__(self, other: Union['Vec2', 'Mat22']) -> Union['Vec2', 'Mat22']:
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
        if isinstance(other, Vec2):
            return Vec2(self.cx.x * other.x + self.cy.x * other.y,
                        self.cx.y * other.x + self.cy.y * other.y)
            
        if isinstance(other, Mat22):
            return Mat22(self * other.cx, self * other.cy)
            
        raise TypeError(f"Unsupported operand type for *: Mat22 and {type(other)}")

    def transpose(self) -> 'Mat22':
        """
        Create transposed matrix (swap rows and columns).

        Returns:
            Mat22: Transposed matrix

        Example:
            >>> Mat22(1,2,3,4).transpose()
            Mat22(Vec2(1.0, 3.0), Vec2(2.0, 4.0))
        """
        return Mat22(self.cx.x, self.cy.x,
                    self.cx.y, self.cy.y)

    @property
    def inverse(self) -> 'Mat22':
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
            inv_det * self.cy.y, -inv_det * self.cx.y,
            -inv_det * self.cy.x, inv_det * self.cx.x
        )

    def solve(self, b: VectorLike) -> 'Vec2':
        """
        Solve the linear system A * x = b.

        Args:
            b: Right-hand side vector (Vec2 or tuple/list)

        Returns:
            Vec2: Solution vector x if matrix is invertible

        Note:
            Returns zero vector if matrix is singular (det ≈ 0)

        Example:
            >>> m = Mat22(1, 0, 0, 1)
            >>> m.solve(Vec2(2, 3))
            Vec2(2.0, 3.0)
        """
        det = self.determinant
        if abs(det) < 1e-8:
            return Vec2.zero()
            
        inv_det = 1.0 / det
        return Vec2(
            inv_det * (self.cy.y * b.x - self.cy.x * b.y),
            inv_det * (-self.cx.y * b.x + self.cx.x * b.y)
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
    def columns(self) -> tuple['Vec2', 'Vec2']:
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
    def rows(self) -> tuple['Vec2', 'Vec2']:
        """
        Matrix row vectors as a tuple.

        Returns:
            (Vec2, Vec2): First and second row vectors

        Example:
            >>> Mat22(1, 2, 3, 4).rows
            (Vec2(1.0, 3.0), Vec2(2.0, 4.0))
        """
        return (Vec2(self.cx.x, self.cy.x),
                Vec2(self.cx.y, self.cy.y))

    def __repr__(self) -> str:
        """Clear string representation with precision handling"""
        return (f"Mat22({self.cx}, {self.cy})")

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
