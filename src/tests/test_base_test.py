# tests/test_base_test.py
"""What BaseTest promises the scenarios built on it.

Controls before setup, Reset and rebuild, and status text. Each scenario used
to handle the first two its own way -- a hasattr guard here, a hand-written
destroy loop there -- and drew its status at world coordinates picked by eye.
"""

import pytest

from box2d import World
from box2d_testbed.base_test import BaseTest, UI
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
    assert len(world.bodies) == 2, "and only one new one replaced it"
    assert scenario.size == 2.0
    assert scenario.crate.shapes[0].aabb.upper.x == pytest.approx(1.0, abs=0.05)


def test_reset_is_a_rebuild(world, scenario_class):
    scenario = scenario_class(world)
    scenario.setup()
    scenario.friction = 0.1
    first = scenario.crate

    scenario.reset = 1

    assert not first.is_valid
    assert len(world.bodies) == 2
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
    scenario.on_mouse_release(scenario.crate.position)  # must not raise


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
    exec(source, namespace)
    drop = namespace["Drop"](world)
    try:
        drop.drop_height = 3.0  # before setup: stored for setup to read
        drop.setup()
        assert drop.box.position.y == pytest.approx(3.0)
        assert drop.status() == "height 3.0"

        drop.drop_height = 10.0  # after: the callback rebuilds
        assert drop.box.position.y == pytest.approx(10.0)
        assert len(world.bodies) == 2
    finally:
        BaseTest.registry["Bodies"].pop("Drop", None)
