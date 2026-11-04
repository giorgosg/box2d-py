"""Definitions as plain data, both ways, driven by one field table.

Every definition -- :class:`.BodyDef`, :class:`.ShapeDef`, the geometry
definitions, :class:`.ChainDef`, :class:`.SurfaceMaterial` and the joint
definitions -- keeps a table of its fields next to its dataclass: each field's
kind of value, unit, valid range, and how to read it back from a live object.
:class:`DefData`, which they all share, works from that table:

- ``to_dict()`` and ``from_dict()`` turn a definition into JSON-ready data and
  back, writing only what differs from the defaults unless ``full=True``;
- ``fields()`` describes each field, for an inspector or a file format;
- ``repr()`` writes the definition as code that makes an equal one;
- ``body.to_def()``, ``shape.to_def()`` and ``joint.to_def()`` read a live
  object back into its definition, as far as Box2D can tell.

.. code-block:: python

    >>> from box2d import BodyDef, def_from_dict
    >>> body_def = BodyDef(type="dynamic", position=(1, 2), linear_damping=0.5)
    >>> body_def
    BodyDef(type='dynamic', position=Vec2(1.0, 2.0), linear_damping=0.5)
    >>> body_def.to_dict()
    {'type': 'dynamic', 'position': [1.0, 2.0], 'linear_damping': 0.5}
    >>> BodyDef.from_dict(body_def.to_dict()) == body_def
    True
"""

import copy
import dataclasses
import difflib
import enum
import math
import re
import struct
from typing import (
    Any,
    Callable,
    ClassVar,
    Iterable,
    Mapping,
    NamedTuple,
    Optional,
    TypeVar,
    Union,
)

from ._checked import lib

__all__ = ["DEFAULTS_VERSION", "DefData", "DefField", "def_from_dict"]

#: The set of defaults a dictionary leaves out, Box2D's and the binding's
#: own. A field missing from a dictionary means "the default of the version
#: reading it", and defaults change between versions, so a file format writes
#: this once at its top, and archives use ``to_dict(full=True)``.
DEFAULTS_VERSION = "3.2.0-1"

_D = TypeVar("_D", bound="DefData")


class DefField(NamedTuple):
    """One field of a definition, as :meth:`DefData.fields` describes it."""

    #: The field's name, as the definition and its dictionary spell it.
    name: str
    #: The kind of value, one of ``float``, ``int``, ``bool``, ``str``,
    #: ``vec2``, ``angle`` (radians), ``body_type``, ``material``,
    #: ``materials``, ``filter``, ``vec2_list``, ``color``, ``body`` or
    #: ``shape``.
    type: str
    #: The default, as ``to_dict`` would write it; None where there is none:
    #: a field that must be given, or one worked out when the object is made.
    default: Any
    #: The field in Box2D's own structure, such as ``"linearDamping"`` or
    #: ``"motionLocks.linearX"``; None if it has no one field there.
    c_name: Optional[str]
    #: The unit, such as ``"m"``, ``"rad/s"`` or ``"Hz"``; None if it has none.
    unit: Optional[str]
    #: The range Box2D accepts, as ``(low, high)``; None if any value will do.
    range: Optional[tuple[float, float]]
    #: What the field means, from the definition's own documentation.
    doc: str
    #: Whether ``to_def()`` reads it back from a live object.
    readable: bool


# -- the table ---------------------------------------------------------------------


class _Live(enum.Enum):
    """How ``to_def`` reads a field, when not by a name or function."""

    #: From the live object's attribute of the field's own name.
    OWN = "own"
    #: By the live class's own ``to_def``, which works it out by hand.
    BY_TO_DEF = "to_def"


BY_TO_DEF = _Live.BY_TO_DEF
_UNSET: Any = object()


class _Row(NamedTuple):
    """One row of a definition's field table.

    ``live`` is how ``to_def()`` reads the field from a live object: the name
    of an attribute, a function of the object, a :class:`_Live`, or None where
    Box2D keeps no way to read it. ``default`` stands in for the dataclass's
    when that is None but means a known value; it may be a function, called
    once. ``c`` is the field's path in the definition's Box2D structure, which
    gives the default of a joint setting that is None.
    """

    codec: str
    unit: Optional[str] = None
    range: Optional[tuple[float, float]] = None
    live: Union[str, Callable[[Any], Any], _Live, None] = _Live.OWN
    default: Any = _UNSET
    c: Optional[str] = None


