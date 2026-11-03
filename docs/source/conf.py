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
    # BodyBuilder.extend's type variable: "the function you decorated".
    ("py:class", "box2d.body._F"),
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
# gives. A reader wants that type, float, so the header says it instead.


def setup(app):
    # Imported here, not at the top: test_version.py reads this file for its
    # version settings where Sphinx is not installed, under Pyodide for one.
    from typing import get_args, get_origin

    from sphinx.ext.autodoc import AttributeDocumenter
    from sphinx.util.typing import stringify_annotation

    from box2d.accessors import B2Accessor
    from box2d.debug_draw import _DrawFlag

    def read_type(annotation):
        """What reading an attribute with this annotation gives, if a descriptor."""
        if get_origin(annotation) is B2Accessor:
            return get_args(annotation)[0]
        if annotation is _DrawFlag:
            return bool
        return None

    class DescriptorAttributeDocumenter(AttributeDocumenter):
        def add_directive_header(self, sig):
            start = len(self.directive.result)
            super().add_directive_header(sig)
            # The class's own annotations rather than get_type_hints, which
            # would have to resolve the names imported only for type checkers.
            name = self.objpath[-1]
            annotation = next(
                (
                    vars(klass)["__annotations__"][name]
                    for klass in getattr(self.parent, "__mro__", ())
                    if name in vars(klass).get("__annotations__", {})
                ),
                None,
            )
            read = read_type(annotation)
            if read is None:
                return
            lines = self.directive.result
            for i in range(start, len(lines)):
                indent, _, rest = lines[i].partition(":type: ")
                if rest and not indent.strip():
                    lines[i] = indent + ":type: " + stringify_annotation(read, "smart")

    app.add_autodocumenter(DescriptorAttributeDocumenter, override=True)
