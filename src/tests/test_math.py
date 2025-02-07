# tests/test_math.py
import pytest
import math
from box2d import Rot, Vec2, Transform
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