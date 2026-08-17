# Running the testbed in a browser

The testbed runs unchanged in a browser: CPython, Box2D and the CFFI bindings
are all compiled to WebAssembly, and hello_imgui draws into a canvas through
SDL. Getting there takes one wheel build with Pyodide's cross-compiler, and
then a static server.

Two files do the work: `index.html` boots Pyodide and runs the testbed's
Python, and `serve.py` puts the freshly built wheel on the same origin as the
page and serves the directory.

## What you need

| | |
|---|---|
| a **Python 3.13** interpreter | `pyodide xbuildenv` 0.29.4 is a 3.13 environment and refuses another host version. A distro Python 3.12 will not do; `uv python install 3.13` is the easy way. |
| the submodules, CMake, a C compiler | the same as a native build -- Box2D and enkiTS are compiled from source, here by emscripten. |
| ~1.5 GB of disk | emsdk and the cross-build environment, cached under `~/.cache/pyodide-build`. |
| node (optional) | only for `build_wasm.sh`, which runs the test suite inside WebAssembly. `pyodide build` does not need it. |

## One-time setup

`pyodide-build` pulls its own pinned dependency set, so keep it out of the
project's `.venv` rather than letting it fight `uv.lock`:

```bash
uv venv --python 3.13 ~/.cache/box2d-pyodide-env
VIRTUAL_ENV=~/.cache/box2d-pyodide-env uv pip install pyodide-build
export PATH="$HOME/.cache/box2d-pyodide-env/bin:$PATH"
```

`uv venv` does not put `pip` in the environment, which is why the install goes
through `uv pip` with `VIRTUAL_ENV` set. With plain `python -m venv` and its
own `pip install pyodide-build`, that step is the usual one.

Then fetch the cross-build environment -- emscripten, and a matching CPython
built for wasm. A few hundred MB, once:

```bash
pyodide xbuildenv install 0.29.4
```

