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


def accessor_declarations():
    """Every b2_* accessor declaration, as (file, line, name, implied argcount).

    A declaration like ``b2_float(lib.b2Body_GetX, lib.b2Body_SetX)`` never
    calls those functions, so they are invisible to call_sites(). The getter is
    invoked with the object's id alone, and the setter with the id, the value,
    and whatever extra_set_args says -- so their arities are implied and can be
    checked the same way.
    """
    package = PROJECT_ROOT / "src" / "box2d"
    factories = {"b2_float", "b2_bool", "b2_int", "b2_vector", "b2_value", "B2Accessor"}
    for path in sorted(package.rglob("*.py")):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name not in factories:
                continue
            extra = 0
            for keyword in node.keywords:
                if keyword.arg == "extra_set_args" and isinstance(
                    keyword.value, (ast.Tuple, ast.List)
                ):
                    extra = len(keyword.value.elts)
            for index, argument in enumerate(node.args[:2]):
                if not (
                    isinstance(argument, ast.Attribute)
                    and isinstance(argument.value, ast.Name)
                    and argument.value.id == "lib"
                ):
                    continue
                implied = 1 if index == 0 else 2 + extra
                yield path.name, node.lineno, argument.attr, implied


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
    assert len(list(call_sites())) > 100


def test_accessor_declarations_are_found():
    """Most accessors are declarative now, so this must not silently find none."""
    assert len(list(accessor_declarations())) > 100


def test_every_call_matches_its_declared_arity():
    arities = declared_arities()
    mismatches = [
        f"{name} at {filename}:{line} passes {argc}, header declares {arities[name]}"
        for filename, line, name, argc in call_sites()
        if name in arities and argc != arities[name]
    ]
    assert not mismatches, "argument count mismatches:\n  " + "\n  ".join(mismatches)


def test_every_accessor_matches_its_declared_arity():
    """The same check for accessors, which reference functions without calling them."""
    arities = declared_arities()
    mismatches = [
        f"{name} at {filename}:{line} is used with {argc} arguments, "
        f"header declares {arities[name]}"
        for filename, line, name, argc in accessor_declarations()
        if name in arities and argc != arities[name]
    ]
    assert not mismatches, "accessor arity mismatches:\n  " + "\n  ".join(mismatches)


def test_no_call_site_targets_a_missing_function():
    """A renamed or removed function must not survive as a dead call."""
    from box2d._box2d import lib

    referenced = list(call_sites()) + list(accessor_declarations())
    missing = [
        f"{name} at {filename}:{line}"
        for filename, line, name, _ in referenced
        if not hasattr(lib, name)
    ]
    assert not missing, "calls to functions absent from the build:\n  " + "\n  ".join(
        missing
    )
