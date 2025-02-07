# vec2.py
import math

class Vec2:
    """2D vector with Box2D math operations.
    
    Features:
    - Component-wise operations
    - Tuple interoperability (+, -, *, etc.)
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
    def Zero(cls):
        """Create a zero vector (0,0).

        Returns:
            Vec2: A zero vector instance.

        Example:
            >>> Vec2.Zero()
            Vec2(0, 0)
        """
        return cls(0.0, 0.0)

    @classmethod
    def Right(cls):
        """Create a right-pointing vector (1,0).

        Returns:
            Vec2: A right vector instance.

        Example:
            >>> Vec2.Right()
            Vec2(1, 0)
        """            
        return cls(1.0, 0.0)

    @classmethod
    def Left(cls):
        """Create a left-pointing vector (-1,0).

        Returns:
            Vec2: A left vector instance.

        Example:
            >>> Vec2.Left()
            Vec2(-1, 0)
        """            
        return cls(-1.0, 0.0)

    @classmethod
    def Up(cls):
        """Create an up-pointing vector (0,1).

        Returns:
            Vec2: An up vector instance.

        Example:
            >>> Vec2.Up()
            Vec2(0, 1)
        """            
        return cls(0.0, 1.0)

    @classmethod
    def Down(cls):
        """Create a down-pointing vector (0,-1).

        Returns:
            Vec2: A down vector instance.

        Example:
            >>> Vec2.Down()
            Vec2(0, -1)
        """        
        return cls(0.0, -1.0)

    @classmethod
    def FromAngle(cls, angle):
        """Create a unit vector from the given angle in radians.

        Args:
            angle (float): The angle in radians.

        Returns:
            Vec2: A unit vector instance.

        Example:
            >>> Vec2.FromAngle(math.pi/2)
            Vec2(0, 1)
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

    def __eq__(self, other):
        """Check if this vector is equal to another vector or tuple.

        Args:
            other (Vec2 or tuple): The vector or tuple to compare with.

        Returns:
            bool: True if the vectors are equal, False otherwise.

        Example:
            >>> Vec2(1.0, 2.0) == (1.0, 2.0)
            True
        """
        if isinstance(other, Vec2):
            return self.x == other.x and self.y == other.y
        return tuple(self) == tuple(other)

    def __add__(self, other):
        """Return the sum of this vector and another vector or tuple.

        Args:
            other (Vec2 or tuple): The vector or tuple to add.

        Returns:
            Vec2: A new vector where each component is the sum of the corresponding components.

        Example:
            >>> Vec2(1.0, 2.0) + (3.0, 4.0)
            Vec2(4, 6)
        """
        return Vec2(self.x + other[0], self.y + other[1])

    def __sub__(self, other):
        """Return the difference between this vector and another vector or tuple.

        Args:
            other (Vec2 or tuple): The vector or tuple to subtract.

        Returns:
            Vec2: A new vector where each component is the difference of the corresponding components.

        Example:
            >>> Vec2(3, 4) - (1, 2)
            Vec2(2, 2)
        """
        return Vec2(self.x - other[0], self.y - other[1])

    def __mul__(self, scalar):
        """Return the product of this vector and a scalar.

        Args:
            scalar (float): The scalar to multiply by.

        Returns:
            Vec2: A new vector where each component is multiplied by the scalar.

        Example:
            >>> Vec2(1.0, 2.0) * 2.0
            Vec2(2, 4)
        """
        return Vec2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar):
        """Return the product of a scalar and this vector.

        Args:
            scalar (float): The scalar to multiply by.

        Returns:
            Vec2: A new vector where each component is multiplied by the scalar.

        Example:
            >>> 2.0 * Vec2(1.0, 2.0)
            Vec2(2, 4)
        """
        return self.__mul__(scalar)

    def __truediv__(self, scalar):
        """Return the quotient of this vector divided by a scalar.

        Args:
            scalar (float): The scalar to divide by.

        Returns:
            Vec2: A new vector where each component is divided by the scalar.

        Raises:
            ZeroDivisionError: If the scalar is zero.

        Example:
            >>> Vec2(2.0, 4.0) / 2.0
            Vec2(1, 2)
        """
        if scalar == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        return Vec2(self.x / scalar, self.y / scalar)

    def __neg__(self):
        """Return the negation of this vector.

        Returns:
            Vec2: A new vector with both components negated.

        Example:
            >>> -Vec2(1.0, 2.0)
            Vec2(-1, -2)
        """
        return Vec2(-self.x, -self.y)

    def __repr__(self):
        """Return a string representation of the vector.

        Returns:
            str: A string in the format 'Vec2(x, y)'.

        Example:
            >>> repr(Vec2(1.0, 2.0))
            'Vec2(1, 2)'
        """
        formatted_x, formatted_y = [f"{v:.3f}".rstrip("0").rstrip(".") for v in self]
        return f"Vec2({formatted_x}, {formatted_y})"

    def __hash__(self):
        """Return the hash value of the vector.

        Returns:
            int: The hash value based on the vector's components.
        """
        return hash((self.x, self.y))

    def __lt__(self, other):
        """Check if this vector is less than another vector or tuple.

        Args:
            other (Vec2 or tuple): The vector or tuple to compare with.

        Returns:
            bool: True if both components of this vector are less than the corresponding components of the other vector.

        Example:
            >>> Vec2(1.0, 2.0) < (2.0, 3.0)
            True
        """
        other = Vec2(*other)
        return self.x < other.x and self.y < other.y
    
    def __le__(self, other):
        """Check if this vector is less than or equal to another vector or tuple.

        Args:
            other (Vec2 or tuple): The vector or tuple to compare with.

        Returns:
            bool: True if both components of this vector are less than or equal to the corresponding components of the other vector.

        Example:
            >>> Vec2(1.0, 2.0) <= (2.0, 3.0)
            True
        """
        other = Vec2(*other)
        return self.x <= other.x and self.y <= other.y
    
    def __ge__(self, other):
        """Check if this vector is greater than or equal to another vector or tuple.

        Args:
            other (Vec2 or tuple): The vector or tuple to compare with.

        Returns:
            bool: True if both components of this vector are greater than or equal to the corresponding components of the other vector.

        Example:
            >>> Vec2(2.0, 3.0) >= (1.0, 2.0)
            True
        """
        other = Vec2(*other)
        return self.x >= other.x and self.y >= other.y
    
    def __gt__(self, other):
        """Check if this vector is greater than another vector or tuple.

        Args:
            other (Vec2 or tuple): The vector or tuple to compare with.

        Returns:
            bool: True if both components of this vector are greater than the corresponding components of the other vector.

        Example:
            >>> Vec2(2.0, 3.0) > (1.0, 2.0)
            True
        """
        other = Vec2(*other)
        return self.x > other.x and self.y > other.y

    @property
    def length(self):
        """The Euclidean length (magnitude) of the vector.

        Returns:
            float: The length of the vector.

        Example:
            >>> Vec2(3.0, 4.0).length
            5.0
        """
        return math.hypot(self.x, self.y)

    @property
    def length_squared(self):
        """The square of the Euclidean length of the vector.

        Returns:
            float: The squared length of the vector.

        Example:
            >>> Vec2(3.0, 4.0).length_squared
            25.0
        """
        return self.x ** 2 + self.y ** 2

    def dot(self, other):
        """Compute the dot product of this vector and another vector or tuple.

        Args:
            other (Vec2 or tuple): The vector or tuple to compute the dot product with.

        Returns:
            float: The dot product of the two vectors.

        Example:
            >>> Vec2(1.0, 2.0).dot((3.0, 4.0))
            11.0
        """
        other = Vec2(*other)
        return self.x * other.x + self.y * other.y

    def cross(self, other):
        """Compute the cross product of this vector and another vector or tuple.

        Args:
            other (Vec2 or tuple): The vector or tuple to compute the cross product with.

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
            other (Vec2 or tuple): The vector or tuple to project onto.

        Returns:
            Vec2: The projection of this vector onto the other vector.

        Raises:
            ValueError: If the other vector is the zero vector.

        Example:
            >>> Vec2(1.0, 0.0).project((0.0, 1.0))
            Vec2(0, 0)
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
            other (Vec2 or tuple): The vector or tuple to reject from.

        Returns:
            Vec2: The component of this vector that is perpendicular to the other vector.

        Example:
            >>> Vec2(3.0, 0.0).reject((0.0, 1.0))
            Vec2(3, 0)
        """
        return self - self.project(other)

    def lerp(self, other, t):
        """Linearly interpolate between this vector and another vector or tuple.

        Args:
            other (Vec2 or tuple): The target vector or tuple.
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
            Vec2(0, -1)
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
            other (Vec2 or tuple): The vector or tuple to compare.

        Returns:
            Vec2: A new vector where each component is the minimum of the corresponding components.

        Example:
            >>> Vec2(1.0, 2.0).min((3.0, 4.0))
            Vec2(1, 2)
        """
        other = Vec2(*other)
        return Vec2(min(self.x, other.x), min(self.y, other.y))

    def max(self, other):
        """Return the component-wise maximum of this vector and another vector or tuple.

        Args:
            other (Vec2 or tuple): The vector or tuple to compare.

        Returns:
            Vec2: A new vector where each component is the maximum of the corresponding components.

        Example:
            >>> Vec2(1.0, 2.0).max((3.0, 4.0))
            Vec2(3, 4)
        """
        other = Vec2(*other)
        return Vec2(max(self.x, other.x), max(self.y, other.y))

    def clamp(self, min_value, max_value):
        """Clamp this vector within the specified range.

        Args:
            min_value (Vec2 or tuple): The minimum value for each component.
            max_value (Vec2 or tuple): The maximum value for each component.

        Returns:
            Vec2: A new vector where each component is clamped within the specified range.

        Example:
            >>> Vec2(0.5, 1.5).clamp((0.0, 0.0), (1.0, 1.0))
            Vec2(0.5, 1)
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

    def inverse(self):
        """Return a new vector with both components inverted.

        Returns:
            Vec2: A new vector with components (-x, -y).

        Example:
            >>> Vec2(1.0, 2.0).inverse()
            Vec2(-1, -2)
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
            Vec2(0, 1)
        """
        new_x = self.x * math.cos(angle) - self.y * math.sin(angle)
        new_y = self.x * math.sin(angle) + self.y * math.cos(angle)
        return Vec2(new_x, new_y)
   
    def multiply_componentwise(self, other) -> 'Vec2':
        """Component-wise multiplication with another vector or tuple.

        Args:
            other (Vec2 or tuple): The vector or tuple to multiply component-wise.

        Returns:
            Vec2: A new vector where each component is the product of the corresponding components.

        Example:
            >>> Vec2(2.0, 3.0).multiply_componentwise((3.0, 4.0))
            Vec2(6, 12)
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
            Vec2(8, -6)
        """
        if direction == 'right':
            return Vec2(s * self.y, -s * self.x)
        return Vec2(-s * self.y, s * self.x)

    def distance_to(self, other) -> float:
        """Calculate the distance between this vector and another vector or tuple.

        Args:
            other (Vec2 or tuple): The vector or tuple to measure the distance to.

        Returns:
            float: The Euclidean distance between the two vectors.

        Example:
            >>> Vec2(0.0, 0.0).distance_to((3.0, 4.0))
            5.0
        """
        other = Vec2(*other)
        return (self - other).length

