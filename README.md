# box2d-py
Python Bindings for Box2D v3 using CFFI

[![Documentation Status](https://readthedocs.org/projects/box2d-py/badge/)](https://box2d-py.readthedocs.io/)
[![Build Status](https://github.com/giorgosg/box2d-py/actions/workflows/build-matrix.yml/badge.svg)](https://github.com/giorgosg/box2d-py/actions/workflows/build-matrix.yml)

Python bindings for the [Box2D physics engine](https://box2d.org/) version 3. Provides Pythonic access to Box2D's feature set.

## Installation

Install from source using [pipx](https://pipx.pypa.io/stable/installation/):

```bash
pipx install "git+https://github.com/giorgosg/box2d-py.git"
```

To include the testbed:

```bash
pipx install "box2d-py[testbed] @ git+https://github.com/giorgosg/box2d-py.git"
```

## Running the Testbed

```bash
box2d-testbed
```

## Example Usage


```python
from box2d import World, Vec2
# Create physics world
world = World(gravity=(0, -9.81))
# Create static ground body
ground = world.new_body().static().position((0, -5)).box(1, 10).build()
# Create dynamic bodies
bodybuilder = world.new_body().dynamic().box(0.5, 0.5)
bodies = [bodybuilder.position((x, 5)).build() for x in range(-5, 5)]
# Simulation loop
for _ in range(60):
    world.step(1/60, 4)
```

## Development Status
⚠️ Early development preview - API subject to change  
Currently supports some of the Box2D v3.0 functionality with active development ongoing.

[Full API Documentation](https://box2d-py.readthedocs.io/) | [Box2D Project](https://github.com/erincatto/box2d)
