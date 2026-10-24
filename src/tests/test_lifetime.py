# tests/test_lifetime.py
"""Using a destroyed Box2D object must raise, not segfault.

Box2D ids name engine-owned storage. Before these guards existed, touching a
body after its world was destroyed took the interpreter down with SIGSEGV
(exit code 139) -- no traceback, no exception, nothing to catch.
"""

import functools

import pytest
from box2d import World, DestroyedError


@pytest.fixture
def world():
    return World()


def test_body_after_world_destroy(world):
    body = world.new_body().dynamic().position(1, 2).build()
    world.destroy()

    with pytest.raises(DestroyedError):
        body.position


def test_shape_after_world_destroy(world):
    body = world.new_body().dynamic().build()
    shape = body.add_circle(radius=1.0)
    world.destroy()

    with pytest.raises(DestroyedError):
        shape.density


def test_shape_after_body_destroy(world):
    body = world.new_body().dynamic().build()
    shape = body.add_circle(radius=1.0)
    body.destroy()

    with pytest.raises(DestroyedError):
        shape.density


def test_body_after_own_destroy(world):
    body = world.new_body().dynamic().build()
    body.destroy()

    with pytest.raises(DestroyedError):
        body.position


def test_joint_after_bodies_destroyed(world):
    body_a = world.new_body().dynamic().position(0, 0).build()
    body_a.add_circle(radius=1.0)
    body_b = world.new_body().dynamic().position(1, 0).build()
    body_b.add_circle(radius=1.0)
    joint = world.add_revolute_joint(body_a, body_b, (0, 0), (0, 0))

    body_a.destroy()
    body_b.destroy()

    with pytest.raises(DestroyedError):
        joint.body_a


def _mouse_joint_gone_with_its_body(world):
    body = world.new_body().dynamic().circle(radius=1.0).build()
    joint = world.add_mouse_joint(body, (0, 0))
    body.destroy()
    return joint


def _mouse_joint_gone_with_its_body_then_destroyed(world):
    joint = _mouse_joint_gone_with_its_body(world)
    joint.destroy()  # what tidying up does; it removes the proxy body
    return joint


def _mouse_joint_destroyed(world):
    body = world.new_body().dynamic().circle(radius=1.0).build()
    joint = world.add_mouse_joint(body, (0, 0))
    joint.destroy()
    return joint


@pytest.mark.parametrize(
    "gone",
    [
        _mouse_joint_gone_with_its_body,
        _mouse_joint_gone_with_its_body_then_destroyed,
        _mouse_joint_destroyed,
    ],
)
def test_mouse_joint_target_after_the_joint_is_gone(world, gone):
    """The target lives on a proxy body rather than the joint, so it needs
    the same check as everything else on a joint: it used to return the
    position of a body nothing was joined to, or raise AttributeError once
    destroy() had dropped the proxy."""
    joint = gone(world)

    with pytest.raises(DestroyedError):
        joint.target
    with pytest.raises(DestroyedError):
        joint.target = (1, 1)


def test_world_step_after_destroy(world):
    world.destroy()

    with pytest.raises(DestroyedError):
        world.step(1 / 60, 4)


def test_destroy_is_idempotent(world):
    body = world.new_body().dynamic().build()

    body.destroy()
    body.destroy()  # must not raise

    world.destroy()
    world.destroy()  # must not raise


def test_is_valid_reports_destruction(world):
    body = world.new_body().dynamic().build()
    shape = body.add_circle(radius=1.0)

    assert world.is_valid is True
    assert body.is_valid is True
    assert shape.is_valid is True

    world.destroy()

    assert world.is_valid is False
    assert body.is_valid is False
    assert shape.is_valid is False


def test_live_objects_are_unaffected(world):
    """The guard must not disturb normal use."""
    body = world.new_body().dynamic().position(0, 10).build()
    body.add_circle(radius=0.5)

    for _ in range(10):
        world.step(1 / 60, 4)

    assert body.is_valid is True
    assert body.position.y < 10  # it fell


