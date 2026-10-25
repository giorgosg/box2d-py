"""
Lifetime tracking for Box2D ids.

Box2D objects are not pointers, they are small value ids naming a slot in
storage the engine owns. Once the thing an id names is gone -- destroyed on its
own, or taken down with its world -- the id is stale, and handing a stale id
back to Box2D reads freed memory and segfaults the interpreter.

Every wrapper stores its id behind an :class:`IdRef`, which asks Box2D whether
the id is still live on each read and raises :class:`.DestroyedError` if it is
not. Box2D's own ``b2*_IsValid`` functions are safe to call on stale ids,
including ids whose world has already been destroyed, so this check never
crashes on the values it is meant to reject.

They are not enough on their own, though. A body, shape, chain, joint or
contact id names its world by the slot the world occupies, not by the world,
and a world made after one is destroyed takes the freed slot -- where the old
ids name the new world's objects, and Box2D calls them valid. So each wrapper
also holds its world's liveness flag, with :func:`join_world`, and is live
only while that world is. The flag is a plain Python one, which
:meth:`.World.destroy` -- the only way a world goes -- turns off: asking Box2D
about the world instead would cost a second call on every property read.

Going the other way, from an id Box2D hands back to the wrapper it belongs to,
is an :class:`IdTable` on the world: one for bodies, one for shapes (chain
segments included) and one for joints. Each wrapper is entered when it is made
and taken out on every path that destroys it -- on its own, with its body or
chain, or with the world -- so a table holds exactly the objects Box2D still
has, and keeps their wrappers alive meanwhile. Box2D's own user data is left
empty. It used to hold a cffi handle to each wrapper, which had to be checked
with Box2D before it could be followed, and which aborted the interpreter when
followed to a wrapper already collected; a table lookup is no slower than the
two together, and has nothing to dangle.
"""

from typing import Optional

#: Where a wrapper keeps its world's liveness flag. A World keeps its own
#: there too, so its own IdRef reads it the same way.
_WORLD_SLOT = "_world_alive"

#: The flag of an object that has no world to outlive. Every class with an
#: IdRef starts with it, so the check is one attribute read, never a lookup
#: with a fallback -- this runs on every property read.
_NO_WORLD = (True,)


def new_liveness():
    """A world's liveness flag: a one-item list, True until it is destroyed.

    A list rather than an attribute on the World so a wrapper can hold it
    without holding the world, and read it with one index.
    """
    return [True]


class DestroyedError(RuntimeError):
    """Raised when a Box2D object is used after it has been destroyed.

    This includes objects destroyed indirectly, such as a body whose world was
    destroyed, or a shape whose body was destroyed.
    """


def raw_id(obj, name: str):
    """Read a stored id without validating it.

    Args:
        obj: The wrapper holding the id.
        name: The :class:`IdRef` attribute name, e.g. ``"_body_id"``.

    Returns:
        The stored id, or None if it was never set or has been released.
    """
    return getattr(obj, f"_raw{name}", None)


def join_world(obj, world) -> None:
    """Record ``world`` as the world ``obj`` belongs to.

    From then on ``obj``'s :class:`IdRef` and :func:`is_live` treat its id as
    gone once that world is, whatever Box2D says of the id itself.

    Args:
        obj: A body, shape, chain or joint wrapper.
        world: Its :class:`.World`.
    """
    setattr(obj, _WORLD_SLOT, world._world_alive)


class IdRef:
    """Data descriptor exposing a Box2D id only while it remains valid.

    Reading the attribute validates the id and raises :class:`.DestroyedError`
    if the underlying object is gone. This puts the check on every use without
    touching the call sites, which matter because there are several hundred.

    Args:
        is_valid: The Box2D validity function for this id type,
            e.g. ``lib.b2Body_IsValid``.
        label: What to call the object in error messages, e.g. ``"body"``.
    """

    __slots__ = ("_is_valid", "_label", "_name", "_slot")

    def __init__(self, is_valid, label: str):
        self._is_valid = is_valid
        self._label = label

    def __set_name__(self, owner, name):
        self._name = name
        self._slot = f"_raw{name}"
        if not hasattr(owner, _WORLD_SLOT):
            setattr(owner, _WORLD_SLOT, _NO_WORLD)

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        raw = getattr(obj, self._slot, None)
        if raw is None or not obj._world_alive[0] or not self._is_valid(raw):
            raise DestroyedError(
                f"This {self._label} has been destroyed and can no longer be used."
            )
        return raw

    def __set__(self, obj, value):
        setattr(obj, self._slot, value)

    def __delete__(self, obj):
        setattr(obj, self._slot, None)


def is_live(obj, name: str, is_valid) -> bool:
    """Report whether a stored id is still valid, without raising.

    Args:
        obj: The wrapper holding the id.
        name: The :class:`IdRef` attribute name, e.g. ``"_shape_id"``.
        is_valid: The Box2D validity function for this id type.

    Returns:
        True if the id is set, its world is live, and Box2D still recognises
        it.
    """
    raw = raw_id(obj, name)
    return raw is not None and obj._world_alive[0] and bool(is_valid(raw))


class IdTable(dict):
    """A world's wrappers of one kind, keyed by their Box2D ids.

    The key is the id's slot, world and generation. Box2D bumps the generation
    each time it reuses a slot, so an id of something destroyed never finds
    whatever took its place, and two worlds' objects never meet in one table,
    even where their ids differ only in the world. The world part is needed
    for that: worlds built the same way hand out the same slots and
    generations.

    Every id this is asked about comes from Box2D, which can report objects
    destroyed since -- an event is a record of the step that has finished --
    so :meth:`find` answers None for an id not in the table, which is how a
    destroyed object reads in events. Where Box2D can only be naming something
    live, :meth:`require` raises instead, as a missing entry there is a bug.

    Args:
        kind: What the table holds, for error messages, e.g. ``"shape"``.
    """

    # Weak-referenceable, so a Contact can reach its world's shapes without
    # keeping the world alive.
    __slots__ = ("_kind", "__weakref__")

    def __init__(self, kind: str):
        super().__init__()
        self._kind = kind

    def add(self, object_id, wrapper) -> None:
        """Enter ``wrapper`` under ``object_id``. Called once it exists."""
        self[object_id.index1, object_id.world0, object_id.generation] = wrapper

    def remove(self, object_id) -> None:
        """Take out whatever is under ``object_id``, if anything.

        Taking out what is not there is not an error, so every destroy path
        can call this without knowing whether another got there first. An id
        of None -- one already let go of -- is not there either.
        """
        if object_id is None:
            return
        self.pop((object_id.index1, object_id.world0, object_id.generation), None)

    def holds(self, wrapper, object_id) -> bool:
        """Whether ``wrapper`` itself is in the table under ``object_id``."""
        found = self.get((object_id.index1, object_id.world0, object_id.generation))
        return found is wrapper

    def find(self, object_id) -> Optional[object]:
        """The wrapper of ``object_id``, or None if it is not in the table.

        Args:
            object_id: An id Box2D reported, e.g. a ``b2ShapeId`` from an event.
        """
        return self.get((object_id.index1, object_id.world0, object_id.generation))

    def require(self, object_id):
        """The wrapper of ``object_id``, which must be in the table.

        Raises:
            LookupError: If it is not. Box2D said the object is live, so this
                is a bug in the binding or an id from another world.
        """
        key = (object_id.index1, object_id.world0, object_id.generation)
        found = self.get(key)
        if found is None:
            raise LookupError(
                f"Box2D reported a {self._kind} (id {key}) that this world has "
                f"no object for"
            )
        return found
