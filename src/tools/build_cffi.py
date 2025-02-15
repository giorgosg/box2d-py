# build_cffi.py
import os
import subprocess
import re
import sys

from cffi import FFI

ffibuilder = FFI()

# Set up directories for temporary files.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEMP_DIR = os.path.join(PROJECT_ROOT, "build", "cffi_temp")
os.makedirs(TEMP_DIR, exist_ok=True)

# Get all .h files in the include directory
cdef_dir = "box2d/include/box2d"
include_dir = "box2d/include/"
# header_files = [f for f in os.listdir(include_dir) if f.endswith('.h')]
header_files = [
    "base.h",
    "math_functions.h",
    "collision.h",
    "id.h",
    "types.h",
    "box2d.h",
]


# Read and combine all header files
def process_header(filename):
    print("Pre-processing " + filename)
    with open(filename, "r") as file:
        filetext = "".join(
            [
                line
                for line in file
                if ("#include" not in line) and ("b2GetTicks" not in line)
            ]
        )
    command = ["gcc", "-CC", "-P", "-undef", "-nostdinc", "-D__linux__", "-E", "-"]
    filetext = subprocess.run(
        command, text=True, input=filetext, stdout=subprocess.PIPE
    ).stdout
    filetext = filetext.replace("B2_API", "")
    # filetext = filetext.replace("B2_API", "__attribute__((visibility(\"default\")))")
    filetext = re.sub("B2_INLINE .*?\n{\n(.|\n)*?\n}\n", "", filetext)
    # filetext = re.sub(r'B2_INLINE .*?{.*?}\n', '', filetext, flags=re.DOTALL)
    filetext = "\n".join(
        [line for line in filetext.splitlines() if not line.startswith("#")]
    )
    temp_filename = os.path.join(TEMP_DIR, os.path.basename(filename) + ".cffi")
    with open(temp_filename, "w") as outfile:
        outfile.write(filetext)
    return filetext


combined_header = ""
for headerfn in header_files:
    combined_header += process_header(os.path.join(cdef_dir, headerfn))
with open(os.path.join("src", "tasks", "task_scheduler.cffi")) as ts:
    combined_header += "".join(l for l in ts)

# Combine the headers
combined_header_file = os.path.join(TEMP_DIR, "combined_header.h.modified")
with open(combined_header_file, "w") as f:
    f.write(combined_header)

ffibuilder.cdef(combined_header)

# Get all .c files in the src directory
src_dir = "box2d/src"
source_files = [
    os.path.join(src_dir, f) for f in os.listdir(src_dir) if f.endswith(".c")
]

# Add the task scheduler source file (which uses enkiTS)
task_scheduler_path = os.path.join("src", "tasks", "task_scheduler.c")
source_files.append(task_scheduler_path)

print("Compiling the following source files:")
for s in source_files:
    print("  ", s)


ffibuilder.set_source(
    "box2d._box2d",
    """
    #include "box2d/box2d.h"
    #include "enkiTS/TaskScheduler_c.h"
    #include "tasks/task_scheduler.h"
    """,
    sources=source_files,
    include_dirs=[include_dir, cdef_dir, "src"],
    library_dirs=["/usr/lib"],
    libraries=["enkiTS"],
    extra_compile_args=[
        "-D__linux__",
        "-DB2_ENABLE_ASSERT=1",
        "-DB2_INTERNAL_ASSERT_ENABLED=1",
    ],
)


def main():
    build_dir = os.path.join(PROJECT_ROOT, "src", "box2d")
    os.makedirs(build_dir, exist_ok=True)

    target_path = os.path.join(build_dir, "_box2d.so")
    ffibuilder.compile(target=target_path, verbose=True)


if __name__ == "__main__":
    main()
