"""Where the scenarios the editor can open come from.

Two stores exist here: the scenarios shipped with the package, which are
readable but not writable, and a directory of the user's own, which is both.
The web build will add a third backed by a content-addressed store on the
network, which is the reason this is an interface at all rather than a pair of
functions over ``open()``.
"""

import os
import re
import sys
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

#: A scenario name has to survive being used as a filename and as the tail of a
#: module name, so it is held to what both accept: a Python identifier, in
#: practice. That is also what keeps a name off the rest of the filesystem --
#: ``..`` and ``/`` and ``C:\`` are all rejected by the same rule, with no path
#: arithmetic to get subtly wrong. It matters more than it looks: on the web
#: these names arrive from strangers.
NAME_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}\Z")


class StoreError(Exception):
    """A store could not do what was asked of it."""


def validate_name(name: str) -> str:
    """Check a scenario name, returning it unchanged.

    Raises:
        StoreError: If the name is not one a store will accept.
    """
    if not isinstance(name, str) or not NAME_PATTERN.match(name):
        raise StoreError(
            f"{name!r} is not a usable scenario name: letters, digits and "
            "underscores only, starting with a letter, up to 64 characters"
        )
    return name


@dataclass(frozen=True)
class ScenarioRef:
    """One scenario a store can produce, as the editor refers to it."""

    store: "ScenarioStore"
    name: str

    @property
    def label(self) -> str:
        return f"{self.store.label}/{self.name}.py"

    @property
    def writable(self) -> bool:
        return self.store.writable

    def read(self) -> str:
        return self.store.read(self.name)


class ScenarioStore:
    """A place scenario source can be read from, and sometimes written to."""

    #: Shown in the editor's file picker to say where a scenario came from.
    label = "?"

    #: False if write and delete will refuse.
    writable = False

    def names(self) -> list[str]:
        """Every scenario in the store, in the order to display them."""
        raise NotImplementedError

    def refs(self) -> list[ScenarioRef]:
        return [ScenarioRef(self, name) for name in self.names()]

    def read(self, name: str) -> str:
        raise NotImplementedError

    def write(self, name: str, source: str) -> ScenarioRef:
        raise StoreError(f"{self.label} scenarios are read-only")

    def delete(self, name: str) -> None:
        raise StoreError(f"{self.label} scenarios are read-only")

    def free_name(self, stem: str) -> str:
        """A name like ``stem`` that nothing in the store is using yet."""
        validate_name(stem)
        taken = set(self.names())
        if stem not in taken:
            return stem
        for suffix in range(1, 1000):
            candidate = f"{stem}_{suffix}"
            if candidate not in taken:
                return candidate
        raise StoreError(f"no free name left around {stem!r}")


class BuiltinStore(ScenarioStore):
    """The ``tb_*.py`` modules that ship with the testbed.

    Read-only on purpose. They are the worked examples, and an installed copy
    of them lives in site-packages where editing in place would be both
    surprising and lost on the next upgrade. The editor's Fork button is how
    one of these becomes something you can change.
    """

    label = "builtin"
    writable = False

    def __init__(self, package: str = "box2d_testbed"):
        self.package = package

    def _files(self):
        return resources.files(self.package)

    def names(self) -> list[str]:
        found = []
        for entry in self._files().iterdir():
            name = entry.name
            if name.startswith("tb_") and name.endswith(".py"):
                found.append(name[: -len(".py")])
        return sorted(found)

    def read(self, name: str) -> str:
        validate_name(name)
        if name not in self.names():
            raise StoreError(f"no builtin scenario file {name!r}")
        return self._files().joinpath(f"{name}.py").read_text(encoding="utf-8")


class UserStore(ScenarioStore):
    """A directory of the user's own scenarios."""

    label = "user"
    writable = True

    def __init__(self, path):
        self.path = Path(path)

    def path_for(self, name: str) -> Path:
        return self.path / f"{validate_name(name)}.py"

    def names(self) -> list[str]:
        if not self.path.is_dir():
            return []
        return sorted(
            path.stem
            for path in self.path.glob("*.py")
            # A file dropped in by hand can be named anything; showing one the
            # loader would then refuse to import is worse than leaving it out.
            if NAME_PATTERN.match(path.stem)
        )

    def read(self, name: str) -> str:
        try:
            return self.path_for(name).read_text(encoding="utf-8")
        except OSError as exc:
            raise StoreError(f"cannot read scenario {name!r}: {exc}") from exc

    def write(self, name: str, source: str) -> ScenarioRef:
        path = self.path_for(name)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source, encoding="utf-8")
        except OSError as exc:
            raise StoreError(f"cannot save scenario {name!r}: {exc}") from exc
        return ScenarioRef(self, name)

    def delete(self, name: str) -> None:
        try:
            self.path_for(name).unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise StoreError(f"cannot delete scenario {name!r}: {exc}") from exc


def user_scenario_dir() -> Path:
    """Where the user's scenarios live, honouring the platform's conventions.

    ``BOX2D_TESTBED_SCENARIOS`` overrides it, which is what the tests use and
    what makes a scenario directory checked into a project of your own
    workable.
    """
    override = os.environ.get("BOX2D_TESTBED_SCENARIOS")
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData/Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library/Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    return base / "box2d-testbed" / "scenarios"


#: What New drops into a fresh file. Absolute imports rather than relative
#: ones: the loader execs this outside the package, and it should also work if
#: it is later copied into a project of your own.
TEMPLATE = '''from box2d_testbed.base_test import BaseTest, UI


class {class_name}(BaseTest, category="User", name="{name}"):
    """One line on what this scenario shows."""

    camera_center = (0, 5)
    camera_zoom = 12.0

    # Every UI.* declaration becomes a control in the panel on the right.
    drop_height = UI.float(8.0, min=1.0, max=20.0)

    def setup(self):
        """Build the scene. Called again by Reset, and after every save."""
        self.world.new_body().static().segment((-20, 0), (20, 0)).build()

        self.box = (
            self.world.new_body()
            .dynamic()
            .position(0, self.drop_height)
            .box(1, 1, friction=0.4)
            .build()
        )

    def after_step(self, dt):
        """Called once per physics step."""

    def debug_draw(self, debug_draw):
        """Called once per frame, on top of the rendered world."""
        debug_draw.draw_string((-6, 12), f"height {{self.box.position.y:.1f}}")

    @drop_height.callback
    def on_drop_height(self, key, value):
        # Changing how a scene is built means building it again.
        self.rebuild()
'''


def template_for(name: str) -> str:
    """The starter scenario, named after the file it is going into."""
    validate_name(name)
    class_name = "".join(part.title() for part in name.split("_") if part) or "Scenario"
    return TEMPLATE.format(class_name=class_name, name=name)
