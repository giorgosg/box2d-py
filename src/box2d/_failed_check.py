"""Which field a failed Box2D check was about, and the value it refused.

:class:`~box2d.InvalidInputError` carries the check's condition as Box2D wrote
it, in C names. This reads the condition against what the call was passed:
``def->linearDamping`` is a field of the definition among the arguments, found
in that definition's field table; ``torque`` is a parameter of a setter, whose
Python name comes from the function, ``b2RevoluteJoint_SetMaxMotorTorque``
being ``max_motor_torque``.

Some checks cover a whole structure, ``b2IsValidMaterial`` or
``b2IsValidCircle``. Those rows of the table are looked through for the first
value that is not a finite number in its range: this names what was refused,
it decides nothing, and if no row looks wrong the field is simply not known.

The field is what reached Box2D, which is not always what the caller wrote: an
anchor assigned to a joint is refused as its frame, and a box's offset as the
vertices worked out from it.

None of it runs until a check has failed. ``test_error_structure.py`` walks
every check in Box2D's sources, so a Box2D update cannot leave one unanswered.
"""

import math
import re
from typing import Any, Optional

from ._box2d import ffi
from .defdata import _from_c, _Row, _rows, _short_values, _structs
from .math import Rot, Transform, Vec2

#: A field's Python name and the value refused, each None if it cannot be told.
_Found = tuple[Optional[str], Any]

_LIMITS: dict[str, Optional[str]] = {"lower": "lower_limit", "upper": "upper_limit"}

#: Functions taking more than one value, or whose value is not the property
#: its name says: each C parameter in order and its Python name, or None where
#: no one Python name fits it.
_ARGUMENTS: dict[str, dict[str, Optional[str]]] = {
    "b2Body_SetTransform": {"position": "position", "rotation": "rotation"},
    "b2Body_SetTargetTransform": {"target": None, "timeStep": "dt"},
    "b2Body_ApplyForce": {"force": "force", "point": "point"},
    "b2Body_ApplyLinearImpulse": {"impulse": "impulse", "point": "point"},
    "b2DistanceJoint_SetLimits": {
        "minLength": "lower_limit",
        "maxLength": "upper_limit",
    },
    "b2DistanceJoint_SetSpringForceRange": {
        "lowerForce": "lower_spring_force",
        "upperForce": "upper_spring_force",
    },
    "b2Joint_SetConstraintTuning": {
        "hertz": "constraint_tuning",
        "dampingRatio": "constraint_tuning",
    },
    "b2PrismaticJoint_SetLimits": _LIMITS,
    "b2RevoluteJoint_SetLimits": _LIMITS,
    "b2Shape_ApplyWind": {"wind": "wind", "drag": "drag", "lift": "lift"},
    "b2WheelJoint_SetLimits": _LIMITS,
    "b2World_SetContactTuning": {
        "hertz": "contact_hertz",
        "dampingRatio": "contact_damping_ratio",
        "pushSpeed": "contact_push_speed",
    },
}

#: The list each of a chain's counts is the length of, by the count's C name.
_LIST_OF_COUNT = {"pointCount": "vertices", "materialCount": "materials"}

#: The C name of a list's length, by the list's.
_LENGTH_OF_LIST = {"points": "pointCount", "vertices": "count"}

#: The fields of definitions with no table, by C name. Only World takes one,
#: and it writes only this: Box2D's defaults pass the checks on the rest.
_NO_TABLE = {"gravity": "gravity"}

#: A field of the definition passed. Where a condition names several, it is
#: testing the last by way of the first: ``def->isLoop ? def->pointCount ...``.
_DEFINITION_FIELD = re.compile(r"def->([\w.]+)")
#: A parameter, maybe a field of one, skipping the name of the check around it.
_PARAMETER = re.compile(r"(?<![\w>.])(?!b2)([a-z]\w*)(?:\.(\w+))?")
_SETTER = re.compile(r"_Set(\w+)$")
_WORD_START = re.compile(r"(?<!^)(?=[A-Z])")


def describe(function: str, condition: str, args: tuple[Any, ...]) -> _Found:
    """The Python name of the field a check was about and the value it refused.

    Either is None if it cannot be told. ``function`` is the function called,
    ``condition`` the check that failed, and ``args`` what the call was passed.
    """
    fields = _DEFINITION_FIELD.findall(condition)
    if fields:
        for each in args:
            if _struct_name(each).endswith("Def"):
                return _definition_field(each, fields[-1])
        return None, None
    parameter = _PARAMETER.search(condition)
    if parameter is None:
        return None, None
    return _argument(function, parameter[1], parameter[2], args)


