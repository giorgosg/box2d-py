# tests/test_doc_examples.py
"""The Python in the README and the documentation pages runs.

Each file's blocks run in order in one namespace, as a reader working down the
page would run them: a later block may use what an earlier one made. A block
written as a ``>>>`` session runs as a doctest, so its output is checked too.

A page whose examples assume names already bound -- the testbed's console
page, whose session is typed where the console binds ``test`` and ``world`` --
gets them from its entry in PRELUDES, bound as the testbed would bind them. A
README block that cannot run here at all is preceded by an HTML comment
starting ``not run:``, which renders as nothing on GitHub and PyPI.
"""

import contextlib
import doctest
import io
import re
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
DOCS = ROOT / "docs" / "source"
GLANCE = sorted((DOCS / "glance").glob("*.rst"))
INSTALL = DOCS / "getting_started" / "install.rst"
QUICKSTART = DOCS / "getting_started" / "quickstart.rst"
#: The guides, in the order the front page lists them.
GUIDES = [
    DOCS / "guides" / f"{name}.rst"
    for name in [
        "concepts",
        "lifetime",
        "events",
        "queries",
        "callbacks_threading",
        "character_movement",
        "debug_drawing",
    ]
]
SCENARIOS = DOCS / "testbed" / "scenarios.rst"
CONSOLE = DOCS / "testbed" / "console.rst"
#: The testbed's pages, in the order the front page lists them.
TESTBED = [
    DOCS / "testbed" / "running.rst",
    SCENARIOS,
    CONSOLE,
    DOCS / "testbed" / "browser.rst",
]
#: Every page whose Python is run, the front page included.
PAGES = [DOCS / "index.rst", INSTALL, QUICKSTART, *GLANCE, *GUIDES, *TESTBED]


def _page_id(path):
    """A page's test id, its path under docs/source, e.g. glance/index.rst."""
    return path.relative_to(DOCS).as_posix()


_MARKDOWN_BLOCK = re.compile(
    r"(?P<before>[^\n]*)\n```python\n(?P<code>.*?)\n```", re.DOTALL
)
_RST_BLOCK = re.compile(
    r"^\.\. code-block:: python\n\n(?P<code>(?:(?:[ \t]+[^\n]*)?\n)+)", re.MULTILINE
)
_RST_DIRECTIVE = re.compile(
    r"^[ \t]*\.\. (?:code-block|code|sourcecode|doctest)::[ \t]*(?P<language>\S*)",
    re.MULTILINE,
)
#: Languages a page may show without running: commands for a shell.
NOT_PYTHON = {"bash", "console", "text"}


def _line_of(text, offset):
    return text.count("\n", 0, offset) + 1


def markdown_blocks(path):
    """(line, code) for each ```python block not marked ``not run:``."""
    text = path.read_text(encoding="utf-8")
    return [
        (_line_of(text, match.start("code")), match["code"])
        for match in _MARKDOWN_BLOCK.finditer(text)
        if not match["before"].startswith("<!-- not run:")
    ]


def rst_blocks(path):
    """(line, code) for each ``.. code-block:: python``."""
    text = path.read_text(encoding="utf-8")
    return [
        (_line_of(text, match.start("code")), textwrap.dedent(match["code"]))
        for match in _RST_BLOCK.finditer(text)
    ]


def run_blocks(path, blocks, names=None):
    """Run the blocks in order in one namespace, and return it.

    Args:
        names: Names bound before the first block runs, if the page assumes
            any.
    """
    namespace = {"__name__": f"doc_example_{path.stem}", **(names or {})}
    for line, code in blocks:
        where = f"{path.name}:{line}"
        if code.lstrip().startswith(">>>"):
            test = doctest.DocTestParser().get_doctest(
                code, namespace, where, str(path), line - 1
            )
            output = io.StringIO()
            runner = doctest.DocTestRunner()
            runner.run(test, out=output.write, clear_globs=False)
            assert runner.failures == 0, f"{where}\n{output.getvalue()}"
            # A DocTest runs in a copy of the globals it is given, so what the
            # session defined has to be carried back for the blocks after it.
            namespace.update(test.globs)
        else:
            with contextlib.redirect_stdout(io.StringIO()):
                exec(compile(code, where, "exec"), namespace)
    return namespace


