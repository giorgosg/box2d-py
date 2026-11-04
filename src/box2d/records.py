"""Fixed-layout records the world writes into buffers the caller owns.

:meth:`World.write_moves <box2d.world.World.write_moves>` and
:meth:`World.write_transforms <box2d.world.World.write_transforms>` write one
record per body, packed one after another, into any writable buffer: a
``bytearray``, a ``memoryview``, an ``array.array``, a numpy array. The layout
is fixed and described here, so nothing that reads the records -- Python,
numpy, JavaScript over a ``DataView`` -- has to hand-code offsets:

.. code-block:: python

    >>> import struct
    >>> from box2d import MOVE_RECORD, World
    >>> world = World()
    >>> body = world.new_body().dynamic().position(1, 5).circle(0.5).build()
    >>> world.step(1 / 60, 4)
    >>> buffer = bytearray(MOVE_RECORD.itemsize * world.move_count)
    >>> count = world.write_moves(buffer)
    >>> key, x, y, cos, sin, flags = struct.unpack_from(MOVE_RECORD.struct, buffer)
    >>> key == body.key, round(x, 2), cos
    (True, 1.0, 1.0)
"""

import enum
from dataclasses import dataclass, field
from typing import Any, NamedTuple, Sequence

__all__ = ["MOVE_RECORD", "MoveFlags", "RecordField", "RecordLayout"]


class _FieldType(NamedTuple):
    struct: str
    numpy: str
    size: int


#: Each field type, by the name a RecordField gives it.
_TYPES = {"u32": _FieldType("I", "<u4", 4), "f32": _FieldType("f", "<f4", 4)}


class RecordField(NamedTuple):
    """One field of a record."""

    #: The field's name.
    name: str
    #: Its offset in bytes from the start of the record.
    offset: int
    #: Its type, ``"u32"`` or ``"f32"``, little-endian either way.
    type: str


@dataclass(frozen=True, init=False)
class RecordLayout:
    """The layout of a record, in every form a reader may want.

    A record is little-endian and packed: no padding between fields, none
    after. A layout that changes gets a new ``version`` rather than changing
    under its readers.
    """

    #: The record's name.
    name: str
    #: Bumped when the layout changes, so a reader can tell.
    version: int
    #: The fields, in order.
    fields: tuple[RecordField, ...]
    #: The size of one record in bytes.
    itemsize: int = field(init=False)

    def __init__(self, name: str, version: int, fields: Sequence[tuple[str, str]]):
        offset = 0
        made = []
        for field_name, field_type in fields:
            made.append(RecordField(field_name, offset, field_type))
            offset += _TYPES[field_type].size
        # Frozen, so set past the dataclass's own __setattr__.
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "version", version)
        object.__setattr__(self, "fields", tuple(made))
        object.__setattr__(self, "itemsize", offset)

    @property
    def struct(self) -> str:
        """A :mod:`struct` format for one record, as ``struct.unpack`` takes."""
        return "<" + "".join(_TYPES[each.type].struct for each in self.fields)

    @property
    def numpy(self) -> dict[str, Any]:
        """A numpy dtype specification, for ``np.dtype(layout.numpy)``."""
        return {
            "names": [each.name for each in self.fields],
            "formats": [_TYPES[each.type].numpy for each in self.fields],
            "offsets": [each.offset for each in self.fields],
            "itemsize": self.itemsize,
        }

    def __repr__(self) -> str:
        fields = ", ".join(f"{each.name}: {each.type}" for each in self.fields)
        return f"<RecordLayout {self.name} v{self.version} ({fields})>"


class MoveFlags(enum.IntFlag):
    """The bits of a move record's ``flags``."""

    #: The body is asleep after the step; on a move, it fell asleep on it.
    ASLEEP = 1


#: A body's place after a step, 24 bytes. ``key`` is the body's
#: :attr:`~box2d.body.Body.key`; ``cos`` and ``sin`` are its rotation, as Box2D
#: keeps it; ``flags`` holds :class:`MoveFlags`.
MOVE_RECORD = RecordLayout(
    "move",
    1,
    [
        ("key", "u32"),
        ("x", "f32"),
        ("y", "f32"),
        ("cos", "f32"),
        ("sin", "f32"),
        ("flags", "u32"),
    ],
)
