# tests/test_joints.py

import pytest
from box2d import World, Vec2
from box2d._box2d import lib
from pytest import approx


@pytest.fixture
def world_and_bodies():
    world = World()
    body_a = world.new_body().dynamic().position(0, 0).build()
    body_b = world.new_body().dynamic().position(2, 0).build()
    return world, body_a, body_b


def test_mouse_joint_creation(world_and_bodies):
    world, body_a, body_b = world_and_bodies
    world, body_a, body_b = world_and_bodies
    initial_target = Vec2(1, 0)

    joint = world.add_mouse_joint(
        body=body_a, target=initial_target, max_force=500.0, damping_ratio=0.5
    )

    # Verify joint properties
    assert joint.is_valid is True
    assert joint.target == initial_target
    assert joint.max_force == approx(500.0)
    assert joint.damping_ratio == approx(0.5)


def test_mouse_joint_target_update(world_and_bodies):
    world, body_a, body_b = world_and_bodies
    joint = world.add_mouse_joint(body_a, Vec2(1, 0), 500.0, 0.5)

    # Test target position updates
    new_target = Vec2(3, 2)
    joint.target = new_target
    assert joint.target == new_target


def test_mouse_joint_property_setters(world_and_bodies):
    world, body_a, body_b = world_and_bodies
    joint = world.add_mouse_joint(body_a, Vec2(1, 0), 500.0, 0.5)

    # Test property setters
    joint.max_force = 750.0
    assert joint.max_force == approx(750.0)

    joint.damping_ratio = 0.3
    assert joint.damping_ratio == approx(0.3)


def test_mouse_joint_reaction_forces(world_and_bodies):
    world, body_a, body_b = world_and_bodies
    dyn_body = world.new_body().dynamic().position(10, 10).circle(5, density=1).build()
    joint = world.add_mouse_joint(dyn_body, Vec2(5, 3), 500.0, 0.7)

    # Step world to generate forces
    # for _ in range(10):
    world.step(1 / 60)

    # Verify reaction forces make sense
    assert joint.reaction_force.length > 0  # Should have some force
    assert joint.reaction_torque > 0


def test_weld_joint_creation(world_and_bodies):
    world, body_a, body_b = world_and_bodies
    # Create a weld joint with distinct local anchors for clarity.
    weld_joint = world.add_weld_joint(
        body_a, body_b, local_anchor_a=(0, 0), local_anchor_b=(1, 0)
    )
    # Verify the joint was successfully created.
    assert weld_joint.is_valid is True
    # Check that the joint's local anchor positions match the provided values.
    # Note: The anchors are reported in each body's local coordinate system.
    assert weld_joint.anchor_a == Vec2(0, 0)
    assert weld_joint.anchor_b == Vec2(1, 0)


def test_weld_joint_property_setters(world_and_bodies):
    world, body_a, body_b = world_and_bodies
    # Create a weld joint with initial spring/damping parameters.
    weld_joint = world.add_weld_joint(
        body_a,
        body_b,
        local_anchor_a=(0, 0),
        local_anchor_b=(0, 0),
        linear_hertz=4.0,
        linear_damping_ratio=0.25,
        angular_hertz=6.0,
        angular_damping_ratio=0.35,
    )
    # Verify initial parameter values.
    assert weld_joint.linear_hertz == pytest.approx(4.0)
    assert weld_joint.linear_damping_ratio == pytest.approx(0.25)
    assert weld_joint.angular_hertz == pytest.approx(6.0)
    assert weld_joint.angular_damping_ratio == pytest.approx(0.35)

    # Update the joint's spring/damping parameters.
    weld_joint.linear_hertz = 9.0
    weld_joint.linear_damping_ratio = 0.5
    weld_joint.angular_hertz = 12.0
    weld_joint.angular_damping_ratio = 0.7

    # Verify the updated parameter values.
    assert weld_joint.linear_hertz == pytest.approx(9.0)
    assert weld_joint.linear_damping_ratio == pytest.approx(0.5)
    assert weld_joint.angular_hertz == pytest.approx(12.0)
    assert weld_joint.angular_damping_ratio == pytest.approx(0.7)
