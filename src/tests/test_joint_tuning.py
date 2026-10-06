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

    assert arm.position.x > settled + 3, (
        "the arm should have swung out to the new anchor"
    )


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
    joint.enable_spring = True
    joint.spring_hertz = 2.0
    joint.spring_damping_ratio = 0.9
    joint.target_translation = 5.0

    for _ in range(300):
        world.step(1 / 60, 4)

    assert slider.position.x == pytest.approx(5.0, abs=0.3)


# --- distance spring force range --------------------------------------------


def test_spring_force_limits_round_trip(world):
    ground = world.add_body(position=(0, 0))
    hanging = world.add_body(body_type="dynamic", position=(0, -3))
    hanging.add_circle(radius=0.5)
    joint = world.add_joint(
        DistanceJointDef(
            ground,
            hanging,
            length=3.0,
            lower_spring_force=-20.0,
            upper_spring_force=40.0,
        )
    )
    assert joint.lower_spring_force == pytest.approx(-20.0)
    assert joint.upper_spring_force == pytest.approx(40.0)

    joint.lower_spring_force = -50.0
    joint.upper_spring_force = 100.0
    assert joint.lower_spring_force == pytest.approx(-50.0)
    assert joint.upper_spring_force == pytest.approx(100.0)


def test_spring_force_limits_are_effectively_unbounded_by_default(world):
    ground = world.add_body(position=(0, 0))
    hanging = world.add_body(body_type="dynamic", position=(0, -3))
    hanging.add_circle(radius=0.5)
    joint = world.add_joint(DistanceJointDef(ground, hanging, length=3.0))

    # Box2D uses FLT_MAX rather than an actual infinity here.
    assert joint.lower_spring_force < -1e37
    assert joint.upper_spring_force > 1e37


def test_spring_force_bounds_that_cross_are_refused(world):
    """Box2D would swap them: upper 0 then lower 10 gave a range of (0, 10)."""
    ground = world.add_body(position=(0, 0))
    hanging = world.add_body(body_type="dynamic", position=(0, -3))
    joint = world.add_joint(DistanceJointDef(ground, hanging, length=3.0))

    joint.upper_spring_force = 0.0
    with pytest.raises(ValueError, match="lower 10.0 is above upper 0.0"):
        joint.lower_spring_force = 10.0
    joint.lower_spring_force = -5.0
    with pytest.raises(ValueError, match="above upper"):
        joint.upper_spring_force = -10.0
    assert (joint.lower_spring_force, joint.upper_spring_force) == (-5.0, 0.0)


def test_a_spring_force_bound_can_be_set_equal_to_the_other(world):
    ground = world.add_body(position=(0, 0))
    hanging = world.add_body(body_type="dynamic", position=(0, -3))
    joint = world.add_joint(DistanceJointDef(ground, hanging, length=3.0))

    joint.lower_spring_force = 0.1
    joint.upper_spring_force = 0.1
    assert joint.upper_spring_force == pytest.approx(0.1)


def test_a_distance_joint_cannot_be_made_with_crossed_spring_forces(world):
    ground = world.add_body(position=(0, 0))
    hanging = world.add_body(body_type="dynamic", position=(0, -3))
    crossed = DistanceJointDef(
        ground, hanging, length=3.0, lower_spring_force=10.0, upper_spring_force=0.0
    )
    with pytest.raises(ValueError, match="above upper"):
        world.add_joint(crossed)


def hanging_length(**limits):
    """How far a weight ends up below a springy distance joint holding it."""
    world = World()
    ground = world.add_body(position=(0, 0))
    weight = world.add_body(body_type="dynamic", position=(0, -3))
    weight.add_box(1, 1, density=100.0)
    world.add_joint(
        DistanceJointDef(
            ground,
            weight,
            length=3.0,
            enable_spring=True,
            spring_hertz=1.0,
            spring_damping_ratio=0.5,
            **limits,
        )
    )
    for _ in range(240):
        world.step(1 / 60, 4)
    length = -weight.position.y
    world.destroy()
    return length


def test_a_spring_that_cannot_push_holds_a_weight_like_a_rope():
    """Holding a weight up is pulling, which upper_spring_force does not limit."""
    unlimited = hanging_length()
    rope = hanging_length(upper_spring_force=0.0)
    assert rope == pytest.approx(unlimited, abs=0.1)


