"""
Builds the box2d._box2d CFFI extension.

setup.py uses two things from here, and importing the module does nothing else:

- ``build_dependencies()``, which build_ext runs first: Box2D compiled as a
  static library with CMake;
- ``ffibuilder()``, which cffi calls for the FFI: the declarations read from
  Box2D's public headers, and how to link the library.

Nothing here needs a particular compiler: the headers are preprocessed in
Python with pcpp, so a Windows build needs only Visual Studio and CMake.

Threads need nothing from this build either. Box2D 3.2 has its own thread
pool, one per world, so the extension is just Box2D. The one other shape of
build is WebAssembly, cross-compiled by pyodide build, where Box2D is built
without threads because the browser runtime has none to give.
"""

import io
import os
import platform
import re
import subprocess
import sysconfig

from cffi import FFI

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BOX2D_DIR = os.path.join(PROJECT_ROOT, "box2d")


def _targeting_emscripten():
    """Whether this build is cross-compiling to WebAssembly.

    pyodide build sets PYODIDE=1 and points the compiler at emcc; either is
    enough to tell, and BOX2D_PY_EMSCRIPTEN forces it for testing the path
    by hand.
    """
    if os.environ.get("BOX2D_PY_EMSCRIPTEN"):
        return True
    if os.environ.get("PYODIDE") == "1":
        return True
    return "emcc" in os.environ.get("CC", "")


EMSCRIPTEN = _targeting_emscripten()


# --- the C libraries ----------------------------------------------------------


def _target_name():
    """A directory name for the platform being built for.

    CMake trees are kept per target, so a native build and a WebAssembly one,
    or two macOS architectures, never share a CMake cache.
    sysconfig.get_platform() follows _PYTHON_HOST_PLATFORM, which is how
    cibuildwheel announces a cross-compile.
    """
    if EMSCRIPTEN:
        return "emscripten"
    return re.sub(r"[^\w.-]", "_", sysconfig.get_platform())


def _cmake_dir(*parts):
    return os.path.join(PROJECT_ROOT, "build", "cmake", _target_name(), *parts)


#: Where the static library lands, whatever the generator.
LIBRARY_DIR = _cmake_dir("lib")


def _macos_architectures():
    """The architectures to build for on macOS, from cibuildwheel's ARCHFLAGS.

    Without this CMake builds for the machine it runs on, and an x86_64 wheel
    cross-compiled on Apple silicon links arm64 libraries -- which fails.
    """
    return re.findall(r"-arch\s+(\S+)", os.environ.get("ARCHFLAGS", ""))


def _cmake_args():
    """CMake configure arguments for the target being built."""
    args = [
        "-DCMAKE_BUILD_TYPE=Release",
        "-DBUILD_SHARED_LIBS=OFF",
        "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
        # A Visual Studio generator puts Release builds in a Release
        # subdirectory, so the per-config variable is the one that counts.
        f"-DCMAKE_ARCHIVE_OUTPUT_DIRECTORY={LIBRARY_DIR}",
        f"-DCMAKE_ARCHIVE_OUTPUT_DIRECTORY_RELEASE={LIBRARY_DIR}",
    ]
    if EMSCRIPTEN:
        args.append(f"-DCMAKE_TOOLCHAIN_FILE={_emscripten_toolchain_file()}")
        # Box2D has to be compiled with the same flags as the extension that
        # links it -- wasm exceptions and longjmp support in particular, since
        # mixing those is a link error rather than a warning.
        args.append(f"-DCMAKE_C_FLAGS={os.environ.get('CFLAGS_BASE', '')}")
    elif platform.system() == "Darwin":
        architectures = _macos_architectures()
        if architectures:
            args.append(f"-DCMAKE_OSX_ARCHITECTURES={';'.join(architectures)}")
        if os.environ.get("MACOSX_DEPLOYMENT_TARGET"):
            target = os.environ["MACOSX_DEPLOYMENT_TARGET"]
            args.append(f"-DCMAKE_OSX_DEPLOYMENT_TARGET={target}")
    # The Visual Studio generator is left to CMake, which picks the newest
    # installed: pinning one broke the build when GitHub's image moved on. Its
    # default runtime is the release DLL one (/MD), which the extension uses
    # too, so that needs no flag either.
    return args


def _emscripten_toolchain_file():
    """The Emscripten CMake toolchain, from the environment pyodide exports.

    Read from the environment rather than by importing pyodide_build: the
    wheel is built in an isolated PEP 517 environment holding only what
    build-system.requires names, and pyodide_build is not among them.
    """
    toolchain = os.environ.get("CMAKE_TOOLCHAIN_FILE", "")
    if not toolchain or not os.path.exists(toolchain):
        raise RuntimeError(
            "cross-compiling to Emscripten but CMAKE_TOOLCHAIN_FILE is not set "
            "to an existing file. Build through `pyodide build`, which exports "
            "it, after `pyodide xbuildenv install`."
        )
    return toolchain


