# tests/test_accessor_gaps.py
"""Accessors that existed in Box2D but had no Python counterpart.

Also covers World's settings, which were mirrored in Python attributes rather
than read back from Box2D. Mirroring makes the Python copy authoritative even
though Box2D's is, so anything changing them another way left the two
disagreeing with no way to notice.
"""

import math

import pytest

from box2d import RevoluteJointDef, Vec2, World


@pytest.fixture
def world():
    world = World()
    yield world
    world.destroy()


# --- world settings now come from Box2D -------------------------------------


@pytest.mark.parametrize(
    "name,value",
    [
        ("enable_sleep", False),
        ("enable_continuous", False),
        ("restitution_threshold", 3.5),
        ("hit_event_threshold", 7.25),
    ],
)
def test_world_settings_round_trip(world, name, value):
    setattr(world, name, value)
    read_back = getattr(world, name)
    if isinstance(value, bool):
        assert read_back is value
    else:
        assert read_back == pytest.approx(value)


def test_world_settings_are_not_a_python_mirror(world):
    """The value must come from Box2D, not from a cached attribute."""
    world.restitution_threshold = 2.0
    assert not hasattr(world, "_restitution_threshold")
    assert world.restitution_threshold == pytest.approx(2.0)


def test_contact_tuning_is_still_cached(world):
    """Box2D has only a combined setter for these and no getter."""
    world.contact_hertz = 25.0
    assert world.contact_hertz == pytest.approx(25.0)
    assert hasattr(world, "_contact_hertz")


# --- body ------------------------------------------------------------------


def test_body_enable_sleep(world):
    body = world.add_body(body_type="dynamic")
    body.enable_sleep = False
    assert body.enable_sleep is False
    body.enable_sleep = True
    assert body.enable_sleep is True


def test_clear_forces(world):
    """Applied force is discarded rather than integrated on the next step."""
    ground = world.add_body(position=(0, -5))
    ground.add_box(40, 1)
    kept = world.add_body(body_type="dynamic", position=(-5, 0))
    kept.add_circle(radius=0.5)
    cleared = world.add_body(body_type="dynamic", position=(5, 0))
    cleared.add_circle(radius=0.5)

    kept.apply_force((500, 0))
    cleared.apply_force((500, 0))
    cleared.clear_forces()
    world.step(1 / 60, 4)

    assert kept.linear_velocity.x > 0.1
    assert cleared.linear_velocity.x == pytest.approx(0.0, abs=1e-3)


def test_wake_touching(world):
    ground = world.add_body(position=(0, 0))
    ground.add_box(40, 1)
    sleeper = world.add_body(body_type="dynamic", position=(0, 1))
    sleeper.add_box(1, 1)

    for _ in range(400):
        world.step(1 / 60, 4)
    assert sleeper.awake is False

    ground.wake_touching()
    assert sleeper.awake is True


def test_set_target_transform_drives_a_kinematic_body(world):
    """Assigning position teleports; this moves, so collision still works."""
    platform = world.add_body(body_type="kinematic", position=(0, 0))
    platform.add_box(2, 0.5)

    platform.set_target_transform((1, 0), math.radians(10), 1 / 60)

    assert platform.linear_velocity.x == pytest.approx(60.0, abs=1.0)
    assert platform.angular_velocity > 0.0


def test_set_target_transform_can_leave_a_sleeper_alone(world):
    platform = world.add_body(body_type="kinematic", position=(0, 0))
    platform.add_box(2, 0.5)
    platform.set_target_transform((1, 0), 0.0, 1 / 60, wake=False)


# --- joint -----------------------------------------------------------------


@pytest.fixture
def joint(world):
    a = world.add_body(position=(0, 0))
    a.add_box(2, 0.5)
    b = world.add_body(body_type="dynamic", position=(0, -2))
    b.add_box(1, 1, density=10.0)
    return world.add_joint(RevoluteJointDef(a, b, anchor=(0, 0)))


def test_joint_type_is_reported(joint):
    assert isinstance(joint.joint_type, int)


def test_joint_separations_start_near_zero(world, joint):
    world.step(1 / 60, 4)
    assert joint.linear_separation == pytest.approx(0.0, abs=0.01)
    assert joint.angular_separation == pytest.approx(0.0, abs=0.01)


def test_joint_separation_is_readable_under_load(world, joint):
    """A loaded joint drifts, which is what a breakable joint watches."""
    for _ in range(60):
        world.step(1 / 60, 4)
    assert joint.linear_separation >= 0.0
    assert isinstance(joint.angular_separation, float)
