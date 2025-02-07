# vec2.py
import math

class Vec2:
    """2D vector with Box2D math operations
    
    Features:
    - Component-wise operations
    - Tuple interoperability (+, -, *, etc.)
    - Cross product variants
    - Distance calculations
    """
    __slots__ = ('_x', '_y')

    def __init__(self, x, y):
        self._x = float(x)
        self._y = float(y)

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    @classmethod
    def Zero(cls):
        """Create a zero vector (0,0)"""
        return cls(0.0, 0.0)

    @classmethod
    def Right(cls):
        """Create a right-pointing vector (1,0)"""
        return cls(1.0, 0.0)

    @classmethod
    def Left(cls):
        """Create a left-pointing vector (-1,0)"""
        return cls(-1.0, 0.0)

    @classmethod
    def Up(cls):
        """Create an up-pointing vector (0,-1)"""
        return cls(0.0, -1.0)

    @classmethod
    def Down(cls):
        """Create a down-pointing vector (0,1)"""
        return cls(0.0, 1.0)

    @classmethod
    def FromAngle(cls, angle):
        """Create a unit vector from the given angle in radians"""
        return cls(math.cos(angle), math.sin(angle))

    @classmethod
    def min(cls, a, b):
        """Component-wise minimum"""
        a = Vec2(*a)
        b = Vec2(*b)
        return cls(min(a.x, b.x), min(a.y, b.y))
    
    @classmethod
    def max(cls, a, b):
        """Component-wise maximum"""
        a = Vec2(*a)
        b = Vec2(*b)
        return cls(max(a.x, b.x), max(a.y, b.y))
    
    @property
    def is_finite(self):
        """True if both components are finite numbers"""
        return math.isfinite(self.x) and math.isfinite(self.y)
   
    def __getitem__(self, index):
        if index == 0:
            return self.x
        elif index == 1:
            return self.y
        raise IndexError("Index out of range. Must be 0 or 1.")

    def __len__(self):
        return 2

    def __iter__(self):
        """Allow tuple unpacking: x, y = vec2"""
        yield self.x
        yield self.y

    def __eq__(self, other):
        if isinstance(other, Vec2):
            return self.x == other.x and self.y == other.y
        return tuple(self) == tuple(other)

    def __add__(self, other):
        return Vec2(self.x + other[0], self.y + other[1])

    def __sub__(self, other):
        return Vec2(self.x - other[0], self.y - other[1])

    def __mul__(self, scalar):
        return Vec2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar):
        return self.__mul__(scalar)

    def __truediv__(self, scalar):
        if scalar == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        return Vec2(self.x / scalar, self.y / scalar)

    def __neg__(self):
        """Support for unary minus operator"""
        return Vec2(-self.x, -self.y)

    def __repr__(self):
        return f"Vec2({self.x:g}, {self.y:g})"

    def __hash__(self):
        return hash((self.x, self.y))

    def __lt__(self, other):
        other = Vec2(*other)
        return self.x < other.x and self.y < other.y
    
    def __le__(self, other):
        other = Vec2(*other)
        return self.x <= other.x and self.y <= other.y
    
    def __ge__(self, other):
        other = Vec2(*other)
        return self.x >= other.x and self.y >= other.y
    
    def __gt__(self, other):
        other = Vec2(*other)
        return self.x > other.x and self.y > other.y

    @property
    def length(self):
        return math.hypot(self.x, self.y)

    @property
    def length_squared(self):
        return self.x ** 2 + self.y ** 2

    def dot(self, other):
        return self.x * other.x + self.y * other.y

    def cross(self, other):
        return self.x * other.y - self.y * other.x

    def normalize(self):
        length = self.length
        if length == 0:
            return Vec2(0.0, 0.0)
        return Vec2(self.x / length, self.y / length)

    @property
    def angle(self):
        return math.atan2(self.y, self.x)

    def project(self, other):
        dot_product = self.dot(other)
        other_dot = other.dot(other)
        if other_dot == 0:
            raise ValueError("Cannot project onto the zero vector.")
        scalar = dot_product / other_dot
        return Vec2(scalar * other.x, scalar * other.y)

    def reject(self, other):
        return self - self.project(other)

    def lerp(self, other, t):
        return self + (other - self) * t

    def perpendicular(self, direction="right"):
        if direction == "right":
            return Vec2(self.y, -self.x)
        elif direction == "left":
            return Vec2(-self.y, self.x)
        else:
            raise ValueError("Direction must be 'left' or 'right'")

    def min(self, other):
        return Vec2(min(self.x, other.x), min(self.y, other.y))

    def max(self, other):
        return Vec2(max(self.x, other.x), max(self.y, other.y))

    def clamp(self, min_value, max_value):
        return self.max(min_value).min(max_value)

    @property
    def heading(self):
        return self.normalize()

    def inverse(self):
        """Return a new vector with both components inverted (x*-1, y*-1)"""
        return Vec2(-self.x, -self.y)

    def rotate(self, angle):
        """Rotate the vector by the given angle in radians"""
        new_x = self.x * math.cos(angle) - self.y * math.sin(angle)
        new_y = self.x * math.sin(angle) + self.y * math.cos(angle)
        return Vec2(new_x, new_y)
   
    def multiply_componentwise(self, other) -> 'Vec2':
        """Component-wise multiplication (like b2Mul)
        
        Args:
            other: Vec2 or tuple to multiply component-wise
            
        Example:
            >>> Vec2(2, 3).multiply_componentwise((3, 4))
            Vec2(6, 12)
        """
        other = Vec2(*other)
        return Vec2(self.x * other.x, self.y * other.y)

    def cross_scalar(self, s: float, direction: str = 'right') -> 'Vec2':
        """Cross product with scalar (b2CrossVS/b2CrossSV)
        
        Args:
            s: Scalar value
            direction: 'right' (vector x scalar) or 'left' (scalar x vector)
            
        Example:
            >>> Vec2(3, 4).cross_scalar(2)
            Vec2(8, -6)
        """
        if direction == 'right':
            return Vec2(s * self.y, -s * self.x)
        return Vec2(-s * self.y, s * self.x)

    def distance_to(self, other) -> float:
        """Calculate distance between two points (b2Distance)
        
        Example:
            >>> Vec2(0, 0).distance_to((3, 4))
            5.0
        """
        other = Vec2(*other)
        return (self - other).length

