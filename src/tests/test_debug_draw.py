# tests/test_debug_draw.py
import pytest
import doctest
from box2d import DebugDraw, World, Vec2
import box2d.debug_draw as debug_draw


def test_doctests():
    # Run doctests for the specific submodule
    results = doctest.testmod(debug_draw)
    assert results.failed == 0


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

    def draw_solid_polygon(self, transform, vertices, radius, color):
        self.draw_polygon_count += 1

    def draw_circle(self, center, radius, color):
        self.draw_circle_count += 1

    def draw_solid_circle(self, transform, center, radius, color):
        self.draw_solid_circle_count += 1

    def draw_segment(self, p1, p2, color):
        self.draw_segment_count += 1

    def draw_point(self, p, size, color):
        self.draw_point_count += 1

    def draw_string(self, p, s, color):
        self.draw_string_count += 1

    def draw_transform(self, transform):
        self.draw_transform_count += 1


def test_debug_draw_callbacks():
    # Setup world and debug drawer
    world = World(gravity=(0, -10))
    debug_draw = MockDebugDraw()

    # Add a dynamic body with a box
    body = world.new_body().dynamic().position(0, 0).build().add_box(1, 1)

    # Step and trigger debug drawing
    world.step(1 / 60)  # Simulate a physics step
    world.draw(debug_draw)  # Explicitly draw

    # Verify at least one polygon was drawn
    assert debug_draw.draw_polygon_count > 0


def test_draw_circle():
    world = World(gravity=(0, -10))
    debug_draw = MockDebugDraw()
    debug_draw.draw_shapes = True

    # Add a dynamic body with a circle
    body = world.new_body().dynamic().position(0, 0).build().add_circle(1)

    # Step and draw
    world.step(1 / 60)
    world.draw(debug_draw)

    # Verify circle was drawn
    assert debug_draw.draw_solid_circle_count > 0


def test_draw_shapes_property():
    """Box2D 3.2 flipped this default to True, so test the toggle, not the default."""
    debug_draw = DebugDraw()

    debug_draw.draw_shapes = True
    assert debug_draw.draw_shapes is True

    debug_draw.draw_shapes = False
    assert debug_draw.draw_shapes is False


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


def test_draw_contacts():
    """Test contact point visualization"""
    world = World(gravity=(0, -10))
    debug_draw = MockDebugDraw()
    debug_draw.draw_contacts = True

    # Create two colliding boxes
    body1 = world.new_body().dynamic().position(0, 0).build().add_box(2, 2)
    body2 = world.new_body().dynamic().position(0, 2).build().add_box(2, 2)

    world.step(1 / 60)  # Let them collide
    world.draw(debug_draw)

    # Verify contact points were drawn
    assert debug_draw.draw_point_count > 0


def test_color_parsing():
    """Test color conversion from hex values"""
    color = debug_draw.Color.from_b2HexColor(0x3366FF)
    assert color.r == 0x33 and color.g == 0x66 and color.b == 0xFF
    assert color.a == 255  # Default alpha

    color_with_alpha = debug_draw.Color.from_b2HexColor(0x123456)
    color_with_alpha.a = 128
    assert color_with_alpha.hex == 0x123456  # Alpha not part of hex


# --- view culling ------------------------------------------------------------


def test_drawing_bounds_round_trips():
    from box2d import AABB, DebugDraw, Vec2

    draw = DebugDraw()
    assert draw.drawing_bounds.upper.x > 1e30, "unset means draw everything"

    draw.drawing_bounds = AABB(lower=Vec2(-5, -3), upper=Vec2(5, 3))
    bounds = draw.drawing_bounds
    assert (bounds.lower.x, bounds.lower.y) == (-5.0, -3.0)
    assert (bounds.upper.x, bounds.upper.y) == (5.0, 3.0)


def test_drawing_bounds_culls_what_is_off_screen():
    """Box2D queries its broad-phase tree with this, so an off-screen shape
    never reaches a callback -- it is not drawn and clipped, it is skipped.

    This was left at the float range, so the testbed drew every shape in the
    world however far outside the view it was.
    """
    from box2d import AABB, DebugDraw, Vec2, World

    class Counter(DebugDraw):
        def __init__(self):
            super().__init__()
            self.count = 0

        def draw_solid_polygon(self, transform, vertices, radius, color):
            self.count += 1

    world = World()
    for x in range(-50, 51, 5):
        body = world.add_body(body_type="dynamic", position=(x, 0))
        body.add_box(1, 1)
    world.step(1 / 60, 4)

    everything = Counter()
    world.draw(everything)

    narrow = Counter()
    narrow.drawing_bounds = AABB(lower=Vec2(-6, -6), upper=Vec2(6, 6))
    world.draw(narrow)

    assert everything.count == 21, "all of them, with no bounds set"
    assert 0 < narrow.count < everything.count, "only the ones in view"
    world.destroy()


def test_both_renderers_cull_to_their_camera():
    """Whichever renderer is in use, it should not be drawing the whole world
    when the camera is looking at a corner of it."""
    import ast
    import pathlib

    for name in ("debug_draw_gl.py", "debug_draw_imgui.py"):
        source = pathlib.Path("src/box2d_testbed", name).read_text()
        tree = ast.parse(source)
        # Find start_frame properly rather than slicing text: the two files
        # put the call at different depths, and a fixed slice missed one.
        start_frames = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "start_frame"
        ]
        assert start_frames, f"{name} has no start_frame"
        body = "\n".join(ast.unparse(node) for node in start_frames)
        assert "drawing_bounds" in body, f"{name} does not cull to its camera"