`pyodide xbuildenv search` lists the versions compatible with the interpreter
you have, if 0.29.4 ever stops being the right one. Changing it means changing
three other things too; see [Versions have to agree](#versions-have-to-agree).

## Build the wheel

From the project root:

```bash
pyodide build
```

A minute or two from cold, and it leaves a wasm32 wheel in `dist/`:

```
dist/box2d_python-0.1.3-cp313-cp313-pyemscripten_2025_0_wasm32.whl   ~320 KiB
```

The build prints a different, longer name at the end
(`...emscripten_4_0_9_wasm32.whl`) and then repacks it to the
`pyemscripten_2025_0` tag above. That second name is the one that matters: it
is the ABI tag Pyodide resolves against, and the file `serve.py` looks for.

To also check the wheel rather than just build it:

```bash
src/tools/build_wasm.sh
```

That builds, creates a Pyodide virtual environment -- a real CPython-on-wasm
under node -- installs the wheel into it, runs the test suite there, and
finally runs `src/tools/wasm_testbed_check.py`, which builds and simulates
every scenario with no canvas. It needs node on `PATH`; emsdk ships one, and
the script tries to find it under `~/.cache/pyodide-build`. If that lookup
comes up empty, any node 18+ on `PATH` will do.

## Serve it

```bash
python web/serve.py              # --port 8000 by default
```

It runs `prepare.py`, which copies the newest `dist/*wasm32.whl` next to
`index.html` and records its filename in `build.json` (the wheel has to be
same-origin for micropip to install it), then serves the directory with
`Cache-Control: no-store` and logs a line per request. Open
<http://localhost:8000>.

The first load pulls roughly 15 MB from the jsDelivr CDN -- the Pyodide
runtime, then `imgui-bundle` and `numpy` from Pyodide's own package index --
so it takes a while and needs network access. Afterwards the browser caches
all of it. Loading progress is reported on the page; failures land in the same
place, with the traceback.

The Cloudflare server serves these same files. From `server/`, `npm run dev`
prepares the wheel and starts the Worker plus local D1 at
<http://127.0.0.1:8787>; requests under `/s` reach the Worker and every other
matching file uses Workers Static Assets.

## Versions have to agree

Four things are pinned to each other, and the failure when they disagree is a
wheel that will not install or a runtime that will not start:

1. the **xbuildenv** version (`pyodide xbuildenv install 0.29.4`),
2. the **host Python** it requires (3.13 for 0.29.4),
3. the `pyodide.js` **CDN URL** in `index.html` (`v0.29.4`),
4. the wheel's **ABI tag**, which follows from 1 (`pyemscripten_2025_0`).

Bumping Pyodide means bumping all four together.

## Differences from the native testbed

- **One thread.** This build has no enkiTS scheduler, so the panel shows
  "Threads: 1 (this build has no scheduler)" and `box2d.HAS_THREADS` is false.
  The testbed defaults to one thread when there is no scheduler, which
  `wasm_testbed_check.py` asserts.
- **The imgui renderer, not OpenGL.** There is no PyOpenGL in the browser, so
  `index.html` sets `BOX2D_TESTBED_RENDERER=imgui` before importing anything;
  geometry is submitted to an `ImDrawList` instead of GL buffers.
- **`hello_imgui.run` returns immediately.** Under Pyodide it is patched to
  drive `requestAnimationFrame`, so the app keeps running after `app.run()`
  hands control back.
- **Nothing you write survives a reload.** The editor works -- Pyodide's
  filesystem accepts the writes -- but it is an in-memory one, so the scenario
  directory is empty again on the next load. See below.

## Sharing scenarios

The editor keeps scenarios in a directory, and in the browser that directory
lives in Pyodide's in-memory filesystem: real enough to edit and reload
against, gone on refresh. Making them persist and shareable is a store behind
`ScenarioStore` in `scenario_store.py`, which is why that is an interface with
two implementations rather than a pair of functions over `open()`.

The store now lives in [`server/`](../server/README.md):

- A Worker over **D1**. `POST /s` stores source and returns its URL; `GET
  /s/<hash>` returns it. Scenario files are a few KB of Python, so one table
  holds them. Content addressing makes every response immutable, so
  `Cache-Control: immutable` and the Cache API keep a popular scenario from
  repeatedly reading the database.
- Addressed by the complete **SHA-256** of the UTF-8 source. Not MD5: Workers'
  `crypto.subtle` does not implement it, while `hashlib.sha256` and
  `crypto.subtle.digest('SHA-256')` agree without another implementation. The
  complete digest also avoids weakening a public content address just to save
  characters in a URL.
- No accounts, and everything public. Which makes it a pastebin that accepts
  Python, so: a size cap, a rate-limiting rule on the write, and no delete
  (immutable content has nothing to update).
- **Nothing fetched is executed on its own.** Opening a shared scenario opens
  its source in the editor unrun; Run is a keypress away, but it is the reader's
  keypress. The browser uses Pyodide's asynchronous Fetch client, so a D1
  request does not block animation frames.

The page and API share one Worker origin. The web bootstrap enables **Share**
and **Open link**; the desktop app hides them unless explicitly opted in with
`BOX2D_TESTBED_SHARING=desktop`.

## The browser's imgui is older than yours

The wheel is ours to build, but `imgui-bundle` is not: the page gets it from
Pyodide's own package index through `loadPackage`, so its version is whatever
that release of Pyodide pinned -- 0.29.4 ships **1.92.4** (September 2025),
while a desktop `pip install` today gets **1.92.900**. There is no pinning
this from our side short of changing the Pyodide version, so the renderer has
to work against both.

That is not hypothetical. `ImDrawList.add_polyline` takes
`(points, col, flags, thickness)` in 1.92.4, keeping the C++ order, and
`(points, col, thickness, flags)` in 1.92.900, which swapped the last two.
`add_rect` swapped the same pair, though the testbed only ever passes its
first three arguments. So `debug_draw_imgui.py` passes thickness and flags
**by keyword**, which both versions accept, rather than relying on an order
that is right in only one of them.

Getting that wrong is quiet rather than loud, which is what makes it worth a
note here. Box2D calls the renderer through a CFFI callback, and an exception
inside one is printed and then ignored -- so the app kept running, every
filled shape still drew, and only the outlines silently went missing. It cost
nothing but a console full of `TypeError: add_polyline(): incompatible
function arguments` at one traceback per frame.

`test_every_primitive_reaches_the_installed_draw_list` in
`src/tests/test_testbed_headless.py` is the guard: it drives every primitive
against a real `ImDrawList` from the installed binding, outside the callback,
where a rejected call fails instead of being swallowed.
