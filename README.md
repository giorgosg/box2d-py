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

Each scenario has its own controls in the side panel, and everything the panel
offers is also on the keyboard:

| key | |
|---|---|
| `p` | pause and resume |
| `o` | single step |
| `r` | restart the scenario |
| `Home` | reset the view |
| `[` `]` | previous and next scenario |

Drag a body to pull it around, drag with the middle button to pan, and scroll
to zoom. The keys are ignored while the editor or the console has the keyboard,
so typing `pr` into either does not pause the simulation.

### Writing scenarios

The **Editor** tab, next to Simulation, edits scenario files. `Ctrl+S` writes
the file, runs it, and rebuilds the world around what it defines, so the loop
is edit, save, watch, with nothing restarted. A scenario that will not compile,
or raises while building, leaves the running scene alone and reports the error
and its line in the editor.

Your own scenarios are ordinary Python files, loaded at startup beside the
shipped ones, from a directory outside the project:

| | |
|---|---|
| Linux | `~/.local/share/box2d-testbed/scenarios` |
| macOS | `~/Library/Application Support/box2d-testbed/scenarios` |
| Windows | `%APPDATA%\box2d-testbed\scenarios` |

`BOX2D_TESTBED_SCENARIOS` points it somewhere else, such as a project of your
own.

**New** starts from a template. **Fork** copies whatever is open -- the
shipped `tb_*.py` included, which open read-only -- into your directory, under
`... copy` names so the fork sits beside the original. The Scenario menu opens
the file behind the running scenario, which is the quick way to find one worth
forking.

### What a scenario looks like

A scenario is a class. Declaring it registers it, under the category and name
it gives:

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

- **`setup`** builds the scene. Reset and `self.rebuild()` throw it away and
  call `setup` again in a new world, keeping the controls and the view, so a
  reset scene runs exactly as it first did -- unless it is built from Python's
  random numbers. Set anything the scene needs on the world here, and read
  `self.world` rather than keeping it.
- **Controls** (`UI.float`, `UI.int`, `UI.bool`, `UI.select`, `UI.button`)
  appear in the scenario's panel and read as attributes. A callback runs when
  one changes, never before `setup`: one that changes how the scene is built
  calls `self.rebuild()`, and one that tunes something in place just sets it.
- **`status`** returns a line, or a list of lines, shown at the top left of the
  view. `debug_draw(self, debug_draw)` draws in the world instead.
- **`after_step(dt)`** runs after every step, and `on_key_down(key)`,
  `on_key_up(key)` and the `on_mouse_*` handlers take input. One that raises is
  reported once and not called again.
- **`camera_center` and `camera_zoom`** frame the scenario when it opens; leave
  them out to frame whatever moves. The **Copy** button in the status bar
  copies the current view as these two lines.

The shipped scenarios keep to a few conventions of their own, as examples of
the library; [CONTRIBUTING.md](https://github.com/giorgosg/box2d-py/blob/main/CONTRIBUTING.md#shipped-scenarios) lists them.

### The console

The **Console** panel along the bottom is a Python prompt on the running
simulation. `test`, `world`, `state` and `app` are bound to what is running and
rebound after every rebuild, `box2d` and `Vec2` are imported, and names you
define stay defined.

<!-- not run: a session at the running testbed's console -->
```python
>>> len(list(world.bodies))
41
>>> for body in world.bodies:
...     body.linear_velocity = (0, 20)
...
>>> test.camera_zoom
14.0
```

| key | |
|---|---|
| `Enter` | run it, or take another line if it is not a complete statement yet |
| `Tab` | complete the name left of the cursor, or indent if there is none |
| `Ctrl+R` | search what you have run |
| `Up` `Down` | walk the history, while the prompt is one line |

Completion works on the live objects -- `world.` lists what that world actually
has -- and a blank line closes a block and runs it, as at any prompt.

## Running in a browser

The testbed also runs in a browser: CPython, Box2D and the bindings compiled to
WebAssembly with Pyodide, drawing through imgui into a canvas. What you write
in its editor lasts until the page reloads, unless you share it: **Share**
uploads the editor's buffer and copies a link to it, and **Open link** loads
one, read-only and not run until you press **Run**. Every shared scenario is
public to anyone with its link.

[`web/README.md`](https://github.com/giorgosg/box2d-py/blob/main/web/README.md) covers building and serving it, and
[`server/README.md`](https://github.com/giorgosg/box2d-py/blob/main/server/README.md) the store that sharing talks to.

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
