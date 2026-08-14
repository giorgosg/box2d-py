# tests/test_shapes.py

import pytest
from box2d import World, Vec2, AABB
from box2d.shape import Circle, Capsule, Segment, Polygon, Box, Chain
from box2d.material import SurfaceMaterial
from box2d.collision_filter import CollisionFilter
from box2d.dataclasses import MassData, CastResult


@pytest.fixture
def world():
    return World()


@pytest.fixture
def static_body(world):
    return world.new_body().static().build()


@pytest.fixture
def dynamic_body(world):
    return world.new_body().dynamic().position(0, 0).build()


def test_circle_shape(dynamic_body):
    circle = dynamic_body.add_circle(radius=0.5)

    assert len(dynamic_body._shapes) == 1
    assert isinstance(circle, Circle)
    assert circle.body == dynamic_body


def test_capsule_shape(dynamic_body):
    capsule = dynamic_body.add_capsule(point1=(-1, 0), point2=(1, 0), radius=0.5)

    assert len(dynamic_body._shapes) == 1
    assert isinstance(capsule, Capsule)
    assert capsule.body == dynamic_body


def test_segment_shape(static_body):
    segment = static_body.add_segment(point1=(-2, 0), point2=(2, 0))

    assert len(static_body._shapes) == 1
    assert isinstance(segment, Segment)
    assert segment.body == static_body


def test_shape_properties_creation(dynamic_body):
    shape = dynamic_body.add_box(1, 1, density=2.0, friction=0.5, restitution=0.8)

    assert isinstance(shape, Box)
    assert shape.density == pytest.approx(2.0)
    assert shape.friction == pytest.approx(0.5)
    assert shape.restitution == pytest.approx(0.8)


def test_sensor_shape(dynamic_body):
    sensor = dynamic_body.add_capsule(
        point1=(-1, 0), point2=(1, 0), radius=0.3, is_sensor=True
    )

    assert sensor.is_sensor is True


def test_polygon_shape(dynamic_body):
    # Valid convex polygon
    vertices = [(-1, -1), (1, -1), (1, 1), (0, 2), (-1, 1)]
    poly = dynamic_body.add_polygon(vertices=vertices)

    assert isinstance(poly, Polygon)
    assert len(dynamic_body._shapes) == 1


def test_invalid_polygon(dynamic_body):
    # Too few vertices
    with pytest.raises(ValueError):
        dynamic_body.add_polygon(vertices=[(0, 0), (1, 0)])

    # Too many vertices
    with pytest.raises(ValueError):
        dynamic_body.add_polygon(vertices=[(i, i) for i in range(9)])


def test_shape_setters(dynamic_body):
    shape = dynamic_body.add_box(1, 1)

    # Test density setter
    shape.density = 1.5
    assert shape.density == pytest.approx(1.5)

    # Test friction setter
    shape.friction = 0.7
    assert shape.friction == pytest.approx(0.7)

    # Test restitution setter
    shape.restitution = 0.6
    assert shape.restitution == pytest.approx(0.6)


def test_box_shape(dynamic_body):
    box = dynamic_body.add_box(width=1.0, height=0.5)

    assert isinstance(box, Box)
    assert isinstance(box, Polygon)  # Box inherits from Polygon


def test_chain_shape(static_body):
    # A valid chain requires at least 4 vertices
    vertices = [(0, 0), (1, 0), (1, 1), (0, 1)]
    chain = static_body.add_chain(
        vertices=vertices, loop=True, friction=0.25, restitution=0.1
    )

    assert isinstance(chain, Chain)
    assert len(chain.segments) == 4  # One segment for each edge

    # Test that segments reference the chain properly
    for segment in chain.segments:
        assert segment.parent_chain == chain
        assert segment.body == static_body


def test_chain_shape_invalid(static_body):
    # Providing fewer than 4 vertices should raise a ValueError
    vertices = [(0, 0), (1, 0), (0.5, 1)]
    with pytest.raises(ValueError):
        static_body.add_chain(vertices=vertices)


def test_material_property(dynamic_body):
    shape = dynamic_body.add_circle(radius=0.5)

    # Test getting the material ID
    default_material = shape.material
    assert isinstance(default_material, int)

    # Test setting a new material ID
    shape.material = 42
    assert shape.material == 42

    # Test with SurfaceMaterial object
    custom_material = SurfaceMaterial(friction=0.8)
    shape.material = custom_material
    assert shape.material == custom_material.material