def destroy_worlds(*objects):
    """Destroy every live world among ``objects``, a scenario's included.

    Read when called, so a scenario that has rebuilt since gives up the world
    it has now, not the one it was made with.
    """
    from box2d import World

    for value in objects:
        world = value if isinstance(value, World) else getattr(value, "world", None)
        if isinstance(world, World) and world.is_valid:
            world.destroy()


def console_names(on_teardown):
    """What the testbed's console binds, with the Drop scenario running.

    The session on the console page is typed at the running testbed, where
    the console binds these. Drop is the one the scenarios page defines, built
    here as the testbed would open it. ``app`` is left out: it is the window.

    Args:
        on_teardown: Registers a function to call once the page has run,
            which destroys the worlds made here and by the page's own code.
    """
    import box2d
    from box2d import Vec2, World
    from box2d_testbed.testbed_state import state

    scenarios = run_blocks(SCENARIOS, rst_blocks(SCENARIOS))
    on_teardown(lambda: destroy_worlds(*scenarios.values()))
    world = World()
    test = scenarios["Drop"](world)
    on_teardown(lambda: destroy_worlds(world, test))
    test.setup()
    return {"test": test, "world": world, "state": state, "box2d": box2d, "Vec2": Vec2}


#: The names a page's examples assume, made fresh for each run of the page.
#: Each is called with a function that registers its cleanup.
PRELUDES = {CONSOLE: console_names}


@pytest.fixture
def scenario_registry_left_as_it_was():
    """The README and the scenarios page each define a scenario, which
    registers itself; take it out.

    BaseTest needs nothing from the testbed extra, so this runs everywhere.
    """
    from box2d_testbed.base_test import BaseTest

    before = {category: dict(tests) for category, tests in BaseTest.registry.items()}
    yield
    BaseTest.registry.clear()
    BaseTest.registry.update(before)


@pytest.fixture
def testbed_state_left_as_it_was():
    """Put the testbed's shared state back after a page has run.

    The console page binds it, and a page's code may set it -- the view, the
    pause, the settings -- which every testbed test after it would inherit.
    Like BaseTest, it needs nothing from the testbed extra.
    """
    from box2d_testbed.testbed_state import state

    before = dict(vars(state))
    yield
    vars(state).clear()
    vars(state).update(before)


def test_the_blocks_are_found():
    """A change of fence or directive must not leave nothing to run."""
    assert len(markdown_blocks(README)) == 3
    assert sum(len(rst_blocks(path)) for path in GLANCE) >= 3
    # Every overview of a class has an example; the math page lists only.
    overviews = [path for path in GLANCE if path.stem.endswith("_glance")]
    assert all(rst_blocks(path) for path in overviews if path.stem != "math_glance")
    assert len(rst_blocks(INSTALL)) >= 2
    assert len(rst_blocks(QUICKSTART)) >= 8
    assert all(rst_blocks(path) for path in GUIDES)
    assert len(rst_blocks(SCENARIOS)) >= 3
    assert len(rst_blocks(CONSOLE)) >= 2


@pytest.mark.parametrize("path", PAGES, ids=_page_id)
def test_every_python_block_is_run(path):
    """A block of Python the tests do not find would go unchecked: one with an
    option such as ``:caption:``, indented, or under another directive."""
    text = path.read_text(encoding="utf-8")
    languages = [match["language"] for match in _RST_DIRECTIVE.finditer(text)]
    assert set(languages) <= NOT_PYTHON | {"python"}, path.name
    assert languages.count("python") == len(rst_blocks(path)), path.name


def test_readme_examples_run(
    scenario_registry_left_as_it_was, testbed_state_left_as_it_was
):
    namespace = run_blocks(README, markdown_blocks(README))

    # The example simulation ends where its comment says.
    assert round(namespace["bodies"][0].position.y, 2) == -4.25

    # The example scenario builds, falls and goes to sleep, as it says.
    from box2d import World

    world = World()
    scenario = namespace["Drop"](world)
    scenario.setup()
    for _ in range(600):
        world.step(1 / 60, 4)
    assert scenario.status() == "asleep"
    world.destroy()


@pytest.mark.parametrize("path", PAGES, ids=_page_id)
def test_page_examples_run(
    path, request, scenario_registry_left_as_it_was, testbed_state_left_as_it_was
):
    prelude = PRELUDES.get(path)
    names = prelude(request.addfinalizer) if prelude else None
    run_blocks(path, rst_blocks(path), names)
