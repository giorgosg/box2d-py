from OpenGL.GL import *
from OpenGL.GL import shaders
import ctypes


def dump_gl_info():
    """Print OpenGL driver information."""
    print("-------------------------------------------------------------")
    print(f"GL Vendor    : {glGetString(GL_VENDOR).decode()}")
    print(f"GL Renderer  : {glGetString(GL_RENDERER).decode()}")
    print(f"GL Version   : {glGetString(GL_VERSION).decode()}")
    major = GLint()
    minor = GLint()
    glGetIntegerv(GL_MAJOR_VERSION, major)
    glGetIntegerv(GL_MINOR_VERSION, minor)
    print(f"GL Version   : {major.value}.{minor.value}")
    print(f"GLSL Version : {glGetString(GL_SHADING_LANGUAGE_VERSION).decode()}")
    print("-------------------------------------------------------------")


def check_gl_error():
    """Check for OpenGL errors."""
    err = glGetError()
    if err != GL_NO_ERROR:
        print(f"OpenGL error = {err}")
        assert False


def print_gl_log(obj):
    """Print shader or program info log."""
    if glIsShader(obj):
        length = GLint()
        glGetShaderiv(obj, GL_INFO_LOG_LENGTH, length)
        log = glGetShaderInfoLog(obj).decode()
    elif glIsProgram(obj):
        length = GLint()
        glGetProgramiv(obj, GL_INFO_LOG_LENGTH, length)
        log = glGetProgramInfoLog(obj).decode()
    else:
        print("PrintLogGL: Not a shader or a program")
        return

    if log:
        print(f"PrintLogGL: {log}")


def _create_shader_from_string(source, shader_type):
    """Create a shader from source string."""
    try:
        shader = glCreateShader(shader_type)
        glShaderSource(shader, source)
        glCompileShader(shader)

        # Check compilation status
        status = GLint()
        glGetShaderiv(shader, GL_COMPILE_STATUS, status)

        if status.value == GL_FALSE:
            print(f"Error compiling shader of type {shader_type}!")
            print_gl_log(shader)
            glDeleteShader(shader)
            return 0

        return shader
    except Exception as e:
        print(f"Error creating shader: {e}")
        return 0


def create_program_from_strings(vertex_string, fragment_string):
    """Create a shader program from vertex and fragment shader strings."""
    vertex = _create_shader_from_string(vertex_string, GL_VERTEX_SHADER)
    if vertex == 0:
        return 0

    fragment = _create_shader_from_string(fragment_string, GL_FRAGMENT_SHADER)
    if fragment == 0:
        return 0

    program = glCreateProgram()
    glAttachShader(program, vertex)
    glAttachShader(program, fragment)
    glLinkProgram(program)

    # Check link status
    status = GLint()
    glGetProgramiv(program, GL_LINK_STATUS, status)
    if status.value == GL_FALSE:
        print("glLinkProgram:")
        print_gl_log(program)
        return 0

    glDeleteShader(vertex)
    glDeleteShader(fragment)

    return program


def create_program_from_files(vertex_path, fragment_path):
    """Create a shader program from vertex and fragment shader files."""
    try:
        with open(vertex_path, "r") as f:
            vertex_source = f.read()

        with open(fragment_path, "r") as f:
            fragment_source = f.read()

        return create_program_from_strings(vertex_source, fragment_source)

    except Exception as e:
        print(f"Error reading shader files: {e}")
        return 0
