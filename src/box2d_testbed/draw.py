import numpy as np
from OpenGL.GL import *
import math
import os
from box2d.math import Vec2, AABB, Transform, Rot
from .shader import create_program_from_files, create_program_from_strings
import OpenGL

OpenGL.ERROR_CHECKING = False


def make_rgba8(hex_color, alpha=255):
    """Convert hex color to RGBA8 in little-endian order (RGBA in memory)."""
    r = (hex_color >> 16) & 0xFF
    g = (hex_color >> 8) & 0xFF
    b = hex_color & 0xFF
    return (alpha << 24) | (b << 16) | (g << 8) | r


class GLBackground:
    def __init__(self, camera):
        """Initialize OpenGL resources for background rendering"""
        self.camera = camera  # Store camera reference
        self.vao_id = None
        self.vbo_id = None
        self.program_id = None
        self.time_uniform = None
        self.resolution_uniform = None
        self.base_color_uniform = None

        # Get the directory containing this file
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # Create shader paths relative to this file
        vertex_shader = os.path.join(current_dir, "shaders", "background.vs")
        fragment_shader = os.path.join(current_dir, "shaders", "background.fs")

        # Create and compile shaders
        self.program_id = create_program_from_files(vertex_shader, fragment_shader)

        # Get uniform locations
        self.time_uniform = glGetUniformLocation(self.program_id, "time")
        self.resolution_uniform = glGetUniformLocation(self.program_id, "resolution")
        self.base_color_uniform = glGetUniformLocation(self.program_id, "baseColor")

        # Generate vertex array and buffer
        self.vao_id = glGenVertexArrays(1)
        self.vbo_id = glGenBuffers(1)

        # Setup vertex attributes
        glBindVertexArray(self.vao_id)
        vertex_attribute = 0
        glEnableVertexAttribArray(vertex_attribute)

        # Define vertices using Vec2
        vertices = [
            Vec2(-1.0, 1.0),  # Top left
            Vec2(-1.0, -1.0),  # Bottom left
            Vec2(1.0, 1.0),  # Top right
            Vec2(1.0, -1.0),  # Bottom right
        ]

        # Convert Vec2 list to flat numpy array
        vertex_data = np.array(
            [(v.x, v.y) for v in vertices], dtype=np.float32
        ).flatten()

        # Upload vertex data
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_id)
        glBufferData(GL_ARRAY_BUFFER, vertex_data.nbytes, vertex_data, GL_STATIC_DRAW)
        glVertexAttribPointer(vertex_attribute, 2, GL_FLOAT, GL_FALSE, 0, None)

        # Cleanup
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

    def destroy(self):
        """Clean up OpenGL resources"""
        if self.vao_id:
            glDeleteVertexArrays(1, [self.vao_id])
            glDeleteBuffers(1, [self.vbo_id])
            self.vao_id = None
            self.vbo_id = None

        if self.program_id:
            glDeleteProgram(self.program_id)
            self.program_id = None

    def draw(self):
        """Draw the background"""
        glUseProgram(self.program_id)

        # Update uniforms
        import glfw

        time = glfw.get_time() % 100.0

        glUniform1f(self.time_uniform, time)
        # Use camera instance for resolution
        glUniform2f(
            self.resolution_uniform, float(self.camera.width), float(self.camera.height)
        )
        glUniform3f(self.base_color_uniform, 0.2, 0.2, 0.2)  # Gray background

        # Draw quad
        glBindVertexArray(self.vao_id)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_id)
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

        # Cleanup
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)
        glUseProgram(0)


class CircleData:
    """Storage class for circle instance data"""

    def __init__(self, position, radius, rgba):
        self.position = position  # Vec2
        self.radius = radius  # float
        self.size = np.array([position.x, position.y, radius, rgba], dtype=np.float32)


