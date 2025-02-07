# tests/test_world.py

import pytest
import box2d

def test_import():
    assert box2d is not None

def test_world():
    world = box2d.World()
    assert world is not None

def test_gravity():
    world = box2d.World(gravity=(0, -10))
    assert world is not None

def invalidgrav():
    world = box2d.World(gravity=-10)

def test_invalid():
    with pytest.raises(Exception):
        invalidgrav()


