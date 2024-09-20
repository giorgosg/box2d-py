# build_box2d.py
import os
import subprocess
import re
import sys

from cffi import FFI

ffibuilder = FFI()

# Get all .h files in the include directory
cdef_dir = 'box2d/include/box2d'
include_dir = 'box2d/include/'
#header_files = [f for f in os.listdir(include_dir) if f.endswith('.h')]
header_files = ['base.h', 'math_functions.h', 'collision.h', 'id.h', 'types.h', 'box2d.h']
# Read and combine all header files

def process_header(filename):
    print("Pre-processing " + filename)
    with open(filename, "r") as file:
        filetext = "".join([line for line in file if ('#include' not in line) and ("b2GetTicks" not in line)])
    command = ['gcc', '-CC', '-P', '-undef', '-nostdinc',
               '-D__linux__', '-E', '-']
    filetext = subprocess.run(command, text=True, input=filetext, stdout=subprocess.PIPE).stdout
    filetext = filetext.replace("B2_API", "")
    filetext = re.sub('B2_INLINE .*?\n{\n(.|\n)*?\n}\n', '', filetext)
    filetext = "\n".join([line for line in filetext.splitlines() if not line.startswith("#")])
    with open(os.path.basename(filename)+".cffi", "w") as outfile:
            outfile.write(filetext)
    return filetext

combined_header = ''
for headerfn in header_files:
    combined_header += process_header(os.path.join(cdef_dir, headerfn))


# Combine the headers
with open("combined_header.h.modified", 'w') as f:
    f.write(combined_header)

ffibuilder.cdef(combined_header)

# Get all .c files in the src directory
src_dir = 'box2d/src'
source_files = [os.path.join(src_dir, f) for f in os.listdir(src_dir) if f.endswith('.c')]
print(source_files)

ffibuilder.set_source(
    "box2d_py._box2d",
    """#include "box2d/box2d.h"
    """,
    sources=source_files,
    include_dirs=[include_dir, cdef_dir],
    extra_compile_args=['-D__linux__', ]
)



if __name__ == "__main__":
    ffibuilder.compile(verbose=True)
