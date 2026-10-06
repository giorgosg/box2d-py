# tests/test_callbacks.py
"""Callbacks Box2D invokes during a step.

None of these were bound, so there was no way to express a collision rule that
categories cannot, no way to build a one-way platform, and no way to decide how
two materials rub together.

All four run inside b2World_Step, so none of them may touch the world. Each
keeps its cffi trampoline alive on the World; letting that be collected while
Box2D still holds the pointer would crash on the next step, which is why the
lifetime is tested here rather than assumed.
"""

import gc

import pytest

from box2d import World, Vec2


@pytest.fixture
def world():
    world = World()
    yield world
    world.destroy()


def falling_pair(world, **shape_args):
    """A ball dropped onto the ground, both shapes taking the given options."""
    ground = world.add_body(position=(0, 0))
    ground.add_box(20, 1, **shape_args)
    ball = world.add_body(body_type="dynamic", position=(0, 4))
    ball.add_circle(radius=0.5, **shape_args)
    return ground, ball


def run(world, steps=180):
    for _ in range(steps):
        world.step(1 / 60, 4)


# --- custom filter ----------------------------------------------------------


def test_custom_filter_can_cancel_a_collision(world):
    ground, ball = falling_pair(world, enable_custom_filtering=True)
    world.custom_filter = lambda a, b: False
    run(world)
    assert ball.position.y < -5, "the ball should have fallen through"


def test_custom_filter_can_allow_a_collision(world):
    ground, ball = falling_pair(world, enable_custom_filtering=True)
    world.custom_filter = lambda a, b: True
    run(world)
    assert ball.position.y > 0, "the ball should be resting on the ground"


def test_custom_filter_receives_both_shapes(world):
    ground, ball = falling_pair(world, enable_custom_filtering=True)
    seen = []
    world.custom_filter = lambda a, b: seen.append((a, b)) or True
    run(world)
    assert seen, "the filter was never consulted"
    assert {seen[0][0], seen[0][1]} == {ground.shapes[0], ball.shapes[0]}


def test_custom_filter_is_not_consulted_without_opting_in(world):
    """Only shapes created with enable_custom_filtering reach the callback."""
    falling_pair(world)
    seen = []
    world.custom_filter = lambda a, b: seen.append(1) or True
    run(world)
    assert not seen


def test_custom_filter_can_be_cleared(world):
    ground, ball = falling_pair(world, enable_custom_filtering=True)
    world.custom_filter = lambda a, b: False
    world.custom_filter = None

    assert world.custom_filter is None
    run(world)
    assert ball.position.y > 0, "clearing should restore normal collision"


# --- pre-solve --------------------------------------------------------------


def test_pre_solve_can_drop_a_contact(world):
    ground, ball = falling_pair(world, enable_pre_solve_events=True)
    world.pre_solve = lambda a, b, manifold: manifold.points.clear()
    run(world)
    assert ball.position.y < -5


def test_pre_solve_receives_the_contact_manifold(world):
    ground, ball = falling_pair(world, enable_pre_solve_events=True)
    seen = []

    def record(shape_a, shape_b, manifold):
        seen.append((shape_a, shape_b, manifold))

    world.pre_solve = record
    run(world)

    assert seen, "pre-solve was never called"
    shape_a, shape_b, manifold = seen[0]
    assert {shape_a, shape_b} == {ground.shapes[0], ball.shapes[0]}
    assert abs(manifold.normal.y) == pytest.approx(1.0, abs=0.1), "flat ground"
    assert manifold.points, "a touching contact has points"


def test_pre_solve_edits_reach_the_solver(world):
    """Turning the normal sideways turns a landing into a push sideways."""
    ground, ball = falling_pair(world, enable_pre_solve_events=True)

    def tilt(shape_a, shape_b, manifold):
        manifold.normal = Vec2(1, 0) if shape_a is ground.shapes[0] else Vec2(-1, 0)

    world.pre_solve = tilt
    run(world, steps=60)
    assert ball.position.y < 0, "with no upward push the ball sinks in"


def test_pre_solve_makes_a_one_way_platform(world):
    """The point of pre-solve: pass through going up, land coming down."""
    platform = world.add_body(position=(0, 0))
    platform.add_box(10, 0.5, enable_pre_solve_events=True)
    player = world.add_body(body_type="dynamic", position=(0, -4))
    player.add_circle(radius=0.5, enable_pre_solve_events=True)
    player.linear_velocity = (0, 12)

    def one_way(shape_a, shape_b, manifold):
        if player.linear_velocity.y > 0:
            manifold.points.clear()

    world.pre_solve = one_way

    peak = -99.0
    for _ in range(180):
        world.step(1 / 60, 4)
        peak = max(peak, player.position.y)

    assert peak > 1.0, "the player never got above the platform"
    assert player.position.y > 0, "and should have landed on top of it"


