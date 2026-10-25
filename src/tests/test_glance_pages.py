"""The overview pages list every public member of the classes they cover.

Each page under ``docs/source/glance`` gives a class its own section, headed
with the class's name, and lists its members there one per bullet, the bullet
starting with the member as code: ``body.position``, or
``body.apply_force(force, point=None, wake=True)`` for a call. So that the
pages stay complete as the classes grow, and accurate as they change:

- every member a class introduces has a bullet in its section, as does an
  override whose parameters differ from what it overrides, as ``Box.create``'s
  do from ``Polygon.create``'s;
- every bullet names something the class has, or the class itself, for its
  constructor;
- a bullet written as a call is a call in the code too, with the same
  parameters in the same order and the same defaults. ``...`` ends the list
  where the page leaves the rest out.

A member is public if its name does not start with an underscore. For a
dataclass, its fields count too, since one without a default is not a class
attribute and so is missing from ``dir()``.
"""

import dataclasses
import inspect
import math
import re
from pathlib import Path

import pytest

import box2d
from box2d import (
    Body,
    BodyBuilder,
    Box,
    Capsule,
    Chain,
    ChainDef,
    ChainSegment,
    Circle,
    CircleDef,
    CapsuleDef,
    DistanceJoint,
    DistanceJointDef,
    FilterJoint,
    FilterJointDef,
    Joint,
    JointDef,
    MotorJoint,
    MotorJointDef,
    MouseJoint,
    MouseJointDef,
    MoverJoint,
    MoverJointDef,
    PogoJoint,
    PogoJointDef,
    Polygon,
    PolygonDef,
    PrismaticJoint,
    PrismaticJointDef,
    RevoluteJoint,
    RevoluteJointDef,
    Segment,
    SegmentDef,
    Shape,
    ShapeDef,
    SurfaceMaterial,
    WeldJoint,
    WeldJointDef,
    WheelJoint,
    WheelJointDef,
    World,
)
from box2d.shapedef import BoxDef
from box2d.world import RayCastResult, SensorEvent, SensorEvents

GLANCE = Path(__file__).resolve().parents[2] / "docs" / "source" / "glance"

#: Each page, and the classes it lists every member of.
PAGES = {
    "world_glance.rst": [World, RayCastResult, SensorEvent, SensorEvents],
    "body_glance.rst": [Body, BodyBuilder],
    "shape_glance.rst": [
        Shape,
        Circle,
        Capsule,
        Segment,
        Polygon,
        Box,
        Chain,
        ChainSegment,
        ShapeDef,
        CircleDef,
        CapsuleDef,
        SegmentDef,
        PolygonDef,
        BoxDef,
        ChainDef,
        SurfaceMaterial,
    ],
    "joint_glance.rst": [
        Joint,
        DistanceJoint,
        FilterJoint,
        MotorJoint,
        MouseJoint,
        MoverJoint,
        PogoJoint,
        PrismaticJoint,
        RevoluteJoint,
        WeldJoint,
        WheelJoint,
        JointDef,
        DistanceJointDef,
        FilterJointDef,
        MotorJointDef,
        MouseJointDef,
        MoverJointDef,
        PogoJointDef,
        PrismaticJointDef,
        RevoluteJointDef,
        WeldJointDef,
        WheelJointDef,
    ],
}

CASES = [(page, cls) for page, classes in PAGES.items() for cls in classes]


def _case_id(case):
    page, cls = case
    return f"{page.removesuffix('_glance.rst')}-{cls.__name__}"


# -- what the code has --------------------------------------------------------


def public_members(cls):
    """The public names on ``cls``, its dataclass fields included."""
    names = {name for name in dir(cls) if not name.startswith("_")}
    if dataclasses.is_dataclass(cls):
        names |= {f.name for f in dataclasses.fields(cls)}
    return names


def documented_members(cls):
    """What ``cls``'s section must list.

    The members it introduces, and the methods it overrides with different
    parameters. An override with the same parameters is its base's member,
    listed in the base's section.
    """
    inherited = set().union(*(public_members(base) for base in cls.__mro__[1:]))
    required = public_members(cls) - inherited
    for name in public_members(cls) & inherited:
        if name not in vars(cls):
            continue
        base = next(b for b in cls.__mro__[1:] if hasattr(b, name))
        ours, theirs = _signature(cls, name), _signature(base, name)
        if ours is not None and theirs is not None and ours != theirs:
            required.add(name)
    return required


