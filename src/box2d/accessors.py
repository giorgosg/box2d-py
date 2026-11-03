"""
Descriptors for properties backed by a pair of Box2D functions.

Most of this binding is the same shape repeated: a getter that calls one
``b2*_Get*`` with an object's id, and a setter that calls the matching
``b2*_Set*`` with a coerced value. Written by hand that is eight lines per
property and around 170 properties, with the coercion and the id lookup
restated every time -- and each restatement is somewhere the rule can be got
wrong, which is how joint anchors ended up rejecting b2Vec2.

Declaring them instead states the rule once::

    class Body:
        _body_id = IdRef(lib.b2Body_IsValid, "body")

        angular_velocity = b2_float(
            lib.b2Body_GetAngularVelocity,
            lib.b2Body_SetAngularVelocity,
            doc="Angular velocity in radians per second.",
        )

The id attribute is found automatically: an accessor looks through its owner
class for the :class:`~box2d.lifetime.IdRef` and reads through that, so the
lifetime guard applies to every accessor without being repeated either.
"""

from typing import Any, Callable, Generic, Optional, Self, TypeVar, overload

from .lifetime import IdRef
from .math import Vec2, VectorLike

#: What reading the property gives.
T = TypeVar("T")
#: What assigning the property takes, which may be looser than what it gives:
#: a Vec2 property takes any vector-like.
S = TypeVar("S")


def _find_id_attribute(owner: type) -> str:
    """Return the name of the IdRef on this class, e.g. ``"_body_id"``."""
    for klass in owner.__mro__:
        for name, value in vars(klass).items():
            if isinstance(value, IdRef):
                return name
    raise TypeError(
        f"{owner.__name__} has no IdRef, so its accessors have no id to read "
        f"through. Give it one, e.g. _body_id = IdRef(lib.b2Body_IsValid, 'body')."
    )


class B2Accessor(Generic[T, S]):
    """A property reading and writing through a pair of Box2D functions.

    Args:
        getter: The ``b2*_Get*`` function, taking the object's id.
        setter: The matching ``b2*_Set*`` function, or None for a read-only
            property.
        adapt_out: Applied to whatever the getter returns, to turn a C value
            into a Python one.
        adapt_in: Applied to the assigned value before the setter sees it.
        extra_set_args: Extra arguments the setter takes after the value, such
            as Box2D's updateBodyMass flag.
        doc: The property's docstring.

    The two type parameters are what reading gives and what assigning takes,
    so a type checker and an editor see an accessor as the property it is.
    """

    def __init__(
        self,
        getter: Callable[..., Any],
        setter: Optional[Callable[..., Any]] = None,
        *,
        adapt_out: Optional[Callable[[Any], T]] = None,
        adapt_in: Optional[Callable[[S], Any]] = None,
        extra_set_args: tuple[Any, ...] = (),
        doc: Optional[str] = None,
    ) -> None:
        self._getter = getter
        self._setter = setter
        self._adapt_out = adapt_out
        self._adapt_in = adapt_in
        self._extra = tuple(extra_set_args)
        self._name: Optional[str] = None
        self._id: Optional[str] = None
        self.__doc__ = doc

    @property
    def settable(self) -> bool:
        """Whether assigning this property does anything, rather than raise."""
        return self._setter is not None

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name
        self._id = _find_id_attribute(owner)

    @overload
    def __get__(self, obj: None, objtype: Optional[type] = None) -> Self: ...

    @overload
    def __get__(self, obj: object, objtype: Optional[type] = None) -> T: ...

    def __get__(self, obj: object, objtype: Optional[type] = None) -> "T | Self":
        if obj is None:
            return self
        value = self._getter(getattr(obj, self._id))
        return self._adapt_out(value) if self._adapt_out is not None else value

    def __set__(self, obj: object, value: S) -> None:
        if self._setter is None:
            raise AttributeError(f"{type(obj).__name__}.{self._name} is read-only.")
        if self._adapt_in is not None:
            value = self._adapt_in(value)
        self._setter(getattr(obj, self._id), value, *self._extra)


def _to_b2vec2(value: VectorLike) -> Any:
    return Vec2(value).b2Vec2[0]


def _from_b2vec2(value: Any) -> Vec2:
    return Vec2(value.x, value.y)


def b2_float(
    getter: Callable[..., Any],
    setter: Optional[Callable[..., Any]] = None,
    *,
    extra_set_args: tuple[Any, ...] = (),
    doc: Optional[str] = None,
) -> B2Accessor[float, float]:
    """A float property. Assigned values are coerced with ``float``."""
    return B2Accessor(
        getter, setter, adapt_in=float, extra_set_args=extra_set_args, doc=doc
    )


def b2_bool(
    getter: Callable[..., Any],
    setter: Optional[Callable[..., Any]] = None,
    *,
    doc: Optional[str] = None,
) -> B2Accessor[bool, bool]:
    """A boolean property. Assigned values are coerced with ``bool``."""
    return B2Accessor(getter, setter, adapt_in=bool, doc=doc)


def b2_int(
    getter: Callable[..., Any],
    setter: Optional[Callable[..., Any]] = None,
    *,
    doc: Optional[str] = None,
) -> B2Accessor[int, int]:
    """An integer property. Assigned values are coerced with ``int``."""
    return B2Accessor(getter, setter, adapt_in=int, doc=doc)


def b2_vector(
    getter: Callable[..., Any],
    setter: Optional[Callable[..., Any]] = None,
    *,
    doc: Optional[str] = None,
) -> B2Accessor[Vec2, VectorLike]:
    """A Vec2 property, accepting any vector-like when assigned."""
    return B2Accessor(
        getter, setter, adapt_out=_from_b2vec2, adapt_in=_to_b2vec2, doc=doc
    )