def test_a_raising_pre_solve_keeps_the_contact(world, capsys):
    ground, ball = falling_pair(world, enable_pre_solve_events=True)

    def broken(shape_a, shape_b, manifold):
        manifold.points.clear()
        raise RuntimeError("boom")

    world.pre_solve = broken
    run(world, steps=60)
    assert ball.position.y > 0, "the edit made before raising is not applied"
    assert "boom" in capsys.readouterr().err


# --- pre-continuous ----------------------------------------------------------


def bullet_at_wall(world):
    """A bullet fired at a thin wall, fast enough to cross it in one step."""
    wall = world.add_body(position=(0, 0))
    wall.add_box(0.1, 10, enable_pre_solve_events=True)
    bullet = world.add_body(body_type="dynamic", position=(-5, 0), is_bullet=True)
    bullet.add_circle(radius=0.1, enable_pre_solve_events=True)
    bullet.linear_velocity = (600, 0)
    return wall, bullet


def test_continuous_collision_stops_a_bullet_at_a_wall(world):
    wall, bullet = bullet_at_wall(world)
    run(world, steps=10)
    assert bullet.position.x < 0


def test_pre_continuous_can_let_a_bullet_through(world):
    wall, bullet = bullet_at_wall(world)
    seen = []

    def let_through(shape_a, shape_b, point, normal):
        seen.append((point, normal))
        return False

    world.pre_continuous = let_through
    run(world, steps=10)

    assert seen, "pre-continuous was never called"
    assert bullet.position.x > 0, "the bullet should have passed the wall"
    point, normal = seen[0]
    assert abs(normal.x) == pytest.approx(1.0, abs=0.01)


def test_pre_solve_and_pre_continuous_are_independent(world):
    world.pre_solve = lambda a, b, manifold: None
    world.pre_continuous = lambda a, b, point, normal: True
    world.pre_solve = None
    assert world.pre_continuous is not None
    world.pre_continuous = None
    assert world.pre_solve is None and world.pre_continuous is None


def test_pre_solve_can_be_cleared(world):
    ground, ball = falling_pair(world, enable_pre_solve_events=True)
    world.pre_solve = lambda a, b, point, normal: False
    world.pre_solve = None

    assert world.pre_solve is None
    run(world)
    assert ball.position.y > 0


# --- friction and restitution mixing ----------------------------------------


def test_friction_mixer_is_consulted(world):
    falling_pair(world, friction=0.5)
    seen = []
    world.friction_mixer = lambda fa, ma, fb, mb: seen.append((fa, fb)) or 0.0
    run(world)
    assert seen, "the friction mixer was never called"
    assert seen[0][0] == pytest.approx(0.5)


def test_restitution_mixer_changes_the_bounce(world):
    ground, ball = falling_pair(world, restitution=0.0)
    world.restitution_mixer = lambda ra, ma, rb, mb: 0.9

    peak_after_landing = -99.0
    landed = False
    for _ in range(300):
        world.step(1 / 60, 4)
        if not landed and ball.position.y < 1.0:
            landed = True
        elif landed:
            peak_after_landing = max(peak_after_landing, ball.position.y)

    assert peak_after_landing > 1.0, "a restitution of 0.9 should bounce it back up"


def test_mixers_can_be_cleared(world):
    falling_pair(world)
    world.friction_mixer = lambda *a: 0.0
    world.restitution_mixer = lambda *a: 1.0
    world.friction_mixer = None
    world.restitution_mixer = None

    assert world.friction_mixer is None
    assert world.restitution_mixer is None
    run(world)


# --- the parts that are easy to get wrong -----------------------------------


def test_trampolines_survive_garbage_collection(world):
    """Box2D holds a pointer to the trampoline, so the World must keep it."""
    ground, ball = falling_pair(world, enable_custom_filtering=True)

    def never_collide(shape_a, shape_b):
        return False

    world.custom_filter = never_collide
    del never_collide
    gc.collect()

    run(world)
    assert ball.position.y < -5, "the callback stopped working after collection"


@pytest.mark.parametrize(
    "name,args",
    [
        ("custom_filter", dict(enable_custom_filtering=True)),
        ("pre_solve", dict(enable_pre_solve_events=True)),
        ("friction_mixer", {}),
        ("restitution_mixer", {}),
    ],
)
def test_a_raising_callback_does_not_break_the_step(world, name, args, capfd):
    """These run inside the solver, so an exception must not escape into it."""
    ground, ball = falling_pair(world, **args)

    def boom(*arguments):
        raise RuntimeError("callback blew up")

    setattr(world, name, boom)
    run(world)

    assert ball.position.y > 0, "the world should still have simulated normally"
    assert "callback blew up" in capfd.readouterr().err


def test_callbacks_are_readable_back(world):
    def filter_fn(a, b):
        return True

    world.custom_filter = filter_fn
    assert world.custom_filter is filter_fn
