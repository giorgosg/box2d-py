# tests/test_events.py
"""The world reports what happened during a step.

Sensor events were the only kind bound; contact, body-move and joint events
were not, so there was no way to learn that two things had hit each other.
"""

import pytest

from box2d import (
    ContactBeginEvent,
    ContactEndEvent,
    ContactEvents,
    ContactHitEvent,
    RevoluteJointDef,
    Vec2,
    World,
)


@pytest.fixture
def world():
    world = World()
    yield world
    world.destroy()


def drop_ball(world, *, contacts=True, hits=False, restitution=0.0):
    """A ball falling onto the ground, both opted into the given events."""
    ground = world.add_body(position=(0, 0))
    ground.add_box(
        20,
        1,
        enable_contact_events=contacts,
        enable_hit_events=hits,
        restitution=restitution,
    )
    ball = world.add_body(body_type="dynamic", position=(0, 6))
    ball.add_circle(
        radius=0.5,
        enable_contact_events=contacts,
        enable_hit_events=hits,
        restitution=restitution,
    )
    return ground, ball


def collect(world, steps=240):
    """Step the world, gathering every event it reports."""
    gathered = ContactEvents()
    for _ in range(steps):
        world.step(1 / 60, 4)
        events = world.get_contact_events()
        gathered.begin.extend(events.begin)
        gathered.end.extend(events.end)
        gathered.hit.extend(events.hit)
    return gathered


# --- contact events ---------------------------------------------------------


def test_contact_begin_is_reported(world):
    ground, ball = drop_ball(world)
    events = collect(world)

    assert events.begin, "the ball never reported touching the ground"
    touch = events.begin[0]
    assert isinstance(touch, ContactBeginEvent)
    assert {touch.shape_a, touch.shape_b} == {ground.shapes[0], ball.shapes[0]}


def test_contact_end_is_reported(world):
    ground, ball = drop_ball(world, restitution=0.8)
    events = collect(world)

    assert events.end, "a bouncing ball should leave the ground again"
    assert isinstance(events.end[0], ContactEndEvent)


def test_no_contact_events_without_opting_in(world):
    """Box2D defaults these off, and the binding must not quietly enable them."""
    drop_ball(world, contacts=False)
    assert not collect(world).begin


def test_hit_events_carry_the_collision(world):
    ground, ball = drop_ball(world, hits=True, restitution=0.5)
    events = collect(world)

    assert events.hit, "a ball dropped 6m should hit hard enough to report"
    hit = events.hit[0]
    assert isinstance(hit, ContactHitEvent)
    assert isinstance(hit.point, Vec2)
    assert isinstance(hit.normal, Vec2)
    assert hit.approach_speed > 1.0
    assert hit.normal.y == pytest.approx(1.0, abs=0.1)


def test_hit_events_respect_the_world_threshold(world):
    """Below the threshold a collision is a touch, not a hit."""
    world.hit_event_threshold = 1000.0
    drop_ball(world, hits=True)
    events = collect(world)

    assert events.begin, "it still touched"
    assert not events.hit, "but nothing was fast enough to count as a hit"


def test_events_describe_only_the_last_step(world):
    """Reading is repeatable until the next step, which replaces the events."""
    drop_ball(world)
    for _ in range(240):
        world.step(1 / 60, 4)
        if world.get_contact_events().begin:
            # Reading does not consume: the same step reports the same events.
            assert len(world.get_contact_events().begin) == 1
            world.step(1 / 60, 4)
            assert not world.get_contact_events().begin, "the step did not replace them"
            break
    else:
        pytest.fail("no contact was ever reported")


def test_contact_events_are_falsy_when_empty(world):
    assert not ContactEvents()
    assert len(ContactEvents()) == 0
    assert world.get_contact_events() is not None


def test_body_can_enable_events_for_all_its_shapes(world):
    """The per-body toggle saves opting in shape by shape."""
    ground = world.add_body(position=(0, 0))
    ground.add_box(20, 1)
    ball = world.add_body(body_type="dynamic", position=(0, 6))
    ball.add_circle(radius=0.5)

    ground.enable_contact_events()
    ball.enable_contact_events()

    assert collect(world).begin


# --- body move events -------------------------------------------------------


def test_body_move_events_report_movers(world):
    ground = world.add_body(position=(0, 0))
    ground.add_box(20, 1)
    ball = world.add_body(body_type="dynamic", position=(0, 6))
    ball.add_circle(radius=0.5)

    world.step(1 / 60, 4)
    events = world.get_body_events()

    assert len(events) == 1, "only the falling ball moved"
    move = events[0]
    assert move.body is ball
    assert move.transform.p.y == pytest.approx(ball.position.y)
    assert move.fell_asleep is False


def test_body_move_events_report_falling_asleep(world):
    ground = world.add_body(position=(0, 0))
    ground.add_box(20, 1)
    ball = world.add_body(body_type="dynamic", position=(0, 2))
    ball.add_circle(radius=0.5)

    slept = 0
    for _ in range(400):
        world.step(1 / 60, 4)
        slept += sum(1 for event in world.get_body_events() if event.fell_asleep)
    assert slept == 1, "the ball should settle and be reported asleep once"


def test_static_bodies_do_not_report_moves(world):
    ground = world.add_body(position=(0, 0))
    ground.add_box(20, 1)
    for _ in range(10):
        world.step(1 / 60, 4)
    assert world.get_body_events() == []


# --- joint events -----------------------------------------------------------


def test_joint_reports_nothing_without_a_threshold(world):
    ground = world.add_body(position=(0, 0))
    weight = world.add_body(body_type="dynamic", position=(0, -3))
    weight.add_box(2, 2, density=200.0)
    world.add_joint(RevoluteJointDef(ground, weight, anchor=(0, 0)))

    for _ in range(60):
        world.step(1 / 60, 4)
        assert world.get_joint_events() == []


def test_joint_reports_above_its_force_threshold(world):
    ground = world.add_body(position=(0, 0))
    weight = world.add_body(body_type="dynamic", position=(0, -3))
    weight.add_box(2, 2, density=200.0)
    joint = world.add_joint(RevoluteJointDef(ground, weight, anchor=(0, 0)))
    joint.force_threshold = 100.0

    reported = []
    for _ in range(60):
        world.step(1 / 60, 4)
        reported.extend(world.get_joint_events())

    assert reported, "a heavy weight should pass a 100N threshold"
    assert reported[0].joint is joint


def test_thresholds_round_trip(world):
    ground = world.add_body(position=(0, 0))
    other = world.add_body(body_type="dynamic", position=(1, 0))
    joint = world.add_joint(RevoluteJointDef(ground, other, anchor=(0, 0)))

    joint.force_threshold = 250.0
    joint.torque_threshold = 75.0
    assert joint.force_threshold == pytest.approx(250.0)
    assert joint.torque_threshold == pytest.approx(75.0)


# --- the sensor opt-in that used to be creation-only ------------------------


def test_sensor_events_can_be_toggled_after_creation(world):
    sensor_body = world.add_body(position=(0, 0))
    sensor = sensor_body.add_box(4, 4, is_sensor=True)
    visitor_body = world.add_body(body_type="dynamic", position=(0, 0))
    visitor = visitor_body.add_circle(radius=0.5)

    visitor.enable_sensor_events = False
    world.step(1 / 60, 4)
    assert sensor.sensor_overlaps == []

    visitor.enable_sensor_events = True
    world.step(1 / 60, 4)
    assert len(sensor.sensor_overlaps) == 1
