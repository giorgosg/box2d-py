#!/bin/bash
# Prepares a Claude Code cloud session: the Box2D source, the Python
# environment (which compiles the CFFI module), and the sharing server's
# node dependencies. Local sessions are left alone.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# Box2D is compiled from source, so the build needs it checked out.
git submodule update --init --recursive

# Creates .venv, builds Box2D with CMake, compiles the CFFI module
# and installs the package in editable mode -- the same as the README.
uv sync --python 3.13 --extra dev --extra testbed

# The Cloudflare Worker in server/ has its own vitest suite. npm ci rather
# than install: it never rewrites package-lock.json, whose libc fields the
# container's npm 10 would otherwise strip.
(cd server && npm ci --no-audit --no-fund)

# Put the venv first so `pytest`, `black` and `python` work without `uv run`.
echo "export PATH=\"$CLAUDE_PROJECT_DIR/.venv/bin:\$PATH\"" >> "$CLAUDE_ENV_FILE"
