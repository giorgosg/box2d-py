#!/usr/bin/env bash
# Build box2d-python as a Pyodide wheel, and check that it runs.
#
# The wheel is WebAssembly, so it cannot be imported by the Python that built
# it. Verification therefore means creating a Pyodide virtual environment --
# a real CPython-on-wasm running under node -- installing the wheel into it,
# and running the suite there.
#
# Prerequisites, once:
#     pip install pyodide-build
#     pyodide xbuildenv install 0.29.4
#
# The xbuildenv version must match the host Python: 0.29.4 is Python 3.13,
# and the 314/315 lines need 3.14/3.15. `pyodide xbuildenv search` lists
# which are compatible with the interpreter you have.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

# emsdk installs its own node, which pyodide venv needs on PATH but does not
# add itself.
EMSDK_NODE="$(find "$HOME/.cache/pyodide-build" -maxdepth 5 -type d -path '*/emsdk/node/*/bin' 2>/dev/null | head -1)"
if [ -n "$EMSDK_NODE" ]; then
    export PATH="$EMSDK_NODE:$PATH"
fi

if ! command -v node > /dev/null; then
    echo "no node on PATH; pyodide venv needs one" >&2
    exit 1
fi

echo "==> Building the wasm32 wheel"
pyodide build

WHEEL="$(ls -t dist/*wasm32.whl | head -1)"
echo "==> Built $WHEEL"

VENV="${BOX2D_WASM_VENV:-build/pyodide-venv}"
echo "==> Creating a Pyodide runtime at $VENV"
rm -rf "$VENV"
pyodide venv "$VENV"

echo "==> Installing the wheel into it"
"$VENV/bin/pip" install --quiet "$WHEEL" pytest

echo "==> Running the suite inside WebAssembly"
# The testbed needs imgui and OpenGL, which this runtime has neither of, and
# the build-config tests inspect the host build rather than this one.
"$VENV/bin/python" -m pytest src/tests -q -p no:cacheprovider \
    --ignore=src/tests/test_testbed.py \
    --ignore=src/tests/test_testbed_ui.py \
    --ignore=src/tests/test_testbed_gui.py \
    --ignore=src/tests/test_human.py \
    --ignore=src/tests/test_build_config.py

echo "==> Running the testbed's Python inside WebAssembly"
# imgui_bundle is in Pyodide's own index but its glfw dependency is not, and
# munch is a pure-Python dependency pip will not resolve without it.
"$VENV/bin/pip" install --quiet --no-deps imgui_bundle munch
"$VENV/bin/python" src/tools/wasm_testbed_check.py

echo
echo "==> $WHEEL is good"

echo
echo "==> To try it in a browser:  python web/serve.py"
