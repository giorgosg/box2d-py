# tests/test_human.py
"""The jointed figure behind the ragdoll scenarios.

Ported from Box2D's shared/human.c, where each of the eleven bones is written
out in full. Here they are a table and one loop, so the tests below check the
table against what actually gets built as much as they check behaviour.
"""

import math
import random

import pytest

from box2d import World
from box2d_testbed.human import BONES, Human


@pytest.fixture
def world():
    world = World()
    ground = world.add_body(position=(0, 0))
    ground.add_segment((-40, 0), (40, 0))
    yield world
    world.destroy()


@pytest.fixture
def human(world):
    return Human(world, (0, 0), friction_torque=0.05)


# --- the table ---------------------------------------------------------------


def test_every_bone_is_built(human):
    assert len(human.bones) == len(BONES) == 11
    assert [bone.name for bone in human.bones] == [d.name for d in BONES]


def test_only_the_root_has_no_joint(human):
    """Ten joints for eleven bones: the hip hangs from nothing."""
    assert human.bones[0].name == "hip"
    assert human.bones[0].joint is None
    assert len(human.joints) == 10
    assert all(bone.joint is not None for bone in human.bones[1:])


def test_parents_are_defined_before_their_children():
    """The build loop looks parents up as it goes, so order matters."""
    seen = set()
    for definition in BONES:
        if definition.parent is not None:
            assert (
                definition.parent in seen
            ), f"{definition.name} is built before its parent {definition.parent}"
        seen.add(definition.name)


def test_bones_are_placed_at_their_declared_heights(human):
    for definition, bone in zip(BONES, human.bones):
        assert bone.body.position.y == pytest.approx(definition.y, abs=1e-4)


def test_scale_multiplies_every_measurement(world):
    small = Human(world, (0, 0), scale=0.5)
    large = Human(world, (10, 0), scale=2.0, group_index=2)

    for definition, bone_s, bone_l in zip(BONES, small.bones, large.bones):
        assert bone_s.body.position.y == pytest.approx(definition.y * 0.5, abs=1e-4)
        assert bone_l.body.position.y == pytest.approx(definition.y * 2.0, abs=1e-4)


def test_feet_are_attached_to_the_lower_legs(human):
    """Two shapes on each lower leg: the capsule and the foot hull."""
    footed = [bone for bone in human.bones if len(bone.body.shapes) == 2]
    assert sorted(bone.name for bone in footed) == [
        "lower_left_leg",
        "lower_right_leg",
    ]


def test_bones_are_named_for_debug_draw(human):
    assert human.bone("head").body.name == "head"
    assert human.torso.name == "torso"


# --- joints ------------------------------------------------------------------


def test_joint_limits_match_the_table(human):
    for definition, bone in zip(BONES[1:], human.bones[1:]):
        lower, upper = definition.limits
        assert bone.joint.limit_enabled is True
        assert bone.joint.lower_limit == pytest.approx(lower, abs=1e-5)
        assert bone.joint.upper_limit == pytest.approx(upper, abs=1e-5)


def test_friction_scale_reaches_the_motor_torque(world):
    """A head resists turning far less than a hip, which is the friction scale."""
    human = Human(world, (0, 0), friction_torque=1.0, scale=1.0)

    head = human.bone("head")
    upper_leg = human.bone("upper_left_leg")
    assert head.joint.max_motor_torque < upper_leg.joint.max_motor_torque
    assert head.joint.max_motor_torque == pytest.approx(0.25)
    assert upper_leg.joint.max_motor_torque == pytest.approx(1.0)


def test_springs_are_off_unless_asked_for(world):
    limp = Human(world, (0, 0))
    assert all(joint.spring_enabled is False for joint in limp.joints)

    sprung = Human(world, (10, 0), hertz=4.0, damping_ratio=0.5, group_index=2)
    assert all(joint.spring_enabled is True for joint in sprung.joints)
    assert all(joint.spring_hertz == pytest.approx(4.0) for joint in sprung.joints)


def test_joint_limits_hold_when_the_figure_lands(world):
    """The limits are what keep a fall looking like a body folding up."""
    random.seed(11)
    human = Human(world, (0, 12), friction_torque=0.05)
    human.apply_random_angular_impulse(20.0)

    worst = 0.0
    for _ in range(600):
        world.step(1 / 60, 4)
        for definition, bone in zip(BONES[1:], human.bones[1:]):
            lower, upper = definition.limits
            angle = bone.joint.angle
            worst = max(worst, lower - angle, angle - upper)

    # Box2D's limits are soft, so a hard landing overshoots a little; what
    # matters is that nothing inverts.
    assert worst < 0.4, f"a joint bent {worst:.2f} rad past its limit"


