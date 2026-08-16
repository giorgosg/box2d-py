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

from box2d import World


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
    world.pre_solve = lambda a, b, point, normal: False
    run(world)
    assert ball.position.y < -5


def test_pre_solve_receives_the_contact_geometry(world):
    ground, ball = falling_pair(world, enable_pre_solve_events=True)
    seen = []

    def record(shape_a, shape_b, point, normal):
        seen.append((point, normal))
        return True

    world.pre_solve = record
    run(world)

    assert seen, "pre-solve was never called"
    point, normal = seen[0]
    assert abs(normal.y) == pytest.approx(1.0, abs=0.1), "a flat ground's normal"
    assert point.y == pytest.approx(0.5, abs=0.6)


def test_pre_solve_makes_a_one_way_platform(world):
    """The point of pre-solve: pass through going up, land coming down."""
    platform = world.add_body(position=(0, 0))
    platform.add_box(10, 0.5, enable_pre_solve_events=True)
    player = world.add_body(body_type="dynamic", position=(0, -4))
    player.add_circle(radius=0.5, enable_pre_solve_events=True)
    player.linear_velocity = (0, 12)

    world.pre_solve = lambda a, b, point, normal: player.linear_velocity.y <= 0

    peak = -99.0
    for _ in range(180):
        world.step(1 / 60, 4)
        peak = max(peak, player.position.y)

    assert peak > 1.0, "the player never got above the platform"
    assert player.position.y > 0, "and should have landed on top of it"


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
