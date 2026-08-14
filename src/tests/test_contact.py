# tests/test_contact.py
"""Contacts can be held onto and inspected.

Box2D 3.2 added a persistent contact id, so a contact seen beginning can be
followed until the matching end event. Neither b2Contact_GetData nor
b2Contact_IsValid was bound, so there was no way to reach the manifold of a
particular contact.

Binding them also uncovered that the manifold conversion had been broken since
the 3.2 upgrade: it read a 'point' field 3.2 removed and a 'maxNormalImpulse'
3.2 renamed. Nothing caught it because every existing test only ever saw an
empty contact list, so no manifold point was ever built.
"""

import pytest

from box2d import Contact, Vec2, World
from box2d.dataclasses import ContactData, Manifold, ManifoldPoint


@pytest.fixture
def world():
    world = World()
    yield world
    world.destroy()


@pytest.fixture
def touching(world):
    """A ball resting on the ground, both reporting contacts."""
    ground = world.add_body(position=(0, 0))
    ground.add_box(20, 1, enable_contact_events=True)
    ball = world.add_body(body_type="dynamic", position=(0, 2))
    ball.add_circle(radius=0.5, enable_contact_events=True)
    for _ in range(120):
        world.step(1 / 60, 4)
    return ground, ball


# --- the manifold conversion that was broken --------------------------------


def test_shape_contact_data_builds_a_manifold(touching):
    """This raised AttributeError for every touching contact since the 3.2 bump."""
    ground, ball = touching
    contacts = ball.shapes[0].contact_data

    assert contacts, "the ball is resting on the ground"
    data = contacts[0]
    assert isinstance(data, ContactData)
    assert isinstance(data.manifold, Manifold)
    assert data.manifold.points, "a resting contact has at least one point"


def test_manifold_normal_is_a_vector_not_a_tuple(touching):
    """A stray trailing comma had been making the normal a one-element tuple."""
    ground, ball = touching
    manifold = ball.shapes[0].contact_data[0].manifold

    assert isinstance(manifold.normal, Vec2)
    assert manifold.normal.length == pytest.approx(1.0, abs=0.01)


def test_manifold_point_fields(touching):
    ground, ball = touching
    point = ball.shapes[0].contact_data[0].manifold.points[0]

    assert isinstance(point, ManifoldPoint)
    assert isinstance(point.anchor_a, Vec2)
    assert isinstance(point.anchor_b, Vec2)
    assert point.separation < 0.1, "a resting contact is barely separated"
    assert point.total_normal_impulse > 0.0, "it is holding the ball up"
    assert isinstance(point.persisted, bool)


def test_body_contact_data_builds_a_manifold(touching):
    ground, ball = touching
    assert ball.contact_data[0].manifold.points


# --- the Contact handle -----------------------------------------------------


def collect_first_contact(world):
    for _ in range(400):
        world.step(1 / 60, 4)
        events = world.get_contact_events()
        if events.begin:
            return events.begin[0].contact
    pytest.fail("no contact ever began")


def test_events_carry_a_contact(world):
    ground = world.add_body(position=(0, 0))
    ground.add_box(20, 1, enable_contact_events=True)
    ball = world.add_body(body_type="dynamic", position=(0, 4))
    ball.add_circle(radius=0.5, enable_contact_events=True)

    contact = collect_first_contact(world)
    assert isinstance(contact, Contact)
    assert contact.is_valid is True


def test_contact_exposes_its_data(world):
    ground = world.add_body(position=(0, 0))
    ground.add_box(20, 1, enable_contact_events=True)
    ball = world.add_body(body_type="dynamic", position=(0, 4))
    ball.add_circle(radius=0.5, enable_contact_events=True)

    contact = collect_first_contact(world)
    data = contact.data

    assert isinstance(data, ContactData)
    assert {data.shape_a, data.shape_b} == {ground.shapes[0], ball.shapes[0]}


def test_contact_identity_survives_across_steps(world):
    """The point of the handle: a begin can be matched to its end."""
    ground = world.add_body(position=(0, 0))
    ground.add_box(20, 1, enable_contact_events=True, restitution=0.7)
    ball = world.add_body(body_type="dynamic", position=(0, 5))
    ball.add_circle(radius=0.5, enable_contact_events=True, restitution=0.7)

    open_contacts = {}
    matched = 0
    for step in range(400):
        world.step(1 / 60, 4)
        events = world.get_contact_events()
        for touch in events.begin:
            open_contacts[touch.contact] = step
        for touch in events.end:
            if open_contacts.pop(touch.contact, None) is not None:
                matched += 1

    assert matched > 0, "a bouncing ball's ends should match its begins"


def test_contacts_are_usable_as_dictionary_keys(world):
    ground = world.add_body(position=(0, 0))
    ground.add_box(20, 1, enable_contact_events=True)
    ball = world.add_body(body_type="dynamic", position=(0, 4))
    ball.add_circle(radius=0.5, enable_contact_events=True)

    contact = collect_first_contact(world)
    same = Contact(contact._contact_id)

    assert contact == same
    assert hash(contact) == hash(same)
    assert len({contact, same}) == 1


def test_contact_repr_says_whether_it_is_live(world):
    ground = world.add_body(position=(0, 0))
    ground.add_box(20, 1, enable_contact_events=True)
    ball = world.add_body(body_type="dynamic", position=(0, 4))
    ball.add_circle(radius=0.5, enable_contact_events=True)

    contact = collect_first_contact(world)
    assert "valid" in repr(contact)


def test_a_stale_contact_reports_no_data(world):
    ground = world.add_body(position=(0, 0))
    ground.add_box(20, 1, enable_contact_events=True)
    ball = world.add_body(body_type="dynamic", position=(0, 4))
    ball.add_circle(radius=0.5, enable_contact_events=True)

    contact = collect_first_contact(world)
    ball.destroy()
    world.step(1 / 60, 4)

    assert contact.is_valid is False
    assert contact.data is None
