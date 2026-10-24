"""
Lifetime tracking for Box2D handles.

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
relies on the user data each wrapper gives Box2D: a cffi handle to itself. A
handle does not keep its object alive, so every wrapper is held by its owner
for as long as Box2D has it -- the world holds bodies and joints, a body its
shapes and chains, a chain its segments -- and released when it is destroyed.
"""

from typing import Callable, Optional

from ._checked import ffi

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


def wrapper_for(
    object_id,
    is_valid: Callable[..., bool],
    get_user_data: Callable[..., object],
) -> Optional[object]:
    """The wrapper an id Box2D reported belongs to, or None if it is gone.

    Box2D's events are a record of the step that has finished, so they can
    name an object destroyed since. Its wrapper has been released by then, and
    following its handle would read freed memory, so the id is checked first.

    Args:
        object_id: The id, e.g. a ``b2ShapeId`` from a sensor event.
        is_valid: The Box2D validity function for this id type.
        get_user_data: The matching user data getter, e.g.
            ``lib.b2Shape_GetUserData``.

    Returns:
        The wrapper, or None if the id is no longer valid or has no handle.
    """
    if not is_valid(object_id):
        return None
    data = get_user_data(object_id)
    return ffi.from_handle(data) if data != ffi.NULL else None
