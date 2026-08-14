# tests/test_shape_geometry.py
"""Shapes expose their own geometry as properties.

Reading a circle's radius used to mean calling get_circle() and unpacking the
CircleDef it returned -- the C API surfacing through the binding that exists to
hide it. Each shape now has a 'geometry' property holding its definition, plus
properties for the individual components.
"""

import pytest

from box2d import World, Vec2, DestroyedError
from box2d.shapedef import CircleDef, CapsuleDef, SegmentDef, PolygonDef


@pytest.fixture
def world():
    world = World()
    yield world
    world.destroy()


@pytest.fixture
def body(world):
    return world.add_body(body_type="dynamic")


# --- circle -----------------------------------------------------------------


def test_circle_components(body):
    circle = body.add_circle(radius=0.5, center=(1, 0))
    assert circle.radius == pytest.approx(0.5)
    assert circle.center == (1, 0)


def test_circle_component_setters(body):
    circle = body.add_circle(radius=0.5)
    circle.radius = 2.0
    circle.center = (3, 4)
    assert circle.radius == pytest.approx(2.0)
    assert circle.center == (3, 4)


def test_circle_setting_radius_keeps_center(body):
    circle = body.add_circle(radius=0.5, center=(1, 2))
    circle.radius = 3.0
    assert circle.center == (1, 2)


def test_circle_geometry_round_trips(body):
    circle = body.add_circle(radius=0.5)
    circle.geometry = CircleDef(radius=1.25, center=(2, 2))
    assert isinstance(circle.geometry, CircleDef)
    assert circle.radius == pytest.approx(1.25)
    assert circle.center == (2, 2)


# --- capsule ----------------------------------------------------------------


def test_capsule_components(body):
    capsule = body.add_capsule(point1=(-1, 0), point2=(1, 0), radius=0.3)
    assert capsule.point1 == (-1, 0)
    assert capsule.point2 == (1, 0)
    assert capsule.radius == pytest.approx(0.3)


def test_capsule_component_setters_are_independent(body):
    capsule = body.add_capsule(point1=(-1, 0), point2=(1, 0), radius=0.3)
    capsule.radius = 0.6
    assert capsule.point1 == (-1, 0) and capsule.point2 == (1, 0)

    capsule.point1 = (-2, 0)
    assert capsule.point2 == (1, 0)
    assert capsule.radius == pytest.approx(0.6)


def test_capsule_geometry_round_trips(body):
    capsule = body.add_capsule(point1=(-1, 0), point2=(1, 0), radius=0.3)
    capsule.geometry = CapsuleDef((0, -2), (0, 2), 0.75)
    assert isinstance(capsule.geometry, CapsuleDef)
    assert capsule.point1 == (0, -2)
    assert capsule.point2 == (0, 2)
    assert capsule.radius == pytest.approx(0.75)


# --- segment ----------------------------------------------------------------


def test_segment_components(body):
    segment = body.add_segment(point1=(-2, 0), point2=(2, 0))
    assert segment.point1 == (-2, 0)
    assert segment.point2 == (2, 0)


def test_segment_component_setters(body):
    segment = body.add_segment(point1=(-2, 0), point2=(2, 0))
    segment.point2 = (5, 1)
    assert segment.point1 == (-2, 0)
    assert segment.point2 == (5, 1)


def test_segment_geometry_round_trips(body):
    segment = body.add_segment(point1=(-2, 0), point2=(2, 0))
    segment.geometry = SegmentDef((0, 0), (1, 1))
    assert isinstance(segment.geometry, SegmentDef)
    assert segment.point1 == (0, 0)
    assert segment.point2 == (1, 1)


# --- polygon and box --------------------------------------------------------


def test_polygon_components(body):
    polygon = body.add_polygon(vertices=[(-1, -1), (1, -1), (1, 1), (-1, 1)])
    assert len(polygon.vertices) == 4
    assert all(isinstance(v, Vec2) for v in polygon.vertices)
    assert polygon.radius == pytest.approx(0.0)


def test_polygon_vertices_setter(body):
    polygon = body.add_polygon(vertices=[(-1, -1), (1, -1), (1, 1), (-1, 1)])
    polygon.vertices = [(-2, -2), (2, -2), (2, 2), (-2, 2)]
    assert len(polygon.vertices) == 4
    assert max(abs(v.x) for v in polygon.vertices) == pytest.approx(2.0)


