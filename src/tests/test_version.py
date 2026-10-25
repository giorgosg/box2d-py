# tests/test_version.py
"""box2d.__version__ is the installed package's version."""

from importlib.metadata import version

import box2d
from box2d._version import find_version


def test_version_is_the_installed_distributions():
    assert box2d.__version__ == version("box2d-python")


def test_version_is_a_string_even_when_not_installed():
    """Imported from a source tree nobody installed, there is no metadata to
    read. The import must still work, and say the version is unknown."""
    assert find_version("no-such-distribution-box2d") == "0+unknown"
