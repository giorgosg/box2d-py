"""A world reports the objects it makes and destroys.

World.object_created and World.object_destroyed are there to override. They
cover what only the binding sees: a body taking its shapes and joints down
with it, a chain its segments, a world everything in it.
"""

import gc

import pytest

from box2d import (
    Body,
    Chain,
    ChainSegment,
    Circle,
    DestroyedError,
    Polygon,
    RevoluteJoint,
    World,
)


class Recorder(World):
    """A world that writes down every report, in order."""

    def __init__(self, *args, **kwargs):
        self.log = []
        super().__init__(*args, **kwargs)

    def object_created(self, obj):
        self.log.append(("created", obj))

    def object_destroyed(self, obj, cause):
        self.log.append(("destroyed", obj, cause))


@pytest.fixture
def world():
    world = Recorder()
    yield world
    world.destroy()


def kinds(log):
    """The log with each object replaced by its class, for comparing order."""
    return [(entry[0], type(entry[1])) + entry[2:] for entry in log]


# -- created -------------------------------------------------------------------


def test_a_body_and_its_shapes_are_reported_in_the_order_made(world):
    body = world.new_body().dynamic().circle(radius=0.5).box(1, 1).build()
    circle, box = body.shapes
    assert world.log == [
        ("created", body),
        ("created", circle),
        ("created", box),
    ]


def test_a_chain_is_reported_before_its_segments(world):
    body = world.add_body()
    world.log.clear()
    chain = body.add_chain([(0, 0), (1, 0), (2, 1), (3, 1)])
    assert world.log == [("created", chain)] + [
        ("created", segment) for segment in chain.segments
    ]


def test_a_joint_is_reported_once_it_exists(world):
    a = world.add_body(body_type="dynamic")
    b = world.add_body(body_type="dynamic", position=(1, 0))
    world.log.clear()
    seen = []
    world.object_created = lambda obj: seen.append(obj.body_b)
    joint = world.add_revolute_joint(a, b, anchor=(0.5, 0))
    assert isinstance(joint, RevoluteJoint)
    # Fully usable when reported: it already knows its bodies.
    assert seen == [b]


def test_a_mouse_joint_reports_its_proxy_body_first(world):
    body = world.add_body(body_type="dynamic")
    world.log.clear()
    joint = world.add_mouse_joint(body, (1, 1))
    assert world.log == [("created", joint.body_a), ("created", joint)]


def test_an_object_is_reported_as_its_mapped_class():
    class Ball(Body):
        pass

    world = Recorder(classes={Body: Ball})
    try:
        body = world.add_body()
        assert world.log == [("created", body)] and type(body) is Ball
    finally:
        world.destroy()


def test_an_object_is_fully_made_before_it_is_reported():
    class Crate(Body):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.label = "crate"

    labels = []

    class Game(World):
        def object_created(self, obj):
            labels.append(obj.label)

    world = Game(classes={Body: Crate})
    try:
        world.add_body()
        assert labels == ["crate"]
    finally:
        world.destroy()


def test_an_error_in_object_created_reaches_the_caller_and_the_object_stays(world):
    def fail(obj):
        raise KeyError("no")

    world.object_created = fail
    with pytest.raises(KeyError):
        world.add_body()
    del world.object_created
    (body,) = world.bodies
    assert body.is_valid


# -- destroyed -----------------------------------------------------------------


def test_a_body_reports_its_joints_then_shapes_then_itself(world):
    body = world.add_body(body_type="dynamic")
    circle = body.add_circle(radius=0.5)
    other = world.add_body(body_type="dynamic", position=(2, 0))
    joint = world.add_distance_joint(body, other)
    world.log.clear()

    body.destroy()

    assert world.log == [
        ("destroyed", joint, body),
        ("destroyed", circle, body),
        ("destroyed", body, body),
    ]


