# tests/test_build_config.py
"""How the extension decides what to build.

The build has two shapes -- native, and cross-compiled to WebAssembly -- and
which one you get is decided by environment variables read when the build
script is imported. That is easy to get subtly wrong
in a way no other test would notice, because the wrong choice still produces
a working extension, just not the one you asked for.

These import the build script fresh under each environment and check what it
decided. They do not build anything, and importing the script must not either.
"""

import importlib
import os
import platform
import sys

import pytest

BUILD_TOOLS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"
)


def load_build_module(environment):
    """Import build_cffi with a given environment, fresh each time.

    The decisions are module-level constants, so the module has to be
    reimported rather than reloaded with the old values still bound.
    """
    saved = {
        key: os.environ.get(key) for key in ("BOX2D_PY_EMSCRIPTEN", "PYODIDE", "CC")
    }
    for key in saved:
        os.environ.pop(key, None)
    os.environ.update(environment)

    if BUILD_TOOLS not in sys.path:
        sys.path.insert(0, BUILD_TOOLS)
    sys.modules.pop("build_cffi", None)
    try:
        return importlib.import_module("build_cffi")
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        sys.modules.pop("build_cffi", None)


@pytest.fixture(autouse=True)
def _restore_build_module():
    """Leave no imported build_cffi behind, whichever way a test ends."""
    yield
    sys.modules.pop("build_cffi", None)


def test_a_plain_build_is_native():
    assert load_build_module({}).EMSCRIPTEN is False


@pytest.mark.parametrize(
    "environment",
    [
        {"PYODIDE": "1"},
        {"CC": "emcc"},
        {"CC": "/some/path/to/emcc"},
        {"BOX2D_PY_EMSCRIPTEN": "1"},
    ],
    ids=["pyodide-env", "cc-emcc", "cc-emcc-path", "forced"],
)
def test_emscripten_is_detected(environment):
    """pyodide build announces itself in more than one way."""
    build = load_build_module(environment)
    assert build.EMSCRIPTEN is True


def test_the_extension_links_only_box2d():
    """Box2D 3.2 runs its own thread pool, so there is no scheduler to link.

    Linux adds pthread for that pool; glibc before 2.34, which manylinux2014
    is, keeps it out of libc.
    """
    config = load_build_module({}).link_config()
    expected = ["box2d"]
    if platform.system() not in ("Windows", "Darwin"):
        expected.append("pthread")
    assert config["libraries"] == expected


def test_a_webassembly_build_links_no_threads():
    """Box2D is built without threads there, so pthread is not wanted."""
    config = load_build_module({"BOX2D_PY_EMSCRIPTEN": "1"}).link_config()
    assert config["libraries"] == ["box2d"]


def test_the_declarations_are_box2ds_api():
    headers = load_build_module({}).cdef_source()
    assert "b2CreateWorld" in headers
    assert "b2World_Step" in headers
    # The enkiTS glue that used to be declared alongside is gone.
    assert "setup_threadpool" not in headers


def test_has_threads_everywhere_but_webassembly():
    from box2d import HAS_THREADS

    assert HAS_THREADS is (sys.platform != "emscripten")


def test_importing_the_build_script_builds_nothing(tmp_path, monkeypatch):
    """setup.py imports it for every command, metadata included.

    It used to preprocess the headers and compile C with gcc as a side effect
    of being imported.
    """
    import subprocess

    calls = []
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: calls.append(a))
    build = load_build_module({})
    assert calls == []
    assert callable(build.ffibuilder)


def test_cdef_has_no_assert_hook():
    """The library is a release build, so b2InternalAssert is not in it.

    The headers declare it only when assertions are on; declaring it here
    would make the extension reference a symbol the library does not have.
    """
    headers = load_build_module({}).cdef_source()
    assert "b2InternalAssert" not in headers
    assert "b2GetTicks" in headers


def test_cmake_trees_are_kept_per_target():
    """A native and a WebAssembly build must not share a CMake cache."""
    native = load_build_module({})
    wasm = load_build_module({"BOX2D_PY_EMSCRIPTEN": "1"})
    assert native.LIBRARY_DIR != wasm.LIBRARY_DIR
    assert "emscripten" in wasm.LIBRARY_DIR


def test_macos_architectures_come_from_archflags(monkeypatch):
    build = load_build_module({})
    monkeypatch.setenv("ARCHFLAGS", "-arch x86_64 -arch arm64")
    assert build._macos_architectures() == ["x86_64", "arm64"]
    monkeypatch.setenv("ARCHFLAGS", "")
    assert build._macos_architectures() == []
