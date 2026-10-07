# tests/test_ownership.py
"""A wrapper must stay alive for as long as Box2D holds its handle.

Box2D's user data on each body, shape and joint is a cffi handle to the Python
wrapper, which is how an id coming back from Box2D -- in a ray cast, an event,
``body.joints`` -- turns into the object the caller made. A handle does not
keep its object alive, so if the caller drops the wrapper and it is collected,
the next lookup through that handle reads freed memory and cffi aborts the
interpreter: ``Fatal Python error: ffi.from_handle() ... points to garbage``.

The crashes cannot be caught, so each is reproduced in a child interpreter and
the test asserts it exits cleanly.
"""

import contextlib
import gc
import io
import subprocess
import sys
import textwrap
import weakref

import pytest

from box2d import World

#: Run before each crash scenario's last line. Collecting frees any wrapper
#: nothing holds, and the allocations after it reuse that memory, so a dangling
#: handle reads garbage reliably rather than finding the old object intact.
_FORGET = """
import gc
gc.collect()
_churn = [bytearray(64) for _ in range(20000)]
"""


def run_isolated(*parts: str) -> str:
    """Run the program ``parts`` make up in a fresh interpreter, returning what
    it printed. Each part is dedented on its own, and ``FORGET()`` on a line of
    its own stands for collecting and reusing whatever nothing holds.

    Fails the test with the child's stderr if it did not exit cleanly, which is
    how a fatal error in cffi shows up: killed by SIGABRT.
    """
    program = "".join(textwrap.dedent(part) for part in parts)
    source = "from box2d import *\n" + program.replace("FORGET()", _FORGET)
    if sys.platform == "emscripten":
        # WebAssembly cannot start a subprocess. Run in this interpreter
        # instead, so the fix is still checked there; a regression aborts the
        # whole run rather than failing one test, which still fails the build.
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            exec(source, {"__name__": "isolated"})
        return printed.getvalue()
    result = subprocess.run(
        [sys.executable, "-c", source], capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, (
        f"the interpreter died with exit status {result.returncode}:\n"
        f"{result.stderr[-2000:]}"
    )
    return result.stdout


@pytest.fixture
def ground_and_ball(world):
    ground = world.new_body().static().build()
    ball = world.new_body().dynamic().position(0, 2).circle(0.5).build()
    return ground, ball


# --- joints ------------------------------------------------------------------


def test_reading_body_joints_after_dropping_the_joint():
    out = run_isolated(
        """
        world = World()
        ground = world.new_body().static().build()
        ball = world.new_body().dynamic().position(0, 2).circle(0.5).build()
        world.add_revolute_joint(ground, ball, anchor=(0, 2))
        FORGET()
        print(type(ball.joints[0]).__name__)
        """
    )
    assert out.strip() == "RevoluteJoint"


def test_body_joints_returns_the_joint_the_caller_was_given(world, ground_and_ball):
    ground, ball = ground_and_ball
    joint = world.add_revolute_joint(ground, ball, anchor=(0, 2))

    assert ball.joints[0] is joint
    assert ground.joints[0] is joint


def collected(make) -> bool:
    """Whether the object ``make()`` returns is freed once nothing else holds it."""
    ref = weakref.ref(make())
    gc.collect()
    return ref() is None


def test_a_destroyed_joint_is_released(world, ground_and_ball):
    ground, ball = ground_and_ball

    def destroyed_joint():
        joint = world.add_revolute_joint(ground, ball, anchor=(0, 2))
        joint.destroy()
        return joint

    assert collected(destroyed_joint)


@pytest.mark.parametrize("which", ["body_a", "body_b"])
def test_a_joint_destroyed_with_its_body_is_released(world, which):
    def joint_gone_with_a_body():
        ground = world.new_body().static().build()
        ball = world.new_body().dynamic().position(0, 2).circle(0.5).build()
        joint = world.add_revolute_joint(ground, ball, anchor=(0, 2))
        getattr(joint, which).destroy()
        assert not joint.is_valid
        return joint

    assert collected(joint_gone_with_a_body)


def test_objects_destroyed_with_their_world_are_released(world):
    """The world holds its bodies and joints only while Box2D has them, so a
    destroyed world that is still referenced does not pin everything it held."""
    refs = []

    def build():
        ground = world.new_body().static().build()
        ball = world.new_body().dynamic().position(0, 2).circle(0.5).build()
        joint = world.add_revolute_joint(ground, ball, anchor=(0, 2))
        refs.extend(weakref.ref(thing) for thing in (ground, ball, joint))

    build()
    world.destroy()
    gc.collect()

    assert [ref() for ref in refs] == [None, None, None]
    assert world.bodies == []


def test_a_world_with_joints_is_still_freed_when_dropped():
    """The world holds its joints and each joint holds its world, a cycle the
    collector has to break. Freeing the world is what destroys it in Box2D."""

    def world_with_joints():
        world = World()
        ground = world.new_body().static().build()
        ball = world.new_body().dynamic().position(0, 2).circle(0.5).build()
        world.add_revolute_joint(ground, ball, anchor=(0, 2))
        world.add_mouse_joint(ball, (1, 2))
        return world

    assert collected(world_with_joints)


def test_a_mouse_joint_gone_with_its_body_takes_its_proxy_body_too(
    world, ground_and_ball
):
    """The drag is a kinematic proxy body joined to the dragged one. Box2D
    takes the joint down with the dragged body, and the proxy, which nothing
    else uses, goes with it rather than lingering in the world."""
    ground, ball = ground_and_ball
    joint = world.add_mouse_joint(ball, (1, 2))
    assert len(world.bodies) == 3

    ball.destroy()

    assert world.bodies == [ground]
    assert not joint.is_valid
    joint.destroy()  # still allowed, and still a no-op


def test_a_mouse_joint_whose_proxy_body_is_destroyed(world, ground_and_ball):
    """The proxy is reachable through world.bodies, so it can be destroyed
    like any other body, which takes the joint with it."""
    ground, ball = ground_and_ball
    joint = world.add_mouse_joint(ball, (1, 2))
    proxy = next(body for body in world.bodies if body not in (ground, ball))

    proxy.destroy()

    assert world.bodies == [ground, ball]
    assert not joint.is_valid
    assert ball.joints == []


#: A pendulum whose joint reports an event on every step it carries load.
_REPORTING_JOINT = """
world = World()
ground = world.new_body().static().build()
ball = world.new_body().dynamic().position(1, 2).circle(0.5).build()
joint = world.add_revolute_joint(ground, ball, anchor=(0, 2))
joint.force_threshold = 0.0
"""


def test_joint_events_after_dropping_the_joint():
    out = run_isolated(
        _REPORTING_JOINT,
        """
        del joint
        FORGET()
        world.step(1 / 60)
        print(type(world.get_joint_events()[0].joint).__name__)
        """,
    )
    assert out.strip() == "RevoluteJoint"


# --- shapes --------------------------------------------------------------------


@pytest.mark.parametrize(
    "make, hit",
    [
        ("Circle.create(ground, radius=1.0)", "Circle"),
        ("Box.create(ground, 2, 2)", "Box"),
        ("Capsule.create(ground, (-1, 0), (1, 0), radius=0.5)", "Capsule"),
        ("Polygon.create(ground, [(-1, -1), (1, -1), (0, 1)])", "Polygon"),
        ("Segment.create(ground, (0, -1), (0, 1))", "Segment"),
        (
            "Chain.create(ground, [(-1, -1), (1, -1), (1, 1), (-1, 1)], loop=True)",
            "ChainSegment",
        ),
    ],
)
def test_a_shape_made_directly_and_dropped(make, hit):
    """The shape classes are public, and their ``create`` builds a shape without
    going through ``body.add_*``, which was where the body took hold of it."""
    out = run_isolated(
        f"""
        world = World()
        ground = world.new_body().static().build()
        {make}
        FORGET()
        hits = world.ray_cast((-5, 0.1), (10, 0))
        print(type(hits[0].shape).__name__)
        """
    )
    assert out.strip() == hit


def test_a_shape_made_directly_belongs_to_its_body(world):
    from box2d import Chain, Circle

    body = world.new_body().static().build()
    shape = Circle.create(body, radius=1.0)
    chain = Chain.create(body, [(-1, -1), (1, -1), (1, 1)])

    assert body.shapes == [shape]
    assert body.chains == [chain]
