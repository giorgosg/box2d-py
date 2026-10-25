box2d-python
============

Python bindings for `Box2D <https://box2d.org/>`_ v3.2.0, the 2D physics
engine, built with `cffi <https://cffi.readthedocs.io/>`_. Box2D itself is
compiled into the package and does the simulating; the bodies, shapes,
joints, queries and events around it are ordinary Python objects.

It runs on Linux, macOS and Windows with Python 3.12, 3.13 or 3.14, and in
WebAssembly under Pyodide. It installs as ``box2d-python`` and imports as
``box2d``:

.. code-block:: python

    from box2d import World

    world = World(gravity=(0, -10))
    ground = world.new_body().static().box(40, 1).build()
    box = world.new_body().dynamic().position(0, 4).box(1, 1).build()

    for _ in range(60):
        world.step(1 / 60, 4)

:doc:`getting_started/install` covers installing it, and
:doc:`getting_started/quickstart` builds a first scene step by step.

.. toctree::
   :maxdepth: 2
   :caption: Getting started

   getting_started/install
   getting_started/quickstart

.. A "Guides" toctree goes here, between Getting started and Overviews, once
   there are guides to put in it.

.. toctree::
   :maxdepth: 2
   :caption: Overviews

   glance/index

.. toctree::
   :maxdepth: 2
   :caption: API reference

   api/api
