#!/usr/bin/env python
import os
import sys
import setuptools
from setuptools.command.build_ext import build_ext

# Add the src/tools directory to the path so we can import build_cffi
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src", "tools"))
from build_cffi import build_dependencies


class BuildExtWithDeps(build_ext):
    """Custom build_ext command that builds C++ dependencies first"""

    def run(self):
        # Build Box2D and enkiTS first
        print("Building Box2D and enkiTS dependencies...")
        build_dependencies()

        # Then run the regular build_ext command
        super().run()


setuptools.setup(
    # Note: metadata is already specified in pyproject.toml.
    cffi_modules=["src/tools/build_cffi.py:ffibuilder"],
    cmdclass={
        "build_ext": BuildExtWithDeps,
    },
)
