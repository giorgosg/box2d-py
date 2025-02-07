# test_docstrings.py
import doctest
from box2d import vec2
import box2d.vec2

# Run the tests
doctest.testmod(vec2, verbose=True)
