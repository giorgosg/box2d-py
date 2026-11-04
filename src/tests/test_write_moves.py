"""A step's moves written straight into a buffer the caller owns.

world.write_moves(buf) is get_body_events without an object per body: one
fixed 24-byte record per moved body, written in C, keyed by the body's slot
(body.key) rather than by its wrapper. The application maps keys to its own
objects, which is what the created and destroyed hooks are for.
"""

import array
import math
import struct

import pytest

from box2d import MOVE_RECORD, Body, DestroyedError, MoveFlags, World

RECORD = struct.Struct(MOVE_RECORD.struct)


def rows(buffer, count):
    """The first `count` records, as dicts by field name."""
    names = [field.name for field in MOVE_RECORD.fields]
    return [
        dict(zip(names, RECORD.unpack_from(buffer, i * RECORD.size)))
        for i in range(count)
    ]


def falling(world, count=3):
    """`count` dynamic circles in the air, so every one moves on a step."""
    return [
        world.new_body().dynamic().position(i * 2, 5).circle(0.5).build()
        for i in range(count)
    ]


# -- the record ------------------------------------------------------------------


def test_the_record_is_24_little_endian_bytes():
    assert MOVE_RECORD.itemsize == 24 == RECORD.size
    assert MOVE_RECORD.struct == "<IffffI"
    assert [(f.name, f.offset, f.type) for f in MOVE_RECORD.fields] == [
        ("key", 0, "u32"),
        ("x", 4, "f32"),
        ("y", 8, "f32"),
        ("cos", 12, "f32"),
        ("sin", 16, "f32"),
        ("flags", 20, "u32"),
    ]
    assert MOVE_RECORD.version == 1


def test_the_c_record_matches_its_description():
    from box2d._box2d import ffi

    assert ffi.sizeof("b2pyMoveRecord") == MOVE_RECORD.itemsize
    c_names = {"key": "key", "x": "x", "y": "y", "cos": "c", "sin": "s"}
    c_names["flags"] = "flags"
    for field in MOVE_RECORD.fields:
        assert ffi.offsetof("b2pyMoveRecord", c_names[field.name]) == field.offset


def test_the_record_is_a_numpy_dtype():
    np = pytest.importorskip("numpy")
    dtype = np.dtype(MOVE_RECORD.numpy)
    assert dtype.itemsize == 24
    assert dtype.names == ("key", "x", "y", "cos", "sin", "flags")
    assert dtype["key"] == np.dtype("<u4") and dtype["x"] == np.dtype("<f4")


# -- writing ---------------------------------------------------------------------


def test_each_moved_body_is_one_record(world):
    bodies = falling(world)
    world.step(1 / 60, 4)
    buffer = bytearray(MOVE_RECORD.itemsize * 8)

    count = world.write_moves(buffer)

    assert count == 3
    written = {row["key"]: row for row in rows(buffer, count)}
    assert set(written) == {body.key for body in bodies}
    for body in bodies:
        row = written[body.key]
        assert row["x"] == pytest.approx(body.position.x)
        assert row["y"] == pytest.approx(body.position.y)
        assert row["cos"] == pytest.approx(math.cos(body.rotation), abs=1e-6)
        assert row["sin"] == pytest.approx(math.sin(body.rotation), abs=1e-6)
        assert row["flags"] == 0


def test_it_writes_what_get_body_events_reports(world):
    falling(world, 5)
    for _ in range(10):
        world.step(1 / 60, 4)
    buffer = bytearray(MOVE_RECORD.itemsize * 8)

    count = world.write_moves(buffer)

    events = world.get_body_events()
    assert count == len(events)
    assert [row["key"] for row in rows(buffer, count)] == [
        event.body.key for event in events
    ]
    for row, event in zip(rows(buffer, count), events):
        assert (row["x"], row["y"]) == pytest.approx(tuple(event.transform.p))
        assert (row["cos"], row["sin"]) == pytest.approx(
            (event.transform.q.c, event.transform.q.s)
        )


