# tests/test_math.py
import pytest
import math
from box2d import Rot, Vec2, Transform, AABB
from pytest import approx

def aprx(a):
    return approx(a, rel=1e-3, abs=1e-3)

def test_rot_callable():
    # Test __call__ method of Rot
    rot = Rot.FromAngle(math.pi/2)  # 90 degrees
    v = Vec2(1.0, 0.0)
    rotated_v = rot(v)
    assert rotated_v.x == aprx(0.0)
    assert rotated_v.y == aprx(1.0)

def test_transform_init():
    # Test Transform initialization
    pos = Vec2(1.0, 2.0)
    rot = Rot.FromAngle(math.pi/4)
    t = Transform(pos, rot)
    assert t.p == pos
    assert t.q == rot

def test_transform_call():
    # Test Transform __call__ method
    pos = Vec2(1.0, 2.0)
    rot = Rot.FromAngle(math.pi/4)
    t = Transform(pos, rot)
    
    # Test with a point
    point = Vec2(1.0, 0.0)
    transformed_point = t(point)
    assert transformed_point.x == aprx(1.0 + math.cos(math.pi/4))
    assert transformed_point.y == aprx(2.0 + math.sin(math.pi/4))

def test_transform_inverted():
    # Test inverted transform
    pos = Vec2(1.0, 2.0)
    rot = Rot.FromAngle(math.pi/4)
    t = Transform(pos, rot)
    
    inv_t = t.inverted()
    
    # Test that applying transform and then inverse transform returns to original
    point = Vec2(1.0, 0.0)
    transformed = t(point)
    inverse_transformed = inv_t(transformed)
    assert inverse_transformed.x == aprx(1.0)
    assert inverse_transformed.y == aprx(0.0)

def test_aabb_init():
    aabb = AABB()
    assert aabb.lower == Vec2(math.inf, math.inf)
    assert aabb.upper == Vec2(-math.inf, -math.inf)
    assert not aabb.is_valid

def test_aabb_from_points():
    aabb = AABB.from_points([(1,2), (3,4)])
    assert aabb.lower == Vec2(1.0, 2.0)
    assert aabb.upper == Vec2(3.0, 4.0)

def test_aabb_properties():
    aabb = AABB(lower=(1,2), upper=(3,4))
    assert aabb.center == Vec2(2.0, 3.0)
    assert aabb.half_size == Vec2(1.0, 1.0)
    assert aabb.width == 2.0
    assert aabb.height == 2.0

def test_aabb_contains():
    aabb1 = AABB(lower=(1,1), upper=(3,3))
    aabb2 = AABB(lower=(2,2), upper=(2,2))
    assert aabb1.contains(aabb2)
    assert not aabb2.contains(aabb1)

def test_aabb_merge():
    aabb = AABB()
    aabb.merge(Vec2(1,2))
    assert aabb.lower == Vec2(1.0, 2.0)
    assert aabb.upper == Vec2(1.0, 2.0)
    
    other_aabb = AABB(lower=(0,0), upper=(2,4))
    aabb.merge(other_aabb)
    assert aabb.lower == Vec2(0.0, 0.0)
    assert aabb.upper == Vec2(2.0, 4.0)

def test_aabb_intersection():
    aabb1 = AABB(lower=(1,1), upper=(3,3))
    aabb2 = AABB(lower=(2,2), upper=(4,4))
    overlap = aabb1 & aabb2
    assert overlap.lower == Vec2(2.0, 2.0)
    assert overlap.upper == Vec2(3.0, 3.0)
    
    # Non-overlapping case
    aabb3 = AABB(lower=(5,5), upper=(6,6))
    overlap = aabb1 & aabb3
    assert not overlap.is_valid

def test_aabb_equality():
    aabb1 = AABB(lower=(1,1), upper=(2,2))
    aabb2 = AABB(lower=(1,1), upper=(2,2))
    assert aabb1 == aabb2
    
    aabb3 = AABB(lower=(1,1), upper=(3,3))
    assert aabb1 != aabb3

def test_aabb_edge_cases():
    # Single point
    aabb = AABB.from_points([(1,1)])
    assert aabb.lower == Vec2(1.0, 1.0)
    assert aabb.upper == Vec2(1.0, 1.0)
    
    # Multiple points with same x/y
    aabb = AABB.from_points([(1,1), (1,2)])
    assert aabb.lower == Vec2(1.0, 1.0)
    assert aabb.upper == Vec2(1.0, 2.0)