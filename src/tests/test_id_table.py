# tests/test_id_table.py
"""Box2D ids lead back to their Python objects through tables on the world.

Box2D reports bodies, shapes and joints by id -- in a ray cast, an event, a
callback, ``body.joints`` -- and each has to come back as the very object the
caller made, not a copy. Each world keeps a table per kind, keyed by id, for
that. These tests hold every such path to returning the same object, every
way of destroying something to taking it out of its table, and the tables of
two worlds to staying apart.
"""

import gc

import pytest

from box2d import (
    AABB,
    DestroyedError,
    RevoluteJointDef,
    ShapeProxy,
    Vec2,
    World,
)
from box2d._checked import ffi, lib


def run(world, steps=60):
    for _ in range(steps):
        world.step(1 / 60, 4)


@pytest.fixture
def scene(world):
    """One of everything: each shape kind, a chain, joints of two kinds."""
    ground = world.add_body(position=(0, 0))
    floor = ground.add_box(40, 1, enable_contact_events=True, enable_hit_events=True)
    chain = ground.add_chain([(-20, 5), (-10, 5), (-10, 10)])

    ball = world.add_body(body_type="dynamic", position=(0, 3))
    circle = ball.add_circle(
        radius=0.5, enable_contact_events=True, enable_hit_events=True
    )
    box = world.add_body(body_type="dynamic", position=(3, 3))
    polygon = box.add_box(1, 1, enable_contact_events=True)
    stick = world.add_body(body_type="dynamic", position=(6, 3))
    capsule = stick.add_capsule((-0.5, 0), (0.5, 0), radius=0.25)
    segment = stick.add_segment((0, -0.5), (0, 0.5))

    hinge = world.add_revolute_joint(ground, stick, anchor=(6, 3))
    mouse = world.add_mouse_joint(box, target=(3, 3))
    return dict(
        ground=ground,
        floor=floor,
        chain=chain,
        ball=ball,
        circle=circle,
        box=box,
        polygon=polygon,
        stick=stick,
        capsule=capsule,
        segment=segment,
        hinge=hinge,
        mouse=mouse,
    )


def every_shape(scene):
    shapes = [
        scene[name] for name in ("floor", "circle", "polygon", "capsule", "segment")
    ]
    return shapes + list(scene["chain"].segments)


# --- every path returns the object that was made ----------------------------


def test_shape_body_and_world_are_the_objects_made(world, scene):
    for shape in every_shape(scene):
        assert shape.body is shape._body
        assert shape.world is world
    assert scene["circle"].body is scene["ball"]
    assert scene["chain"].world is world


def test_joint_bodies_and_body_joints_are_the_objects_made(world, scene):
    hinge, mouse = scene["hinge"], scene["mouse"]
    assert hinge.body_a is scene["ground"]
    assert hinge.body_b is scene["stick"]
    assert mouse.body_b is scene["box"]
    assert mouse.body_a is mouse._proxy
    assert scene["stick"].joints == [hinge]
    assert scene["stick"].joints[0] is hinge
    assert scene["box"].joints[0] is mouse


def test_queries_and_casts_return_the_shapes_made(world, scene):
    shapes = every_shape(scene)
    everywhere = AABB(lower=Vec2(-50, -50), upper=Vec2(50, 50))

    found = world.query_aabb(everywhere)
    assert {id(s) for s in found} == {id(s) for s in shapes}

    found = world.query_shape(ShapeProxy.box(100, 100))
    assert {id(s) for s in found} == {id(s) for s in shapes}

    assert world.query_circle((0, 3), 0.1)[0] is scene["circle"]

    hits = world.cast_ray((0, 10), (0, -20))
    assert [h.shape for h in hits][:2] == [scene["circle"], scene["floor"]]
    assert (
        world.cast_ray((0, 10), (0, -20), first_hit_only=True)[0].shape
        is (scene["circle"])
    )
    hits = world.cast_shape(ShapeProxy.circle(0.1, (3, 10)), (0, -20))
    assert hits[0].shape is scene["polygon"]

    # Standing on the floor, and up against the ball.
    planes = world.collide_mover((0.95, 1.0), (0.95, 2.8), 0.5)
    assert {id(p.shape) for p in planes} == {id(scene["floor"]), id(scene["circle"])}