def test_a_body_falling_asleep_is_flagged(world):
    world.new_body().static().box(20, 1).build()
    crate = world.new_body().dynamic().position(0, 3).box(1, 1).build()
    buffer = bytearray(MOVE_RECORD.itemsize)
    flags = []
    for _ in range(300):
        world.step(1 / 60, 4)
        if world.write_moves(buffer):
            flags.append(rows(buffer, 1)[0]["flags"])
        if not crate.awake:
            break

    assert flags[-1] == MoveFlags.ASLEEP
    assert set(flags[:-1]) == {0}


def test_a_buffer_too_small_gets_what_fits_and_the_count_needed(world):
    falling(world, 4)
    world.step(1 / 60, 4)
    whole = bytearray(MOVE_RECORD.itemsize * 4)
    world.write_moves(whole)
    # One record and a half: only the whole record is written.
    small = bytearray(MOVE_RECORD.itemsize + 12)

    assert world.write_moves(small) == 4
    assert small[: MOVE_RECORD.itemsize] == whole[: MOVE_RECORD.itemsize]
    assert small[MOVE_RECORD.itemsize :] == bytes(12)
    assert world.write_moves(bytearray()) == 4


def test_move_count_sizes_the_buffer(world):
    falling(world, 3)
    assert world.move_count == 0
    world.step(1 / 60, 4)
    assert world.move_count == 3


def test_a_destroyed_body_is_left_out_even_when_its_slot_is_reused(world):
    first, second = falling(world, 2)
    world.step(1 / 60, 4)
    key = first.key
    first.destroy()
    # Box2D hands the freed slot to the next body made.
    reborn = world.new_body().dynamic().position(-5, 5).build()
    assert reborn.key == key
    buffer = bytearray(MOVE_RECORD.itemsize * 4)

    count = world.write_moves(buffer)

    # The step's event for the old body is stale; the new one has not moved.
    assert [row["key"] for row in rows(buffer, count)] == [second.key]


@pytest.mark.parametrize(
    "make",
    [
        lambda size: memoryview(bytearray(size)),
        lambda size: array.array("I", bytes(size)),
    ],
    ids=["memoryview", "array"],
)
def test_any_writable_buffer_will_do(world, make):
    falling(world, 2)
    world.step(1 / 60, 4)
    buffer = make(MOVE_RECORD.itemsize * 2)

    assert world.write_moves(buffer) == 2
    assert {row["key"] for row in rows(bytes(buffer), 2)} == {
        body.key for body in world.bodies
    }


def test_a_numpy_array_of_records(world):
    np = pytest.importorskip("numpy")
    bodies = falling(world, 3)
    world.step(1 / 60, 4)
    records = np.zeros(8, dtype=np.dtype(MOVE_RECORD.numpy))

    count = world.write_moves(records)

    assert sorted(records["key"][:count]) == sorted(body.key for body in bodies)


def test_a_read_only_buffer_is_refused(world):
    falling(world, 1)
    world.step(1 / 60, 4)
    with pytest.raises(BufferError):
        world.write_moves(bytes(MOVE_RECORD.itemsize))


# -- every body, not just the moved ----------------------------------------------


def test_write_transforms_writes_every_body(world):
    ground = world.new_body().static().position(0, -1).box(20, 1).build()
    bodies = falling(world, 2)
    buffer = bytearray(MOVE_RECORD.itemsize * 4)

    count = world.write_transforms(buffer)

    assert count == 3
    written = {row["key"]: row for row in rows(buffer, count)}
    assert set(written) == {ground.key, *(body.key for body in bodies)}
    assert written[ground.key]["y"] == -1
    assert written[ground.key]["cos"] == 1


