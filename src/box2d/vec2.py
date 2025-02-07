# vec2.py
import math

class Vec2:
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

    def __getitem__(self, index):
        if index == 0:
            return self.x
        elif index == 1:
            return self.y
        raise IndexError("Index out of range. Must be 0 or 1.")

    def __len__(self):
        return 2

    def __iter__(self):
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

    def __repr__(self):
        return f"Vec2({self.x:.2f}, {self.y:.2f})"

    def __hash__(self):
        return hash((self.x, self.y))

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