def test_a_spring_that_cannot_pull_lets_a_weight_fall_like_a_strut():
    """lower_spring_force limits pulling; at zero the weight is not held."""
    unlimited = hanging_length()
    strut = hanging_length(lower_spring_force=0.0)
    assert strut > unlimited + 5.0


def propped_height(**limits):
    """How high a weight ends up, resting on a springy distance joint below it."""
    world = World()
    ground = world.add_body(position=(0, 0))
    weight = world.add_body(body_type="dynamic", position=(0, 3))
    weight.add_box(1, 1, density=100.0)
    world.add_joint(
        DistanceJointDef(
            ground,
            weight,
            length=3.0,
            enable_spring=True,
            spring_hertz=1.0,
            spring_damping_ratio=0.5,
            **limits,
        )
    )
    for _ in range(240):
        world.step(1 / 60, 4)
    height = weight.position.y
    world.destroy()
    return height


def test_a_spring_that_cannot_push_lets_a_weight_on_top_fall_like_a_rope():
    """Holding a weight up from below is pushing, which a rope cannot do."""
    assert propped_height() > 2.0
    assert propped_height(upper_spring_force=0.0) < 0.0


def test_a_spring_that_cannot_pull_props_a_weight_up_like_a_strut():
    """The counterpart: a strut pushes, so the weight stays up."""
    assert propped_height(lower_spring_force=0.0) > 2.0


# --- chain surface materials ------------------------------------------------


@pytest.fixture
def chain_body(world):
    body = world.add_body(position=(0, 0))
    return body


def test_an_open_chain_has_a_segment_between_each_pair_of_points(chain_body):
    chain = chain_body.add_chain([(-15, 0), (-5, -1), (5, -1), (15, 0)])
    assert len(chain.segments) == 3


def test_a_loop_also_joins_its_last_point_to_its_first(chain_body):
    chain = chain_body.add_chain([(-10, 0), (-3, -6), (3, -6), (10, 0)], loop=True)
    assert len(chain.segments) == 4


def test_a_chain_can_have_one_material_per_segment(chain_body):
    frictions = (0.1, 0.5, 0.9, 0.2)
    materials = [SurfaceMaterial(friction=f) for f in frictions]
    chain = chain_body.add_chain(
        [(-10, 0), (-3, -6), (3, -6), (10, 0)], loop=True, materials=materials
    )
    assert [segment.friction for segment in chain.segments] == [
        pytest.approx(f) for f in frictions
    ]


def test_a_chain_rejects_the_wrong_number_of_materials(chain_body):
    """Box2D takes one material or one per segment, nothing between."""
    points = [(-10, 0), (-3, -6), (3, -6), (10, 0)]
    with pytest.raises(ValueError, match="one per segment"):
        chain_body.add_chain(points, materials=[SurfaceMaterial() for _ in range(4)])


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
    materials = [SurfaceMaterial(friction=0.9) for _ in range(3)]
    chain = chain_body.add_chain(
        [(-15, 0), (-5, 0), (5, 0), (15, 0)], materials=materials
    )

    chain.set_surface_material(SurfaceMaterial(friction=0.0), 1)

    frictions = [segment.friction for segment in chain.segments]
    assert frictions == [pytest.approx(0.9), pytest.approx(0.0), pytest.approx(0.9)]


def test_reading_a_material_matches_the_segment(chain_body):
    materials = [SurfaceMaterial(friction=f) for f in (0.1, 0.2, 0.3)]
    chain = chain_body.add_chain(
        [(-15, 0), (-5, 0), (5, 0), (15, 0)], materials=materials
    )

    for index, segment in enumerate(chain.segments):
        assert chain.get_surface_material(index).friction == pytest.approx(
            segment.friction
        )


def test_a_bad_segment_index_raises_rather_than_segfaulting(chain_body):
    """Box2D only asserts the index, and asserts are compiled out of a release
    build, so an unguarded index past the segments reads out of bounds."""
    chain = chain_body.add_chain([(-15, 0), (-5, 0), (5, 0), (15, 0)])

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
