Installation
============

box2d-python needs Python 3.12, 3.13 or 3.14, on Linux, macOS or Windows. It
also runs in WebAssembly, under Pyodide.

From PyPI
---------

.. code-block:: bash

    pip install --pre box2d-python

The testbed, a window of example scenarios to run and edit, is the
``testbed`` extra:

.. code-block:: bash

    pip install --pre "box2d-python[testbed]"

``--pre`` is needed while the release is a candidate, 3.2.0rc1: pip skips
pre-releases unless asked. Wheels are built for Linux (x86_64 and aarch64,
glibc and musl), macOS (arm64 and x86_64) and Windows (AMD64), so nothing is
compiled there; elsewhere pip builds the source package, which needs the tools
listed under building from source. The 0.1.x releases on PyPI predate the Box2D v3.2 port
and have a different API.

From git
--------

The current ``main``, built from source, so it needs the same tools as
building from source does, below:

.. code-block:: bash

    pip install "box2d-python[testbed] @ git+https://github.com/giorgosg/box2d-py.git"

From source
-----------

Box2D is compiled from source as part of the build. That needs:

- git
- a C compiler
- CMake 3.22 or newer
- Box2D itself, which is a git submodule, so clone with
  ``--recurse-submodules``, or run ``git submodule update --init`` in a clone
  made without it.

.. code-block:: bash

    git clone --recurse-submodules https://github.com/giorgosg/box2d-py.git
    cd box2d-py
    pip install -e ".[testbed]"

``-e`` installs in editable mode: ``src/`` is what gets imported, so edits to
the Python take effect without installing again. The project's
`CONTRIBUTING.md <https://github.com/giorgosg/box2d-py/blob/main/CONTRIBUTING.md>`_
covers the rest of development, from the ``uv`` setup to running the tests,
and `web/README.md <https://github.com/giorgosg/box2d-py/blob/main/web/README.md>`_
covers building for WebAssembly.

Versions
--------

From its first release for Box2D v3.2.0, the binding's version follows
Box2D's. Its releases for Box2D v3.2.0 are numbered:

- ``3.2.0rc1``, ``3.2.0rc2`` and so on, for release candidates;
- ``3.2.0``, the release;
- ``3.2.0.1``, ``3.2.0.2`` and so on, for fixes to the binding alone, built
  against the same Box2D.

These are ordinary `PEP 440 <https://peps.python.org/pep-0440/>`_ versions,
so pip orders them as listed. ``box2d-python>=3.2.0rc1,<3.3`` asks for any of
them. The release candidate has to be named in the lower bound: PEP 440 sorts
``3.2.0rc1`` before ``3.2``, and pip skips pre-releases unless a specifier
names one, so ``>=3.2`` alone would leave the candidates out.

Two values tell the versions apart at runtime. ``box2d.__version__`` is the
binding's, read from the installed package; imported from a source tree that
was never installed, it is ``"0+unknown"``:

.. code-block:: python

    import box2d

    print(box2d.__version__)

``box2d.BOX2D_VERSION`` is the Box2D the binding was built against:

.. code-block:: python

    >>> box2d.BOX2D_VERSION
    (3, 2, 0)

Threads
-------

``box2d.HAS_THREADS`` says whether a world can step on more than one thread.
Box2D brings its own thread pool, so it is True everywhere but WebAssembly,
where the browser runtime has no threads and Box2D is built without them.
There, ``World(threads=2)`` raises :class:`RuntimeError`.

.. code-block:: python

    from box2d import HAS_THREADS, World

    world = World(threads=4 if HAS_THREADS else 1)
