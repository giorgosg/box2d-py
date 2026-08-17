"""Turning edited source into registered scenarios.

A scenario is a class, and a scenario file is a module that defines one. This
runs such a module and works out what it registered, so that saving a file the
second time replaces what the first save produced instead of piling up beside
it. Nothing here raises into the app's frame loop: a file that will not compile
or blows up on import comes back as a LoadError carrying the line to point at.
"""

import sys
import traceback
import types
from pathlib import Path

from .base_test import BaseTest
from .scenario_store import ScenarioStore, StoreError, validate_name

#: User scenarios are executed as submodules of this, which exists only in
#: sys.modules. Giving them a package keeps their tracebacks and their
#: __name__ readable, and means two files can define classes of the same name.
USER_PACKAGE = "box2d_testbed_user"


class LoadError(Exception):
    """A scenario file did not load.

    Attributes:
        line: Where to put the editor's marker, if it is known.
        detail: The full traceback, for the pane that has room for it.
    """

    def __init__(self, message: str, line: int = None, detail: str = None):
        super().__init__(message)
        self.message = message
        self.line = line
        self.detail = detail or message


def _parent_package() -> types.ModuleType:
    """The synthetic package user scenarios are loaded into."""
    module = sys.modules.get(USER_PACKAGE)
    if module is None:
        module = types.ModuleType(USER_PACKAGE)
        # Empty rather than absent: relative imports inside a scenario then
        # fail with "no known parent package" instead of a KeyError from the
        # import machinery.
        module.__path__ = []
        sys.modules[USER_PACKAGE] = module
    return module


def _registry_snapshot():
    return {category: dict(tests) for category, tests in BaseTest.registry.items()}


def _registry_restore(snapshot):
    """Put the registry back exactly as the snapshot found it.

    In place, because state.all_tests and the Tests panel hold references to
    the registry and to the per-category dicts inside it.
    """
    for category in list(BaseTest.registry):
        if category not in snapshot:
            del BaseTest.registry[category]
    for category, tests in snapshot.items():
        current = BaseTest.registry.setdefault(category, {})
        current.clear()
        current.update(tests)


def _newly_registered(snapshot):
    """Every (category, name, cls) the last exec added or replaced."""
    added = []
    for category, tests in BaseTest.registry.items():
        for name, cls in tests.items():
            if snapshot.get(category, {}).get(name) is not cls:
                added.append((category, name, cls))
    return added