_f = _Row

NON_NEGATIVE = (0.0, math.inf)


def _rows(cls: type) -> dict[str, _Row]:
    """A class's whole table, its bases' rows first. A class takes a base's
    row away by setting it to None."""
    rows: dict[str, Optional[_Row]] = {}
    for klass in reversed(cls.__mro__):
        rows.update(klass.__dict__.get("_table", {}))
    return {name: row for name, row in rows.items() if row is not None}


# -- 32-bit floats -------------------------------------------------------------------

_F32 = struct.Struct("<f")

#: How far a value worked out from Box2D's 32-bit floats may be from the
#: decimal it was: two units in the last place, relative to at least 1.
ROUNDING = 2.0**-22


def _f32(value: float) -> float:
    """The 32-bit float Box2D would store for ``value``."""
    try:
        return _F32.unpack(_F32.pack(value))[0]
    except OverflowError:
        return math.copysign(math.inf, value)


def _short(value: float, tolerance: float = 0.0) -> float:
    """The shortest decimal Box2D stores as the same 32-bit float.

    Box2D reads 0.7 back as 0.699999988079071; this gives 0.7 again, so
    definitions read from live objects, and the defaults, are as written. A
    value worked out from others, such as a box's width from its corners,
    carries their rounding as well, and is given a relative ``tolerance``.
    """
    if not math.isfinite(value):
        return value
    target = _f32(value)
    slack = tolerance * max(1.0, abs(value))
    for digits in range(1, 10):
        candidate = float(f"{value:.{digits}g}")
        if _f32(candidate) == target or abs(candidate - value) <= slack:
            return candidate
    return value


