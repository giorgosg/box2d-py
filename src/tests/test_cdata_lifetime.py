"""Lifetime rules for the C structures the bindings hand to Box2D.

These bugs are close to invisible on Linux. A structure that is freed too
early usually still holds its data, because glibc does not hand the block to
anything else before Box2D reads it, so the binding looks correct. macOS
reuses the block immediately and Box2D reads zeros -- which is how a dangling
polygon and two dangling joint frames were found, by CI, months after they
were written.

So the rules are pinned here rather than left to the platform. The tests
force the reuse that macOS does on its own: allocating many blocks of the
same size after the structure should have died, and reading what is left.
"""

import pytest

import box2d
from box2d._box2d import ffi, lib
from box2d.shapedef import PolygonDef


def churn(kind="b2Transform", count=3000):
    """Allocate enough blocks to reclaim anything just freed.

    What lands in the reclaimed block is the allocator's business: cffi
    zeroes what it hands out, so Linux and macOS read back zeros, while
    Windows leaves whatever was there. The tests below therefore ask only
    whether the original data survived, which is the actual invariant --
    asserting zeros made this suite fail on Windows, intermittently.
    """
    return [ffi.new(f"{kind} *") for _ in range(count)]


def a_transform():
    """A transform whose owner is dropped as soon as this returns."""
    transform = ffi.new("b2Transform *")
    transform.p.x = 3.0
    transform.p.y = 1.0
    return transform[0]


def test_dereferencing_keeps_the_pointer_alive():
    """p[0] chains ownership, so ``value.b2Vec2[0]`` is safe to pass along.

    Almost every call in the bindings relies on this: the property builds a
    structure, [0] dereferences it, and the result is passed by value. If
    this rule ever changed, most of the binding would be reading freed
    memory rather than the three places that were.
    """
    value = a_transform()
    _junk = churn()
    assert (value.p.x, value.p.y) == (3.0, 1.0)


def test_a_struct_field_does_not_keep_its_structure_alive():
    """Why the joint frame getters bind the frame to a local first."""
    point = a_transform().p  # the transform dies here
    _junk = churn()
    assert (point.x, point.y) != (3.0, 1.0), (
        "taking a struct field now keeps the structure alive; the frame "
        "getters in joint.py no longer need their local"
    )


def test_addressof_does_not_keep_its_argument_alive():
    """Why the polygon setter binds the polygon to a local first."""
    pointer = ffi.addressof(a_transform())  # the transform dies here
    _junk = churn()
    assert (pointer.p.x, pointer.p.y) != (3.0, 1.0), (
        "ffi.addressof now keeps its argument alive; the local in "
        "Polygon.geometry is no longer load-bearing"
    )


@pytest.fixture
def body():
    world = box2d.World()
    yield world.add_body(position=(0, 0))
    world.destroy()


def test_polygon_geometry_survives_a_hostile_allocator(body, monkeypatch):
    """The polygon must still be alive when Box2D reads it.

    The gap that matters is between taking the address and Box2D following
    it: that is where a temporary has already died and where macOS happens to
    reuse the block. Reclaiming inside b2Shape_SetPolygon reproduces that gap
    on any platform -- churning any earlier proves nothing, because the
    temporary is still an argument on the stack.
    """
    kept_alive = []

    class HostileLib:
        """Forwards to the real lib, reclaiming freed blocks on the way in."""

        def __getattr__(self, name):
            return getattr(lib, name)

        def b2Shape_SetPolygon(self, shape_id, pointer):
            kept_alive.append(churn("b2Polygon"))
            return lib.b2Shape_SetPolygon(shape_id, pointer)

    polygon = body.add_polygon(vertices=[(-1, -1), (1, -1), (1, 1), (-1, 1)])
    # The module's own name for lib -- the compiled object is read-only.
    monkeypatch.setattr(box2d.shape, "lib", HostileLib())
    polygon.geometry = PolygonDef([(0, 0), (2, 0), (2, 2)])

    assert len(polygon.vertices) == 3


def test_local_anchors_read_back_what_was_set(body):
    """The plain round trip macOS caught, kept as the behavioural check."""
    other = body.world.add_body(position=(5, 0))
    joint = body.world.add_joint(box2d.RevoluteJointDef(body, other, anchor=(1, 1)))

    joint.local_anchor_a = (3, 1)
    assert joint.local_anchor_a == box2d.Vec2(3, 1)

    joint.local_anchor_b = (-1, 0)
    assert joint.local_anchor_b == box2d.Vec2(-1, 0)


def test_getting_a_polygon_does_not_depend_on_box2d_internals():
    """b2Shape_GetPolygon returns by value; the count must come back intact."""
    world = box2d.World()
    try:
        body = world.add_body(position=(0, 0))
        shape = body.add_box(width=2, height=2)
        _junk = churn("b2Polygon")
        assert len(shape.vertices) == 4
    finally:
        world.destroy()


def test_the_binding_never_addresses_a_temporary():
    """A source check, because the runtime symptom only shows on macOS.

    ffi.addressof must be given a name that is still live at the call, not an
    expression that builds a structure on the spot.
    """
    import pathlib
    import re

    package = pathlib.Path(box2d.__file__).parent
    # Only a bare local, or an attribute of self. Anything else cannot be told
    # apart from the bug: `polygon_def.b2Polygon` builds a structure on the
    # spot and `self._def` returns one the instance holds, and the two are
    # spelled identically. Requiring a local settles it at the call site.
    safe = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*|self\.[A-Za-z_][A-Za-z0-9_]*)$")
    offenders = []

    for source in sorted(package.glob("*.py")):
        for number, line in enumerate(source.read_text().splitlines(), 1):
            for argument in re.findall(r"ffi\.addressof\(([^()]*)\)", line):
                if not safe.match(argument.strip()):
                    offenders.append(f"{source.name}:{number}: {argument.strip()}")

    assert not offenders, "ffi.addressof given a temporary:\n" + "\n".join(offenders)


def test_the_binding_never_keeps_a_field_of_a_returned_structure():
    """The joint-frame bug, checked at the source.

    Unlike the polygon setter, this one cannot be provoked at runtime here:
    the freed structure is read while building the return value, with no
    point in between to reclaim the block from. So the shape of the code is
    what gets checked -- binding a struct field of a value Box2D just
    returned, instead of the value itself.
    """
    import ast
    import pathlib

    package = pathlib.Path(box2d.__file__).parent
    offenders = []

    for source in sorted(package.glob("*.py")):
        tree = ast.parse(source.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            value = node.value
            # name = lib.b2Something(...).field
            if (
                isinstance(value, ast.Attribute)
                and isinstance(value.value, ast.Call)
                and isinstance(value.value.func, ast.Attribute)
                and isinstance(value.value.func.value, ast.Name)
                and value.value.func.value.id == "lib"
            ):
                call = value.value.func.attr
                offenders.append(
                    f"{source.name}:{node.lineno}: {call}(...).{value.attr}"
                )

    assert not offenders, (
        "a field was kept from a structure Box2D returned; bind the "
        "structure to a local and read through it:\n" + "\n".join(offenders)
    )
