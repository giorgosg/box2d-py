"""Engine objects refuse attributes they do not have.

A Box2D property set under a wrong name -- ``joint.motor_enabled = True`` for
``joint.enable_motor`` -- would otherwise add a plain attribute to the Python
object and change nothing in the simulation, with no error to say so. Two
testbed controls did nothing for exactly that reason.
"""

import difflib
import inspect

_MISSING = object()

#: (class, name) -> whether assigning that name on an instance is allowed.
#: Only the library's own classes are looked up, so this stays small.
_settable = {}


class FixedAttributes:
    """Mixin: assigning a public name the class does not let you set raises.

    What can be set is what the class declares as data: its properties, and
    plain class attributes such as ``user_data``. Anything else -- a name it
    does not have, or one of its methods -- would only put a Python attribute
    on the object that Box2D never sees. Names starting with an underscore are
    the implementation's own and are left alone.

    Only the library's own classes are fixed. A subclass defined elsewhere --
    ``class Game(World)`` keeping a score -- is the application's to add
    attributes to, as any Python class would be.
    """

    __slots__ = ()
    _fixed = False

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # __package__ rather than "box2d", so a vendored copy is still fixed.
        cls._fixed = cls.__module__.startswith(f"{__package__}.")

    def __setattr__(self, name, value):
        if self._fixed and not name.startswith("_"):
            owner = type(self)
            allowed = _settable.get((owner, name))
            if allowed is None:
                allowed = _settable[owner, name] = _is_data(owner, name)
            if not allowed:
                raise AttributeError(_refusal(owner, name), name=name)
        super().__setattr__(name, value)


def _is_data(owner, name):
    """Whether ``name`` is something on ``owner`` an instance may assign."""
    attr = inspect.getattr_static(owner, name, _MISSING)
    if attr is _MISSING:
        return False
    if hasattr(type(attr), "__set__"):
        return True  # a property or an accessor
    return not (callable(attr) or isinstance(attr, (classmethod, staticmethod)))


def _can_set(owner, name):
    """Whether assigning ``name`` would work, not just be let through.

    A read-only property or accessor passes :func:`_is_data` so that its own
    read-only error is the one raised, but it is no use as a suggestion.
    """
    if not _is_data(owner, name):
        return False
    attr = inspect.getattr_static(owner, name)
    if isinstance(attr, property):
        return attr.fset is not None
    return getattr(attr, "settable", True)


def _words(name):
    """The words of a name, ignoring order and a past-tense ending, so that
    ``motor_enabled`` and ``enable_motor`` read as the same name."""
    return sorted(word.removesuffix("d") for word in name.split("_"))


def _refusal(owner, name):
    if inspect.getattr_static(owner, name, _MISSING) is not _MISSING:
        return (
            f"{owner.__name__}.{name} is a method, not a setting; assigning to "
            f"it would only hide the method."
        )

    settable = [n for n in dir(owner) if not n.startswith("_") and _can_set(owner, n)]
    # The same words in another order, then the name as the end of longer
    # ones (``hertz`` for ``spring_hertz``), then names containing it less its
    # first or last word (``spring_force_range`` for ``lower_spring_force``
    # and ``upper_spring_force``), then whatever is spelt closest.
    close = [n for n in settable if _words(n) == _words(name)]
    if not close and len(name) >= 3:
        close = [n for n in settable if n.endswith(f"_{name}")]
    words = name.split("_")
    if not close and len(words) >= 3:
        cores = {"_".join(words[1:]), "_".join(words[:-1])}
        close = [n for n in settable if any(f"_{c}_" in f"_{n}_" for c in cores)]
    close = close or difflib.get_close_matches(name, settable, n=1)
    if len(close) == 1:
        hint = f" Did you mean {close[0]!r}?"
    elif close:
        hint = f" Did you mean one of {', '.join(map(repr, close))}?"
    else:
        hint = ""
    return (
        f"{owner.__name__} has no attribute {name!r}, and setting one would "
        f"change nothing in the simulation.{hint} Keep application data on "
        f"user_data."
    )
