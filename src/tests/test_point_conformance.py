# tests/test_point_conformance.py
"""Every point-taking parameter in the API accepts every point form.

box2d-py has one rule for points: pass any *vector-like* -- tuple, list, Vec2,
or a raw b2Vec2 -- and it is normalised through the Vec2 constructor.

The rule kept drifting because nothing enforced it. joint.py built its anchors
with ``Vec2(*anchor)`` instead, which silently rejected b2Vec2 and reported a
wrong-length anchor as "Vec2.__init__() takes from 2 to 3 positional arguments".
The per-module tests never caught it because none of them passed a joint an
anchor in more than one form.

This module tests the rule itself rather than any one call site: every entry
point below is exercised with all four forms. The coverage guard at the bottom
fails when a new point-shaped parameter appears without being added here, so
the next joint.py cannot go untested.
"""

import inspect

import pytest

from box2d import World, Vec2
from box2d.body import Body, BodyBuilder
from box2d.shape import Shape


def point_forms():
    """The four ways a point may be spelled. Built per-call: b2Vec2 is cdata."""
    return [
        pytest.param((3.0, 4.0), id="tuple"),
        pytest.param([3.0, 4.0], id="list"),
        pytest.param(Vec2(3.0, 4.0), id="Vec2"),
        pytest.param(Vec2(3.0, 4.0).b2Vec2[0], id="b2Vec2"),
    ]


@pytest.fixture
def world():
    world = World()
    yield world
    world.destroy()


@pytest.fixture
def bodies(world):
    """Two overlapping dynamic bodies, enough to anchor any joint."""
    a = world.new_body().dynamic().position(0, 0).build()
    a.add_circle(radius=1.0)
    b = world.new_body().dynamic().position(1, 0).build()
    b.add_circle(radius=1.0)
    return a, b


# --- the entry points, one invoker each -------------------------------------
#
# Each invoker receives (world, bodies, point) and must pass 'point' into the
# named parameter. Keep this table in sync with the coverage guard below.

