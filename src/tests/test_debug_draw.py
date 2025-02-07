# tests/test_debug_draw.py
import pytest
from box2d import DebugDraw, World, Vec2

@pytest.fixture
def world():
    return World(gravity=(0, -10))

@pytest.fixture
def debug_draw():
    return DebugDraw()

@pytest.fixture
def dynamic_body(world):
    builder = world.new_body().dynamic().position(0, 0)
    body = builder.add_box(1, 1).build()
    return body

class MockDebugDraw(DebugDraw):
    def __init__(self):
        super().__init__()
        self.draw_polygon_count = 0
        self.draw_circle_count = 0
        self.draw_segment_count = 0
        self.draw_point_count = 0
        self.draw_string_count = 0
        self.draw_transform_count = 0
        self.draw_solid_circle_count = 0

        self.draw_shapes = True

    def _draw_solid_polygon(self, transform, vertices, count, radius, color):
        self.draw_polygon_count += 1

    def _draw_circle(self, center, radius, color):
        self.draw_circle_count += 1

    def _draw_solid_circle(self, transform, radius, color):
        self.draw_solid_circle_count += 1

    def _draw_segment(self, p1, p2, color):
        self.draw_segment_count += 1

    def _draw_point(self, p, size, color):
        self.draw_point_count += 1

    def _draw_string(self, p, s, color):
        self.draw_string_count += 1

    def _draw_transform(self, transform):
        self.draw_transform_count += 1

def test_debug_draw_callbacks():
    # Setup world and debug drawer
    world = World(gravity=(0, -10))
    debug_draw = MockDebugDraw()
    
    # Add a dynamic body with a box
    body = (
        world.new_body()
        .dynamic()
        .position(0, 0)
        .build()
        .add_box(1, 1)
    )
    
    # Step and trigger debug drawing
    world.step(1/60)  # Simulate a physics step
    world.draw(debug_draw)  # Explicitly draw
    
    # Verify at least one polygon was drawn
    assert debug_draw.draw_polygon_count > 0

def test_draw_circle():
    world = World(gravity=(0, -10))
    debug_draw = MockDebugDraw()
    debug_draw.draw_shapes = True
    
    # Add a dynamic body with a circle
    body = (
        world.new_body()
        .dynamic()
        .position(0, 0)
        .build()
        .add_circle(1)
    )
    
    # Step and draw
    world.step(1/60)
    world.draw(debug_draw)
    
    # Verify circle was drawn
    assert debug_draw.draw_solid_circle_count > 0

def test_draw_shapes_property():
    debug_draw = DebugDraw()
    assert debug_draw.draw_shapes is False
    
    debug_draw.draw_shapes = True
    assert debug_draw.draw_shapes is True

def test_draw_aabbs_property():
    debug_draw = DebugDraw()
    assert debug_draw.draw_aabbs is False
    
    debug_draw.draw_aabbs = True
    assert debug_draw.draw_aabbs is True

def test_draw_joints_property():
    debug_draw = DebugDraw()
    assert debug_draw.draw_joints is False
    
    debug_draw.draw_joints = True
    assert debug_draw.draw_joints is True
