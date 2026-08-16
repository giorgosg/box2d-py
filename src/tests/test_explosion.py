# tests/test_explosion.py
"""World.explode applies a radial impulse.

b2World_Explode was never bound, so there was no way to push everything away
from a point -- the one primitive every game with a grenade in it needs.
"""

import math

import pytest

from box2d import World


@pytest.fixture
def world():
    world = World()
    world.gravity = (0, 0)  # so only the blast moves anything
    yield world
    world.destroy()


def ring(world, count=8, radius=3.0):
    """Bodies evenly spaced on a circle around the origin."""
    bodies = []
    for i in range(count):
        angle = 2 * math.pi * i / count
        body = world.add_body(
            body_type="dynamic",
            position=(radius * math.cos(angle), radius * math.sin(angle)),
        )
        body.add_circle(radius=0.3)
        bodies.append(body)
    return bodies


def settle(world, steps=30):
    for _ in range(steps):
        world.step(1 / 60, 4)


def test_explosion_pushes_bodies_outward(world):
    bodies = ring(world)
    before = [body.position.length for body in bodies]

    world.explode((0, 0), radius=6.0, impulse_per_length=20.0)
    settle(world)

    after = [body.position.length for body in bodies]
    assert all(a > b for a, b in zip(after, before)), "every body should be pushed out"


def test_explosion_is_radially_even(world):
    """A symmetric ring should stay symmetric."""
    bodies = ring(world)
    world.explode((0, 0), radius=6.0, impulse_per_length=20.0)
    settle(world)

    distances = [body.position.length for body in bodies]
    assert max(distances) - min(distances) < 0.5


def test_negative_impulse_implodes(world):
    body = world.add_body(body_type="dynamic", position=(3, 0))
    body.add_circle(radius=0.3)

    world.explode((0, 0), radius=6.0, impulse_per_length=-20.0)
    settle(world)

    assert body.position.x < 3.0, "a negative impulse should pull inward"


def test_bodies_beyond_the_radius_are_untouched(world):
    # On different axes, so the blasted body cannot fly into the far one.
    near = world.add_body(body_type="dynamic", position=(2, 0))
    near.add_circle(radius=0.3)
    far = world.add_body(body_type="dynamic", position=(0, 20))
    far.add_circle(radius=0.3)

    world.explode((0, 0), radius=5.0, impulse_per_length=50.0)
    settle(world)

    assert near.position.x > 2.0
    assert far.position.y == pytest.approx(20.0)


def test_static_bodies_are_unaffected(world):
    wall = world.add_body(position=(3, 0))
    wall.add_box(1, 10)

    world.explode((0, 0), radius=10.0, impulse_per_length=100.0)
    settle(world)

    assert wall.position == (3, 0)


def test_explosion_position_is_vector_like(world):
    """It takes a point, so it takes any of the usual spellings."""
    from box2d import Vec2

    for position in ((1, 0), [1, 0], Vec2(1, 0)):
        body = world.add_body(body_type="dynamic", position=(2, 0))
        body.add_circle(radius=0.3)
        world.explode(position, radius=5.0, impulse_per_length=10.0)
        world.step(1 / 60, 4)
        body.destroy()


def test_falloff_softens_the_edge(world):
    """With a long falloff, a body just outside the radius still moves."""
    outside = world.add_body(body_type="dynamic", position=(6, 0))
    outside.add_circle(radius=0.3)

    world.explode((0, 0), radius=5.0, falloff=4.0, impulse_per_length=50.0)
    settle(world)

    assert outside.position.x > 6.0


def test_mask_limits_what_is_affected(world):
    from box2d import CollisionFilter

    shielded = world.add_body(body_type="dynamic", position=(2, 0))
    shielded.add_circle(radius=0.3, filter=CollisionFilter(category=0x0002))
    exposed = world.add_body(body_type="dynamic", position=(0, 2))
    exposed.add_circle(radius=0.3, filter=CollisionFilter(category=0x0004))

    # Only category 0x0004 is in the mask.
    world.explode((0, 0), radius=6.0, impulse_per_length=40.0, mask=0x0004)
    settle(world)

    assert exposed.position.y > 2.0, "the exposed body should be thrown"
    assert shielded.position.x == pytest.approx(2.0), "the masked-out body should not"