def test_polygon_geometry_round_trips(body):
    polygon = body.add_polygon(vertices=[(-1, -1), (1, -1), (1, 1), (-1, 1)])
    polygon.geometry = PolygonDef([(0, 0), (2, 0), (2, 2)])
    assert isinstance(polygon.geometry, PolygonDef)
    assert len(polygon.vertices) == 3


def test_box_inherits_polygon_geometry(body):
    box = body.add_box(2, 1)
    assert len(box.vertices) == 4
    assert isinstance(box.geometry, PolygonDef)


# --- the get_X/X twins are gone ---------------------------------------------


@pytest.mark.parametrize(
    "removed",
    [
        "get_circle",
        "set_circle",
        "get_contact_data",
        "get_sensor_overlaps",
        "get_contact_capacity",
        "get_sensor_capacity",
    ],
)
def test_shape_getter_twins_removed(body, removed):
    circle = body.add_circle(radius=1.0)
    assert not hasattr(circle, removed)


@pytest.mark.parametrize(
    "removed",
    ["get_joints", "get_contact_data", "get_contact_capacity", "get_joint_count"],
)
def test_body_getter_twins_removed(body, removed):
    assert not hasattr(body, removed)


def test_capacities_are_properties(body):
    shape = body.add_circle(radius=1.0)
    assert isinstance(shape.contact_capacity, int)
    assert isinstance(shape.sensor_capacity, int)
    assert isinstance(body.contact_capacity, int)
    assert isinstance(body.joint_count, int)


def test_collections_are_properties(body):
    shape = body.add_circle(radius=1.0)
    assert shape.contact_data == []
    assert shape.sensor_overlaps == []
    assert body.contact_data == []
    assert body.joints == []


# --- gaps found while porting testbed scenarios -----------------------------


def test_thin_box_is_allowed(body):
    """Boxes are built directly, not via a convex hull with a minimum size.

    Routing boxes through PolygonDef rejected anything thinner than Box2D's
    linear slop, which made a house of cards impossible to build.
    """
    shape = body.add_box(0.002, 0.4)
    assert shape in body.shapes
    assert len(shape.vertices) == 4


def test_box_offset_and_angle_survive_the_direct_path(body):
    import math

    shape = body.add_box(2.0, 1.0, offset=(3, 4), angle=math.pi / 2)
    xs = [v.x for v in shape.vertices]
    ys = [v.y for v in shape.vertices]
    # Rotated a quarter turn, so the 2x1 box is 1 wide and 2 tall about (3, 4).
    assert max(xs) - min(xs) == pytest.approx(1.0, abs=1e-5)
    assert max(ys) - min(ys) == pytest.approx(2.0, abs=1e-5)
    assert sum(xs) / 4 == pytest.approx(3.0, abs=1e-5)
    assert sum(ys) / 4 == pytest.approx(4.0, abs=1e-5)


def test_shape_destroy(body):
    shape = body.add_circle(radius=1.0)
    other = body.add_circle(radius=0.5, center=(2, 0))

    shape.destroy()

    assert shape.is_valid() is False
    assert shape not in body.shapes
    assert other.is_valid() is True
    with pytest.raises(DestroyedError):
        shape.density


def test_shape_destroy_is_idempotent(body):
    shape = body.add_circle(radius=1.0)
    shape.destroy()
    shape.destroy()


def test_surface_properties_are_settable_live(body):
    """tangent_speed and rolling_resistance were creation-only before."""
    shape = body.add_box(2.0, 0.5, friction=0.8)

    shape.tangent_speed = 3.5
    shape.rolling_resistance = 0.25

    assert shape.tangent_speed == pytest.approx(3.5)
    assert shape.rolling_resistance == pytest.approx(0.25)
    assert shape.friction == pytest.approx(0.8)  # untouched


def test_surface_material_round_trips(body):
    from box2d.material import SurfaceMaterial

    shape = body.add_circle(radius=1.0)
    shape.surface_material = SurfaceMaterial(
        friction=0.3, restitution=0.4, rolling_resistance=0.5, tangent_speed=6.0
    )

    material = shape.surface_material
    assert material.friction == pytest.approx(0.3)
    assert material.restitution == pytest.approx(0.4)
    assert material.rolling_resistance == pytest.approx(0.5)
    assert material.tangent_speed == pytest.approx(6.0)