def _struct_name(value: Any) -> str:
    """The name of the C structure ``value`` is or points to, else ``""``."""
    if not isinstance(value, ffi.CData):
        return ""
    kind = ffi.typeof(value)
    if kind.kind == "pointer":
        kind = kind.item
    return kind.cname.removeprefix("struct ") if kind.kind == "struct" else ""


def _definition_field(definition: Any, path: str) -> _Found:
    table = _structs.get(_struct_name(definition))
    if table is None:
        if path not in _NO_TABLE:
            return None, None
        return _NO_TABLE[path], _python(getattr(definition, path))
    if path in _LIST_OF_COUNT:
        return _LIST_OF_COUNT[path], None
    if path == "base":
        return _first_refused(table, definition, "base.")
    for name, row in _rows(table).items():
        if row.c != path:
            continue
        if row.codec == "material":
            return _first_refused(
                _structs["b2SurfaceMaterial"], getattr(definition, path)
            )
        if row.codec == "materials":
            return _first_refused_material(definition)
        return name, _read(definition, row)
    return None, None


def _first_refused_material(chain: Any) -> _Found:
    for each in range(chain.materialCount):
        found = _first_refused(_structs["b2SurfaceMaterial"], chain.materials[each])
        if found[0] is not None:
            return found
    return None, None


def _first_refused(table: type, structure: Any, prefix: str = "") -> _Found:
    """The first field of a structure holding something Box2D would refuse."""
    for name, row in _rows(table).items():
        if row.c is not None and row.c.startswith(prefix):
            value = _read(structure, row)
            if _refused(value, row.range):
                return name, value
    return None, None


def _refused(value: Any, allowed: Optional[tuple[float, float]]) -> bool:
    if isinstance(value, Vec2):
        return not value.is_finite
    if isinstance(value, list):
        return any(_refused(each, None) for each in value)
    if isinstance(value, float):
        low, high = allowed or (-math.inf, math.inf)
        return not math.isfinite(value) or not low <= value <= high
    return False


def _read(structure: Any, row: _Row) -> Any:
    """A field of a Box2D structure, as Python values."""
    if row.c in _LENGTH_OF_LIST:
        points = getattr(structure, row.c)
        count = getattr(structure, _LENGTH_OF_LIST[row.c])
        return [_python(points[each]) for each in range(count)]
    return _python(_from_c(structure, row))


def _argument(
    function: str, parameter: str, member: Optional[str], args: tuple[Any, ...]
) -> _Found:
    """The field and value of a parameter of ``function``, or of its ``member``."""
    # A geometry is found by its type, wherever the function takes it.
    for each in args:
        struct = _struct_name(each)
        if struct in _structs and struct.lower() == f"b2{parameter.lower()}":
            return _first_refused(_structs[struct], each)
    # A method takes its object's id first; b2SetLengthUnitsPerMeter takes none.
    position = 1 if "_" in function else 0
    named = _ARGUMENTS.get(function)
    if named is not None:
        if parameter not in named:
            return None, None
        field = named[parameter]
        position += list(named).index(parameter)
    else:
        setter = _SETTER.search(function)
        field = _snake(setter[1] if setter else parameter)
    if field is None or position >= len(args):
        return None, None
    value = args[position]
    struct = _struct_name(value)
    if struct in _structs:
        return _first_refused(_structs[struct], value)
    # A structure passed whole, whose fields the function checks by name.
    leaf = member or parameter
    if struct and hasattr(value, leaf):
        return _snake(leaf), _python(getattr(value, leaf))
    return field, _python(value)


def _python(value: Any) -> Any:
    """A value out of Box2D as Python holds it, None for what it has no form of."""
    if isinstance(value, ffi.CData):
        struct = _struct_name(value)
        if struct == "b2Vec2" and ffi.typeof(value).kind == "struct":
            return _short_values(Vec2.from_b2Vec2(value))
        if struct == "b2Rot":
            return _short_values(Rot.from_b2Rot(value).angle)
        if struct == "b2Transform":
            return Transform.from_b2Transform(value)
        return None
    return _short_values(value)


def _snake(name: str) -> str:
    return _WORD_START.sub("_", name).lower()
