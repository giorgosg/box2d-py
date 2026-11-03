"""The application chooses the classes a world makes.

A world's class map replaces a library class with a subclass of it wherever
that world makes one, so every object handed back -- by add_body, contact
events, queries, body.shapes -- is the application's own class, with no
user_data hop to reach its extras.
"""

import pytest

import box2d
from box2d import (
    Body,
    Box,
    Capsule,
    Chain,
    ChainSegment,
    Circle,
    MouseJoint,
    Polygon,
    RevoluteJoint,
    Segment,
    Shape,
    World,
    classes_with,
)


class Ball(Body):
    def hit(self):
        return "ouch"


class BallCircle(Circle):
    pass


@pytest.fixture
def ball_world():
    world = World(classes={Body: Ball, Circle: BallCircle})
    yield world
    world.destroy()


def test_add_body_makes_the_mapped_class(ball_world):
    body = ball_world.add_body(body_type="dynamic")
    assert type(body) is Ball
    assert body.hit() == "ouch"


def test_the_builder_makes_the_mapped_classes(ball_world):
    body = ball_world.new_body().dynamic().circle(radius=0.5).box(1, 1).build()
    assert type(body) is Ball
    circle, box = body.shapes
    assert type(circle) is BallCircle
    # Only the classes named are replaced.
    assert type(box) is Box


def test_objects_read_back_from_box2d_are_the_mapped_class(ball_world):
    ground = ball_world.add_body()
    ground.add_box(10, 1)
    ball = ball_world.add_body(body_type="dynamic", position=(0, 1))
    shape = ball.add_circle(radius=0.5, enable_contact_events=True)
    for _ in range(30):
        ball_world.step(1 / 60, 4)

    assert ball_world.bodies == [ground, ball]
    (found,) = ball_world.query_circle((0, 1), 0.1)
    assert found is shape
    assert type(found.body) is Ball


def test_a_world_subclass_names_its_classes():
    class Game(World):
        classes = {Body: Ball}

    world = Game()
    try:
        assert type(world.add_body()) is Ball
    finally:
        world.destroy()


def test_constructor_classes_add_to_the_subclass_ones():
    class Game(World):
        classes = {Body: Ball}

    world = Game(classes={Circle: BallCircle})
    try:
        body = world.add_body()
        assert type(body) is Ball
        assert type(body.add_circle(radius=1)) is BallCircle
    finally:
        world.destroy()


def test_class_for_answers_the_class_the_world_makes(ball_world):
    assert ball_world.class_for(Body) is Ball
    assert ball_world.class_for(Polygon) is Polygon


def test_every_shape_kind_is_mapped_separately():
    made = {}
    for base in (Box, Capsule, Circle, Polygon, Segment, Chain, ChainSegment):
        made[base] = type(f"My{base.__name__}", (base,), {})
    world = World(classes=made)
    try:
        body = world.add_body()
        assert type(body.add_box(1, 1)) is made[Box]
        assert type(body.add_capsule((0, 0), (1, 0), 0.2)) is made[Capsule]
        assert type(body.add_circle(radius=1)) is made[Circle]
        assert type(body.add_polygon([(0, 0), (1, 0), (0, 1)])) is made[Polygon]
        assert type(body.add_segment((0, 0), (1, 0))) is made[Segment]
        chain = body.add_chain([(0, 0), (1, 0), (2, 1), (3, 1)])
        assert type(chain) is made[Chain]
        # Box2D makes a chain's segments, and they come out mapped as well.
        assert {type(segment) for segment in chain.segments} == {made[ChainSegment]}
    finally:
        world.destroy()


def test_joints_are_mapped_by_kind():
    class Hinge(RevoluteJoint):
        pass

    world = World(classes={RevoluteJoint: Hinge})
    try:
        a = world.add_body(body_type="dynamic")
        b = world.add_body(body_type="dynamic", position=(1, 0))
        joint = world.add_revolute_joint(a, b, anchor=(0.5, 0))
        assert type(joint) is Hinge
        assert a.joints == [joint]
    finally:
        world.destroy()


def test_a_mouse_joint_proxy_is_an_ordinary_body_of_the_mapped_class(ball_world):
    body = ball_world.add_body(body_type="dynamic")
    joint = ball_world.add_mouse_joint(body, (1, 1))
    assert type(joint) is MouseJoint
    assert type(joint.body_a) is Ball


def test_a_subclass_keeps_its_own_attributes_and_init():
    class Crate(Body):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.label = "crate"

    world = World(classes={Body: Crate})
    try:
        assert world.add_body().label == "crate"
    finally:
        world.destroy()


@pytest.mark.parametrize(
    "classes, error",
    [
        ({Body: str}, TypeError),
        ({Body: BallCircle}, TypeError),
        # Box is a Polygon, but mapping Polygon must not be met with a Box.
        ({Polygon: Box}, TypeError),
        # Shape is not something a world makes; its kinds are.
        ({Shape: BallCircle}, ValueError),
        ({World: World}, ValueError),
        ({"Body": Ball}, ValueError),
    ],
)
def test_a_bad_class_map_fails_when_the_world_is_made(classes, error):
    with pytest.raises(error):
        World(classes=classes)


def test_classes_with_mixes_one_class_into_every_kind():
    class Extras:
        def extra(self):
            return type(self).__name__

    classes = classes_with(Extras, Shape)
    assert set(classes) == {Box, Capsule, Circle, Polygon, Segment, ChainSegment}
    for base, made in classes.items():
        assert issubclass(made, base) and issubclass(made, Extras)

    world = World(classes=classes)
    try:
        circle = world.add_body().add_circle(radius=1)
        assert circle.extra() == "ExtrasCircle"
    finally:
        world.destroy()


def test_classes_with_hands_back_the_same_classes_each_time():
    class Extras:
        pass

    assert classes_with(Extras, Body) == classes_with(Extras, Body)
    assert classes_with(Extras, Body)[Body] is classes_with(Extras, Body)[Body]


def test_classes_with_covers_bodies_chains_and_joints():
    class Extras:
        pass

    assert set(classes_with(Extras, Body)) == {Body}
    assert set(classes_with(Extras, Chain)) == {Chain}
    joints = classes_with(Extras, box2d.Joint)
    assert RevoluteJoint in joints and MouseJoint in joints
    assert box2d.Joint not in joints


def test_classes_with_refuses_what_a_world_never_makes():
    class Extras:
        pass

    with pytest.raises(ValueError):
        classes_with(Extras, World)


def test_a_world_shows_the_whole_map_it_uses():
    class Game(World):
        classes = {Body: Ball}

    world = Game(classes={Circle: BallCircle})
    try:
        assert dict(world.classes) == {Body: Ball, Circle: BallCircle}
        assert Game.classes == {Body: Ball}
        with pytest.raises(AttributeError):
            world.classes = {}
        with pytest.raises(TypeError):
            world.classes[Body] = Body
    finally:
        world.destroy()


def test_mapping_a_class_to_another_kind_says_which_to_map():
    with pytest.raises(TypeError, match="Box is made as Box: map Box"):
        World(classes={Polygon: Box})


def test_a_segment_class_that_fails_leaves_no_chain_behind():
    class Broken(ChainSegment):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            raise KeyError("broken")

    world = World(classes={ChainSegment: Broken})
    try:
        body = world.add_body()
        with pytest.raises(KeyError):
            body.add_chain([(0, 0), (1, 0), (2, 1), (3, 1)])
        assert body.chains == [] and world._shapes == {}
        body.destroy()
        assert world.bodies == []
    finally:
        world.destroy()
