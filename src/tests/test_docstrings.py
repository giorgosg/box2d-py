# test_docstrings.py
import doctest
import box2d.vec2
from box2d import math

# Run the tests
doctest.testmod(math, verbose=False)
