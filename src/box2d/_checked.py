"""
The compiled library, with Box2D's input checks turned into exceptions.

Box2D validates what it is given -- a joint definition with a NaN anchor, a
negative density, a pogo spring with a negative rest length -- and in a
release build it handles a failed check by logging a line and returning
early. A setter silently does nothing; a create function returns a null id.
Either way Python carried on, and the mistake surfaced later and somewhere
else, typically as a DestroyedError from an object that was never created.

So this module installs a log callback, and wraps every library function
that can fail a check. The callback records the failure; the wrapper raises
:class:`InvalidInputError` as soon as the call that failed returns.

Getters and validity checks are not wrapped. They contain no checks, and they
are the hot path: every id access calls an ``_IsValid`` function. A test parses
Box2D's sources to make sure no function with a check is ever left unwrapped.

Box2D's other log messages -- a body going unstable, a snapshot from another
build -- are warnings rather than errors, and go to the ``box2d`` logger.
"""

import logging
import re
import types

from ._box2d import ffi, lib as _raw_lib

__all__ = ["lib", "ffi", "InvalidInputError", "is_checked"]

log = logging.getLogger("box2d")


class InvalidInputError(ValueError):
    """Box2D rejected an argument.

    The message names the Box2D function and the check that failed, e.g.
    ``b2CreatePogoJoint rejected its input: b2IsValidVec2( def->normal )``.
    """


# Exported from the package, so report it as living there.
InvalidInputError.__module__ = "box2d"


#: Failed checks reported by the log callback and not yet raised. A list
#: rather than a flag so that nothing is lost if two arrive together.
_pending = []

_INVALID_INPUT = re.compile(r"invalid input: (?P<condition>.*) in (?P<function>\w+)")


@ffi.callback("b2LogFcn")
def _on_log(message):
    text = ffi.string(message).decode("utf-8", "replace").strip()
    if text.startswith("invalid input"):
        _pending.append(text)
    else:
        log.warning(text)


_raw_lib.b2SetLogFcn(_on_log)


def _raise_pending(called):
    """Raise for the failed checks, naming the function that was called.

    Box2D names the function the check is written in, which is sometimes an
    internal helper -- every create-shape function checks the density in
    b2CreateShape -- so the helper is mentioned after the public name.
    """
    messages = list(_pending)
    _pending.clear()
    described = []
    for text in messages:
        match = _INVALID_INPUT.match(text)
        if match is None:
            described.append(text)
            continue
        where = "" if match["function"] == called else f" (in {match['function']})"
        described.append(f"{called} rejected its input: {match['condition']}{where}")
    raise InvalidInputError("; ".join(described))


# Functions that never check their input, and so are passed through untouched.
_UNCHECKED = re.compile(r"_(Get|Is)[A-Z]|^b2(Get|Default|Is)[A-Z]")


def is_checked(name: str) -> bool:
    """Whether calls to the named library function are checked for errors."""
    return name.startswith("b2") and not _UNCHECKED.search(name)


def _checked(function, name):
    def call(*args):
        result = function(*args)
        if _pending:
            _raise_pending(name)
        return result

    call.__name__ = call.__qualname__ = name
    call.__wrapped__ = function
    return call


class _CheckedLib:
    """Stands in for the cffi ``lib``, wrapping the functions that check input.

    Everything else -- constants, global variables, the task scheduler's
    function pointers -- is the library's own object. Wrapped functions are
    cached on first use; nothing else is, so a global variable is always read
    fresh.
    """

    def __getattr__(self, name):
        value = getattr(_raw_lib, name)
        # cffi cdata are all callable, constants included, so test for what
        # the library's functions actually are.
        if isinstance(value, types.BuiltinFunctionType) and is_checked(name):
            value = _checked(value, name)
            setattr(self, name, value)
        return value

    def __dir__(self):
        return dir(_raw_lib)


lib = _CheckedLib()