def _signature(cls, name):
    """The signature of ``cls.name`` as it is called, or None if not a method.

    ``name`` is the class's own name for its constructor. ``self`` and
    ``cls`` are left out, as a call leaves them out.
    """
    if name == cls.__name__:
        return inspect.signature(cls)
    attr = inspect.getattr_static(cls, name, None)
    if isinstance(attr, staticmethod):
        return inspect.signature(attr.__func__)
    if isinstance(attr, classmethod):
        return inspect.signature(getattr(cls, name))
    if inspect.isfunction(attr):
        signature = inspect.signature(attr)
        parameters = list(signature.parameters.values())[1:]
        return signature.replace(parameters=parameters)
    return None


def _tokens(signature):
    """``(name, default)`` per parameter, with ``*`` and ``/`` as markers.

    A default is ``inspect.Parameter.empty`` when there is none.
    """
    tokens = []
    kinds = inspect.Parameter
    star_seen = False
    previous = None
    for parameter in signature.parameters.values():
        if previous is kinds.POSITIONAL_ONLY and parameter.kind is not previous:
            tokens.append(("/", kinds.empty))
        if parameter.kind is kinds.VAR_POSITIONAL:
            star_seen = True
            tokens.append((f"*{parameter.name}", kinds.empty))
        elif parameter.kind is kinds.VAR_KEYWORD:
            tokens.append((f"**{parameter.name}", kinds.empty))
        else:
            if parameter.kind is kinds.KEYWORD_ONLY and not star_seen:
                star_seen = True
                tokens.append(("*", kinds.empty))
            tokens.append((parameter.name, parameter.default))
        previous = parameter.kind
    if previous is kinds.POSITIONAL_ONLY:
        tokens.append(("/", kinds.empty))
    return tokens


# -- what the page says -------------------------------------------------------

_HEADING = re.compile(r"^(?P<title>[^\n]+)\n(?P<rule>([=\-^~])\3+)$", re.MULTILINE)
#: A bullet's leading code: one or more literals, joined by commas or "or".
_BULLET = re.compile(r"^\* (?P<lead>``[^`]+``(?:(?:, | or )``[^`]+``)*)", re.MULTILINE)
_LITERAL = re.compile(r"``([^`]+)``")


def sections(text):
    """``{title: body}`` for each section underlined with ``-``.

    The pages underline their title with ``=``, a class with ``-`` and its
    groups with ``^``, so a section runs to the next ``=`` or ``-`` heading.
    """
    headings = [
        match
        for match in _HEADING.finditer(text)
        if len(match["rule"]) >= len(match["title"])
    ]
    found = {}
    for index, match in enumerate(headings):
        if match["rule"][0] != "-":
            continue
        end = len(text)
        for later in headings[index + 1 :]:
            if later["rule"][0] in "=-":
                end = later.start()
                break
        found[match["title"].strip()] = text[match.end() : end]
    return found


def bullets(section):
    """``(name, literal)`` for each member a section's bullets lead with.

    ``body.apply_force(force, point=None)`` names ``apply_force``, and
    ``lock_x``, ``lock_y`` names both. The receiver before the last dot is
    only the page's example, so it is not read.
    """
    found = []
    for match in _BULLET.finditer(section):
        for literal in _LITERAL.findall(match["lead"]):
            head = literal.split("(", 1)[0]
            for piece in head.split(","):
                found.append((piece.strip().rsplit(".", 1)[-1], literal))
    return found


def _split_arguments(text):
    """Split a parameter list on its top-level commas."""
    parts, depth, current = [], 0, ""
    for char in text:
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        if char == "," and depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        parts.append(current.strip())
    return parts


def written_tokens(literal):
    """``(name, default text)`` per parameter of a call as the page writes it,
    or None if it is not written as a call. The default text is None when the
    page gives no default."""
    if "(" not in literal:
        return None
    inside = literal[literal.index("(") + 1 : literal.rindex(")")]
    tokens = []
    for part in _split_arguments(inside):
        name, _, default = part.partition("=")
        tokens.append((name.strip(), default.strip() or None))
    return tokens


_NAMES = {**vars(box2d), "math": math}


def _defaults_match(written, actual):
    if actual is dataclasses.MISSING or repr(actual) == "<factory>":
        return True  # made fresh for each instance; the page says what it is
    try:
        value = eval(written, dict(_NAMES))  # noqa: S307 -- our own docs
    except Exception:
        return False
    if isinstance(actual, (int, float)) and not isinstance(actual, bool):
        return isinstance(value, (int, float)) and math.isclose(
            value, actual, rel_tol=1e-6
        )
    return value == actual


