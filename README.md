# box2d-py
Python Bindings for Box2D v3 using CFFI

[![Documentation Status](https://readthedocs.org/projects/box2d-py/badge/)](https://box2d-py.readthedocs.io/)
[![Build Status](https://github.com/giorgosg/box2d-py/actions/workflows/build-matrix.yml/badge.svg)](https://github.com/giorgosg/box2d-py/actions/workflows/build-matrix.yml)

Python bindings for the [Box2D physics engine](https://box2d.org/) version 3.2.
Provides Pythonic access to Box2D's feature set, on Linux, macOS and Windows.

## Installation

Install from source using pip

```bash
pip install "git+https://github.com/giorgosg/box2d-py.git"
```

To include the testbed:

```bash
pip install "box2d-python[testbed] @ git+https://github.com/giorgosg/box2d-py.git"
```

Or Install from pypi:

```bash
pip install box2d-python[testbed]
```

## Building from source

Box2D and enkiTS are compiled from source as part of the build, so it needs
git, a C compiler and CMake 3.22 or newer. Everything on the Python side
comes out of `uv.lock`.

```bash
git clone --recurse-submodules https://github.com/giorgosg/box2d-py.git
cd box2d-py
uv sync --python 3.13 --extra dev --extra testbed
```

That creates `.venv`, builds Box2D and enkiTS with CMake, compiles the CFFI
module, and installs the package in editable mode -- `src/` is what gets
imported, so Python edits take effect with no reinstall.

Then the testbed and the tests:

```bash
uv run box2d-testbed
uv run pytest          # 1243 tests
uv run pytest -m gui   # 3 more, each opening a real window
```

pip does the same job, which is what CI uses:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,testbed]"
```

## Running the Testbed

```bash
box2d-testbed
```

Each scenario has its own controls in the side panel. Everything the panel
offers is also on the keyboard, so a scenario can be driven without moving
the mouse off it:

| key | |
|---|---|
| `p` | pause and resume |
| `o` | single step |
| `r` | restart the scenario |
| `Home` | reset the view |
| `[` `]` | previous and next scenario |

Drag to pan, scroll to zoom. A scenario can set the view it opens with
through `camera_center` and `camera_zoom`; the status bar shows the current
pair and copies it, so a view can be framed by hand and pasted back into the
scenario as its default.

## Example Usage


```python
from box2d import World
# Create physics world
world = World(gravity=(0, -9.81))
# Create static ground body (box takes full width and height)
ground = world.new_body().static().position(0, -5).box(20, 1).build()
# Create dynamic bodies
bodybuilder = world.new_body().dynamic().box(0.5, 0.5)
bodies = [bodybuilder.position(x, 5).build() for x in range(-5, 5)]
# Simulation loop
for _ in range(180):
    world.step(1/60, 4)
# Bodies have come to rest on top of the ground
print(round(bodies[0].position.y, 2))  # -4.25
```

## Development Status

⚠️ Early development preview - API subject to change

Tracks Box2D 3.2. Bodies, all seven joint types, every shape, sensor and
contact events, the collision queries and casts, and character movement are
bound and covered by tests; 1243 of them run on Linux, macOS and Windows for
Python 3.12 and 3.13.

World snapshots are not bound yet.

[Full API Documentation](https://box2d-py.readthedocs.io/) | [Box2D Project](https://github.com/erincatto/box2d)
