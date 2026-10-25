# box2d-py

[![Documentation Status](https://readthedocs.org/projects/box2d-py/badge/)](https://box2d-py.readthedocs.io/)
[![Build Status](https://github.com/giorgosg/box2d-py/actions/workflows/build-matrix.yml/badge.svg)](https://github.com/giorgosg/box2d-py/actions/workflows/build-matrix.yml)

Python bindings for the [Box2D physics engine](https://box2d.org/) v3.2.0,
built with CFFI. Box2D itself is compiled into the package and does the
simulating; the bodies, shapes, joints, queries and events around it are
ordinary Python objects. It runs on Linux, macOS and Windows with Python 3.12,
3.13 or 3.14, and in WebAssembly under Pyodide. A testbed comes with it: a
window of example scenarios to run and edit, and to write your own in.

## Installation

```bash
pip install "git+https://github.com/giorgosg/box2d-py.git"
```

The testbed is the `testbed` extra:

```bash
pip install "box2d-python[testbed] @ git+https://github.com/giorgosg/box2d-py.git"
```

Either builds Box2D from source, so it needs git, a C compiler and CMake 3.22
or newer. The releases on PyPI, 0.1.x, predate the Box2D v3.2.0 port this
README describes, and their API differs from it.
[Installation](https://box2d-py.readthedocs.io/en/latest/getting_started/install.html)
in the documentation has the rest: building from a clone, and how the
versions are numbered.

## Example usage

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
    world.step(1 / 60, 4)
# Bodies have come to rest on top of the ground
print(round(bodies[0].position.y, 2))  # -4.25
```

Box2D checks what it is given. An argument it rejects raises
`box2d.InvalidInputError`, a `ValueError`, from the call that passed it --
naming the Box2D function and the check that failed -- and leaves the world as
it was:

```python
>>> body = world.new_body().dynamic().build()
>>> body.add_circle(radius=0.5, density=-1)
Traceback (most recent call last):
  ...
box2d.InvalidInputError: b2CreateCircleShape rejected its input: b2IsValidFloat( def->density ) && def->density >= 0.0f (in b2CreateShape)
```

Box2D's other diagnostics, such as a body going unstable, are logged to the
`box2d` logger.

The [quickstart](https://box2d-py.readthedocs.io/en/latest/getting_started/quickstart.html)
builds a first scene step by step, and the
[documentation](https://box2d-py.readthedocs.io/) covers the rest of the API.

## The testbed

```bash
box2d-testbed
```

A window of scenarios, each showing one part of Box2D running live, with its
own controls in the side panel. `p` pauses, `o` steps, `r` resets the
scenario, `Home` resets the view, and `[` `]` move between scenarios. Drag a
body with the left button to pull it, drag with the middle button to pan, and
scroll to zoom.
[Running the testbed](https://box2d-py.readthedocs.io/en/latest/testbed/running.html) covers the panels, the settings
and the rest.

### What a scenario looks like

A scenario is a class, and declaring it registers it under the category and
name it gives:

```python
from box2d_testbed.base_test import BaseTest, UI


class Drop(BaseTest, category="Bodies", name="Drop"):
    """A box dropped onto the ground from a height you choose.

    Watch it settle: Box2D puts a body to sleep once it has been still for a
    moment, and the status line says when that happens.
    """

    camera_center = (0, 5)
    camera_zoom = 12.0

    drop_height = UI.float(8.0, min=1.0, max=20.0)

    def setup(self):
        self.world.new_body().static().segment((-20, 0), (20, 0)).build()
        self.box = (
            self.world.new_body()
            .dynamic()
            .position(0, self.drop_height)
            .box(1, 1, friction=0.4)
            .build()
        )

    @drop_height.callback
    def on_drop_height(self, key, value):
        # Where the box starts is part of building the scene, so build it again.
        self.rebuild()

    def status(self):
        return "asleep" if not self.box.awake else f"height {self.box.position.y:.1f}"
```

`setup` builds the scene, the `UI` declarations are controls in its panel, and
`status` is shown at the top left of the view. Your own scenarios are Python
files in a directory of your own, which the **Editor** tab, beside the
simulation, edits: `Ctrl+S` saves the file, runs it, and puts its scenario on
screen, with nothing restarted. **Fork** copies any scenario, the shipped
ones included, into a file of your own to change.
[Writing scenarios](https://box2d-py.readthedocs.io/en/latest/testbed/scenarios.html) covers all of it.

### The console

The **Console** panel along the bottom is a Python prompt on the running
simulation, with `test` and `world` bound to what is running, and completion
on the live objects. [The console](https://box2d-py.readthedocs.io/en/latest/testbed/console.html) covers it.

## Running in a browser

The testbed also runs in a web page: CPython, Box2D and the bindings compiled
to WebAssembly with Pyodide. It is single threaded, and what you write in its
editor lasts until the page reloads, unless you share it: **Share** uploads a
scenario and copies its public link, and **Open link** opens one read-only,
without running it until you press **Run**.
[The testbed in a browser](https://box2d-py.readthedocs.io/en/latest/testbed/browser.html) covers the differences, and
[`web/README.md`](https://github.com/giorgosg/box2d-py/blob/main/web/README.md)
building and serving it.

## Development status

⚠️ Early development preview - API subject to change

Built against Box2D's v3.2.0 release (`box2d.BOX2D_VERSION`); the `box2d`
submodule is pinned to that tag. The binding's own version is
`box2d.__version__`.

Bound and covered by tests on Linux, macOS and Windows for Python 3.12, 3.13
and 3.14, and in WebAssembly:

- bodies, every shape, and chains
- every joint type -- distance, filter, motor, mover, pogo, prismatic,
  revolute, weld and wheel -- plus a mouse joint for dragging
- sensor, contact, hit, body-move and joint events, and the pre-solve,
  pre-continuous, custom filter and material mixing callbacks
- the collision queries and casts
- character movement, both kinematic (the mover queries and plane solver) and
  dynamic (the mover and pogo joints)
- solver tuning, profiling counters and a deterministic state hash

Not bound yet: world snapshots, and recording and replay.

[CONTRIBUTING.md](https://github.com/giorgosg/box2d-py/blob/main/CONTRIBUTING.md) covers building from source, the tests and
the project's conventions.

## Links

[Documentation](https://box2d-py.readthedocs.io/) |
[Box2D](https://box2d.org/) |
[Box2D on GitHub](https://github.com/erincatto/box2d) |
[Contributing](https://github.com/giorgosg/box2d-py/blob/main/CONTRIBUTING.md)
