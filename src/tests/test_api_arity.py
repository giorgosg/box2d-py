# tests/test_api_arity.py
"""Every Box2D call passes the number of arguments the header declares.

Upgrading Box2D was verified by checking that each lib.b2* name still existed.
That misses functions whose *signature* changed while keeping their name, and
one slipped through: 3.2 added a wakeAttached argument to b2DestroyJoint, so
releasing a dragged body crashed the testbed with "b2DestroyJoint expected 2
arguments, got 1". No test destroyed a joint, so nothing caught it.

Existence is not enough, so this compares every call site against the arity
declared in the headers the extension was built from. It is static: it needs no
call to be executed, which is the point, since the gap was in a path only
reachable by dragging with a mouse.
"""

import ast
import pathlib
import re

import pytest

HEADERS = ["box2d.h", "collision.h", "math_functions.h", "types.h", "base.h", "id.h"]
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]


def declared_arities():
    """Parameter counts for every B2_API function, read from the headers."""
    include = PROJECT_ROOT / "box2d" / "include" / "box2d"
    arities = {}
    for header in HEADERS:
        path = include / header
        if not path.exists():
            continue
        text = path.read_text()
        for match in re.finditer(
            r"B2_API\s+[A-Za-z0-9_ *]+?\s+(b2[A-Za-z0-9_]+)\s*\(([^;]*?)\)\s*;",
            text,
            re.S,
        ):
            name, params = match.group(1), match.group(2).strip()
            if params in ("void", ""):
                arities[name] = 0
                continue
            depth = count = 0
            count = 1
            for char in params:
                if char in "([":
                    depth += 1
                elif char in ")]":
                    depth -= 1
                elif char == "," and depth == 0:
                    count += 1
            arities[name] = count
    return arities


def call_sites():
    """Every lib.b2*(...) call in the binding, as (file, line, name, argcount)."""
    package = PROJECT_ROOT / "src" / "box2d"
    for path in sorted(package.rglob("*.py")):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id == "lib"
                and func.attr.startswith("b2")
            ):
                yield path.name, node.lineno, func.attr, len(node.args)


def test_headers_are_readable():
    """Guard against the audit silently passing because it parsed nothing."""
    assert len(declared_arities()) > 300


def test_call_sites_are_found():
    assert len(list(call_sites())) > 200


def test_every_call_matches_its_declared_arity():
    arities = declared_arities()
    mismatches = [
        f"{name} at {filename}:{line} passes {argc}, header declares {arities[name]}"
        for filename, line, name, argc in call_sites()
        if name in arities and argc != arities[name]
    ]
    assert not mismatches, "argument count mismatches:\n  " + "\n  ".join(mismatches)


def test_no_call_site_targets_a_missing_function():
    """A renamed or removed function must not survive as a dead call."""
    from box2d._box2d import lib

    missing = [
        f"{name} at {filename}:{line}"
        for filename, line, name, _ in call_sites()
        if not hasattr(lib, name)
    ]
    assert not missing, "calls to functions absent from the build:\n  " + "\n  ".join(
        missing
    )
