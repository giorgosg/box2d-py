"""
The view onto the world: where it is centred and how far it is zoomed.

Kept apart from any renderer. It was defined beside the OpenGL one, which
meant importing the camera pulled in PyOpenGL -- so the imgui renderer,
whose whole point is running where there is no GL, could not be imported
in a browser.
"""

import numpy as np

from box2d import Vec2


class Camera:
    def __init__(self):
        self.width = 1280
        self.height = 800
        self.reset_view()
        self._matrix = None

    def reset_view(self):
        """Reset camera to initial position and zoom"""
        self.center = Vec2(0.0, 0.0)
        self.zoom = 1.0
        self._matrix = None

    def set_view(self, center, zoom, width, height):
        """Set camera view parameters"""
        if (
            self.center != Vec2(*center)
            or self.zoom != zoom
            or self.width != width
            or self.height != height
        ):
            self.center = Vec2(*center)
            self.zoom = zoom
            self.width = width
            self.height = height
            self._matrix = None

    def convert_screen_to_world(self, ps):
        """Convert from screen coordinates to world coordinates"""
        w = float(self.width)
        h = float(self.height)
        u = ps.x / w
        v = (h - ps.y) / h

        ratio = w / h
        extents = Vec2(self.zoom * ratio, self.zoom)

        lower = self.center - extents
        upper = self.center + extents

        pw = Vec2((1.0 - u) * lower.x + u * upper.x, (1.0 - v) * lower.y + v * upper.y)
        return pw

    def convert_world_to_screen(self, pw):
        """Convert from world coordinates to screen coordinates"""
        w = float(self.width)
        h = float(self.height)
        ratio = w / h

        extents = Vec2(self.zoom * ratio, self.zoom)

        # Vec2 operations
        lower = self.center - extents
        upper = self.center + extents

        u = (pw.x - lower.x) / (upper.x - lower.x)
        v = (pw.y - lower.y) / (upper.y - lower.y)

        ps = Vec2(u * w, (1.0 - v) * h)
        return ps

    def build_projection_matrix(self, z_bias=0.0):
        """Build projection matrix for rendering"""
        if self._matrix is not None:
            return self._matrix
        ratio = float(self.width) / float(self.height)
        extents = Vec2(self.zoom * ratio, self.zoom)

        # Vec2 operations
        lower = self.center - extents
        upper = self.center + extents

        w = upper.x - lower.x
        h = upper.y - lower.y

        matrix = np.zeros(16, dtype=np.float32)

        # Column-major order
        matrix[0] = 2.0 / w
        matrix[5] = 2.0 / h
        matrix[10] = -1.0
        matrix[12] = -2.0 * self.center.x / w
        matrix[13] = -2.0 * self.center.y / h
        matrix[14] = z_bias
        matrix[15] = 1.0
        self._matrix = matrix
        return matrix
