"""The mover and pogo joints, Box2D 3.2's pieces for physics-driven characters.

A dynamic character is driven by a mover joint, which pushes it toward a
commanded velocity, and held up off the ground by a pogo joint, a spring that
is rebuilt every step wherever a downward ray lands.
"""

import pytest

from box2d import World, MoverJoint, PogoJoint, MoverJointDef, PogoJointDef

STEP = 1 / 60
SUBSTEPS = 4
#: Box2D solves in substeps, and a joint's impulse is per substep.
SUBSTEP = STEP / SUBSTEPS


@pytest.fixture
def world():
    world = World(gravity=(0, -10))
    yield world
    world.destroy()


def character(world, position=(0, 2)):
    body = world.add_body(body_type="dynamic", position=position, lock_rotation=True)
    body.add_circle(radius=0.5, density=1, friction=0)
    return body


def run(world, steps):
    for _ in range(steps):
        world.step(STEP, SUBSTEPS)


# --- mover joint ------------------------------------------------------------


def test_mover_joint_reaches_the_commanded_velocity(world):
    anchor = world.add_body()
    body = character(world)
    world.add_mover_joint(
        anchor, body, linear_velocity=(3, 0), max_velocity_force=(1000, 0)
    )
    run(world, 60)
    assert body.linear_velocity.x == pytest.approx(3, abs=1e-3)


def test_mover_joint_leaves_an_undriven_axis_alone(world):
    """No force on y, so gravity is still the character's own."""
    anchor = world.add_body()
    body = character(world)
    world.add_mover_joint(
        anchor, body, linear_velocity=(3, 0), max_velocity_force=(1000, 0)
    )
    run(world, 30)
    assert body.linear_velocity.y == pytest.approx(-10 * 30 * STEP, rel=0.05)


def test_mover_joint_force_is_capped(world):
    """A weak drive accelerates slowly: at most force / mass per second."""
    anchor = world.add_body()
    body = character(world)
    world.gravity = (0, 0)
    mass = body.mass
    world.add_mover_joint(
        anchor, body, linear_velocity=(100, 0), max_velocity_force=(mass, 0)
    )
    run(world, 60)
    assert body.linear_velocity.x == pytest.approx(1.0, rel=0.02)


def test_mover_joint_settings_round_trip(world):
    joint = world.add_mover_joint(world.add_body(), character(world))
    assert isinstance(joint, MoverJoint)

    joint.linear_velocity = (1.5, -2)
    joint.max_velocity_force = (40, 7)

    assert joint.linear_velocity == (1.5, -2)
    assert joint.max_velocity_force == (40, 7)


def test_mover_joint_def_ignores_anchors(world):
    definition = MoverJointDef(world.add_body(), character(world), anchor=(1, 1))
    assert "local_anchor_a" not in definition.joint_arguments()


# --- pogo joint -------------------------------------------------------------


def pogo(world, ground, body, **kwargs):
    settings = dict(
        local_anchor_a=(0, 0),
        hertz=5,
        damping_ratio=1,
        rest_length=1.5,
        max_compression_force=1000,
        max_tension_force=1000,
    )
    settings.update(kwargs)
    return world.add_pogo_joint(ground, body, **settings)


def test_pogo_joint_holds_a_body_at_its_rest_length(world):
    ground = world.add_body()
    body = character(world, position=(0, 3))
    joint = pogo(world, ground, body)
    assert isinstance(joint, PogoJoint)

    run(world, 180)

    assert joint.length == pytest.approx(1.5, abs=0.02)
    assert body.position.y == pytest.approx(1.5, abs=0.02)


def test_pogo_joint_impulse_carries_the_weight(world):
    ground = world.add_body()
    body = character(world, position=(0, 1.5))
    joint = pogo(world, ground, body)
    run(world, 180)
    weight = body.mass * 10
    assert joint.impulse / SUBSTEP == pytest.approx(weight, rel=0.02)


def test_pogo_joint_compression_cap_limits_the_push(world):
    """Allowed less force than the weight, the spring cannot hold it up."""
    ground = world.add_body()
    body = character(world, position=(0, 1.5))
    weight = body.mass * 10
    pogo(world, ground, body, max_compression_force=0.5 * weight)
    run(world, 60)
    assert body.position.y < 1.0


def test_pogo_joint_can_be_warm_started(world):
    """Rebuilt each step, as a character does, it holds as steadily as one
    long-lived pogo would -- if each carries the last one's state forward."""
    ground = world.add_body()
    body = character(world, position=(0, 1.5))
    impulse = velocity = 0.0
    for _ in range(180):
        joint = pogo(world, ground, body, impulse=impulse, velocity=velocity)
        world.step(STEP, SUBSTEPS)
        impulse, velocity = joint.impulse, joint.velocity
        joint.destroy()
    assert body.position.y == pytest.approx(1.5, abs=0.02)


def test_pogo_joint_settings_round_trip(world):
    joint = pogo(world, world.add_body(), character(world))
    joint.rest_length = 2.0
    joint.hertz = 3.0
    joint.damping_ratio = 0.5
    assert joint.rest_length == pytest.approx(2.0)
    assert joint.hertz == pytest.approx(3.0)
    assert joint.damping_ratio == pytest.approx(0.5)


def test_pogo_normal_is_normalized(world):
    """Box2D uses the normal as given, so a long one would scale the spring."""
    ground = world.add_body()
    body = character(world, position=(0, 1.5))
    joint = pogo(world, ground, body, normal=(0, 10))
    run(world, 180)
    assert joint.impulse / SUBSTEP == pytest.approx(body.mass * 10, rel=0.02)


def test_pogo_normal_must_have_a_direction(world):
    with pytest.raises(ValueError, match="pogo normal"):
        pogo(world, world.add_body(), character(world), normal=(0, 0))


def test_pogo_joint_def_builds_a_pogo_joint(world):
    definition = PogoJointDef(world.add_body(), character(world), rest_length=1.0)
    assert isinstance(world.add_joint(definition), PogoJoint)
