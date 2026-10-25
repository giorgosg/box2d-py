# tests/test_doctests.py
"""Every example in the box2d package's docstrings runs and shows what it says.

This used to be a test_doctests in five of the test files, one per module, so
the other modules' examples never ran and two of them had stopped working.
Each example has to stand on its own, importing what it uses, as a reader
copying it would have to.
"""

import doctest
import importlib
import pkgutil

import pytest

import box2d

MODULES = ["box2d"] + sorted(
    module.name for module in pkgutil.walk_packages(box2d.__path__, "box2d.")
)


def test_every_module_is_found():
    assert {"box2d.world", "box2d.shape", "box2d.mover"} <= set(MODULES)


@pytest.mark.parametrize("name", MODULES)
def test_docstring_examples(name):
    results = doctest.testmod(importlib.import_module(name))
    assert results.failed == 0, f"{results.failed} example(s) failed in {name}"