def test_events_and_contacts_return_the_objects_made(world, scene):
    sensor_body = world.add_body(position=(0, 1.5))
    sensor = sensor_body.add_box(4, 1, is_sensor=True, enable_sensor_events=True)
    scene["circle"].enable_sensor_events = True
    scene["mouse"].destroy()  # let the box fall too

    begun, hits, sensed, moved = [], [], [], set()
    for _ in range(120):
        world.step(1 / 60, 4)
        events = world.get_contact_events()
        begun += events.begin
        hits += events.hit
        sensed += world.get_sensor_events().begin
        moved |= {id(e.body) for e in world.get_body_events()}

    pairs = [{id(e.shape_a), id(e.shape_b)} for e in begun]
    assert {id(scene["circle"]), id(scene["floor"])} in pairs
    assert any(
        e.shape_a is scene["circle"] or e.shape_b is scene["circle"] for e in hits
    )
    assert [(e.sensor, e.visitor) for e in sensed] == [(sensor, scene["circle"])]
    assert id(scene["ball"]) in moved

    touching = [e.contact for e in begun if e.contact.is_valid]
    data = touching[0].data
    assert {id(data.shape_a), id(data.shape_b)} in pairs

    contacts = scene["ball"].contact_data
    assert contacts and all(scene["circle"] in (c.shape_a, c.shape_b) for c in contacts)
    assert scene["floor"] in [
        c.shape_a if c.shape_b is scene["circle"] else c.shape_b
        for c in scene["circle"].contact_data
    ]


def test_sensor_overlaps_return_the_shapes_made(world):
    holder = world.add_body(position=(0, 0))
    sensor = holder.add_box(4, 4, is_sensor=True, enable_sensor_events=True)
    ball = world.add_body(body_type="dynamic", position=(0, 0), gravity_scale=0)
    circle = ball.add_circle(radius=0.5, enable_sensor_events=True)
    world.step(1 / 60, 4)
    assert sensor.sensor_overlaps == [circle]
    assert sensor.sensor_overlaps[0] is circle


def test_joint_events_return_the_joint_made(world):
    ground = world.add_body(position=(0, 0))
    ball = world.add_body(body_type="dynamic", position=(0, -1))
    ball.add_circle(radius=0.5)
    joint = world.add_joint(RevoluteJointDef(ground, ball, anchor=(0, 0)))
    joint.force_threshold = 0.001
    world.step(1 / 60, 4)
    assert [e.joint for e in world.get_joint_events()] == [joint]
    assert world.get_joint_events()[0].joint is joint


def test_callbacks_receive_the_shapes_made(world, scene):
    for shape in (scene["floor"], scene["circle"]):
        shape.enable_pre_solve_events = True
    world.add_body(body_type="dynamic", position=(0, 5)).add_circle(
        radius=0.5, enable_custom_filtering=True
    )
    filtered, solved = [], []
    world.custom_filter = lambda a, b: filtered.append((a, b)) or True
    world.pre_solve = lambda a, b, manifold: solved.append((a, b))
    run(world)
    shapes = set(map(id, every_shape(scene)))
    shapes |= {id(s) for b in world.bodies for s in b.shapes}
    assert filtered and all(id(a) in shapes and id(b) in shapes for a, b in filtered)
    assert {id(scene["circle"]), id(scene["floor"])} in [
        {id(a), id(b)} for a, b in solved
    ]


def test_wrappers_are_found_with_nothing_else_holding_them(world):
    """The table is what keeps a wrapper alive while Box2D has its object."""
    body = world.add_body(body_type="dynamic", position=(0, 0))
    body.add_circle(radius=0.5)
    del body
    gc.collect()
    [shape] = world.query_circle((0, 0), 0.1)
    assert shape.body is world.bodies[0]


# --- destroying takes things out of the tables ------------------------------


def table_sizes(world):
    return len(world._bodies), len(world._shapes), len(world._joints)


def test_explicit_destroys_leave_the_tables(world, scene):
    before = table_sizes(world)
    scene["circle"].destroy()
    scene["chain"].destroy()
    scene["hinge"].destroy()
    scene["mouse"].destroy()  # and its proxy body
    after = table_sizes(world)
    assert after == (before[0] - 1, before[1] - 1 - 2, before[2] - 2)

    everywhere = AABB(lower=Vec2(-50, -50), upper=Vec2(50, 50))
    found = world.query_aabb(everywhere)
    assert scene["circle"] not in found
    assert not set(map(id, scene["chain"].segments)) & set(map(id, found))
    assert scene["stick"].joints == []


def test_a_body_destroy_takes_its_shapes_chains_and_joints_out(world, scene):
    before = table_sizes(world)
    scene["ground"].destroy()  # floor, a 2-segment chain, the hinge
    assert table_sizes(world) == (before[0] - 1, before[1] - 3, before[2] - 1)
    scene["box"].destroy()  # its shape, the mouse joint and the joint's proxy
    assert table_sizes(world) == (before[0] - 3, before[1] - 4, before[2] - 2)


