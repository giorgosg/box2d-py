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
uv run pytest          # 1360 tests
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

A scenario that will not compile, or that raises while building, leaves the
scene you had running alone and reports itself: the message and the line in the
editor, the traceback in the scenario's own panel. A per-frame hook that raises
is reported once and then not called again, so a broken `after_step` neither
takes the window down nor floods the terminal.

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

Tracks Box2D `main`, which is ahead of the 3.1.1 release and not yet tagged
3.2.0, so what is bound here moves with upstream.

Bodies, all seven joint types, every shape, sensor and contact events, the
collision queries and casts, and character movement are bound and covered by
tests; 1360 of them run on Linux, macOS and Windows for Python 3.12 and 3.13.

World snapshots are not bound yet.

[Full API Documentation](https://box2d-py.readthedocs.io/) | [Box2D Project](https://github.com/erincatto/box2d)