def test_shape_collision_filter(dynamic_body):
    shape = dynamic_body.add_box(1, 1)

    custom_filter = CollisionFilter(category=0x0002, mask=0x0004, group=3)
    shape.filter = custom_filter

    retrieved_filter = shape.filter
    assert retrieved_filter.category == 0x0002
    assert retrieved_filter.mask == 0x0004
    assert retrieved_filter.group == 3


# New tests for previously untested properties and methods


def test_event_flags(dynamic_body):
    """Test enable_contact_events, enable_pre_solve_events, enable_hit_events properties"""
    shape = dynamic_body.add_circle(radius=0.5)

    # Contact events
    assert not shape.enable_contact_events  # Should be False by default
    shape.enable_contact_events = True
    assert shape.enable_contact_events is True

    # Pre-solve events
    assert not shape.enable_pre_solve_events  # Should be False by default
    shape.enable_pre_solve_events = True
    assert shape.enable_pre_solve_events is True

    # Hit events
    assert not shape.enable_hit_events  # Should be False by default
    shape.enable_hit_events = True
    assert shape.enable_hit_events is True


def test_shape_introspection_properties(dynamic_body, world):
    """Test shape_type, world, aabb, mass_data properties"""
    shape = dynamic_body.add_circle(radius=0.5)

    # Test shape_type property
    assert isinstance(shape.shape_type, int)

    # Test world property
    assert shape.world == world

    # Test aabb property
    aabb = shape.aabb
    assert isinstance(aabb, AABB)
    assert aabb.lower.x < aabb.upper.x
    assert aabb.lower.y < aabb.upper.y

    # Test mass_data property
    mass_data = shape.mass_data
    assert isinstance(mass_data, MassData)
    assert mass_data.mass > 0
    assert isinstance(mass_data.center, Vec2)
    assert mass_data.rotational_inertia >= 0


def test_shape_validity_and_collision_methods(dynamic_body):
    """Test is_valid, test_point, ray_cast, get_closest_point methods"""
    shape = dynamic_body.add_circle(radius=1.0, center=(0, 0))

    # Test is_valid
    assert shape.is_valid() is True

    # Test test_point
    assert shape.test_point((0, 0)) is True  # Point at center should be inside
    assert shape.test_point((1.5, 0)) is False  # Point outside radius should be outside

    # Test ray_cast
    hit_result = shape.ray_cast(
        (-2, 0), (4, 0)
    )  # Ray from left to right through circle
    assert hit_result is not None
    assert isinstance(hit_result, CastResult)
    assert isinstance(hit_result.point, Vec2)
    assert isinstance(hit_result.normal, Vec2)
    assert 0 < hit_result.fraction < 1

    miss_result = shape.ray_cast((-2, 2), (4, 0))  # Ray above the circle
    assert miss_result is None

    # Test get_closest_point
    closest = shape.get_closest_point((2, 0))
    assert isinstance(closest, Vec2)
    assert abs(closest.x) <= 1.0  # Should be on the circle boundary
    assert abs(closest.y) <= 1.0


def test_contact_and_sensor_methods(world):
    """Test contact_data, contact_capacity, sensor_overlaps and sensor_capacity"""
    body1 = world.new_body().dynamic().position(0, 0).build()
    shape1 = body1.add_circle(radius=1.0)

    body2 = (
        world.new_body().static().position(5, 0).build()
    )  # Far apart, no contact initially
    shape2 = body2.add_box(1, 1)

    # Test contact_capacity
    assert shape1.contact_capacity == 0  # No contacts initially

    # Test contact_data
    contacts = shape1.contact_data
    assert isinstance(contacts, list)
    assert len(contacts) == 0  # No contacts initially

    # Test contact_data property
    assert len(shape1.contact_data) == 0

    # Create a sensor shape and test sensor methods
    body3 = world.new_body().static().position(0, 0).build()
    sensor = body3.add_circle(radius=2.0, is_sensor=True)

    # Test sensor_capacity
    assert sensor.sensor_capacity >= 0

    # Test sensor_overlaps
    overlaps = sensor.sensor_overlaps
    assert isinstance(overlaps, list)

    # Test sensor_overlaps property
    assert isinstance(sensor.sensor_overlaps, list)


