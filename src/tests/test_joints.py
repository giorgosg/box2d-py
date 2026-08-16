# tests/test_joints.py

import pytest
from box2d import World, Vec2, MouseJoint, WeldJoint, RevoluteJoint
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

    joint = MouseJoint(
        world=world,
        body=body_a,
        target=initial_target,
        max_force=500.0,
        damping_ratio=0.5,
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

    # Verify reaction forces make sense. Since 3.2 the mouse joint is a motor
    # joint with a linear spring only, so it pulls without twisting: force is
    # non-zero, torque is not.
    assert joint.constraint_force.length > 0
    assert joint.constraint_torque == 0


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
    assert weld_joint.local_anchor_a == Vec2(0, 0)
    assert weld_joint.local_anchor_b == Vec2(1, 0)


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


def test_revolute_joint_creation(world_and_bodies):
    world, body_a, body_b = world_and_bodies
    # Create a revolute joint with distinct local anchors for each body, as well as limit and motor settings.
    revolute_joint = RevoluteJoint(
        world=world,
        body_a=body_a,
        body_b=body_b,
        local_anchor_a=(0, 0),  # Local anchor on body_a
        local_anchor_b=(1, 1),  # Local anchor on body_b
        collide_connected=False,
        lower_angle=-0.5,
        upper_angle=0.5,
        enable_limit=True,
        motor_speed=2.0,
        max_motor_torque=10.0,
        enable_motor=True,
        reference_angle=0.0,
    )

    # Verify that the joint is valid.
    assert revolute_joint.is_valid is True

    # Check that the joint's local anchor positions match those provided.
    # Note: The Joint base class exposes properties 'local_anchor_a' and 'local_anchor_b'
    # which reflect each body's local connection point.
    assert revolute_joint.local_anchor_a == Vec2(0, 0)
    assert revolute_joint.local_anchor_b == Vec2(1, 1)

    # Verify limit and motor settings.
    assert revolute_joint.lower_limit == pytest.approx(-0.5)
    assert revolute_joint.upper_limit == pytest.approx(0.5)
    assert revolute_joint.motor_speed == pytest.approx(2.0)
    assert revolute_joint.max_motor_torque == pytest.approx(10.0)


def test_revolute_joint_via_world_method(world_and_bodies):
    world, body_a, body_b = world_and_bodies
    # Create the revolute joint using the world's add function.
    revolute_joint = world.add_revolute_joint(
        body_a=body_a,
        body_b=body_b,
        local_anchor_a=(0, 0),
        local_anchor_b=(1, 1),
        collide_connected=True,
        lower_angle=-0.5,
        upper_angle=0.5,
        enable_limit=True,
        motor_speed=2.0,
        max_motor_torque=10.0,
        enable_motor=True,
        reference_angle=0.0,
    )

    # Verify joint validity.
    assert revolute_joint.is_valid is True

    # Check that the local anchor points match the provided values.
    from box2d import Vec2

    assert revolute_joint.local_anchor_a == Vec2(0, 0)
    assert revolute_joint.local_anchor_b == Vec2(1, 1)

    # Verify joint limit and motor settings.
    import pytest

    assert revolute_joint.lower_limit == pytest.approx(-0.5)
    assert revolute_joint.upper_limit == pytest.approx(0.5)
    assert revolute_joint.motor_speed == pytest.approx(2.0)
    assert revolute_joint.max_motor_torque == pytest.approx(10.0)


# --- destroying joints, which nothing exercised before ----------------------


@pytest.fixture
def joint_bodies():
    world = World()
    a = world.new_body().dynamic().position(0, 0).build()
    a.add_circle(radius=1.0)
    b = world.new_body().dynamic().position(2, 0).build()
    b.add_circle(radius=1.0)
    yield world, a, b
    world.destroy()


def make_joint(kind, world, a, b):
    anchors = dict(local_anchor_a=(0, 0), local_anchor_b=(0, 0))
    if kind == "revolute":
        return world.add_revolute_joint(a, b, **anchors)
    if kind == "weld":
        return world.add_weld_joint(a, b, **anchors)
    if kind == "distance":
        return world.add_distance_joint(a, b, length=2.0, **anchors)
    if kind == "prismatic":
        return world.add_prismatic_joint(a, b, axis=(1, 0), **anchors)
    if kind == "wheel":
        return world.add_wheel_joint(a, b, axis=(0, 1), **anchors)
    if kind == "motor":
        return world.add_motor_joint(a, b)
    if kind == "mouse":
        return world.add_mouse_joint(a, (1, 1))
    raise AssertionError(kind)


@pytest.mark.parametrize(
    "kind", ["revolute", "weld", "distance", "prismatic", "wheel", "motor", "mouse"]
)
def test_joint_destroy(kind, joint_bodies):
    """b2DestroyJoint gained a wakeAttached argument in 3.2 and nothing noticed."""
    world, a, b = joint_bodies
    joint = make_joint(kind, world, a, b)

    joint.destroy()

    assert joint.is_valid is False
    world.step(1 / 60, 4)


@pytest.mark.parametrize(
    "kind", ["revolute", "weld", "distance", "prismatic", "wheel", "motor", "mouse"]
)
def test_joint_destroy_is_idempotent(kind, joint_bodies):
    world, a, b = joint_bodies
    joint = make_joint(kind, world, a, b)
    joint.destroy()
    joint.destroy()


def test_joint_destroy_can_leave_bodies_asleep(joint_bodies):
    world, a, b = joint_bodies
    joint = make_joint("revolute", world, a, b)
    joint.destroy(wake_attached=False)
    assert joint.is_valid is False


def test_mouse_joint_destroy_removes_its_proxy_body(joint_bodies):
    """The proxy is an implementation detail; it must not outlive the joint."""
    world, a, b = joint_bodies
    before = len(world.bodies)

    joint = world.add_mouse_joint(a, (1, 1))
    assert len(world.bodies) == before + 1

    joint.destroy()
    assert len(world.bodies) == before
