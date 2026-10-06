# tests/test_shape_defs.py
"""Shape definitions are part of the public API, importable from ``box2d``.

They used to be reachable only through ``box2d.shapedef`` and
``box2d.material``, so the samples -- which are meant to use nothing but the
public API -- reached into submodules for them.
"""

import doctest
import importlib
import math

import pytest

import box2d
import box2d.shapedef

SUBMODULE_NAMES = [
    ("box2d.shapedef", "ShapeDef"),
    ("box2d.shapedef", "CircleDef"),
    ("box2d.shapedef", "CapsuleDef"),
    ("box2d.shapedef", "SegmentDef"),
    ("box2d.shapedef", "PolygonDef"),
    ("box2d.shapedef", "ChainDef"),
    ("box2d.material", "SurfaceMaterial"),
]


@pytest.mark.parametrize("module, name", SUBMODULE_NAMES)
def test_exported_from_the_package(module, name):
    """The top-level name is the submodule's class, so old imports keep working
    and isinstance checks agree whichever path a caller imported from."""
    assert getattr(box2d, name) is getattr(importlib.import_module(module), name)
    assert name in box2d.__all__


# --- whether a polygon can be built -----------------------------------------
#
# Box2D builds a polygon from the convex hull of the points it is given, and
# refuses when there is no hull to build. Its rules, from b2ComputeHull: 3 to 8
# points; points closer than half the linear slop (0.005 m) are welded into
# one; and a point within twice the linear slop of the line through its
# neighbours is dropped as collinear.


def test_a_triangle_is_valid():
    assert box2d.PolygonDef([(0, 0), (1, 0), (0, 1)]).is_valid


def _circle_points(count, radius=1.0):
    return [
        (
            radius * math.cos(2 * math.pi * i / count),
            radius * math.sin(2 * math.pi * i / count),
        )
        for i in range(count)
    ]


BUILDABLE = {
    "triangle": [(0, 0), (1, 0), (0, 1)],
    "box": [(-1, -1), (1, -1), (1, 1), (-1, 1)],
    "clockwise box": [(-1, 1), (1, 1), (1, -1), (-1, -1)],
    # A concave outline is not refused: Box2D takes its hull, the triangle.
    "concave outline": [(0, 0), (2, 0), (0.6, 0.6), (0, 2)],
    # The repeated corner is welded away, leaving a triangle.
    "triangle with a repeated corner": [(0, 0), (1, 0), (0, 1), (0, 0)],
    "eight points, the most allowed": _circle_points(8),
    # The apex is 0.02 off the base, twice the collinear tolerance.
    "flat triangle above the slop": [(0, 0), (1, 0), (0.5, 0.02)],
}

NOT_BUILDABLE = {
    "no points": [],
    "two points": [(0, 0), (1, 0)],
    "nine points": _circle_points(9),
    "collinear": [(0, 0), (1, 0), (2, 0)],
    "collinear, out of order": [(2, 2), (0, 0), (1, 1), (3, 3)],
    "one point repeated": [(1, 1), (1, 1), (1, 1)],
    # Two distinct points once the duplicates are welded.
    "a segment with repeats": [(0, 0), (1, 0), (1, 0), (0, 0)],
    # The apex is 0.005 off the base, inside the 0.01 collinear tolerance.
    "flat triangle within the slop": [(0, 0), (1, 0), (0.5, 0.005)],
    # 2 mm sides: every point is within welding distance of a neighbour or
    # the line through them.
    "a triangle smaller than the slop": [(0, 0), (0.002, 0), (0, 0.002)],
    "a vertex that is not a number": [(0, 0), (1, 0), (math.nan, 1)],
    "an infinite vertex": [(0, 0), (1, 0), (0, math.inf)],
}


@pytest.mark.parametrize("vertices", BUILDABLE.values(), ids=BUILDABLE.keys())
def test_buildable_vertices_are_valid(vertices):
    assert box2d.PolygonDef(vertices).is_valid


@pytest.mark.parametrize("vertices", NOT_BUILDABLE.values(), ids=NOT_BUILDABLE.keys())
def test_unbuildable_vertices_are_not_valid(vertices):
    assert not box2d.PolygonDef(vertices).is_valid


@pytest.fixture
def body():
    world = box2d.World()
    yield world.new_body().dynamic().build()
    world.destroy()


def _adds(body, vertices, radius=0.0):
    try:
        body.add_polygon(vertices, radius)
    except ValueError:
        return False
    return True


@pytest.mark.parametrize(
    "vertices",
    [*BUILDABLE.values(), *NOT_BUILDABLE.values()],
    ids=[*BUILDABLE.keys(), *NOT_BUILDABLE.keys()],
)
def test_is_valid_says_whether_adding_the_polygon_succeeds(body, vertices):
    """The point of asking: is_valid is True exactly when building would work."""
    assert box2d.PolygonDef(vertices).is_valid == _adds(body, vertices)


# Box2D refuses a polygon shape whose rounding radius is negative or not a
# number, even when its hull is fine.
RADII = {
    "no radius": (None, True),
    "zero": (0.0, True),
    "rounded": (0.25, True),
    "negative": (-0.1, False),
    "nan": (math.nan, False),
    "infinite": (math.inf, False),
}


@pytest.mark.parametrize("radius, valid", RADII.values(), ids=RADII.keys())
def test_the_radius_must_be_a_size(body, radius, valid):
    triangle = BUILDABLE["triangle"]
    assert box2d.PolygonDef(triangle, radius).is_valid == valid
    assert _adds(body, triangle, radius or 0.0) == valid


def test_doctests():
    results = doctest.testmod(box2d.shapedef)
    assert results.failed == 0
