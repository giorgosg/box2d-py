import os
import sys
sys.path.insert(0, os.path.abspath('src'))

from setuptools import setup, find_packages
#from build_box2d import builder

setup(use_scm_version={"local_scheme": "no-local-version"},
      package_dir={"": "src"},
      cffi_modules=["src/box2d-py/build_cffi.py:ffibuilder"],
      packages=find_packages(where="src"),
      )

