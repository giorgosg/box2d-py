"""World and body settings Box2D 3.2 added: restitution solver tuning,
continuous collision safety factor, body extents, the state hash, the SSE2
fallback, and the build's version and SIMD support."""

import pytest

import box2d
from box2d import World, HAS_THREADS

STEP = 1 / 60


@pytest.fixture
def world():
    world = World()
    yield world
    world.destroy()


def pile(world):
    """A small, deterministic pile of boxes to step."""
    ground = world.add_body()
    ground.add_box(20, 1)
    for i in range(12):
        body = world.add_body(
            body_type="dynamic", position=((i % 4) * 1.1 - 2, 1 + (i // 4) * 1.1)
        )
        body.add_box(1, 1, restitution=0.3)


def stepped_hash(steps=90, **world_args):
    world = World(**world_args)
    pile(world)
    for _ in range(steps):
        world.step(STEP, 4)
    value = world.state_hash
    world.destroy()
    return value


# --- version and SIMD -------------------------------------------------------


def test_box2d_version_is_reported():
    assert box2d.BOX2D_VERSION >= (3, 2, 0)


def test_avx2_support_is_reported():
    assert isinstance(box2d.HAS_AVX2, bool)


# --- restitution ------------------------------------------------------------


def test_restitution_iterations_round_trip(world):
    world.restitution_iterations = 12
    assert world.restitution_iterations == 12


def test_restitution_propagation_round_trips(world):
    assert world.enable_restitution_propagation is False
    world.enable_restitution_propagation = True
    assert world.enable_restitution_propagation is True


# --- state hash -------------------------------------------------------------


def test_state_hash_matches_for_identical_simulations():
    assert stepped_hash() == stepped_hash()


def test_state_hash_changes_as_the_world_moves():
    assert stepped_hash(steps=10) != stepped_hash(steps=11)


@pytest.mark.skipif(not HAS_THREADS, reason="this build has no threads")
def test_state_hash_ignores_the_thread_count():
    assert stepped_hash(threads=1) == stepped_hash(threads=4)


def test_sse2_fallback_simulates_identically():
    """Box2D's solvers are deterministic across instruction sets, so the
    fallback is a comparison tool, not a different simulation."""
    reference = stepped_hash()

    world = World()
    world.enable_sse2_fallback(True)
    pile(world)
    for _ in range(90):
        world.step(STEP, 4)
    assert world.state_hash == reference
    world.destroy()


# --- bodies -----------------------------------------------------------------


def test_safety_factor_defaults_to_half(world):
    assert world.add_body(body_type="dynamic").safety_factor == pytest.approx(0.5)


def test_safety_factor_can_be_set_at_creation(world):
    body = world.add_body(body_type="dynamic", safety_factor=0.1)
    assert body.safety_factor == pytest.approx(0.1)

    built = world.new_body().dynamic().safety_factor(0.2).build()
    assert built.safety_factor == pytest.approx(0.2)


def test_safety_factor_is_settable(world):
    body = world.add_body(body_type="dynamic")
    body.safety_factor = 0.05
    assert body.safety_factor == pytest.approx(0.05)


def test_body_extents_describe_its_shapes(world):
    body = world.add_body(body_type="dynamic", position=(5, 5))
    body.add_circle(radius=0.5, center=(2, 0))

    assert body.min_extent == pytest.approx(0.5, abs=1e-3)
    assert body.max_extent == pytest.approx(0.5, abs=1e-3)
    assert body.max_extent_origin >= 2.5 - 1e-3


# --- distance joint spring force --------------------------------------------


def test_distance_joint_reports_its_spring_force(world):
    """A spring stretched past its length pulls, which reads negative."""
    world.gravity = (0, 0)
    anchor = world.add_body()
    weight = world.add_body(body_type="dynamic", position=(3, 0))
    weight.add_circle(radius=0.25)
    joint = world.add_distance_joint(
        anchor, weight, length=1, enable_spring=True, hertz=2, damping_ratio=0.5
    )
    world.step(STEP, 4)
    assert joint.spring_force < 0


def test_distance_joint_spring_force_is_zero_without_a_spring(world):
    anchor = world.add_body()
    weight = world.add_body(body_type="dynamic", position=(3, 0))
    weight.add_circle(radius=0.25)
    joint = world.add_distance_joint(anchor, weight, length=1)
    world.step(STEP, 4)
    assert joint.spring_force == 0