def test_create_and_destroy_cycles_do_not_grow_the_tables(world):
    ground = world.add_body(position=(0, 0))
    before = table_sizes(world)
    for _ in range(50):
        body = world.add_body(body_type="dynamic", position=(0, 2))
        body.add_circle(radius=0.5)
        body.add_chain([(0, 0), (1, 0), (2, 0)])
        world.add_revolute_joint(ground, body, anchor=(0, 2))
        world.add_mouse_joint(body, target=(0, 2))
        body.destroy()
    assert table_sizes(world) == before


def test_a_world_destroy_empties_its_tables(scene):
    world = scene["ground"].world
    world.destroy()
    assert table_sizes(world) == (0, 0, 0)


def test_events_naming_a_destroyed_object_report_none(world):
    ground = world.add_body(position=(0, 0))
    floor = ground.add_box(20, 1, enable_contact_events=True)
    ball = world.add_body(body_type="dynamic", position=(0, 0.9))
    ball.add_circle(radius=0.5, enable_contact_events=True)
    world.step(1 / 60, 4)
    assert world.get_contact_events().begin
    ball.destroy()
    world.step(1 / 60, 4)
    [end] = world.get_contact_events().end
    assert {end.shape_a, end.shape_b} == {floor, None}


# --- each world has its own tables ------------------------------------------


@pytest.fixture
def twins():
    """Two worlds built the same way, so their objects' ids coincide."""
    worlds = [World(), World()]
    made = []
    for world in worlds:
        ground = world.add_body(position=(0, 0))
        ground.add_box(20, 1)
        ball = world.add_body(body_type="dynamic", position=(0, 3))
        ball.add_circle(radius=0.5)
        joint = world.add_revolute_joint(ground, ball, anchor=(0, 3))
        made.append((world, ground, ball, joint))
    yield made
    for world in worlds:
        world.destroy()


def test_twin_worlds_share_ids_but_not_objects(twins):
    (world_a, ground_a, ball_a, joint_a), (world_b, ground_b, ball_b, joint_b) = twins
    id_a, id_b = ball_a.shapes[0]._shape_id, ball_b.shapes[0]._shape_id
    # The premise: only the world part of the ids tells them apart.
    assert (id_a.index1, id_a.generation) == (id_b.index1, id_b.generation)

    assert world_a._shapes.find(id_b) is None
    assert world_b._shapes.find(id_a) is None
    assert world_a._bodies.find(ball_b._body_id) is None
    assert world_a._joints.find(joint_b._joint_id) is None
    with pytest.raises(LookupError):
        world_a._shapes.require(id_b)

    assert world_b.query_circle((0, 3), 0.1) == [ball_b.shapes[0]]
    assert ball_b.shapes[0].body is ball_b
    assert ball_b.joints[0] is joint_b
    assert joint_b.body_a is ground_b


def test_a_joint_to_a_body_of_another_world_is_refused(twins):
    (world_a, ground_a, _, _), (_, _, ball_b, _) = twins
    with pytest.raises(ValueError, match="belong to this world"):
        world_a.add_revolute_joint(ground_a, ball_b, anchor=(0, 3))


# --- what is no longer in the table -----------------------------------------


def test_box2d_user_data_is_left_empty(world, scene):
    """Box2D's user data no longer carries anything of ours."""
    assert lib.b2World_GetUserData(world._world_id) == ffi.NULL
    for body in world.bodies:
        assert lib.b2Body_GetUserData(body._body_id) == ffi.NULL
    for shape in every_shape(scene):
        assert lib.b2Shape_GetUserData(shape._shape_id) == ffi.NULL
    for joint in (scene["hinge"], scene["mouse"]):
        assert lib.b2Joint_GetUserData(joint._joint_id) == ffi.NULL


def test_user_data_still_rides_on_the_objects(world):
    body = world.add_body(user_data="body", position=(0, 3), body_type="dynamic")
    body.add_circle(radius=0.5, user_data="shape")
    chain = body.add_chain([(5, 0), (6, 0), (7, 0)], user_data="chain")
    other = world.add_body(user_data="other")
    joint = world.add_revolute_joint(other, body, anchor=(0, 3))
    joint.user_data = "joint"
    world.user_data = "world"

    [found] = world.query_circle((0, 3), 0.1)
    assert found.user_data == "shape"
    assert found.body.user_data == "body"
    assert body.chains[0].user_data == "chain" and chain.user_data == "chain"
    assert body.joints[0].user_data == "joint"
    assert joint.body_a.user_data == "other"
    assert found.world.user_data == "world"


def test_a_missing_entry_raises_a_python_error(world, scene):
    """An id Box2D reports with no object behind it is a bug, and should say so
    -- not abort the interpreter, as following a dangling handle did."""
    circle = scene["circle"]
    world._shapes.remove(circle._shape_id)
    with pytest.raises(LookupError, match="shape"):
        world.query_circle((0, 3), 0.1)
    with pytest.raises(LookupError, match="shape"):
        world.cast_ray((0, 10), (0, -20))
    with pytest.raises(LookupError, match="shape"):
        world.cast_ray((0, 10), (0, -20), first_hit_only=True)

    hinge = scene["hinge"]
    world._bodies.remove(scene["stick"]._body_id)
    with pytest.raises(LookupError, match="body"):
        hinge.body_b
    world._joints.remove(hinge._joint_id)
    with pytest.raises(LookupError, match="joint"):
        scene["ground"].joints