ENTRY_POINTS = {
    # BodyBuilder
    "BodyBuilder.position": lambda w, bs, p: w.new_body().position(p).build(),
    "BodyBuilder.linear_velocity": lambda w, bs, p: w.new_body()
    .linear_velocity(p)
    .build(),
    "BodyBuilder.circle.center": lambda w, bs, p: w.new_body()
    .circle(radius=1.0, center=p)
    .build(),
    "BodyBuilder.box.offset": lambda w, bs, p: w.new_body().box(1, 1, offset=p).build(),
    "BodyBuilder.capsule.point1": lambda w, bs, p: w.new_body()
    .capsule(p, (1.0, 1.0), 0.5)
    .build(),
    "BodyBuilder.capsule.point2": lambda w, bs, p: w.new_body()
    .capsule((1.0, 1.0), p, 0.5)
    .build(),
    "BodyBuilder.segment.point1": lambda w, bs, p: w.new_body()
    .segment(p, (1.0, 1.0))
    .build(),
    "BodyBuilder.segment.point2": lambda w, bs, p: w.new_body()
    .segment((1.0, 1.0), p)
    .build(),
    # Body
    "Body.position": lambda w, bs, p: setattr(bs[0], "position", p),
    "Body.linear_velocity": lambda w, bs, p: setattr(bs[0], "linear_velocity", p),
    "Body.apply_force.force": lambda w, bs, p: bs[0].apply_force(p),
    "Body.apply_force.point": lambda w, bs, p: bs[0].apply_force((1.0, 1.0), p),
    "Body.apply_linear_impulse.impulse": lambda w, bs, p: bs[0].apply_linear_impulse(p),
    "Body.apply_linear_impulse.point": lambda w, bs, p: bs[0].apply_linear_impulse(
        (1.0, 1.0), p
    ),
    "Body.get_local_point": lambda w, bs, p: bs[0].get_local_point(p),
    "Body.get_world_point": lambda w, bs, p: bs[0].get_world_point(p),
    "Body.get_local_vector": lambda w, bs, p: bs[0].get_local_vector(p),
    "Body.get_world_vector": lambda w, bs, p: bs[0].get_world_vector(p),
    "Body.get_local_point_velocity.local_point": lambda w, bs, p: bs[
        0
    ].get_local_point_velocity(p),
    "Body.get_world_point_velocity.world_point": lambda w, bs, p: bs[
        0
    ].get_world_point_velocity(p),
    # Shape
    "Shape.test_point.point": lambda w, bs, p: bs[0].shapes[0].test_point(p),
    "Shape.get_closest_point.target": lambda w, bs, p: bs[0]
    .shapes[0]
    .get_closest_point(p),
    "Shape.ray_cast.origin": lambda w, bs, p: bs[0].shapes[0].ray_cast(p, (5.0, 5.0)),
    "Shape.ray_cast.translation": lambda w, bs, p: bs[0]
    .shapes[0]
    .ray_cast((-5.0, 0.0), p),
    "Body.add_circle.center": lambda w, bs, p: bs[0].add_circle(radius=1.0, center=p),
    "Body.add_box.offset": lambda w, bs, p: bs[0].add_box(1, 1, offset=p),
    "Body.add_capsule.point1": lambda w, bs, p: bs[0].add_capsule(p, (1.0, 1.0), 0.5),
    "Body.add_capsule.point2": lambda w, bs, p: bs[0].add_capsule((1.0, 1.0), p, 0.5),
    "Body.add_segment.point1": lambda w, bs, p: bs[0].add_segment(p, (1.0, 1.0)),
    "Body.add_segment.point2": lambda w, bs, p: bs[0].add_segment((1.0, 1.0), p),
    # World
    "World.gravity": lambda w, bs, p: setattr(w, "gravity", p),
    "World.query_circle.position": lambda w, bs, p: w.query_circle(p, 1.0),
    "World.ray_cast.origin": lambda w, bs, p: w.ray_cast(p, (5.0, 5.0)),
    "World.ray_cast.target": lambda w, bs, p: w.ray_cast((0.0, 0.0), p),
    # Joints -- the module that drifted
    "World.add_revolute_joint.local_anchor_a": lambda w, bs, p: w.add_revolute_joint(
        *bs, local_anchor_a=p, local_anchor_b=(0.0, 0.0)
    ),
    "World.add_revolute_joint.local_anchor_b": lambda w, bs, p: w.add_revolute_joint(
        *bs, local_anchor_a=(0.0, 0.0), local_anchor_b=p
    ),
    "World.add_weld_joint.local_anchor_a": lambda w, bs, p: w.add_weld_joint(
        *bs, local_anchor_a=p, local_anchor_b=(0.0, 0.0)
    ),
    "World.add_weld_joint.local_anchor_b": lambda w, bs, p: w.add_weld_joint(
        *bs, local_anchor_a=(0.0, 0.0), local_anchor_b=p
    ),
    "World.add_distance_joint.local_anchor_a": lambda w, bs, p: w.add_distance_joint(
        *bs, local_anchor_a=p, local_anchor_b=(0.0, 0.0)
    ),
    "World.add_distance_joint.local_anchor_b": lambda w, bs, p: w.add_distance_joint(
        *bs, local_anchor_a=(0.0, 0.0), local_anchor_b=p
    ),
    "World.add_prismatic_joint.local_anchor_a": lambda w, bs, p: w.add_prismatic_joint(
        *bs, local_anchor_a=p, local_anchor_b=(0.0, 0.0), axis=(1.0, 0.0)
    ),
    "World.add_prismatic_joint.local_anchor_b": lambda w, bs, p: w.add_prismatic_joint(
        *bs, local_anchor_a=(0.0, 0.0), local_anchor_b=p, axis=(1.0, 0.0)
    ),
    "World.add_prismatic_joint.axis": lambda w, bs, p: w.add_prismatic_joint(
        *bs, local_anchor_a=(0.0, 0.0), local_anchor_b=(0.0, 0.0), axis=p
    ),
    "World.add_wheel_joint.local_anchor_a": lambda w, bs, p: w.add_wheel_joint(
        *bs, local_anchor_a=p, local_anchor_b=(0.0, 0.0), axis=(1.0, 0.0)
    ),
    "World.add_wheel_joint.local_anchor_b": lambda w, bs, p: w.add_wheel_joint(
        *bs, local_anchor_a=(0.0, 0.0), local_anchor_b=p, axis=(1.0, 0.0)
    ),
    "World.add_wheel_joint.axis": lambda w, bs, p: w.add_wheel_joint(
        *bs, local_anchor_a=(0.0, 0.0), local_anchor_b=(0.0, 0.0), axis=p
    ),
    "World.add_motor_joint.linear_velocity": lambda w, bs, p: w.add_motor_joint(
        *bs, linear_velocity=p
    ),
    "World.add_mouse_joint.target": lambda w, bs, p: w.add_mouse_joint(bs[0], p),
    # World anchors: resolved through Transform.inverse rather than passed straight
    # to the joint, so they exercise a different conversion path.
    "World.add_revolute_joint.anchor": lambda w, bs, p: w.add_revolute_joint(
        *bs, anchor=p
    ),
    "World.add_weld_joint.anchor": lambda w, bs, p: w.add_weld_joint(*bs, anchor=p),
    "World.add_prismatic_joint.anchor": lambda w, bs, p: w.add_prismatic_joint(
        *bs, anchor=p, axis=(1.0, 0.0)
    ),
    "World.add_wheel_joint.anchor": lambda w, bs, p: w.add_wheel_joint(
        *bs, anchor=p, axis=(1.0, 0.0)
    ),
}


