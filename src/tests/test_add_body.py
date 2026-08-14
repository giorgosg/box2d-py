# tests/test_add_body.py
"""World.add_body creates a body in one call, and the builder is sugar over it.

Bodies were the only entity without a direct ``world.add_*`` method: joints had
``world.add_revolute_joint``, shapes had ``body.add_box``, but a body required
the 394-line BodyBuilder. BodyBuilder now accumulates keyword arguments and
builds through add_body, so both paths share one creation point.
"""

import math

import pytest

from box2d import World, Vec2, BodyType
from box2d.dataclasses import BodyDef


@pytest.fixture
def world():
    world = World()
    yield world
    world.destroy()


# --- add_body itself --------------------------------------------------------


def test_add_body_defaults_to_static(world):
    assert world.add_body().type == "static"


@pytest.mark.parametrize("name", ["static", "kinematic", "dynamic"])
def test_body_type_by_name(world, name):
    assert world.add_body(body_type=name).type == name


@pytest.mark.parametrize(
    "enum_value,name",
    [
        (BodyType.STATIC, "static"),
        (BodyType.KINEMATIC, "kinematic"),
        (BodyType.DYNAMIC, "dynamic"),
    ],
)
def test_body_type_by_enum(world, enum_value, name):
    assert world.add_body(body_type=enum_value).type == name


def test_invalid_body_type_names_the_valid_ones(world):
    with pytest.raises(ValueError, match="Invalid body type"):
        world.add_body(body_type="bouncy")


def test_properties_round_trip(world):
    body = world.add_body(
        body_type="dynamic",
        position=(2, 3),
        rotation=math.pi / 4,
        linear_velocity=(1, -1),
        angular_velocity=0.5,
        gravity_scale=0.25,
        sleep_threshold=0.1,
        is_bullet=True,
    )
    assert body.position == (2, 3)
    assert body.rotation == pytest.approx(math.pi / 4)
    assert body.linear_velocity == (1, -1)
    assert body.angular_velocity == pytest.approx(0.5)
    assert body.gravity_scale == pytest.approx(0.25)
    assert body.sleep_threshold == pytest.approx(0.1)
    assert body.is_bullet is True


def test_omitted_arguments_keep_box2d_defaults(world):
    """Every parameter defaults to None, meaning 'leave Box2D's default alone'."""
    explicit = world.add_body(body_type="dynamic")
    reference = world.add_body(body_type="dynamic", gravity_scale=1.0)
    assert explicit.gravity_scale == reference.gravity_scale
    assert explicit.position == (0, 0)


def test_body_has_no_shapes_until_added(world):
    body = world.add_body(body_type="dynamic")
    assert body.shapes == []
    body.add_circle(radius=1.0)
    assert len(body.shapes) == 1


def test_body_is_tracked_by_the_world(world):
    body = world.add_body()
    assert body in world.bodies


def test_add_body_simulates(world):
    ground = world.add_body(position=(0, -5))
    ground.add_box(20, 1)
    ball = world.add_body(body_type="dynamic", position=(0, 5))
    ball.add_circle(radius=0.5)

    for _ in range(180):
        world.step(1 / 60, 4)

    assert ball.position.y == pytest.approx(-4.0, abs=0.1)


# --- user_data, which used to be unreachable --------------------------------


def test_user_data_survives_creation(world):
    """Body.__init__ used to overwrite user_data with its own cdata handle."""
    payload = {"tag": "player"}
    body = world.add_body(user_data=payload)
    assert body.user_data is payload


def test_user_data_defaults_to_none(world):
    assert world.add_body().user_data is None


def test_body_def_is_not_mutated(world):
    """A definition must be reusable; creation used to clobber its user_data."""
    from box2d.body import Body

    body_def = BodyDef(user_data="mine")
    first = Body(world, body_def)
    second = Body(world, body_def)

    assert body_def.user_data == "mine"
    assert first.user_data == "mine"
    assert second.user_data == "mine"
    assert first is not second


# --- the builder is now a shim ----------------------------------------------