def test_a_destroyed_object_raises_rather_than_looking_anything_up(world, scene):
    scene["circle"].destroy()
    with pytest.raises(DestroyedError):
        scene["circle"].body
    with pytest.raises(DestroyedError):
        scene["circle"].world
    scene["hinge"].destroy()
    with pytest.raises(DestroyedError):
        scene["hinge"].body_a
    scene["chain"].destroy()
    with pytest.raises(DestroyedError):
        scene["chain"].world


def test_a_contact_does_not_keep_its_world_alive():
    """A contact reads its shapes through its world's table, but holding one
    must not pin the world, and every object in it, for as long as it is kept."""
    import weakref

    world = World()
    ground = world.add_body(position=(0, 0))
    ground.add_box(20, 1, enable_contact_events=True)
    ball = world.add_body(body_type="dynamic", position=(0, 0.9))
    ball.add_circle(radius=0.5, enable_contact_events=True)
    world.step(1 / 60, 4)
    [begin] = world.get_contact_events().begin
    contact = begin.contact
    assert contact.data is not None

    gone = weakref.ref(world)
    del world, ground, ball, begin
    gc.collect()
    assert gone() is None
    assert contact.is_valid is False
    assert contact.data is None


# --- a missing entry never makes something undestroyable --------------------


def test_a_body_whose_joint_is_missing_can_still_be_destroyed(world, scene):
    """body.joints raises for a joint it cannot place, but destroying the body
    has to go ahead regardless, taking the joint with it."""
    stick, hinge = scene["stick"], scene["hinge"]
    world._joints.remove(hinge._joint_id)
    with pytest.raises(LookupError, match="joint"):
        stick.joints
    stick.destroy()
    assert not stick.is_valid
    assert not hinge.is_valid


# --- query callbacks hand their errors back ---------------------------------


#: cffi reports an exception raised in a callback as unraisable, and carries
#: on with a default answer. pytest turns that into this warning, which these
#: tests make an error.
_NOT_LEFT_TO_CFFI = pytest.mark.filterwarnings(
    "error::pytest.PytestUnraisableExceptionWarning"
)


@pytest.fixture
def failing_require(monkeypatch):
    """Make every strict shape lookup fail with something other than a
    LookupError, as a bug in the binding would."""

    def broken(self, object_id):
        raise RuntimeError("boom")

    monkeypatch.setattr(type(World()._shapes), "require", broken)


@pytest.mark.parametrize(
    "query",
    [
        lambda w: w.query_aabb(AABB(lower=Vec2(-1, 2), upper=Vec2(1, 4))),
        lambda w: w.query_circle((0, 3), 0.1),
        lambda w: w.query_shape(ShapeProxy.circle(0.1, (0, 3))),
        lambda w: w.cast_ray((0, 10), (0, -20)),
        lambda w: w.cast_shape(ShapeProxy.circle(0.1, (0, 10)), (0, -20)),
    ],
)
@_NOT_LEFT_TO_CFFI
def test_any_error_in_a_query_callback_is_raised_by_the_query(
    world, scene, failing_require, query
):
    with pytest.raises(RuntimeError, match="boom"):
        query(world)


@_NOT_LEFT_TO_CFFI
def test_the_callback_factories_collect_errors_without_a_list(world, scene):
    """Used on their own, without an errors list, the callbacks still stop the
    query rather than let cffi print and carry on with a default answer."""
    from box2d.world import make_overlap_callback

    results = []
    callback = make_overlap_callback(results, world=world)
    world._shapes.clear()  # Every shape is now missing.
    lib.b2World_OverlapAABB(
        world._world_id,
        Vec2(0, 0).b2Vec2[0],
        AABB(lower=Vec2(-50, -50), upper=Vec2(50, 50)).b2AABB[0],
        lib.b2DefaultQueryFilter(),
        callback,
        ffi.NULL,
    )
    assert results == []


# --- a mouse joint that cannot be made leaves nothing behind ----------------


def test_a_mouse_joint_that_fails_to_create_destroys_its_proxy(world, scene):
    from box2d import InvalidInputError

    bodies = list(world.bodies)
    with pytest.raises(InvalidInputError):
        world.add_mouse_joint(scene["ball"], target=(0, 3), hertz=float("nan"))
    assert world.bodies == bodies
    assert scene["ball"].joints == []