def test_sensor_actually_detects_overlap(world):
    """A sensor must report shapes that overlap it, and emit a begin event.

    The pre-existing sensor tests only assert types, so they stayed green when
    Box2D 3.1 made shape.enable_sensor_events opt-in and sensors silently
    stopped detecting anything.
    """
    sensor_body = world.new_body().static().position(0, 0).build()
    sensor = sensor_body.add_box(4, 4, is_sensor=True)

    visitor = world.new_body().dynamic().position(0, 0).build()
    visitor.add_circle(radius=0.5)

    world.step(1 / 60, 4)

    assert len(sensor.sensor_overlaps) == 1
    assert len(world.get_sensor_events().begin) == 1


def test_sensor_events_can_be_disabled_per_shape(world):
    """A shape opting out of sensor events must not be detected."""
    sensor_body = world.new_body().static().position(0, 0).build()
    sensor = sensor_body.add_box(4, 4, is_sensor=True)

    visitor = world.new_body().dynamic().position(0, 0).build()
    visitor.add_circle(radius=0.5, enable_sensor_events=False)

    world.step(1 / 60, 4)

    assert sensor.sensor_overlaps == []


def test_chain_segments(static_body):
    """Test ChainSegment class and its properties"""
    vertices = [(0, 0), (3, 0), (3, 3), (0, 3)]
    chain = static_body.add_chain(vertices=vertices, loop=True)

    # Test that we have the right number of segments
    assert len(chain.segments) == 4

    # Test segment properties
    for segment in chain.segments:
        # Test parent chain reference
        assert segment.parent_chain == chain

        # Test body reference
        assert segment.body == static_body

        # Test shape properties
        assert hasattr(segment, "friction")
        assert hasattr(segment, "restitution")

        # Test valid shape
        assert segment.is_valid()


def test_shape_multiple_materials(static_body):
    """Test creating a chain with multiple materials"""
    vertices = [(0, 0), (3, 0), (3, 3), (0, 3)]

    # Create two different materials
    mat1 = SurfaceMaterial(friction=0.1, restitution=0.9)
    mat2 = SurfaceMaterial(friction=0.9, restitution=0.1)

    chain = static_body.add_chain(
        vertices=vertices,
        loop=True,
        materials=[mat1, mat2, mat1, mat2, mat1],  # One material per segment
    )

    # Test that segments have different materials
    assert chain.segments[0].material != chain.segments[1].material
    assert chain.segments[0].material == chain.segments[2].material
    assert chain.segments[1].material == chain.segments[3].material


def test_circle_get_set_geometry(dynamic_body):
    """Test the geometry property for Circle shapes."""
    # Create a circle with known dimensions
    initial_radius = 0.5
    initial_center = (1.0, 2.0)
    circle = dynamic_body.add_circle(radius=initial_radius, center=initial_center)

    # Get the geometry and verify initial values
    circle_def = circle.geometry
    assert circle_def.radius == pytest.approx(initial_radius)
    assert circle_def.center.x == pytest.approx(1.0)
    assert circle_def.center.y == pytest.approx(2.0)

    # Modify the geometry
    new_radius = 1.5
    new_center = Vec2(3.0, 4.0)
    from box2d.shapedef import CircleDef

    new_circle_def = CircleDef(radius=new_radius, center=new_center)
    circle.geometry = new_circle_def

    # Get the updated geometry and verify changes
    updated_def = circle.geometry
    assert updated_def.radius == pytest.approx(new_radius)
    assert updated_def.center.x == pytest.approx(3.0)
    assert updated_def.center.y == pytest.approx(4.0)


def test_capsule_get_set_geometry(dynamic_body):
    """Test the geometry property for Capsule shapes."""
    # Create a capsule with known dimensions
    initial_point1 = (-1.0, 0.5)
    initial_point2 = (1.0, 0.5)
    initial_radius = 0.3
    capsule = dynamic_body.add_capsule(
        point1=initial_point1, point2=initial_point2, radius=initial_radius
    )

    # Get the geometry and verify initial values
    capsule_def = capsule.geometry
    assert capsule_def.vertex1.x == pytest.approx(-1.0)
    assert capsule_def.vertex1.y == pytest.approx(0.5)
    assert capsule_def.vertex2.x == pytest.approx(1.0)
    assert capsule_def.vertex2.y == pytest.approx(0.5)
    assert capsule_def.radius == pytest.approx(initial_radius)

    # Modify the geometry
    from box2d.shapedef import CapsuleDef

    new_capsule_def = CapsuleDef(
        vertex1=Vec2(-2.0, 1.0), vertex2=Vec2(2.0, 1.0), radius=0.6
    )
    capsule.geometry = new_capsule_def

    # Get the updated geometry and verify changes
    updated_def = capsule.geometry
    assert updated_def.vertex1.x == pytest.approx(-2.0)
    assert updated_def.vertex1.y == pytest.approx(1.0)
    assert updated_def.vertex2.x == pytest.approx(2.0)
    assert updated_def.vertex2.y == pytest.approx(1.0)
    assert updated_def.radius == pytest.approx(0.6)