def test_a_destroyed_object_can_still_be_read_when_reported(world):
    body = world.add_body(body_type="dynamic", position=(3, 4))
    body.add_circle(radius=0.5)
    read = []

    def note(obj, cause):
        read.append(obj.body.position if isinstance(obj, Circle) else obj.position)

    world.object_destroyed = note
    body.destroy()
    assert read == [(3, 4), (3, 4)]
    with pytest.raises(DestroyedError):
        body.position


def test_a_chain_reports_its_segments_then_itself(world):
    body = world.add_body()
    chain = body.add_chain([(0, 0), (1, 0), (2, 1), (3, 1)])
    world.log.clear()

    chain.destroy()

    assert world.log == [
        ("destroyed", segment, chain) for segment in chain.segments
    ] + [("destroyed", chain, chain)]


def test_a_body_reports_its_chains_segments_first(world):
    body = world.add_body()
    chain = body.add_chain([(0, 0), (1, 0), (2, 1), (3, 1)])
    world.log.clear()

    body.destroy()

    assert kinds(world.log) == [
        ("destroyed", ChainSegment, body) for _ in chain.segments
    ] + [("destroyed", Chain, body), ("destroyed", Body, body)]


def test_a_shape_and_a_joint_report_only_themselves(world):
    a = world.add_body(body_type="dynamic")
    b = world.add_body(body_type="dynamic", position=(1, 0))
    shape = a.add_box(1, 1)
    joint = world.add_weld_joint(a, b)
    world.log.clear()

    shape.destroy()
    joint.destroy()

    assert world.log == [("destroyed", shape, shape), ("destroyed", joint, joint)]


def test_a_mouse_joint_takes_its_proxy_body_with_it(world):
    body = world.add_body(body_type="dynamic")
    joint = world.add_mouse_joint(body, (1, 1))
    proxy = joint.body_a
    world.log.clear()

    joint.destroy()

    assert world.log == [("destroyed", joint, joint), ("destroyed", proxy, joint)]
    assert not proxy.is_valid


def test_destroying_a_dragged_body_reports_the_drag_too(world):
    body = world.add_body(body_type="dynamic")
    joint = world.add_mouse_joint(body, (1, 1))
    proxy = joint.body_a
    world.log.clear()

    body.destroy()

    assert world.log == [
        ("destroyed", joint, body),
        ("destroyed", proxy, body),
        ("destroyed", body, body),
    ]
    assert not proxy.is_valid
    assert world.bodies == []


def test_destroying_twice_reports_once(world):
    body = world.add_body()
    body.destroy()
    body.destroy()
    assert kinds(world.log) == [("created", Body), ("destroyed", Body, body)]


def test_the_world_reports_everything_with_itself_as_cause():
    world = Recorder()
    a = world.add_body(body_type="dynamic")
    circle = a.add_circle(radius=1)
    b = world.add_body(body_type="dynamic", position=(1, 0))
    joint = world.add_revolute_joint(a, b, anchor=(0.5, 0))
    world.log.clear()

    world.destroy()

    assert world.log == [
        ("destroyed", joint, world),
        ("destroyed", circle, world),
        ("destroyed", a, world),
        ("destroyed", b, world),
    ]


def test_a_world_collected_unreferenced_reports_nothing():
    log = []

    class Quiet(World):
        def object_destroyed(self, obj, cause):
            log.append(obj)

    world = Quiet()
    world.add_body()
    del world
    gc.collect()
    assert log == []


def test_a_refused_destroy_reports_nothing(world):
    body = world.add_body(body_type="dynamic")
    body.add_polygon([(0, 0), (1, 0), (0, 1)], enable_pre_solve_events=True)
    ground = world.add_body(position=(0, -0.5))
    ground.add_box(10, 1, enable_pre_solve_events=True)
    attempts = []

    def destroy_mid_step(shape_a, shape_b, manifold):
        try:
            shape_a.body.destroy()
        except RuntimeError:
            attempts.append("refused")

    world.pre_solve = destroy_mid_step
    world.log.clear()
    for _ in range(10):
        world.step(1 / 60, 4)

    assert attempts and set(attempts) == {"refused"}
    assert world.log == []


