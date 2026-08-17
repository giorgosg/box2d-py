# tests/test_scenario_store.py
"""Where editable scenarios are kept, and what they may be called.

The name check is the load-bearing part. It is what keeps a store's writes
inside its own directory, and on the web build the names will arrive from
strangers, so it is tested as a boundary rather than as validation.
"""

import hashlib
import json

import pytest

from box2d_testbed.scenario_store import (
    BuiltinStore,
    BrowserSharedStore,
    ScenarioRef,
    SharedStore,
    StoreError,
    UserStore,
    template_for,
    user_scenario_dir,
    validate_name,
    configured_shared_store,
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


class _Response:
    """The small part of an urllib response SharedStore consumes."""

    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def read(self, limit=-1):
        return self.body if limit < 0 else self.body[:limit]


def sharing_server():
    """An in-process transport with the Worker's content-addressed contract."""
    saved = {}
    requests = []

    def open_request(request, timeout):
        requests.append((request, timeout))
        if request.get_method() == "POST":
            digest = hashlib.sha256(request.data).hexdigest()
            saved[digest] = request.data
            return _Response(json.dumps({"id": digest}).encode())
        digest = request.full_url.rsplit("/", 1)[-1]
        return _Response(saved[digest])

    return SharedStore("http://scenarios.test", opener=open_request), saved, requests


def test_a_shared_store_publishes_and_reads_by_the_complete_hash():
    store, saved, requests = sharing_server()
    source = "# snowman: ☃\n"
    expected = hashlib.sha256(source.encode()).hexdigest()

    ref = store.publish(source)

    assert ref.name == expected
    assert ref.label == f"shared/{expected}.py"
    assert not ref.writable
    assert ref.runnable
    assert ref.load_name == f"shared_{expected[:56]}"
    assert store.fork_stem(ref.name) == f"shared_{expected[:12]}"
    assert store.url_for(ref.name) == f"http://scenarios.test/s/{expected}"
    assert saved == {expected: source.encode()}
    assert requests[0][0].get_method() == "POST"
    assert requests[0][1] == 5.0
    assert ref.read() == source
    assert requests[-1][0].get_method() == "GET"


def test_shared_hashes_and_links_resolve_to_the_same_remembered_ref():
    store, _, _ = sharing_server()
    digest = "a" * 64

    by_hash = store.reference(digest)
    by_link = store.reference(f"http://scenarios.test/s/{digest}?from=friend")

    assert by_hash == by_link
    assert store.names() == [digest], "the session picker does not duplicate it"


@pytest.mark.parametrize(
    "reference",
    [
        "",
        "abcd",
        "g" * 64,
        "http://somewhere-else.test/s/" + "a" * 64,
        "http://scenarios.test/not-s/" + "a" * 64,
        "http://scenarios.test/s/" + "a" * 64 + "/more",
    ],
)
def test_a_shared_reference_must_be_a_hash_or_a_link_from_our_server(reference):
    store, _, _ = sharing_server()

    with pytest.raises(StoreError):
        store.reference(reference)


def test_downloaded_content_is_verified_against_its_address():
    digest = hashlib.sha256(b"the promised source").hexdigest()
    store = SharedStore(
        "http://scenarios.test",
        opener=lambda request, timeout: _Response(b"something else"),
    )

    with pytest.raises(StoreError, match="does not match"):
        store.read(digest)


def test_the_client_enforces_the_servers_size_limit_before_connecting():
    called = False

    def should_not_open(request, timeout):
        nonlocal called
        called = True

    store = SharedStore("http://scenarios.test", opener=should_not_open)

    with pytest.raises(StoreError, match="65536"):
        store.publish("x" * (64 * 1024 + 1))
    assert not called


def test_the_server_url_can_be_configured_for_the_desktop_app(monkeypatch):
    monkeypatch.setenv("BOX2D_TESTBED_SERVER", "https://share.example.test/")

    store = SharedStore()

    assert store.base_url == "https://share.example.test"


def test_sharing_is_off_by_default_and_each_runtime_opts_into_its_transport(
    monkeypatch,
):
    monkeypatch.delenv("BOX2D_TESTBED_SHARING", raising=False)
    assert configured_shared_store() is None

    monkeypatch.setenv("BOX2D_TESTBED_SHARING", "desktop")
    assert type(configured_shared_store()) is SharedStore

    monkeypatch.setenv("BOX2D_TESTBED_SHARING", "web")
    assert type(configured_shared_store()) is BrowserSharedStore


def test_the_browser_store_uses_its_async_transport_for_both_directions():
    source = "# fetched without blocking wasm\n"
    body = source.encode()
    digest = hashlib.sha256(body).hexdigest()
    calls = []
    store = BrowserSharedStore("https://scenarios.test")

    async def fetch(url, *, method, response_limit, body=None):
        calls.append((url, method, response_limit, body))
        if method == "POST":
            return json.dumps({"id": digest}).encode()
        return source.encode()

    store._fetch = fetch

    async def round_trip():
        ref = await store.publish_async(source)
        return ref, await store.read_async(ref.name)

    # The fake transport never yields. Drive this immediate coroutine directly
    # so the same test works in Pyodide, whose browser event loop deliberately
    # cannot implement blocking asyncio.run().
    operation = round_trip()
    try:
        operation.send(None)
    except StopIteration as completed:
        ref, loaded = completed.value
    else:  # pragma: no cover - means the fake unexpectedly became asynchronous
        operation.close()
        raise AssertionError("the fake browser transport unexpectedly yielded")

    assert ref.name == digest
    assert loaded == source
    assert calls == [
        ("https://scenarios.test/s", "POST", 8 * 1024, source),
        (f"https://scenarios.test/s/{digest}", "GET", 64 * 1024, None),
    ]