def test_destroying_one_body_leaves_others_usable(world):
    keep = world.new_body().dynamic().position(0, 0).build()
    drop = world.new_body().dynamic().position(5, 0).build()

    drop.destroy()

    assert keep.is_valid is True
    assert keep.position == (0, 0)
    world.step(1 / 60, 4)


def test_is_valid_is_a_property_everywhere():
    """Shape and Chain had it as a method while the rest had a property.

    Mixing the two up went unnoticed one way round: a method used as
    ``if shape.is_valid:`` is a bound method, always true.
    """
    from box2d import Body, Chain, Contact, Joint, Shape

    for cls in (World, Body, Shape, Chain, Joint, Contact):
        assert isinstance(cls.__dict__.get("is_valid"), property), cls.__name__


def test_a_world_made_after_one_is_destroyed_does_not_revive_its_objects():
    """Box2D names a body, shape, chain or joint by its world's slot, not by
    the world, and a world made after a destroy takes the freed slot. So the
    old ids named the new world's objects: an old body read a new body's
    position, and an old circle read a polygon as if it were one.
    """
    old = World()
    body = old.new_body().dynamic().position(1, 2).circle(0.5).build()
    shape = body.shapes[0]
    chain = old.new_body().static().chain([(0, 0), (1, 0), (2, 0)]).build().chains[0]
    segment = chain.segments[0]
    joint = old.add_distance_joint(body, old.new_body().static().build())
    old.destroy()

    new = World()
    try:
        # As much as the old world had, so every old id has a new namesake.
        new.new_body().dynamic().position(7, 7).box(1, 1).build()
        new.new_body().static().chain([(0, 5), (1, 5), (2, 5)]).build()
        anchor = new.new_body().static().build()
        new.add_distance_joint(new.bodies[0], anchor)

        for gone in (body, shape, chain, segment, joint):
            assert gone.is_valid is False, type(gone).__name__
        with pytest.raises(DestroyedError):
            body.position
        with pytest.raises(DestroyedError):
            shape.radius
        with pytest.raises(DestroyedError):
            segment.friction
        with pytest.raises(DestroyedError):
            chain.get_surface_material()
        with pytest.raises(DestroyedError):
            joint.rest_length
    finally:
        new.destroy()


def test_objects_destroyed_before_their_world_stay_gone_in_the_next():
    """Destroyed on their own, or taken down with a body, before the world
    went: World.destroy no longer holds them, so it cannot release them, and
    their ids would name the next world's objects in the same places."""
    old = World()
    body = old.new_body().dynamic().position(1, 2).circle(0.5).build()
    shape = body.shapes[0]
    holder = old.new_body().static().chain([(0, 0), (1, 0), (2, 0)]).build()
    chain = holder.chains[0]
    segment = chain.segments[0]
    anchor = old.new_body().static().build()
    joint = old.add_distance_joint(body, anchor)
    body.destroy()  # takes its shape and the joint with it
    chain.destroy()
    old.destroy()

    new = World()
    try:
        # Built the same way, so every old id has a new namesake.
        twin = new.new_body().dynamic().position(7, 7).circle(0.5).build()
        new_holder = new.new_body().static().chain([(0, 5), (1, 5), (2, 5)]).build()
        new_anchor = new.new_body().static().build()
        new_joint = new.add_distance_joint(twin, new_anchor)

        for gone in (body, shape, chain, segment, joint):
            assert gone.is_valid is False, type(gone).__name__
        with pytest.raises(DestroyedError):
            shape.radius
        with pytest.raises(DestroyedError):
            segment.friction
        with pytest.raises(DestroyedError):
            joint.rest_length

        # Destroying the dead again must not destroy their namesakes.
        for gone in (body, shape, chain, joint):
            gone.destroy()
        assert twin.is_valid and twin.shapes[0].is_valid
        assert new_holder.chains[0].is_valid and new_joint.is_valid
    finally:
        new.destroy()


