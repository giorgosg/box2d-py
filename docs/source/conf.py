# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import box2d

project = "box2d-python"
copyright = "2025–2026, Giorgos Giagas"
author = "Giorgos Giagas"

# The package's own version, which it reads from the installed metadata, so
# that pyproject.toml stays the one place a version is written. `release` is
# the full version, the one each page's <title> shows; `version` is the short
# major.minor form Sphinx offers as |version|: 3.2 for 3.2.0rc1 or 3.2.0.1.
release = box2d.__version__
version = ".".join(release.split(".")[:2])

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_rtd_theme",
]

templates_path = ["_templates"]
exclude_patterns = []

# So the standard types the signatures are full of -- int, float, tuple,
# ValueError -- link to CPython's own documentation rather than sitting there
# as plain text.
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}

# Signatures name types in full, box2d.math.Vec2 rather than Vec2, which
# leaves them too wide to read. Show the last component and link it.
python_use_unqualified_type_names = True

# What `sphinx-build -n` can never resolve, so that running it says something.
# Everything here is a word standing in for a type rather than naming one:
# napoleon's "optional" marker, the prose types a few docstrings use, and the
# C types cffi and Box2D hand back, which have no Python documentation.
nitpick_ignore = [
    ("py:class", "optional"),
    ("py:class", "callable"),
    ("py:class", "vector-like"),
    ("py:class", "_cffi_backend._CDataBase"),
    ("py:class", "b2Filter"),
    ("py:class", "b2QueryFilter"),
    # Type variables: BodyBuilder.extend's "the function you decorated", and
    # World.class_for's "the class you asked about".
    ("py:class", "box2d.body._F"),
    ("py:class", "box2d.world._T"),
]

# The compiled extension is not mocked: readthedocs builds it (see
# .readthedocs.yml, which installs the package with cmake and the submodules).
# Mocking it made every module that reads a Box2D default at import time fail to
# import, which silently left most of the API undocumented.
#
# Nothing is put on sys.path here either. Pointing it at src/ shadowed the
# installed package with the source tree, which carries no compiled _box2d --
# so every autodoc directive failed to import and rendered as nothing, and the
# build still reported success. autodoc imports what is installed instead: the
# editable install locally, the wheel readthedocs builds.

# Napoleon settings for Google-style docstrings
napoleon_google_docstring = True
napoleon_include_init_with_doc = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"


# -- Properties backed by descriptors ----------------------------------------
# Most engine properties are descriptors, B2Accessor and DebugDraw's flags,
# annotated with the descriptor's own type -- `friction: B2Accessor[float,
# float]` -- because that is what lets a type checker see what reading one
# gives. A reader wants that type, float, so before autodoc reads the classes
# their annotations are rewritten to it. This touches only the docs build's
# own import of box2d, and works the same whichever autodoc Sphinx ships.


def setup(app):
    # Here rather than at the top: test_version.py runs this file to read its
    # version settings, and must not change the classes it then tests.
    import inspect
    import pkgutil
    from importlib import import_module
    from typing import get_args, get_origin

    from box2d.accessors import B2Accessor
    from box2d.debug_draw import _DrawFlag

    def read_type(annotation):
        """What reading an attribute with this annotation gives, if a descriptor."""
        if get_origin(annotation) is B2Accessor:
            return get_args(annotation)[0]
        if annotation is _DrawFlag:
            return bool
        return None

    for module_info in pkgutil.iter_modules(box2d.__path__, "box2d."):
        module = import_module(module_info.name)
        for _, cls in inspect.getmembers(module, inspect.isclass):
            annotations = vars(cls).get("__annotations__", {})
            for name, annotation in annotations.items():
                read = read_type(annotation)
                if read is not None:
                    annotations[name] = read