class GLCircles:
    def __init__(self, camera):
        self.camera = camera
        self.vao_id = None
        self.vbo_ids = [None, None]  # Need two buffers: vertices and instance data
        self.program_id = None
        self.projection_uniform = None
        self.pixel_scale_uniform = None
        self.circles = []

        # Get the directory containing this file
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # Create shader paths relative to this file
        vertex_shader = os.path.join(current_dir, "shaders", "circle.vs")
        fragment_shader = os.path.join(current_dir, "shaders", "circle.fs")

        self.program_id = create_program_from_files(vertex_shader, fragment_shader)
        self.projection_uniform = glGetUniformLocation(
            self.program_id, "projectionMatrix"
        )
        self.pixel_scale_uniform = glGetUniformLocation(self.program_id, "pixelScale")

        # Generate vertex array and buffers
        self.vao_id = glGenVertexArrays(1)
        self.vbo_ids = glGenBuffers(2)

        # Setup vertex attributes
        glBindVertexArray(self.vao_id)

        # Attribute locations
        vertex_attribute = 0
        position_instance = 1
        radius_instance = 2
        color_instance = 3

        glEnableVertexAttribArray(vertex_attribute)
        glEnableVertexAttribArray(position_instance)
        glEnableVertexAttribArray(radius_instance)
        glEnableVertexAttribArray(color_instance)

        # Vertex buffer for single quad
        a = 1.1
        vertices = np.array(
            [
                -a,
                -a,  # Bottom left
                a,
                -a,  # Bottom right
                -a,
                a,  # Top left
                a,
                -a,  # Bottom right
                a,
                a,  # Top right
                -a,
                a,  # Top left
            ],
            dtype=np.float32,
        )

        # Upload quad vertices
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_ids[0])
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        glVertexAttribPointer(vertex_attribute, 2, GL_FLOAT, GL_FALSE, 0, None)

        # Circle instance buffer
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_ids[1])
        glBufferData(
            GL_ARRAY_BUFFER, self.BATCH_SIZE * 16, None, GL_DYNAMIC_DRAW
        )  # 16 bytes per instance

        # Setup instance attributes
        stride = 16  # 4 floats * 4 bytes
        offset = 0
        glVertexAttribPointer(
            position_instance, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(offset)
        )
        offset += 8  # 2 floats * 4 bytes
        glVertexAttribPointer(
            radius_instance, 1, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(offset)
        )
        offset += 4  # 1 float * 4 bytes
        glVertexAttribPointer(
            color_instance,
            4,
            GL_UNSIGNED_BYTE,
            GL_TRUE,
            stride,
            ctypes.c_void_p(offset),
        )

        # Set attribute divisors for instancing
        glVertexAttribDivisor(position_instance, 1)
        glVertexAttribDivisor(radius_instance, 1)
        glVertexAttribDivisor(color_instance, 1)

        # Cleanup
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

    def destroy(self):
        """Clean up OpenGL resources"""
        if self.vao_id:
            glDeleteVertexArrays(1, [self.vao_id])
            glDeleteBuffers(2, self.vbo_ids)
            self.vao_id = None
            self.vbo_ids = [None, None]

        if self.program_id:
            glDeleteProgram(self.program_id)
            self.program_id = None

    def add_circle(self, center, radius, color):
        """Add circle for batch rendering"""
        rgba = make_rgba8(color)
        self.circles.append(CircleData(center, radius, rgba))

    def draw(self):
        """Render all circles in batch"""
        if not self.circles:
            return

        glUseProgram(self.program_id)

        # Update uniforms
        proj_matrix = self.camera.build_projection_matrix(0.2)
        glUniformMatrix4fv(self.projection_uniform, 1, GL_FALSE, proj_matrix)
        glUniform1f(self.pixel_scale_uniform, self.camera.height / self.camera.zoom)

        glBindVertexArray(self.vao_id)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_ids[1])

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Convert circles to numpy array for efficient upload
        instance_data = np.array([c.size for c in self.circles], dtype=np.float32)

        # Draw in batches if needed
        count = len(self.circles)
        base = 0
        while count > 0:
            batch_count = min(count, self.BATCH_SIZE)
            batch_data = instance_data[base : base + batch_count]

            glBufferSubData(GL_ARRAY_BUFFER, 0, batch_data.nbytes, batch_data)
            glDrawArraysInstanced(GL_TRIANGLES, 0, 6, batch_count)

            count -= self.BATCH_SIZE
            base += self.BATCH_SIZE

        glDisable(GL_BLEND)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)
        glUseProgram(0)

        self.circles.clear()

    BATCH_SIZE = 2048  # Maximum number of circles per batch


