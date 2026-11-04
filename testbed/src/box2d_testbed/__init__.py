"""Interactive testbed for box2d-py."""

import os

# Both of these have to be set before anything imports OpenGL.GL, so they live
# here rather than in the modules that care: PyOpenGL builds its wrappers at
# import time, and setting ERROR_CHECKING afterwards leaves the checked, much
# slower ones in place. They were previously set in two modules, both of which
# had already pulled in OpenGL.GL by then.
#
# Guarded because there is no PyOpenGL in a browser, and the imgui renderer
# does not need one. An unguarded import here made the whole package
# unimportable there, however lazy everything downstream was.
try:
    import OpenGL
except ImportError:  # pragma: no cover - depends on the platform
    OpenGL = None
else:
    OpenGL.ERROR_CHECKING = False

    if os.getenv("XDG_SESSION_TYPE") == "wayland" and not os.getenv(
        "PYOPENGL_PLATFORM"
    ):
        os.environ["PYOPENGL_PLATFORM"] = "x11"

__all__ = ["main"]


def __getattr__(name):
    """Import the app only when it is actually asked for.

    Importing it here pulled in imgui_bundle, so anything under this package
    needed the whole GUI stack installed -- including the scenarios and the
    human figure, which need neither. CI installs only the dev extra, so
    every testbed test failed to collect rather than running.
    """
    if name == "main":
        from .testbed import main

        return main
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
