# build_cffi.py
import os
import subprocess
import sys
from cffi import FFI
import re
import platform

ffibuilder = FFI()

# Set up directories
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BOX2D_DIR = os.path.join(PROJECT_ROOT, "box2d")
ENKITS_DIR = os.path.join(PROJECT_ROOT, "enkits")
BOX2D_BUILD_DIR = os.path.join(BOX2D_DIR, "build")
ENKITS_BUILD_DIR = os.path.join(ENKITS_DIR, "build")
TEMP_DIR = os.path.join(PROJECT_ROOT, "build", "cffi_temp")
os.makedirs(TEMP_DIR, exist_ok=True)


def build_dependencies():
    """Build Box2D and enkiTS using CMake"""
    # Build Box2D
    print("Building Box2D...")
    os.makedirs(BOX2D_BUILD_DIR, exist_ok=True)

    box2d_cmake_args = [
        "cmake",
        "-S",
        BOX2D_DIR,
        "-B",
        BOX2D_BUILD_DIR,
        "-DBOX2D_BUILD_DOCS=OFF",
        "-DBOX2D_SAMPLES=OFF",
        "-DBOX2D_UNIT_TESTS=OFF",
        "-DBUILD_SHARED_LIBS=OFF",
        "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
        "-DCMAKE_BUILD_TYPE=Release",
    ]

    if platform.system() == "Windows":
        box2d_cmake_args.extend(
            [
                "-G",
                "Visual Studio 17 2022",
                "-A",
                "x64",
                "-DCMAKE_CXX_FLAGS_RELEASE=/MD",
            ]
        )

    subprocess.run(box2d_cmake_args, check=True)
    subprocess.run(
        ["cmake", "--build", BOX2D_BUILD_DIR, "--config", "Release"], check=True
    )

    # Build enkiTS
    print("Building enkiTS...")
    os.makedirs(ENKITS_BUILD_DIR, exist_ok=True)

    enkits_cmake_args = [
        "cmake",
        "-S",
        ENKITS_DIR,
        "-B",
        ENKITS_BUILD_DIR,
        "-DENKITS_BUILD_EXAMPLES=OFF",
        "-DENKITS_BUILD_SHARED=OFF",
        "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
        "-DCMAKE_BUILD_TYPE=Release",
    ]

    if platform.system() == "Windows":
        enkits_cmake_args.extend(
            [
                "-G",
                "Visual Studio 17 2022",
                "-A",
                "x64",
                "-DCMAKE_CXX_FLAGS_RELEASE=/MD",
            ]
        )

    subprocess.run(enkits_cmake_args, check=True)
    subprocess.run(
        ["cmake", "--build", ENKITS_BUILD_DIR, "--config", "Release"], check=True
    )


def process_headers():
    """Process Box2D headers for CFFI"""
    # Add missing function declarations
    extra_declarations = """
    """

    headers = [
        "base.h",
        "math_functions.h",
        "collision.h",
        "id.h",
        "types.h",
        "box2d.h",
    ]

    combined_header = extra_declarations
    cdef_dir = os.path.join(BOX2D_DIR, "include", "box2d")

    for header in headers:
        with open(os.path.join(cdef_dir, header), "r") as f:
            filetext = "".join(
                [
                    line
                    for line in f
                    if (
                        ("#include" not in line)
                        and ("b2GetTicks" not in line)
                        and ("b2Internal" not in line)
                    )
                ]
            )
        command = ["gcc", "-E", "-P", "-D__linux__", "-"]
        filetext = subprocess.run(
            command, text=True, input=filetext, stdout=subprocess.PIPE
        ).stdout
        filetext = filetext.replace("B2_API", "")
        filetext = re.sub("B2_INLINE .*?\n{\n(.|\n)*?\n}\n", "", filetext)
        filetext = "\n".join(
            [line for line in filetext.splitlines() if not line.startswith("#")]
        )
        temp_filename = os.path.join(TEMP_DIR, os.path.basename(header) + ".cffi")
        with open(temp_filename, "w") as outfile:
            outfile.write(filetext)

        combined_header += filetext + "\n"

    # Add task scheduler definitions
    with open(os.path.join("src", "tasks", "task_scheduler.cffi")) as f:
        combined_header += f.read()

    return combined_header


def compile_task_scheduler():
    """Compile task_scheduler.c into an object file with PIC."""
    ts_c_path = os.path.join(PROJECT_ROOT, "src", "tasks", "task_scheduler.c")
    ts_obj = os.path.join(TEMP_DIR, "task_scheduler.o")
    enkits_include = os.path.join(ENKITS_DIR, "src")
    box2d_include = os.path.join(BOX2D_DIR, "include")
    compile_cmd = [
        "gcc",
        "-fPIC",
        "-c",
        ts_c_path,
        "-I",
        enkits_include,
        "-I",
        box2d_include,
        "-o",
        ts_obj,
    ]
    print("Compiling task_scheduler.c...")
    subprocess.run(compile_cmd, check=True)
    return ts_obj


def get_platform_specific_config():
    """Get platform-specific build configuration."""
    import platform

    if platform.system() == "Windows":
        return {
            "libraries": ["box2d", "enkiTS"],  # Use box2dd.lib on Windows
            "extra_compile_args": ["/MD", "/O2"],  # Use release runtime
            "extra_link_args": [
                "/NODEFAULTLIB:LIBCMTD",
                "/NODEFAULTLIB:MSVCRTD",
            ],  # Ignore debug runtime
            "library_dirs": [
                os.path.join(BOX2D_BUILD_DIR, "src", "Release"),  # Updated path
                os.path.join(ENKITS_BUILD_DIR, "Release"),
            ],
        }
    else:
        return {
            "libraries": ["box2d", "enkiTS", "stdc++"],
            "extra_compile_args": [],
            "extra_link_args": [],
            "library_dirs": [
                os.path.join(BOX2D_BUILD_DIR, "src"),
                ENKITS_BUILD_DIR,
            ],
        }


# Build dependencies
build_dependencies()

# Process headers and set up CFFI builder
ffibuilder.cdef(process_headers())

# Compile the task_scheduler.c and get the object file
task_scheduler_obj = compile_task_scheduler()

# Configure CFFI builder
platform_config = get_platform_specific_config()
ffibuilder.set_source(
    "box2d._box2d",
    """
    #include "box2d/box2d.h"
    #include "TaskScheduler_c.h"
    #include "tasks/task_scheduler.h"
    """,
    include_dirs=[
        os.path.join(BOX2D_DIR, "include"),
        os.path.join(BOX2D_DIR, "src"),
        os.path.join(ENKITS_DIR, "src"),
        os.path.join(PROJECT_ROOT, "src", "tasks"),
        "src",
    ],
    library_dirs=platform_config["library_dirs"],  # Use platform-specific paths
    libraries=platform_config["libraries"],
    extra_objects=[task_scheduler_obj],
    extra_compile_args=platform_config["extra_compile_args"],
    extra_link_args=platform_config["extra_link_args"],
)


def main(build_target=None):
    if build_target:
        ffibuilder.compile(target=build_target, verbose=True)
    else:
        ffibuilder.compile(verbose=True)


if __name__ == "__main__":
    main()