class SolidCircleData:
    """Storage class for solid circle instance data"""

    __slots__ = ["size"]

    def __init__(self, transform, radius, rgba):
        # Use a structured dtype where color is uint32.
        dtype = np.dtype(
            [
                ("p_x", np.float32),
                ("p_y", np.float32),
                ("q_s", np.float32),
                ("q_c", np.float32),
                ("radius", np.float32),
                ("color", np.uint32),
            ]
        )
        self.size = (
            np.array(
                [
                    (
                        transform.p.x,
                        transform.p.y,
                        transform.q.c,
                        transform.q.s,
                        radius,
                        rgba,
                    )
                ],
                dtype=dtype,
            )
            .view(np.float32)
            .reshape(-1)
        )


class GLSolidCircles:
    def __init__(self, camera):
        self.camera = camera
        self.vao_id = None
        self.vbo_ids = [None, None]  # Need two buffers: vertices and instance data
        self.program_id = None
        self.projection_uniform = None
        self.pixel_scale_uniform = None
        self.circles = []

        # Get the directory containing this file
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # Create shader paths relative to this file
        vertex_shader = os.path.join(current_dir, "shaders", "solid_circle.vs")
        fragment_shader = os.path.join(current_dir, "shaders", "solid_circle.fs")

        self.program_id = create_program_from_files(vertex_shader, fragment_shader)
        self.projection_uniform = glGetUniformLocation(
            self.program_id, "projectionMatrix"
        )
        self.pixel_scale_uniform = glGetUniformLocation(self.program_id, "pixelScale")

        # Generate vertex array and buffers
        self.vao_id = glGenVertexArrays(1)
        self.vbo_ids = glGenBuffers(2)

        # Setup vertex attributes
        glBindVertexArray(self.vao_id)

        # Attribute locations
        vertex_attribute = 0
        transform_instance = 1
        radius_instance = 2
        color_instance = 3

        glEnableVertexAttribArray(vertex_attribute)
        glEnableVertexAttribArray(transform_instance)
        glEnableVertexAttribArray(radius_instance)
        glEnableVertexAttribArray(color_instance)

        # Vertex buffer for single quad
        a = 1.1
        vertices = np.array(
            [
                -a,
                -a,  # Bottom left
                a,
                -a,  # Bottom right
                -a,
                a,  # Top left
                a,
                -a,  # Bottom right
                a,
                a,  # Top right
                -a,
                a,  # Top left
            ],
            dtype=np.float32,
        )

        # Upload quad vertices
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_ids[0])
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        glVertexAttribPointer(vertex_attribute, 2, GL_FLOAT, GL_FALSE, 0, None)

        # Circle instance buffer
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_ids[1])
        glBufferData(
            GL_ARRAY_BUFFER, self.BATCH_SIZE * 24, None, GL_DYNAMIC_DRAW
        )  # 24 bytes per instance

        # Setup instance attributes
        stride = 24  # 6 floats * 4 bytes
        offset = 0
        glVertexAttribPointer(
            transform_instance, 4, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(offset)
        )
        offset += 16  # 4 floats * 4 bytes
        glVertexAttribPointer(
            radius_instance, 1, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(offset)
        )
        offset += 4  # 1 float * 4 bytes
        glVertexAttribPointer(
            color_instance,
            4,
            GL_UNSIGNED_BYTE,
            GL_TRUE,
            stride,
            ctypes.c_void_p(offset),
        )

        # Set attribute divisors for instancing
        glVertexAttribDivisor(transform_instance, 1)
        glVertexAttribDivisor(radius_instance, 1)
        glVertexAttribDivisor(color_instance, 1)

        # Cleanup
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

    def destroy(self):
        """Clean up OpenGL resources"""
        if self.vao_id:
            glDeleteVertexArrays(1, [self.vao_id])
            glDeleteBuffers(2, self.vbo_ids)
            self.vao_id = None
            self.vbo_ids = [None, None]

        if self.program_id:
            glDeleteProgram(self.program_id)
            self.program_id = None

    def add_circle(self, transform, radius, color):
        """Add solid circle for batch rendering"""
        rgba = make_rgba8(color)
        self.circles.append(SolidCircleData(transform, radius, rgba))

    def draw(self):
        """Render all solid circles in batch"""
        if not self.circles:
            return

        glUseProgram(self.program_id)

        # Update uniforms
        proj_matrix = self.camera.build_projection_matrix(0.2)
        glUniformMatrix4fv(self.projection_uniform, 1, GL_FALSE, proj_matrix)
        glUniform1f(self.pixel_scale_uniform, self.camera.height / self.camera.zoom)

        glBindVertexArray(self.vao_id)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_ids[1])

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Convert circles to numpy array for efficient upload
        instance_data = np.array([c.size for c in self.circles], dtype=np.float32)

        # Draw in batches if needed
        count = len(self.circles)
        base = 0
        while count > 0:
            batch_count = min(count, self.BATCH_SIZE)
            batch_data = instance_data[base : base + batch_count]

            glBufferSubData(GL_ARRAY_BUFFER, 0, batch_data.nbytes, batch_data)
            glDrawArraysInstanced(GL_TRIANGLES, 0, 6, batch_count)

            count -= self.BATCH_SIZE
            base += self.BATCH_SIZE

        glDisable(GL_BLEND)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)
        glUseProgram(0)

        self.circles.clear()

    BATCH_SIZE = 2048  # Maximum number of circles per batch