def test_segment_get_set_geometry(static_body):
    """Test the geometry property for Segment shapes."""
    # Create a segment with known dimensions
    initial_point1 = (-3.0, 0.0)
    initial_point2 = (3.0, 0.0)
    segment = static_body.add_segment(point1=initial_point1, point2=initial_point2)

    # Get the geometry and verify initial values
    segment_def = segment.geometry
    assert segment_def.vertex1.x == pytest.approx(-3.0)
    assert segment_def.vertex1.y == pytest.approx(0.0)
    assert segment_def.vertex2.x == pytest.approx(3.0)
    assert segment_def.vertex2.y == pytest.approx(0.0)

    # Modify the geometry
    from box2d.shapedef import SegmentDef

    new_segment_def = SegmentDef(vertex1=Vec2(0.0, -2.0), vertex2=Vec2(0.0, 2.0))
    segment.geometry = new_segment_def

    # Get the updated geometry and verify changes
    updated_def = segment.geometry
    assert updated_def.vertex1.x == pytest.approx(0.0)
    assert updated_def.vertex1.y == pytest.approx(-2.0)
    assert updated_def.vertex2.x == pytest.approx(0.0)
    assert updated_def.vertex2.y == pytest.approx(2.0)


def test_polygon_get_set_geometry(dynamic_body):
    """Test the geometry property for Polygon shapes."""
    # Create a polygon with known dimensions (a simple square)
    initial_vertices = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    polygon = dynamic_body.add_polygon(vertices=initial_vertices)

    # Get the geometry and verify we have a polygon with 4 vertices
    polygon_def = polygon.geometry
    assert len(polygon_def.vertices) == 4

    # Create a new polygon shape (a triangle)
    from box2d.shapedef import PolygonDef

    new_polygon_def = PolygonDef(vertices=[(0, 0), (2, 0), (1, 2)])
    polygon.geometry = new_polygon_def

    # Get the updated geometry and verify changes
    updated_def = polygon.geometry
    assert len(updated_def.vertices) == 3
    # Check the first vertex
    assert updated_def.vertices[0].x == pytest.approx(0.0)
    assert updated_def.vertices[0].y == pytest.approx(0.0)
    # Check the second vertex
    assert updated_def.vertices[1].x == pytest.approx(2.0)
    assert updated_def.vertices[1].y == pytest.approx(0.0)
    # Check the third vertex
    assert updated_def.vertices[2].x == pytest.approx(1.0)
    assert updated_def.vertices[2].y == pytest.approx(2.0)


def test_box_get_set_geometry(dynamic_body):
    """Test the geometry property for Box shapes (which are Polygons)."""
    # Create a box with known dimensions
    box = dynamic_body.add_box(width=2.0, height=1.0)

    # Get the geometry as a polygon
    polygon_def = box.geometry
    assert len(polygon_def.vertices) == 4  # Box has 4 corners

    # Calculate expected width and height from vertices
    # We need to find the width and height by examining min/max coordinates
    x_coords = [v.x for v in polygon_def.vertices]
    y_coords = [v.y for v in polygon_def.vertices]
    width = max(x_coords) - min(x_coords)
    height = max(y_coords) - min(y_coords)
    assert width == pytest.approx(2.0)
    assert height == pytest.approx(1.0)

    # Create a new polygon shape with different dimensions
    from box2d.shapedef import PolygonDef

    new_box_vertices = [(-1.5, -0.5), (1.5, -0.5), (1.5, 0.5), (-1.5, 0.5)]
    new_polygon_def = PolygonDef(vertices=new_box_vertices)
    box.geometry = new_polygon_def

    # Verify the changes
    updated_def = box.geometry
    assert len(updated_def.vertices) == 4
    x_coords = [v.x for v in updated_def.vertices]
    y_coords = [v.y for v in updated_def.vertices]
    width = max(x_coords) - min(x_coords)
    height = max(y_coords) - min(y_coords)
    assert width == pytest.approx(3.0)
    assert height == pytest.approx(1.0)
