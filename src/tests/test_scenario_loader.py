# tests/test_scenario_loader.py
"""Running edited source, and what happens when it is wrong.

Saving a file is the testbed's compile step, so the interesting cases here are
all failures: the scenario you were looking at has to survive a save that will
not compile, and a file that has been saved five times must have registered one
scenario rather than five.
"""

import textwrap

import pytest

from box2d import World
from box2d_testbed.base_test import BaseTest
from box2d_testbed.scenario_loader import (
    USER_PACKAGE,
    LoadError,
    ScenarioLoader,
    source_path_hint,
)
from box2d_testbed.scenario_store import UserStore, template_for

CATEGORY = "_Loader"


def source(name, class_name="Scenario", category=CATEGORY, body=None, header=""):
    """A scenario file, as short as one can be."""
    setup = textwrap.indent(textwrap.dedent(body or "pass").strip("\n"), " " * 8)
    return (
        "from box2d_testbed.base_test import BaseTest, UI\n"
        f"{header}\n\n"
        f'class {class_name}(BaseTest, category="{category}", name="{name}"):\n'
        "    def setup(self):\n"
        f"{setup}\n"
    )


@pytest.fixture(autouse=True)
def registry_left_as_it_was():
    """The registry is global, and these tests fill it with rubbish."""
    snapshot = {c: dict(tests) for c, tests in BaseTest.registry.items()}
    yield
    for category in list(BaseTest.registry):
        if category not in snapshot:
            del BaseTest.registry[category]
    for category, tests in snapshot.items():
        current = BaseTest.registry.setdefault(category, {})
        current.clear()
        current.update(tests)


@pytest.fixture
def loader():
    """A loader of this test's own, so tests cannot see each other's files."""
    return ScenarioLoader()


def registered(name, category=CATEGORY):
    return BaseTest.registry.get(category, {}).get(name)


def simulate(cls, steps=4):
    """Build the scenario and step it, which is what the testbed will do."""
    world = World()
    obj = cls(world)
    obj.setup()
    for _ in range(steps):
        world.step(1 / 60, 4)
        obj.after_step(1 / 60)
    return obj


def test_a_loaded_scenario_is_registered_and_runs(loader):
    body = """
        self.world.new_body().static().segment((-10, 0), (10, 0)).build()
        self.ball = self.world.new_body().dynamic().position(0, 6).circle(0.5).build()
    """
    classes = loader.load_source("mine", source("Falling", body=body))

    assert [cls.name for cls in classes] == ["Falling"]
    assert registered("Falling") is classes[0]
    obj = simulate(classes[0])
    assert obj.ball.position.y < 6, "it should have fallen"


def test_the_template_loads_and_runs(loader):
    """The starter file is the first thing a user sees; it must work."""
    classes = loader.load_source("untitled", template_for("untitled"))

    assert [cls.name for cls in classes] == ["untitled"]
    simulate(classes[0])


def test_saving_again_replaces_rather_than_accumulates(loader):
    loader.load_source("mine", source("First"))
    first = registered("First")

    classes = loader.load_source("mine", source("First"))

    assert registered("First") is classes[0]
    assert registered("First") is not first, "a reload is a new class"
    assert len(BaseTest.registry[CATEGORY]) == 1


def test_renaming_a_scenario_leaves_no_ghost_behind(loader):
    """The bug this exists to prevent: the panel listing scenarios that were
    renamed away, each one a class nothing can reach."""
    loader.load_source("mine", source("Before"))
    assert registered("Before") is not None

    loader.load_source("mine", source("After"))

    assert registered("Before") is None
    assert registered("After") is not None
    assert list(BaseTest.registry[CATEGORY]) == ["After"]


def test_a_name_another_file_has_claimed_is_left_alone(loader):
    """Two files both declaring one name: unloading the first must not take the
    second's registration with it."""
    loader.load_source("first", source("Shared"))
    second = loader.load_source("second", source("Shared"))[0]

    loader.unload("first")

    assert registered("Shared") is second


def test_two_files_may_use_the_same_class_name(loader):
    """They are separate modules, so nothing collides but their scenario names."""
    a = loader.load_source("a", source("Alpha", class_name="Scenario"))[0]
    b = loader.load_source("b", source("Beta", class_name="Scenario"))[0]

    assert a is not b
    assert registered("Alpha") is a
    assert registered("Beta") is b