class CapsuleData:
    """Storage class for capsule instance data"""

    def __init__(self, transform, radius, length, rgba):
        dtype = np.dtype(
            [
                ("t0", np.float32),
                ("t1", np.float32),
                ("t2", np.float32),
                ("t3", np.float32),
                ("radius", np.float32),
                ("length", np.float32),
                ("color", np.uint32),
            ]
        )
        self.size = (
            np.array(
                [
                    (
                        transform[0],
                        transform[1],
                        transform[2],
                        transform[3],
                        radius,
                        length,
                        rgba,
                    )
                ],
                dtype=dtype,
            )
            .view(np.float32)
            .reshape(-1)
        )


class GLSolidCapsules:
    def __init__(self, camera):
        self.camera = camera
        self.vao_id = None
        self.vbo_ids = [None, None]
        self.program_id = None
        self.projection_uniform = None
        self.pixel_scale_uniform = None
        self.capsules = []

        current_dir = os.path.dirname(os.path.abspath(__file__))
        vertex_shader = os.path.join(current_dir, "shaders", "solid_capsule.vs")
        fragment_shader = os.path.join(current_dir, "shaders", "solid_capsule.fs")

        self.program_id = create_program_from_files(vertex_shader, fragment_shader)
        self.projection_uniform = glGetUniformLocation(
            self.program_id, "projectionMatrix"
        )
        self.pixel_scale_uniform = glGetUniformLocation(self.program_id, "pixelScale")

        self.vao_id = glGenVertexArrays(1)
        self.vbo_ids = glGenBuffers(2)

        glBindVertexArray(self.vao_id)

        vertex_attribute = 0
        transform_instance = 1
        radius_instance = 2
        length_instance = 3
        color_instance = 4

        glEnableVertexAttribArray(vertex_attribute)
        glEnableVertexAttribArray(transform_instance)
        glEnableVertexAttribArray(radius_instance)
        glEnableVertexAttribArray(length_instance)
        glEnableVertexAttribArray(color_instance)

        # Vertex buffer for single quad
        a = 1.1
        vertices = np.array(
            [
                -a,
                -a,  # Bottom left
                a,
                -a,  # Bottom right
                -a,
                a,  # Top left
                a,
                -a,  # Bottom right
                a,
                a,  # Top right
                -a,
                a,  # Top left
            ],
            dtype=np.float32,
        )

        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_ids[0])
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        glVertexAttribPointer(vertex_attribute, 2, GL_FLOAT, GL_FALSE, 0, None)

        # Capsule instance buffer
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_ids[1])
        glBufferData(
            GL_ARRAY_BUFFER, self.BATCH_SIZE * 28, None, GL_DYNAMIC_DRAW
        )  # 28 bytes per instance

        # Setup instance attributes
        stride = 28  # 7 floats * 4 bytes
        offset = 0
        glVertexAttribPointer(
            transform_instance, 4, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(offset)
        )
        offset += 16  # 4 floats * 4 bytes
        glVertexAttribPointer(
            radius_instance, 1, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(offset)
        )
        offset += 4  # 1 float * 4 bytes
        glVertexAttribPointer(
            length_instance, 1, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(offset)
        )
        offset += 4  # 1 float * 4 bytes
        glVertexAttribPointer(
            color_instance,
            4,
            GL_UNSIGNED_BYTE,
            GL_TRUE,
            stride,
            ctypes.c_void_p(offset),
        )

        # Set attribute divisors for instancing
        glVertexAttribDivisor(transform_instance, 1)
        glVertexAttribDivisor(radius_instance, 1)
        glVertexAttribDivisor(length_instance, 1)
        glVertexAttribDivisor(color_instance, 1)

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

    def destroy(self):
        """Clean up OpenGL resources"""
        if self.vao_id:
            glDeleteVertexArrays(1, [self.vao_id])
            glDeleteBuffers(2, self.vbo_ids)
            self.vao_id = None
            self.vbo_ids = [None, None]

        if self.program_id:
            glDeleteProgram(self.program_id)
            self.program_id = None

    def add_capsule(self, p1, p2, radius, color):
        """Add capsule for batch rendering"""
        d = p2 - p1
        length = np.sqrt(d.x * d.x + d.y * d.y)
        if length < 0.001:
            print("WARNING: sample app: capsule too short!")
            return

        axis = d / length
        center = 0.5 * (p1 + p2)
        transform = (center.x, center.y, axis.x, axis.y)

        rgba = make_rgba8(color)
        self.capsules.append(CapsuleData(transform, radius, length, rgba))

    def draw(self):
        """Render all capsules in batch"""
        if not self.capsules:
            return

        glUseProgram(self.program_id)

        # Update uniforms
        proj_matrix = self.camera.build_projection_matrix(0.2)
        glUniformMatrix4fv(self.projection_uniform, 1, GL_FALSE, proj_matrix)
        glUniform1f(self.pixel_scale_uniform, self.camera.height / self.camera.zoom)

        glBindVertexArray(self.vao_id)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_ids[1])

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Convert capsules to numpy array for efficient upload
        instance_data = np.array([c.size for c in self.capsules], dtype=np.float32)

        # Draw in batches if needed
        count = len(self.capsules)
        base = 0
        while count > 0:
            batch_count = min(count, self.BATCH_SIZE)
            batch_data = instance_data[base : base + batch_count]

            glBufferSubData(GL_ARRAY_BUFFER, 0, batch_data.nbytes, batch_data)
            glDrawArraysInstanced(GL_TRIANGLES, 0, 6, batch_count)

            count -= self.BATCH_SIZE
            base += self.BATCH_SIZE

        glDisable(GL_BLEND)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)
        glUseProgram(0)

        self.capsules.clear()

    BATCH_SIZE = 2048  # Maximum number of capsules per batch


