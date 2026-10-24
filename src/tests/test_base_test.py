# tests/test_base_test.py
"""What BaseTest promises the scenarios built on it.

Controls before setup, Reset and rebuild, and status text. Each scenario used
to handle the first two its own way -- a hasattr guard here, a hand-written
destroy loop there -- and drew its status at world coordinates picked by eye.
"""

import pytest

from box2d import DestroyedError, World
from box2d_testbed.base_test import BaseTest, UI, world_like
from box2d_testbed import testbed_simulation

CATEGORY = "_BaseTest"


@pytest.fixture(autouse=True)
def registry_left_as_it_was():
    """Scenarios defined here register themselves; take them out again."""
    yield
    BaseTest.registry.pop(CATEGORY, None)


@pytest.fixture
def world():
    world = World()
    yield world
    world.destroy()


@pytest.fixture
def scenario_class():
    class Crate(BaseTest, category=CATEGORY, name="Crate"):
        size = UI.float(1.0, min=0.5, max=2.0)
        friction = UI.float(0.6, min=0.0, max=1.0)

        def setup(self):
            self.world.new_body().static().segment((-5, 0), (5, 0)).build()
            self.crate = (
                self.world.new_body()
                .dynamic()
                .position(0, 2)
                .box(self.size, self.size, friction=self.friction)
                .build()
            )

        @size.callback
        def on_size(self, key, value):
            self.rebuild()

        @friction.callback
        def on_friction(self, key, value):
            # Relies on setup having run, with no guard.
            self.crate.shapes[0].friction = value

    return Crate


def test_a_control_set_before_setup_is_kept_for_setup(world, scenario_class):
    """Setting a control on a fresh scenario configures it; the callback,
    which needs the scene, waits until there is one."""
    scenario = scenario_class(world)
    scenario.friction = 0.2  # would raise in on_friction if it ran now
    scenario.size = 1.5  # would rebuild a scene that does not exist yet

    assert world.bodies == []
    scenario.setup()
    assert scenario.crate.shapes[0].friction == pytest.approx(0.2)
    assert len(world.bodies) == 2


def test_after_setup_controls_run_their_callbacks(world, scenario_class):
    scenario = scenario_class(world)
    scenario.setup()
    scenario.friction = 0.9
    assert scenario.crate.shapes[0].friction == pytest.approx(0.9)


def test_rebuild_replaces_the_scene_and_keeps_the_controls(world, scenario_class):
    scenario = scenario_class(world)
    scenario.setup()
    first = scenario.crate

    scenario.size = 2.0  # its callback rebuilds

    assert not first.is_valid, "the old scene is gone"
    assert len(scenario.world.bodies) == 2, "and only one new one replaced it"
    assert scenario.size == 2.0
    assert scenario.crate.shapes[0].bounds.upper.x == pytest.approx(1.0, abs=0.05)


def test_reset_is_a_rebuild(world, scenario_class):
    scenario = scenario_class(world)
    scenario.setup()
    scenario.friction = 0.1
    first = scenario.crate

    scenario.reset = 1

    assert not first.is_valid
    assert len(scenario.world.bodies) == 2
    assert scenario.crate.shapes[0].friction == pytest.approx(0.1)


def test_rebuild_before_setup_does_nothing(world, scenario_class):
    """Otherwise setup would build a second copy of the scene on top."""
    scenario = scenario_class(world)
    scenario.rebuild()
    assert world.bodies == []
    scenario.setup()
    assert len(world.bodies) == 2


def test_rebuild_lets_go_of_a_drag(world, scenario_class):
    scenario = scenario_class(world)
    scenario.setup()
    scenario.on_mouse_down(scenario.crate.position)
    assert scenario.mouse_joint is not None

    scenario.rebuild()

    assert scenario.mouse_joint is None
    assert len(scenario.world.bodies) == 2, "the drag's proxy body was left behind"
    assert all(body.type != "kinematic" for body in scenario.world.bodies)
    scenario.on_mouse_release(scenario.crate.position)  # must not raise


def test_rebuild_builds_in_a_new_world_and_destroys_the_old_one(world, scenario_class):
    """A new world numbers the scene from the start, as the first one did, so
    it runs as it first ran."""
    scenario = scenario_class(world)
    scenario.setup()
    crate = scenario.crate

    scenario.rebuild()

    assert not world.is_valid
    assert scenario.world is not world and scenario.world.is_valid
    with pytest.raises(DestroyedError):
        crate.position


def test_rebuild_makes_its_world_with_the_maker_it_was_given(world, scenario_class):
    """The testbed hands over its own maker after constructing the scenario,
    so a scenario overriding __init__(self, world) needs nothing more."""
    made = []

    def new_world():
        made.append(World(gravity=(0, -3)))
        return made[-1]

    scenario = scenario_class(world)
    scenario._new_world = new_world
    scenario.setup()
    scenario.rebuild()
    scenario.rebuild()

    assert len(made) == 2
    assert scenario.world is made[1]
    assert not made[0].is_valid, "each rebuild destroys the world it replaces"
    made[1].destroy()


