#!/usr/bin/env python
"""Measure what reading a step's moves costs, natively or inside Pyodide.

A renderer that redraws only what moved reads the world's move events once a
frame. With hundreds of awake bodies under Pyodide that reading can cost more
than the step, so this measures it, the step beside it for scale:

    python src/tools/bench_moves.py --bodies 500
    build/pyodide-venv/bin/python src/tools/bench_moves.py --bodies 500

Each way of reading is timed as a renderer would use it, from the step's
events to one packed record per moved body in a buffer:

- ``events``: ``world.get_body_events()`` alone, an object per moved body;
- ``events+pack``: the same, then each one packed into the buffer by hand;
- ``write_moves``: ``world.write_moves(buf)``, the records written in C. Left
  out when the box2d being measured has none.

Each frame's reading is repeated ``--repeat`` times on the same step and
averaged, since a browser's clock may tick only every millisecond or so.
Times are microseconds per frame: median, 95th percentile, worst.
"""

import argparse
import json
import statistics
import struct
import sys
import time

import box2d

#: The move record, as world.write_moves writes it.
RECORD = struct.Struct("<IffffI")


def parse_arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bodies", type=int, default=500, help="Awake bodies")
    parser.add_argument("--frames", type=int, default=300, help="Frames to measure")
    parser.add_argument(
        "--warmup", type=int, default=30, help="Frames to discard first"
    )
    parser.add_argument(
        "--repeat", type=int, default=10, help="Reads per frame, averaged"
    )
    parser.add_argument("--json", help="Also write the results here, as JSON")
    parser.add_argument("--label", default="", help="A note stored with the results")
    return parser.parse_args(argv)


def make_world(count):
    """A box of circles kept awake and stirred, so every one moves each step."""
    world = box2d.World(gravity=(0, -10))
    side = int(count**0.5) + 1
    walls = world.new_body().static()
    half = side * 0.6 + 1
    walls.box(2 * half, 1, offset=(0, -0.5))
    walls.box(1, 4 * half, offset=(-half, 2 * half))
    walls.box(1, 4 * half, offset=(half, 2 * half))
    walls.build()
    for i in range(count):
        x = (i % side) * 1.1 - side * 0.55
        y = (i // side) * 1.1 + 1
        world.new_body().dynamic().position(x, y).enable_sleep(False).circle(
            radius=0.4
        ).build()
    return world


def read_events(world, buffer):
    return len(world.get_body_events())


def read_and_pack(world, buffer):
    pack = RECORD.pack_into
    size = RECORD.size
    offset = 0
    for event in world.get_body_events():
        transform = event.transform
        pack(
            buffer,
            offset,
            event.body._body_id.index1,
            transform.p.x,
            transform.p.y,
            transform.q.c,
            transform.q.s,
            int(event.fell_asleep),
        )
        offset += size
    return offset // size


def read_into(world, buffer):
    return world.write_moves(buffer)


def summarise(samples):
    ordered = sorted(samples)
    return {
        "median": statistics.median(ordered),
        "p95": ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))],
        "max": ordered[-1],
    }


def main(argv=None):
    arguments = parse_arguments(argv)
    world = make_world(arguments.bodies)
    buffer = bytearray(RECORD.size * (arguments.bodies + 16))

    readers = {"events": read_events, "events+pack": read_and_pack}
    if hasattr(world, "write_moves"):
        readers["write_moves"] = read_into
    samples = {"step": [], **{name: [] for name in readers}}

    clock = time.perf_counter
    for frame in range(arguments.warmup + arguments.frames):
        start = clock()
        world.step(1 / 60, 4)
        step = clock() - start
        if frame < arguments.warmup:
            continue
        samples["step"].append(step * 1e6)
        for name, read in readers.items():
            start = clock()
            for _ in range(arguments.repeat):
                moved = read(world, buffer)
            samples[name].append((clock() - start) / arguments.repeat * 1e6)
            if moved < arguments.bodies:
                raise SystemExit(f"{name} read {moved} moves, expected every body")

    results = {
        "label": arguments.label,
        "platform": sys.platform,
        "python": sys.version.split()[0],
        "box2d": box2d.__version__,
        "bodies": arguments.bodies,
        "frames": arguments.frames,
        "us_per_frame": {name: summarise(values) for name, values in samples.items()},
    }
    world.destroy()

    print(
        f"{arguments.bodies} bodies, {arguments.frames} frames, "
        f"{results['platform']}, Python {results['python']}"
    )
    print(f"{'':>12} {'median':>9} {'p95':>9} {'max':>9}   (us per frame)")
    for name, summary in results["us_per_frame"].items():
        print(
            f"{name:>12} {summary['median']:9.1f} {summary['p95']:9.1f} "
            f"{summary['max']:9.1f}"
        )
    if arguments.json:
        with open(arguments.json, "w") as handle:
            json.dump(results, handle, indent=2)


if __name__ == "__main__":
    main()
