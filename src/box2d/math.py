import math
from .vec2 import Vec2

class Rot:
    """
    Represents a 2D rotation using cosine and sine values.
    This is similar to using complex numbers for rotations but 
    is more explicit about the rotation context.
    """
    __slots__ = ('s', 'c')  # sin/cos storage like Box2D

    def __init__(self, angle_radians=0.0):
        """
        Initialize a Rot instance with the given angle in radians.
        
        Args:
            angle_radians (float, optional): The angle in radians. Defaults to 0.0.
        """
        self.c = math.cos(angle_radians)
        self.s = math.sin(angle_radians)

    @classmethod
    def FromAngle(cls, angle_radians):
        """
        Create a Rot instance from the given angle in radians.
        
        Args:
            angle_radians (float): The angle in radians.
        
        Returns:
            Rot: A new Rot instance representing the given angle.
        """
        return cls(angle_radians)

    @classmethod
    def from_b2Rot(cls, b2_rot):
        """
        Create a Rot instance from a b2Rot struct.
        
        Args:
            b2_rot: The b2Rot struct from the Box2D C library.
        
        Returns:
            Rot: A new Rot instance with the same rotation as the b2Rot.
        """
        return cls.from_sincos(b2_rot.s, b2_rot.c)

    @classmethod
    def from_sincos(cls, s: float, c: float) -> 'Rot':
        """Create rotation directly from sin/cos values"""
        inst = cls(0)
        inst.s = s
        inst.c = c
        return inst

    @property
    def angle_radians(self):
        """
        Get the angle in radians.
        
        Returns:
            float: The angle in radians.
        """
        return math.atan2(self.s, self.c)

    @property
    def angle_degrees(self):
        """
        Get the angle in degrees.
        
        Returns:
            float: The angle in degrees.
        """
        return math.degrees(self.angle_radians)

    @property
    def x_axis(self) -> Vec2:
        """Get X-axis (column 1 of rotation matrix)"""
        return Vec2(self.c, self.s)

    @property
    def y_axis(self) -> Vec2:
        """Get Y-axis (column 2 of rotation matrix)"""
        return Vec2(-self.s, self.c)

    def __mul__(self, other):
        """Rotate vector or combine rotations"""
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
        """Handle vector * rotation"""
        if isinstance(other, (tuple, Vec2)):
            return self.rotate_vector(other)
        return self.__mul__(other)

    def __str__(self):
        """
        Get a string representation of this rotation.
        
        Returns:
            str: A string in the format 'Rot(c=..., s=...)'.
        """
        return f"Rot(c={self.c:.6f}, s={self.s:.6f})"

    def __repr__(self):
        """
        Get a string that can be used to recreate this rotation.
        
        Returns:
            str: A string in the format 'Rot.FromAngle(...)'.
        """
        return f"Rot.FromAngle({self.angle_radians:.6f})"

    def __eq__(self, other):
        """
        Check if this rotation is equal to another.
        
        Args:
            other (Rot): The other rotation to compare with.
        
        Returns:
            bool: True if the rotations are equal, False otherwise.
        """
        if isinstance(other, Rot):
            return self.c == other.c and self.s == other.s
        return False

    def __hash__(self):
        """
        Get the hash value for this rotation.
        
        Returns:
            int: The hash value.
        """
        return hash((self.c, self.s))

    def Normalize(self):
        """
        Normalize this rotation.
        
        Returns:
            Rot: A new normalized Rot instance.
        """
        length = math.hypot(self.c, self.s)
        if length == 0:
            return Rot(0.0)
        c = self.c / length
        s = self.s / length
        return Rot(math.atan2(s, c))

    def __getstate__(self):
        """
        Get the state for pickling.
        
        Returns:
            float: The angle in radians.
        """
        return self.angle_radians

    def __setstate__(self, state):
        """
        Set the state from the pickled value.
        
        Args:
            state (float): The angle in radians.
        """
        self.__init__(state)

    @classmethod
    def Identity(cls):
        """
        Get the identity rotation (0 radians).
        
        Returns:
            Rot: The identity rotation.
        """
        return cls(0.0)

    @classmethod
    def Zero(cls):
        """
        Get the zero rotation (0 radians).
        
        Returns:
            Rot: The zero rotation.
        """
        return cls(0.0)

    def inverse(self):
        """
        Get the inverse of this rotation.
        
        Returns:
            Rot: The inverse rotation.
        """
        return Rot(-self.angle_radians)

    def interpolate(self, other, t):
        """
        Interpolate between this rotation and another.
        
        Args:
            other (Rot): The target rotation.
            t (float): The interpolation factor in [0, 1].
        
        Returns:
            Rot: The interpolated rotation.
        """
        angle = self.angle_radians + t * (other.angle_radians - self.angle_radians)
        return Rot(angle)

    def rotate_vector(self, v):
        """
        Rotate a vector using this rotation.
        
        Args:
            v (Vec2 or tuple or list): The vector to rotate.
        
        Returns:
            Vec2: The rotated vector.
        """
        v = Vec2(*v)
        x = self.c * v.x - self.s * v.y
        y = self.c * v.y + self.s * v.x
        return Vec2(x, y)

    def __call__(self, v):
        """
        Rotate a vector using this rotation.
        
        Args:
            v (Vec2 or tuple or list): The vector to rotate.
        
        Returns:
            Vec2: The rotated vector.
        """
        return self.rotate_vector(v)
    
class Transform:
    """Position and rotation transform (like b2Transform)"""
    
    __slots__ = ('p', 'q')
    
    def __init__(self, 
                position = Vec2(0, 0), 
                rotation = Rot(0)):
        self.p = position if isinstance(position, Vec2) else Vec2(*position)
        self.q = rotation if isinstance(rotation, Rot) else Rot(rotation)

    def __call__(self, point) -> Vec2:
        """Transform a point (rotate then translate)"""
        return self.q * point + self.p

    def inverted(self) -> 'Transform':
        """Get inverse transform"""
        inv_rot = Rot.from_sincos(-self.q.s, self.q.c)
        return Transform(inv_rot * (-self.p), inv_rot)