class ScenarioLoader:
    """Loads scenario source, and remembers what each file registered."""

    def __init__(self):
        # file name -> [(category, scenario name, class), ...]
        self._generations: dict[str, list] = {}

    def classes_for(self, name: str) -> list:
        """The scenario classes the named file currently has registered."""
        return [cls for _, _, cls in self._generations.get(name, ())]

    def owner_of(self, cls) -> str:
        """Which file registered this class, or None for a builtin."""
        for name, entries in self._generations.items():
            if any(entry[2] is cls for entry in entries):
                return name
        return None

    def unload(self, name: str) -> None:
        """Drop what a previous load of this file registered."""
        for category, scenario_name, cls in self._generations.pop(name, ()):
            tests = BaseTest.registry.get(category)
            # Only if it is still ours: another file may have claimed the name
            # since, and dropping its entry would be worse than leaving stale.
            if tests is not None and tests.get(scenario_name) is cls:
                del tests[scenario_name]
            if tests is not None and not tests:
                BaseTest.registry.pop(category, None)

    def load_source(self, name: str, source: str, filename: str = None) -> list:
        """Run a scenario file and register what it defines.

        Args:
            name: The file's name, without the extension.
            source: Its Python source.
            filename: Where it lives, for tracebacks. A placeholder is used
                for an unsaved buffer.

        Returns:
            list: The scenario classes it registered.

        Raises:
            LoadError: If it does not compile, raises on import, or defines no
                scenario. The registry is left as it was in every case.
        """
        validate_name(name)
        filename = filename or f"<scenario {name}>"
        module_name = f"{USER_PACKAGE}.{name}"

        try:
            code = compile(source, filename, "exec")
        except SyntaxError as exc:
            raise LoadError(
                f"{exc.msg} (line {exc.lineno})",
                line=exc.lineno,
                detail="".join(traceback.format_exception_only(type(exc), exc)),
            ) from exc

        module = types.ModuleType(module_name)
        module.__file__ = filename
        module.__package__ = USER_PACKAGE
        _parent_package()

        snapshot = _registry_snapshot()
        previous_module = sys.modules.get(module_name)
        sys.modules[module_name] = module
        try:
            exec(code, module.__dict__)
        except BaseException as exc:
            _registry_restore(snapshot)
            if previous_module is None:
                sys.modules.pop(module_name, None)
            else:
                sys.modules[module_name] = previous_module
            raise LoadError(
                _describe(exc),
                line=_line_in(exc, filename),
                detail=_format_exception(exc),
            ) from exc

        registered = _newly_registered(snapshot)
        if not registered:
            _registry_restore(snapshot)
            sys.modules.pop(module_name, None)
            raise LoadError(
                "no scenario in this file: it defines no BaseTest subclass "
                "with a category and a name"
            )

        # Only now that the new generation is in place, so a file that fails
        # to load leaves the scenario you had working still working.
        self.unload(name)
        self._generations[name] = registered
        return [cls for _, _, cls in registered]

    def load_ref(self, ref) -> list:
        """Load a scenario straight from its store."""
        source = ref.read()
        path = getattr(ref.store, "path_for", None)
        return self.load_source(
            ref.load_name, source, filename=str(path(ref.name)) if path else None
        )

    def load_store(self, store: ScenarioStore) -> list:
        """Load every scenario in a store, at startup.

        One bad file must not keep the rest out, and must not stop the testbed
        from starting, so failures are collected rather than raised.

        Returns:
            list: One LoadError per file that would not load.
        """
        errors = []
        for ref in store.refs():
            try:
                self.load_ref(ref)
            except (LoadError, StoreError) as exc:
                if isinstance(exc, StoreError):
                    exc = LoadError(str(exc))
                errors.append((ref, exc))
        return errors


def _describe(exc: BaseException) -> str:
    """One line about what went wrong, with a hint where one helps."""
    message = f"{type(exc).__name__}: {exc}"
    if isinstance(exc, ModuleNotFoundError) and (exc.name or "").startswith(
        USER_PACKAGE
    ):
        # A file copied out of the package by hand rather than forked, still
        # carrying the relative imports that only work inside it.
        return (
            f"{message}\nrelative imports do not work in a scenario file; write "
            "'from box2d_testbed.base_test import BaseTest, UI'"
        )
    return message


def _line_in(exc: BaseException, filename: str):
    """The last line of ours the exception passed through."""
    line = None
    for frame in traceback.extract_tb(exc.__traceback__):
        if frame.filename == filename:
            line = frame.lineno
    return line


def _format_exception(exc: BaseException) -> str:
    """The traceback, with this module's own frames trimmed off the top."""
    formatted = traceback.format_exception(type(exc), exc, exc.__traceback__)
    # The first entry is the "Traceback (most recent call last):" line and the
    # second is our exec() call, which tells the reader nothing about their bug.
    if len(formatted) > 2 and __file__ in formatted[1]:
        formatted = formatted[:1] + formatted[2:]
    return "".join(formatted)


#: The testbed's one loader. A scenario file's registrations have to be tracked
#: across saves, and there is one registry for them to land in, so tracking
#: them anywhere but a single place would let two loaders disagree about who
#: owns a name.
loader = ScenarioLoader()


def source_path_hint(cls) -> str:
    """Where a scenario class came from, for the editor to open it.

    Returns the file's name without extension, for a user scenario or a
    builtin alike, or None if it cannot be worked out.
    """
    name = loader.owner_of(cls)
    if name is not None:
        return name
    module = getattr(cls, "__module__", "")
    if module.startswith("box2d_testbed.tb_"):
        return module.rsplit(".", 1)[-1]
    path = getattr(sys.modules.get(module, None), "__file__", None)
    return Path(path).stem if path else None
