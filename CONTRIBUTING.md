# Contributing to box2d-py

How to build box2d-py from a clone, run what CI runs, and the conventions the
code, the tests and the documentation keep to. The [README](README.md) is for
using it.

## Building from source

Box2D is compiled from source as part of the build, so it needs git, a C
compiler and CMake 3.22 or newer. Box2D itself is a git submodule, so clone
with `--recurse-submodules`, or run `git submodule update --init` in a clone
made without it. Everything on the Python side comes out of `uv.lock`.

```bash
git clone --recurse-submodules https://github.com/giorgosg/box2d-py.git
cd box2d-py
uv sync --python 3.13 --extra dev --extra testbed
```

That creates `.venv`, builds Box2D with CMake, compiles the CFFI module, and
installs the package in editable mode -- `src/` is what gets imported, so
Python edits take effect with no reinstall.

The CMake builds live in `build/cmake/<platform>`, so rebuilding after a change
only recompiles what changed. Delete `build/` to start from scratch, which is
also how to switch compilers: CMake keeps the one it found first.

pip does the same job, which is what CI uses:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,testbed]"
```

Either way, the testbed then runs from the clone:

```bash
uv run box2d-testbed
```

## Running the tests

```bash
uv run pytest
uv run pytest -m gui   # 3 more, each opening a real window
```

The `gui` tests are left out by default because they need a display. The
headless tests run the whole imgui shell on null backends, drawing through
imgui, but the `gui` tests are the only ones that open a real window and draw
with the OpenGL renderer, so they matter on an imgui_bundle upgrade. On a
machine without a display,
`xvfb-run -a uv run pytest -m gui` gives them one. The testbed's other tests
skip when the `testbed` extra is not installed, which is how most of the CI
matrix runs them.

The sharing server in `server/` has its own suite, run by `npm test`, and the
WebAssembly build has `src/tools/build_wasm.sh`, which builds the wheel and
runs the suite inside Pyodide. [`server/README.md`](server/README.md) and
[`web/README.md`](web/README.md) cover what each needs.

The desktop testbed hides the editor's **Share** and **Open link** buttons,
since its scenarios are already files. To try them, start the sharing server
locally first -- `npm run dev` in `server/`, after the setup
[`server/README.md`](server/README.md) describes -- and point the testbed at
it:

```bash
BOX2D_TESTBED_SHARING=desktop \
BOX2D_TESTBED_SERVER=http://127.0.0.1:8787 \
uv run box2d-testbed
```

## Lint, formatting and the docs

Lint and formatting are ruff, as CI runs them; `pre-commit install` runs both
on each commit:

```bash
uv run ruff check src setup.py web docs/source
uv run ruff format src setup.py web docs/source
```

ruff is pinned to one version in three places that must agree: the `dev` extra
in `pyproject.toml`, the hook's `rev` in `.pre-commit-config.yaml`, and CI's
lint job, which reads the first. So a formatter release cannot reformat files
nobody touched.

The documentation is Sphinx, published on
[readthedocs](https://box2d-py.readthedocs.io/). CI builds it with warnings as
errors and every unresolved reference reported:

```bash
uv run sphinx-build -W --keep-going -n -b html docs/source docs/build/html
```

## Conventions

### Examples run

The examples are tests, so they cannot drift from the code unnoticed:

- The Python blocks in `README.md` and in the pages under `docs/source` are
  run by `src/tests/test_doc_examples.py`. Each file's blocks run in order in
  one namespace, as a reader working down the page would run them, and a block
  written as a `>>>` session runs as a doctest, so its output is checked too.
  The pages are listed in its `PAGES`, so a new page with Python on it is added
  there.
- In the docs, Python goes in a plain `.. code-block:: python`, with no options,
  so the test finds it; shell commands are `bash`, `console` or `text`.
- A page whose examples assume names already bound, as the testbed console
  page's session assumes the names the console binds, gets them from its
  entry in the test's `PRELUDES`, bound as the testbed would bind them.
- A README block that cannot run under pytest at all is preceded by an HTML
  comment starting `not run:` and saying why, which renders as nothing on
  GitHub and PyPI:

  ````markdown
  <!-- not run: opens the testbed's window -->
  ```python
  from box2d_testbed import main
  main()
  ```
  ````

- The examples in the `box2d` package's docstrings run too, through
  `src/tests/test_doctests.py`. Each has to stand on its own, importing what it
  uses, as a reader copying it would have to.

### The API

Some rules hold across the whole API, and a test holds each one:

- Anywhere box2d-py takes a point, it accepts any vector-like: a tuple, a list,
  a `Vec2` or a raw `b2Vec2`. `Vec2` itself, and the body builder's `position`
  and `linear_velocity`, also take the two components as separate scalars.
  `src/tests/test_point_conformance.py` tries every point-taking parameter with
  every form, and fails when a new one appears without being added to it.
- Engine objects refuse attributes they do not define, so a misspelt property
  raises instead of quietly setting nothing (`test_fixed_attributes.py`).
- An argument Box2D rejects raises `box2d.InvalidInputError` from the call
  that passed it, and leaves the world as it was (`test_invalid_input.py`).
- Every call into Box2D passes the number of arguments its header declares
  (`test_api_arity.py`), which is what catches a signature that changed on a
  Box2D upgrade while keeping its name.

### The tests

- `src/tests/conftest.py` provides a `world` fixture, a fresh world destroyed
  after the test, and `random_left_as_it_was` for a test that seeds Python's
  `random`. It also points `BOX2D_TESTBED_SCENARIOS` at a temporary directory
  for the whole session, so no test reads or writes your own scenarios.
- A test module that needs the testbed's imgui starts with
  `pytest.importorskip("imgui_bundle", reason="needs the testbed extra")`. In
  a module where only some tests need it, those few carry a `skipif` mark
  instead, as `needs_gui_stack` does in `test_testbed.py`, so the rest still
  run without the extra. A test that opens a window is marked `gui`.

### Shipped scenarios

The scenarios shipped in `src/box2d_testbed/tb_*.py` double as examples of the
library, so they keep to these:

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

### Commits

A commit's subject is one sentence in the imperative saying what changes, such
as "Let Mat22.solve take any vector-like, as the other Mat22 methods do", with
no prefix. The body, where there is one, says what the change does and why.
