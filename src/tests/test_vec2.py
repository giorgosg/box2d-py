# tests/test_vec2.py

import pytest
from box2d import Vec2

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
