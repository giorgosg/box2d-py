# tests/test_diagnostics.py
"""What the world reports about itself: timings, sizes, and tuning knobs.

None of this was bound, so there was no way to ask why a scene had got slow,
how much memory it was using, or whether it had come to rest.

Profile and Counters map their fields onto Box2D's structs by converting
snake_case to camelCase rather than listing both names, which is compact but
would silently produce zeros if a name stopped matching. The conformance
tests below check every derived name against the struct.
"""

import os
from dataclasses import fields

import pytest

from box2d import Profile, World
from box2d._box2d import ffi
from box2d.diagnostics import _COUNTER_FIELDS, _PROFILE_FIELDS


@pytest.fixture
def world():
    world = World()
    yield world
    world.destroy()


@pytest.fixture
def busy_world(world):
    """A world with enough in it to have non-trivial counters."""
    ground = world.add_body(position=(0, 0))
    ground.add_box(40, 1)
    for i in range(20):
        body = world.add_body(body_type="dynamic", position=(i % 5, 2 + i))
        body.add_box(0.5, 0.5)
    # Long enough that the boxes are piled up and in contact, but not so long
    # that they have gone to sleep -- a sleeping scene profiles as almost
    # nothing and empties the solver graph.
    for _ in range(150):
        world.step(1 / 60, 4)
    return world


# --- the name mapping, which is derived and so could drift ------------------


def test_every_profile_field_exists_on_the_struct():
    profile = ffi.new("b2Profile*")
    for python_name, c_name in _PROFILE_FIELDS:
        assert hasattr(
            profile, c_name
        ), f"Profile.{python_name} maps to b2Profile.{c_name}, which does not exist"


def test_every_counter_field_exists_on_the_struct():
    counters = ffi.new("b2Counters*")
    for python_name, c_name in _COUNTER_FIELDS:
        assert hasattr(
            counters, c_name
        ), f"Counters.{python_name} maps to b2Counters.{c_name}, which does not exist"


def test_profile_covers_the_whole_struct():
    """A field added to b2Profile should be added here too."""
    c_names = {c_name for _, c_name in _PROFILE_FIELDS}
    struct_names = set(dir(ffi.new("b2Profile*")))
    assert c_names == struct_names, f"unmapped: {struct_names - c_names}"


def test_counters_covers_the_whole_struct():
    c_names = {c_name for _, c_name in _COUNTER_FIELDS} | {"colorCounts"}
    struct_names = set(dir(ffi.new("b2Counters*")))
    assert c_names == struct_names, f"unmapped: {struct_names - c_names}"


def test_conversion_reads_real_values_not_zeros():
    """The mapping could match names and still read the wrong fields."""
    c_profile = ffi.new("b2Profile*")
    for index, (_, c_name) in enumerate(_PROFILE_FIELDS):
        setattr(c_profile, c_name, float(index + 1))

    profile = Profile.from_b2Profile(c_profile)
    for index, (python_name, _) in enumerate(_PROFILE_FIELDS):
        assert getattr(profile, python_name) == pytest.approx(index + 1)


# --- profile ----------------------------------------------------------------


def test_profile_reports_the_last_step(busy_world):
    profile = busy_world.profile
    assert isinstance(profile, Profile)
    assert profile.step > 0.0, "a step with 21 bodies should take measurable time"


def test_profile_phases_are_within_the_total(busy_world):
    """Phases are parts of the step, so none may exceed it."""
    profile = busy_world.profile
    for field in fields(profile):
        if field.name != "step":
            assert getattr(profile, field.name) <= profile.step + 1e-6


def test_slowest_ranks_phases_and_excludes_the_total(busy_world):
    slowest = busy_world.profile.slowest(3)

    assert len(slowest) == 3
    assert "step" not in [name for name, _ in slowest]
    assert [value for _, value in slowest] == sorted(
        (value for _, value in slowest), reverse=True
    )


def test_a_world_that_has_never_stepped_profiles_as_zero(world):
    assert world.profile.step == 0.0


# --- counters ---------------------------------------------------------------


def test_counters_count_what_is_in_the_world(world):
    ground = world.add_body(position=(0, 0))
    ground.add_box(20, 1)
    ball = world.add_body(body_type="dynamic", position=(0, 2))
    ball.add_circle(radius=0.5)
    world.step(1 / 60, 4)

    counters = world.counters
    assert counters.body_count == 2
    assert counters.shape_count == 2
    assert counters.byte_count > 0


def test_counters_track_contacts(world):
    ground = world.add_body(position=(0, 0))
    ground.add_box(20, 1)
    ball = world.add_body(body_type="dynamic", position=(0, 1.4))
    ball.add_circle(radius=0.5)

    for _ in range(60):
        world.step(1 / 60, 4)
    assert world.counters.contact_count >= 1


def test_counters_track_joints(world):
    from box2d import RevoluteJointDef

    ground = world.add_body(position=(0, 0))
    arm = world.add_body(body_type="dynamic", position=(1, 0))
    arm.add_box(2, 0.2)
    world.add_joint(RevoluteJointDef(ground, arm, anchor=(0, 0)))
    world.step(1 / 60, 4)

    assert world.counters.joint_count == 1


