# tests/test_doc_examples.py
"""The Python in the README and the glance pages runs.

Each file's blocks run in order in one namespace, as a reader working down the
page would run them: a later block may use what an earlier one made. A block
written as a ``>>>`` session runs as a doctest, so its output is checked too.

A README block that cannot run here -- the console session, which needs the
running testbed -- is preceded by an HTML comment starting ``not run:``, which
renders as nothing on GitHub and PyPI.
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
GLANCE = sorted((ROOT / "docs" / "source" / "glance").glob("*.rst"))

_MARKDOWN_BLOCK = re.compile(
    r"(?P<before>[^\n]*)\n```python\n(?P<code>.*?)\n```", re.DOTALL
)
_RST_BLOCK = re.compile(
    r"^\.\. code-block:: python\n\n(?P<code>(?:(?:[ \t]+[^\n]*)?\n)+)", re.MULTILINE
)


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


def run_blocks(path, blocks):
    """Run the blocks in order in one namespace, and return it."""
    namespace = {"__name__": f"doc_example_{path.stem}"}
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


@pytest.fixture
def scenario_registry_left_as_it_was():
    """The README defines a scenario, which registers itself; take it out.

    BaseTest needs nothing from the testbed extra, so this runs everywhere.
    """
    from box2d_testbed.base_test import BaseTest

    before = {category: dict(tests) for category, tests in BaseTest.registry.items()}
    yield
    BaseTest.registry.clear()
    BaseTest.registry.update(before)


def test_the_blocks_are_found():
    """A change of fence or directive must not leave nothing to run."""
    assert len(markdown_blocks(README)) == 3
    assert sum(len(rst_blocks(path)) for path in GLANCE) >= 3


def test_readme_examples_run(scenario_registry_left_as_it_was):
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


@pytest.mark.parametrize("path", GLANCE, ids=lambda path: path.name)
def test_glance_examples_run(path):
    run_blocks(path, rst_blocks(path))
