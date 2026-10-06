# box2d-py
Python Bindings for Box2D v3 using CFFI

[![Documentation Status](https://readthedocs.org/projects/box2d-py/badge/)](https://box2d-py.readthedocs.io/)
[![Build Status](https://github.com/giorgosg/box2d-py/actions/workflows/build-matrix.yml/badge.svg)](https://github.com/giorgosg/box2d-py/actions/workflows/build-matrix.yml)

Python bindings for the [Box2D physics engine](https://box2d.org/), built
against Box2D `main` rather than a tagged release. Provides Pythonic access to
Box2D's feature set, on Linux, macOS and Windows.

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

Box2D is compiled from source as part of the build, so it needs git, a C
compiler and CMake 3.22 or newer. Everything on the Python side
comes out of `uv.lock`.

```bash
git clone --recurse-submodules https://github.com/giorgosg/box2d-py.git
cd box2d-py
uv sync --python 3.13 --extra dev --extra testbed
```

That creates `.venv`, builds Box2D with CMake, compiles the CFFI module, and installs the package in editable mode -- `src/` is what gets
imported, so Python edits take effect with no reinstall.

The CMake builds live in `build/cmake/<platform>`, so rebuilding after a change
only recompiles what changed. Delete `build/` to start from scratch, which is
also how to switch compilers: CMake keeps the one it found first.

Then the testbed and the tests:

```bash
uv run box2d-testbed
uv run pytest
uv run pytest -m gui   # 3 more, each opening a real window
```

Lint and formatting are ruff, as CI runs them; `pre-commit install` runs both
on each commit:

```bash
uv run ruff check src setup.py web docs/source
uv run ruff format src setup.py web docs/source
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

Keyboard shortcuts are ignored while the editor or the console has the
keyboard, so typing `pr` into either does not pause the simulation.

## Writing scenarios in the testbed

The **Editor** tab, next to Simulation, edits scenario files and reloads them
into the running app. `Ctrl+S` writes the file, executes it, and rebuilds the
world around what it defines -- so the loop is edit, save, watch, with nothing
restarted.

Your own scenarios are ordinary Python files in a directory outside the
project:

| | |
|---|---|
| Linux | `~/.local/share/box2d-testbed/scenarios` |
| macOS | `~/Library/Application Support/box2d-testbed/scenarios` |
| Windows | `%APPDATA%\box2d-testbed\scenarios` |

`BOX2D_TESTBED_SCENARIOS` points that somewhere else, which is how a directory
of scenarios lives in a project of your own. They are loaded at startup and
appear in the Tests panel beside the shipped ones.

**New** starts from a template. **Fork** copies whatever is open -- including
any of the shipped `tb_*.py`, which open read-only -- into your own directory,
renaming its scenarios to `... copy` so the fork sits beside the original
rather than replacing it, and rewriting its imports so the file stands alone.
The Scenario menu also opens the file behind the scenario that is running,
which is the quick way to find the one worth forking.

In the browser build, **Share** uploads the current editor buffer and copies its
immutable link. **Open link** accepts either that URL or its complete SHA-256
hash. Downloaded scenarios open read-only and are not executed: review the
source, then press **Run**, or **Fork** it into an editable in-browser file.

The desktop app keeps these server controls hidden by default; its scenarios
are already persistent files. They can be enabled explicitly for development:

```bash
BOX2D_TESTBED_SHARING=desktop \
BOX2D_TESTBED_SERVER=http://127.0.0.1:8787 \
box2d-testbed
```

There are no accounts and every shared scenario is public to anyone with its
link.

A scenario that will not compile, or that raises while building, leaves the
scene you had running alone and reports itself: the message and the line in the
editor, the traceback in the scenario's own panel. A per-frame hook that raises
is reported once and then not called again, so a broken `after_step` neither
takes the window down nor floods the terminal.

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

- **`setup`** builds the scene. Reset and `self.rebuild()` throw the scene away
  and call it again, keeping the controls as they are.
- **Controls** (`UI.float`, `UI.int`, `UI.bool`, `UI.select`, `UI.button`) appear
  in the scenario's panel. Read them as attributes. A callback runs when one
  changes, but never before `setup` has built the scene, so it can rely on what
  `setup` made: one that changes how the scene is built calls
  `self.rebuild()`, and one that tunes something in place just sets it.
- **`status`** returns a line, or a list of lines, shown at the top left of the
  view. `debug_draw(self, debug_draw)` draws in the world instead, for labels
  that belong to something in it.
- **`after_step(dt)`** runs after every step, and `on_key_down(key)`,
  `on_key_up(key)` and the `on_mouse_*` handlers take input. Dragging bodies
  with the mouse is already handled.
- **`camera_center` and `camera_zoom`** frame the scenario when it opens. Leave
  them out to frame whatever moves. The **Copy** button in the status bar
  copies the current view as these two lines.

The shipped scenarios double as examples of the library, so they keep to a few
conventions:

- The docstring says what the scenario shows, what to look at and why, and any
  keys it takes.
- Bodies are made with the builder, `world.new_body()...build()`, with
  `.static()` spelt out for the ground.
- Comments explain the physics or the reason for a number, not what the next
  line does.
- Only the public API: nothing from `box2d._box2d` or `ffi`, and no
  underscore attributes.
- Controls give `min=` and `max=` by keyword, and use `UI.float` for anything
  physical.
- Imports run standard library, then `box2d`, then the testbed.

## The console

The **Console** panel along the bottom is a Python prompt on the running
simulation. `test`, `world`, `state` and `app` are bound to what is running and
rebound after every rebuild, `box2d` and `Vec2` are imported, and names you
define stay defined.

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

The prompt is a small code editor, so a block can be typed into it with
highlighting and auto-indent, and it grows as you go; a blank line closes the
block and runs it, as at any prompt. Completion works on the live objects
themselves -- `world.` lists what that world actually has -- because it evaluates
the name to the left of the dot, which is also the reason to complete a name
rather than the result of a call.

The output above the prompt can be selected and copied: drag across it,
double-click a word, `Ctrl+C`. Clicking in it without selecting anything hands
the keyboard back to the prompt, so reading something does not mean clicking
back before you can type again.

Between this and the editor, most questions about a scenario can be answered
without restarting it.

## Sharing server

[`server/`](server/README.md) contains the Cloudflare Worker and D1 schema for
the public, content-addressed scenario store. Posting Python source returns a
shareable `/s/<sha256>` URL; following it returns exactly those UTF-8 bytes.
It is what the editor's **Share** and **Open link** buttons talk to, as
described above.

## Running in a browser

The testbed also runs in a browser: CPython, Box2D and the bindings compiled to
WebAssembly with Pyodide, drawing through imgui into a canvas. It is single
threaded, and what you write in the editor lasts until the page reloads unless
you share it. [`web/README.md`](web/README.md) covers building the wheel,
checking it under node, and serving it.

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

## Development Status

⚠️ Early development preview - API subject to change

Tracks Box2D `main`, currently the 3.2.0 API (`box2d.BOX2D_VERSION`) ahead of
it being tagged, so what is bound here moves with upstream.

Bound and covered by tests on Linux, macOS and Windows for Python 3.12 and
3.13, and in WebAssembly:

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

[Full API Documentation](https://box2d-py.readthedocs.io/) | [Box2D Project](https://github.com/erincatto/box2d)
