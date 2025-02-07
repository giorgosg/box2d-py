# tests/test_vec2.py

import pytest
import math
from box2d import Vec2
from pytest import approx

def aprx(a):
    return approx(a, rel=1e-3, abs=1e-3)

def test_vec2_creation():
    v = Vec2(1.0, 2.0)
    assert v.x == 1.0
    assert v.y == 2.0

def test_vec2_operations():
    v1 = Vec2(1.0, 2.0)
    v2 = Vec2(2.0, 3.0)

    # Test addition
    v3 = v1 + v2
    assert v3 == Vec2(3.0, 5.0)

    # Test subtraction
    v4 = v2 - v1
    assert v4 == Vec2(1.0, 1.0)

    # Test scalar multiplication
    v5 = v1 * 2
    assert v5 == Vec2(2.0, 4.0)

    # Test reverse scalar multiplication
    v6 = 2 * v1
    assert v6 == Vec2(2.0, 4.0)

def test_vec2_equality():
    v1 = Vec2(1.0, 2.0)
    v2 = Vec2(1.0, 2.0)
    v3 = Vec2(2.0, 2.0)

    assert v1 == v2
    assert v1 != v3
    assert v1 == (1.0, 2.0)

def test_vec2_indexing():
    v = Vec2(1.0, 2.0)
    assert v[0] == 1.0
    assert v[1] == 2.0

    with pytest.raises(IndexError):
        _ = v[2]

def test_vec2_iteration():
    v = Vec2(1.0, 2.0)
    components = [x for x in v]
    assert components == [1.0, 2.0]

def test_vec2_repr():
    v = Vec2(1.5, 2.5)
    assert repr(v) == "Vec2(1.5, 2.5)"

def test_dot_product():
    v1 = Vec2(1.0, 2.0)
    v2 = Vec2(3.0, 4.0)
    assert v1.dot(v2) == 11.0

def test_cross_product():
    v1 = Vec2(1.0, 2.0)
    v2 = Vec2(3.0, 4.0)
    assert v1.cross(v2) == -2.0

def test_length():
    v = Vec2(3.0, 4.0)
    assert v.length == 5.0
    assert v.length_squared == 25.0

def test_normalize():
    v = Vec2(3.0, 4.0)
    normalized = v.normalize()
    assert abs(normalized.x) == aprx(0.6) and abs(normalized.y) == aprx(0.8)

def test_angle():
    v = Vec2(1.0, 1.0)
    angle = v.angle
    assert angle == aprx(0.785)

def test_project():
    v1 = Vec2(1.0, 2.0)
    v2 = Vec2(3.0, 4.0)
    proj = v2.project(v1)
    assert proj.x == aprx(2.2)
    assert proj.y == aprx(4.4)

def test_reject():
    v1 = Vec2(1.0, 2.0)
    v2 = Vec2(3.0, 4.0)
    rej = v2.reject(v1)
    assert rej.x == aprx(0.8) 
    assert rej.y == aprx(-0.4)

def test_lerp():
    v1 = Vec2(0.0, 0.0)
    v2 = Vec2(10.0, 10.0)
    lerped = v1.lerp(v2, 0.5)
    assert lerped == Vec2(5.0, 5.0)

def test_perpendicular():
    v = Vec2(1.0, 2.0)
    perp_right = v.perpendicular("right")
    perp_left = v.perpendicular("left")
    assert perp_right == Vec2(2.0, -1.0)
    assert perp_left == Vec2(-2.0, 1.0)

def test_min_max():
    v1 = Vec2(1.0, 2.0)
    v2 = Vec2(3.0, 4.0)
    min_v = v1.min(v2)
    max_v = v1.max(v2)
    assert min_v == Vec2(1.0, 2.0)
    assert max_v == Vec2(3.0, 4.0)

def test_clamp():
    v = Vec2(5.0, 10.0)
    min_vec = Vec2(3.0, 4.0)
    max_vec = Vec2(7.0, 8.0)
    clamped = v.clamp(min_vec, max_vec)
    assert clamped == Vec2(5.0, 8.0)


def test_heading():
    v = Vec2(3.0, 4.0)
    heading = v.heading
    assert heading == v.normalize()

def test_common_vectors():
    assert Vec2.Zero() == Vec2(0.0, 0.0)
    assert Vec2.Right() == Vec2(1.0, 0.0)
    assert Vec2.Left() == Vec2(-1.0, 0.0)
    assert Vec2.Up() == Vec2(0.0, -1.0)
    assert Vec2.Down() == Vec2(0.0, 1.0)

def test_from_angle():
    v = Vec2.FromAngle(math.pi/2)  # 90 degrees (pointing up)
    assert v.x == aprx(0.0) and v.y == aprx(1.0)

def test_inverse():
    v = Vec2(1.0, -2.0)
    inv = v.inverse()
    assert inv == Vec2(-1.0, 2.0)

def test_rotate():
    v = Vec2(1.0, 0.0)
    rotated = v.rotate(math.pi/2)  # 90 degrees
    assert rotated.x == aprx(0.0) and rotated.y == aprx(1.0)