def test_an_error_in_object_destroyed_comes_after_the_destroy_completes(world):
    body = world.add_body(body_type="dynamic")
    shape = body.add_circle(radius=1)
    reported = []

    def fail(obj, cause):
        reported.append(obj)
        raise ValueError(f"cannot let {type(obj).__name__} go")

    world.object_destroyed = fail
    with pytest.raises(ValueError, match="Circle"):
        body.destroy()

    # Every object was still reported, and every one of them is gone.
    assert reported == [shape, body]
    assert not body.is_valid and not shape.is_valid
    assert world.bodies == []


def test_hooks_are_methods_of_world_that_do_nothing():
    world = World()
    try:
        assert world.object_created(world) is None
        assert world.object_destroyed(world, world) is None
    finally:
        world.destroy()


def test_shapes_bodies_and_joints_are_all_reported_as_their_kind(world):
    a = world.add_body(body_type="dynamic")
    a.add_polygon([(0, 0), (1, 0), (0, 1)])
    b = world.add_body(body_type="dynamic", position=(1, 0))
    world.add_revolute_joint(a, b, anchor=(0.5, 0))
    world.log.clear()

    a.destroy()

    assert kinds(world.log) == [
        ("destroyed", RevoluteJoint, a),
        ("destroyed", Polygon, a),
        ("destroyed", Body, a),
    ]


# -- what a report may do --------------------------------------------------------


def test_destroying_again_from_a_report_is_a_no_op(world):
    body = world.add_body(body_type="dynamic")
    body.add_circle(radius=1)
    seen = []

    def again(obj, cause):
        seen.append(obj)
        cause.destroy()
        obj.destroy()

    world.object_destroyed = again
    body.destroy()

    assert len(seen) == 2 and not body.is_valid
    assert world.bodies == []


def test_a_report_destroying_the_world_cannot_reach_the_next_one():
    made = []

    class Restarting(World):
        def object_destroyed(self, obj, cause):
            if cause is self and not made:
                self.destroy()
                made.append(World())

    world = Restarting()
    world.add_body()
    world.destroy()

    (next_world,) = made
    try:
        # It took the freed slot, and the outer destroy must have left it be.
        assert next_world.is_valid
        next_world.step(1 / 60, 4)
    finally:
        next_world.destroy()


def test_a_report_cannot_add_to_a_body_that_is_going(world):
    body = world.add_body(body_type="dynamic")

    def add_more(obj, cause):
        obj.add_circle(radius=1)

    world.object_destroyed = add_more
    with pytest.raises(RuntimeError, match="being destroyed"):
        body.destroy()
    assert not body.is_valid and world.bodies == []


def test_a_mouse_joint_whose_proxy_report_raises_is_still_whole(world):
    body = world.add_body(body_type="dynamic")
    reported = []

    def fail_on_proxy(obj):
        reported.append(obj)
        if isinstance(obj, Body) and obj is not body:
            raise KeyError("proxy")

    world.object_created = fail_on_proxy
    with pytest.raises(KeyError):
        world.add_mouse_joint(body, (1, 1))

    # Both were made and reported; nothing was left behind without the other.
    proxy, joint = reported
    assert joint.body_a is proxy and len(world.bodies) == 2
    del world.object_created
    joint.destroy()
    assert world.bodies == [body]


def test_a_chain_whose_report_raises_still_reports_every_segment(world):
    body = world.add_body()
    reported = []

    def fail_on_chain(obj):
        reported.append(obj)
        if isinstance(obj, Chain):
            raise KeyError("chain")

    world.object_created = fail_on_chain
    with pytest.raises(KeyError):
        body.add_chain([(0, 0), (1, 0), (2, 1), (3, 1)])
    (chain,) = body.chains
    assert reported == [chain, *chain.segments]


def test_objects_made_directly_are_reported_neither_made_nor_destroyed(world):
    from box2d.dataclasses import BodyDef

    body = Body(world, BodyDef())
    circle = Circle.create(body, 1.0)
    assert world.log == []
    assert world.bodies == [body] and body.shapes == [circle]

    body.destroy()
    assert world.log == []