def signature_problems(cls, name, literal):
    """How a bullet's call differs from the code, as a list of complaints."""
    written = written_tokens(literal)
    signature = _signature(cls, name)
    if written is None:
        if signature is not None:
            return [f"{literal!r}: {name} is a method; write it as a call"]
        return []
    if signature is None:
        return [f"{literal!r}: {name} is not a method, so not a call"]
    actual = _tokens(signature)
    problems = []
    for index, (written_name, written_default) in enumerate(written):
        if written_name == "...":
            return problems
        if index >= len(actual):
            return problems + [f"{literal!r}: {written_name} is not a parameter"]
        actual_name, actual_default = actual[index]
        if written_name != actual_name:
            problems.append(
                f"{literal!r}: parameter {index + 1} is {actual_name}, not {written_name}"
            )
            return problems
        if (written_default is None) != (actual_default is inspect.Parameter.empty):
            has = "has no default" if written_default is not None else "has a default"
            problems.append(f"{literal!r}: {actual_name} {has}")
        elif written_default is not None and not _defaults_match(
            written_default, actual_default
        ):
            problems.append(
                f"{literal!r}: {actual_name} defaults to {actual_default!r}, "
                f"not {written_default}"
            )
    missing = [token for token, _ in actual[len(written) :]]
    if missing:
        problems.append(f"{literal!r}: leaves out {', '.join(missing)}")
    return problems


def _section(page, cls):
    text = (GLANCE / page).read_text(encoding="utf-8")
    found = sections(text)
    assert cls.__name__ in found, f"{page} has no section headed {cls.__name__}"
    return found[cls.__name__]


# -- the tests ----------------------------------------------------------------


@pytest.mark.parametrize("case", CASES, ids=_case_id)
def test_every_member_is_listed(case):
    page, cls = case
    listed = {name for name, _ in bullets(_section(page, cls))}
    missing = sorted(documented_members(cls) - listed)
    assert not missing, f"{page}: {cls.__name__} section does not list {missing}"


@pytest.mark.parametrize("case", CASES, ids=_case_id)
def test_every_listed_member_exists(case):
    page, cls = case
    unknown = sorted(
        {
            name
            for name, _ in bullets(_section(page, cls))
            if name != cls.__name__ and name not in public_members(cls)
        }
    )
    assert not unknown, f"{page}: {cls.__name__} has no {unknown}"


@pytest.mark.parametrize("case", CASES, ids=_case_id)
def test_every_call_matches_the_code(case):
    page, cls = case
    problems = []
    for name, literal in bullets(_section(page, cls)):
        if name == cls.__name__ or name in public_members(cls):
            problems += signature_problems(cls, name, literal)
    assert not problems, f"{page}, {cls.__name__}:\n" + "\n".join(problems)


def test_every_page_is_checked():
    """A new overview page is added to PAGES, or it goes unchecked."""
    pages = {path.name for path in GLANCE.glob("*_glance.rst")}
    assert pages - {"math_glance.rst"} == set(PAGES)


# -- the checks themselves ----------------------------------------------------

_PAGE = """\
Title
=====

Thing
-----

Group
^^^^^

* ``thing.go(speed, wait=True)`` - Go
* ``a``, ``b`` - Two at once

Other
-----

* ``other.c`` - C
"""


def test_a_section_runs_to_the_next_heading_of_its_level():
    found = sections(_PAGE)
    assert set(found) == {"Thing", "Other"}
    assert [name for name, _ in bullets(found["Thing"])] == ["go", "a", "b"]


def test_a_call_is_compared_parameter_by_parameter():
    class Thing:
        def go(self, speed, wait=True, *, limit=None, **extra):
            pass

        @property
        def a(self):
            return 1

    assert (
        signature_problems(Thing, "go", "go(speed, wait=True, *, limit=None, **extra)")
        == []
    )
    assert signature_problems(Thing, "go", "go(speed, ...)") == []
    assert signature_problems(Thing, "go", "go(speed, wait=False, ...)")
    assert signature_problems(Thing, "go", "go(pace, ...)")
    assert signature_problems(Thing, "go", "go(speed)")
    assert signature_problems(Thing, "go", "thing.go")
    assert signature_problems(Thing, "a", "thing.a()")
    assert signature_problems(Thing, "a", "thing.a") == []


def test_an_override_with_new_parameters_is_its_own_member():
    class Base:
        def make(self, a):
            pass

        def keep(self, a):
            pass

    class Derived(Base):
        def make(self, a, b):
            pass

        def keep(self, a):
            pass

    assert documented_members(Derived) == {"make"}


def test_defaults_are_compared_as_values():
    assert _defaults_match("0.6", 0.6000000238418579)
    assert _defaults_match("(0, 0)", box2d.Vec2(0, 0))
    assert not _defaults_match("1", 0.0)
    assert _defaults_match("None", None)
