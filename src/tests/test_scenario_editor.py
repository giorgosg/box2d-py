# tests/test_scenario_editor.py
"""The source rewriting behind Fork.

A copy of a builtin has two problems the moment it is written: it declares the
same scenario names as the original, which means it replaces it in the panel
rather than appearing beside it, and it imports its own package relatively,
which only works from inside that package. Both are fixed on the way out.
"""

import pytest

# The editor is imgui's, so without the testbed extra there is nothing to test.
pytest.importorskip("imgui_bundle", reason="needs the testbed extra")

from box2d_testbed.scenario_store import ScenarioRef  # noqa: E402
from box2d_testbed.scenario_editor import (  # noqa: E402
    rename_scenarios,
    rewrite_relative_imports,
)


def test_a_scenario_is_renamed_so_the_copy_sits_beside_the_original():
    source = 'class Foo(BaseTest, category="Bodies", name="Body Type"):\n    pass\n'

    rewritten, renamed = rename_scenarios(source, set())

    assert renamed == ["Body Type copy"]
    assert 'name="Body Type copy"' in rewritten
    assert (
        'category="Bodies"' in rewritten
    ), "the category is kept, so it sorts alongside"


def test_every_scenario_in_the_file_is_renamed():
    """Forking tb_joints means forking twenty scenarios at once."""
    source = (
        'class A(BaseTest, category="C", name="First"):\n    pass\n\n'
        'class B(BaseTest, category="C", name="Second"):\n    pass\n'
    )

    rewritten, renamed = rename_scenarios(source, set())

    assert renamed == ["First copy", "Second copy"]
    assert 'name="First copy"' in rewritten
    assert 'name="Second copy"' in rewritten


def test_a_name_already_taken_is_stepped_around():
    """Forking the same scenario twice, which is what comparing two changes
    against the original takes."""
    source = 'class A(BaseTest, category="C", name="Thing"):\n    pass\n'

    first, _ = rename_scenarios(source, {"Thing"})
    second, _ = rename_scenarios(source, {"Thing", "Thing copy"})
    third, names = rename_scenarios(source, {"Thing", "Thing copy", "Thing copy 2"})

    assert 'name="Thing copy"' in first
    assert 'name="Thing copy 2"' in second
    assert 'name="Thing copy 3"' in third
    assert names == ["Thing copy 3"]


def test_two_scenarios_wanting_the_same_new_name_do_not_collide():
    source = (
        'class A(BaseTest, category="C", name="Thing"):\n    pass\n\n'
        'class B(BaseTest, category="D", name="Thing"):\n    pass\n'
    )

    _, renamed = rename_scenarios(source, set())

    assert renamed == ["Thing copy", "Thing copy 2"]


def test_a_class_header_split_over_several_lines_is_still_found():
    source = (
        "class Wrapped(\n"
        "    BaseTest,\n"
        '    category="Bodies",\n'
        '    name="Body Type",\n'
        "):\n    pass\n"
    )

    _, renamed = rename_scenarios(source, set())

    assert renamed == ["Body Type copy"]


def test_single_quotes_work_the_same():
    source = "class A(BaseTest, category='C', name='Thing'):\n    pass\n"

    rewritten, renamed = rename_scenarios(source, set())

    assert renamed == ["Thing copy"]
    assert "name='Thing copy'" in rewritten


def test_a_name_that_is_not_a_class_header_is_left_alone():
    """``name=`` turns up in scenario code as often as in a class header."""
    source = (
        "class A(BaseTest, category='C', name='Thing'):\n"
        "    def setup(self):\n"
        "        self.body = self.world.new_body(name='ground').build()\n"
        "        label = self.name\n"
    )

    rewritten, renamed = rename_scenarios(source, set())

    assert renamed == ["Thing copy"]
    assert "name='ground'" in rewritten
    assert "label = self.name" in rewritten


def test_nothing_to_rename_is_not_an_error():
    rewritten, renamed = rename_scenarios("answer = 42\n", set())

    assert renamed == []
    assert rewritten == "answer = 42\n"


def test_relative_imports_are_made_absolute():
    source = (
        "from .base_test import BaseTest, UI\n"
        "from .shared import donut, Car  # noqa: F401\n"
        "from .human import Human\n"
    )

    rewritten = rewrite_relative_imports(source)

    assert rewritten == (
        "from box2d_testbed.base_test import BaseTest, UI\n"
        "from box2d_testbed.shared import donut, Car  # noqa: F401\n"
        "from box2d_testbed.human import Human\n"
    )


def test_imports_that_are_already_absolute_are_untouched():
    source = (
        "import math\n"
        "from box2d import Vec2, Color\n"
        "from box2d.shape import Circle\n"
        "from itertools import product\n"
    )

    assert rewrite_relative_imports(source) == source


def test_a_dot_that_is_not_an_import_is_untouched():
    source = "x = self.world.bodies\ny = 1.5\nfrom_here = a.b\n"

    assert rewrite_relative_imports(source) == source


