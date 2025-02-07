# vec2.py

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

    def __repr__(self):
        return f"Vec2({self.x:.2f}, {self.y:.2f})"

    def __hash__(self):
        return hash((self.x, self.y))
