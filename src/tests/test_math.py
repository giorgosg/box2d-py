# tests/test_math.py
import pytest
import doctest
import math
from box2d import Vec2, Rot, Transform, AABB, Mat22
from box2d import math as box2d_math


def test_doctests():
    # Run doctests for the specific submodule
    results = doctest.testmod(box2d_math)
    assert results.failed == 0


def test_vec2_normalize_zero_vector():
    v = Vec2(0, 0)
    normalized = v.normalize()
    assert normalized == Vec2(0, 0), "Normalizing zero vector should return zero"


def test_vec2_project_onto_zero_vector_raises_error():
    v = Vec2(1, 1)
    with pytest.raises(ValueError):
        v.project((0, 0))


def test_vec2_lerp_extrapolation():
    a = Vec2(1, 2)
    b = Vec2(3, 4)
    result = a.lerp(b, 2.5)
    expected = Vec2(1 + 2 * 2.5, 2 + 2 * 2.5)
    assert result == expected, "Lerp should extrapolate when t > 1"


def test_vec2_rotation_45_degrees():
    v = Vec2(1, 0)
    rotated = v.rotate(math.pi / 4)
    expected = Vec2(math.sqrt(2) / 2, math.sqrt(2) / 2)
    assert rotated.x == pytest.approx(expected.x)
    assert rotated.y == pytest.approx(expected.y)


def test_rot_composition():
    rot1 = Rot(math.pi / 2)
    rot2 = Rot(math.pi / 2)
    combined = rot1 * rot2
    assert combined.angle_radians == pytest.approx(math.pi)


def test_rot_normalization():
    # Create non-unit rotation
    rot = Rot.from_sincos(2, 2).normalize()
    assert math.isclose(math.hypot(rot.s, rot.c), 1.0, rel_tol=1e-9)


def test_transform_inverse():
    t = Transform(Vec2(2, 3), Rot(math.pi / 3))
    point = Vec2(5, 7)
    transformed = t.inverse(t(point))
    assert transformed.x == pytest.approx(point.x)
    assert transformed.y == pytest.approx(point.y)


def test_aabb_from_multiple_points():
    points = [(-2, 5), (3, -1), (4, 4), (0, 0)]
    aabb = AABB.from_points(points)
    assert aabb.lower == Vec2(-2, -1)
    assert aabb.upper == Vec2(4, 5)


def test_aabb_intersection_complex():
    a = AABB((0, 0), (5, 5))
    b = AABB((3, 3), (7, 7))
    intersection = a & b
    assert intersection.lower == Vec2(3, 3)
    assert intersection.upper == Vec2(5, 5)
    assert intersection.is_valid


def test_mat22_solve_singular():
    # Create singular matrix (determinant zero)
    mat = Mat22(1, 2, 2, 4)
    result = mat.solve(Vec2(3, 6))
    assert result == Vec2(0, 0), "Should return zero vector for singular matrix"


def test_componentwise_multiplication():
    v1 = Vec2(2, -3)
    v2 = Vec2(-4, 5)
    result = v1.multiply_componentwise(v2)
    assert result == Vec2(-8, -15)


def test_mat22_inversion():
    original = Mat22(2, 1, 1, 2)
    inverse = original.inverse
    identity = original * inverse  # Should approximate identity
    assert identity.rows[0].x == pytest.approx(1)
    assert identity.rows[1].y == pytest.approx(1)


def test_aabb_contraction():
    aabb = AABB((1, 1), (3, 3)).expanded(-0.5)
    assert aabb == AABB((1.5, 1.5), (2.5, 2.5))


def test_rot_pickle_roundtrip():
    import pickle

    original = Rot(math.pi / 3)
    reconstructed = pickle.loads(pickle.dumps(original))
    assert original == reconstructed