def test_source_that_will_not_compile_changes_nothing(loader):
    working = loader.load_source("mine", source("Working"))[0]

    with pytest.raises(LoadError) as caught:
        loader.load_source("mine", "class Broken(:\n")

    assert caught.value.line == 1
    assert "invalid syntax" in caught.value.message
    assert registered("Working") is working, "the scenario on screen survives"


def test_a_file_that_raises_on_import_reports_the_line(loader):
    working = loader.load_source("mine", source("Working"))[0]
    broken = "x = 1\ny = 2\nraise ValueError('boom')\n"

    with pytest.raises(LoadError) as caught:
        loader.load_source("mine", broken)

    assert caught.value.line == 3
    assert "ValueError: boom" in caught.value.message
    assert "boom" in caught.value.detail
    assert registered("Working") is working


def test_half_a_file_does_not_leave_half_its_scenarios_registered(loader):
    """Registration happens as the class statement runs, so a file that fails
    part way through has already registered what came before it."""
    partial = source("Fine") + "\nraise RuntimeError('after the class')\n"

    with pytest.raises(LoadError, match="after the class"):
        loader.load_source("mine", partial)

    assert registered("Fine") is None
    assert CATEGORY not in BaseTest.registry


def test_a_file_with_no_scenario_in_it_is_an_error(loader):
    working = loader.load_source("mine", source("Working"))[0]

    with pytest.raises(LoadError, match="no scenario"):
        loader.load_source("mine", "answer = 42\n")

    assert registered("Working") is working, "and it did not unload what worked"


def test_relative_imports_are_explained_rather_than_just_failing(loader):
    """What you get from copying a builtin by hand instead of forking it."""
    with pytest.raises(LoadError) as caught:
        loader.load_source("mine", "from .base_test import BaseTest\n")

    assert "relative imports do not work" in caught.value.message
    assert "from box2d_testbed.base_test import" in caught.value.message


def test_unloading_removes_the_category_it_emptied(loader):
    loader.load_source("mine", source("Only"))
    assert CATEGORY in BaseTest.registry

    loader.unload("mine")

    assert CATEGORY not in BaseTest.registry
    assert loader.classes_for("mine") == []


def test_a_module_name_of_its_own_keeps_tracebacks_readable(loader):
    cls = loader.load_source("my_file", source("Named"))[0]

    assert cls.__module__ == f"{USER_PACKAGE}.my_file"


def test_a_whole_directory_loads_and_bad_files_do_not_stop_it(loader, tmp_path):
    store = UserStore(tmp_path)
    store.write("good", source("Good"))
    store.write("also_good", source("AlsoGood"))
    store.write("bad", "def broken(\n")

    errors = loader.load_store(store)

    assert [ref.name for ref, _ in errors] == ["bad"]
    assert isinstance(errors[0][1], LoadError)
    assert registered("Good") is not None
    assert registered("AlsoGood") is not None


def test_a_loaded_scenario_knows_which_file_it_came_from(loader, monkeypatch):
    monkeypatch.setattr("box2d_testbed.scenario_loader.loader", loader)
    cls = loader.load_source("mine", source("Mine"))[0]

    assert loader.owner_of(cls) == "mine"
    assert source_path_hint(cls) == "mine"


def test_a_builtin_scenario_points_at_its_own_module():
    from box2d_testbed import tb_bodies  # noqa: F401

    assert source_path_hint(BaseTest.registry["Bodies"]["Body Type"]) == "tb_bodies"


def test_the_filename_shown_in_a_traceback_is_the_real_one(loader, tmp_path):
    """So that a traceback in the console points somewhere you can open."""
    path = tmp_path / "mine.py"
    broken = "raise ValueError('boom')\n"
    path.write_text(broken)

    with pytest.raises(LoadError) as caught:
        loader.load_source("mine", broken, filename=str(path))

    assert str(path) in caught.value.detail
    # The line itself, which only linecache can supply, and only for a file
    # that is really there.
    assert "raise ValueError('boom')" in caught.value.detail
