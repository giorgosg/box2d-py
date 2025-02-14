import os
import sys

sys.path.insert(0, os.path.abspath("src"))

from setuptools import setup, find_packages

setup(
    use_scm_version={"local_scheme": "no-local-version"},
    package_dir={"": "src"},
    cffi_modules=["src/tools/build_cffi.py:ffibuilder"],
    packages=find_packages(where="src", include=["box2d*", "testbed*"]),
    extras_require={
        "testbed": ["dearpygui"],
        "test": ["pytest"],
    },
    entry_points={
        "console_scripts": [
            "box2d-testbed=testbed.testbed:main",
        ]
    },
)
