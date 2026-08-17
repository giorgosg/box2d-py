# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "box2d-python"
copyright = "2025, Giorgos Giagas"
author = "Giorgos Giagas"
release = "2025"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_rtd_theme",
]

templates_path = ["_templates"]
exclude_patterns = []

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