def _alike(a: Any, b: Any) -> bool:
    """Whether two encoded values are the same to Box2D, floats as it stores them."""
    if isinstance(a, float) and isinstance(b, float):
        return _f32(a) == _f32(b)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(map(_alike, a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_alike(a[k], b[k]) for k in a)
    return type(a) is type(b) and a == b


# -- values ------------------------------------------------------------------------

BODY_TYPES = ("static", "kinematic", "dynamic")


def _body_type_name(value: Any) -> Any:
    """A body type's name; a value no type has is left for Box2D to refuse."""
    if isinstance(value, int) and 0 <= value < len(BODY_TYPES):
        return BODY_TYPES[value]
    return value


def _encode(codec: str, value: Any, full: bool, body_ref: Any) -> Any:
    """``value`` as the JSON-ready data a dictionary holds."""
    from .math import Rot, Vec2

    if value is None:
        return None
    if codec == "float":
        return float(value)
    if codec == "int":
        return int(value)
    if codec == "bool":
        return bool(value)
    if codec == "str":
        return str(value)
    if codec == "vec2":
        x, y = Vec2(value)
        return [x, y]
    if codec == "vec2_list":
        return [_encode("vec2", point, full, body_ref) for point in value]
    if codec == "angle":
        # A Rot holds a sine and a cosine, whose angle is not quite the one
        # that made it.
        return _short(value.angle, ROUNDING) if isinstance(value, Rot) else float(value)
    if codec == "body_type":
        return _body_type_name(value)
    if codec == "color":
        return value if isinstance(value, int) else value.b2HexColor
    if codec == "material":
        return value.to_dict(full=full)
    if codec == "materials":
        return [material.to_dict(full=full) for material in value]
    if codec == "filter":
        return {"category": value.category, "mask": value.mask, "group": value.group}
    if codec == "body":
        if body_ref is None:
            raise TypeError(
                "a joint definition names its bodies, which a dictionary cannot "
                "hold: pass body_ref, a function giving each body's reference"
            )
        return body_ref(value)
    raise AssertionError(f"no codec {codec!r}")


def _decode(codec: str, value: Any, where: str, resolve: Any) -> Any:
    """The definition's value for data ``to_dict`` wrote, checked."""
    from .collision_filter import CollisionFilter
    from .dataclasses import BodyType
    from .material import SurfaceMaterial
    from .math import Vec2

    def refuse(what: str) -> Any:
        raise TypeError(f"{where} must be {what}, not {value!r}")

    def number(x: Any) -> bool:
        return isinstance(x, (int, float)) and not isinstance(x, bool)

    if value is None:
        return None
    if codec in ("float", "angle"):
        return float(value) if number(value) else refuse("a number")
    if codec in ("int", "color"):
        ok = isinstance(value, int) and not isinstance(value, bool)
        return value if ok else refuse("an integer")
    if codec == "bool":
        return value if isinstance(value, bool) else refuse("true or false")
    if codec == "str":
        return value if isinstance(value, str) else refuse("a string")
    if codec == "vec2":
        if (
            isinstance(value, (list, tuple))
            and len(value) == 2
            and all(map(number, value))
        ):
            return Vec2(*value)
        return refuse("a pair of numbers")
    if codec == "vec2_list":
        if not isinstance(value, (list, tuple)):
            return refuse("a list of points")
        return [
            _decode("vec2", point, f"{where}[{i}]", resolve)
            for i, point in enumerate(value)
        ]
    if codec == "body_type":
        if value in BODY_TYPES:
            return BodyType(BODY_TYPES.index(value))
        return refuse(" or ".join(repr(name) for name in BODY_TYPES))
    if codec == "material":
        return SurfaceMaterial.from_dict(_mapping(value, where), _where=where)
    if codec == "materials":
        if not isinstance(value, (list, tuple)):
            return refuse("a list of materials")
        return [
            SurfaceMaterial.from_dict(_mapping(each, f"{where}[{i}]"), _where=where)
            for i, each in enumerate(value)
        ]
    if codec == "filter":
        data = dict(_mapping(value, where))
        _refuse_unknown(data, ("category", "mask", "group"), where)
        for key, given in data.items():
            if not isinstance(given, int) or isinstance(given, bool):
                raise TypeError(f"{where}.{key} must be an integer, not {given!r}")
        return CollisionFilter(**data)
    if codec == "body":
        if resolve is None:
            raise TypeError(
                f"{where} names a body: pass resolve, a function giving the "
                "body for each reference"
            )
        return resolve(value)
    raise AssertionError(f"no codec {codec!r}")


def _mapping(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{where} must be a dictionary, not {value!r}")
    return value


def _refuse_unknown(data: Mapping[str, Any], known: Iterable[str], where: str) -> None:
    """Refuse a key a definition does not have, naming the near miss."""
    known = list(known)
    for key in data:
        if key not in known:
            raise ValueError(f"{where} has no field {key!r}{_near_miss(key, known)}")


def _near_miss(word: Any, options: Iterable[str]) -> str:
    """The end of an error message, naming the option ``word`` nearly is."""
    hint = difflib.get_close_matches(str(word), list(options), n=1)
    return f"; did you mean {hint[0]!r}?" if hint else ""


def _code(codec: str, value: Any) -> str:
    """``value`` as Python source, for a definition's repr."""
    from .math import Rot

    if codec == "angle" and isinstance(value, Rot):
        return repr(_short(value.angle, ROUNDING))
    if codec == "body_type":
        return repr(_body_type_name(value))
    if codec == "vec2_list":
        return "[" + ", ".join(_code("vec2", point) for point in value) + "]"
    if codec == "vec2":
        from .math import Vec2

        return repr(Vec2(value))
    return repr(value)


# -- documentation -------------------------------------------------------------------

_ATTRIBUTE = re.compile(r"^(\s*)(\w+)(?: \([^)]*\))?:\s*(.*)$")


def _attribute_docs(cls: type) -> dict[str, str]:
    """Each field's line or lines from an ``Attributes:`` section, bases first."""
    docs: dict[str, str] = {}
    for klass in reversed(cls.__mro__):
        lines = (klass.__dict__.get("__doc__") or "").expandtabs().splitlines()
        inside = False
        indent = None
        name = None
        for line in lines:
            if line.strip() == "Attributes:":
                inside, indent, name = True, None, None
                continue
            if not inside:
                continue
            if not line.strip():
                name = None
                continue
            match = _ATTRIBUTE.match(line)
            depth = len(line) - len(line.lstrip())
            if match and (indent is None or depth == indent):
                indent = depth
                name = match.group(2)
                docs[name] = match.group(3).strip()
            elif indent is not None and depth > indent and name:
                docs[name] += " " + line.strip()
            else:
                inside = False
    return docs


# -- defaults ------------------------------------------------------------------------

_defaults: dict[tuple[type, bool], dict[str, Any]] = {}

#: The kinds of value a field's default can be read from Box2D's structure as.
_C_DEFAULTS = ("float", "bool", "vec2")


def _defaults_of(cls: type, full: bool) -> dict[str, Any]:
    """Each field's default, encoded as ``to_dict`` writes it; None where a
    field has none. Worked out once per class, so never handed out as it is."""
    key = (cls, full)
    if key in _defaults:
        return _defaults[key]
    declared = {each.name: each for each in dataclasses.fields(cls)}
    structure = getattr(cls, "_c_struct", None)
    made = getattr(lib, f"b2Default{structure[2:]}", None) if structure else None
    box2d_default = made() if made else None
    found: dict[str, Any] = {}
    for name, row in _rows(cls).items():
        if row.default is not _UNSET:
            raw = row.default() if callable(row.default) else row.default
        else:
            declaration = declared[name]
            if declaration.default is not dataclasses.MISSING:
                raw = declaration.default
            elif declaration.default_factory is not dataclasses.MISSING:
                raw = declaration.default_factory()
            else:
                raw = None
            # None, for a setting of a joint, is whatever Box2D's own default
            # definition says, and a field that must be given has no default.
            settable = declaration.default is None and row.codec in _C_DEFAULTS
            if settable and row.c and box2d_default is not None:
                raw = _from_c(box2d_default, row)
        encoded = _encode(row.codec, raw, full, None)
        found[name] = _clean(encoded) if raw is not None else None
    _defaults[key] = found
    return found


def _from_c(structure: Any, row: _Row) -> Any:
    """A field's value in a Box2D structure, by its path."""
    from .math import Vec2

    value = structure
    for part in row.c.split("."):
        value = getattr(value, part)
    return Vec2.from_b2Vec2(value) if row.codec == "vec2" else value


def _clean(encoded: Any) -> Any:
    """Encoded data with each float as the shortest decimal Box2D stores alike."""
    if isinstance(encoded, float):
        return _short(encoded)
    if isinstance(encoded, list):
        return [_clean(each) for each in encoded]
    if isinstance(encoded, dict):
        return {key: _clean(each) for key, each in encoded.items()}
    return encoded


def _read_live(obj: Any, name: str, row: _Row) -> Any:
    """One field of a live object, floats as the decimals they were set as."""
    live = row.live
    if callable(live):
        value = live(obj)
    else:
        value = getattr(obj, name if live is _Live.OWN else live)
    return _short_values(value)


def _short_values(value: Any, tolerance: float = 0.0) -> Any:
    """``value`` with its floats as the decimals Box2D stores alike: a float,
    a point, a list of them, or a definition such as a material."""
    from .math import Vec2

    if isinstance(value, float):
        return _short(value, tolerance)
    if isinstance(value, Vec2):
        return Vec2(_short(value.x, tolerance), _short(value.y, tolerance))
    if isinstance(value, list):
        return [_short_values(each, tolerance) for each in value]
    if isinstance(value, DefData) and dataclasses.is_dataclass(value):
        changes = {
            each.name: _short_values(getattr(value, each.name), tolerance)
            for each in dataclasses.fields(value)
            if isinstance(getattr(value, each.name), float)
        }
        return dataclasses.replace(value, **changes)
    return value


# -- the shared behaviour ------------------------------------------------------------


#: Every definition with a kind, by kind, as each is defined.
_kinds: dict[str, type] = {}

#: Every definition, by the name of the Box2D structure it stands for.
_structs: dict[str, type] = {}


class DefData:
    """What every definition can do with its field table.

    Not made on its own: :class:`.BodyDef`, :class:`.ShapeDef`, the geometry
    and chain definitions, :class:`.SurfaceMaterial` and the joint
    definitions are each one.

    Two definitions are equal when Box2D would make the same thing of them: a
    field left as None equals its default, and floats are compared as the
    32-bit floats Box2D stores. A subclass may add fields of its own, which
    are compared and shown by ``repr`` but are not data: dictionaries hold
    only the fields in the table.
    """

    __slots__ = ()

    #: The ``"kind"`` a dictionary of this definition carries, for
    #: :func:`~box2d.defdata.def_from_dict`; None for a body, a shape's own
    #: settings or a material, which are not told apart that way.
    kind: ClassVar[Optional[str]] = None
    #: The definition's field table, by field name.
    _table: ClassVar[dict[str, Optional[_Row]]] = {}
    #: The Box2D structure the ``c`` of each row is a path in.
    _c_struct: ClassVar[Optional[str]] = None

    def __init_subclass__(cls, **keywords: Any) -> None:
        super().__init_subclass__(**keywords)
        # A dataclass with slots is made twice, and the later is the one kept.
        kind = cls.__dict__.get("kind")
        if kind is not None:
            _kinds[kind] = cls
        struct = cls.__dict__.get("_c_struct")
        if struct is not None:
            _structs[struct] = cls

    @classmethod
    def fields(cls) -> tuple[DefField, ...]:
        """Every field a dictionary of this definition can hold, described.

        Example:
            >>> from box2d import BodyDef
            >>> damping = {f.name: f for f in BodyDef.fields()}["linear_damping"]
            >>> damping.default, damping.unit, damping.c_name, damping.range
            (0.0, '1/s', 'linearDamping', (0.0, inf))
        """
        defaults = _defaults_of(cls, True)
        docs = _attribute_docs(cls)
        return tuple(
            DefField(
                name=name,
                type=row.codec,
                default=copy.deepcopy(defaults[name]),
                c_name=row.c,
                unit=row.unit,
                range=row.range,
                doc=docs.get(name, ""),
                readable=row.live is not None,
            )
            for name, row in _rows(cls).items()
        )

    def _data_values(self, full: bool = False) -> dict[str, Any]:
        """Each field's value: None for one that is to count as its default."""
        return {name: getattr(self, name) for name in _rows(type(self))}

    def _written_values(self, full: bool) -> dict[str, Any]:
        """The values a dictionary is made from, which may need the bodies."""
        return self._data_values(full)

    def _encoded(
        self, values: Mapping[str, Any], full: bool, body_ref: Any
    ) -> dict[str, Any]:
        defaults = _defaults_of(type(self), full)
        rows = _rows(type(self))
        data: dict[str, Any] = {}
        if self.kind is not None:
            data["kind"] = self.kind
        for name, value in values.items():
            row = rows[name]
            if row.codec == "shape":
                shape = value if value is not None else _shape_def_class()()
                data.update(shape.to_dict(full=full))
                continue
            if value is None:
                if full:
                    data[name] = copy.deepcopy(defaults[name])
                continue
            encoded = _encode(row.codec, value, full, body_ref)
            default = defaults[name]
            if not full and default is not None and _alike(encoded, default):
                continue
            data[name] = encoded
        return data

    def to_dict(
        self, full: bool = False, body_ref: Optional[Callable[[Any], Any]] = None
    ) -> dict[str, Any]:
        """This definition as JSON-ready data.

        Points are ``[x, y]``, rotations an angle in radians, body types
        ``"static"``, ``"kinematic"`` or ``"dynamic"``, a filter its three
        integers, a material a dictionary of its own. ``user_data`` is left
        out: it is the application's, not data.

        Args:
            full: Write every field. Without it, a field at its default is
                left out, which means "the default of the version reading
                this": see :data:`DEFAULTS_VERSION`.
            body_ref: For a joint, a function giving each body's reference in
                the dictionary, such as its index in a scene, and so what
                :meth:`from_dict`'s ``resolve`` is given back.

        Returns:
            dict: The data, which :meth:`from_dict` makes an equal definition
            from.
        """
        return self._encoded(self._written_values(full), full, body_ref)

    @classmethod
    def from_dict(
        cls: type[_D],
        data: Mapping[str, Any],
        resolve: Optional[Callable[[Any], Any]] = None,
        _where: Optional[str] = None,
    ) -> _D:
        """The definition ``data`` describes, as :meth:`to_dict` wrote it.

        Strict: a key the definition does not have raises, naming the field
        meant, and so does a value of the wrong kind. Exactly what
        :meth:`to_dict` writes is accepted.

        Args:
            data: The dictionary.
            resolve: For a joint, a function giving the body for each
                reference ``to_dict``'s ``body_ref`` wrote.

        Raises:
            ValueError: For a key the definition does not have, or another
                definition's ``"kind"``.
            TypeError: For a value of the wrong kind.
        """
        where = _where or cls.__name__
        data = dict(_mapping(data, where))
        kind = data.pop("kind", cls.kind)
        if kind != cls.kind:
            raise ValueError(f"{where} is a {cls.kind!r}, not a {kind!r}")
        rows = _rows(cls)
        shape_field = next(
            (name for name, row in rows.items() if row.codec == "shape"), None
        )
        shape_names = list(_rows(_shape_def_class())) if shape_field else []
        known = [name for name in rows if name != shape_field] + shape_names
        _refuse_unknown(data, known, where)
        defaults = _defaults_of(cls, True)
        declared = {each.name: each for each in dataclasses.fields(cls)}
        arguments = {}
        shape_data = {}
        for key, value in data.items():
            if key in shape_names:
                shape_data[key] = value
                continue
            # None is what a full dictionary writes for a field with no
            # default, worked out later; for any other it is a mistake.
            if value is None and (
                defaults[key] is not None or declared[key].default is not None
            ):
                raise TypeError(f"{where}.{key} cannot be None")
            arguments[key] = _decode(rows[key].codec, value, f"{where}.{key}", resolve)
        if shape_field and shape_data:
            arguments[shape_field] = _shape_def_class().from_dict(
                shape_data, _where=where
            )
        return cls(**arguments)

    @classmethod
    def _read(cls: type[_D], obj: Any) -> _D:
        """The definition of live ``obj``, its readable fields read from it."""
        return cls(
            **{
                name: _read_live(obj, name, row)
                for name, row in _rows(cls).items()
                if row.live is not None and row.live is not BY_TO_DEF
            }
        )

    def _declared(self) -> tuple[Any, ...]:
        """This definition's dataclass fields."""
        return dataclasses.fields(self)  # pyright: ignore[reportArgumentType]

    def __eq__(self, other: object) -> bool:
        if type(other) is not type(self):
            return NotImplemented
        assert isinstance(other, DefData)
        mine = self._encoded(self._data_values(True), True, id)
        theirs = other._encoded(other._data_values(True), True, id)
        if not _alike(mine, theirs):
            return False
        rows = _rows(type(self))
        for each in self._declared():
            if each.name not in rows:
                if getattr(self, each.name) != getattr(other, each.name):
                    return False
            elif rows[each.name].codec == "shape":
                default = _shape_def_class()()
                if (getattr(self, each.name) or default) != (
                    getattr(other, each.name) or default
                ):
                    return False
        return True

    def __repr__(self) -> str:
        defaults = _defaults_of(type(self), False)
        rows = _rows(type(self))
        declared = {each.name: each for each in self._declared()}
        shown = []
        for name, value in self._data_values().items():
            row = rows[name]
            if value is None:
                continue
            if row.codec == "shape":
                if value != _shape_def_class()():
                    shown.append(f"{name}={value!r}")
                continue
            required = (
                declared[name].default is dataclasses.MISSING
                and declared[name].default_factory is dataclasses.MISSING
            )
            if not required and row.codec != "body":
                encoded = _encode(row.codec, value, False, None)
                if defaults[name] is not None and _alike(encoded, defaults[name]):
                    continue
            shown.append(f"{name}={_code(row.codec, value)}")
        for name in declared:
            if name not in rows and getattr(self, name) is not None:
                shown.append(f"{name}={getattr(self, name)!r}")
        return f"{type(self).__name__}({', '.join(shown)})"


def _shape_def_class() -> Any:
    from .shapedef import ShapeDef

    return ShapeDef


def def_from_dict(
    data: Mapping[str, Any], resolve: Optional[Callable[[Any], Any]] = None
) -> DefData:
    """The shape or joint definition ``data`` describes, by its ``"kind"``.

    Args:
        data: A dictionary a shape, chain or joint definition's ``to_dict``
            wrote.
        resolve: For a joint, a function giving the body for each reference.

    Raises:
        ValueError: If ``data`` has no ``"kind"``, or one no definition has.

    Example:
        >>> from box2d import CircleDef, def_from_dict
        >>> def_from_dict({"kind": "circle", "radius": 0.5, "density": 2.0})
        CircleDef(radius=0.5, shape=ShapeDef(density=2.0))
    """
    data = _mapping(data, "a definition")
    kind = data.get("kind")
    if kind is None:
        raise ValueError(
            'a definition\'s dictionary needs a "kind" to tell what it is; '
            "a body's has none, and is read by BodyDef.from_dict"
        )
    if kind not in _kinds:
        raise ValueError(f"no definition is of kind {kind!r}{_near_miss(kind, _kinds)}")
    return _kinds[kind].from_dict(data, resolve=resolve)