def test_color_counts_is_the_full_graph(busy_world):
    """One entry per solver colour; constraints in a colour solve in parallel."""
    colors = busy_world.counters.color_counts
    assert len(colors) == 24
    assert all(isinstance(count, int) for count in colors)
    assert sum(colors) > 0, "20 piled boxes should populate the graph"
    assert sum(colors) < busy_world.counters.contact_count * 24


def test_color_counts_empty_once_everything_sleeps(busy_world):
    """The graph holds what is being solved, not what exists.

    Easy to misread as a bug: the contacts are still counted, but a sleeping
    island is not in the constraint graph, so every colour reads zero.
    """
    for _ in range(600):
        busy_world.step(1 / 60, 4)

    assert busy_world.awake_body_count == 0
    assert busy_world.counters.contact_count > 0, "the contacts still exist"
    assert sum(busy_world.counters.color_counts) == 0


def test_counters_are_independent_objects(world):
    world.step(1 / 60, 4)
    first = world.counters
    body = world.add_body(body_type="dynamic", position=(0, 0))
    body.add_circle(radius=1)
    world.step(1 / 60, 4)

    assert world.counters.body_count == first.body_count + 1
    assert first.body_count == 0, "the earlier snapshot should not have changed"


# --- awake count and bounds -------------------------------------------------


def test_awake_body_count_falls_as_a_scene_settles(world):
    ground = world.add_body(position=(0, 0))
    ground.add_box(20, 1)
    for i in range(5):
        body = world.add_body(body_type="dynamic", position=(i * 2 - 4, 2))
        body.add_box(0.5, 0.5)

    world.step(1 / 60, 4)
    assert world.awake_body_count == 5

    for _ in range(600):
        world.step(1 / 60, 4)
    assert world.awake_body_count == 0, "everything should have settled"


def test_bounds_contain_every_shape(world):
    for x in (-10, 10):
        body = world.add_body(position=(x, 0))
        body.add_circle(radius=1)

    bounds = world.bounds
    assert bounds.lower.x <= -11
    assert bounds.upper.x >= 11


# --- tuning -----------------------------------------------------------------


def test_maximum_linear_speed_round_trips(world):
    world.maximum_linear_speed = 50.0
    assert world.maximum_linear_speed == pytest.approx(50.0)


def test_maximum_linear_speed_caps_a_body(world):
    world.maximum_linear_speed = 5.0
    body = world.add_body(body_type="dynamic", position=(0, 0))
    body.add_circle(radius=0.5)
    body.linear_velocity = (500, 0)
    world.step(1 / 60, 4)

    assert body.linear_velocity.length <= 5.1, "the cap should have applied"


def test_contact_recycle_distance_round_trips(world):
    world.contact_recycle_distance = 0.0
    assert world.contact_recycle_distance == 0.0
    world.contact_recycle_distance = 0.1
    assert world.contact_recycle_distance == pytest.approx(0.1)


def test_worker_count_is_one_for_a_single_threaded_world(world):
    assert world.worker_count == 1


def test_warm_starting_round_trips(world):
    assert world.enable_warm_starting is True, "Box2D defaults it on"
    world.enable_warm_starting = False
    assert world.enable_warm_starting is False
    world.enable_warm_starting = True
    assert world.enable_warm_starting is True


def test_disabling_warm_starting_costs_stability(world):
    """Box2D's header claims this; a tall stack is where it shows."""

    def settle(warm_starting):
        world = World()
        world.enable_warm_starting = warm_starting
        ground = world.add_body(position=(0, 0))
        ground.add_box(20, 1)
        boxes = []
        for i in range(10):
            box = world.add_body(body_type="dynamic", position=(0, 1 + i * 1.02))
            box.add_box(1, 1)
            boxes.append(box)
        for _ in range(240):
            world.step(1 / 60, 4)
        drift = max(abs(box.position.x) for box in boxes)
        world.destroy()
        return drift

    assert settle(True) < settle(
        False
    ), "warm starting should hold the stack straighter"


def test_speculative_can_be_toggled(world):
    """No getter exists, so this only checks the call is wired up."""
    world.enable_speculative(False)
    world.enable_speculative(True)


def test_rebuild_static_tree_keeps_queries_working(world):
    for x in range(20):
        body = world.add_body(position=(x * 2, 0))
        body.add_box(1, 1)
    world.step(1 / 60, 4)

    before = len(world.query_circle((10, 0), 5))
    world.rebuild_static_tree()
    assert len(world.query_circle((10, 0), 5)) == before


def test_dump_memory_stats_writes_its_file(world, tmp_path, monkeypatch):
    """Box2D picks the filename and writes to the working directory."""
    monkeypatch.chdir(tmp_path)
    world.step(1 / 60, 4)
    world.dump_memory_stats()

    assert os.path.exists(tmp_path / "box2d_memory.txt")
