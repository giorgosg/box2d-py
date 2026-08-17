# tests/test_scenario_store.py
"""Where editable scenarios are kept, and what they may be called.

The name check is the load-bearing part. It is what keeps a store's writes
inside its own directory, and on the web build the names will arrive from
strangers, so it is tested as a boundary rather than as validation.
"""

import pytest

from box2d_testbed.scenario_store import (
    BuiltinStore,
    ScenarioRef,
    StoreError,
    UserStore,
    template_for,
    user_scenario_dir,
    validate_name,
)


@pytest.mark.parametrize(
    "name",
    [
        "scenario",
        "my_scenario_2",
        "A",
        "_private",
        "a" * 64,
    ],
)
def test_ordinary_names_are_accepted(name):
    assert validate_name(name) == name


@pytest.mark.parametrize(
    "name",
    [
        "",
        ".",
        "..",
        "../escape",
        "..\\escape",
        "/etc/passwd",
        "C:\\windows\\system32",
        "with space",
        "with-dash",
        "with.dot",
        "trailing/",
        "2leading_digit",
        "a" * 65,
        "nul\x00byte",
        "café",
        None,
        7,
    ],
)
def test_nothing_that_could_leave_the_directory_is_accepted(name):
    """Rejecting anything but an identifier is what makes this airtight.

    There is no path arithmetic here to get wrong: traversal, absolute paths
    and separators are all refused by the same rule that refuses a space.
    """
    with pytest.raises(StoreError):
        validate_name(name)


def test_a_user_store_round_trips(tmp_path):
    store = UserStore(tmp_path / "not-created-yet")
    assert store.names() == []

    ref = store.write("falling", "# hello\n")
    assert ref.name == "falling"
    assert ref.writable
    assert store.read("falling") == "# hello\n"
    assert store.names() == ["falling"]
    # Written into a directory that did not exist.
    assert (tmp_path / "not-created-yet" / "falling.py").is_file()

    store.write("falling", "# replaced\n")
    assert store.read("falling") == "# replaced\n"
    assert store.names() == ["falling"], "a rewrite is not a second scenario"

    store.delete("falling")
    assert store.names() == []
    # Deleting what is not there is what the editor does after a failed write.
    store.delete("falling")


def test_names_are_listed_in_order_and_unusable_ones_left_out(tmp_path):
    store = UserStore(tmp_path)
    for name in ("zebra", "apple", "middle"):
        store.write(name, "")
    # Dropped in by hand rather than written through the store: the loader
    # could not import them, so offering them in the picker would only fail.
    (tmp_path / "not a scenario.py").write_text("")
    (tmp_path / "9lives.py").write_text("")
    (tmp_path / "notes.txt").write_text("")

    assert store.names() == ["apple", "middle", "zebra"]


def test_a_missing_scenario_is_a_store_error(tmp_path):
    with pytest.raises(StoreError, match="cannot read"):
        UserStore(tmp_path).read("absent")


def test_free_name_steps_around_what_is_there(tmp_path):
    store = UserStore(tmp_path)
    assert store.free_name("untitled") == "untitled"
    store.write("untitled", "")
    assert store.free_name("untitled") == "untitled_1"
    store.write("untitled_1", "")
    assert store.free_name("untitled") == "untitled_2"


def test_the_builtins_are_readable_and_not_writable():
    store = BuiltinStore()
    names = store.names()

    assert "tb_joints" in names
    assert names == sorted(names)
    assert all(name.startswith("tb_") for name in names)
    assert "base_test" not in names, "only the scenario modules"

    assert "class " in store.read("tb_bodies")
    with pytest.raises(StoreError, match="read-only"):
        store.write("tb_bodies", "")
    with pytest.raises(StoreError, match="read-only"):
        store.delete("tb_bodies")
    with pytest.raises(StoreError, match="no builtin scenario"):
        store.read("nonexistent")


def test_a_ref_says_where_it_came_from(tmp_path):
    user = ScenarioRef(UserStore(tmp_path), "mine")
    builtin = ScenarioRef(BuiltinStore(), "tb_bodies")

    assert user.label == "user/mine.py"
    assert user.writable
    assert builtin.label == "builtin/tb_bodies.py"
    assert not builtin.writable


def test_the_scenario_directory_can_be_pointed_somewhere_else(monkeypatch):
    monkeypatch.setenv("BOX2D_TESTBED_SCENARIOS", "/somewhere/else")
    assert user_scenario_dir() == __import__("pathlib").Path("/somewhere/else")

    monkeypatch.delenv("BOX2D_TESTBED_SCENARIOS")
    monkeypatch.setenv("XDG_DATA_HOME", "/xdg")
    default = user_scenario_dir()
    # The XDG path is only the Linux answer; elsewhere it is the platform's own.
    assert default.name == "scenarios"
    assert default.parent.name == "box2d-testbed"


def test_the_template_is_named_after_its_file():
    source = template_for("my_ragdoll")

    assert "class MyRagdoll(" in source
    assert 'name="my_ragdoll"' in source
    # Absolute, because the loader runs a scenario file on its own.
    assert "from box2d_testbed.base_test import BaseTest, UI" in source
    assert "from ." not in source