def test_an_object_whose_world_is_destroyed_without_it_being_tracked_is_gone():
    """The sturdy check: each object knows its world, whichever path let go."""
    old = World()
    body = old.new_body().dynamic().position(1, 2).build()
    # As if the world had lost track of it.
    old._bodies.clear()
    old.destroy()

    new = World()
    try:
        new.new_body().dynamic().position(7, 7).build()
        assert body.is_valid is False
        with pytest.raises(DestroyedError):
            body.position
    finally:
        new.destroy()


# --- every object shares its world's liveness flag ---------------------------


def _two_bodies(world):
    a = world.new_body().dynamic().position(0, 0).circle(0.5).build()
    b = world.new_body().dynamic().position(1, 0).circle(0.5).build()
    return a, b


def _joint_between_two_bodies(kind, world):
    return getattr(world, f"add_{kind}_joint")(*_two_bodies(world))


#: One maker per kind of object with an id, each given a live world.
MAKERS = {
    "body-static": lambda w: w.new_body().static().build(),
    "body-kinematic": lambda w: w.new_body().kinematic().build(),
    "body-dynamic": lambda w: w.new_body().dynamic().build(),
    "shape-box": lambda w: w.new_body().build().add_box(1, 1),
    "shape-circle": lambda w: w.new_body().build().add_circle(0.5),
    "shape-capsule": lambda w: w.new_body().build().add_capsule((0, 0), (1, 0), 0.2),
    "shape-polygon": lambda w: (
        w.new_body().build().add_polygon([(0, 0), (1, 0), (0, 1)])
    ),
    "shape-segment": lambda w: w.new_body().build().add_segment((0, 0), (1, 0)),
    "chain": lambda w: w.new_body().build().add_chain([(0, 0), (1, 0), (2, 0)]),
    "chain-segment": lambda w: (
        w.new_body().build().add_chain([(0, 0), (1, 0), (2, 0)]).segments[0]
    ),
    "joint-mouse": lambda w: w.add_mouse_joint(_two_bodies(w)[0], (0, 0)),
    **{
        f"joint-{kind}": functools.partial(_joint_between_two_bodies, kind)
        for kind in (
            "filter",
            "weld",
            "revolute",
            "prismatic",
            "wheel",
            "distance",
            "motor",
            "mover",
            "pogo",
        )
    },
}


@pytest.mark.parametrize("kind", sorted(MAKERS))
def test_every_object_holds_its_worlds_own_liveness_flag(kind):
    """The flag is what makes an object of a destroyed world read as gone,
    so one made without it would come back to life in the next world."""
    world = World()
    try:
        made = MAKERS[kind](world)
        assert made._world_alive is world._world_alive
    finally:
        world.destroy()
    assert made.is_valid is False


def _all_subclasses(cls):
    for sub in cls.__subclasses__():
        yield sub
        yield from _all_subclasses(sub)


def test_the_flag_test_covers_every_joint_and_shape_class():
    from box2d import Joint, Shape
    from box2d.shape import ChainSegment

    world = World()
    try:
        made = {type(make(world)) for make in MAKERS.values()}
    finally:
        world.destroy()
    for base in (Joint, Shape):
        missing = set(_all_subclasses(base)) - made - {ChainSegment} - {base}
        assert not missing, missing
    assert ChainSegment in made


def test_a_destroy_refused_mid_step_leaves_the_world_and_its_objects_live():
    """Box2D cannot destroy a world while it steps, and the refusal must come
    before anything is marked gone."""
    world = World()
    ground = world.new_body().static().box(20, 1).build()
    ball = world.new_body().dynamic().position(0, 1.2).circle(0.5).build()
    refusals = []

    def pre_solve(shape_a, shape_b, manifold):
        try:
            world.destroy()
        except RuntimeError as refused:
            refusals.append(refused)
        return True

    world.pre_solve = pre_solve
    ball.shapes[0].enable_pre_solve_events = True
    try:
        for _ in range(30):
            world.step(1 / 60, 4)
        assert refusals, "the callback never ran"
        assert world.is_valid and ground.is_valid and ball.is_valid
        assert world._world_alive[0] is True
    finally:
        world.pre_solve = None
        world.destroy()
