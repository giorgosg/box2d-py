"""Where the scenarios the editor can open come from.

The shipped scenarios are readable, the user's directory is writable, and the
sharing server is immutable and addressed by a SHA-256 digest. Keeping all
three behind stores lets the editor treat their source alike while preserving
the important differences: a builtin cannot be overwritten, and downloaded
Python is opened for review rather than run on arrival.
"""

import asyncio
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

#: A scenario name has to survive being used as a filename and as the tail of a
#: module name, so it is held to what both accept: a Python identifier, in
#: practice. That is also what keeps a name off the rest of the filesystem --
#: ``..`` and ``/`` and ``C:\`` are all rejected by the same rule, with no path
#: arithmetic to get subtly wrong. It matters more than it looks: on the web
#: these names arrive from strangers.
NAME_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}\Z")

#: The Worker accepts the same limit. Checking before opening a connection
#: makes an accidental giant paste cheap, while the server remains the actual
#: enforcement boundary.
MAX_SCENARIO_BYTES = 64 * 1024

#: Shared scenario names are the complete digest returned by the server.
HASH_PATTERN = re.compile(r"[0-9a-f]{64}\Z")

DEFAULT_SCENARIO_SERVER = "http://127.0.0.1:8787"


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

    @property
    def runnable(self) -> bool:
        return self.store.runnable

    @property
    def load_name(self) -> str:
        """A safe synthetic Python module name for this scenario.

        Local names already are Python identifiers. A content hash can start
        with a digit, so the shared store gives it an internal prefix when the
        user explicitly runs it.
        """
        return self.store.load_name(self.name)

    def read(self) -> str:
        return self.store.read(self.name)


class ScenarioStore:
    """A place scenario source can be read from, and sometimes written to."""

    #: Shown in the editor's file picker to say where a scenario came from.
    label = "?"

    #: False if write and delete will refuse.
    writable = False

    #: True when the source is standalone code the loader can execute. Builtin
    #: modules use package-relative imports and are meant to be forked first.
    runnable = False

    def names(self) -> list[str]:
        """Every scenario in the store, in the order to display them."""
        raise NotImplementedError

    def refs(self) -> list[ScenarioRef]:
        return [ScenarioRef(self, name) for name in self.names()]

    def read(self, name: str) -> str:
        raise NotImplementedError

    def load_name(self, name: str) -> str:
        """Name to hand to the scenario loader when this source is run."""
        return validate_name(name)

    def fork_stem(self, name: str) -> str:
        """Base filename to use when this scenario is copied to UserStore."""
        return validate_name(name)

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
    runnable = True

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


