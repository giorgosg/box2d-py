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
"""

from ._box2d import lib


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

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        raw = getattr(obj, self._slot, None)
        if raw is None or not self._is_valid(raw):
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
        True if the id is set and Box2D still recognises it.
    """
    raw = raw_id(obj, name)
    return raw is not None and bool(is_valid(raw))
