"""A reset scene runs again exactly as it first did, given the same random
numbers -- several scenes are built from Python's, and draw new ones on Reset.

rebuild() builds the scene again in a new world, made as the first one was.
It used to build it in the world it already lived in, and that could not be
exact: Box2D reuses the ids it frees, last freed first, and solves in id
order, so once a scene had run its contacts came back numbered differently
and the rebuilt scene was simulated differently -- 14 of the 55 scenarios
diverged. Ragdoll's Respawn, pressed after the figure had landed, dropped the
next one somewhere a fresh one would not land.
"""

import random

import pytest

from box2d import World
from box2d_testbed import (  # noqa: F401  (registers the scenarios)
    tb_benchmark,
    tb_bodies,
    tb_character,
    tb_clock,
    tb_collision,
    tb_continuous,
    tb_events,
    tb_joints,
    tb_shapes,
    tb_stacking,
)
from box2d_testbed import testbed_simulation
from box2d_testbed.base_test import BaseTest
from box2d_testbed.testbed_state import state
from testbed_scenarios import every_scenario, press, run, scenario

#: Enough for every scene to have collided, stacked or swung, which is when a
#: rebuild in the old world used to come out differently.
SECONDS = 2.0

#: Several scenarios build from Python's random numbers, so both builds of a
#: scene draw the same ones.
SEED = 1234

# These tests seed Python's random numbers; put them back afterwards.
pytestmark = pytest.mark.usefixtures("random_left_as_it_was")


@pytest.fixture
def fresh_world():
    """A second fresh world, for the scene built once, destroyed after the test."""
    world = World()
    yield world
    world.destroy()


def motion(world):
    """Every body's transform and velocities, in creation order.

    As the floats' hex spellings, so the comparison is bit for bit: ``==`` on
    the floats themselves would take -0.0 for 0.0.
    """
    rows = []
    for body in world.bodies:
        transform = body.transform
        values = (
            transform.p.x,
            transform.p.y,
            transform.q.c,
            transform.q.s,
            body.linear_velocity.x,
            body.linear_velocity.y,
            body.angular_velocity,
        )
        rows.append(tuple(float(value).hex() for value in values))
    return rows


@pytest.mark.parametrize("category, name", every_scenario())
def test_a_reset_scene_runs_again_exactly_as_it_first_did(world, category, name):
    """Compared bit for bit after running: a solve order that differs shows up
    as a difference somewhere, even in a scene that ends up looking the same.
    """
    random.seed(SEED)
    test = scenario(world, category, name)
    run(test, SECONDS)
    first_run = motion(world)
    first_hash = world.state_hash

    random.seed(SEED)
    press(test, "reset")

    assert not world.is_valid, "the first world is gone"
    assert test.world is not world and test.world.is_valid
    run(test, SECONDS)

    assert motion(test.world) == first_run
    assert test.world.state_hash == first_hash


def test_compound_count_builds_the_scene_a_fresh_world_would(world, fresh_world):
    """Count used to destroy and set up by hand, in creation order, so the
    smaller scene it built came out in reverse id order."""
    # The pieces fall a while before they land on each other.
    seconds = 3.0

    fresh = BaseTest.registry["Benchmark"]["Compound"](fresh_world)
    fresh.count = 2
    fresh.setup()
    run(fresh, seconds)

    changed = scenario(world, "Benchmark", "Compound")
    changed.count = 2
    run(changed, seconds)

    assert motion(changed.world) == motion(fresh_world)


# --- in the testbed ---------------------------------------------------------


@pytest.fixture
def testbed_state_left_as_it_was():
    """The testbed's state is one shared object; put back what these change."""
    names = (
        "current_test_cls",
        "current_test_obj",
        "scenario_error",
        "step_count",
        "center",
        "scale",
        "gravity",
        "threads",
        "enable_sleeping",
        "enable_warm_starting",
        "max_linear_speed",
    )
    saved = {name: getattr(state, name) for name in names}
    yield
    for name, value in saved.items():
        setattr(state, name, value)


