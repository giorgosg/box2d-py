# tests/test_rot.py

import pytest
import math
from box2d import Rot, Vec2
from pytest import approx

def aprx(a):
    return approx(a, rel=1e-3, abs=1e-3)

def test_rot_creation():
    rot = Rot(0.0)
    assert rot.c == 1.0
    assert rot.s == 0.0

    rot = Rot(math.pi/2)
    assert rot.c == aprx(0.0)
    assert rot.s == aprx(1.0)

def test_rot_from_angle():
    rot = Rot(math.pi/4)
    assert rot.c == aprx(math.cos(math.pi/4))
    assert rot.s == aprx(math.sin(math.pi/4))

def test_rot_multiplication():
    rot1 = Rot(math.pi/4)
    rot2 = Rot(math.pi/2)
    combined = rot1 * rot2
    assert combined.angle_radians == aprx(3 * math.pi / 4)

def test_rot_equality():
    rot1 = Rot(math.pi/2)
    rot2 = Rot(math.pi/2)
    assert rot1 == rot2

    rot3 = Rot(math.pi/4)
    assert rot1 != rot3

def test_rot_string_representation():
    rot = Rot(math.pi/2)
    assert str(rot) == f"Rot(c={rot.c:.6f}, s={rot.s:.6f})"

def test_rot_repr():
    rot = Rot(math.pi/2)
    assert repr(rot).startswith("Rot(")

def test_rot_normalization():
    rot = Rot(0.0)
    normalized = rot.normalize()
    assert normalized.c == 1.0
    assert normalized.s == 0.0

def test_rot_identity():
    identity = Rot.Identity()
    assert identity.c == 1.0
    assert identity.s == 0.0

def test_rot_zero():
    zero = Rot.Zero()
    assert zero.c == 1.0
    assert zero.s == 0.0

def test_rot_inverse():
    rot = Rot(math.pi/4)
    inverse = rot.inverse()
    assert inverse.angle_radians == aprx(-math.pi/4)

def test_rot_interpolate():
    rot1 = Rot(0.0)
    rot2 = Rot(math.pi/2)
    interpolated = rot1.interpolate(rot2, 0.5)
    assert interpolated.angle_radians == aprx(math.pi/4)

def test_rot_rotate_vector():
    rot = Rot(math.pi/2)
    v = Vec2(1.0, 0.0)
    rotated_v = rot.rotate_vector(v)
    assert rotated_v.x == aprx(0.0)
    assert rotated_v.y == aprx(1.0)

def test_rot_angle_properties():
    rot = Rot(math.pi/4)
    assert rot.angle_radians == aprx(math.pi/4)
    assert rot.angle_degrees == aprx(45.0)

def test_rot_edge_cases():
    rot = Rot(0.0)
    assert rot.angle_radians == 0.0

    rot = Rot(math.pi)
    assert rot.angle_radians == aprx(math.pi)