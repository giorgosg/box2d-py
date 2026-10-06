#!/usr/bin/env python
"""The parts of the build pyproject.toml cannot express: the C libraries and
the CFFI extension. Both come from src/tools/build_cffi.py."""

import os
import sys

import setuptools
from setuptools.command.build_ext import build_ext

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "tools")
)
import build_cffi  # noqa: E402


class BuildExtWithDeps(build_ext):
    """Build Box2D and enkiTS with CMake before the extension that links them."""

    def run(self):
        build_cffi.build_dependencies()
        super().run()


options = {}
if not build_cffi.EMSCRIPTEN:
    # cffi compiles against the stable ABI, so one wheel serves every CPython
    # from 3.12 on. Pyodide resolves its wheels by their own tag, so the
    # WebAssembly build keeps the version-specific one.
    options["bdist_wheel"] = {"py_limited_api": "cp312"}

setuptools.setup(
    # Metadata is in pyproject.toml.
    cffi_modules=["src/tools/build_cffi.py:ffibuilder"],
    cmdclass={"build_ext": BuildExtWithDeps},
    options=options,
)