def test_without_a_maker_a_rebuild_copies_the_world_as_the_scenario_found_it():
    """Not as setup or the running scene left it: setup sets up its own world
    again, and a change made while the scene ran is part of that run."""

    def keep_out(shape_a, shape_b):
        return True

    world = World(gravity=(1, -3))
    world.enable_sleeping = False
    world.contact_hertz = 45.0
    world.restitution_threshold = 2.5
    world.custom_filter = keep_out
    world.user_data = "mine"

    class Tuned(BaseTest, category=CATEGORY, name="Tuned"):
        def setup(self):
            self.world.hit_event_threshold = 7.0

        def after_step(self, dt):
            self.world.gravity = (0, 0)

    scenario = Tuned(world)
    scenario.setup()
    scenario.after_step(1 / 60)
    scenario.world.enable_warm_starting = False
    scenario.rebuild()

    new = scenario.world
    try:
        assert new.gravity == (1, -3)
        assert new.enable_sleeping is False
        assert new.enable_warm_starting is True
        assert new.contact_hertz == pytest.approx(45.0)
        assert new.restitution_threshold == pytest.approx(2.5)
        assert new.hit_event_threshold == pytest.approx(7.0), "from setup"
        assert new.custom_filter is keep_out
        assert new.user_data == "mine"
    finally:
        new.destroy()


def test_world_like_keeps_the_threads_and_the_split_apart():
    """The thread count is the pool's size and fixed; the worker count is
    how a step is split, and can be changed after creation."""
    try:
        threaded = World(threads=2)
    except RuntimeError:
        pytest.skip("this build has no threads")
    threaded.worker_count = 3
    copy = world_like(threaded)()
    try:
        assert copy.threads == 2
        assert copy.worker_count == 3
    finally:
        copy.destroy()
        threaded.destroy()


def test_a_drag_ends_when_the_scenario_destroys_the_dragged_body(world, scenario_class):
    """Box2D takes the mouse joint down with the body. The testbed calls the
    mouse handlers directly, so the drag and release that follow must cope."""
    scenario = scenario_class(world)
    scenario.setup()
    grab = scenario.crate.position
    scenario.on_mouse_down(grab)
    assert scenario.mouse_joint is not None

    scenario.crate.destroy()

    scenario.on_mouse_drag(grab + (1, 1), (1, 1))
    assert scenario.mouse_joint is None
    scenario.on_mouse_release(grab + (1, 1))
    assert scenario.mouse_joint is None
    assert len(world.bodies) == 1, "the drag's proxy body was left behind"


def test_a_press_after_the_dragged_body_went_grabs_again(world, scenario_class):
    """The release can go unseen -- the testbed only reports it over the
    simulation view -- so a dead joint must not block the next grab."""
    scenario = scenario_class(world)
    scenario.setup()
    scenario.on_mouse_down(scenario.crate.position)
    scenario.crate.destroy()
    other = world.new_body().dynamic().position(3, 2).box(1, 1).build()

    scenario.on_mouse_down(other.position)

    assert scenario.mouse_joint is not None and scenario.mouse_joint.is_valid
    assert scenario.mouse_joint.body_b is other
    assert len(world.bodies) == 3, "ground, other, and one proxy body"


def test_a_setup_that_raises_leaves_the_scenario_not_set_up(world):
    class Broken(BaseTest, category=CATEGORY, name="Broken"):
        def setup(self):
            raise RuntimeError("half built")

    scenario = Broken(world)
    with pytest.raises(RuntimeError):
        scenario.setup()
    assert scenario.is_set_up is False


def test_a_subclass_inherits_the_set_up_tracking(world, scenario_class):
    class Bigger(scenario_class, category=CATEGORY, name="Bigger"):
        def setup(self):
            super().setup()
            self.extra = self.world.new_body().dynamic().circle(0.5).build()

    scenario = Bigger(world)
    scenario.setup()
    assert scenario.is_set_up is True
    scenario.friction = 0.3
    assert scenario.crate.shapes[0].friction == pytest.approx(0.3)


def test_a_setup_from_a_mixin_is_tracked_too(world):
    """Only a setup written on the scenario class itself used to be tracked,
    so one inherited from a mixin left every control and Reset dead."""

    class Scene:
        def setup(self):
            self.ball = self.world.new_body().dynamic().circle(0.5).build()

    class Mixed(Scene, BaseTest, category=CATEGORY, name="Mixed"):
        radius = UI.float(0.5, min=0.1, max=1.0)

        @radius.callback
        def on_radius(self, key, value):
            self.ball.shapes[0].radius = value

    scenario = Mixed(world)
    scenario.setup()
    assert scenario.is_set_up
    scenario.radius = 0.8
    assert scenario.ball.shapes[0].radius == pytest.approx(0.8)

    first = scenario.ball
    scenario.reset = 1
    assert not first.is_valid, "Reset rebuilt the scene"