@pytest.mark.parametrize("entry", sorted(ENTRY_POINTS), ids=lambda e: e)
@pytest.mark.parametrize("point", point_forms())
def test_entry_point_accepts_every_form(world, bodies, entry, point):
    """Passing a point in any supported form must be accepted."""
    ENTRY_POINTS[entry](world, bodies, point)


@pytest.mark.parametrize("entry", sorted(ENTRY_POINTS), ids=lambda e: e)
def test_entry_point_rejects_wrong_length(world, bodies, entry):
    """A wrong-length point must fail with the shared message, not an internal one."""
    with pytest.raises(ValueError, match="exactly 2 elements"):
        ENTRY_POINTS[entry](world, bodies, (1.0, 2.0, 3.0))


# --- coverage guard ---------------------------------------------------------

# Parameters whose names look point-shaped but are genuinely scalars.
SCALAR_EXCEPTIONS = {
    "angular_velocity",
    "max_motor_force",
    "max_motor_torque",
    "max_force",
    "max_torque",
    "max_length",
    "min_length",
    "target_angle",
    "reference_angle",
    "correction_factor",
    "tangent_speed",
    "hertz",
}

POINT_NAME_HINTS = ("anchor", "center", "offset", "point", "axis", "target", "origin")


def discovered_point_parameters():
    """Parameters across the public API whose names indicate they take a point."""
    found = set()
    for cls in (BodyBuilder, Body, World, Shape):
        for name in dir(cls):
            if name.startswith("_"):
                continue
            fn = inspect.getattr_static(cls, name)
            if not inspect.isfunction(fn):
                continue
            try:
                sig = inspect.signature(fn)
            except (ValueError, TypeError):
                continue
            for param in sig.parameters:
                if param == "self" or param in SCALAR_EXCEPTIONS:
                    continue
                if any(hint in param for hint in POINT_NAME_HINTS):
                    found.add(f"{cls.__name__}.{name}.{param}")
    return found


def test_every_point_parameter_is_covered():
    """A new point-shaped parameter must be added to ENTRY_POINTS.

    This is what makes the rule enforceable rather than remembered. If it fails,
    either add the parameter to ENTRY_POINTS or, if it is really a scalar, to
    SCALAR_EXCEPTIONS.
    """
    covered = set(ENTRY_POINTS)
    # ENTRY_POINTS keys omit the parameter for single-point entries; accept a
    # match on either the full "Class.method.param" or the "Class.method" prefix.
    uncovered = {
        param
        for param in discovered_point_parameters()
        if param not in covered and param.rsplit(".", 1)[0] not in covered
    }
    assert not uncovered, "point parameters with no conformance test: " + ", ".join(
        sorted(uncovered)
    )