@pytest.fixture
def simulation(testbed_state_left_as_it_was):
    """The testbed's simulation showing Ragdoll, with no renderer and without
    loading the user's scenarios. The world is destroyed after the test."""
    cls = testbed_simulation.TestbedSimulation
    simulation = cls.__new__(cls)
    simulation.world = None
    simulation._applied_settings = None
    simulation.debug_draw = None
    state.current_test_cls = BaseTest.registry["Joints"]["Ragdoll"]
    simulation.init_test()
    yield simulation
    simulation.world.destroy()


def test_reset_in_the_testbed_moves_everything_onto_the_new_world(simulation):
    test = simulation.current_test_obj
    old = simulation.world
    for _ in range(30):
        simulation.update_physics()
    state.center, state.scale = (3.0, 4.0), 7.0

    press(test, "reset")

    assert not old.is_valid
    assert simulation.world is test.world
    assert simulation.world.is_valid and simulation.world is not old
    assert state.current_test_obj is test, "the same scenario, rebuilt"
    assert state.step_count == 0, "counted for the new world"
    assert (state.center, state.scale) == ((3.0, 4.0), 7.0), "the view is kept"
    simulation.update_physics()  # steps the new world, not the old one
    assert state.step_count == 1


def test_rebuilding_a_scenario_no_longer_open_leaves_the_testbed_alone(simulation):
    """A scenario object outlives its turn -- a console name can hold it --
    and rebuilding it must not swap the open scenario's world out."""
    left = simulation.current_test_obj
    state.current_test_cls = BaseTest.registry["Joints"]["Soft Body"]
    simulation.init_test()
    showing = simulation.world

    left.rebuild()

    assert simulation.world is showing and showing.is_valid
    assert simulation.current_test_obj.world is showing
    assert left.world is not showing
    left.world.destroy()


def test_reset_rebuilds_a_scenario_that_takes_only_a_world(simulation):
    """Scenarios may override __init__(self, world); the testbed must not
    need them to accept anything more."""

    class Own(BaseTest, category="_Rebuild", name="Own"):
        def __init__(self, world):
            super().__init__(world)

        def setup(self):
            self.world.new_body().dynamic().circle(0.5).build()

    try:
        state.current_test_cls = Own
        simulation.init_test()
        test = simulation.current_test_obj
        assert test is not None, state.scenario_error
        old = simulation.world

        press(test, "reset")

        assert not old.is_valid
        assert simulation.world is test.world
    finally:
        BaseTest.registry.pop("_Rebuild", None)


def test_reset_gives_a_hook_that_raised_another_go(simulation):
    """A hook that raises is set aside until the scene is built again."""

    class Flaky(BaseTest, category="_Rebuild", name="Flaky"):
        calls = 0

        def setup(self):
            pass

        def after_step(self, dt):
            Flaky.calls += 1
            raise ValueError("bad step")

    try:
        state.current_test_cls = Flaky
        simulation.init_test()
        simulation.update_physics()
        simulation.update_physics()
        assert Flaky.calls == 1, "set aside after raising"
        assert "bad step" in state.scenario_error

        press(simulation.current_test_obj, "reset")
        assert state.scenario_error is None, "the panel stops showing it"
        simulation.update_physics()

        assert Flaky.calls == 2
        assert "bad step" in state.scenario_error, "and shows it again"
    finally:
        BaseTest.registry.pop("_Rebuild", None)


def test_reset_in_the_testbed_makes_the_world_with_the_panels_settings(simulation):
    """The panel's settings, as they are now -- not as the scene's own setup
    left them, and not as they were when the scenario was opened."""
    test = simulation.current_test_obj
    state.enable_sleeping = False
    state.enable_warm_starting = False
    state.max_linear_speed = 123.0
    simulation.update_physics()  # applies them to the running world

    press(test, "reset")

    world = simulation.world
    assert world.gravity == state.gravity
    assert world.worker_count == state.threads
    assert world.enable_sleeping is False
    assert world.enable_warm_starting is False
    assert world.max_linear_speed == pytest.approx(123.0)
    # Ragdoll's setup stiffens the contacts; the new world gets that from
    # setup running again.
    assert world.contact_hertz == pytest.approx(240.0)
