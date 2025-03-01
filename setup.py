#!/usr/bin/env python
import setuptools

setuptools.setup(
    # Note: metadata is already specified in pyproject.toml.
    cffi_modules=["src/tools/build_cffi.py:ffibuilder"],
)