# Define a structured dtype for the instance data.
# Total size = 4*4 (transform) + 16*4 (points) + 4 (count) + 4 (radius) + 4 (color) = 92 bytes.
polygon_dtype = np.dtype(
    [
        ("transform", np.float32, 4),  # transform: p.x, p.y, q.c, q.s
        ("points", np.float32, 16),  # 8 points * 2 components each
        ("count", np.int32),  # integer count
        ("radius", np.float32),
        ("color", np.uint32),
    ]
)


class GLSolidPolygons:
    BATCH_SIZE = 512  # Maximum number of polygons per batch

    def __init__(self, camera):
        self.camera = camera
        # Preallocate buffers using the structured dtype.
        self.instance_buffers = []  # Full batches filled this frame.
        self.free_buffers = []  # Buffers available for reuse.
        self.current_buffer = np.empty(self.BATCH_SIZE, dtype=polygon_dtype)
        self.polygons_count = 0

        current_dir = os.path.dirname(os.path.abspath(__file__))
        vertex_shader = os.path.join(current_dir, "shaders", "solid_polygon.vs")
        fragment_shader = os.path.join(current_dir, "shaders", "solid_polygon.fs")

        self.program_id = create_program_from_files(vertex_shader, fragment_shader)
        self.projection_uniform = glGetUniformLocation(
            self.program_id, "projectionMatrix"
        )
        self.pixel_scale_uniform = glGetUniformLocation(self.program_id, "pixelScale")

        self.vao_id = glGenVertexArrays(1)
        self.vbo_ids = glGenBuffers(2)

        glBindVertexArray(self.vao_id)
        vertex_attribute = 0
        instance_transform = 1
        instance_point12 = 2
        instance_point34 = 3
        instance_point56 = 4
        instance_point78 = 5
        instance_point_count = 6
        instance_radius = 7
        instance_color = 8

        for attr in range(9):
            glEnableVertexAttribArray(attr)

        a = 1.1
        vertices = np.array(
            [
                -a,
                -a,
                a,
                -a,
                -a,
                a,
                a,
                -a,
                a,
                a,
                -a,
                a,
            ],
            dtype=np.float32,
        )
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_ids[0])
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        glVertexAttribPointer(vertex_attribute, 2, GL_FLOAT, GL_FALSE, 0, None)

        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_ids[1])
        glBufferData(
            GL_ARRAY_BUFFER,
            self.BATCH_SIZE * polygon_dtype.itemsize,
            None,
            GL_DYNAMIC_DRAW,
        )
        stride = polygon_dtype.itemsize
        offset = 0
        glVertexAttribPointer(
            instance_transform, 4, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(offset)
        )
        offset += 16
        glVertexAttribPointer(
            instance_point12, 4, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(offset)
        )
        offset += 16
        glVertexAttribPointer(
            instance_point34, 4, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(offset)
        )
        offset += 16
        glVertexAttribPointer(
            instance_point56, 4, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(offset)
        )
        offset += 16
        glVertexAttribPointer(
            instance_point78, 4, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(offset)
        )
        offset += 16
        glVertexAttribIPointer(
            instance_point_count, 1, GL_INT, stride, ctypes.c_void_p(offset)
        )
        offset += 4
        glVertexAttribPointer(
            instance_radius, 1, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(offset)
        )
        offset += 4
        glVertexAttribPointer(
            instance_color,
            4,
            GL_UNSIGNED_BYTE,
            GL_TRUE,
            stride,
            ctypes.c_void_p(offset),
        )
        for attr in range(1, 9):
            glVertexAttribDivisor(attr, 1)

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

    def add_polygon(self, transform, points, count, radius, color):
        """Pack polygon data into the current instance buffer using the structured dtype.
        Format:
            transform: [p.x, p.y, q.c, q.s]
            points: 8 pairs of (x, y) (fill remaining with 0.0)
            count: integer
            radius: float
            color: uint32 bit pattern
        """
        rgba = make_rgba8(color)
        rec = self.current_buffer[self.polygons_count]
        rec["transform"] = [transform.p.x, transform.p.y, transform.q.c, transform.q.s]
        pts = np.zeros(16, dtype=np.float32)
        for i in range(count):
            pts[i * 2] = points[i].x
            pts[i * 2 + 1] = points[i].y
        rec["points"] = pts
        rec["count"] = count
        rec["radius"] = radius
        rec["color"] = rgba

        self.polygons_count += 1

        # When the current buffer is full, recycle it.
        if self.polygons_count == self.BATCH_SIZE:
            self.instance_buffers.append(self.current_buffer)
            if self.free_buffers:
                self.current_buffer = self.free_buffers.pop()
            else:
                self.current_buffer = np.empty(self.BATCH_SIZE, dtype=polygon_dtype)
            self.polygons_count = 0

    def draw(self):
        """Render all polygons in batch"""
        if self.polygons_count == 0 and not self.instance_buffers:
            return

        glUseProgram(self.program_id)
        proj_matrix = self.camera.build_projection_matrix(0.2)
        glUniformMatrix4fv(self.projection_uniform, 1, GL_FALSE, proj_matrix)
        glUniform1f(self.pixel_scale_uniform, self.camera.height / self.camera.zoom)

        glBindVertexArray(self.vao_id)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_ids[1])
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Draw upload full batches.
        for buf in self.instance_buffers:
            glBufferSubData(GL_ARRAY_BUFFER, 0, buf.nbytes, buf.ravel())
            glDrawArraysInstanced(GL_TRIANGLES, 0, 6, self.BATCH_SIZE)

        # Draw partial batch.
        if self.polygons_count > 0:
            buf = self.current_buffer[: self.polygons_count]
            glBufferSubData(GL_ARRAY_BUFFER, 0, buf.nbytes, buf.ravel())
            glDrawArraysInstanced(GL_TRIANGLES, 0, 6, self.polygons_count)

        glDisable(GL_BLEND)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)
        glUseProgram(0)

        # Instead of discarding buffers, add them to the free pool for reuse.
        self.free_buffers.extend(self.instance_buffers)
        # Also, keep the current_buffer for future use.
        # Reset for the next frame.
        self.instance_buffers.clear()
        self.polygons_count = 0


