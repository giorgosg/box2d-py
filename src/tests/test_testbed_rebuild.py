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


# --- what a scenario raises, in the testbed ---------------------------------


@pytest.fixture
def open_scenario(simulation):
    """Open a scenario class in the testbed; its registration goes after."""

    def open_(cls):
        state.current_test_cls = cls
        simulation.init_test()
        assert simulation.current_test_obj is not None, state.scenario_error
        return simulation.current_test_obj

    yield open_
    BaseTest.registry.pop("_Raises", None)


INPUT_HANDLERS = [
    ("on_key_down", ("a",)),
    ("on_key_up", ("a",)),
    ("on_mouse_down", ((0.0, 0.0),)),
    ("on_mouse_drag", ((0.0, 0.0), (1.0, 0.0))),
    ("on_mouse_release", ((0.0, 0.0),)),
]


@pytest.mark.parametrize("handler, args", INPUT_HANDLERS)
def test_an_input_handler_that_raises_is_reported_and_set_aside(
    simulation, open_scenario, handler, args
):
    """As a per-frame hook is: once, in the panel, and not again until Reset."""
    calls = []

    def raising(self, *args):
        calls.append(args)
        raise ValueError(f"bad {handler}")

    cls = type(
        "Handles",
        (BaseTest,),
        {"setup": lambda self: None, handler: raising},
        category="_Raises",
        name="Handles",
    )
    test = open_scenario(cls)

    simulation.run_hook(handler, *args)
    simulation.run_hook(handler, *args)

    assert len(calls) == 1, "set aside after raising"
    assert f"ValueError: bad {handler}" in state.scenario_error
    assert simulation.is_set_aside(handler)
    assert state.current_test_obj is test, "and the scenario carries on"

    simulation.press("reset")
    assert state.scenario_error is None
    simulation.run_hook(handler, *args)
    assert len(calls) == 2, "a rebuilt scene gives it another go"


def test_a_view_that_raises_leaves_the_scenario_open(simulation, open_scenario):
    """view() frames the scenario as it opens, and on Home: a scenario can
    override it, and one that raises is reported, as the hooks are."""

    class Unframed(BaseTest, category="_Raises", name="Unframed"):
        def setup(self):
            pass

        def view(self):
            raise ValueError("bad view")

    test = open_scenario(Unframed)

    assert "ValueError: bad view" in state.scenario_error
    assert state.current_test_obj is test
    simulation.reset_view()  # Home: set aside, so nothing more is raised


def test_a_control_callback_that_raises_is_reported_and_greyed_out(
    simulation, open_scenario
):
    from box2d_testbed.ui import UI

    class Controlled(BaseTest, category="_Raises", name="Controlled"):
        count = UI.int(1, 0, 10)
        other = UI.bool(False)
        seen = []

        def setup(self):
            pass

        @count.callback
        def on_count(self, key, value):
            raise ValueError("bad count")

        @other.callback
        def on_other(self, key, value):
            Controlled.seen.append(value)

    test = open_scenario(Controlled)

    simulation.set_control("count", 3)

    assert "ValueError: bad count" in state.scenario_error
    assert test.count == 3, "the value was taken before the callback raised"
    assert simulation.is_set_aside("count"), "so the panel greys it out"
    simulation.set_control("count", 4)
    assert test.count == 3, "and nothing reaches it while it is"

    simulation.set_control("other", True)
    assert Controlled.seen == [True], "the other controls still work"

    simulation.press("reset")
    assert not simulation.is_set_aside("count")
    assert state.scenario_error is None


@pytest.fixture
def setup_fails(open_scenario):
    """A scenario open in the testbed that built once and now raises on every
    rebuild, until its ``fail`` is cleared. Declared here, as the others are,
    so it is registered only while the test runs."""
    from box2d_testbed.ui import UI

    class SetupFails(BaseTest, category="_Raises", name="Setup Fails"):
        builds = 0
        fail = False
        hook_calls = 0
        rebuild_now = UI.button("Rebuild")

        def setup(self):
            SetupFails.builds += 1
            self.world.new_body().dynamic().circle(0.5).build()
            if SetupFails.fail:
                raise ValueError("bad rebuild")
            self.ready = True

        @rebuild_now.callback
        def on_rebuild_now(self, key, value):
            self.rebuild()

        def after_step(self, dt):
            SetupFails.hook_calls += 1
            self.ready  # what setup had yet to build when it raised

        status = on_key_down = after_step

    test = open_scenario(SetupFails)
    SetupFails.fail = True
    SetupFails.hook_calls = 0
    return test


@pytest.mark.parametrize("button", ["reset", "rebuild_now"])
def test_a_rebuild_that_raises_is_reported_and_reset_tries_again(
    simulation, setup_fails, button
):
    """Reported in the panel as a failed first build is, but the scenario
    stays open, with its controls, so Reset can build it again."""
    test = setup_fails
    SetupFails = type(test)

    simulation.press(button)

    assert "ValueError: bad rebuild" in state.scenario_error
    assert state.current_test_obj is test, "still there to press Reset on"
    assert test.world is simulation.world and simulation.world.is_valid
    assert not simulation.is_set_aside(button), "the failure is setup's"

    # The hooks would see a scene setup did not finish; they wait for one
    # that it did, and the build's traceback is not replaced by theirs.
    simulation.update_physics()
    simulation.status_lines()
    simulation.run_hook("on_key_down", "a")
    assert SetupFails.hook_calls == 0
    assert "ValueError: bad rebuild" in state.scenario_error

    simulation.press("reset")
    assert SetupFails.builds == 3, "Reset tried again, and it raised again"
    assert "ValueError: bad rebuild" in state.scenario_error

    SetupFails.fail = False
    simulation.press("reset")
    assert state.scenario_error is None
    simulation.update_physics()
    assert SetupFails.hook_calls == 1, "a whole scene runs its hooks again"
