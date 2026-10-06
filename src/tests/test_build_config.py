# tests/test_build_config.py
"""How the extension decides what to build.

The build has three shapes now -- native with threads, native without, and
cross-compiled to WebAssembly -- and which one you get is decided by
environment variables read when the build script is imported. That is easy to get subtly wrong
in a way no other test would notice, because the wrong choice still produces
a working extension, just not the one you asked for.

These import the build script fresh under each environment and check what it
decided. They do not build anything, and importing the script must not either.
"""

import importlib
import os
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
        key: os.environ.get(key)
        for key in ("BOX2D_PY_NO_THREADS", "BOX2D_PY_EMSCRIPTEN", "PYODIDE", "CC")
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


def test_a_plain_build_has_threads():
    build = load_build_module({})
    assert build.EMSCRIPTEN is False
    assert build.WITH_THREADS is True


def test_no_threads_is_opt_in():
    build = load_build_module({"BOX2D_PY_NO_THREADS": "1"})
    assert build.WITH_THREADS is False
    assert build.EMSCRIPTEN is False


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


def test_emscripten_implies_no_threads():
    """The reason the two are linked: wasm has no thread pool to give.

    Left unlinked, a wasm build would try to compile enkiTS and link a C++
    thread pool that cannot run there.
    """
    build = load_build_module({"PYODIDE": "1"})
    assert build.EMSCRIPTEN is True
    assert build.WITH_THREADS is False


def test_a_threadless_build_links_only_box2d():
    """No enkiTS, and no C++ runtime -- enkiTS was the only C++ in the build."""
    build = load_build_module({"BOX2D_PY_NO_THREADS": "1"})
    config = build.link_config()

    assert config["libraries"] == ["box2d"]


def test_a_threaded_build_links_the_scheduler():
    build = load_build_module({})
    config = build.link_config()

    assert "box2d" in config["libraries"]
    assert "enkiTS" in config["libraries"]


def test_the_scheduler_is_declared_only_when_it_is_built():
    """cffi must not promise symbols the extension does not carry.

    A cdef naming setup_threadpool in a build without it produces an
    extension whose import fails on a missing symbol, rather than a build
    that simply has no threads.
    """
    threaded = load_build_module({})
    headers = threaded.cdef_source()
    assert "setup_threadpool" in headers

    threadless = load_build_module({"BOX2D_PY_NO_THREADS": "1"})
    headers = threadless.cdef_source()
    assert "setup_threadpool" not in headers
    assert "c_enqueue_tasks" not in headers
    # The Box2D API is still all there.
    assert "b2CreateWorld" in headers
    assert "b2World_Step" in headers


def test_has_threads_matches_what_was_built():
    """The runtime flag should describe the extension actually loaded."""
    from box2d import HAS_THREADS
    from box2d._box2d import lib

    assert HAS_THREADS is hasattr(lib, "setup_threadpool")


def test_importing_the_build_script_builds_nothing(tmp_path, monkeypatch):
    """setup.py imports it for every command, metadata included.

    It used to preprocess the headers and compile the task scheduler with gcc
    as a side effect of being imported.
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
