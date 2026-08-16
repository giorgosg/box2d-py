# box2d-py
Python Bindings for Box2D v3 using CFFI

[![Documentation Status](https://readthedocs.org/projects/box2d-py/badge/)](https://box2d-py.readthedocs.io/)
[![Build Status](https://github.com/giorgosg/box2d-py/actions/workflows/build-matrix.yml/badge.svg)](https://github.com/giorgosg/box2d-py/actions/workflows/build-matrix.yml)

Python bindings for the [Box2D physics engine](https://box2d.org/) version 3.2.
Provides Pythonic access to Box2D's feature set, on Linux, macOS, Windows and
in the browser.

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

## Running the Testbed

```bash
box2d-testbed
```

53 scenarios across 9 categories -- bodies, shapes, joints, stacking,
continuous collision, events, character movement, collision queries and
benchmarks -- each with its own controls in the side panel.

Everything the panel offers is also on the keyboard, so a scenario can be
driven without moving the mouse off it:

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

### Drawing without OpenGL

```bash
BOX2D_TESTBED_RENDERER=imgui box2d-testbed
```

Draws through imgui's draw list instead of OpenGL, which needs no GL context
and is what the browser build uses. Which one is quicker depends on the
scene -- median milliseconds per frame spent drawing, 200 frames each:

| scenario | OpenGL | imgui |
|---|---|---|
| Benchmark/Many Pyramids (1380 flat shapes) | 33.9 | 24.3 |
| Shapes/Rounded | 4.0 | 7.0 |

Flat shapes go straight into the draw list, so it wins there. Rounded ones
cost it: every corner becomes a fan of triangles built in Python, which the
OpenGL renderer gets from the shader instead.

`src/tools/bench_render.py` produces these, and counts the primitives each
renderer was asked for so it is clear both drew the same scene.

## Building for the browser

The bindings cross-compile to WebAssembly, so Box2D can be driven from Python
in a browser through [Pyodide](https://pyodide.org). The testbed does not come
along -- it needs OpenGL -- but the whole physics API does.

```bash
pip install pyodide-build
pyodide xbuildenv install 0.29.4   # must match your Python; see note below
./src/tools/build_wasm.sh
```

That builds a `wasm32` wheel into `dist/`, then verifies it by creating a
Pyodide runtime, installing the wheel and running the test suite inside
WebAssembly. 759 of the tests run there; the rest need the testbed's GUI or
inspect the host build.

Two things to know:

- **The cross-build environment is tied to your Python version.** 0.29.4 is
  Python 3.13; the 314 and 315 lines need 3.14 and 3.15. Run
  `pyodide xbuildenv search` to see which are compatible with the interpreter
  you have.
- **The wasm build is single threaded.** enkiTS needs a real thread pool, and
  Emscripten only has one with `SharedArrayBuffer` and the COOP/COEP headers
  that go with it. `box2d.HAS_THREADS` is `False` there, and `World(threads=N)`
  for N above one raises rather than pretending. Box2D itself is unaffected;
  only the task scheduler is missing.

The same switch works natively, if you want a build without the C++ thread
pool: `BOX2D_PY_NO_THREADS=1 python src/tools/build_cffi.py`.

### The testbed in a browser

The testbed follows, through the imgui renderer -- it draws with imgui's draw
list rather than OpenGL, so it needs no GL context:

```bash
python web/serve.py       # then open http://localhost:8000
```

That copies the newest wheel next to `web/index.html` and serves both. The
page loads Pyodide from a CDN, pulls `imgui-bundle` from Pyodide's own
package index, and starts the testbed.

The Pyodide version in `web/index.html` must match the one the wheel was
built against -- a wheel carries an ABI tag (`pyemscripten_2025_0`) and will
not load on another.

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
Python 3.12 and 3.13, and most run in WebAssembly as well.

World snapshots are not bound yet.

Active development, and the API is still free to change.

[Full API Documentation](https://box2d-py.readthedocs.io/) | [Box2D Project](https://github.com/erincatto/box2d)