def test_builder_routes_through_add_body(world, monkeypatch):
    seen = {}
    original = World.add_body

    def spy(self, **kwargs):
        seen.update(kwargs)
        return original(self, **kwargs)

    monkeypatch.setattr(World, "add_body", spy)
    world.new_body().dynamic().position(2, 3).gravity_scale(0.5).build()

    assert seen["body_type"] == "dynamic"
    assert seen["position"] == Vec2(2, 3)
    assert seen["gravity_scale"] == 0.5


def test_builder_holds_no_body_state(world):
    """The builder keeps keyword arguments, not a definition of its own."""
    builder = world.new_body().dynamic()
    assert not hasattr(builder, "_def")
    assert builder._body_args == {"body_type": "dynamic"}


def test_builder_and_add_body_agree(world):
    built = world.new_body().dynamic().position(1, 2).gravity_scale(0.5).build()
    direct = world.add_body(body_type="dynamic", position=(1, 2), gravity_scale=0.5)

    assert built.type == direct.type
    assert built.position == direct.position
    assert built.gravity_scale == direct.gravity_scale


def test_builder_reuse_produces_independent_bodies(world):
    builder = world.new_body().dynamic().box(0.5, 0.5)
    first = builder.position(1, 1).build()
    second = builder.position(2, 2).build()

    assert first is not second
    assert first.position == (1, 1)
    assert second.position == (2, 2)
    assert len(first.shapes) == 1 and len(second.shapes) == 1


def test_builder_rotation_is_not_double_wrapped(world):
    """The builder passes radians; add_body is what turns them into a Rot."""
    body = world.new_body().dynamic().rotation(math.pi / 4).build()
    assert body.rotation == pytest.approx(math.pi / 4)


# --- Body.type, which was broken in both directions --------------------------


def test_body_type_is_readable_and_writable(world):
    """`body.type = x` raised AttributeError; `body.set_type = x` raised NameError."""
    body = world.add_body(body_type="dynamic")
    assert body.type == "dynamic"

    body.type = "static"
    assert body.type == "static"


def test_body_type_accepts_enum(world):
    body = world.add_body()
    body.type = BodyType.KINEMATIC
    assert body.type == "kinematic"


def test_body_type_rejects_unknown_name(world):
    body = world.add_body()
    with pytest.raises(ValueError, match="Invalid body type"):
        body.type = "bouncy"


def test_stray_set_type_property_is_gone(world):
    """@type.setter was applied to a function named set_type, creating a second property."""
    assert not hasattr(world.add_body(), "set_type")


def test_add_body_and_type_setter_share_one_resolver(world):
    """Both paths must accept the same spellings and reject the same ones."""
    from box2d.body import Body

    assert Body.resolve_type("dynamic") == Body.resolve_type(BodyType.DYNAMIC)
    with pytest.raises(ValueError, match="Invalid body type"):
        Body.resolve_type("bouncy")


def test_builder_accumulates_shapes_across_builds(world):
    """A builder keeps the shapes configured on it, so reuse stacks them.

    This is easy to walk into when building many differently-shaped bodies from
    one builder: the second body silently gets the first body's shape too. Use a
    fresh builder, or world.add_body plus body.add_*, when the shapes differ.
    """
    builder = world.new_body().dynamic()

    first = builder.polygon([(0, 0), (1, 0), (1, 1)]).build()
    second = builder.polygon([(2, 0), (3, 0), (3, 1)]).build()

    assert len(first.shapes) == 1
    assert len(second.shapes) == 2, "documented behaviour: the builder accumulates"


def test_add_body_does_not_accumulate(world):
    """The direct API has no such trap, since the body owns its shapes."""
    first = world.add_body(body_type="dynamic")
    first.add_polygon(vertices=[(0, 0), (1, 0), (1, 1)])
    second = world.add_body(body_type="dynamic")
    second.add_polygon(vertices=[(2, 0), (3, 0), (3, 1)])

    assert len(first.shapes) == 1
    assert len(second.shapes) == 1