# --- collision filtering -----------------------------------------------------


def _contacts_between_tags(world, steps=240):
    """Tags of the two shapes in every contact reported, as a set of pairs.

    Each figure's bodies carry a tag as user_data, so a contact can be traced
    back to which figure -- or figures -- it belongs to.
    """
    for body in world.bodies:
        body.enable_contact_events()

    pairs = set()
    for _ in range(steps):
        world.step(1 / 60, 4)
        for event in world.get_contact_events().begin:
            tag_a = event.shape_a.body.user_data
            tag_b = event.shape_b.body.user_data
            if tag_a is not None and tag_b is not None:
                pairs.add(frozenset((tag_a, tag_b)))
    return pairs


def test_a_figure_never_collides_with_itself(world):
    """The negative group index: otherwise the bones fight as it folds up."""
    Human(world, (0, 8), user_data="solo")

    pairs = _contacts_between_tags(world)

    assert frozenset(("solo",)) not in pairs, "bones of one figure collided"


def test_two_figures_do_collide_with_each_other(world):
    """Different group indices, so a crowd piles up rather than interpenetrating."""
    Human(world, (0, 0), group_index=1, user_data="lower")
    Human(world, (0, 3), group_index=2, user_data="upper")

    pairs = _contacts_between_tags(world)

    assert frozenset(("lower", "upper")) in pairs, "the two figures passed through"
    assert frozenset(("lower",)) not in pairs, "and neither collided with itself"
    assert frozenset(("upper",)) not in pairs


# --- driving it --------------------------------------------------------------


def test_set_velocity_moves_every_bone(human):
    human.set_velocity((5.0, 0.0))
    assert all(
        bone.body.linear_velocity.x == pytest.approx(5.0) for bone in human.bones
    )


def test_zero_friction_turns_the_motors_off(human):
    human.set_joint_friction_torque(0.0)
    assert all(joint.motor_enabled is False for joint in human.joints)

    human.set_joint_friction_torque(0.5)
    assert all(joint.motor_enabled is True for joint in human.joints)


def test_friction_torque_is_scaled_per_joint(world):
    human = Human(world, (0, 0), scale=2.0)
    human.set_joint_friction_torque(1.0)

    # scale (2.0) times the joint's own share (0.25 for the head).
    assert human.bone("head").joint.max_motor_torque == pytest.approx(0.5)


def test_zero_hertz_turns_the_springs_off(world):
    human = Human(world, (0, 0), hertz=4.0, damping_ratio=0.5)
    human.set_joint_spring_hertz(0.0)
    assert all(joint.spring_enabled is False for joint in human.joints)


def test_sensor_events_can_be_enabled(human):
    human.enable_sensor_events(True)
    assert all(
        shape.enable_sensor_events for bone in human.bones for shape in bone.body.shapes
    )


def test_random_impulse_spins_the_torso(world):
    random.seed(3)
    human = Human(world, (0, 10))
    before = human.torso.angular_velocity
    human.apply_random_angular_impulse(50.0)
    assert human.torso.angular_velocity != pytest.approx(before)


# --- lifetime ----------------------------------------------------------------


def test_destroy_removes_everything(world):
    human = Human(world, (0, 5))
    assert len(world.bodies) == 12  # eleven bones and the ground

    human.destroy()

    assert len(world.bodies) == 1
    assert human.bones == []


def test_repeated_spawning_leaks_nothing(world):
    """The ragdoll scenario respawns on a button, so this must stay flat."""
    for _ in range(20):
        human = Human(world, (0, 5))
        for _ in range(5):
            world.step(1 / 60, 4)
        human.destroy()

    assert len(world.bodies) == 1
    assert world.counters.joint_count == 0


def test_destroy_is_safe_after_the_world_took_the_bodies(world):
    """Destroying a body takes its joints, so the ids may already be gone."""
    human = Human(world, (0, 5))
    for bone in human.bones:
        bone.body.destroy()

    human.destroy()  # must not raise
    assert human.bones == []


# --- falling -----------------------------------------------------------------


