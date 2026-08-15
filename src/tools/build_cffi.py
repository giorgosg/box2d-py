# build_cffi.py
import os
import subprocess
import sys
from cffi import FFI
import re
import platform

# Set up directories
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BOX2D_DIR = os.path.join(PROJECT_ROOT, "box2d")
ENKITS_DIR = os.path.join(PROJECT_ROOT, "enkits")
BOX2D_BUILD_DIR = os.path.join(BOX2D_DIR, "build")
ENKITS_BUILD_DIR = os.path.join(ENKITS_DIR, "build")
TEMP_DIR = os.path.join(PROJECT_ROOT, "build", "cffi_temp")

# Threads are optional at build time. enkiTS needs a real thread pool, which
# rules it out on targets that have none -- WebAssembly without
# SharedArrayBuffer being the one that prompted this. Box2D itself is happy
# single threaded; only World(threads=N>1) needs the scheduler.
WITH_THREADS = os.environ.get("BOX2D_PY_NO_THREADS", "") == ""


def ensure_temp_dir():
    """Ensure the temporary directory exists."""
    os.makedirs(TEMP_DIR, exist_ok=True)


def build_dependencies():
    """Build Box2D and enkiTS using CMake"""
    # Always start with clean build directories to avoid CMake cache issues
    import shutil

    if os.path.exists(BOX2D_BUILD_DIR):
        print(f"Removing existing build directory: {BOX2D_BUILD_DIR}")
        shutil.rmtree(BOX2D_BUILD_DIR)
    os.makedirs(BOX2D_BUILD_DIR, exist_ok=True)

    if WITH_THREADS:
        if os.path.exists(ENKITS_BUILD_DIR):
            print(f"Removing existing build directory: {ENKITS_BUILD_DIR}")
            shutil.rmtree(ENKITS_BUILD_DIR)
        os.makedirs(ENKITS_BUILD_DIR, exist_ok=True)

    # Build Box2D
    print("Building Box2D...")
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

    if not WITH_THREADS:
        print("Skipping enkiTS: building without thread support")
        return

    # Build enkiTS
    print("Building enkiTS...")
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


def strip_inline_definitions(text):
    """Remove inline function definitions, which cdef() cannot parse.

    cdef() accepts declarations only, so any function carrying a body has to go.
    Box2D marks these with its B2_INLINE macro in most headers but writes plain
    'static inline' in id.h, and the bodies contain brace initializers such as
    ``b2WorldId id = { ... };``, so this counts braces rather than matching a
    pattern -- a regex cannot handle the nesting, and matching only B2_INLINE
    silently let id.h's definitions through.
    """
    markers = ("B2_INLINE", "static inline")
    lines = text.splitlines(keepends=True)
    kept = []
    i = 0
    while i < len(lines):
        if not lines[i].lstrip().startswith(markers):
            kept.append(lines[i])
            i += 1
            continue

        # Consume the signature and its body, balancing braces.
        depth = 0
        seen_brace = False
        while i < len(lines):
            depth += lines[i].count("{") - lines[i].count("}")
            seen_brace = seen_brace or "{" in lines[i]
            i += 1
            if seen_brace and depth <= 0:
                break
    return "".join(kept)


def process_headers():
    """Process Box2D headers for CFFI"""
    ensure_temp_dir()

    # Add missing function declarations
    extra_declarations = """
    """

    headers = [
        "base.h",
        "constants.h",
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
        filetext = strip_inline_definitions(filetext)
        filetext = "\n".join(
            [line for line in filetext.splitlines() if not line.startswith("#")]
        )
        temp_filename = os.path.join(TEMP_DIR, os.path.basename(header) + ".cffi")
        with open(temp_filename, "w") as outfile:
            outfile.write(filetext)

        combined_header += filetext + "\n"

    # Add task scheduler definitions, when there is a scheduler to declare.
    if WITH_THREADS:
        with open(os.path.join("src", "tasks", "task_scheduler.cffi")) as f:
            combined_header += f.read()

    return combined_header


def compile_task_scheduler():
    """Compile task_scheduler.c into an object file with PIC."""
    ensure_temp_dir()

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

    if not WITH_THREADS:
        # Box2D alone. No enkiTS, and no C++ runtime, since enkiTS was the
        # only C++ in the build.
        return {
            "libraries": ["box2d"],
            "extra_compile_args": [],
            "extra_link_args": [],
            "library_dirs": [os.path.join(BOX2D_BUILD_DIR, "src")],
        }

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


def create_ffibuilder():
    """Create and configure the FFI builder."""
    ffibuilder = FFI()

    # Process headers and set up CFFI builder
    ffibuilder.cdef(process_headers())

    # Compile the task_scheduler.c and get the object file
    task_scheduler_obj = compile_task_scheduler() if WITH_THREADS else None

    # Configure CFFI builder
    platform_config = get_platform_specific_config()
    source = '#include "box2d/box2d.h"'
    if WITH_THREADS:
        source += """
        #include "TaskScheduler_c.h"
        #include "tasks/task_scheduler.h"
        """
    ffibuilder.set_source(
        "box2d._box2d",
        source,
        include_dirs=[
            os.path.join(BOX2D_DIR, "include"),
            os.path.join(BOX2D_DIR, "src"),
            os.path.join(ENKITS_DIR, "src"),
            os.path.join(PROJECT_ROOT, "src", "tasks"),
            "src",
        ],
        library_dirs=platform_config["library_dirs"],  # Use platform-specific paths
        libraries=platform_config["libraries"],
        extra_objects=[task_scheduler_obj] if task_scheduler_obj else [],
        extra_compile_args=platform_config["extra_compile_args"],
        extra_link_args=platform_config["extra_link_args"],
    )

    return ffibuilder


ffibuilder = create_ffibuilder()


def build(build_target=None):
    """Build the entire project."""
    # Build dependencies first
    build_dependencies()

    # Create FFI builder and compile
    # ffibuilder = create_ffibuilder()
    if build_target:
        ffibuilder.compile(target=build_target, verbose=True)
    else:
        ffibuilder.compile(verbose=True)


if __name__ == "__main__":
    build()
