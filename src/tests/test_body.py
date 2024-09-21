import box2d
import pytest

def test_create():
    world = box2d.World(gravity=(0, -10))
    groundbody = world.create_body(position=(0, -10))
    groundbody.create_box((50, 10))
    dynbody = world.create_body(position=(0, 4.0), type=box2d.body.DYNAMIC)
    dynbody.create_box(dimensions=(1.0, 1.0), density=1.0, friction=0.3)


