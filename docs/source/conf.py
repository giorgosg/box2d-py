# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import sys, os, sphinx_rtd_theme

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'box2d-py'
copyright = '2025, Giorgos Giagas'
author = 'Giorgos Giagas'
release = '2025'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.napoleon',
              'sphinx.ext.viewcode',
              'sphinx_rtd_theme',
              ]

templates_path = ['_templates']
exclude_patterns = []

# Mock CFFI imports that require compiled binaries
autodoc_mock_imports = ["box2d._box2d"]

# Napoleon settings for Google-style docstrings
napoleon_google_docstring = True
napoleon_include_init_with_doc = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
sys.path.insert(0, os.path.abspath('../../src/'))  # Add project to path