def _cmake(source_dir, name, extra_args):
    """Configure and build one project. Both steps are incremental."""
    build_dir = _cmake_dir(name)
    subprocess.run(
        ["cmake", "-S", source_dir, "-B", build_dir, *_cmake_args(), *extra_args],
        check=True,
    )
    subprocess.run(
        ["cmake", "--build", build_dir, "--config", "Release", "--parallel"],
        check=True,
    )


def build_dependencies():
    """Build Box2D as a static library."""
    print(f"Building Box2D in {_cmake_dir('box2d')}")
    _cmake(
        BOX2D_DIR,
        "box2d",
        [
            "-DBOX2D_SAMPLES=OFF",
            "-DBOX2D_UNIT_TESTS=OFF",
            "-DBOX2D_BENCHMARKS=OFF",
            "-DBOX2D_DOCS=OFF",
        ],
    )


# --- the declarations -----------------------------------------------------------


def strip_inline_definitions(text):
    """Remove inline function definitions, which cdef() cannot parse.

    cdef() accepts declarations only, so any function carrying a body has to go.
    After preprocessing every Box2D inline -- B2_INLINE, B2_ID_INLINE,
    B2_FORCE_INLINE -- starts with 'static inline'. Their bodies contain brace
    initializers such as ``b2WorldId id = { ... };``, so this counts braces
    rather than matching a pattern, which cannot handle the nesting.
    """
    lines = text.splitlines(keepends=True)
    kept = []
    i = 0
    while i < len(lines):
        if not lines[i].lstrip().startswith("static inline"):
            kept.append(lines[i])
            i += 1
            continue

        # Consume the signature and its body, balancing braces.
        depth = 0
        seen_brace = False
        while i < len(lines):
            depth += lines[i].count("{") - lines[i].count("}")
            seen_brace = seen_brace or "{" in lines[i]
            i += 1
            if seen_brace and depth <= 0:
                break
    return "".join(kept)


def _preprocess_box2d_headers():
    """box2d.h with its own includes expanded and its macros applied.

    pcpp is a C preprocessor written in Python, which is what keeps the build
    free of any particular compiler. System headers are skipped rather than
    expanded: cdef() knows stdint.h's types already, and could not parse a
    libc's headers anyway.
    """
    import pcpp

    class Preprocessor(pcpp.Preprocessor):
        def on_include_not_found(self, is_malformed, is_system, curdir, path):
            raise pcpp.OutputDirective(pcpp.Action.IgnoreAndRemove)

        def on_comment(self, token):
            return False

    preprocessor = Preprocessor()
    preprocessor.line_directive = None
    preprocessor.add_path(os.path.join(BOX2D_DIR, "include"))
    # The library is a static release build: no export decoration, and no
    # assertions, so b2InternalAssert -- declared only when they are on -- is
    # not in it to be declared.
    preprocessor.define("BOX2D_EXPORT")
    preprocessor.define("NDEBUG")
    preprocessor.parse('#include "box2d/box2d.h"\n', "<box2d-py>")

    output = io.StringIO()
    preprocessor.write(output)
    if preprocessor.return_code:
        raise RuntimeError("preprocessing Box2D's headers failed")
    return output.getvalue()


def cdef_source():
    """Everything the extension declares to cffi: Box2D's public API."""
    text = strip_inline_definitions(_preprocess_box2d_headers())
    # Pragmas and the like are left by the preprocessor; cdef() wants none.
    return "\n".join(line for line in text.splitlines() if not line.startswith("#"))


# --- the extension --------------------------------------------------------------


def link_config():
    """The libraries the extension links, and where they are."""
    libraries = ["box2d"]
    # Box2D's thread pool is POSIX threads outside Windows. macOS has them in
    # its C library; on Linux, glibc before 2.34 -- which manylinux2014 is --
    # keeps them in libpthread. WebAssembly is built without them.
    if not EMSCRIPTEN and platform.system() not in ("Windows", "Darwin"):
        libraries.append("pthread")
    return {"libraries": libraries, "library_dirs": [LIBRARY_DIR]}


def ffibuilder():
    """The FFI for box2d._box2d. cffi's setuptools hook calls this."""
    ffi = FFI()
    ffi.cdef(cdef_source())
    ffi.set_source(
        "box2d._box2d",
        '#include "box2d/box2d.h"\n',
        include_dirs=[os.path.join(BOX2D_DIR, "include")],
        **link_config(),
    )
    return ffi
