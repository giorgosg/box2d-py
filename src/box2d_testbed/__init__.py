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

from .testbed import main  # noqa: E402

__all__ = ["main"]
