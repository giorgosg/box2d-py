# tests/test_math.py
import pytest
import doctest
import math
from box2d import shape_def


def test_doctests():
    # Run doctests for the specific submodule
    results = doctest.testmod(shape_def)
    assert results.failed == 0
