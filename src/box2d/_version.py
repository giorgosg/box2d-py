"""The binding's own version, read from the installed package's metadata."""

from importlib.metadata import PackageNotFoundError, version

#: What __version__ says when there is no metadata to read.
UNKNOWN = "0+unknown"


def find_version(distribution: str = "box2d-python") -> str:
    """Return the installed version of ``distribution``.

    The version lives in one place, pyproject.toml, and reaches the package
    through the metadata installing it writes. An editable install reports
    the version it was installed at, until it is installed again.

    Returns:
        The version string, or ``"0+unknown"`` -- a valid PEP 440 version
        that sorts below any release -- when the package is imported from a
        source tree that was never installed.
    """
    try:
        return version(distribution)
    except PackageNotFoundError:
        return UNKNOWN