def test_write_transforms_takes_the_bodies_to_write(world):
    first, second = falling(world, 2)
    second.rotation = math.pi / 2
    buffer = bytearray(MOVE_RECORD.itemsize * 4)

    assert world.write_transforms(buffer, [second]) == 1
    (row,) = rows(buffer, 1)
    assert row["key"] == second.key
    assert (row["cos"], row["sin"]) == pytest.approx((0, 1), abs=1e-6)


def test_write_transforms_flags_sleeping_bodies(world):
    sleeper, waker = falling(world, 2)
    sleeper.awake = False
    buffer = bytearray(MOVE_RECORD.itemsize * 2)

    world.write_transforms(buffer, [sleeper, waker])

    assert [row["flags"] for row in rows(buffer, 2)] == [MoveFlags.ASLEEP, 0]


def test_write_transforms_refuses_destroyed_and_foreign_bodies(world):
    (body,) = falling(world, 1)
    body.destroy()
    buffer = bytearray(MOVE_RECORD.itemsize * 2)
    with pytest.raises(DestroyedError):
        world.write_transforms(buffer, [body])

    other = World()
    try:
        stranger = other.add_body()
        with pytest.raises(ValueError, match="another world"):
            world.write_transforms(buffer, [stranger])
    finally:
        other.destroy()


# -- the key -----------------------------------------------------------------------


def test_a_key_is_the_bodys_box2d_slot(world):
    a, b = world.add_body(), world.add_body()
    assert isinstance(a.key, int) and a.key != b.key
    assert a.key == a._body_id.index1


def test_a_key_stays_with_the_body_for_its_life(world):
    (body,) = falling(world, 1)
    key = body.key
    for _ in range(10):
        world.step(1 / 60, 4)
    assert body.key == key


def test_a_destroyed_body_has_no_key(world):
    body = world.add_body()
    body.destroy()
    with pytest.raises(DestroyedError):
        body.key


def test_key_is_read_only(world):
    body = world.add_body()
    with pytest.raises(AttributeError):
        body.key = 3


def test_a_mapped_body_class_has_a_key_too():
    class Ball(Body):
        pass

    world = World(classes={Body: Ball})
    try:
        ball = world.add_body()
        assert ball.key == ball._body_id.index1
    finally:
        world.destroy()


# -- what the review found ----------------------------------------------------------


def test_write_transforms_never_calls_static_or_disabled_bodies_asleep(world):
    ground = world.new_body().static().box(20, 1).build()
    (parked,) = falling(world, 1)
    parked.enabled = False
    buffer = bytearray(MOVE_RECORD.itemsize * 2)

    world.write_transforms(buffer, [ground, parked])

    assert [row["flags"] for row in rows(buffer, 2)] == [0, 0]


def test_write_transforms_on_a_destroyed_world_raises():
    world = World()
    world.destroy()
    with pytest.raises(DestroyedError):
        world.write_transforms(bytearray(MOVE_RECORD.itemsize))


def test_a_buffer_is_let_go_of_even_when_writing_raises(world):
    body = world.add_body()
    body.destroy()
    buffer = bytearray(MOVE_RECORD.itemsize)
    with pytest.raises(DestroyedError):
        world.write_transforms(buffer, [body])
    # A bytearray still exported to C could not be resized.
    buffer.extend(bytes(MOVE_RECORD.itemsize))
    world.write_moves(buffer)
    buffer.extend(bytes(1))


def test_inside_a_step_there_are_no_moves_yet(world):
    world.new_body().static().box(20, 1, enable_pre_solve_events=True).build()
    world.new_body().dynamic().position(0, 0.6).box(
        1, 1, enable_pre_solve_events=True
    ).build()
    seen = []

    def during(shape_a, shape_b, manifold):
        seen.append(world.write_moves(bytearray(MOVE_RECORD.itemsize * 4)))
        return True

    world.pre_solve = during
    world.step(1 / 60, 4)
    assert seen and set(seen) == {0}


def test_a_record_layout_cannot_be_changed():
    with pytest.raises(AttributeError):
        MOVE_RECORD.itemsize = 3
