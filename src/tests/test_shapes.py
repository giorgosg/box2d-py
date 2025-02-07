# tests/test_shapes.py

import pytest
from box2d import World, Vec2
from box2d._box2d import lib
from pytest import approx
def test_capsule_shape():
    world = World()
    body = world.new_body().dynamic().position(0, 0).build()
    
    body.add_capsule(point1=(-1, 0), point2=(1, 0), radius=0.5)
    
    assert lib.b2Body_GetShapeCount(body._body_id) == 1
    shape_type = lib.b2Shape_GetType(body._shapes[0]._shape_id)
    assert shape_type == lib.b2_capsuleShape

def test_segment_shape():
    world = World()
    body = world.new_body().static().build()
    
    body.add_segment(point1=(-2, 0), point2=(2, 0))
    
    assert lib.b2Body_GetShapeCount(body._body_id) == 1
    assert lib.b2Shape_GetType(body._shapes[0]._shape_id) == lib.b2_segmentShape

def test_shape_properties():
    world = World()
    body = world.new_body().build()
    
    shape = body.add_box(1, 1, density=2.0, friction=0.5, restitution=0.8)
    
    assert lib.b2Shape_GetDensity(shape._shape_id) == approx(2.0)
    assert lib.b2Shape_GetFriction(shape._shape_id) == approx(0.5)
    assert lib.b2Shape_GetRestitution(shape._shape_id) == approx(0.8)

def test_sensor_shape_events():
    world = World()
    body = world.new_body().build()
    
    sensor_shape = body.add_capsule(
        point1=(-1, 0), point2=(1, 0), radius=0.3, 
        is_sensor=True
    )
    
    assert lib.b2Shape_IsSensor(sensor_shape._shape_id) is True

def test_polygon_shape():
    world = World()
    body = world.new_body().dynamic().position(0, 0).build()
    
    # Valid convex polygon
    vertices = [(-1, -1), (1, -1), (1, 1), (0, 2), (-1, 1)]
    poly_shape = body.add_polygon(vertices=vertices)
    
    assert lib.b2Shape_GetType(poly_shape._shape_id) == lib.b2_polygonShape
  
def test_invalid_polygon():
    world = World()
    body = world.new_body().build()
    
    # Too few vertices
    with pytest.raises(ValueError):
        body.add_polygon(vertices=[(0,0), (1,0)])
    
    # Too many vertices
    with pytest.raises(ValueError):
        body.add_polygon(vertices=[(i,i) for i in range(9)])

def test_polygon_properties():
    world = World()
    body = world.new_body().build()
    
    triangle = [(0,0), (1,0), (0.5, 1)]
    poly = body.add_polygon(
        vertices=triangle,
        density=1.5,
        friction=0.3,
        restitution=0.7,
        is_sensor=True
    )
    
    assert lib.b2Shape_GetDensity(poly._shape_id) == approx(1.5)
    assert lib.b2Shape_GetFriction(poly._shape_id) == approx(0.3)
    assert lib.b2Shape_GetRestitution(poly._shape_id) == approx(0.7)
    assert lib.b2Shape_IsSensor(poly._shape_id) is True
