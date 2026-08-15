# tests/test_joint_tuning.py
"""The joint and chain settings that had no binding.

Joint frames were readable but not writable, so a joint could not be
retargeted without rebuilding it. Constraint tuning, the prismatic spring's
target, and the distance spring's force range had no binding at all, and
neither did a chain's materials -- which meant a chain's friction was fixed
for its lifetime.
"""

import math

import pytest

from box2d import (
    DistanceJointDef,
    PrismaticJointDef,
    RevoluteJointDef,
    Rot,
    Transform,
    Vec2,
    World,
)
from box2d.material import SurfaceMaterial


@pytest.fixture
def world():
    world = World()
    yield world
    world.destroy()


@pytest.fixture
def hinge(world):
    """An arm hanging off a hinge at the origin."""
    ground = world.add_body(position=(0, 0))
    arm = world.add_body(body_type="dynamic", position=(2, 0))
    arm.add_box(4, 0.4)
    joint = world.add_joint(RevoluteJointDef(ground, arm, anchor=(0, 0)))
    return ground, arm, joint


# --- local frames -----------------------------------------------------------


def test_local_frames_are_readable(hinge):
    _, _, joint = hinge
    assert isinstance(joint.local_frame_a, Transform)
    assert isinstance(joint.local_frame_b, Transform)


def test_local_anchor_can_be_moved(hinge):
    """The point of making these settable: retarget without rebuilding."""
    _, _, joint = hinge
    joint.local_anchor_a = (3, 1)

    assert joint.local_anchor_a == Vec2(3, 1)


def test_moving_the_anchor_keeps_the_frame_rotation(hinge):
    _, _, joint = hinge
    joint.local_frame_a = Transform(Vec2(0, 0), Rot(math.pi / 3))
    before = joint.local_frame_a.q.angle

    joint.local_anchor_a = (1, 1)

    assert joint.local_frame_a.q.angle == pytest.approx(before)
    assert joint.local_anchor_a == Vec2(1, 1)


def test_setting_the_frame_moves_the_body(world, hinge):
    """A retargeted joint actually pulls the body somewhere else."""
    _, arm, joint = hinge
    for _ in range(120):
        world.step(1 / 60, 4)
    settled = arm.position.x

    joint.local_anchor_a = (6, 0)
    arm.awake = True
    for _ in range(120):
        world.step(1 / 60, 4)

    assert (
        arm.position.x > settled + 3
    ), "the arm should have swung out to the new anchor"


def test_local_frame_b_is_settable(hinge):
    _, _, joint = hinge
    joint.local_frame_b = Transform(Vec2(-1, 0), Rot(0.0))
    assert joint.local_anchor_b == Vec2(-1, 0)


# --- constraint tuning ------------------------------------------------------


def test_constraint_tuning_round_trips(hinge):
    _, _, joint = hinge
    joint.constraint_tuning = (30.0, 0.5)

    hertz, damping_ratio = joint.constraint_tuning
    assert hertz == pytest.approx(30.0)
    assert damping_ratio == pytest.approx(0.5)


def test_the_default_tuning_is_stiff_but_not_zero(hinge):
    """Easy to assume the default is 0Hz meaning rigid. It is 60Hz, which
    behaves rigidly but is a different setting."""
    hertz, damping_ratio = hinge[2].constraint_tuning
    assert hertz == pytest.approx(60.0)
    assert damping_ratio == pytest.approx(2.0)


def test_soft_tuning_lets_a_joint_be_pulled_apart(world):
    """A rigid joint holds its anchor; a soft one is dragged off it."""

    def separation(hertz):
        world = World()
        ground = world.add_body(position=(0, 0))
        weight = world.add_body(body_type="dynamic", position=(0, -2))
        weight.add_box(1, 1, density=500.0)
        joint = world.add_joint(RevoluteJointDef(ground, weight, anchor=(0, 0)))
        if hertz:
            joint.constraint_tuning = (hertz, 0.1)
        for _ in range(120):
            world.step(1 / 60, 4)
        drift = joint.linear_separation
        world.destroy()
        return drift

    assert separation(2.0) > separation(0.0), "a soft joint should give under load"


# --- prismatic target translation -------------------------------------------


