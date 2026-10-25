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


@pytest.fixture
def process_state_left_alone(monkeypatch):
    """Examples that touch process-wide state touch a copy of it.

    The collision_filter examples name categories in the default registry,
    whose bits depend on what named categories before them -- a testbed
    scenario run earlier had already taken "player". They get a fresh one.
    BodyBuilder.extend's example adds a method to BodyBuilder, which is taken
    off again.
    """
    from box2d import BodyBuilder, collision_filter

    monkeypatch.setattr(
        collision_filter,
        "DEFAULT_CATEGORY_REGISTRY",
        collision_filter.CollisionCategoryRegistry(auto_create=True),
    )
    before = set(vars(BodyBuilder))
    yield
    for added in set(vars(BodyBuilder)) - before:
        delattr(BodyBuilder, added)


@pytest.mark.parametrize("name", MODULES)
@pytest.mark.usefixtures("process_state_left_alone")
def test_docstring_examples(name):
    results = doctest.testmod(importlib.import_module(name))
    assert results.failed == 0, f"{results.failed} example(s) failed in {name}"