class GLPoints:
    def __init__(self, camera):
        self.camera = camera
        self.points = []  # list of (x, y, size, r, g, b, a)
        vertex_shader = (
            "#version 330\n"
            "uniform mat4 projectionMatrix;\n"
            "layout(location = 0) in vec2 v_position;\n"
            "layout(location = 1) in float v_size;\n"
            "layout(location = 2) in vec4 v_color;\n"
            "out vec4 f_color;\n"
            "void main(void){\n"
            "  f_color = v_color;\n"
            "  gl_Position = projectionMatrix * vec4(v_position, 0.0, 1.0);\n"
            "  gl_PointSize = v_size;\n"
            "}\n"
        )
        fragment_shader = (
            "#version 330\n"
            "in vec4 f_color;\n"
            "out vec4 color;\n"
            "void main(void){\n"
            "  color = f_color;\n"
            "}\n"
        )
        self.program_id = create_program_from_strings(vertex_shader, fragment_shader)
        self.projection_uniform = glGetUniformLocation(
            self.program_id, "projectionMatrix"
        )
        self.vao_id = glGenVertexArrays(1)
        self.vbo_id = glGenBuffers(1)
        glBindVertexArray(self.vao_id)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_id)
        # Allocate an empty dynamic buffer
        glBufferData(GL_ARRAY_BUFFER, 0, None, GL_DYNAMIC_DRAW)
        stride = (
            2 * 4 + 4 + 4
        )  # 2 floats (8 bytes) + 1 float (4 bytes) + 4 bytes for color
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 1, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(8))
        glEnableVertexAttribArray(2)
        glVertexAttribPointer(
            2, 4, GL_UNSIGNED_BYTE, GL_TRUE, stride, ctypes.c_void_p(12)
        )
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

    def add_point(self, pos, size, color):
        rgba = make_rgba8(color)
        r = rgba & 0xFF
        g = (rgba >> 8) & 0xFF
        b = (rgba >> 16) & 0xFF
        a = (rgba >> 24) & 0xFF
        self.points.append((pos.x, pos.y, size, r, g, b, a))

    def draw(self):
        if not self.points:
            return
        dtype = np.dtype(
            [("position", np.float32, 2), ("size", np.float32), ("color", np.uint8, 4)]
        )
        buffer = np.empty(len(self.points), dtype=dtype)
        for i, pt in enumerate(self.points):
            buffer["position"][i] = (pt[0], pt[1])
            buffer["size"][i] = pt[2]
            buffer["color"][i] = (pt[3], pt[4], pt[5], pt[6])
        flat_data = buffer.view(np.uint8)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_id)
        glBufferData(GL_ARRAY_BUFFER, flat_data.nbytes, flat_data, GL_DYNAMIC_DRAW)
        glUseProgram(self.program_id)
        proj = self.camera.build_projection_matrix(0.0)
        glUniformMatrix4fv(self.projection_uniform, 1, GL_FALSE, proj)
        glBindVertexArray(self.vao_id)
        glEnable(GL_PROGRAM_POINT_SIZE)
        glDrawArrays(GL_POINTS, 0, len(self.points))
        glDisable(GL_PROGRAM_POINT_SIZE)
        glBindVertexArray(0)
        glUseProgram(0)
        self.points.clear()

    def destroy(self):
        if self.vao_id:
            glDeleteVertexArrays(1, [self.vao_id])
            self.vao_id = None
        if self.vbo_id:
            glDeleteBuffers(1, [self.vbo_id])
            self.vbo_id = None
        if self.program_id:
            glDeleteProgram(self.program_id)
            self.program_id = None