def test_prismatic_target_translation_round_trips(world):
    ground = world.add_body(position=(0, 0))
    slider = world.add_body(body_type="dynamic", position=(0, 0))
    slider.add_box(1, 1)
    joint = world.add_joint(
        PrismaticJointDef(ground, slider, anchor=(0, 0), axis=(1, 0))
    )

    joint.target_translation = 3.0
    assert joint.target_translation == pytest.approx(3.0)


def test_prismatic_spring_drives_towards_its_target(world):
    """With the spring on, the joint is a linear servo."""
    world.gravity = (0, 0)
    ground = world.add_body(position=(0, 0))
    slider = world.add_body(body_type="dynamic", position=(0, 0))
    slider.add_box(1, 1)
    joint = world.add_joint(
        PrismaticJointDef(ground, slider, anchor=(0, 0), axis=(1, 0))
    )
    joint.spring_enabled = True
    joint.spring_hertz = 2.0
    joint.spring_damping_ratio = 0.9
    joint.target_translation = 5.0

    for _ in range(300):
        world.step(1 / 60, 4)

    assert slider.position.x == pytest.approx(5.0, abs=0.3)


# --- distance spring force range --------------------------------------------


def test_spring_force_range_round_trips(world):
    ground = world.add_body(position=(0, 0))
    hanging = world.add_body(body_type="dynamic", position=(0, -3))
    hanging.add_circle(radius=0.5)
    joint = world.add_joint(DistanceJointDef(ground, hanging, length=3.0))

    joint.spring_force_range = (-50.0, 100.0)
    lower, upper = joint.spring_force_range
    assert lower == pytest.approx(-50.0)
    assert upper == pytest.approx(100.0)


def test_default_spring_force_range_is_effectively_unbounded(world):
    ground = world.add_body(position=(0, 0))
    hanging = world.add_body(body_type="dynamic", position=(0, -3))
    hanging.add_circle(radius=0.5)
    joint = world.add_joint(DistanceJointDef(ground, hanging, length=3.0))

    lower, upper = joint.spring_force_range
    # Box2D uses FLT_MAX rather than an actual infinity here.
    assert lower < -1e37
    assert upper > 1e37


def test_a_spring_that_can_only_pull_behaves_like_a_rope(world):
    """Clamping the range at zero is what turns a spring into a rope."""

    def rest_length(force_range):
        world = World()
        ground = world.add_body(position=(0, 0))
        weight = world.add_body(body_type="dynamic", position=(0, -3))
        weight.add_box(1, 1, density=100.0)
        joint = world.add_joint(DistanceJointDef(ground, weight, length=3.0))
        joint.spring_enabled = True
        joint.spring_hertz = 1.0
        joint.spring_damping_ratio = 0.1
        if force_range is not None:
            joint.spring_force_range = force_range
        for _ in range(240):
            world.step(1 / 60, 4)
        length = -weight.position.y
        world.destroy()
        return length

    # A spring allowed no upward force cannot hold the weight up at all.
    assert rest_length((0.0, 0.0)) > rest_length(None)


# --- chain surface materials ------------------------------------------------


@pytest.fixture
def chain_body(world):
    body = world.add_body(position=(0, 0))
    return body


def test_a_chain_has_one_shared_material_by_default(chain_body):
    chain = chain_body.add_chain([(-15, 0), (-5, -1), (5, -1), (15, 0)])
    assert chain.has_per_segment_materials is False


def test_a_chain_can_have_one_material_per_segment(chain_body):
    """Box2D takes one material or one per point, nothing between."""
    materials = [SurfaceMaterial(friction=f) for f in (0.1, 0.5, 0.9, 0.2)]
    chain = chain_body.add_chain(
        [(-10, 0), (-3, -6), (3, -6), (10, 0)], loop=True, materials=materials
    )
    assert chain.has_per_segment_materials is True
    assert len(chain.segments) == 4


def test_a_loop_rejects_the_wrong_number_of_materials(chain_body):
    """This validation demanded points + 1 for a loop, which Box2D rejects."""
    points = [(-10, 0), (-3, -6), (3, -6), (10, 0)]
    with pytest.raises(ValueError, match="one per point"):
        chain_body.add_chain(
            points, loop=True, materials=[SurfaceMaterial() for _ in range(5)]
        )


