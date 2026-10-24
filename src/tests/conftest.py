"""Fixtures shared by the whole suite."""

import os
import random

import pytest

from box2d import World


@pytest.fixture(autouse=True, scope="session")
def isolated_scenario_dir(tmp_path_factory):
    """Keep the tests out of the user's own scenario directory.

    The testbed loads editable scenarios from a directory outside the project,
    and several tests build the whole app. Left alone they would run against
    whatever happens to be on the machine -- and a test that saves would write
    there. So the directory is redirected for the session, which is what
    BOX2D_TESTBED_SCENARIOS is for.
    """
    path = tmp_path_factory.mktemp("scenarios")
    previous = os.environ.get("BOX2D_TESTBED_SCENARIOS")
    os.environ["BOX2D_TESTBED_SCENARIOS"] = str(path)
    try:
        yield path
    finally:
        if previous is None:
            os.environ.pop("BOX2D_TESTBED_SCENARIOS", None)
        else:
            os.environ["BOX2D_TESTBED_SCENARIOS"] = previous


@pytest.fixture
def world():
    """A fresh world, destroyed after the test.

    Test modules that need one set up differently define their own ``world``,
    which takes precedence over this.
    """
    world = World()
    yield world
    world.destroy()


@pytest.fixture(autouse=True)
def rebuilt_worlds_destroyed(monkeypatch):
    """Destroy every world a scenario's rebuild made, after the test.

    A rebuild builds the scene again in a new world, which the scenario holds
    and the test never sees, so no fixture of the test's destroys it. Left to
    the garbage collector, Box2D's 128 world slots run out in a run with it
    off, or merely slow. So the worlds are recorded where rebuilds make them.
    """
    try:
        from box2d_testbed import base_test
    except ImportError:  # no testbed, so no rebuilds
        yield
        return

    made = []

    def recorded(*args, **kwargs):
        world = World(*args, **kwargs)
        made.append(world)
        return world

    monkeypatch.setattr(base_test, "World", recorded)
    yield
    for world in made:
        world.destroy()  # a no-op on one a later rebuild destroyed


@pytest.fixture
def random_left_as_it_was():
    """Put Python's random numbers back as they were after the test.

    For tests that seed the random module, which is shared: left seeded, it
    would hand every test after them the same numbers.
    """
    saved = random.getstate()
    yield
    random.setstate(saved)