class GLLines:
    def __init__(self, camera):
        self.camera = camera
        self.lines = []  # list of vertices: each vertex as (x, y, r, g, b, a)
        vertex_shader = (
            "#version 330\n"
            "uniform mat4 projectionMatrix;\n"
            "layout(location = 0) in vec2 v_position;\n"
            "layout(location = 1) in vec4 v_color;\n"
            "out vec4 f_color;\n"
            "void main(void){\n"
            "  f_color = v_color;\n"
            "  gl_Position = projectionMatrix * vec4(v_position, 0.0, 1.0);\n"
            "}\n"
        )
        fragment_shader = (
            "#version 330\n"
            "in vec4 f_color;\n"
            "out vec4 color;\n"
            "void main(void){\n"
            "  color = f_color;\n"
            "}\n"
        )
        self.program_id = create_program_from_strings(vertex_shader, fragment_shader)
        self.projection_uniform = glGetUniformLocation(
            self.program_id, "projectionMatrix"
        )
        self.vao_id = glGenVertexArrays(1)
        self.vbo_id = glGenBuffers(1)
        glBindVertexArray(self.vao_id)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_id)
        glBufferData(GL_ARRAY_BUFFER, 0, None, GL_DYNAMIC_DRAW)
        stride = 2 * 4 + 4  # 2 floats (8 bytes) + 4 bytes for color
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(
            1, 4, GL_UNSIGNED_BYTE, GL_TRUE, stride, ctypes.c_void_p(8)
        )
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

    def add_line(self, p1, p2, color):
        rgba = make_rgba8(color)
        r = rgba & 0xFF
        g = (rgba >> 8) & 0xFF
        b = (rgba >> 16) & 0xFF
        a = (rgba >> 24) & 0xFF
        self.lines.append((p1.x, p1.y, r, g, b, a))
        self.lines.append((p2.x, p2.y, r, g, b, a))

    def draw(self):
        if not self.lines:
            return
        dtype = np.dtype([("position", np.float32, 2), ("color", np.uint8, 4)])
        buffer = np.empty(len(self.lines), dtype=dtype)
        for i, vertex in enumerate(self.lines):
            buffer["position"][i] = (vertex[0], vertex[1])
            buffer["color"][i] = (vertex[2], vertex[3], vertex[4], vertex[5])
        flat_data = buffer.view(np.uint8)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_id)
        glBufferData(GL_ARRAY_BUFFER, flat_data.nbytes, flat_data, GL_DYNAMIC_DRAW)
        glUseProgram(self.program_id)
        proj = self.camera.build_projection_matrix(0.0)
        glUniformMatrix4fv(self.projection_uniform, 1, GL_FALSE, proj)
        glBindVertexArray(self.vao_id)
        glDrawArrays(GL_LINES, 0, len(self.lines))
        glBindVertexArray(0)
        glUseProgram(0)
        self.lines.clear()

    def destroy(self):
        if self.vao_id:
            glDeleteVertexArrays(1, [self.vao_id])
            self.vao_id = None
        if self.vbo_id:
            glDeleteBuffers(1, [self.vbo_id])
            self.vbo_id = None
        if self.program_id:
            glDeleteProgram(self.program_id)
            self.program_id = None
