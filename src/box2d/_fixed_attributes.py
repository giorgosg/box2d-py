"""Engine objects refuse attributes they do not have.

A Box2D property set under a wrong name -- ``joint.enable_motor = True`` for
``joint.motor_enabled`` -- would otherwise add a plain attribute to the Python
object and change nothing in the simulation, with no error to say so. Two
testbed controls did nothing for exactly that reason.
"""

import difflib


class FixedAttributes:
    """Mixin: setting a public attribute the class does not define raises.

    Names starting with an underscore are the implementation's own and are
    left alone. Application data belongs on ``user_data``, which every engine
    object has.

    Only the library's own classes are fixed. A subclass defined elsewhere --
    ``class Game(World)`` keeping a score -- is the application's to add
    attributes to, as any Python class would be.
    """

    __slots__ = ()
    _fixed = False

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._fixed = cls.__module__.startswith("box2d.")

    def __setattr__(self, name, value):
        if self._fixed and name[0] != "_" and not hasattr(type(self), name):
            raise AttributeError(_unknown_attribute(self, name), name=name)
        super().__setattr__(name, value)


def _words(name):
    """The words of a name, ignoring order and a past-tense ending, so that
    ``enable_motor`` and ``motor_enabled`` read as the same name."""
    return sorted(word.removesuffix("d") for word in name.split("_"))


def _unknown_attribute(obj, name):
    owner = type(obj)
    public = [n for n in dir(owner) if not n.startswith("_")]
    # The same words in another order, then the name as the end of a longer
    # one (``hertz`` for ``spring_hertz``), then whatever is spelt closest.
    close = [n for n in public if _words(n) == _words(name)]
    close = close or [n for n in public if n.endswith(f"_{name}")]
    close = close or difflib.get_close_matches(name, public, n=1)
    hint = f" Did you mean {close[0]!r}?" if close else ""
    return (
        f"{owner.__name__} has no attribute {name!r}, and setting one would "
        f"change nothing in the simulation.{hint} Keep application data on "
        f"user_data."
    )