class SharedStore(ScenarioStore):
    """The public, immutable scenario server.

    ``publish`` adds source and returns its content-addressed reference;
    ``reference`` turns either a bare digest or one of this server's links into
    a reference. Names are remembered only for this app session because the
    server deliberately has no account or per-user listing.

    The desktop transport is synchronous at this layer, with async wrappers
    that move it off the ImGui thread when explicitly enabled. The browser
    subclass implements the same async surface with Fetch.
    """

    label = "shared"
    writable = False
    runnable = True

    def __init__(self, base_url: str = None, *, timeout: float = 5.0, opener=None):
        self.base_url = (
            base_url
            or os.environ.get("BOX2D_TESTBED_SERVER")
            or DEFAULT_SCENARIO_SERVER
        ).rstrip("/")
        self.timeout = timeout
        self._opener = opener or urlopen
        self._names: list[str] = []

    def names(self) -> list[str]:
        return list(self._names)

    def load_name(self, name: str) -> str:
        self._validate_hash(name)
        # Keep the loader's longstanding 64-character identifier limit. The
        # remaining 224 hash bits are still far beyond any realistic collision
        # concern, while the full digest remains the external name and URL.
        return f"shared_{name[:56]}"

    def fork_stem(self, name: str) -> str:
        self._validate_hash(name)
        return f"shared_{name[:12]}"

    def url_for(self, name: str) -> str:
        self._validate_server()
        self._validate_hash(name)
        return f"{self.base_url}/s/{name}"

    def reference(self, value: str, *, remember: bool = True) -> ScenarioRef:
        """Resolve a full sharing URL or a bare SHA-256 digest."""
        if not isinstance(value, str):
            raise StoreError(f"{value!r} is not a scenario hash or link")
        value = value.strip()
        if HASH_PATTERN.fullmatch(value):
            name = value
        else:
            self._validate_server()
            parsed = urlsplit(value)
            configured = urlsplit(self.base_url)
            expected_prefix = configured.path.rstrip("/") + "/s/"
            same_server = (
                parsed.scheme.lower(),
                parsed.netloc.lower(),
            ) == (configured.scheme.lower(), configured.netloc.lower())
            if not same_server or not parsed.path.startswith(expected_prefix):
                raise StoreError(f"paste a SHA-256 hash or a link from {self.base_url}")
            name = parsed.path[len(expected_prefix) :]
            if "/" in name:
                raise StoreError(f"{value!r} is not a scenario link")
        self._validate_hash(name)
        if remember:
            self._remember(name)
        return ScenarioRef(self, name)

    def publish(self, source: str) -> ScenarioRef:
        """Store source and return the immutable reference the server assigned."""
        if not isinstance(source, str):
            raise StoreError("a shared scenario must be text")
        body = source.encode("utf-8")
        if len(body) > MAX_SCENARIO_BYTES:
            raise StoreError(
                f"scenario is {len(body)} bytes; the sharing limit is "
                f"{MAX_SCENARIO_BYTES}"
            )
        expected = hashlib.sha256(body).hexdigest()
        request = Request(
            f"{self._server_url()}/s",
            data=body,
            headers={"Content-Type": "text/x-python; charset=utf-8"},
            method="POST",
        )
        payload = self._open(request, response_limit=8 * 1024)
        try:
            result = json.loads(payload.decode("utf-8"))
            returned = result["id"]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise StoreError(
                "sharing server returned an invalid save response"
            ) from exc
        if returned != expected:
            raise StoreError(
                "sharing server returned a hash that does not match the source"
            )
        self._remember(returned)
        return ScenarioRef(self, returned)

    async def publish_async(self, source: str) -> ScenarioRef:
        """Publish without blocking the UI thread in the desktop opt-in mode."""
        return await asyncio.to_thread(self.publish, source)

    def read(self, name: str) -> str:
        """Fetch source and verify that it really has the requested address."""
        self._validate_hash(name)
        request = Request(self.url_for(name), method="GET")
        body = self._open(request, response_limit=MAX_SCENARIO_BYTES)
        actual = hashlib.sha256(body).hexdigest()
        if actual != name:
            raise StoreError(
                f"sharing server returned content that does not match {name}"
            )
        try:
            return body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise StoreError("shared scenario is not UTF-8 text") from exc

    async def read_async(self, name: str) -> str:
        """Read without blocking the UI thread in the desktop opt-in mode."""
        return await asyncio.to_thread(self.read, name)

    def _server_url(self) -> str:
        self._validate_server()
        return self.base_url

    def _validate_server(self) -> None:
        parsed = urlsplit(self.base_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise StoreError("BOX2D_TESTBED_SERVER must be an http:// or https:// URL")
        if parsed.query or parsed.fragment:
            raise StoreError("the sharing server URL cannot contain ? or #")

    @staticmethod
    def _validate_hash(name: str) -> str:
        if not isinstance(name, str) or not HASH_PATTERN.fullmatch(name):
            raise StoreError(f"{name!r} is not a complete SHA-256 scenario hash")
        return name

    def _remember(self, name: str) -> None:
        if name not in self._names:
            self._names.insert(0, name)

    def _open(self, request: Request, *, response_limit: int) -> bytes:
        try:
            with self._opener(request, timeout=self.timeout) as response:
                body = response.read(response_limit + 1)
        except HTTPError as exc:
            detail = ""
            try:
                detail = exc.read(1024).decode("utf-8", errors="replace").strip()
            except OSError:
                pass
            suffix = f": {detail}" if detail else ""
            raise StoreError(
                f"sharing server returned HTTP {exc.code}{suffix}"
            ) from exc
        except (OSError, URLError) as exc:
            raise StoreError(f"cannot reach sharing server: {exc}") from exc
        if len(body) > response_limit:
            raise StoreError("sharing server returned more data than allowed")
        return body


class BrowserSharedStore(SharedStore):
    """A SharedStore transported by Pyodide's asynchronous browser Fetch API."""

    def publish(self, source: str) -> ScenarioRef:
        raise StoreError("browser sharing must be awaited")

    def read(self, name: str) -> str:
        raise StoreError("browser downloads must be awaited")

    async def publish_async(self, source: str) -> ScenarioRef:
        if not isinstance(source, str):
            raise StoreError("a shared scenario must be text")
        source_bytes = source.encode("utf-8")
        if len(source_bytes) > MAX_SCENARIO_BYTES:
            raise StoreError(
                f"scenario is {len(source_bytes)} bytes; the sharing limit is "
                f"{MAX_SCENARIO_BYTES}"
            )
        expected = hashlib.sha256(source_bytes).hexdigest()
        payload = await self._fetch(
            f"{self._server_url()}/s",
            method="POST",
            body=source,
            response_limit=8 * 1024,
        )
        try:
            result = json.loads(payload.decode("utf-8"))
            returned = result["id"]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise StoreError(
                "sharing server returned an invalid save response"
            ) from exc
        if returned != expected:
            raise StoreError(
                "sharing server returned a hash that does not match the source"
            )
        self._remember(returned)
        return ScenarioRef(self, returned)

    async def read_async(self, name: str) -> str:
        self._validate_hash(name)
        body = await self._fetch(
            self.url_for(name), method="GET", response_limit=MAX_SCENARIO_BYTES
        )
        if hashlib.sha256(body).hexdigest() != name:
            raise StoreError(
                f"sharing server returned content that does not match {name}"
            )
        try:
            return body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise StoreError("shared scenario is not UTF-8 text") from exc

    async def _fetch(
        self,
        url: str,
        *,
        method: str,
        response_limit: int,
        body: str = None,
    ) -> bytes:
        try:
            from pyodide.http import pyfetch

            options = {"method": method}
            if body is not None:
                options.update(
                    body=body,
                    headers={"Content-Type": "text/x-python; charset=utf-8"},
                )
            response = await pyfetch(url, **options)
            if not response.ok:
                detail = (await response.text())[:1024].strip()
                suffix = f": {detail}" if detail else ""
                raise StoreError(
                    f"sharing server returned HTTP {response.status}{suffix}"
                )
            payload = await response.bytes()
        except StoreError:
            raise
        except (ImportError, OSError) as exc:
            raise StoreError(f"cannot reach sharing server: {exc}") from exc
        if len(payload) > response_limit:
            raise StoreError("sharing server returned more data than allowed")
        return payload


def configured_shared_store() -> SharedStore | None:
    """The sharing client explicitly selected for this runtime, if any.

    Desktop keeps its uncluttered local-file editor by default. Set
    ``BOX2D_TESTBED_SHARING=desktop`` to opt in there; the web bootstrap sets
    it to ``web`` and points the client at its own Worker origin.
    """
    mode = os.environ.get("BOX2D_TESTBED_SHARING", "").lower()
    if mode == "web":
        return BrowserSharedStore()
    if mode in ("1", "true", "desktop"):
        return SharedStore()
    return None


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