def test_material_round_trips_through_the_chain(chain_body):
    chain = chain_body.add_chain([(-15, 0), (-5, -1), (5, -1), (15, 0)])
    chain.set_surface_material(SurfaceMaterial(friction=0.9, restitution=0.25))

    material = chain.get_surface_material()
    assert material.friction == pytest.approx(0.9)
    assert material.restitution == pytest.approx(0.25)


def test_setting_a_shared_material_reaches_every_segment(chain_body):
    """The point of the binding: change a chain's surface without rebuilding."""
    chain = chain_body.add_chain([(-15, 0), (-5, -1), (5, -1), (15, 0)], loop=True)
    chain.set_surface_material(SurfaceMaterial(friction=0.05))

    assert all(segment.friction == pytest.approx(0.05) for segment in chain.segments)


def test_one_segment_can_be_made_slippery(chain_body):
    """Per-segment materials: an icy patch on otherwise grippy ground."""
    # An open chain uses its end points as ghosts, so six points make three
    # real segments while Box2D still wants six materials.
    materials = [SurfaceMaterial(friction=0.9) for _ in range(6)]
    chain = chain_body.add_chain(
        [(-25, 0), (-15, 0), (-5, 0), (5, 0), (15, 0), (25, 0)], materials=materials
    )
    assert len(chain.segments) == 3

    chain.set_surface_material(SurfaceMaterial(friction=0.0), 1)

    frictions = [segment.friction for segment in chain.segments]
    assert frictions == [pytest.approx(0.9), pytest.approx(0.0), pytest.approx(0.9)]


def test_reading_a_material_matches_the_segment_not_the_chain_array(chain_body):
    """Box2D's own getter is off by one on an open chain, so this reads the
    segment instead. Comparing the two is the whole reason it does."""
    from box2d._box2d import lib

    materials = [SurfaceMaterial(friction=round(0.1 * (i + 1), 1)) for i in range(6)]
    chain = chain_body.add_chain(
        [(-25, 0), (-15, 0), (-5, 0), (5, 0), (15, 0), (25, 0)], materials=materials
    )

    for index, segment in enumerate(chain.segments):
        assert chain.get_surface_material(index).friction == pytest.approx(
            segment.friction
        )
        raw = lib.b2Chain_GetSurfaceMaterial(chain._chain_id, index)
        assert raw.friction != pytest.approx(segment.friction), "off by one"


def test_a_bad_segment_index_raises_rather_than_segfaulting(chain_body):
    """Box2D bounds the setter by its material count but indexes the shorter
    segment array, so an unguarded index past the segments crashes."""
    materials = [SurfaceMaterial(friction=0.9) for _ in range(6)]
    chain = chain_body.add_chain(
        [(-25, 0), (-15, 0), (-5, 0), (5, 0), (15, 0), (25, 0)], materials=materials
    )
    assert chain.surface_material_count == 6, "more materials than segments"

    for bad_index in (3, 5, -1):
        with pytest.raises(IndexError, match="out of range"):
            chain.set_surface_material(SurfaceMaterial(), bad_index)
        with pytest.raises(IndexError, match="out of range"):
            chain.get_surface_material(bad_index)


def test_material_read_back_is_a_copy(chain_body):
    chain = chain_body.add_chain([(-15, 0), (-5, -1), (5, -1), (15, 0)])
    chain.set_surface_material(SurfaceMaterial(friction=0.7))

    material = chain.get_surface_material()
    material.friction = 0.1

    assert chain.get_surface_material().friction == pytest.approx(0.7)


# --- parent chain -----------------------------------------------------------


def test_a_chain_segment_knows_its_chain(chain_body):
    chain = chain_body.add_chain([(-15, 0), (-5, -1), (5, -1), (15, 0)])
    assert all(segment.parent_chain is chain for segment in chain.segments)


def test_an_ordinary_shape_has_no_parent_chain(chain_body):
    assert chain_body.add_box(1, 1).parent_chain is None


def test_a_plain_segment_shape_has_no_parent_chain(chain_body):
    """Same shape type as a chain segment, but owned by no chain."""
    segment = chain_body.add_segment((-1, 0), (1, 0))
    assert segment.parent_chain is None


def test_body_exposes_its_chains(chain_body):
    chain = chain_body.add_chain([(-15, 0), (-5, -1), (5, -1), (15, 0)])
    assert chain_body.chains == [chain]
