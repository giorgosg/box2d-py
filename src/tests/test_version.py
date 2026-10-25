# tests/test_version.py
"""box2d.__version__ is the installed package's version."""

import runpy
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import pytest

import box2d
from box2d._version import UNKNOWN, find_version


def test_version_is_what_find_version_reports():
    assert box2d.__version__ == find_version()


def test_version_is_the_installed_distributions():
    try:
        installed = version("box2d-python")
    except PackageNotFoundError:
        pytest.skip("box2d-python is not installed; imported from a source tree")
    assert box2d.__version__ == installed


def test_version_is_a_string_even_when_not_installed():
    """Imported from a source tree nobody installed, there is no metadata to
    read. The import must still work, and say the version is unknown."""
    assert find_version("no-such-distribution-box2d") == UNKNOWN == "0+unknown"


@pytest.mark.parametrize(
    "installed, short",
    [("0.2.0", "0.2"), ("3.2.0rc1", "3.2"), ("3.2.0", "3.2"), ("3.2.0.1", "3.2")],
)
def test_the_docs_report_the_packages_version(monkeypatch, installed, short):
    """The docs take their version from the package rather than keeping their
    own, so the two cannot drift apart."""
    monkeypatch.setattr(box2d, "__version__", installed)
    conf = Path(__file__).resolve().parents[2] / "docs" / "source" / "conf.py"
    settings = runpy.run_path(str(conf))
    assert settings["release"] == installed
    assert settings["version"] == short