def test_a_subclass_finishes_its_own_setup_before_callbacks_run(world, scenario_class):
    """super().setup() returning is not the scene being finished: a subclass
    still has its own parts to build."""

    class Labelled(scenario_class, category=CATEGORY, name="Labelled"):
        def setup(self):
            super().setup()
            self.friction = 0.2  # a callback now would find no self.label
            self.label = "made after the parent's setup"

        @scenario_class.friction.callback
        def on_friction_needing_label(self, key, value):
            assert self.label

    scenario = Labelled(world)
    scenario.setup()  # raised AttributeError when the callback ran early
    assert scenario.friction == 0.2, "the value is kept"

    scenario.friction = 0.3  # and once the scene is whole, callbacks run
    assert scenario.crate.shapes[0].friction == pytest.approx(0.3)


def test_a_setup_that_sets_its_own_control_does_not_recurse_on_reset(world):
    class SelfSet(BaseTest, category=CATEGORY, name="SelfSet"):
        count = UI.int(3, min=1, max=10)

        def setup(self):
            self.count = 4  # e.g. clamped to what fits
            for i in range(self.count):
                self.world.new_body().dynamic().position(i, 0).circle(0.4).build()

        @count.callback
        def on_count(self, key, value):
            self.rebuild()

    scenario = SelfSet(world)
    scenario.setup()
    scenario.reset = 1
    scenario.reset = 1
    assert len(scenario.world.bodies) == 4


def test_a_rebuild_that_raises_leaves_no_half_scene_marked_whole(world):
    """Callbacks stay off over a half-built scene, and Reset tries again."""

    class Flaky(BaseTest, category=CATEGORY, name="Flaky"):
        fail = False
        size = UI.float(1.0, min=0.5, max=2.0)

        def setup(self):
            self.world.new_body().static().segment((-5, 0), (5, 0)).build()
            if self.fail:
                raise RuntimeError("half built")
            self.thing = self.world.new_body().dynamic().circle(self.size).build()

        @size.callback
        def on_size(self, key, value):
            self.thing.shapes[0].radius = value

    scenario = Flaky(world)
    scenario.setup()
    scenario.fail = True
    with pytest.raises(RuntimeError):
        scenario.rebuild()
    assert scenario.is_set_up is False
    scenario.size = 1.5  # would touch the destroyed body if it ran

    scenario.fail = False
    scenario.reset = 1
    assert scenario.is_set_up
    assert scenario.thing.shapes[0].radius == pytest.approx(1.5)


# --- status ---------------------------------------------------------------------


def simulation_showing(scenario):
    """A TestbedSimulation holding one scenario, without loading the user's
    scenario directory or building a renderer."""
    cls = testbed_simulation.TestbedSimulation
    simulation = cls.__new__(cls)
    simulation.current_test_obj = scenario
    simulation._failed_hooks = set()
    return simulation


@pytest.mark.parametrize(
    "status, lines",
    [
        (None, []),
        ("one line", ["one line"]),
        ("two\nlines", ["two", "lines"]),
        (["a list", 3], ["a list", "3"]),
        (("a tuple",), ["a tuple"]),
        (42, ["42"]),
    ],
)
def test_status_comes_back_as_lines(world, status, lines):
    class Reporting(BaseTest, category=CATEGORY, name="Reporting"):
        def setup(self):
            pass

        def status(self):
            return status

    assert simulation_showing(Reporting(world)).status_lines() == lines


def test_by_default_there_is_no_status(world, scenario_class):
    assert simulation_showing(scenario_class(world)).status_lines() == []


def test_a_status_that_raises_is_reported_once(world, capsys):
    class Failing(BaseTest, category=CATEGORY, name="Failing"):
        calls = 0

        def setup(self):
            pass

        def status(self):
            Failing.calls += 1
            raise ValueError("bad status")

    simulation = simulation_showing(Failing(world))
    assert simulation.status_lines() == []
    assert simulation.status_lines() == []
    assert Failing.calls == 1
    assert capsys.readouterr().out.count("status raised") == 1


def test_the_readme_example_runs(world):
    """README shows a whole scenario; it should keep working as written."""
    import pathlib
    import re

    readme = pathlib.Path(__file__).parents[2] / "README.md"
    section = readme.read_text(encoding="utf-8").split(
        "### What a scenario looks like", 1
    )[1]
    source = re.search(r"```python\n(.*?)```", section, re.S).group(1)

    namespace = {}
    try:
        exec(source, namespace)
        drop = namespace["Drop"](world)
        drop.drop_height = 3.0  # before setup: stored for setup to read
        drop.setup()
        assert drop.box.position.y == pytest.approx(3.0)
        assert drop.status() == "height 3.0"

        drop.drop_height = 10.0  # after: the callback rebuilds
        assert drop.box.position.y == pytest.approx(10.0)
        assert len(drop.world.bodies) == 2
    finally:
        BaseTest.registry["Bodies"].pop("Drop", None)