def test_every_builtin_survives_being_forked():
    """The real inputs: whatever the shipped scenarios happen to do today."""
    from box2d_testbed.scenario_store import BuiltinStore

    store = BuiltinStore()
    for name in store.names():
        rewritten = rewrite_relative_imports(store.read(name))
        rewritten, renamed = rename_scenarios(rewritten, set())

        assert "from ." not in rewritten, f"{name} kept a relative import"
        assert renamed, f"{name} has scenarios, so some should have been renamed"
        # It still has to be Python, which a bad substitution would not be.
        compile(rewritten, f"{name}.py", "exec")


# --- the editor's own behaviour, without a window ----------------------------
#
# Everything below drives the editor directly. It needs no imgui context and no
# frames: only the panel's gui() draws, and that is covered in
# test_testbed_headless.

BROKEN = "class Unfinished(:\n"

WORKING = (
    "from box2d_testbed.base_test import BaseTest\n\n\n"
    'class Works(BaseTest, category="_Editor", name="works"):\n'
    "    def setup(self):\n"
    "        self.world.new_body().static().segment((-5, 0), (5, 0)).build()\n"
)


@pytest.fixture
def editor(tmp_path, monkeypatch):
    """An editor over a scenario directory of its own, and no simulation.

    The registry and the selected scenario are both process-wide, and loading
    is what these tests do, so both are put back afterwards -- otherwise the
    scenario left selected here is the one another test finds running.
    """
    from types import SimpleNamespace

    from box2d_testbed.base_test import BaseTest
    from box2d_testbed.scenario_editor import ScenarioEditor
    from box2d_testbed.testbed_state import state

    monkeypatch.setenv("BOX2D_TESTBED_SCENARIOS", str(tmp_path))
    snapshot = {c: dict(tests) for c, tests in BaseTest.registry.items()}
    selected = (state.current_test_cls, state.current_test_obj, state.scenario_error)
    try:
        yield ScenarioEditor(SimpleNamespace(simulation=None))
    finally:
        state.current_test_cls, state.current_test_obj, state.scenario_error = selected
        for category in list(BaseTest.registry):
            if category not in snapshot:
                del BaseTest.registry[category]
        for category, tests in snapshot.items():
            current = BaseTest.registry.setdefault(category, {})
            current.clear()
            current.update(tests)


def test_new_writes_a_scenario_and_opens_it(editor, tmp_path):
    editor.new()

    assert editor.ref.name == "untitled"
    assert editor.ref.writable
    assert (tmp_path / "untitled.py").is_file()
    assert not editor.dirty
    assert editor.message == "loaded untitled"

    # A second one steps around the first rather than overwriting it.
    editor.new()
    assert editor.ref.name == "untitled_1"


def test_a_fork_that_will_not_load_says_so(editor):
    """Rather than reporting the rename it just did and looking successful."""
    editor.user_store.write("broken", BROKEN)
    editor.open(ScenarioRef(editor.user_store, "broken"))

    editor.fork()

    assert editor.message_is_error is True
    assert "invalid syntax" in editor.message
    assert "forked" not in editor.message


def test_reverting_throws_the_edits_away(editor):
    editor.user_store.write("mine", WORKING)
    editor.open(ScenarioRef(editor.user_store, "mine"))
    editor.editor.set_text(BROKEN)
    assert editor.dirty

    editor.revert()

    assert not editor.dirty
    assert "class Works" in editor.editor.get_text()


def test_a_builtin_cannot_be_saved_over(editor):
    """Save is disabled in the toolbar, but the method is the thing that has to
    refuse: the menu offers it too."""
    from box2d_testbed.scenario_store import BuiltinStore

    editor.open(ScenarioRef(BuiltinStore(), "tb_bodies"))
    before = editor.editor.get_text()
    editor.editor.set_text("# vandalised\n")

    editor.save()

    assert BuiltinStore().read("tb_bodies") == before, "the shipped file is untouched"


def test_deleting_takes_the_scenario_out_of_the_registry(editor, tmp_path):
    from box2d_testbed.base_test import BaseTest

    editor.user_store.write("mine", WORKING)
    editor.open(ScenarioRef(editor.user_store, "mine"))
    editor.load()
    assert "works" in BaseTest.registry["_Editor"]

    editor.delete()

    assert "_Editor" not in BaseTest.registry
    assert not (tmp_path / "mine.py").exists()
    assert editor.ref is None
    assert not editor.dirty, "nothing is open, so there is nothing unsaved"


def test_opening_a_scenario_that_has_gone_missing_reports_it(editor, tmp_path):
    editor.user_store.write("mine", WORKING)
    ref = ScenarioRef(editor.user_store, "mine")
    (tmp_path / "mine.py").unlink()

    editor.open(ref)

    assert editor.message_is_error is True
    assert "cannot read" in editor.message
    assert editor.ref is None, "and nothing was opened"
