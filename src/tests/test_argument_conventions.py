# tests/test_argument_conventions.py
"""Anywhere box2d-py takes a point, it accepts the same forms.

That means any vector-like -- tuple, list, Vec2, b2Vec2 -- or the two
components as separate scalars. BodyBuilder.position and .linear_velocity used
to be the sole exceptions, taking two scalars and rejecting everything else,
which is what made the README's own example raise TypeError.
"""

import pytest

from box2d import World, Vec2
from box2d.math import to_vec2


VECTOR_LIKE = [
    pytest.param((1.0, 2.0), id="tuple"),
    pytest.param([1.0, 2.0], id="list"),
    pytest.param(Vec2(1.0, 2.0), id="Vec2"),
]


@pytest.fixture
def world():
    world = World()
    yield world
    world.destroy()


# --- Vec2 and to_vec2 accept the same forms ---------------------------------


@pytest.mark.parametrize("point", VECTOR_LIKE)
def test_vec2_accepts_vector_like(point):
    assert Vec2(point) == (1.0, 2.0)


@pytest.mark.parametrize("point", VECTOR_LIKE)
def test_to_vec2_accepts_vector_like(point):
    assert to_vec2(point) == (1.0, 2.0)


def test_vec2_accepts_two_scalars():
    assert Vec2(1.0, 2.0) == (1.0, 2.0)


def test_to_vec2_accepts_two_scalars():
    assert to_vec2(1.0, 2.0) == (1.0, 2.0)


def test_vec2_from_b2vec2_round_trips():
    assert Vec2(Vec2(1.0, 2.0).b2Vec2) == (1.0, 2.0)


# --- the builder, which used to be the outlier ------------------------------


@pytest.mark.parametrize("point", VECTOR_LIKE)
def test_builder_position_accepts_vector_like(world, point):
    body = world.new_body().dynamic().position(point).build()
    assert body.position == (1.0, 2.0)


def test_builder_position_accepts_two_scalars(world):
    body = world.new_body().dynamic().position(1.0, 2.0).build()
    assert body.position == (1.0, 2.0)


@pytest.mark.parametrize("point", VECTOR_LIKE)
def test_builder_linear_velocity_accepts_vector_like(world, point):
    body = world.new_body().dynamic().linear_velocity(point).build()
    assert body.linear_velocity == (1.0, 2.0)


def test_builder_linear_velocity_accepts_two_scalars(world):
    body = world.new_body().dynamic().linear_velocity(1.0, 2.0).build()
    assert body.linear_velocity == (1.0, 2.0)


# --- the rest of the point-taking surface -----------------------------------


@pytest.mark.parametrize("point", VECTOR_LIKE)
def test_body_position_setter(world, point):
    body = world.new_body().dynamic().build()
    body.position = point
    assert body.position == (1.0, 2.0)


@pytest.mark.parametrize("point", VECTOR_LIKE)
def test_body_point_conversions(world, point):
    body = world.new_body().dynamic().position(0, 0).build()
    assert body.get_local_point(point) == (1.0, 2.0)
    assert body.get_world_point(point) == (1.0, 2.0)


@pytest.mark.parametrize("point", VECTOR_LIKE)
def test_shape_offsets(world, point):
    body = world.new_body().dynamic().build()
    assert body.add_circle(radius=1.0, center=point) is not None
    assert body.add_box(1, 1, offset=point) is not None


@pytest.mark.parametrize("point", VECTOR_LIKE)
def test_world_queries(world, point):
    body = world.new_body().dynamic().position(1, 2).build()
    body.add_circle(radius=1.0)
    world.step(1 / 60, 4)
    assert isinstance(world.query_circle(point, 2.0), list)
    assert isinstance(world.ray_cast(point, (5.0, 5.0)), list)


@pytest.mark.parametrize("point", VECTOR_LIKE)
def test_world_gravity(point):
    world = World(gravity=point)
    try:
        assert world.gravity == (1.0, 2.0)
    finally:
        world.destroy()


# --- bad input fails clearly, not with a half-built object ------------------


def test_wrong_length_is_rejected():
    with pytest.raises(ValueError, match="exactly 2 elements"):
        Vec2((1, 2, 3))
    with pytest.raises(ValueError, match="exactly 2 elements"):
        to_vec2((1, 2, 3))


def test_non_vector_is_rejected():
    """A bare scalar used to build a Vec2 with no components at all."""
    with pytest.raises(TypeError):
        Vec2(5)
    with pytest.raises(TypeError):
        to_vec2(None)


def test_builder_rejects_bare_scalar(world):
    with pytest.raises(TypeError):
        world.new_body().position(5)