def test_a_dropped_figure_lands_and_settles(world):
    random.seed(7)
    human = Human(world, (0, 10), friction_torque=0.05)

    for _ in range(600):
        world.step(1 / 60, 4)

    assert all(bone.body.position.y < 1.5 for bone in human.bones), "it should be down"
    assert all(bone.body.position.y > -0.5 for bone in human.bones), "not through it"


def test_a_stiff_figure_folds_less_than_a_limp_one(world):
    """What the friction control is for."""

    def spread_after_landing(friction):
        world = World()
        ground = world.add_body(position=(0, 0))
        ground.add_segment((-40, 0), (40, 0))
        random.seed(5)
        human = Human(world, (0, 8), friction_torque=friction)
        for _ in range(500):
            world.step(1 / 60, 4)
        head = human.head.position
        feet = human.bone("lower_left_leg").body.position
        distance = math.hypot(head.x - feet.x, head.y - feet.y)
        world.destroy()
        return distance

    # A stiff figure keeps its head further from its feet: it stays extended
    # rather than crumpling into a pile.
    assert spread_after_landing(1.0) > spread_after_landing(0.0)


# --- resizing ----------------------------------------------------------------


def test_set_scale_resizes_every_measurement(world):
    human = Human(world, (0, 5), scale=1.0)
    head_radius = human.head.shapes[0].geometry.radius

    human.set_scale(3.0)

    assert human.scale == 3.0
    assert human.head.shapes[0].geometry.radius == pytest.approx(head_radius * 3.0)
    for definition, bone in zip(BONES, human.bones):
        offset = bone.body.position.y - human.hip.position.y
        expected = (definition.y - BONES[0].y) * 3.0
        assert offset == pytest.approx(expected, abs=1e-3)


def test_set_scale_keeps_the_hip_where_it_was(world):
    human = Human(world, (0, 5), scale=1.0)
    hip_before = human.hip.position

    human.set_scale(4.0)

    assert human.hip.position.x == pytest.approx(hip_before.x)
    assert human.hip.position.y == pytest.approx(hip_before.y)


def test_set_scale_updates_mass(world):
    """Shapes changed size, so the mass has to be recomputed from them."""
    human = Human(world, (0, 5), scale=1.0)
    mass = human.head.mass

    human.set_scale(2.0)

    # Mass goes with area in two dimensions, so doubling the size quadruples it.
    assert human.head.mass == pytest.approx(4.0 * mass, rel=0.05)


def test_set_scale_grows_friction_by_the_cube(world):
    human = Human(world, (0, 5), scale=1.0, friction_torque=1.0)
    torque = human.bone("head").joint.max_motor_torque

    human.set_scale(3.0)

    assert human.bone("head").joint.max_motor_torque == pytest.approx(27.0 * torque)


def test_set_scale_is_measured_from_the_original(world):
    """Scaling twice must not compound: 2 then 4 is 4, not 8."""
    human = Human(world, (0, 5), scale=1.0, friction_torque=1.0)
    human.set_scale(2.0)
    human.set_scale(4.0)

    assert human.scale == 4.0
    assert human.bone("head").joint.max_motor_torque == pytest.approx(
        64.0 * 0.25, rel=1e-3
    )


def test_a_too_small_scale_is_refused(world):
    """The feet are a hull, and below about half size Box2D cannot build one."""
    human = Human(world, (0, 5), scale=1.0)

    with pytest.raises(ValueError, match="minimum polygon size"):
        human.set_scale(0.2)


def test_a_refused_scale_changes_nothing(world):
    """It is checked up front, so a figure is never left half resized."""
    human = Human(world, (0, 5), scale=1.0)
    before = [bone.body.position.y for bone in human.bones]

    with pytest.raises(ValueError):
        human.set_scale(0.2)

    assert [bone.body.position.y for bone in human.bones] == before
    assert human.scale == 1.0


def test_a_negative_scale_is_refused(world):
    human = Human(world, (0, 5))
    with pytest.raises(ValueError, match="must be positive"):
        human.set_scale(-1.0)


def test_a_resized_figure_still_simulates(world):
    """The joints must survive being rebuilt underneath the figure."""
    human = Human(world, (0, 8), scale=1.0)
    human.set_scale(5.0)

    for _ in range(300):
        world.step(1 / 60, 4)

    assert all(joint.is_valid for joint in human.joints)
    assert all(abs(bone.body.position.x) < 50 for bone in human.bones)
