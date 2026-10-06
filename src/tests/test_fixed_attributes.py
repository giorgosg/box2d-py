# tests/test_fixed_attributes.py
"""Engine objects refuse attributes they do not define.

Setting a property under a wrong name used to add a plain attribute to the
Python object and change nothing in Box2D, silently. Two testbed controls were
broken that way -- ``joint.motor_enabled`` for ``joint.enable_motor`` among
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
        # Names like the two that broke testbed controls.
        ("joint", "motor_enabled", "enable_motor"),
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
    objects["joint"].enable_motor = True
    assert objects["joint"].enable_motor is True
    objects["body"].angular_damping = 0.5
    assert objects["body"].angular_damping == pytest.approx(0.5)
    objects["shape"].friction = 0.25
    assert objects["shape"].friction == pytest.approx(0.25)


def test_a_rejected_name_is_left_unset(objects):
    joint = objects["joint"]
    with pytest.raises(AttributeError):
        joint.motor_enabled = True
    assert "motor_enabled" not in vars(joint)
    assert joint.enable_motor is False


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


@pytest.mark.parametrize(
    "kind, method",
    [
        ("world", "enable_sse2_fallback"),
        ("body", "wake_touching"),
        ("body", "destroy"),
        ("joint", "wake_bodies"),
    ],
)
def test_a_method_cannot_be_assigned_over(objects, kind, method):
    """``world.enable_sse2_fallback = True`` reads like a setting and would
    silently hide the method instead."""
    obj = objects[kind]
    with pytest.raises(AttributeError, match="is a method"):
        setattr(obj, method, True)
    assert method not in vars(obj)


@pytest.mark.parametrize(
    "kind, wrong, candidates",
    [
        ("body", "velocity", ["angular_velocity", "linear_velocity"]),
        ("joint", "limit", ["lower_limit", "upper_limit"]),
    ],
)
def test_every_plausible_name_is_offered(objects, kind, wrong, candidates):
    """With more than one fit, picking one would mislead as often as help."""
    with pytest.raises(AttributeError, match="Did you mean one of") as raised:
        setattr(objects[kind], wrong, 1.0)
    for name in candidates:
        assert repr(name) in str(raised.value)


def test_only_names_that_can_be_set_are_offered(world):
    """``spring_force`` reads the force right now; it is no help to someone
    setting the old ``spring_force_range``."""
    ground = world.add_body(position=(0, 0))
    body = world.add_body(body_type="dynamic", position=(0, -3))
    joint = world.add_distance_joint(ground, body, (0, 0), (0, 0), length=3.0)

    with pytest.raises(AttributeError) as raised:
        joint.spring_force_range = (-1.0, 1.0)
    message = str(raised.value)
    assert "'spring_force'" not in message
    assert "'lower_spring_force'" in message
    assert "'upper_spring_force'" in message


def test_a_one_letter_name_gets_no_guess(objects):
    """``body.x`` is not a misspelt ``lock_x``."""
    with pytest.raises(AttributeError) as raised:
        objects["body"].x = 1.0
    assert "Did you mean" not in str(raised.value)


def test_an_empty_name_raises_attribute_error(objects):
    with pytest.raises(AttributeError):
        setattr(objects["body"], "", 1)


# --- user_data at creation ----------------------------------------------------
# Box2D's own userData slot holds the handle that maps an id back to its Python
# object, so user_data given at creation is kept on the object instead. For
# shapes and chains it used to go into that slot: anything but a C pointer
# raised, and anything else was overwritten by the handle straight after.


@pytest.mark.parametrize(
    "add",
    [
        lambda body: body.add_circle(radius=0.5, user_data="tag"),
        lambda body: body.add_box(1, 1, user_data="tag"),
        lambda body: body.add_capsule((0, 0), (0, 1), 0.25, user_data="tag"),
        lambda body: body.add_segment((0, 0), (1, 0), user_data="tag"),
        lambda body: body.add_polygon([(0, 0), (1, 0), (0, 1)], user_data="tag"),
        lambda body: body.add_chain([(0, 0), (1, 0), (2, 0)], user_data="tag"),
    ],
    ids=["circle", "box", "capsule", "segment", "polygon", "chain"],
)
def test_user_data_given_at_creation_is_kept(world, add):
    body = world.new_body().dynamic().build()
    assert add(body).user_data == "tag"


def test_user_data_through_the_builder(world):
    body = world.new_body().dynamic().circle(0.5, user_data={"id": 7}).build()
    assert body.shapes[0].user_data == {"id": 7}
    # The shape still maps back to itself, so queries find the same object.
    found = world.query_circle((0, 0), 0.1)
    assert found[0] is body.shapes[0]
