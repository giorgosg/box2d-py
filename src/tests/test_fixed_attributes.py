# tests/test_fixed_attributes.py
"""Engine objects refuse attributes they do not define.

Setting a property under a wrong name used to add a plain attribute to the
Python object and change nothing in Box2D, silently. Two testbed controls were
broken that way -- ``joint.enable_motor`` for ``joint.motor_enabled`` among
them -- and nothing noticed, because nothing raised.
"""

import pytest

from box2d import World


@pytest.fixture
def world():
    world = World()
    yield world
    world.destroy()


@pytest.fixture
def objects(world):
    """One of each engine object a user holds."""
    ground = world.new_body().static().build()
    chain = ground.add_chain([(-5, 0), (0, 0), (5, 0)], loop=False)
    body = world.new_body().dynamic().position(0, 2).build()
    shape = body.add_circle(radius=0.5)
    joint = world.add_revolute_joint(ground, body, anchor=(0, 2))
    return {
        "world": world,
        "body": body,
        "shape": shape,
        "chain": chain,
        "joint": joint,
    }


KINDS = ["world", "body", "shape", "chain", "joint"]


@pytest.mark.parametrize("kind", KINDS)
def test_an_unknown_attribute_raises(objects, kind):
    with pytest.raises(AttributeError, match="no attribute 'tag'"):
        objects[kind].tag = "player"


@pytest.mark.parametrize("kind", KINDS)
def test_user_data_is_where_application_data_goes(objects, kind):
    obj = objects[kind]
    assert obj.user_data is None
    obj.user_data = {"tag": "player"}
    assert obj.user_data == {"tag": "player"}


@pytest.mark.parametrize(
    "kind, wrong, right",
    [
        # The two names that broke testbed controls.
        ("joint", "enable_motor", "motor_enabled"),
        ("joint", "spring_frequency_hertz", "spring_hertz"),
        # The tail of a longer name, and a plain misspelling.
        ("joint", "hertz", "spring_hertz"),
        ("body", "angular_dampening", "angular_damping"),
    ],
)
def test_the_error_names_the_property_that_was_meant(objects, kind, wrong, right):
    with pytest.raises(AttributeError, match=f"Did you mean '{right}'"):
        setattr(objects[kind], wrong, 1.0)


def test_real_properties_still_set(objects):
    objects["joint"].motor_enabled = True
    assert objects["joint"].motor_enabled is True
    objects["body"].angular_damping = 0.5
    assert objects["body"].angular_damping == pytest.approx(0.5)
    objects["shape"].friction = 0.25
    assert objects["shape"].friction == pytest.approx(0.25)


def test_a_rejected_name_is_left_unset(objects):
    joint = objects["joint"]
    with pytest.raises(AttributeError):
        joint.enable_motor = True
    assert "enable_motor" not in vars(joint)
    assert joint.motor_enabled is False


def test_a_subclass_of_yours_can_add_attributes(world):
    """Fixing attributes is for the library's own classes, not yours.

    The trade is that a subclass of yours gets no misspelling check either:
    it behaves like any other Python class.
    """

    class Game(World):
        def __init__(self):
            super().__init__()
            self.score = 0

    game = Game()
    game.score += 1
    assert game.score == 1
    game.destroy()

    with pytest.raises(AttributeError):
        world.score = 0
